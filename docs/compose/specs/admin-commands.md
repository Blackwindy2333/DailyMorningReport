---
feature: admin-commands
status: designed
updated: 2026-08-06
branch: main
commits: 106c4db..<head-sha> # 交付时填写
---

# 管理员 /dmr 配置命令（1.2.0）

## Report

## [S1] Problem

- 插件配置只能通过 WebUI / config.toml 修改，管理员在群聊中无法远程调整配置（推送时间、模块开关等）。
- 需要一种仅限管理员、在目标群内生效、以可配置前缀（默认 `/dmr`，大小写不敏感）触发的群聊命令机制。

## [S2] Design

1. **监听机制**
   - 使用 `@EventHandler("dmr_admin_commands", event_type=EventType.ON_MESSAGE_PRE_PROCESS, intercept_message=False, weight=100)`：非阻塞旁路，不拦截消息链。
   - 消息 dict 字段：`platform`、`message_info.user_info.user_id`（发送者）、`message_info.group_info.group_id`（群）、`session_id`（回复流）、`processed_plain_text`（文本）。
   - 静态 `@Command` 正则无法表达可配置前缀，故采用 EventHandler 运行时过滤。
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

- [ ] T1: 编写规格文档 — acceptance: `docs/compose/specs/admin-commands.md` 落盘并提交 (covers: S1, S2, S3)
- [ ] T2: 配置模型 — acceptance: `config_models.py` 含 `admin_command_enabled`/`admin_command_prefix`，`config_version="1.2.0"` (covers: S2)
- [ ] T3: admin_commands.py 模块 — acceptance: 前缀剥离、子命令解析、值类型转换、敏感键判定、嵌套 set/reset 默认值、status 脱敏、help 文本均可单测 (covers: S2)
- [ ] T4: plugin.py 集成 — acceptance: EventHandler 过滤链、鉴权、无权限回复、`set`/`reset`/`status`/`help`/`push` 执行、调度重启逻辑生效 (covers: S2; depends: T3)
- [ ] T5: manifest 版本 — acceptance: `_manifest.json` `version="1.2.0"` (covers: S2)
- [ ] T6: 测试 — acceptance: 覆盖解析/转换/敏感字段拒绝/鉴权/无权限回复/set 应用/reset 默认值/status 脱敏/push；全套通过 (covers: S2; depends: T4)
- [ ] T7: 验证 — acceptance: `python -m pytest tests/` 全绿、`python -m ruff check .` 与 format 通过 (covers: S2; depends: T6)
- [ ] T8: 独立审查 — acceptance: 子代理审查无 critical (covers: S2; depends: T7)
- [ ] T9: README 更新 — acceptance: 命令说明（含仅运行时生效提示）、配置表新增两行、更新日志 1.2.0 (covers: S2; depends: T2)
- [ ] T10: 收尾 — acceptance: 规格 `status: delivered`、Report 填充、commits 范围记录并提交 (covers: —; depends: T8)
