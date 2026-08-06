"""模板渲染测试：正常卡片、错误占位卡片、封面缺失占位、AI 额度表。"""

import pytest

from DailyMorningReport.collectors.base import CollectorResult
from DailyMorningReport.render.templates import (
    ai_quota_card,
    anime_card,
    error_card,
    dram_card,
    fx_card,
    gold_card,
    movie_card,
    news_card,
    render_ai_quota_private,
    render_group1,
    render_group2,
    render_group3,
)


def _ok(module_id: str, data: dict) -> CollectorResult:
    return CollectorResult(module_id=module_id, status="ok", data=data, fetched_at="2026-08-06")


def _err(module_id: str, msg: str = "连接超时") -> CollectorResult:
    return CollectorResult(module_id=module_id, status="error", error_msg=msg)


def test_news_card_ok(config) -> None:
    result = _ok("news", {"news": ["第一条新闻", "第二条新闻"], "tip": "今日一言"})
    html = news_card(result, limit=10)
    assert "新闻速读" in html
    assert "第一条新闻" in html
    assert "第二条新闻" in html
    assert "今日一言" in html


def test_news_card_limit(config) -> None:
    result = _ok("news", {"news": [f"新闻{i}" for i in range(20)]})
    html = news_card(result, limit=5)
    assert html.count("news-item") >= 5
    assert "新闻5" not in html


def test_error_card_rendered() -> None:
    html = error_card("tech", "科技热点", "HTTP 403")
    assert "科技热点获取失败" in html
    assert "HTTP 403" in html
    assert "error-card" in html


def test_dram_card_ok() -> None:
    result = _ok(
        "dram",
        {
            "items": [
                {"name": "DDR5 16Gb", "high": 68.0, "low": 33.0, "avg": 51.333, "change": 0.3},
                {"name": "DDR4 8Gb", "high": 74.0, "low": 20.5, "avg": 42.237, "change": -0.2},
            ]
        },
    )
    html = dram_card(result)
    assert "DDR5 16Gb" in html
    assert "51.33" in html
    assert "up" in html
    assert "down" in html


def test_dram_error_card() -> None:
    html = dram_card(_err("dram"))
    assert "DRAM 价格获取失败" in html


def test_fx_card_ok() -> None:
    result = _ok("fx", {"base": "CNY", "rates": [{"code": "USD", "rate": 0.1479}]})
    html = fx_card(result)
    assert "USD" in html
    assert "0.1479" in html


def test_gold_card_ok() -> None:
    result = _ok("gold", {"metals": [{"name": "伦敦金", "price": 4267.02, "unit": "美元/盎司"}]})
    html = gold_card(result)
    assert "伦敦金" in html
    assert "4267.02" in html


def test_ai_quota_card_ok() -> None:
    result = _ok(
        "ai_quota",
        {
            "quotas": [
                {"provider": "OpenRouter", "balance": 3.766, "currency": "USD", "note": ""},
                {"provider": "DeepSeek", "balance": 110.0, "currency": "CNY", "note": ""},
            ]
        },
    )
    html = ai_quota_card(result)
    assert "OpenRouter" in html
    assert "DeepSeek" in html
    assert "3.77" in html
    assert "110" in html


def test_ai_quota_unlimited_shows_text() -> None:
    """balance=None（按量计费无上限）显示'无上限'而非数字。"""
    result = _ok(
        "ai_quota",
        {"quotas": [{"provider": "OpenRouter", "balance": None, "currency": "USD", "note": "按量计费/无上限"}]},
    )
    html = ai_quota_card(result)
    assert "无上限" in html
    assert "-1" not in html


def test_ai_quota_error() -> None:
    html = ai_quota_card(_err("ai_quota", "未配置任何 AI 厂商 API Key"))
    assert "AI 额度获取失败" in html
    assert "未配置任何 AI 厂商 API Key" in html


