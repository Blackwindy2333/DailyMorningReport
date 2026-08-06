"""油价采集器（Viki API）。

真实响应结构（已现场验证）——支持 ?region=任意地区 参数：
{
  "code": 200, "message": "...",
  "data": {
    "region": "北京",
    "trend": {"next_adjustment_date": "...", "direction": "下调", "description": "..."},
    "items": [
      {"name": "92#汽油", "price": 7.97, "price_desc": "7.97 元/升"},
      {"name": "95#汽油", "price": 8.48, ...},
      {"name": "0#柴油", "price": 7.69, ...}
    ]
  }
}
地区列表来自配置 render.fuel_regions（默认北京），可配置任意地区名。
"""

from __future__ import annotations

from .base import BaseCollector, CollectorError, CollectorResult

VIKI_FUEL_URL = "https://60s-api.viki.moe/v2/fuel-price"


class FuelCollector(BaseCollector):
    """成品油价格（多地区 + 调价趋势）。"""

    module_id = "fuel"
    display_name = "油价"

    async def collect(self) -> CollectorResult:
        regions = getattr(self.config.render, "fuel_regions", None) or ["北京"]
        regions = [str(r).strip() for r in regions if str(r).strip()]
        if not regions:
            return self.error_result("未配置油价地区")
        try:
            all_regions: list[dict] = []
            last_trend: dict = {}
            for region in regions:
                try:
                    payload = await self.fetch_json(VIKI_FUEL_URL, params={"region": region})
                except CollectorError as exc:
                    self.logger.warning("油价地区 %s 查询失败: %s", region, exc)
                    continue
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
                if parsed_items:
                    all_regions.append(
                        {
                            "region": str(data.get("region") or region),
                            "items": parsed_items,
                        }
                    )
                trend = data.get("trend") or {}
                if trend.get("description"):
                    last_trend = {
                        "description": str(trend.get("description") or ""),
                        "direction": str(trend.get("direction") or ""),
                    }
            if not all_regions:
                raise CollectorError("油价数据为空（所有地区查询失败）")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"regions": all_regions, "trend": last_trend},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
