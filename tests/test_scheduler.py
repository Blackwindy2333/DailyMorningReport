"""调度器测试：下一个触发时刻计算（含跨天）。"""

import datetime as dt
import logging
from zoneinfo import ZoneInfo

import pytest

from DailyMorningReport.scheduler import DailyScheduler

TZ = ZoneInfo("Asia/Shanghai")


def test_next_run_today_after_push_time() -> None:
    now = dt.datetime(2026, 8, 6, 7, 0, tzinfo=TZ)
    assert DailyScheduler.next_run(now, dt.time(8, 0), TZ) == dt.datetime(2026, 8, 6, 8, 0, tzinfo=TZ)


def test_next_run_today_before_push_time_crosses_day() -> None:
    now = dt.datetime(2026, 8, 6, 9, 0, tzinfo=TZ)
    assert DailyScheduler.next_run(now, dt.time(8, 0), TZ) == dt.datetime(2026, 8, 7, 8, 0, tzinfo=TZ)


def test_next_run_exact_time_not_in_past() -> None:
    now = dt.datetime(2026, 8, 6, 8, 0, 0, tzinfo=TZ)
    assert DailyScheduler.next_run(now, dt.time(8, 0), TZ) == dt.datetime(2026, 8, 7, 8, 0, tzinfo=TZ)


def test_parse_push_time_valid() -> None:
    sched = DailyScheduler("Asia/Shanghai", "09:30", lambda: None, None)
    assert sched._parse_push_time() == dt.time(9, 30)


def test_parse_push_time_invalid_falls_back() -> None:
    sched = DailyScheduler("Asia/Shanghai", "not-a-time", lambda: None, logging.getLogger("t"))
    assert sched._parse_push_time() == dt.time(8, 0)


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    async def noop() -> None:
        pass

    sched = DailyScheduler("Asia/Shanghai", "08:00", noop, logging.getLogger("t"))
    sched.start()
    task = sched._task
    assert task is not None
    sched.start()  # 再次调用不应新建任务
    assert sched._task is task
    await sched.stop()


@pytest.mark.asyncio
async def test_stop_without_start() -> None:
    async def noop() -> None:
        pass

    sched = DailyScheduler("Asia/Shanghai", "08:00", noop, logging.getLogger("t"))
    await sched.stop()
