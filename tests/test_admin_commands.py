"""管理员 /dmr 命令测试：解析/转换/敏感拦截/鉴权/set/reset/status/help/push。"""

import logging

import pytest

from DailyMorningReport.admin_commands import (
    AdminCommandError,
    affects_scheduler,
    build_help_text,
    build_status_text,
    convert_value,
    get_nested,
    is_sensitive_key,
    parse_command,
    set_nested,
    strip_prefix,
)
from DailyMorningReport.config_models import DailyMorningReportConfig
from DailyMorningReport.plugin import DailyMorningReportPlugin


# ── 纯函数：前缀剥离 ──


def test_strip_prefix_case_insensitive() -> None:
    assert strip_prefix("/dmr status", "/dmr") == "status"
    assert strip_prefix("/DMR status", "/dmr") == "status"
    assert strip_prefix("/dmr", "/dmr") == ""
    assert strip_prefix(" /dmr help ", "/dmr") == "help"


def test_strip_prefix_boundary_and_mismatch() -> None:
    assert strip_prefix("/dmrxxx", "/dmr") is None  # 前缀后非空白不触发
    assert strip_prefix("/morning_report", "/dmr") is None
    assert strip_prefix("hello /dmr", "/dmr") is None
    assert strip_prefix("/dmr", "") is None  # 空前缀禁用


def test_parse_command() -> None:
    assert parse_command("SET basic.push_time 09:00") == ("set", ["basic.push_time", "09:00"])
    assert parse_command("status") == ("status", [])
    assert parse_command("") == ("", [])


# ── 纯函数：类型转换 ──


def test_convert_value() -> None:
    assert convert_value("true") is True
    assert convert_value("FALSE") is False
    assert convert_value("42") == 42
    assert convert_value("-3.5") == -3.5
    assert convert_value("USD,EUR") == ["USD", "EUR"]
    assert convert_value("北京，上海") == ["北京", "上海"]
    assert convert_value("09:00") == "09:00"
    assert convert_value("hello world") == "hello world"


def test_is_sensitive_key_and_scheduler() -> None:
    assert is_sensitive_key("ai_quota.openrouter.api_key")
    assert is_sensitive_key("ai_quota.deepseek")  # 平铺 key 也属敏感
    assert is_sensitive_key("external_api.tmdb_api_key")
    assert not is_sensitive_key("modules.ai_quota_enabled")  # 模块开关不受影响
    assert not is_sensitive_key("modules.ai_quota_public")
    assert not is_sensitive_key("basic.push_time")
    assert affects_scheduler("basic.push_time")
    assert affects_scheduler("basic.enabled")
    assert not affects_scheduler("modules.news_enabled")


def test_set_nested_and_get_nested() -> None:
    data = {"basic": {"push_time": "08:00"}}
    updated = set_nested(data, "basic.push_time", "09:00")
    assert updated["basic"]["push_time"] == "09:00"
    assert data["basic"]["push_time"] == "08:00"  # 原字典不变
    assert get_nested(updated, "basic.push_time") == "09:00"
    assert get_nested(updated, "basic.nope") is None


def test_set_nested_requires_dict_path() -> None:
    data = {"basic": "not-a-section"}
    with pytest.raises(AdminCommandError):
        set_nested(data, "basic.push_time", "09:00")


def test_status_masks_sensitive() -> None:
    config = DailyMorningReportConfig()
    config.ai_quota.openrouter = "sk-test"
    config.basic.admin_qqs = ["111", "222"]
    text = build_status_text(config.model_dump())
    assert "ai_quota.openrouter = ****" in text
    assert "sk-test" not in text
    assert "admin_qqs = 111、222" in text
    assert "config_version = 1.4.0" in text


def test_help_text_notes_runtime_only() -> None:
    text = build_help_text("/dmr")
    assert "仅运行时生效" in text
    assert "/dmr set" in text
    assert "/dmr push" in text


# ── 集成：过滤链与子命令执行 ──


class FakeCtx:
    def __init__(self) -> None:
        self.logger = logging.getLogger("admin_test")
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, text: str, stream_id: str) -> bool:
        self.sent.append((text, stream_id))
        return True


def test_admin_command_wired_as_observe_hook() -> None:
    """监听器注册为 chat.receive.after_process 的 OBSERVE Hook（Host 已停用消息事件分发）。"""
    from maibot_sdk.types import HookMode

    info = DailyMorningReportPlugin.on_admin_command_message.__maibot_component_info__
    assert info.hook == "chat.receive.after_process"
    assert info.name == "dmr_admin_commands"
    assert info.mode == HookMode.OBSERVE


def _make_plugin(**basic_overrides) -> DailyMorningReportPlugin:
    config = DailyMorningReportConfig()
    data = config.model_dump()
    data["basic"].update(basic_overrides)
    plugin = DailyMorningReportPlugin()
    ctx = FakeCtx()
    ctx.send = type("Send", (), {"text": ctx.send_text})()
    plugin._ctx = ctx
    plugin.set_plugin_config(data)
    return plugin


def _msg(text: str, user_id: str = "123456", group_id: str = "10001", platform: str = "qq") -> dict:
    return {
        "platform": platform,
        "session_id": f"s-{group_id}",
        "processed_plain_text": text,
        "message_info": {
            "user_info": {"user_id": user_id},
            "group_info": {"group_id": group_id} if group_id else None,
        },
        "raw_message": [],
    }


