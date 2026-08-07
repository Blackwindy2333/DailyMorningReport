"""每日早报插件配置模型。

所有敏感字段（API Key 等）默认空字符串，由用户在 WebUI / config.toml 中填写。
"""

from typing import List, Literal

from maibot_sdk import Field, PluginConfigBase


class PluginSection(PluginConfigBase):
    """插件基础配置（SDK 强制要求含 config_version）"""

    __ui_label__ = "插件信息"
    __ui_icon__ = "info"
    __ui_order__ = 0

    config_version: str = Field(default="1.4.1", description="配置版本")


class BasicSection(PluginConfigBase):
    """基础设置"""

    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"
    __ui_order__ = 1

    enabled: bool = Field(default=True, description="是否启用每日定时推送")
    push_time: str = Field(default="08:00", description="每日推送时间（HH:MM）")
    timezone: str = Field(default="Asia/Shanghai", description="时区（IANA 名称）")
    target_groups: List[str] = Field(
        default_factory=list,
        description="推送目标QQ群号列表（留空则不推送群消息）",
    )
    admin_qqs: List[str] = Field(
        default_factory=list,
        description="管理员QQ号列表（AI额度私聊目标，可多个）",
    )
    retry_count: int = Field(default=3, description="数据源失败重试次数")
    retry_interval: float = Field(default=5.0, description="重试间隔（秒）")
    request_timeout: float = Field(default=15.0, description="请求超时（秒）")
    admin_command_enabled: bool = Field(default=True, description="是否启用管理员 /dmr 配置命令")
    admin_command_prefix: str = Field(default="/dmr", description="管理员命令前缀（大小写不敏感，可更改）")


class AiQuotaSection(PluginConfigBase):
    """AI 额度（4 家厂商，key 非空即启用）"""

    __ui_label__ = "AI 额度"
    __ui_icon__ = "account_balance_wallet"
    __ui_order__ = 3

    openrouter: str = Field(
        default="",
        description="OpenRouter API Key（留空则跳过该厂商）。申请：https://openrouter.ai/settings/keys",
    )
    deepseek: str = Field(
        default="",
        description="DeepSeek API Key（留空则跳过该厂商）。申请：https://platform.deepseek.com/api_keys",
    )
    kimi: str = Field(
        default="",
        description="Kimi API Key（留空则跳过该厂商）。申请：https://platform.moonshot.cn/console/api-keys",
    )
    siliconflow: str = Field(
        default="",
        description="SiliconFlow API Key（留空则跳过该厂商）。申请：https://cloud.siliconflow.cn/account/ak",
    )


class ExternalApiSection(PluginConfigBase):
    """外部 API Key"""

    __ui_label__ = "外部 API Key"
    __ui_icon__ = "vpn_key"
    __ui_order__ = 4

    exchangerate_api_key: str = Field(
        default="",
        description="ExchangeRate-API Key（汇率，可留空，免费端点免 key）。申请：https://www.exchangerate-api.com/",
    )
    rawg_api_key: str = Field(
        default="",
        description="RAWG API Key（游戏发售模块）。申请：https://rawg.io/apidocs",
    )
    tmdb_api_key: str = Field(
        default="",
        description="TMDB API Key（豆瓣反爬时的电影降级源，可留空）。申请：https://www.themoviedb.org/settings/api",
    )


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
    game_source: Literal["auto", "rawg", "epic"] = Field(
        default="auto",
        description="游戏发售数据源：auto（自动降级，优先 epic 免 key）/ rawg（需 key，全平台）/ epic（免 key，国内直连）",
    )
    fx_currencies: List[str] = Field(
        default_factory=lambda: ["USD", "EUR", "JPY", "HKD", "GBP"],
        description="汇率展示币种列表（ISO 代码）",
    )
    fuel_regions: List[str] = Field(
        default_factory=lambda: ["北京"],
        description="油价展示地区列表（支持任意地区名，如 广东/上海）",
    )


class ModulesSection(PluginConfigBase):
    """模块开关（关闭的模块不采集、不渲染；组内全部关闭则整图跳过）"""

    __ui_label__ = "模块开关"
    __ui_icon__ = "toggle_on"
    __ui_order__ = 2

    holiday_enabled: bool = Field(default=True, description="今日提醒（节日/历史）")
    news_enabled: bool = Field(default=True, description="新闻速读")
    tech_enabled: bool = Field(default=True, description="科技热点")

    fx_enabled: bool = Field(default=True, description="实时汇率")
    fuel_enabled: bool = Field(default=True, description="油价")
    gold_enabled: bool = Field(default=True, description="金价")
    dram_enabled: bool = Field(default=True, description="DRAM 价格")
    ai_usage_enabled: bool = Field(default=True, description="昨日 AI 消费")

    anime_enabled: bool = Field(default=True, description="新番放送")
    movie_enabled: bool = Field(default=True, description="电影")
    game_enabled: bool = Field(default=True, description="游戏发售")

    ai_quota_enabled: bool = Field(default=True, description="AI 额度（私聊/公开）")
    ai_quota_public: bool = Field(default=False, description="AI 额度是否公开推送到群（默认仅私发管理员）")


class DailyMorningReportConfig(PluginConfigBase):
    """每日早报完整配置"""

    __ui_label__ = "每日早报"

    plugin: PluginSection = Field(default_factory=PluginSection)
    basic: BasicSection = Field(default_factory=BasicSection)
    modules: ModulesSection = Field(default_factory=ModulesSection)
    ai_quota: AiQuotaSection = Field(default_factory=AiQuotaSection)
    external_api: ExternalApiSection = Field(default_factory=ExternalApiSection)
    render: RenderSection = Field(default_factory=RenderSection)
