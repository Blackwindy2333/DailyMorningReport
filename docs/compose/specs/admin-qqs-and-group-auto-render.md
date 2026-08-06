---
feature: admin-qqs-and-group-auto-render
status: delivered
updated: 2026-08-06
branch: main
commits: ad0f03a..f236b93
---

# 多管理员与组自动渲染（1.1.0）

## Report

**What was built** — 插件升级至 1.1.0：管理员 QQ 由单个字符串改为 `admin_qqs` 列表（AI 额度私聊图推送给列表中的每个管理员）；删除「分组开关」（`group1/2/3_enabled` 与整个 `GroupSection`），组图片是否渲染改为执行时按模块开关推导（组内任一模块启用即渲染，全部禁用才跳过整图，无任何设置项控制）；`ai_quota_public` 移入「模块开关」分组，作为组 2 的隐式触发源（公开额度开启时即使组 2 基础模块全禁用也渲染额度卡）；manifest 与 config_version 同步升至 1.1.0；README 按 Steam_Status_Monitor 格式重写（居中标题+徽章、目录、特性一览、配置表、项目结构、功能详解、常见问题、折叠更新日志 1.1.0/1.0.0、鸣谢）。

**Verification** — `python -m pytest tests/` → PASS，95 passed；`python -m ruff check .` → PASS；`python -m ruff format --check .` → PASS。独立审查（general-6）结论：4 项规格契约全部达成，无 critical；2 处 minor（配置描述空格、ai_quota 隐式触发未测）已修复并补测试。

**Journey log**
- 组 2 的「全部禁用即跳过」字面推导与 ai_quota_public 存在边界冲突：公开额度是组 2 的隐式触发源，需在规格与测试中显式记录（继承旧行为，非回归）。
- 版本选择上，配置字段更名/删除属不兼容变更，但用户选定 minor 提升 1.1.0 而非 2.0.0（README 更新日志承担迁移提示职责）。
- 测试沿用仓库既有 mock 风格（FakeCtx/FakeRender），多管理员推送通过 `_execute` 全链路验证发送流，而非只断言 render 层。
- 审查发现提交数实际为 6（规格文档创建 + 5 个实现/文档提交 + 2 个审查修复提交），与任务描述预期的 7 有出入，已在交付范围中如实记录为 `ad0f03a..f236b93`。

## [S1] Problem

- 管理员 QQ 仅支持单个（`basic.admin_qq: str`），无法让多个管理员接收 AI 额度私聊。
- 「分组开关」`group1/2/3_enabled` 与模块开关职责重叠：组是否渲染本应由模块开关在执行时推导，设置中的组开关冗余且可能互相冲突。
- 版本号长期停留在 1.0.0，未随功能迭代提升。
- README 结构与社区主流插件（如 Steam_Status_Monitor）不一致，缺少徽章、项目结构、更新日志等章节。

## [S2] Design

1. **多管理员（AI 额度私聊目标）**
   - `basic.admin_qq: str` → `basic.admin_qqs: List[str]`（默认 `[]`，description「管理员QQ号列表（AI额度私聊目标，可多个）」）。
   - 旧 `admin_qq` 字符串不再读取（不兼容变更；`config_version` 升版提示迁移，不写 ConfigUpgradeHook）。
   - 推送：每张私聊图为 `admin_qqs` 中每个 QQ 各推送一张。
   - 私聊条件：`admin_qqs` 非空 且 `ai_quota_public == false` 且 `ai_quota` 模块启用。
2. **移除分组开关，渲染按模块开关执行时推导**
   - 删除 `GroupSection`（`group1/2/3_enabled`），`DailyMorningReportConfig` 不再含 `groups` 字段。
   - `ai_quota_public` 移入 `ModulesSection`（归属 AI 额度，`__ui_label__ = "模块开关"`）。
   - 组渲染判定：采集完成后、渲染前，按 `_enabled_group_modules(_GROUPx_MODULES)` 非空推导；组内任一模块启用即渲染。
   - 组 2 例外：`ai_quota_public == true` 且 `ai_quota` 模块启用时，`ai_quota` 作为组 2 的隐式触发源——即使组 2 基础模块全部禁用，组 2 仍渲染（仅额度卡）。
   - 组内启用模块全部采集失败（status=error）仍渲染该组（失败隔离占位卡片行为不变）；仅组内模块全部被禁用才跳过整图。
   - 不新增任何设置项控制组渲染。
3. **版本号**：`_manifest.json` `version` → `1.1.0`；`plugin.config_version` → `1.1.0`。
4. **README 重写**：参照 `Steam_Status_Monitor/README.md` 结构——居中标题（含版本）+ 徽章、目录、特性一览、安装与配置（表格）、项目结构、功能详解、快速上手、常见问题、更新日志（折叠，含 1.1.0 与 1.0.0）、许可证与鸣谢、返回顶部。配置表格移除分组开关行、`admin_qq` 改 `admin_qqs`。

## [S3] Out of Scope

- 不编写 ConfigUpgradeHook：旧 `admin_qq` 字符串不自动迁移。
- 不改动 MaiBot 主程序代码。
- 不新增任何组级渲染控制项。

## Tasks

- [x] T1: 编写规格文档 — acceptance: `docs/compose/specs/admin-qqs-and-group-auto-render.md` 落盘并提交 (covers: S1, S2, S3)
- [x] T2: 配置模型改造 — acceptance: `config_models.py` 无 `GroupSection`、`admin_qqs` 为 `List[str]`、`ai_quota_public` 位于 `ModulesSection`、`config_version="1.1.0"` (covers: S2)
- [x] T3: plugin.py 适配 — acceptance: 私聊图为每个 `admin_qqs` 推送；`_render` 无 `groups` 引用，组渲染由模块开关集合推导 (covers: S2; depends: T2)
- [x] T4: 测试更新与新增 — acceptance: `test_config`/`test_orchestrator`/`test_module_switches` 适配新字段；新增多管理员私发测试；全套通过 (covers: S2; depends: T3)
- [x] T5: manifest 版本号 — acceptance: `_manifest.json` `version="1.1.0"` (covers: S2)
- [x] T6: README 重写 — acceptance: 格式对齐 Steam_Status_Monitor，配置表含 `admin_qqs`、无分组开关，更新日志含 1.1.0/1.0.0 (covers: S2; depends: T2)
- [x] T7: 验证 — acceptance: `python -m pytest tests/` 全绿、`python -m ruff check .` 与 format 通过 (covers: S2; depends: T4, T5)
- [x] T8: 独立审查 — acceptance: 子代理审查无 critical 发现 (covers: S2; depends: T7)
- [x] T9: 收尾 — acceptance: 规格文档 `status: delivered`、Report 填充、`commits` 范围记录并提交 (covers: —; depends: T8)