@pytest.mark.asyncio
async def test_set_updates_config_and_replies() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr set basic.push_time 09:00"))
    assert plugin.config.basic.push_time == "09:00"
    assert plugin.ctx.sent[-1][0] == "已设置 basic.push_time = 09:00（仅运行时生效，重启后恢复 WebUI 配置值）"


@pytest.mark.asyncio
async def test_set_list_value() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr set basic.admin_qqs 111,222"))
    assert plugin.config.basic.admin_qqs == ["111", "222"]


@pytest.mark.asyncio
async def test_set_restarts_scheduler_for_scheduler_keys() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    calls: list[int] = []

    async def fake_restart() -> None:
        calls.append(1)

    plugin._restart_scheduler = fake_restart
    await plugin._dispatch_admin_command(_msg("/dmr set basic.enabled false"))
    assert calls == [1]
    assert plugin.config.basic.enabled is False


@pytest.mark.asyncio
async def test_set_non_scheduler_key_no_restart() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    calls: list[int] = []

    async def fake_restart() -> None:
        calls.append(1)

    plugin._restart_scheduler = fake_restart
    await plugin._dispatch_admin_command(_msg("/dmr set modules.news_enabled false"))
    assert calls == []
    assert plugin.config.modules.news_enabled is False


@pytest.mark.asyncio
async def test_set_rejects_sensitive_key() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr set external_api.rawg_api_key abc"))
    assert "敏感信息" in plugin.ctx.sent[-1][0]
    assert plugin.config.external_api.rawg_api_key == ""


@pytest.mark.asyncio
async def test_set_rejects_ai_quota_key() -> None:
    """平铺 AI 额度 key 也不允许通过命令修改。"""
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr set ai_quota.deepseek sk-test"))
    assert "敏感信息" in plugin.ctx.sent[-1][0]
    assert plugin.config.ai_quota.deepseek == ""


@pytest.mark.asyncio
async def test_set_rejects_invalid_value() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr set basic.enabled not-a-bool"))
    assert "配置值无效" in plugin.ctx.sent[-1][0]
    assert plugin.config.basic.enabled is True


@pytest.mark.asyncio
async def test_reset_restores_default() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"], push_time="09:00")
    await plugin._dispatch_admin_command(_msg("/dmr reset basic.push_time"))
    assert plugin.config.basic.push_time == "08:00"


@pytest.mark.asyncio
async def test_reset_unknown_key() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr reset basic.nope"))
    assert "未知配置键" in plugin.ctx.sent[-1][0]


@pytest.mark.asyncio
async def test_status_replies_with_masked_config() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr status"))
    reply = plugin.ctx.sent[-1][0]
    assert "【早报当前配置】" in reply
    assert "admin_qqs = 123456" in reply
    assert "****" in reply  # api_key 类字段已脱敏


@pytest.mark.asyncio
async def test_push_executes() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    calls: list[int] = []

    async def fake_execute() -> None:
        calls.append(1)

    plugin._execute = fake_execute
    await plugin._dispatch_admin_command(_msg("/dmr push"))
    assert calls == [1]
    assert plugin.ctx.sent[-1][0] == "日报已生成并推送"


@pytest.mark.asyncio
async def test_help_subcommand() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr"))
    assert "早报管理命令" in plugin.ctx.sent[-1][0]


@pytest.mark.asyncio
async def test_unknown_subcommand() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr frobnicate"))
    assert "未知子命令" in plugin.ctx.sent[-1][0]


# ── 集成：鉴权与过滤链 ──


@pytest.mark.asyncio
async def test_non_admin_receives_no_permission() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr status", user_id="999999"))
    assert plugin.ctx.sent[-1][0] == "无权限执行早报管理命令"


@pytest.mark.asyncio
async def test_outside_group_receives_no_permission() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr status", group_id="20002"))
    assert plugin.ctx.sent[-1][0] == "无权限执行早报管理命令"


@pytest.mark.asyncio
async def test_private_message_from_admin_no_permission() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr status", group_id=""))
    assert plugin.ctx.sent[-1][0] == "无权限执行早报管理命令"


@pytest.mark.asyncio
async def test_ignored_when_disabled() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"], admin_command_enabled=False)
    await plugin._dispatch_admin_command(_msg("/dmr status"))
    assert plugin.ctx.sent == []


@pytest.mark.asyncio
async def test_ignored_for_non_qq_and_other_prefix() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    await plugin._dispatch_admin_command(_msg("/dmr status", platform="wx"))
    await plugin._dispatch_admin_command(_msg("/morning_report"))
    assert plugin.ctx.sent == []


@pytest.mark.asyncio
async def test_raw_message_fallback_text() -> None:
    plugin = _make_plugin(admin_qqs=["123456"], target_groups=["10001"])
    message = _msg("", user_id="123456", group_id="10001")
    message["processed_plain_text"] = ""
    message["raw_message"] = [{"type": "text", "data": {"text": "/dmr set basic.push_time 07:00"}}]
    await plugin._dispatch_admin_command(message)
    assert plugin.config.basic.push_time == "07:00"
