"""每日早报插件配置模型。

所有敏感字段（API Key 等）默认空字符串，由用户在 WebUI / config.toml 中填写。
"""

from maibot_sdk import Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    """插件基础配置（SDK 强制要求含 config_version）"""

    __ui_label__ = "插件信息"
    __ui_icon__ = "info"
    __ui_order__ = 0

    config_version: str = Field(default="1.0.0", description="配置版本")


class BasicSection(PluginConfigBase):
    """基础设置"""

    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"
    __ui_order__ = 1

    enabled: bool = Field(default=True, description="是否启用每日定时推送")
    push_time: str = Field(default="08:00", description="每日推送时间（HH:MM）")
    timezone: str = Field(default="Asia/Shanghai", description="时区（IANA 名称）")
    target_groups: list = Field(
        default_factory=list,
        description="推送目标QQ群号列表（留空则不推送群消息）",
    )
    admin_qq: str = Field(default="", description="管理员QQ号（AI额度私聊目标）")
    retry_count: int = Field(default=3, description="数据源失败重试次数")
    retry_interval: float = Field(default=5.0, description="重试间隔（秒）")
    request_timeout: float = Field(default=15.0, description="请求超时（秒）")


class GroupSection(PluginConfigBase):
    """分组开关"""

    __ui_label__ = "分组开关"
    __ui_icon__ = "view_agenda"
    __ui_order__ = 2

    group1_enabled: bool = Field(default=True, description="资讯速览（新闻+科技）")
    group2_enabled: bool = Field(default=True, description="行情财经（汇率+油价+金价+DRAM）")
    group3_enabled: bool = Field(default=True, description="文娱生活（新番+电影+游戏）")
    ai_quota_public: bool = Field(default=False, description="AI额度是否公开推送到群（默认仅私发管理员）")


class AiProviderSection(PluginConfigBase):
    """单个 AI 厂商额度配置"""

    enabled: bool = Field(default=True, description="是否启用该厂商额度查询")
    api_key: str = Field(default="", description="API Key（留空则跳过该厂商）")


class AiQuotaSection(PluginConfigBase):
    """AI 额度（4 家厂商）"""

    __ui_label__ = "AI 额度"
    __ui_icon__ = "account_balance_wallet"
    __ui_order__ = 3

    openrouter: AiProviderSection = Field(default_factory=AiProviderSection)
    deepseek: AiProviderSection = Field(default_factory=AiProviderSection)
    kimi: AiProviderSection = Field(default_factory=AiProviderSection)
    siliconflow: AiProviderSection = Field(default_factory=AiProviderSection)


class ExternalApiSection(PluginConfigBase):
    """外部 API Key"""

    __ui_label__ = "外部 API Key"
    __ui_icon__ = "vpn_key"
    __ui_order__ = 4

    exchangerate_api_key: str = Field(default="", description="ExchangeRate-API Key（可留空，免费端点免 key）")
    rawg_api_key: str = Field(default="", description="RAWG API Key（游戏发售模块）")


class RenderSection(PluginConfigBase):
    """渲染与内容量"""

    __ui_label__ = "渲染设置"
    __ui_icon__ = "image"
    __ui_order__ = 5

    card_width: int = Field(default=750, description="图片宽度（px）")
    device_scale_factor: float = Field(default=2.0, description="高清倍率")
    covers_enabled: bool = Field(default=True, description="是否加载封面图")
    news_count: int = Field(default=10, description="新闻条数")
    tech_count: int = Field(default=15, description="科技热榜条数")
    game_days: int = Field(default=7, description="游戏发售前瞻天数")
    fx_currencies: list = Field(
        default_factory=lambda: ["USD", "EUR", "JPY", "HKD", "GBP"],
        description="汇率展示币种列表（ISO 代码）",
    )


class DailyMorningReportConfig(PluginConfigBase):
    """每日早报完整配置"""

    __ui_label__ = "每日早报"

    plugin: PluginSection = Field(default_factory=PluginSection)
    basic: BasicSection = Field(default_factory=BasicSection)
    groups: GroupSection = Field(default_factory=GroupSection)
    ai_quota: AiQuotaSection = Field(default_factory=AiQuotaSection)
    external_api: ExternalApiSection = Field(default_factory=ExternalApiSection)
    render: RenderSection = Field(default_factory=RenderSection)
