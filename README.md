<div align="center">

# 📰 每日早报插件 v1.1.0

> 每天定时采集新闻、科技热点、行情财经、影视动漫等数据，渲染为精美长图推送至 QQ 群

[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![MaiBot Plugin](https://img.shields.io/badge/MaiBot-Plugin-green?style=for-the-badge&logo=python)](https://github.com/MaiM-with-u/MaiBot)
[![GitHub stars](https://img.shields.io/github/stars/Blackwindy2333/DailyMorningReport?style=for-the-badge&color=FF6B6B)](https://github.com/Blackwindy2333/DailyMorningReport/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Blackwindy2333/DailyMorningReport?style=for-the-badge&color=45B7D1)](https://github.com/Blackwindy2333/DailyMorningReport/issues)

</div>

---

## 📑 目录

- [✨ 特性一览](#-特性一览)
- [🔧 安装与配置](#-安装与配置)
- [📁 项目结构](#-项目结构)
- [📰 功能详解](#-功能详解)
- [🚀 快速上手](#-快速上手)
- [❓ 常见问题](#-常见问题)
- [📜 更新日志](#-更新日志)
- [🙏 鸣谢](#-鸣谢)

---

## ✨ 特性一览

✅ **每日定时推送** — 默认每天 08:00（可配置）自动生成早报，分 3 组长图推送到指定群

✅ **模块独立开关** — 12 项内容模块可分别开关，关闭的模块不采集、不渲染；组内全部关闭自动跳过整图（无分组开关，渲染与否执行时自动推导）

✅ **今日提醒** — 内置公历节日表 + 历史上的今天（出生/逝世/大事记）

✅ **昨日 AI 消费** — 昨日各模型调用次数与 Token 消耗汇总（基于本机统计能力）

✅ **电影双源** — 豆瓣主源，反爬失败时自动降级 TMDB

✅ **AI 额度私报** — OpenRouter / DeepSeek / Kimi / SiliconFlow 四家余额，默认仅私发管理员（支持多个管理员），也可配置公开进群

✅ **多地区油价** — 支持任意地区名（广东/上海/北京等），金价、汇率、DRAM 价格一应俱全

✅ **早报存档** — 每日数据自动存档到插件数据目录（保留最近 30 天）

✅ **手动触发** — 群内发送 `/morning_report`（别名 `/早报`）随时生成一次

✅ **失败隔离** — 单个数据源失败不影响其他模块，图片中以占位卡片明确指出失败模块

✅ **自动重试** — 网络错误/5xx 自动重试（默认 3 次，指数退避）

✅ **双通道日志** — SDK 插件日志 + 独立滚动文件日志，带 `[run=]` 前缀与分阶段耗时，便于按次排查

---

## 🔧 安装与配置

### 安装

在 MaiBot 插件管理器中搜索 `com.maibot.daily-morning-report` 安装，或手动克隆：

```bash
cd MaiBot/plugins
git clone https://github.com/Blackwindy2333/DailyMorningReport.git
```

启动 MaiBot 后插件自动安装依赖（httpx、beautifulsoup4），在 WebUI 插件管理中启用「每日早报」即可。

### 配置

在 MaiBot WebUI 插件设置页配置，关键项：

| 配置节 | 配置项 | 说明 | 默认值 |
|:-------|:-------|:-----|:-------|
| **基础设置** | `enabled` | 是否启用每日定时推送 | 开 |
| | `push_time` | 每日推送时间（HH:MM） | `08:00` |
| | `timezone` | 时区（IANA 名称） | `Asia/Shanghai` |
| | `target_groups` | 推送目标 QQ 群号列表（留空不推群） | `[]` |
| | `admin_qqs` | 管理员 QQ 号列表（AI 额度私聊目标，可多个） | `[]` |
| | `retry_count` / `retry_interval` | 失败重试次数 / 间隔秒数 | `3` / `5.0` |
| | `request_timeout` | 请求超时（秒） | `15.0` |
| **模块开关** | `holiday_enabled` / `news_enabled` / `tech_enabled` | 今日提醒 / 新闻速读 / 科技热点 | 开 |
| | `fx_enabled` / `fuel_enabled` / `gold_enabled` / `dram_enabled` | 汇率 / 油价 / 金价 / DRAM | 开 |
| | `ai_usage_enabled` | 昨日 AI 消费 | 开 |
| | `anime_enabled` / `movie_enabled` / `game_enabled` | 新番 / 电影 / 游戏 | 开 |
| | `ai_quota_enabled` | AI 额度（私聊/公开） | 开 |
| | `ai_quota_public` | AI 额度公开进群（开启后不再私发管理员） | 关 |
| **AI 额度** | `ai_quota.<provider>.enabled` / `.api_key` | 各厂商开关与 API Key（留空跳过该家） | 开 / 空 |
| **外部 API Key** | `exchangerate_api_key` | ExchangeRate-API Key（可留空，免费端点免 key） | 空 |
| | `rawg_api_key` | RAWG Key（游戏发售模块） | 空 |
| | `tmdb_api_key` | TMDB Key（豆瓣反爬时的电影降级源，可留空） | 空 |
| **渲染设置** | `card_width` / `device_scale_factor` | 图片宽度（px）/ 高清倍率 | `750` / `2.0` |
| | `covers_enabled` | 是否加载封面图 | 开 |
| | `news_count` / `tech_count` | 新闻 / 科技条数 | `10` / `15` |
| | `game_days` | 游戏发售前瞻天数 | `7` |
| | `fx_currencies` | 汇率展示币种列表 | `USD/EUR/JPY/HKD/GBP` |
| | `fuel_regions` | 油价展示地区列表（支持任意地区名） | `北京` |

> AI 额度四家厂商：`openrouter`、`deepseek`、`kimi`、`siliconflow`。

---

## 📁 项目结构

```
DailyMorningReport/
├── _manifest.json          # 插件清单（manifest v2）
├── plugin.py               # 主插件类（生命周期、采集→渲染→推送编排）
├── config_models.py        # 配置模型（6 个配置节）
├── scheduler.py            # 每日定时调度（时区感知）
├── pusher.py               # 推送器（群推送 + 管理员私聊推送）
├── archive.py              # 早报存档（保留 30 天自动清理）
├── log_config.py           # 双通道日志系统（滚动文件 handler）
├── collectors/             # 采集器（每模块一个，失败隔离）
│   ├── base.py             # 采集器基类（重试、URL 脱敏）
│   ├── news.py             # 新闻速读（60s-api）
│   ├── tech.py             # 科技热点（IT之家热榜）
│   ├── holiday.py          # 今日提醒（节日 + 历史上的今天）
│   ├── fx.py               # 汇率（open.er-api.com）
│   ├── fuel.py             # 油价（多地区）
│   ├── gold.py             # 金价
│   ├── dram.py             # DRAM 价格（dramx.com）
│   ├── ai_usage.py         # 昨日 AI 消费（token_trend 能力）
│   ├── ai_quota.py         # AI 额度（四家厂商）
│   ├── anime.py            # 新番（Bangumi）
│   ├── movie.py            # 电影（豆瓣 + TMDB 降级）
│   └── game.py             # 游戏发售（RAWG）
├── render/                 # 渲染模块（SDK html2png）
│   ├── templates.py        # 3 组 HTML 模板（禁用模块卡片跳过）
│   └── covers.py           # 封面下载（并发限流 + data URL 内嵌）
├── tests/                  # pytest 单元测试（94 个用例）
├── README.md
└── LICENSE
```

---

## 📰 功能详解

### 内容模块

| 模块 | 来源 | 备注 |
|:-----|:-----|:-----|
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

### 指令

| 指令 | 说明 |
|:-----|:-----|
| `/morning_report`（`/早报`） | 手动生成并推送一次早报（群聊/私聊均可用） |

### 权限与能力

- 使用能力：`send.image`（群/私聊发图）、`send.text`（命令文本响应）、`statistics.local.token_trend`（昨日 AI 消费）
- 渲染走 SDK `ctx.render.html2png`，不引入额外渲染依赖
- 所有 API Key 仅存于配置；URL 中的敏感参数（如 RAWG key）在错误消息/日志中自动剥离，Authorization 头中的 key 不入日志

---

## 🚀 快速上手

1. 将插件放入 MaiBot `plugins/` 目录并启用，填写推送目标群 `target_groups`。
2. 可选：填写 `admin_qqs` 接收 AI 额度私聊；填写 `rawg_api_key` 启用游戏模块。
3. 默认每天 08:00 自动推送；也可在群里发送 `/morning_report` 手动生成一次。
4. 推送内容为 3 张长图：资讯速览、行情财经、文娱生活。

---

## ❓ 常见问题

### Q1: 安装后插件未加载？

✅ 检查 `_manifest.json` 格式是否正确，确认 MaiBot 日志中无报错。重启 MaiBot 后插件应自动加载。

### Q2: 某模块显示失败占位卡片？

✅ 查看日志中该模块采集失败原因（日志带 `[run=时间戳]` 前缀，可按次检索）；重试次数不足可调大 `retry_count`。

### Q3: 某模块完全不出现？

✅ 检查模块开关（`modules.<module>_enabled`）是否误关；组内模块全部关闭时整图自动跳过。

### Q4: 游戏模块不显示？

✅ 检查 `rawg_api_key` 是否填写。

### Q5: 定时推送不触发？

✅ 检查 `enabled`、`push_time`、`target_groups` 配置。

### Q6: AI 额度不私发？

✅ 检查 `admin_qqs` 是否填写、至少一家厂商已填 key、`ai_quota_enabled` 未关闭。

### Q7: 昨日 AI 消费不显示？

✅ 需 MaiBot 已开启本机统计能力（manifest 已声明 `statistics.local.token_trend`）。

### Q8: 图片乱码/豆腐块？

✅ 部署环境缺少中文字体时，在系统中安装 Noto Sans CJK 或微软雅黑。

### Q9: 豆瓣抓取失败？

✅ 豆瓣可能加强反爬，属预期降级（自动切 TMDB；无 TMDB key 则占位卡片）。

---

## 📜 更新日志

<details>
<summary>点击展开版本历史</summary>

### 版本 1.1.0

**新功能**
- 管理员支持多个：`admin_qqs` 列表，AI 额度私聊图推送给所有管理员

**行为调整**
- 移除「分组开关」（`group1/2/3_enabled`）：组图片是否渲染在执行时按模块开关自动推导，组内模块全部关闭即跳过整图
- `ai_quota_public` 移入「模块开关」分组

**文档**
- README 改版，对齐社区主流插件格式（新增徽章、项目结构、更新日志等章节）

### 版本 1.0.0

**初始发布**
- 每日定时推送（默认 08:00，可配置时区/时间）
- 分 3 组长图：资讯速览 / 行情财经 / 文娱生活
- 12 项模块独立开关 + 失败隔离 + 自动重试（指数退避）
- 今日提醒（内置公历节日 + 历史上的今天）
- 昨日 AI 消费汇总（token_trend 统计能力）
- 电影双源（豆瓣 + TMDB 降级）、新番（Bangumi）、游戏发售（RAWG）
- 汇率 / 多地区油价 / 金价 / DRAM 价格
- AI 额度四家（OpenRouter/DeepSeek/Kimi/SiliconFlow），默认私发管理员
- 早报存档（保留 30 天自动清理）
- `/morning_report`（`/早报`）手动触发
- 双通道日志系统（SDK 插件日志 + 独立滚动文件日志）

</details>

---

## 许可证

MIT

## 鸣谢

- MaiBot 团队：[MaiM-with-u](https://github.com/MaiM-with-u/MaiBot)
- MaiBot Plugin SDK：[maibot-plugin-sdk](https://github.com/Mai-with-u/maibot-plugin-sdk)
- 数据来源：60s-api.viki.moe、IT之家、open.er-api.com、Bangumi、豆瓣、TMDB、RAWG、dramx.com

---

<div align="center">

**如果这个插件对你有帮助，请点亮 ⭐ 支持一下！**

[⬆ 返回顶部](#-每日早报插件-v110)

</div>