def test_anime_cover_placeholder() -> None:
    result = _ok(
        "anime",
        {
            "animes": [
                {"name": "示例新番", "air_date": "2026-08-06", "score": 7.6, "image_url": "https://lain.bgm.tv/x.jpg"}
            ]
        },
    )
    html = anime_card(result, cover_base64={})
    assert "示例新番" in html
    assert "暂无图" in html  # 封面未下载时占位


def test_anime_cover_embedded() -> None:
    result = _ok(
        "anime",
        {
            "animes": [
                {"name": "示例新番", "air_date": "2026-08-06", "score": None, "image_url": "https://lain.bgm.tv/x.jpg"}
            ]
        },
    )
    html = anime_card(result, cover_base64={"https://lain.bgm.tv/x.jpg": "data:image/jpeg;base64,AAAA"})
    assert 'src="data:image/jpeg;base64,AAAA"' in html
    assert "暂无图" not in html


def test_movie_card_ok() -> None:
    result = _ok(
        "movie",
        {
            "movies": [
                {
                    "name": "去你的岛",
                    "date": "08月07日",
                    "genre": "爱情 / 动画",
                    "region": "中国大陆",
                    "wish": "5028人想看",
                    "image_url": "",
                }
            ]
        },
    )
    html = movie_card(result, cover_base64={})
    assert "去你的岛" in html
    assert "08月07日" in html
    assert "5028人想看" in html


def test_html_escaping() -> None:
    """恶意/特殊字符应被转义。"""
    result = _ok("news", {"news": ["<script>alert(1)</script>", '标题 "带引号"']})
    html = news_card(result)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_render_group1(config) -> None:
    html = render_group1(_ok("news", {"news": ["n1"]}), _ok("tech", {"titles": ["t1"]}), config)
    assert "每日早报 · 资讯速览" in html
    assert "n1" in html
    assert "t1" in html


def test_render_group2_with_public_quota(config) -> None:
    fx = _ok("fx", {"rates": [{"code": "USD", "rate": 0.1}]})
    fuel = _ok("fuel", {"region": "北京", "items": [{"name": "92#", "price": 7.97}], "trend": {}})
    gold = _ok("gold", {"metals": [{"name": "黄金", "price": 900, "unit": "元/克"}]})
    dram = _ok("dram", {"items": [{"name": "DDR5", "high": 1, "low": 1, "avg": 1, "change": 0}]})
    quota = _ok("ai_quota", {"quotas": [{"provider": "Kimi", "balance": 1.0, "currency": "CNY", "note": ""}]})
    html = render_group2(fx, fuel, gold, dram, quota, config)
    assert "每日早报 · 行情财经" in html
    assert "Kimi" in html


def test_render_group3(config) -> None:
    anime = _ok("anime", {"animes": [{"name": "新番A", "air_date": "", "score": None, "image_url": ""}]})
    movie = _ok(
        "movie", {"movies": [{"name": "电影A", "date": "", "genre": "", "region": "", "wish": "", "image_url": ""}]}
    )
    game = _ok("game", {"games": [{"name": "游戏A", "released": "", "platforms": ["PC"], "image_url": ""}]})
    html = render_group3(anime, movie, game, {}, config)
    assert "每日早报 · 文娱生活" in html
    assert "新番A" in html
    assert "电影A" in html
    assert "游戏A" in html


def test_render_ai_quota_private(config) -> None:
    result = _ok("ai_quota", {"quotas": [{"provider": "SiliconFlow", "balance": 18.0, "currency": "CNY", "note": ""}]})
    html = render_ai_quota_private(result, config)
    assert "AI 服务额度" in html
    assert "SiliconFlow" in html


@pytest.mark.asyncio
async def test_cover_manager_missing_cache(tmp_path, mock_logger) -> None:
    """缓存未命中返回 None（不崩溃）。"""
    from DailyMorningReport.render.covers import CoverManager

    manager = CoverManager(tmp_path, mock_logger, timeout=2.0)
    assert manager.load_base64("https://example.com/x.jpg") is None
    await manager.close()
