"""模块开关测试：关闭项不采集、不渲染；组内全关则整图跳过。"""

import asyncio

import pytest

from DailyMorningReport.collectors.base import CollectorResult
from DailyMorningReport.config_models import DailyMorningReportConfig
from DailyMorningReport.plugin import (
    _GROUP1_MODULES,
    _GROUP2_MODULES,
    _GROUP3_MODULES,
    _MODULE_SWITCH_FIELD,
    DailyMorningReportPlugin,
)


def test_all_switches_default_on(config) -> None:
    """默认全部模块开关为开。"""
    for module_id, field in _MODULE_SWITCH_FIELD.items():
        assert getattr(config.modules, field) is True, f"{module_id} 默认应开启"


def test_switch_field_mapping_complete() -> None:
    """模块归属与开关字段映射完整覆盖所有采集器。"""
    from DailyMorningReport.collectors import COLLECTORS

    registered = set(COLLECTORS.keys())
    mapped = set(_MODULE_SWITCH_FIELD.keys())
    assert registered == mapped  # 每个采集器都有开关，无多余映射


def test_build_collectors_filters_disabled(config, mock_logger) -> None:
    """关闭某模块后，采集器列表中不含该模块（不发起请求）。"""
    config.modules.news_enabled = False
    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    plugin._ctx = type("Ctx", (), {"logger": mock_logger})()

    collectors = plugin._build_collectors()
    module_ids = [c.module_id for c in collectors]
    assert "news" not in module_ids
    assert "tech" in module_ids  # 其余不受影响


def test_build_collectors_all_default(config, mock_logger) -> None:
    """默认全开时所有采集器都在。"""
    from DailyMorningReport.collectors import COLLECTORS

    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    plugin._ctx = type("Ctx", (), {"logger": mock_logger})()
    collectors = plugin._build_collectors()
    assert {c.module_id for c in collectors} == set(COLLECTORS.keys())


def test_module_enabled_helper(config) -> None:
    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    assert plugin._module_enabled("news") is True
    config.modules.game_enabled = False
    assert plugin._module_enabled("game") is False
    assert plugin._module_enabled("unknown_module") is True  # 未映射默认启用


def test_enabled_group_modules(config) -> None:
    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    config.modules.news_enabled = False
    config.modules.tech_enabled = False
    enabled = plugin._enabled_group_modules(_GROUP1_MODULES)
    assert enabled == {"holiday"}  # 只有 holiday 仍启用
    # 全关
    config.modules.holiday_enabled = False
    assert plugin._enabled_group_modules(_GROUP1_MODULES) == set()


class FakeCtxRender:
    def __init__(self) -> None:
        self.calls = []

    async def html2png(self, html: str, **kwargs):
        del html, kwargs
        self.calls.append(1)
        return {"image_base64": "REF", "mime_type": "image/png", "width": 750, "height": 100}


def _make_plugin_with_render(config) -> DailyMorningReportPlugin:
    plugin = DailyMorningReportPlugin()
    plugin._plugin_config_instance = config
    ctx = type("Ctx", (), {"logger": __import__("logging").getLogger("t"), "render": FakeCtxRender()})()
    plugin._ctx = ctx
    return plugin


def _ok(module_id: str) -> CollectorResult:
    data = {
        "news": {"news": ["n"], "tip": ""},
        "tech": {"titles": ["t"]},
        "holiday": {"holidays": [], "history": []},
        "fx": {"rates": []},
        "fuel": {"regions": [], "trend": {}},
        "gold": {"metals": []},
        "dram": {"items": []},
        "ai_usage": {"date": "", "models": [], "totals": {}},
        "anime": {"animes": []},
        "movie": {"movies": []},
        "game": {"games": []},
        "ai_quota": {"quotas": []},
    }
    return CollectorResult(module_id=module_id, status="ok", data=data.get(module_id, {}))


def _all_results() -> dict[str, CollectorResult]:
    return {mid: _ok(mid) for mid in _MODULE_SWITCH_FIELD}


@pytest.mark.asyncio
async def test_group_skipped_when_all_disabled() -> None:
    """组内所有模块禁用 → 该组整图不渲染。"""
    config = DailyMorningReportConfig()
    config.modules.anime_enabled = False
    config.modules.movie_enabled = False
    config.modules.game_enabled = False
    plugin = _make_plugin_with_render(config)

    images = await plugin._render(_all_results())
    # 组 3 全禁用：只渲染组 1 和组 2（2 张群图）
    assert len(images["groups"]) == 2
    assert len(plugin._ctx.render.calls) == 2


@pytest.mark.asyncio
async def test_partial_group_disabled_renders_remaining() -> None:
    """组内部分禁用：渲染剩余模块的卡片，但整图仍渲染。"""
    config = DailyMorningReportConfig()
    config.modules.news_enabled = False  # 组 1 只有 news 禁用
    plugin = _make_plugin_with_render(config)
    images = await plugin._render(_all_results())
    assert len(images["groups"]) == 3  # 组 1 仍有 tech+holiday，整图保留
    assert len(plugin._ctx.render.calls) == 3


@pytest.mark.asyncio
async def test_ai_quota_private_skipped_when_disabled() -> None:
    """ai_quota 禁用 → 私聊图不渲染。"""
    config = DailyMorningReportConfig()
    config.basic.admin_qq = "123456"
    config.ai_quota.openrouter.api_key = "sk-test"
    config.modules.ai_quota_enabled = False
    plugin = _make_plugin_with_render(config)
    images = await plugin._render(_all_results())
    assert images["private"] == []


@pytest.mark.asyncio
async def test_ai_quota_private_rendered_when_enabled() -> None:
    """ai_quota 启用且配置 key → 私聊图渲染。"""
    config = DailyMorningReportConfig()
    config.basic.admin_qq = "123456"
    config.ai_quota.openrouter.api_key = "sk-test"
    plugin = _make_plugin_with_render(config)
    images = await plugin._render(_all_results())
    assert len(images["private"]) == 1


@pytest.mark.asyncio
async def test_ai_quota_public_requires_switch() -> None:
    """ai_quota_public=true 但 ai_quota 模块禁用 → 组 2 不含额度卡。"""
    config = DailyMorningReportConfig()
    config.groups.ai_quota_public = True
    config.modules.ai_quota_enabled = False
    plugin = _make_plugin_with_render(config)
    images = await plugin._render(_all_results())
    assert len(images["groups"]) == 3  # 组 2 仍有 fx/fuel/gold/dram/ai_usage
    assert len(plugin._ctx.render.calls) == 3


def test_group_mapping_consistency() -> None:
    """三组模块集合互不重叠且覆盖全部映射。"""
    all_group_modules = set(_GROUP1_MODULES) | set(_GROUP2_MODULES) | set(_GROUP3_MODULES)
    assert all_group_modules == set(_MODULE_SWITCH_FIELD) - {"ai_quota"}
    assert len(_GROUP1_MODULES) + len(_GROUP2_MODULES) + len(_GROUP3_MODULES) == len(all_group_modules)
