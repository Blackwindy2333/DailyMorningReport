"""汇率采集器（ExchangeRate-API 免费端点）。

真实响应结构（已现场验证）：
{
  "result": "success",
  "base_code": "CNY",
  "rates": {"USD": 0.147881, "EUR": 0.12815, ...}
}
免费端点无需 key（约 1500 次/月），key 从配置读取以防限流。
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseCollector, CollectorError, CollectorResult

FX_API_URL = "https://open.er-api.com/v6/latest/CNY"

# 展示格式：1 人民币 = X 外币
DEFAULT_CURRENCIES = ("USD", "EUR", "JPY", "HKD", "GBP")


class FxCollector(BaseCollector):
    """法币汇率（CNY 基准）。"""

    module_id = "fx"
    display_name = "实时汇率"

    def __init__(self, config: Any, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        currencies = getattr(config.render, "fx_currencies", None) or DEFAULT_CURRENCIES
        self._currencies = [str(c).upper() for c in currencies]

    async def collect(self) -> CollectorResult:
        try:
            payload = await self.fetch_json(FX_API_URL)
            rates = payload.get("rates") or {}
            result = []
            for code in self._currencies:
                if code in rates:
                    result.append(
                        {"code": code, "rate": round(float(rates[code]), 4)}
                    )
            if not result:
                raise CollectorError("汇率数据为空（检查币种列表配置）")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                fetched_at=payload.get("time_last_update_utc", ""),
                data={"base": "CNY", "rates": result},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
