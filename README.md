# 每日早报（DailyMorningReport）

MaiBot 第三方插件：每天定时采集新闻、科技热点、硬件价格、汇率、AI 额度、油价金价、影视动漫、游戏发售等多维数据，渲染为精美图片推送至 QQ 群。

## 功能

- **每日定时推送**：默认每天 08:00（可配置）自动生成早报并推送到指定群
- **分 3 组推送**：资讯速览（今日提醒+新闻+科技）、行情财经（汇率+油价+金价+DRAM+昨日 AI 消费）、文娱生活（新番+电影+游戏），每组一张长图
- **今日提醒**：节假日（内置公历节日表）与历史上的今天
- **昨日 AI 消费**：昨日各模型调用次数与 Token 消耗汇总（基于本机统计）
- **电影双源**：豆瓣主源，反爬失败时自动降级到 TMDB
- **AI 额度私报**：OpenRouter / DeepSeek / Kimi / SiliconFlow 四家余额，默认仅私发管理员；也可配置公开进群
- **早报存档**：每日数据自动存档到插件数据目录（保留最近 30 天，可配置）
- **手动触发**：群内发送 `/morning_report`（别名 `/早报`）随时生成一次
- **失败隔离**：单个数据源失败不影响其他模块，图片中以占位卡片明确指出失败模块
- **自动重试**：网络错误/5xx 自动重试（默认 3 次，指数退避）

## 安装

1. 将本插件目录放入 MaiBot 的 `plugins/` 下（作为独立仓库，不改动主程序）
2. 启动 MaiBot，插件自动安装依赖（httpx、beautifulsoup4）
3. 在 WebUI 插件管理中启用「每日早报」

## 配置项

在 WebUI 插件配置页（或 `config.toml`）中填写：

### 基础设置
| 字段 | 说明 | 默认值 |
|---|---|---|
| `enabled` | 是否启用每日定时推送 | `true` |
| `push_time` | 每日推送时间（HH:MM） | `08:00` |
| `timezone` | 时区（IANA 名称） | `Asia/Shanghai` |
| `target_groups` | 推送目标 QQ 群号列表（留空不推群） | `[]` |
| `admin_qq` | 管理员 QQ（AI 额度私聊目标） | 空 |
| `retry_count` / `retry_interval` | 失败重试次数 / 间隔秒数 | `3` / `5.0` |
| `request_timeout` | 请求超时（秒） | `15.0` |

### 分组开关
| 字段 | 说明 | 默认值 |
|---|---|---|
| `group1_enabled` / `group2_enabled` / `group3_enabled` | 三组开关 | `true` |
| `ai_quota_public` | AI 额度是否公开推送到群（开启后不再私发） | `false` |

### AI 额度（每家独立）
| 字段 | 说明 |
|---|---|
| `ai_quota.<provider>.enabled` | 是否启用该厂商查询 |
| `ai_quota.<provider>.api_key` | API Key（留空跳过该家） |

四家：`openrouter`、`deepseek`、`kimi`、`siliconflow`。

### 外部 API Key
| 字段 | 说明 |
|---|---|
| `exchangerate_api_key` | ExchangeRate-API Key（可留空，免费端点免 key） |
| `rawg_api_key` | RAWG Key（游戏发售模块，留空则该模块跳过） |
| `tmdb_api_key` | TMDB Key（豆瓣反爬时的电影降级源，留空则仅用豆瓣） |

### 渲染设置
| 字段 | 说明 | 默认值 |
|---|---|---|
| `card_width` / `device_scale_factor` | 图片宽度（px）/ 高清倍率 | `750` / `2.0` |
| `covers_enabled` | 是否加载封面图 | `true` |
| `news_count` / `tech_count` | 新闻 / 科技条数 | `10` / `15` |
| `game_days` | 游戏发售前瞻天数 | `7` |
| `fx_currencies` | 汇率展示币种列表 | `USD/EUR/JPY/HKD/GBP` |
| `fuel_regions` | 油价展示地区列表（支持任意地区名） | `北京` |

## 命令

| 命令 | 说明 |
|---|---|
| `/morning_report`（`/早报`） | 手动生成并推送一次早报（群聊/私聊均可用） |

## 数据源

| 模块 | 来源 | 备注 |
|---|---|---|
| 今日提醒 | 60s-api.viki.moe + 内置节日表 | 免费 |
| 新闻速读 | 60s-api.viki.moe | 免费 |
| 科技热点 | IT之家热榜 | 网页抓取 |
| 汇率 | open.er-api.com | 免费免 key |
| 油价 / 金价 | 60s-api.viki.moe | 免费；油价支持多地区 |
| DRAM 价格 | dramx.com | 网页抓取 |
| 昨日 AI 消费 | MaiBot 本机统计 | 需统计能力 |
| 新番 | api.bgm.tv/calendar | 官方 API |
| 电影 | movie.douban.com → api.themoviedb.org | 豆瓣反爬时自动降级 TMDB |
| 游戏 | api.rawg.io | 需 key |
| AI 额度 | 四家官方 API | 需 key |

## 权限与能力

- 使用能力：`send.image`（群/私聊发图）、`send.text`（命令文本响应）、`statistics.local.token_trend`（昨日 AI 消费）
- 渲染走 SDK `ctx.render.html2png`，不引入额外渲染依赖
- 所有 API Key 仅存于配置，日志自动脱敏（`key[:4] + "****"`）

## 故障排查

| 现象 | 处理 |
|---|---|
| 某模块显示失败占位卡片 | 查看日志中该模块采集失败原因；重试次数不足可调大 `retry_count` |
| 游戏模块不显示 | 检查 `rawg_api_key` 是否填写 |
| 定时推送不触发 | 检查 `enabled`、`push_time`、`target_groups` 配置 |
| AI 额度不私发 | 检查 `admin_qq` 是否填写、至少一家厂商已填 key |
| 昨日 AI 消费不显示 | 需 MaiBot 已开启本机统计能力（manifest 已声明 `statistics.local.token_trend`） |
| 油价地区不生效 | 检查 `fuel_regions` 填写的地区名是否与油价站点一致（如 广东/上海/北京） |
| 电影显示（TMDB） | 豆瓣被反爬时自动降级 TMDB，需配置 `tmdb_api_key` 否则该模块失败占位 |
| 图片乱码/豆腐块 | 部署环境缺少中文字体时，在系统中安装 Noto Sans CJK 或微软雅黑 |
| 豆瓣抓取失败 | 豆瓣可能加强反爬，属预期降级（自动切 TMDB；无 TMDB key 则占位卡片） |

## 开发

```bash
# 单元测试（需在插件根目录）
python -m pytest tests/
```

## 许可

MIT
