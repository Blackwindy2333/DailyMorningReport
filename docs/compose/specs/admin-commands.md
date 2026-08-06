---
feature: admin-commands
status: delivered
updated: 2026-08-06
branch: main
commits: 106c4db..d613d76
---

# 管理员 /dmr 配置命令（1.2.0）

## Report

**What was built** — 插件升级至 1.2.0：新增管理员群聊配置命令。目标群（`target_groups`）内的管理员（`admin_qqs`）发送以可配置前缀（默认 `/dmr`，大小写不敏感）开头的消息即可执行 5 个子命令：`help`、`status`（敏感字段脱敏为 `****`）、`set <点分键> <值>`（true/false→bool、数字→数值、逗号分隔→列表，整份配置经配置模型校验）、`reset <键>`（恢复默认值）、`push`（立即推送一次早报）。含 `api_key`/`token`/`secret` 的字段禁止通过命令修改；`set`/`reset` 涉及 `basic.enabled`/`push_time`/`timezone` 时自动重启调度器。修改仅运行时生效（内存 `self.config`），不写 config.toml，help 与 README 均明示。新增配置项 `admin_command_enabled`（总开关）与 `admin_command_prefix`（前缀）；manifest 与 config_version 同步 1.2.0。

**Verification** — `python -m pytest tests/` → PASS，123 passed（含新增 28 例 admin_commands 测试：纯函数 9 例 + 集成 19 例，覆盖鉴权/无权限回复/敏感字段拒绝/调度重启/接线断言）；`python -m ruff check .` → PASS；`python -m ruff format --check .` → PASS。独立审查两轮：首轮发现 1 个 critical（EventHandler 消息事件分发已被 Host 停用）与 README 缺口；修复为 `@HookHandler("chat.receive.after_process", mode=HookMode.OBSERVE)` 并经第二轮回审确认无遗留 critical；README 已补齐。

**Journey log**
- **关键死路**：初版用 `@EventHandler(ON_MESSAGE_PRE_PROCESS)` 监听消息，独立审查核实当前 MaiBot Host 已注释 `handle_mai_events(ON_MESSAGE)`（src/chat/message_receive/bot.py:783），消息事件不再分发——入站消息只走 `chat.receive.*` Hook。改为 `@HookHandler("chat.receive.after_process", mode=HookMode.OBSERVE)`（bot.py:724 每条入站消息触发，message=序列化 SessionMessage 含 processed_plain_text/message_info/session_id；observe 由 hook_dispatcher 后台 create_task 执行，非阻塞）。教训：插件消息监听先确认 Host 当前分发机制（Hook vs Event），勿假设文档示例仍生效。
- **持久化约束**：Host 的 `component.update_plugin_config` 能力仅授予 `builtin.plugin-management`，第三方插件无官方配置写接口；经用户决策采用「仅运行时生效」（Steam_Status_Monitor 的 /steam set 先例），不引入 override 文件（避免双配置源）。
- **命令前缀可配置**使静态 `@Command` 正则不可行（装饰器在类定义期求值），改用 Hook + 运行时 `strip_prefix`（大小写不敏感、前缀后须为空白，避免 `/dmrxxx` 误触发）。
- 测试直接调用 `_dispatch_admin_command` 会掩盖"监听器未接线"类问题，故新增接线断言测试（校验 `__maibot_component_info__` 的 hook/name/mode）。
- `set_plugin_config`（SDK）会重建 `self.config` 实例并校验整份配置，配合 `get_plugin_config_data` 浅拷贝 + `set_nested` 深拷贝，无共享可变状态污染。

## [S1] Problem

- 插件配置只能通过 WebUI / config.toml 修改，管理员在群聊中无法远程调整配置（推送时间、模块开关等）。
- 需要一种仅限管理员、在目标群内生效、以可配置前缀（默认 `/dmr`，大小写不敏感）触发的群聊命令机制。

## [S2] Design

1. **监听机制**
   - 使用 `@HookHandler("chat.receive.after_process", name="dmr_admin_commands", mode=HookMode.OBSERVE)`：OBSERVE 旁路，由 Host 对每条入站消息在 `message.process()` 后触发，后台协程执行、不阻塞消息链。
   - 不使用 `@EventHandler`：当前 MaiBot Host 已停用消息事件分发（`ON_MESSAGE` 桥接被注释），入站消息只走 `chat.receive.*` Hook。
   - 消息 dict 字段：`platform`、`message_info.user_info.user_id`（发送者）、`message_info.group_info.group_id`（群）、`session_id`（回复流）、`processed_plain_text`（无则回退 `raw_message` text 段拼接）。
   - 静态 `@Command` 正则无法表达可配置前缀，故采用 Hook 运行时过滤。
