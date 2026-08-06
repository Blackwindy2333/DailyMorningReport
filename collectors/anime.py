"""新番放送采集器（Bangumi Calendar API）。

端点：GET https://api.bgm.tv/calendar（每日放送）
响应结构（官方 OpenAPI 规范确认）：
[
  {
    "weekday": {"en": "Mon", "cn": "星期一", "ja": "月耀日", "id": 1},
    "items": [
      {
        "id": 12, "url": "https://bgm.tv/subject/12",
        "type": 2, "name": "ちょびっツ", "name_cn": "人形电脑天使心",
        "air_date": "2002-04-02", "air_weekday": 2,
        "images": {"large": "https://lain.bgm.tv/pic/cover/l/...", "grid": "...", ...},
        "rating": {"total": 2289, "score": 7.6}
      }
    ]
  },
  ... 共 7 组（按星期）
]
取当天（weekday.id == 今日星期）的条目。封面交给 render/covers.py 下载内嵌。
"""

from __future__ import annotations

import datetime as dt

from .base import BaseCollector, CollectorError, CollectorResult

BGM_CALENDAR_URL = "https://api.bgm.tv/calendar"


class AnimeCollector(BaseCollector):
    """当日新番放送。"""

    module_id = "anime"
    display_name = "新番放送"

    async def collect(self) -> CollectorResult:
        try:
            payload = await self.fetch_json(
                BGM_CALENDAR_URL,
                headers={"User-Agent": "DailyMorningReport/1.0 (MaiBot plugin)"},
            )
            if not isinstance(payload, list):
                raise CollectorError("Bangumi 日历响应结构异常")
            today_weekday = dt.date.today().isoweekday()  # 1=周一 ... 7=周日
            target = None
            for day_group in payload:
                weekday = (day_group.get("weekday") or {}).get("id")
                if weekday == today_weekday:
                    target = day_group
                    break
            items = (target or {}).get("items") or []
            animes = []
            for subject in items:
                if not isinstance(subject, dict):
                    continue
                name_cn = str(subject.get("name_cn") or "").strip()
                name = str(subject.get("name") or "").strip()
                images = subject.get("images") or {}
                rating = subject.get("rating") or {}
                score = rating.get("score")
                animes.append(
                    {
                        "name": name_cn or name,
                        "air_date": str(subject.get("air_date") or ""),
                        "image_url": str(images.get("large") or images.get("grid") or ""),
                        "score": float(score) if isinstance(score, (int, float)) else None,
                    }
                )
            if not animes:
                raise CollectorError("今日无新番数据")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"animes": animes},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
