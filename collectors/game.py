"""游戏发售采集器（RAWG API）。

端点：GET https://api.rawg.io/api/games?key=...&dates=YYYY-MM-DD,YYYY-MM-DD&ordering=-added&page_size=N
响应（公开标准结构）：
{
  "count": 1000, "next": "...", "previous": null,
  "results": [
    {
      "id": 1, "slug": "...", "name": "...",
      "released": "2026-08-10",
      "background_image": "https://media.rawg.io/media/...",
      "platforms": [{"platform": {"name": "PC", "slug": "pc"}, ...}]
    }
  ]
}
无 key 返回 401。key 为空时跳过模块并提示配置。
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from .base import BaseCollector, CollectorError, CollectorResult

RAWG_API_URL = "https://api.rawg.io/api/games"


class GameCollector(BaseCollector):
    """近期发售新游。"""

    module_id = "game"
    display_name = "游戏发售"

    def __init__(self, config: Any, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self._days = int(getattr(config.render, "game_days", 7))

    async def collect(self) -> CollectorResult:
        api_key = self.config.external_api.rawg_api_key
        if not api_key:
            return self.error_result("未配置 RAWG API Key，跳过游戏发售模块")
        try:
            today = dt.date.today()
            end = today + dt.timedelta(days=self._days)
            url = (
                f"{RAWG_API_URL}?key={api_key}&dates={today.isoformat()},{end.isoformat()}&ordering=-added&page_size=10"
            )
            payload = await self.fetch_json(url)
            results = payload.get("results") or []
            games = []
            for item in results:
                platforms = [
                    str(plat_obj.get("name") or "")
                    for plat in (item.get("platforms") or [])
                    if isinstance(plat, dict) and isinstance(plat_obj := plat.get("platform"), dict)
                ]
                games.append(
                    {
                        "name": str(item.get("name") or ""),
                        "released": str(item.get("released") or ""),
                        "platforms": [p for p in platforms if p],
                        "image_url": str(item.get("background_image") or ""),
                    }
                )
            if not games:
                raise CollectorError("近期无新游发售数据")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"games": games},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