2. **过滤链（全部满足才执行命令）**
   - `config.basic.admin_command_enabled == True`；`platform == "qq"`；存在 `user_info.user_id`。
   - 文本以前缀开头（大小写不敏感），且前缀之后为空或空白（避免 `/dmrxxx` 误触发）。
   - `user_id ∈ admin_qqs`；`group_info` 存在且 `group_id ∈ target_groups`。
   - 前缀命中但未通过鉴权/范围校验 → 向 `session_id` 回复「无权限执行早报管理命令」。
3. **命令集**（前缀 P，默认 `/dmr`；子命令大小写不敏感）
   - `P help` — 命令用法说明（含「仅运行时生效，重启后恢复 WebUI 配置值」提示）。
   - `P status` — 当前配置摘要；路径含 `api_key`/`token`/`secret`（不区分大小写）的字段值显示 `****`。
   - `P set <点分键> <值>` — 修改配置项。键含敏感词（`api_key`/`token`/`secret`）时拒绝并提示去 WebUI 修改；值转换规则：`true/false`（不区分大小写）→ bool，整型 → int，浮点 → float，含中英文逗号 → `List[str]`（分割并 strip），其余 → str；转换后以 `DailyMorningReportConfig` 校验整份配置，非法则回复错误；合法则更新内存 `self.config` 并回复新值（非敏感值可回显）。
   - `P reset <点分键>` — 将该键恢复为配置模型的默认值（从 `build_default_config()` 取），应用流程同 `set`。
   - `P push` — 立即执行一次早报（复用 `_running_lock` 与 `_execute`），回复「日报已生成并推送」。
   - set/reset 若涉及 `basic.enabled`/`basic.push_time`/`basic.timezone`，需重启调度器使时间生效。
4. **持久化**：仅运行时生效（内存 `self.config`），不写 config.toml、无 override 文件；重启后恢复 WebUI/config.toml 值。`help` 与 README 明示。
5. **配置新增**：`basic.admin_command_enabled: bool = True`（总开关）；`basic.admin_command_prefix: str = "/dmr"`（前缀，可更改）。
6. **版本号**：`_manifest.json` `version` → `1.2.0`；`plugin.config_version` → `1.2.0`。

## [S3] Out of Scope

- 不持久化命令修改（无 override 文件；仅运行时生效）。
- 不支持私聊命令（仅 target_groups 内群聊）。
- 不允许通过命令修改含 `api_key`/`token`/`secret` 的字段。
- 不改动 MaiBot 主程序代码。

## Tasks

- [x] T1: 编写规格文档 — acceptance: `docs/compose/specs/admin-commands.md` 落盘并提交 (covers: S1, S2, S3)
- [x] T2: 配置模型 — acceptance: `config_models.py` 含 `admin_command_enabled`/`admin_command_prefix`，`config_version="1.2.0"` (covers: S2)
- [x] T3: admin_commands.py 模块 — acceptance: 前缀剥离、子命令解析、值类型转换、敏感键判定、嵌套 set/reset 默认值、status 脱敏、help 文本均可单测 (covers: S2)
- [x] T4: plugin.py 集成 — acceptance: HookHandler 过滤链、鉴权、无权限回复、`set`/`reset`/`status`/`help`/`push` 执行、调度重启逻辑生效 (covers: S2; depends: T3)
- [x] T5: manifest 版本 — acceptance: `_manifest.json` `version="1.2.0"` (covers: S2)
- [x] T6: 测试 — acceptance: 覆盖解析/转换/敏感字段拒绝/鉴权/无权限回复/set 应用/reset 默认值/status 脱敏/push；全套通过 (covers: S2; depends: T4)
- [x] T7: 验证 — acceptance: `python -m pytest tests/` 全绿、`python -m ruff check .` 与 format 通过 (covers: S2; depends: T6)
- [x] T8: 独立审查 — acceptance: 子代理审查无 critical（首轮 critical 已修复并经复审确认） (covers: S2; depends: T7)
- [x] T9: README 更新 — acceptance: 命令说明（含仅运行时生效提示）、配置表新增两行、更新日志 1.2.0 (covers: S2; depends: T2)
- [x] T10: 收尾 — acceptance: 规格 `status: delivered`、Report 填充、commits 范围记录并提交 (covers: —; depends: T8)
