"""每日定时调度器：按 push_time（本地时区）触发一次完整流程。

SDK 无内置 cron，使用 asyncio 后台任务实现。支持时区（zoneinfo）、
配置热更新重启、手动命令与定时触发共用同一执行函数（锁防并发）。
"""

from __future__ import annotations

from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

import asyncio
import datetime as dt
import logging


class DailyScheduler:
    """每日定时调度循环。"""

    def __init__(
        self,
        timezone: str,
        push_time: str,
        job: Callable[[], Awaitable[None]],
        logger: logging.Logger,
    ) -> None:
        self._timezone = timezone
        self._push_time = push_time
        self._job = job
        self._logger = logger
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """启动后台调度循环（幂等）。"""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """取消调度任务（吞掉 CancelledError）。"""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def _parse_push_time(self) -> dt.time:
        """解析 HH:MM 配置，非法时回退到 08:00。"""
        try:
            hour, minute = self._push_time.strip().split(":")
            return dt.time(int(hour), int(minute))
        except (ValueError, AttributeError):
            self._logger.warning("push_time 格式非法: %r，回退到 08:00", self._push_time)
            return dt.time(8, 0)

    @staticmethod
    def next_run(now: dt.datetime, push_time: dt.time, tz: ZoneInfo) -> dt.datetime:
        """计算下一个触发时刻：今天 HH:MM，若已过则推到明天（纯函数，便于测试）。"""
        candidate = now.replace(hour=push_time.hour, minute=push_time.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += dt.timedelta(days=1)
        return candidate

    def _resolve_tz(self) -> ZoneInfo:
        """解析时区，非法配置回退到 Asia/Shanghai。"""
        try:
            return ZoneInfo(self._timezone)
        except (KeyError, ValueError, OSError):
            self._logger.warning("时区配置非法: %r，回退到 Asia/Shanghai", self._timezone)
            return ZoneInfo("Asia/Shanghai")

    async def _run_loop(self) -> None:
        """调度主循环：睡到下一个触发时刻 → 执行任务 → 循环。"""
        tz = self._resolve_tz()
        while True:
            now = dt.datetime.now(tz)
            next_at = self.next_run(now, self._parse_push_time(), tz)
            sleep_seconds = max(0.0, (next_at - now).total_seconds())
            self._logger.info(
                "下次早报推送: %s（%d 秒后）",
                next_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
                int(sleep_seconds),
            )
            try:
                await asyncio.sleep(sleep_seconds)
            except asyncio.CancelledError:
                return
            try:
                await self._job()
            except Exception:
                self._logger.exception("定时推送执行异常，调度循环继续")
