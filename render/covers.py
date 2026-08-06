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
import logging
from pathlib import Path

import httpx

from ..collectors.base import content_hash

_CACHE_PREFIX = "covers"
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
_MAX_CONCURRENT = 4


class CoverManager:
    """封面下载与缓存管理器。"""

    def __init__(self, runtime_dir: Path, logger: logging.Logger, timeout: float = 15.0) -> None:
        self._cache_dir = runtime_dir / _CACHE_PREFIX
        self._logger = logger
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    async def close(self) -> None:
        """关闭内部客户端。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
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
        async with self._semaphore:  # 限制并发下载
            return await self._download(url)

    async def _download(self, url: str) -> str | None:
        try:
            client = await self._get_client()
            response = await client.get(url, headers={"Referer": _referer_of(url)})
            if response.status_code != 200:
                self._logger.warning("封面下载失败 HTTP %s: %s", response.status_code, url)
                return None
            content_type = response.headers.get("content-type", "")
            if not _is_image(content_type, url):
                self._logger.warning("封面非图片类型: %s (%s)", url, content_type)
                return None
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_path(url, _suffix_for(content_type))
            path.write_bytes(response.content)
            return self.load_base64(url)
        except httpx.HTTPError as exc:
            self._logger.warning("封面下载异常: %s (%s)", url, exc)
            return None


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


def _is_image(content_type: str, url: str) -> bool:
    if content_type and content_type.startswith("image/"):
        return True
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
