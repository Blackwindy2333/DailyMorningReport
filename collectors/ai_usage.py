"""昨日 AI 消费汇总采集器（基于 SDK ctx.statistics）。

使用 ctx.statistics.local.models(days=2, limit=N) 获取最近两天的模型汇总，
按日期区分昨日与今日。需要 manifest capabilities 声明 statistics.local.models。

响应结构（SDK 层约定，list[dict]，字段以 Host 实际返回为准，做容错）：
[{"model_name": "gpt-4o", "date": "2026-08-05", "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}, ...]
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .base import BaseCollector, CollectorResult


class AiUsageCollector(BaseCollector):
    """昨日 AI 消费（token 用量）汇总。"""

    module_id = "ai_usage"
    display_name = "昨日 AI 消费"

    def __init__(self, config: Any, logger: logging.Logger, ctx: Any = None) -> None:
        super().__init__(config, logger)
        self._ctx = ctx

    async def collect(self) -> CollectorResult:
        if self._ctx is None:
            return self.error_result("统计能力不可用（ctx 未注入）")
        try:
            records = await self._ctx.statistics.local.models(days=2, limit=100)
        except Exception as exc:  # 统计能力未授权或失败，跳过模块
            return self.error_result(f"统计查询失败: {exc}")
        if not records:
            return self.error_result("近两日无模型调用记录")

        yesterday_key = self._yesterday_key()
        yesterday = [r for r in records if self._record_date(r) == yesterday_key]
        if not yesterday:
            return self.error_result("昨日无模型调用记录")

        # 聚合：按模型汇总 token 用量
        by_model: dict[str, dict[str, Any]] = {}
        for record in yesterday:
            name = str(record.get("model_name") or record.get("model") or "未知模型")
            item = by_model.setdefault(
                name, {"model": name, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            )
            item["calls"] += int(record.get("calls") or record.get("request_count") or 1)
            item["prompt_tokens"] += int(record.get("prompt_tokens") or 0)
            item["completion_tokens"] += int(record.get("completion_tokens") or 0)
            item["total_tokens"] += int(record.get("total_tokens") or 0)

        totals = {
            "calls": sum(v["calls"] for v in by_model.values()),
            "prompt_tokens": sum(v["prompt_tokens"] for v in by_model.values()),
            "completion_tokens": sum(v["completion_tokens"] for v in by_model.values()),
            "total_tokens": sum(v["total_tokens"] for v in by_model.values()),
        }
        return CollectorResult(
            module_id=self.module_id,
            status="ok",
            data={
                "date": yesterday_key,
                "models": sorted(by_model.values(), key=lambda v: v["total_tokens"], reverse=True),
                "totals": totals,
            },
        )

    @staticmethod
    def _yesterday_key() -> str:
        import datetime as dt

        return (dt.date.today() - dt.timedelta(days=1)).isoformat()

    @staticmethod
    def _record_date(record: dict[str, Any]) -> str:
        """从记录提取日期（容错多种日期字段格式）。"""
        for key in ("date", "day", "created_at"):
            value = record.get(key)
            if value:
                match = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
                if match:
                    return match.group(1)
        return ""
