"""新模块测试：节假日/纪念日、AI 消费汇总、早报存档。"""

import json

import pytest

from DailyMorningReport.archive import ArchiveManager
from DailyMorningReport.collectors.ai_usage import AiUsageCollector
from DailyMorningReport.collectors.base import CollectorResult
from DailyMorningReport.collectors.holiday import HolidayCollector, FIXED_HOLIDAYS
from DailyMorningReport.render.templates import ai_usage_card, holiday_card

VIKI_HISTORY = {
    "code": 200,
    "message": "ok",
    "data": {
        "month": 8,
        "day": 6,
        "items": [
            {"title": "威尼斯国际电影节创办", "year": "1932", "description": "...", "event_type": "event"},
            {"title": "弗莱明出生", "year": "1881", "description": "...", "event_type": "birth"},
            {"title": "方志敏逝世", "year": "1935", "description": "...", "event_type": "death"},
        ],
    },
}


@pytest.mark.asyncio
async def test_holiday_fixed_and_history(config, mock_logger) -> None:
    collector = HolidayCollector(config, mock_logger)

    async def fake_json(url, **kwargs):
        del url, kwargs
        return VIKI_HISTORY

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert len(result.data["history"]) == 3
    assert result.data["history"][0]["title"] == "威尼斯国际电影节创办"


def test_fixed_holidays_table() -> None:
    import datetime as dt

    assert FIXED_HOLIDAYS[(1, 1)] == "元旦"
    assert FIXED_HOLIDAYS[(10, 1)] == "国庆节"
    # 1 月 1 日应有元旦
    holidays = HolidayCollector._fixed_holidays(dt.date(2026, 1, 1))
    assert "元旦" in holidays
    # 普通日期无节日
    assert HolidayCollector._fixed_holidays(dt.date(2026, 6, 15)) == []


@pytest.mark.asyncio
async def test_holiday_history_failure_keeps_fixed(config, mock_logger) -> None:
    """历史 API 失败时节日表仍可用（不致命）。"""
    collector = HolidayCollector(config, mock_logger)

    from DailyMorningReport.collectors.base import CollectorError as CE

    async def fake_json(url, **kwargs):
        del url, kwargs
        raise CE("HTTP 503")

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["history"] == []


def test_holiday_card_renders(config) -> None:
    result = CollectorResult(
        module_id="holiday",
        status="ok",
        data={"holidays": ["国庆节"], "history": [{"title": "历史事件", "year": "1949", "event_type": "event"}]},
    )
    html = holiday_card(result)
    assert "国庆节" in html
    assert "历史事件" in html
    assert "1949年" in html


# ── AI 消费汇总 ──


class FakeLocal:
    def __init__(self, series) -> None:
        self._series = series

    async def token_trend(self, *, days: int = 7, bucket: str = "day", group_by: str = "", top_items: int = 10):
        del days, bucket, group_by, top_items
        # 模拟 SDK 解包行为：直接返回 series 内容（不含 success/series 包装）
        return self._series


class FakeStats:
    def __init__(self, series) -> None:
        self.local = FakeLocal(series)


class FakeCtxMin:
    def __init__(self, series) -> None:
        self.statistics = FakeStats(series)


@pytest.mark.asyncio
async def test_ai_usage_aggregates_yesterday(config, mock_logger) -> None:
    yesterday = (__import__("datetime").date.today() - __import__("datetime").timedelta(days=1)).isoformat()
    today = __import__("datetime").date.today().isoformat()
    # 模拟主程序 token_trend 真实返回（按日分桶，value 为 total_tokens）
    series = {
        "timestamps": [f"{yesterday} 00:00:00", f"{today} 00:00:00"],
        "values_by_key": {"gpt_4o": [165.0, 0.0], "claude": [0.0, 1998.0]},
        "labels_by_key": {"gpt_4o": "gpt-4o", "claude": "claude"},
        "total": 2163.0,
        "source_count": 2,
    }
    collector = AiUsageCollector(config, mock_logger, ctx=FakeCtxMin(series))
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["date"] == yesterday
    assert result.data["totals"]["total_tokens"] == 165  # 仅昨日
    models = result.data["models"]
    assert len(models) == 1  # claude 是今天，被过滤
    assert models[0]["model"] == "gpt-4o"
    assert models[0]["total_tokens"] == 165


@pytest.mark.asyncio
async def test_ai_usage_no_records(config, mock_logger) -> None:
    collector = AiUsageCollector(
        config, mock_logger, ctx=FakeCtxMin({"timestamps": [], "values_by_key": {}, "labels_by_key": {}})
    )
    result = await collector.collect()
    assert result.status == "error"


@pytest.mark.asyncio
async def test_ai_usage_missing_yesterday(config, mock_logger) -> None:
    """timestamps 不含昨日时返回可读错误（不崩溃）。"""
    today = __import__("datetime").date.today().isoformat()
    series = {
        "timestamps": [f"{today} 00:00:00"],
        "values_by_key": {"gpt_4o": [10.0]},
        "labels_by_key": {"gpt_4o": "gpt-4o"},
    }
    collector = AiUsageCollector(config, mock_logger, ctx=FakeCtxMin(series))
    result = await collector.collect()
    assert result.status == "error"
    assert "昨日" in result.error_msg


@pytest.mark.asyncio
async def test_ai_usage_no_ctx(config, mock_logger) -> None:
    collector = AiUsageCollector(config, mock_logger, ctx=None)
    result = await collector.collect()
    assert result.status == "error"
    assert "ctx" in result.error_msg


def test_ai_usage_card_renders(config) -> None:
    result = CollectorResult(
        module_id="ai_usage",
        status="ok",
        data={
            "date": "2026-08-05",
            "models": [{"model": "gpt-4o", "total_tokens": 1500}],
            "totals": {"total_tokens": 1500},
        },
    )
    html = ai_usage_card(result)
    assert "昨日 AI 消费" in html
    assert "gpt-4o" in html
    assert "1,500" in html


# ── 早报存档 ──


def test_archive_save_and_prune(tmp_path, mock_logger) -> None:
    manager = ArchiveManager(tmp_path, mock_logger, max_files=2)
    results = {"news": CollectorResult(module_id="news", status="ok", data={"news": ["n1"]})}
    manager.save(results)

    archive_file = tmp_path / "archive" / (__import__("datetime").date.today().isoformat() + ".json")
    assert archive_file.exists()
    payload = json.loads(archive_file.read_text(encoding="utf-8"))
    assert payload["status"]["news"] == "ok"
    assert payload["modules"]["news"]["news"] == ["n1"]


def test_archive_prunes_old(tmp_path, mock_logger) -> None:
    manager = ArchiveManager(tmp_path, mock_logger, max_files=2)
    # 造 3 个旧文件
    for i in range(3):
        d = tmp_path / "archive"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"2026-01-0{i}.json").write_text("{}", encoding="utf-8")
    manager._prune()
    remaining = list((tmp_path / "archive").glob("*.json"))
    assert len(remaining) == 2


def test_archive_save_oserror_does_not_crash(tmp_path, mock_logger) -> None:
    # data_dir 指向一个文件，mkdir 会失败
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    bad = ArchiveManager(blocker, mock_logger)
    bad.save({"news": CollectorResult(module_id="news", status="ok")})  # 不应抛异常
