"""配置模型测试：默认值、嵌套结构、空 key 行为。"""

from DailyMorningReport.config_models import DailyMorningReportConfig


def test_default_values(config: DailyMorningReportConfig) -> None:
    assert config.plugin.config_version == "1.1.0"
    assert config.basic.enabled is True
    assert config.basic.push_time == "08:00"
    assert config.basic.timezone == "Asia/Shanghai"
    assert config.basic.target_groups == []
    assert config.basic.admin_qqs == []
    assert config.basic.retry_count == 3
    assert config.basic.retry_interval == 5.0
    assert config.basic.request_timeout == 15.0


def test_modules_defaults(config: DailyMorningReportConfig) -> None:
    """模块开关默认全开；ai_quota_public 默认私有；已无分组开关。"""
    assert config.modules.ai_quota_public is False
    for field in (
        "holiday_enabled",
        "news_enabled",
        "tech_enabled",
        "fx_enabled",
        "fuel_enabled",
        "gold_enabled",
        "dram_enabled",
        "ai_usage_enabled",
        "anime_enabled",
        "movie_enabled",
        "game_enabled",
        "ai_quota_enabled",
    ):
        assert getattr(config.modules, field) is True
    assert not hasattr(config, "groups")


def test_ai_quota_nested_defaults(config: DailyMorningReportConfig) -> None:
    for section in (
        config.ai_quota.openrouter,
        config.ai_quota.deepseek,
        config.ai_quota.kimi,
        config.ai_quota.siliconflow,
    ):
        assert section.enabled is True
        assert section.api_key == ""


def test_external_api_empty_keys(config: DailyMorningReportConfig) -> None:
    assert config.external_api.exchangerate_api_key == ""
    assert config.external_api.rawg_api_key == ""


def test_render_defaults(config: DailyMorningReportConfig) -> None:
    assert config.render.card_width == 750
    assert config.render.news_count == 10
    assert config.render.tech_count == 15
    assert config.render.game_days == 7
    assert config.render.fx_currencies == ["USD", "EUR", "JPY", "HKD", "GBP"]


def test_custom_values_override() -> None:
    cfg = DailyMorningReportConfig()
    cfg.basic.push_time = "09:30"
    cfg.basic.target_groups = ["10001", "10002"]
    cfg.basic.admin_qqs = ["111", "222"]
    cfg.ai_quota.deepseek.api_key = "sk-test"
    assert cfg.basic.push_time == "09:30"
    assert cfg.basic.target_groups == ["10001", "10002"]
    assert cfg.basic.admin_qqs == ["111", "222"]
    assert cfg.ai_quota.deepseek.api_key == "sk-test"
