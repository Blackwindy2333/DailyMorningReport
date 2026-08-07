"""封面图处理：下载 → runtime_dir 缓存 → base64 内嵌。

策略：渲染前把封面 URL 下载到 runtime_dir/covers/<hash>.jpg，读入转 base64 内嵌
到 HTML 的 <img src="data:image/jpeg;base64,...">。规避豆瓣/Bangumi/RAWG 防盗链，
不依赖 html2png 的网络权限。下载失败则返回占位（None），不影响整图。

懒加载策略：并发下载限制（信号量，默认 4 路）+ 单张超时，避免封面多时串行拖慢
渲染；已缓存封面直接命中，不再请求网络。
"""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ..collectors.base import content_hash

_CACHE_PREFIX = "covers"
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_MAX_CONCURRENT = 4
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 单张封面最大 5MB，防内存耗尽
_MAX_REDIRECTS = 5


async def _is_safe_url(url: str) -> bool:
    """SSRF 防护：仅允许 http/https，且解析后的 IP 非私网/环回/链路本地/多播。"""
    try:
        if url.startswith("//"):  # protocol-relative（如豆瓣封面 //img...）
            url = "https:" + url
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        loop = asyncio.get_event_loop()
        try:
            addr_info = await loop.getaddrinfo(parsed.hostname, None)
        except Exception:
            return False
        for addr in addr_info:  # 全量校验，不限于前 8 条，防混合 A 记录绕过
            try:
                ip = ipaddress.ip_address(addr[4][0])
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_unspecified
                    or ip.is_link_local
                    or ip.is_multicast
                ):
                    return False
            except ValueError:
                return False
        return True
    except Exception:
        return False


class CoverManager:
    """封面下载与缓存管理器。"""

    def __init__(self, runtime_dir: Path, logger: logging.Logger, timeout: float = 15.0) -> None:
        self._cache_dir = runtime_dir / _CACHE_PREFIX
        self._logger = logger
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        self._inflight: dict[str, asyncio.Task] = {}  # 同 URL 去重，防并发重复下载

    async def close(self) -> None:
        """关闭内部客户端。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=False,  # 手动跟随并在每次跳转时校验 SSRF
            )
        return self._client

    def _cache_path(self, url: str, suffix: str = ".jpg") -> Path:
        """按 URL 哈希生成缓存文件路径（白名单文件名）。"""
        return self._cache_dir / f"{content_hash(url)}{suffix}"

    def load_base64(self, url: str) -> str | None:
        """从缓存读取封面并转 base64；缓存未命中返回 None。"""
        if not url:
            return None
        # 兼容历史 .jpg 缓存与按 content-type 保存的扩展名
        for suffix in _IMAGE_EXTENSIONS:
            path = self._cache_path(url, suffix)
            if path.exists():
                break
        else:
            return None
        try:
            data = path.read_bytes()
        except OSError:
            return None
        mime = _guess_mime(path)
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    async def ensure_cover(self, url: str) -> str | None:
        """确保封面已缓存并返回 data URL；失败返回 None（渲染层用占位）。"""
        cached = self.load_base64(url)
        if cached is not None:
            return cached
        # 同 URL 并发去重：已有在下载则复用，避免重复请求
        existing = self._inflight.get(url)
        if existing and not existing.done():
            return await existing

        async def _worker() -> str | None:
            async with self._semaphore:  # 限制并发下载
                return await self._download(url)

        task = asyncio.create_task(_worker())
        self._inflight[url] = task
        try:
            return await task
        finally:
            self._inflight.pop(url, None)

    async def _download(self, url: str) -> str | None:
        data, suffix = await self._safe_download(url)
        if data is None:
            return None
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(url, suffix)
            path.write_bytes(data)
        except OSError as exc:
            self._logger.warning("封面缓存写入失败: %s (%s)", url, exc)
            return None
        return self.load_base64(url)

    async def _safe_download(self, url: str) -> tuple[bytes | None, str]:
        """安全下载：手动跟随重定向（每次跳转校验 SSRF）+ 流式读取限制大小。

        返回 (图片字节, 扩展名)；失败返回 (None, "")。
        """
        client = await self._get_client()
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            if not await _is_safe_url(current):
                self._logger.warning("封面 URL 未通过 SSRF 校验，跳过: %s", current)
                return None, ""
            try:
                async with client.stream(
                    "GET", current, follow_redirects=False,
                    headers={"Referer": _referer_of(current)},
                ) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            return None, ""
                        current = str(httpx.URL(current).join(location))
                        continue
                    if response.status_code != 200:
                        self._logger.warning("封面下载失败 HTTP %s: %s", response.status_code, current)
                        return None, ""
                    content_type = response.headers.get("content-type", "")
                    if not _is_image(content_type, current):
                        self._logger.warning("封面非图片类型: %s (%s)", current, content_type)
                        return None, ""
                    data = b""
                    async for chunk in response.aiter_bytes():
                        data += chunk
                        if len(data) > _MAX_IMAGE_BYTES:
                            self._logger.warning("封面前 %d 字节超限（>%d），跳过: %s", len(data), _MAX_IMAGE_BYTES, current)
                            return None, ""
                    return data, _suffix_for(content_type)
            except httpx.HTTPError as exc:
                self._logger.warning("封面下载异常: %s (%s)", current, exc)
                return None, ""
        self._logger.warning("封面下载重定向次数超限: %s", url)
        return None, ""


def _guess_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".png": "image/png",
        ".webp": "image/webp",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suffix, "image/jpeg")


def _suffix_for(content_type: str) -> str:
    """按 content-type 推断缓存文件扩展名。"""
    return {
        "image/png": ".png",
        "image/webp": ".webp",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }.get(content_type.split(";")[0].strip().lower(), ".jpg")


_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
)


def _is_image(content_type: str, url: str) -> bool:
    # 白名单仅允许具体位图类型，排除 svg 等可能异常的格式
    if content_type:
        return content_type.split(";")[0].strip().lower() in _IMAGE_CONTENT_TYPES
    return any(url.lower().endswith(ext) for ext in _IMAGE_EXTENSIONS)


def _referer_of(url: str) -> str:
    """根据封面来源生成 Referer（豆瓣/Bangumi/RAWG 防盗链）。"""
    if "douban" in url:
        return "https://movie.douban.com/"
    if "bgm.tv" in url or "lain.bgm.tv" in url:
        return "https://bgm.tv/"
    if "rawg.io" in url:
        return "https://rawg.io/"
    return ""
