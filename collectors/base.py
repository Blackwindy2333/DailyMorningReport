"""采集器基础框架：统一结果结构、异常与抽象基类。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class CollectorError(Exception):
    """采集器内部错误，统一由 collect() 收敛为 CollectorResult。"""


def mask_key(api_key: str) -> str:
    """日志脱敏：仅保留前 4 位，其余打码。"""
    if not api_key:
        return ""
    return api_key[:4] + "****"


@dataclass
class CollectorResult:
    """采集器统一输出结构。"""

    module_id: str
    status: Literal["ok", "error"]
    data: dict[str, Any] = field(default_factory=dict)
    error_msg: str = ""
    fetched_at: str = ""


class BaseCollector:
    """所有采集器的抽象基类，子类只需实现 collect()。"""

    module_id: str = ""
    display_name: str = ""

    def __init__(self, config: Any, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._client: httpx.AsyncClient | None = None

    @property
    def _timeout(self) -> float:
        return float(self.config.basic.request_timeout)

    @property
    def _retry_count(self) -> int:
        return max(1, int(self.config.basic.retry_count))

    @property
    def _retry_interval(self) -> float:
        return float(self.config.basic.retry_interval)

    async def get_client(self) -> httpx.AsyncClient:
        """懒创建共享异步客户端（浏览器 UA）。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers={"User-Agent": DEFAULT_USER_AGENT},
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """关闭会话（on_unload 调用）。"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _retryable(self, exc: Exception, status_code: int | None = None) -> bool:
        """判断错误是否值得重试：连接错误/超时/5xx 重试，4xx 不重试。"""
        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
            return True
        if status_code is not None and status_code >= 500:
            return True
        return False

    async def _request_with_retry(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET 请求，带可配置重试（指数退避），失败抛 CollectorError。"""
        client = await self.get_client()
        last_exc: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                response = await client.get(url, **kwargs)
                if response.status_code >= 400:
                    if self._retryable(Exception(), response.status_code) and attempt < self._retry_count - 1:
                        await asyncio.sleep(self._retry_interval * (2**attempt))
                        continue
                    raise CollectorError(f"HTTP {response.status_code}: {url}")
                return response
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_exc = exc
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_interval * (2**attempt))
                    continue
                raise CollectorError(f"请求失败: {exc}") from exc
        raise CollectorError(f"请求失败: {last_exc}")

    async def fetch_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """GET + JSON 解析，带重试；失败抛 CollectorError。"""
        response = await self._request_with_retry(url, **kwargs)
        try:
            data = response.json()
        except ValueError as exc:
            raise CollectorError(f"JSON 解析失败: {url}") from exc
        if not isinstance(data, dict):
            raise CollectorError(f"响应非 JSON 对象: {url}")
        return data

    async def fetch_text(self, url: str, **kwargs: Any) -> str:
        """GET + 文本解码，带重试；失败抛 CollectorError。"""
        response = await self._request_with_retry(url, **kwargs)
        return response.text

    def error_result(self, error_msg: str) -> CollectorResult:
        """构造失败结果（异常不向上泄漏）。"""
        self.logger.warning("采集失败 [%s]: %s", self.module_id, error_msg)
        return CollectorResult(module_id=self.module_id, status="error", error_msg=error_msg)

    async def collect(self) -> CollectorResult:
        """子类实现：取数 → 解析 → 返回 CollectorResult。"""
        raise NotImplementedError


def content_hash(url: str) -> str:
    """封面 URL 内容哈希（文件名白名单用）。"""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
