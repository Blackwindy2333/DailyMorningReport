---
feature: ai-quota-flat-config
status: designed
updated: 2026-08-06
branch: main
commits: 0a0a08e..<head-sha> # 交付时填写
---

# AI 额度平铺 Key 配置（1.3.0）

## Report

## [S1] Problem

- 用户部署端在 WebUI 原始 TOML 编辑器中把 `ai_quota.deepseek` 写成了平铺字符串（`deepseek = "sk-..."`），而配置模型要求嵌套节 `{enabled, api_key}`，导致校验失败（`插件配置校验请求失败`）。
- 用户决策：修改配置模型本身，让 AI 额度一栏**只需填写 API Key 字符串**，无需 enabled 开关与嵌套结构。

## [S2] Design

1. **配置模型**
   - 删除 `AiProviderSection` 类。
   - `AiQuotaSection` 改为 4 个字符串字段：`openrouter` / `deepseek` / `kimi` / `siliconflow`，各为 `str = Field(default="", description="XX API Key（留空则跳过该厂商）")`。
   - 启用语义：**key 非空即启用该厂商**（不再有 `enabled` 开关）。
   - `config_version` → `1.3.0`；`_manifest.json` `version` → `1.3.0`。
2. **ai_quota 采集器**
   - `key_map` 改为直接读字符串；`if api_key:` 非空即采集；`section.enabled` 引用删除。
3. **/dmr 安全**（保护既有「key 仅限 WebUI」决策）
   - `is_sensitive_key` 扩展：`key == "ai_quota"` 或以 `"ai_quota."` 开头视为敏感（`modules.ai_quota_enabled`/`modules.ai_quota_public` 不受影响，因不以 `ai_quota.` 开头）。
   - `status` 中对 `ai_quota.*` 值脱敏为 `****`；`set` 对 `ai_quota.*` 拒绝并提示去 WebUI 修改。
   - `build_help_text` 提示改为「AI 额度 key 与含 api_key/token/secret 的字段请到 WebUI 修改」。
4. **迁移行为**（依赖 Runner 版本迁移，不写 ConfigUpgradeHook）
   - 版本号 1.2.0 → 1.3.0 触发 Runner `rebuild_plugin_config_data(新默认, 旧配置)`：平铺字符串值（如 `deepseek = "sk-..."`）迁移到新结构合法；旧嵌套 dict（`[ai_quota.xxx] enabled/api_key`）会原样覆盖到 str 字段导致校验失败——部署端需把 4 家厂商全部改为平铺字符串，或通过 WebUI 表单重新填写。
   - 迁移提示写入 README 更新日志与交付说明。

## [S3] Out of Scope

- 不编写 ConfigUpgradeHook / 兼容旧嵌套结构（不做兜底）。
- 不改动 MaiBot 主程序代码（WebUI 原始 TOML 编辑器不校验结构属主程序行为）。
- AI 额度 key 仍不允许通过 `/dmr` 设置（保持既有安全决策）。

## Tasks

- [ ] T1: 规格文档 — acceptance: `docs/compose/specs/ai-quota-flat-config.md` 落盘并提交 (covers: S1, S2, S3)
- [ ] T2: 配置模型 — acceptance: `AiQuotaSection` 为 4 个字符串字段、无 `AiProviderSection`、`config_version="1.3.0"` (covers: S2)
- [ ] T3: ai_quota 采集器 — acceptance: 读字符串 key，非空即采集，无 `section.enabled` 引用 (covers: S2; depends: T2)
- [ ] T4: 敏感检测与帮助 — acceptance: `is_sensitive_key("ai_quota.deepseek")` 为 True、`modules.ai_quota_enabled` 为 False；help 文本更新 (covers: S2)
- [ ] T5: manifest 版本 — acceptance: `_manifest.json` `version="1.3.0"` (covers: S2)
- [ ] T6: 测试适配 — acceptance: 5 个测试文件（config/admin_commands/module_switches/orchestrator/parsers）全部适配字符串字段；新增 `is_sensitive_key` 断言；全套通过 (covers: S2; depends: T4)
- [ ] T7: 验证 — acceptance: `python -m pytest tests/` 全绿、`python -m ruff check .` 与 format 通过 (covers: S2; depends: T6)
- [ ] T8: 独立审查 — acceptance: 子代理审查无 critical (covers: S2; depends: T7)
- [ ] T9: README 更新 — acceptance: AI 额度配置表改为平铺 key、更新日志 1.3.0（含迁移提示） (covers: S2; depends: T2)
- [ ] T10: 收尾 — acceptance: 规格 `status: delivered`、Report 填充、commits 范围记录并提交 (covers: —; depends: T8)
