"""重试与错误处理测试：用 httpx.MockTransport 注入失败/成功响应。"""

import logging

import httpx
import pytest

from DailyMorningReport.collectors.base import (
    BaseCollector,
    CollectorError,
    CollectorResult,
)

logger = logging.getLogger("test")


class _EchoCollector(BaseCollector):
    """测试用采集器：直接暴露 fetch_json。"""

    module_id = "echo"
    display_name = "测试"

    async def collect(self) -> CollectorResult:
        try:
            data = await self.fetch_json("https://example.com/data")
            return CollectorResult(module_id=self.module_id, status="ok", data=data)
        except CollectorError as exc:
            return self.error_result(str(exc))

    async def collect_from(self, url: str) -> CollectorResult:
        """从指定 URL 采集（测试 query 参数泄露防护）。"""
        try:
            await self.fetch_json(url)
            return CollectorResult(module_id=self.module_id, status="ok")
        except CollectorError as exc:
            return self.error_result(str(exc))


def _make_client(handler) -> httpx.AsyncClient:
    """构造带 MockTransport 的客户端。"""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)


def _fast_config(config) -> None:
    """把重试间隔调小以加速测试。"""
    config.basic.retry_interval = 0.01
    config.basic.retry_count = 3


@pytest.mark.asyncio
async def test_success_first_try(config, mock_logger) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(200, json={"ok": True})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data == {"ok": True}
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_retry_on_500(config, mock_logger) -> None:
    """5xx 应重试到成功（配置重试 3 次）。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"ok": True})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_exhausted(config, mock_logger) -> None:
    """持续 5xx 重试耗尽后返回 error。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(500, json={"error": "oops"})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "error"
    assert calls["n"] == config.basic.retry_count


@pytest.mark.asyncio
async def test_404_no_retry(config, mock_logger) -> None:
    """4xx 不重试，直接失败。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(404, json={"error": "not found"})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "error"
    assert "404" in result.error_msg
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_connection_error_retries(config, mock_logger) -> None:
    """连接错误应重试。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"ok": True})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_timeout_retries(config, mock_logger) -> None:
    """超时错误应重试。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"ok": True})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    result = await collector.collect()
    assert result.status == "ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_url_key_not_leaked_in_error(config, mock_logger) -> None:
    """回归测试：query string 中的 key 不得出现在错误消息（防泄露）。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        calls["n"] += 1
        return httpx.Response(403, json={"error": "forbidden"})

    _fast_config(config)
    collector = _EchoCollector(config, mock_logger)
    collector._client = _make_client(handler)
    # 直接调用带 key 的 URL（模拟 game.py 的请求）
    result = await collector.collect_from("https://api.rawg.io/api/games?key=SECRET123&page_size=10")
    assert result.status == "error"
    assert "SECRET123" not in result.error_msg
    assert calls["n"] == 1  # 403 不重试


def test_safe_url_strips_query() -> None:
    collector = _EchoCollector(None, None)
    assert collector._safe_url("https://api.rawg.io/api/games?key=SECRET&x=1") == "https://api.rawg.io/api/games"
    assert "SECRET" not in collector._safe_url("https://api.rawg.io/api/games?key=SECRET&x=1")


def test_content_hash_stable() -> None:
    from DailyMorningReport.collectors.base import content_hash

    url = "https://lain.bgm.tv/pic/cover/l/1.jpg"
    assert content_hash(url) == content_hash(url)
    assert len(content_hash(url)) == 16
