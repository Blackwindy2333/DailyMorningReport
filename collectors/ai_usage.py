"""昨日 AI 消费汇总采集器（基于 SDK ctx.statistics）。

使用 ctx.statistics.local.token_trend(days=2, bucket="day", group_by="model")：
返回按日分桶的模型 token 趋势，可精确提取"昨日"的数据。
响应结构（主程序 src/plugin_runtime/capabilities/data.py 确认）：
{
  "success": true,
  "series": {
    "timestamps": ["2026-08-05 00:00:00", "2026-08-06 00:00:00"],   # 按日分桶
    "values_by_key": {"gpt_4o": [150.0, 0.0], ...},                  # 每个模型：按 timestamps 顺序的 total_tokens
    "labels_by_key": {"gpt_4o": "gpt-4o"},                            # key -> 模型名
    "total": 150.0,
    "source_count": 2
  }
}
注意：statistics.local.models 仅按 model_name 聚合且无日期字段，不适用"昨日"场景。
"""

from __future__ import annotations

import datetime as dt
import logging
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
            result = await self._ctx.statistics.local.token_trend(days=2, bucket="day", group_by="model", top_items=20)
        except Exception as exc:  # 统计能力未授权或失败，跳过模块
            return self.error_result(f"统计查询失败: {exc}")
        series = (result or {}).get("series") or {}
        timestamps = series.get("timestamps") or []
        if not timestamps:
            return self.error_result("近两日无模型调用记录")

        # 找到"昨日"（00:00:00 格式日期）的索引
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        yesterday_index = None
        for index, ts in enumerate(timestamps):
            if str(ts).startswith(yesterday):
                yesterday_index = index
                break
        if yesterday_index is None:
            return self.error_result("昨日无模型调用记录")

        # 汇总各模型昨日 token 用量
        labels_by_key = series.get("labels_by_key") or {}
        values_by_key = series.get("values_by_key") or {}
        models = []
        total_tokens = 0
        for key, values in values_by_key.items():
            value = float(values[yesterday_index]) if yesterday_index < len(values) else 0.0
            if value <= 0:
                continue
            name = str(labels_by_key.get(key) or key)
            models.append({"model": name, "total_tokens": int(value)})
            total_tokens += int(value)

        if not models:
            return self.error_result("昨日无模型调用记录")
        models.sort(key=lambda m: m["total_tokens"], reverse=True)
        return CollectorResult(
            module_id=self.module_id,
            status="ok",
            data={
                "date": yesterday,
                "models": models,
                "totals": {"total_tokens": total_tokens},
            },
        )
