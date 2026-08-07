"""节假日/纪念日采集器。

数据来源（双通道，互不依赖）：
1. Viki 今日历史 API：GET https://60s-api.viki.moe/v2/today-in-history
   响应（已实测）：{"data": {"month": 8, "day": 6, "items": [
     {"title": "...", "year": "1932", "description": "...", "event_type": "event|birth|death"}
   ]}}
2. 内置公历固定节日表（local），无需外部依赖；农历节日（春节/中秋等）随年份浮动，
   本模块不做农历计算（YAGNI），可后续扩展。

展示：今日提示放在组 1 资讯速览顶部。
"""

from __future__ import annotations

import datetime as dt

from .base import BaseCollector, CollectorError, CollectorResult

VIKI_HISTORY_URL = "https://60s-api.viki.moe/v2/today-in-history"

# 公历固定节日（月, 日 -> 节日名）
FIXED_HOLIDAYS: dict[tuple[int, int], str] = {
    (1, 1): "元旦",
    (2, 14): "情人节",
    (3, 8): "妇女节",
    (3, 12): "植树节",
    (4, 1): "愚人节",
    (5, 1): "劳动节",
    (5, 4): "青年节",
    (6, 1): "儿童节",
    (7, 1): "建党节",
    (8, 1): "建军节",
    (9, 10): "教师节",
    (10, 1): "国庆节",
    (12, 25): "圣诞节",
}


class HolidayCollector(BaseCollector):
    """今日节日/纪念日/历史事件。"""

    module_id = "holiday"
    display_name = "今日提醒"

    async def collect(self) -> CollectorResult:
        try:
            today = self._today()
            holidays = self._fixed_holidays(today)
            history = await self._history_events()
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"holidays": holidays, "history": history},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))

    @staticmethod
    def _fixed_holidays(today: dt.date) -> list[str]:
        """查内置公历固定节日表。"""
        name = FIXED_HOLIDAYS.get((today.month, today.day))
        return [name] if name else []

    async def _history_events(self) -> list[dict]:
        """拉取今日历史事件（失败不致命，仅跳过历史部分）。"""
        try:
            payload = await self.fetch_json(VIKI_HISTORY_URL)
            items = (payload.get("data") or {}).get("items") or []
            events = []
            for item in items:
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                events.append(
                    {
                        "title": title,
                        "year": str(item.get("year") or ""),
                        "event_type": str(item.get("event_type") or ""),
                    }
                )
            return events
        except Exception as exc:  # 历史事件拉取失败不致命，仅跳过该部分
            self.logger.warning("今日历史事件拉取失败: %s", exc)
            return []
