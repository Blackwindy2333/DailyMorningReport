<div align="center">

# 📰 每日早报插件 v1.4.1

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

✅ **管理员命令** — 目标群内管理员可用 `/dmr` 前缀命令查看/修改配置（仅运行时生效）、立即推送早报

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
| | `admin_command_enabled` | 是否启用管理员 `/dmr` 配置命令 | 开 |
| | `admin_command_prefix` | 管理员命令前缀（大小写不敏感，可更改） | `/dmr` |
| **模块开关** | `holiday_enabled` / `news_enabled` / `tech_enabled` | 今日提醒 / 新闻速读 / 科技热点 | 开 |
| | `fx_enabled` / `fuel_enabled` / `gold_enabled` / `dram_enabled` | 汇率 / 油价 / 金价 / DRAM | 开 |
| | `ai_usage_enabled` | 昨日 AI 消费 | 开 |
| | `anime_enabled` / `movie_enabled` / `game_enabled` | 新番 / 电影 / 游戏 | 开 |
| | `ai_quota_enabled` | AI 额度（私聊/公开） | 开 |
| | `ai_quota_public` | AI 额度公开进群（开启后不再私发管理员） | 关 |
| **AI 额度** | `ai_quota.openrouter` / `deepseek` / `kimi` / `siliconflow` | 各厂商 API Key（留空跳过该家） | 空 |
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

### 🔑 API 申请指南

以下数据源需要申请 API Key（其余模块均为免费公开源，无需任何 Key）：

