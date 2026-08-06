"""新闻速读采集器（Viki 60s API）。

真实响应结构（已现场验证）：
{
  "code": 200, "message": "...",
  "data": {
    "date": "2026-08-06",
    "news": ["...", "..."],       # 新闻列表
    "tip": "今日一语（单数字段）",
    "day_of_week": "星期四",
    "lunar_date": "丙午年六月廿四"
  }
}
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseCollector, CollectorError, CollectorResult

VIKI_60S_URL = "https://60s-api.viki.moe/v2/60s"


class NewsCollector(BaseCollector):
    """每日 60 秒读懂世界。"""

    module_id = "news"
    display_name = "新闻速读"

    def __init__(self, config: Any, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self._news_count = int(getattr(config.render, "news_count", 10))

    async def collect(self) -> CollectorResult:
        try:
            payload = await self.fetch_json(VIKI_60S_URL)
            data = payload.get("data") or {}
            news_list = data.get("news") or []
            news = [str(item).strip() for item in news_list if str(item).strip()]
            limited = news[: self._news_count]
            if not limited:
                raise CollectorError("新闻列表为空")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                fetched_at=data.get("date", ""),
                data={
                    "news": limited,
                    "tip": str(data.get("tip") or ""),
                    "day_of_week": str(data.get("day_of_week") or ""),
                    "lunar_date": str(data.get("lunar_date") or ""),
                },
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
