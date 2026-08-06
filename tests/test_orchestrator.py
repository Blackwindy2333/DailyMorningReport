"""插件编排测试：用 mock ctx 验证采集→渲染→推送链路与失败隔离。"""

import asyncio
import logging
from pathlib import Path

import pytest

from DailyMorningReport.collectors.base import CollectorResult
from DailyMorningReport.config_models import DailyMorningReportConfig
from DailyMorningReport.plugin import DailyMorningReportPlugin


class FakePaths:
    data_dir = Path(".")
    runtime_dir = Path(".")


class FakeRender:
    def __init__(self) -> None:
        self.calls = []

    async def html2png(self, html: str, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {"image_base64": "REFL", "mime_type": "image/png", "width": 750, "height": 100}


class FakeChat:
    async def get_stream_by_group_id(self, group_id: str, platform: str = "qq"):
        del platform
        return type("S", (), {"session_id": f"group-{group_id}"})()

    async def get_stream_by_user_id(self, user_id: str, platform: str = "qq"):
        del platform
        return type("S", (), {"session_id": f"user-{user_id}"})()


class FakeCtx:
    def __init__(self) -> None:
        self.logger = logging.getLogger("fake")
        self.paths = FakePaths()
        self.render = FakeRender()
        self.chat = FakeChat()
        self.sent_images = []
        self.sent_texts = []

    async def send_image(self, image_base64: str, stream_id: str) -> bool:
        self.sent_images.append((image_base64, stream_id))
        return True


async def _make_plugin(config) -> DailyMorningReportPlugin:
    from DailyMorningReport.archive import ArchiveManager
    from DailyMorningReport.pusher import Pusher

    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    ctx = FakeCtx()
    ctx.send = type(
        "Send",
        (),
        {
            "image": ctx.send_image,
            "text": lambda text, stream_id: ctx.sent_texts.append((text, stream_id)) or True,
        },
    )()
    plugin._ctx = ctx
    plugin._pusher = Pusher(ctx, ctx.logger)
    plugin._archive = ArchiveManager(Path("."), ctx.logger)
    return plugin


def _ok(module_id: str, data: dict) -> CollectorResult:
    return CollectorResult(module_id=module_id, status="ok", data=data)


def _err(module_id: str) -> CollectorResult:
    return CollectorResult(module_id=module_id, status="error", error_msg="测试失败")


@pytest.mark.asyncio
async def test_orchestrator_collect_failure_isolated() -> None:
    """单个采集器失败不影响其他模块与整体推送。"""
    config = DailyMorningReportConfig()
    config.basic.target_groups = ["10001"]
    config.basic.admin_qqs = ["123456"]
    config.ai_quota.openrouter.api_key = "sk-or-1"
    plugin = await _make_plugin(config)

    # 用固定结果替换真实采集：news ok，其余 error（模拟大部分失败）
    async def fake_collect(self) -> CollectorResult:
        del self
        return CollectorResult(module_id="", status="error", error_msg="网络不可用")

    plugin._build_collectors = lambda: []  # 不用真实采集器
    # 直接走渲染链路：构造全部失败的结果集
    results = {
        "news": _ok("news", {"news": ["n1"], "tip": "t"}),
        "tech": _err("tech"),
        "dram": _err("dram"),
        "fx": _err("fx"),
        "fuel": _err("fuel"),
        "gold": _err("gold"),
        "anime": _err("anime"),
        "movie": _err("movie"),
        "game": _err("game"),
    }
    images = await plugin._render(results)
    assert len(images["groups"]) == 3  # 三组照常渲染（含失败占位卡片）
    assert len(images["private"]) == 0  # ai_quota 失败不私发


@pytest.mark.asyncio
async def test_orchestrator_ai_quota_private_and_public() -> None:
    """ai_quota：默认私发管理员；ai_quota_public=true 时并入群图。"""
    config = DailyMorningReportConfig()
    config.basic.target_groups = ["10001"]
    config.basic.admin_qqs = ["123456"]
    config.ai_quota.openrouter.api_key = "sk-or-1"
    plugin = await _make_plugin(config)

    results = {
        "news": _ok("news", {"news": ["n1"], "tip": ""}),
        "tech": _ok("tech", {"titles": ["t1"]}),
        "fx": _ok("fx", {"rates": [{"code": "USD", "rate": 0.1}]}),
        "fuel": _ok("fuel", {"regions": [{"region": "北京", "items": []}], "trend": {}}),
        "gold": _ok("gold", {"metals": []}),
        "dram": _ok("dram", {"items": []}),
        "anime": _ok("anime", {"animes": []}),
        "movie": _ok("movie", {"movies": []}),
        "game": _ok("game", {"games": []}),
        "ai_quota": _ok(
            "ai_quota", {"quotas": [{"provider": "OpenRouter", "balance": 3.7, "currency": "USD", "note": ""}]}
        ),
    }
    images = await plugin._render(results)
    assert len(images["groups"]) == 3
    assert len(images["private"]) == 1  # 私发管理员

    # public=true 时并入组 2
    config.modules.ai_quota_public = True
    images2 = await plugin._render(results)
    assert len(images2["groups"]) == 3
    assert len(images2["private"]) == 0  # 已公开，不再私发


@pytest.mark.asyncio
async def test_full_execute_pushes_to_groups() -> None:
    """完整 _execute 链路：渲染 3 组图并推送到目标群。"""
    config = DailyMorningReportConfig()
    config.basic.target_groups = ["10001", "10002"]
    config.basic.admin_qqs = []
    plugin = await _make_plugin(config)
    plugin._collectors = []

    # 全部采集器返回 ok（最小数据）
    async def fake_collect(self) -> CollectorResult:
        module_id = self.module_id
        data_map = {
            "news": {"news": ["n"], "tip": ""},
            "tech": {"titles": ["t"]},
            "fx": {"rates": []},
            "fuel": {"regions": [{"region": "北京", "items": []}], "trend": {}},
            "gold": {"metals": []},
            "dram": {"items": []},
            "anime": {"animes": []},
            "movie": {"movies": []},
            "game": {"games": []},
        }
        return CollectorResult(module_id=module_id, status="ok", data=data_map.get(module_id, {}))

    class FakeCollector:
        module_id = ""

        async def collect(self):  # noqa: D102
            return await fake_collect(self)

        async def close(self):  # noqa: D102
            pass

    plugin._build_collectors = lambda: [
        type("C", (FakeCollector,), {"module_id": mid})()
        for mid in ("news", "tech", "fx", "fuel", "gold", "dram", "anime", "movie", "game")
    ]
    plugin._running_lock = asyncio.Lock()

    await plugin._execute()

    # 两个群各收到 3 张图 = 6 次发送
    assert len(plugin.ctx.sent_images) == 6
    sent_streams = {stream_id for _, stream_id in plugin.ctx.sent_images}
    assert sent_streams == {"group-10001", "group-10002"}


@pytest.mark.asyncio
async def test_full_execute_private_to_multiple_admins() -> None:
    """多管理员：每张私聊图推送给 admin_qqs 中每个 QQ。"""
    config = DailyMorningReportConfig()
    config.basic.target_groups = []
    config.basic.admin_qqs = ["111", "222"]
    config.ai_quota.openrouter.api_key = "sk-or-1"
    plugin = await _make_plugin(config)
    plugin._collectors = []

    async def fake_collect(self) -> CollectorResult:
        module_id = self.module_id
        data_map = {
            "news": {"news": ["n"], "tip": ""},
            "tech": {"titles": ["t"]},
            "fx": {"rates": []},
            "fuel": {"regions": [{"region": "北京", "items": []}], "trend": {}},
            "gold": {"metals": []},
            "dram": {"items": []},
            "anime": {"animes": []},
            "movie": {"movies": []},
            "game": {"games": []},
            "ai_quota": {"quotas": [{"provider": "OpenRouter", "balance": 3.7, "currency": "USD", "note": ""}]},
        }
        return CollectorResult(module_id=module_id, status="ok", data=data_map.get(module_id, {}))

    class FakeCollector:
        module_id = ""

        async def collect(self):  # noqa: D102
            return await fake_collect(self)

        async def close(self):  # noqa: D102
            pass

    plugin._build_collectors = lambda: [
        type("C", (FakeCollector,), {"module_id": mid})()
        for mid in ("news", "tech", "fx", "fuel", "gold", "dram", "anime", "movie", "game", "ai_quota")
    ]
    plugin._running_lock = asyncio.Lock()

    await plugin._execute()

    # 1 张私聊图 × 2 个管理员 = 2 次私聊发送
    private_streams = {stream_id for _, stream_id in plugin.ctx.sent_images if stream_id.startswith("user-")}
    assert private_streams == {"user-111", "user-222"}
    assert len(plugin.ctx.sent_images) == 2