| 配置项 | 用途 | 申请地址 | 是否必填 |
|:-------|:-----|:---------|:---------|
| `ai_quota.openrouter` | AI 额度（OpenRouter） | [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys) | 选填 |
| `ai_quota.deepseek` | AI 额度（DeepSeek） | [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys) | 选填 |
| `ai_quota.kimi` | AI 额度（Kimi） | [platform.moonshot.cn/console/api-keys](https://platform.moonshot.cn/console/api-keys) | 选填 |
| `ai_quota.siliconflow` | AI 额度（SiliconFlow） | [cloud.siliconflow.cn/account/ak](https://cloud.siliconflow.cn/account/ak) | 选填 |
| `external_api.rawg_api_key` | 游戏发售（RAWG） | [rawg.io/apidocs](https://rawg.io/apidocs) | 选填（不填则游戏模块跳过） |
| `external_api.tmdb_api_key` | 电影降级源（TMDB） | [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) | 选填（豆瓣反爬时自动降级 TMDB） |
| `external_api.exchangerate_api_key` | 汇率（ExchangeRate-API） | [exchangerate-api.com](https://www.exchangerate-api.com/) | 选填（免费端点免 key） |

> **免费源说明**：新闻/科技/今日提醒/油价/金价（60s-api、IT之家）、DRAM（dramx）、新番（Bangumi）、电影（豆瓣）均为免费公开源，无需 Key。<br>
> **标注**：每个配置项在 WebUI 表格中已附申请地址，鼠标悬停可查看完整说明。

---

## 📁 项目结构

```
DailyMorningReport/
├── _manifest.json          # 插件清单（manifest v2）
├── plugin.py               # 主插件类（生命周期、采集→渲染→推送编排、/dmr 命令监听）
├── admin_commands.py       # 管理员 /dmr 命令解析与配置应用
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

### 管理员命令（/dmr）

仅 `admin_qqs` 中的管理员在 `target_groups` 内群聊发送时生效（前缀大小写不敏感，可通过 `admin_command_prefix` 更改）：

| 命令 | 说明 |
|:-----|:-----|
| `/dmr help` | 命令帮助 |
| `/dmr status` | 查看当前配置摘要（API Key 等敏感字段脱敏） |
| `/dmr set <键> <值>` | 修改配置项，如 `/dmr set basic.push_time 09:00`、`/dmr set modules.news_enabled false`；true/false→布尔，数字→数值，逗号分隔→列表 |
| `/dmr reset <键>` | 恢复该配置项默认值 |
| `/dmr push` | 立即推送一次早报 |

> 注意：`/dmr` 对配置的修改**仅运行时生效**，重启后恢复 WebUI / config.toml 中的配置值；AI 额度 key 与含 `api_key`/`token`/`secret` 的字段不允许通过命令修改，请到 WebUI 设置。

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

### Q8: /dmr 命令不生效？

✅ 检查 `admin_command_enabled` 是否开启、发送者是否在 `admin_qqs`、所在群是否在 `target_groups`、前缀是否与 `admin_command_prefix` 一致；`/dmr` 修改仅运行时生效，重启后恢复 WebUI 配置值。

### Q8: 图片乱码/豆腐块？

✅ 部署环境缺少中文字体时，在系统中安装 Noto Sans CJK 或微软雅黑。

### Q9: 豆瓣抓取失败？

✅ 豆瓣可能加强反爬，属预期降级（自动切 TMDB；无 TMDB key 则占位卡片）。

---

## 📜 更新日志

<details>
<summary>点击展开版本历史</summary>

### 版本 1.4.1

**Bug 修复**
- 修复油价/金价采集单地区/单条解析失败隔离：坏价格兜底，不中断整模块
- 修复 `on_unload` 竞态：等待进行中的早报生成完成（带超时），避免中途关闭采集器悬浮推送
- 修复调度循环前段异常静默终止：循环体整体纳入 try，DST 边界等异常 60 秒后重试
- 修复存档日期口径：用配置时区（非系统本地），并补 JSON 序列化异常兜底
- 修复 AI 消费非法时区回退（统一 Asia/Shanghai）
- 修复电影/游戏/节日日期用配置时区（`BaseCollector._today()` 统一口径）
- 修复采集重试不覆盖 429 限流（免费 API 常见瞬时错误）
- 修复封面收集空列表/None 安全回退
- 修复封面类型白名单排除 SVG（仅 jpg/png/webp/gif）
- 修复封面同 URL 并发重复下载（in-flight 去重）

### 版本 1.4.0

**新功能**
- 内嵌 MiSans 字体（GB2312 子集 woff2，Regular/Medium/Bold/Heavy 4 字重），彻底解决容器无中文字体导致的渲染回退问题
- 配置项与 README 标注全部 API 申请地址（新增「🔑 API 申请指南」章节）

**Bug 修复**
- 修复封面下载 SSRF 风险：`covers.py` 下载外部 URL 前校验 scheme 白名单 + 内网 IP 拦截；并修复**重定向绕过**——手动跟随重定向且逐跳校验（防公网 302 跳转内网/云元数据），封面下载加 5MB 大小上限防内存耗尽，支持 protocol-relative（`//img`）URL
- 修复周日获取不到新番数据：Bangumi `/calendar` 的 `weekday.id`（0=周日）与 ISO `isoweekday` 映射修正
- 修复 `on_unload` 清理中断：改用 `gather(return_exceptions=True)` 并行关闭任务与连接
- 修复采集异常逃逸：重试捕获所有 `httpx.HTTPError`，避免击穿失败隔离
- 修复 RAWG key 经 URL query 泄露：改为 `params` 传递 + 日志脱敏
- 修复 `capabilities` 缺 `render.html2png`/`chat.*` 导致渲染与推送被拒
- 修复昨日 AI 消费日期口径：改用配置时区计算"昨天"，与调度/新番等模块一致

**其他**
- 日志系统对接官方 SDK（`ctx.logger`），增强渲染/推送链路日志便于排查

### 版本 1.3.0

**行为调整**
- AI 额度配置简化为平铺 API Key：`ai_quota.<provider>` 直接填写 key 字符串（如 `ai_quota.deepseek = "sk-..."`），空即跳过该厂商；移除 `enabled` 开关与嵌套结构
- `/dmr` 敏感字段保护覆盖 `ai_quota.*`：AI 额度 key 不允许通过命令查看/修改，请到 WebUI 填写

> **升级提示**：从 1.2.0 升级时，若旧配置仍为嵌套结构（`[ai_quota.xxx]` 下的 `enabled`/`api_key`），请将四家厂商改为平铺 key 字符串，或删除后在 WebUI 表单中重新填写。

### 版本 1.2.0

**新功能**
- 管理员配置命令：目标群内管理员可用 `/dmr` 前缀命令（可更改，大小写不敏感）查看/修改配置、立即推送早报
- 子命令：`help` / `status`（敏感字段脱敏）/ `set <键> <值>`（类型自动转换）/ `reset <键>`（恢复默认）/ `push`
- 新增配置项 `admin_command_enabled`（总开关）与 `admin_command_prefix`（命令前缀）

**行为调整**
- `/dmr` 对配置的修改仅运行时生效，重启后恢复 WebUI 配置值；含 `api_key`/`token`/`secret` 的字段禁止通过命令修改

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

[⬆ 返回顶部](#-每日早报插件-v130)

</div>
