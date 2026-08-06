"""AI 额度采集器（OpenRouter / DeepSeek / Kimi / SiliconFlow）。

各家端点与响应（均已现场验证或经官方文档/开源实现确认）：

- OpenRouter: GET https://openrouter.ai/api/v1/auth/key
    {"data": {"label": "...", "usage": 1.23, "limit": 5.0, "is_free_tier": false}}
    limit 为 null 表示无上限；剩余 = limit - usage。
- DeepSeek: GET https://api.deepseek.com/user/balance
    {"is_available": true, "balance_infos": [{"currency": "CNY", "total_balance": "110.00", ...}]}
- Kimi: GET https://api.moonshot.cn/v1/users/me/balance
    {"data": {"available_balance": 100.0, "voucher_balance": 0, "cash_balance": 100.0}}
- SiliconFlow: GET https://api.siliconflow.cn/v1/user/info
    {"code": 20000, "data": {"balance": 10.0, "chargeBalance": 8.0, "totalBalance": 18.0}}

每家独立解析，一家失败不影响其余；key 一律脱敏，不写日志。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

import httpx

from .base import BaseCollector, CollectorError, CollectorResult, mask_key

# 归一化输出结构
# {"provider": str, "balance": float, "currency": str, "note": str}


class AiQuotaCollector(BaseCollector):
    """四家 AI 服务额度查询。"""

    module_id = "ai_quota"
    display_name = "AI 额度"

    async def collect(self) -> CollectorResult:
        quotas: list[dict[str, Any]] = []
        tasks: list[tuple[str, str, Callable[[str], Coroutine[Any, Any, dict[str, Any]]]]] = []

        cfg = self.config.ai_quota
        key_map = {
            "OpenRouter": (cfg.openrouter, self._fetch_openrouter),
            "DeepSeek": (cfg.deepseek, self._fetch_deepseek),
            "Kimi": (cfg.kimi, self._fetch_kimi),
            "SiliconFlow": (cfg.siliconflow, self._fetch_siliconflow),
        }
        for name, (section, fetcher) in key_map.items():
            if section.enabled and section.api_key:
                tasks.append((name, section.api_key, fetcher))

        for name, api_key, fetcher in tasks:
            try:
                item = await fetcher(api_key)
                quotas.append(item)
                self.logger.info("AI额度 [%s] 查询成功", name)
            except CollectorError as exc:
                self.logger.warning("AI额度 [%s] 查询失败: %s", name, exc)

        if not quotas:
            return self.error_result("未配置任何 AI 厂商 API Key")
        return CollectorResult(
            module_id=self.module_id,
            status="ok",
            data={"quotas": quotas},
        )

    async def _fetch_openrouter(self, api_key: str) -> dict[str, Any]:
        payload = await self.fetch_json(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        data = payload.get("data") or {}
        limit = data.get("limit")
        usage = float(data.get("usage") or 0)
        if limit is None:
            balance = None
            note = "按量计费/无上限"
        else:
            balance = float(limit) - usage
            note = ""
        return {
            "provider": "OpenRouter",
            "balance": balance if balance is not None else -1.0,
            "currency": "USD",
            "note": note,
        }

    async def _fetch_deepseek(self, api_key: str) -> dict[str, Any]:
        payload = await self.fetch_json(
            "https://api.deepseek.com/user/balance",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        infos = payload.get("balance_infos") or []
        if not infos:
            raise CollectorError("DeepSeek 响应缺少 balance_infos")
        info = infos[0]
        return {
            "provider": "DeepSeek",
            "balance": float(info.get("total_balance") or 0),
            "currency": str(info.get("currency") or "CNY"),
            "note": "",
        }

    async def _fetch_kimi(self, api_key: str) -> dict[str, Any]:
        payload = await self.fetch_json(
            "https://api.moonshot.cn/v1/users/me/balance",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        data = payload.get("data") or {}
        balance = data.get("available_balance")
        if balance is None:
            raise CollectorError("Kimi 响应缺少 available_balance")
        return {
            "provider": "Kimi",
            "balance": float(balance),
            "currency": "CNY",
            "note": "",
        }

    async def _fetch_siliconflow(self, api_key: str) -> dict[str, Any]:
        payload = await self.fetch_json(
            "https://api.siliconflow.cn/v1/user/info",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        code = payload.get("code")
        if code is not None and code != 20000:
            raise CollectorError(f"SiliconFlow 错误: {payload.get('message') or code}")
        data = payload.get("data") or {}
        balance = data.get("totalBalance")
        if balance is None:
            raise CollectorError("SiliconFlow 响应缺少 totalBalance")
        return {
            "provider": "SiliconFlow",
            "balance": float(balance),
            "currency": "CNY",
            "note": "",
        }
