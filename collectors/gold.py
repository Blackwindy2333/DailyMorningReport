"""金价采集器（Viki API）。

真实响应结构（已现场验证）——metals 数组含国际与国内金价：
{
  "code": 200, "message": "...",
  "data": {
    "date": "2026-08-06",
    "metals": [
      {"name": "伦敦金(现货黄金)", "sell_price": "4267.02", "unit": "美元/盎司", ...},
      {"name": "黄金价格", "sell_price": "924.27", "unit": "元/克", ...},
      ...
    ]
  }
}
"""

from __future__ import annotations

from .base import BaseCollector, CollectorError, CollectorResult

VIKI_GOLD_URL = "https://60s-api.viki.moe/v2/gold-price"

# 展示优先级与关键词匹配
GOLD_KEYWORDS = ("伦敦金", "纽约黄金", "黄金价格", "白银", "铂金")


class GoldCollector(BaseCollector):
    """国际/国内金价。"""

    module_id = "gold"
    display_name = "金价"

    async def collect(self) -> CollectorResult:
        try:
            payload = await self.fetch_json(VIKI_GOLD_URL)
            data = payload.get("data") or {}
            metals = data.get("metals") or []
            parsed = []
            for metal in metals:
                name = str(metal.get("name") or "")
                if any(keyword in name for keyword in GOLD_KEYWORDS):
                    parsed.append(
                        {
                            "name": name,
                            "price": float(metal.get("sell_price") or 0),
                            "unit": str(metal.get("unit") or ""),
                        }
                    )
            if not parsed:
                raise CollectorError("金价数据为空")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                fetched_at=data.get("date", ""),
                data={"metals": parsed},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
