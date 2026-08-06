---
feature: admin-qqs-and-group-auto-render
status: designed
updated: 2026-08-06
branch: main
commits: ad0f03a..<head-sha> # 交付时填写
---

# 多管理员与组自动渲染（1.1.0）

## Report

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
   - 组内启用模块全部采集失败（status=error）仍渲染该组（失败隔离占位卡片行为不变）；仅组内模块全部被禁用才跳过整图。
   - 不新增任何设置项控制组渲染。
3. **版本号**：`_manifest.json` `version` → `1.1.0`；`plugin.config_version` → `1.1.0`。
4. **README 重写**：参照 `Steam_Status_Monitor/README.md` 结构——居中标题（含版本）+ 徽章、目录、特性一览、安装与配置（表格）、项目结构、功能详解、快速上手、常见问题、更新日志（折叠，含 1.1.0 与 1.0.0）、许可证与鸣谢、返回顶部。配置表格移除分组开关行、`admin_qq` 改 `admin_qqs`。

## [S3] Out of Scope

- 不编写 ConfigUpgradeHook：旧 `admin_qq` 字符串不自动迁移。
- 不改动 MaiBot 主程序代码。
- 不新增任何组级渲染控制项。

## Tasks

- [ ] T1: 编写规格文档 — acceptance: `docs/compose/specs/admin-qqs-and-group-auto-render.md` 落盘并提交 (covers: S1, S2, S3)
- [ ] T2: 配置模型改造 — acceptance: `config_models.py` 无 `GroupSection`、`admin_qqs` 为 `List[str]`、`ai_quota_public` 位于 `ModulesSection`、`config_version="1.1.0"` (covers: S2)
- [ ] T3: plugin.py 适配 — acceptance: 私聊图为每个 `admin_qqs` 推送；`_render` 无 `groups` 引用，组渲染由模块开关集合推导 (covers: S2; depends: T2)
- [ ] T4: 测试更新与新增 — acceptance: `test_config`/`test_orchestrator`/`test_module_switches` 适配新字段；新增多管理员私发测试；全套通过 (covers: S2; depends: T3)
- [ ] T5: manifest 版本号 — acceptance: `_manifest.json` `version="1.1.0"` (covers: S2)
- [ ] T6: README 重写 — acceptance: 格式对齐 Steam_Status_Monitor，配置表含 `admin_qqs`、无分组开关，更新日志含 1.1.0/1.0.0 (covers: S2; depends: T2)
- [ ] T7: 验证 — acceptance: `python -m pytest tests/` 全绿、`python -m ruff check .` 与 format 通过 (covers: S2; depends: T4, T5)
- [ ] T8: 独立审查 — acceptance: 子代理审查无 critical 发现 (covers: S2; depends: T7)
- [ ] T9: 收尾 — acceptance: 规格文档 `status: delivered`、Report 填充、`commits` 范围记录并提交 (covers: —; depends: T8)
