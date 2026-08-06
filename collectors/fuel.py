"""油价采集器（Viki API）。

真实响应结构（已现场验证）——注意：非"各省"，而是单地区 + 调价趋势：
{
  "code": 200, "message": "...",
  "data": {
    "region": "北京",
    "trend": {
      "next_adjustment_date": "8月14日24时",
      "direction": "下调",
      "change_ton": 120,
      "change_liter_desc": "0.09元/升-0.11元/升",
      "description": "下次调价时间: 8月14日24时，预计下调120元/吨 (0.09元/升-0.11元/升)"
    },
    "items": [
      {"name": "92#汽油", "price": 7.97, "price_desc": "7.97 元/升"},
      {"name": "95#汽油", "price": 8.48, ...},
      {"name": "0#柴油", "price": 7.69, ...}
    ]
  }
}
"""

from __future__ import annotations

from .base import BaseCollector, CollectorError, CollectorResult

VIKI_FUEL_URL = "https://60s-api.viki.moe/v2/fuel-price"


class FuelCollector(BaseCollector):
    """成品油价格（地区 + 调价趋势）。"""

    module_id = "fuel"
    display_name = "油价"

    async def collect(self) -> CollectorResult:
        try:
            payload = await self.fetch_json(VIKI_FUEL_URL)
            data = payload.get("data") or {}
            items = data.get("items") or []
            parsed_items = []
            for item in items:
                parsed_items.append(
                    {
                        "name": str(item.get("name") or ""),
                        "price": float(item.get("price") or 0),
                    }
                )
            if not parsed_items:
                raise CollectorError("油价数据为空")
            trend = data.get("trend") or {}
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                fetched_at=data.get("updated", ""),
                data={
                    "region": str(data.get("region") or ""),
                    "items": parsed_items,
                    "trend": {
                        "description": str(trend.get("description") or ""),
                        "direction": str(trend.get("direction") or ""),
                    },
                },
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
