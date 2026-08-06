"""采集器解析测试：用固化的真实响应数据测各模块解析（不访问网络）。"""

import pytest

from DailyMorningReport.collectors.ai_quota import AiQuotaCollector
from DailyMorningReport.collectors.anime import AnimeCollector
from DailyMorningReport.collectors.dram import DramCollector
from DailyMorningReport.collectors.fuel import FuelCollector
from DailyMorningReport.collectors.fx import FxCollector
from DailyMorningReport.collectors.game import GameCollector
from DailyMorningReport.collectors.gold import GoldCollector
from DailyMorningReport.collectors.movie import MovieCollector
from DailyMorningReport.collectors.news import NewsCollector
from DailyMorningReport.collectors.tech import TechCollector

# ── 固化 fixture（来自 2026-08-06 现场抓取的真实响应） ──

VIKI_60S = {
    "code": 200,
    "message": "ok",
    "data": {
        "date": "2026-08-06",
        "news": [
            "中消协：2026 年上半年为消费者挽回经济损失 4.47 亿元",
            "河南出台带薪休假新政：干部带头休假",
            "国内首批高快速路迎来到期免费潮",
        ],
        "tip": "真正的自由，不是为所欲为",
        "day_of_week": "星期四",
        "lunar_date": "丙午年六月廿四",
    },
}

VIKI_FUEL = {
    "code": 200,
    "message": "ok",
    "data": {
        "region": "北京",
        "trend": {
            "next_adjustment_date": "8月14日24时",
            "direction": "下调",
            "change_ton": 120,
            "description": "下次调价时间: 8月14日24时，预计下调120元/吨",
        },
        "items": [
            {"name": "92#汽油", "price": 7.97},
            {"name": "95#汽油", "price": 8.48},
            {"name": "0#柴油", "price": 7.69},
        ],
        "updated": "2026/08/06 14:04:55",
    },
}

VIKI_GOLD = {
    "code": 200,
    "message": "ok",
    "data": {
        "date": "2026-08-06",
        "metals": [
            {"name": "黄金价格", "sell_price": "924.27", "unit": "元/克"},
            {"name": "伦敦金(现货黄金)", "sell_price": "4267.02", "unit": "美元/盎司"},
            {"name": "白银价格", "sell_price": "13.827", "unit": "元/克"},
            {"name": "铂金价格", "sell_price": "375.3", "unit": "元/克"},
        ],
    },
}

ER_API = {
    "result": "success",
    "base_code": "CNY",
    "time_last_update_utc": "Thu, 06 Aug 2026 00:02:31 +0000",
    "rates": {"CNY": 1, "USD": 0.147881, "EUR": 0.12815, "JPY": 23.33042, "HKD": 1.159924, "GBP": 0.109903},
}

ITHOME_HTML = """
<ul class="bar"><li data-id="1" class="sel">日榜</li></ul>
<ul class="bd order sel" id="d-1">
  <li><a title="余承东更正发布会口误" href="https://www.ithome.com/0/986/204.htm">余承东更正发布会口误</a></li>
  <li><a title="长鑫拒绝苹果压价" href="https://www.ithome.com/0/986/176.htm">长鑫拒绝苹果压价</a></li>
</ul>
"""

DRAMX_HTML = """
<div class="table-title"><span>国际 DRAM 颗粒现货价格($美元)</span><time>2026-08-06 11:00</time></div>
<table class="price-table">
  <tr><th>项目</th><th>盘高点</th><th>盘低点</th><th>盘平均</th><th>涨幅度</th></tr>
  <tr>
    <td class="table-list-title"><a title="SK Hynix、Samsung"> DDR5 16Gb (2Gx8) 4800/5600</a></td>
    <td>68.00</td><td>33.00</td><td>51.333</td><td><img src="/Images/stable.gif">0.00%</td>
  </tr>
  <tr>
    <td class="table-list-title"><a title="Samsung、SK Hynix、Micron"> DDR4 8Gb (1Gx8) 3200</a></td>
    <td>74.00</td><td>20.50</td><td>42.237</td><td><img src="/Images/up.png">0.30%</td>
  </tr>
</table>
"""

BGM_CALENDAR = [
    {
        "weekday": {"en": "Thu", "cn": "星期四", "ja": "木耀日", "id": 4},
        "items": [
            {
                "id": 400001,
                "url": "https://bgm.tv/subject/400001",
                "type": 2,
                "name": "Sample Anime",
                "name_cn": "示例新番",
                "air_date": "2026-08-06",
                "air_weekday": 4,
                "images": {
                    "large": "https://lain.bgm.tv/pic/cover/l/x.jpg",
                    "grid": "https://lain.bgm.tv/pic/cover/g/x.jpg",
                },
                "rating": {"total": 100, "score": 7.6},
            }
        ],
    }
]

DOUBAN_HTML = """
<div class="item mod">
  <a class="thumb" href="https://movie.douban.com/subject/35275131/">
    <img src="https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2934716566.jpg" class="" />
  </a>
  <div class="intro">
    <h3><a href="https://movie.douban.com/subject/35275131/">去你的岛</a><span class="icon"></span></h3>
    <ul>
      <li class="dt">08月07日</li>
      <li class="dt">爱情 / 动画 / 奇幻</li>
      <li class="dt">中国大陆</li>
      <li class="dt last"><span class="">5028人想看</span></li>
    </ul>
  </div>
</div>
"""

RAWG_GAMES = {
    "count": 1,
    "next": None,
    "results": [
        {
            "id": 1,
            "slug": "sample-game",
            "name": "Sample Game",
            "released": "2026-08-10",
            "background_image": "https://media.rawg.io/media/games/1.jpg",
            "platforms": [{"platform": {"name": "PC", "slug": "pc"}}],
        }
    ],
}

OPENROUTER_RESP = {"data": {"label": "sk-...AbCd", "usage": 1.234, "limit": 5.0, "is_free_tier": False}}
DEEPSEEK_RESP = {
    "is_available": True,
    "balance_infos": [
        {"currency": "CNY", "total_balance": "110.00", "granted_balance": "10.00", "topped_up_balance": "100.00"}
    ],
}
KIMI_RESP = {"data": {"available_balance": 88.5, "voucher_balance": 0, "cash_balance": 88.5}}
SILICONFLOW_RESP = {"code": 20000, "data": {"balance": 10.0, "chargeBalance": 8.0, "totalBalance": 18.0}}


# ── 工具：为采集器注入固化响应 ──


def _install(collector, json_resp=None, text_resp=None):
    """替换 fetch_json / fetch_text 为返回固化的响应。"""

    async def fake_json(url, **kwargs):
        del url, kwargs
        return json_resp

    async def fake_text(url, **kwargs):
        del url, kwargs
        return text_resp

    if json_resp is not None:
        collector.fetch_json = fake_json  # type: ignore[method-assign]
    if text_resp is not None:
        collector.fetch_text = fake_text  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_news_parse(config, mock_logger) -> None:
    collector = NewsCollector(config, mock_logger)
    _install(collector, json_resp=VIKI_60S)
    result = await collector.collect()
    assert result.status == "ok"
    assert len(result.data["news"]) == 3
    assert result.data["tip"] == "真正的自由，不是为所欲为"
    assert result.data["lunar_date"] == "丙午年六月廿四"


@pytest.mark.asyncio
async def test_fuel_parse(config, mock_logger) -> None:
    collector = FuelCollector(config, mock_logger)
    _install(collector, json_resp=VIKI_FUEL)
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["regions"][0]["region"] == "北京"
    assert result.data["regions"][0]["items"][0] == {"name": "92#汽油", "price": 7.97}
    assert result.data["trend"]["direction"] == "下调"


@pytest.mark.asyncio
async def test_fuel_multi_region(config, mock_logger) -> None:
    """多地区配置时按 region 参数分别查询。"""
    config.render.fuel_regions = ["北京", "广东"]
    collector = FuelCollector(config, mock_logger)
    seen_regions = []

    async def fake_json(url, **kwargs):
        del url
        region = kwargs.get("params", {}).get("region", "")
        seen_regions.append(region)
        return {"code": 200, "data": {"region": region, "items": [{"name": "92#汽油", "price": 7.99}]}}

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert seen_regions == ["北京", "广东"]
    assert len(result.data["regions"]) == 2


@pytest.mark.asyncio
async def test_fuel_region_failure_isolated(config, mock_logger) -> None:
    """单地区失败不影响其他地区。"""
    config.render.fuel_regions = ["北京", "广东"]
    from DailyMorningReport.collectors.base import CollectorError as CE

    collector = FuelCollector(config, mock_logger)

    async def fake_json(url, **kwargs):
        del url
        region = kwargs.get("params", {}).get("region", "")
        if region == "广东":
            raise CE("HTTP 503")
        return {"code": 200, "data": {"region": region, "items": [{"name": "92#", "price": 7.0}]}}

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert len(result.data["regions"]) == 1
    assert result.data["regions"][0]["region"] == "北京"


@pytest.mark.asyncio
async def test_gold_parse(config, mock_logger) -> None:
    collector = GoldCollector(config, mock_logger)
    _install(collector, json_resp=VIKI_GOLD)
    result = await collector.collect()
    assert result.status == "ok"
    names = [m["name"] for m in result.data["metals"]]
    assert "伦敦金(现货黄金)" in names
    assert "白银价格" in names


@pytest.mark.asyncio
async def test_fx_parse(config, mock_logger) -> None:
    collector = FxCollector(config, mock_logger)
    _install(collector, json_resp=ER_API)
    result = await collector.collect()
    assert result.status == "ok"
    codes = [r["code"] for r in result.data["rates"]]
    assert codes == ["USD", "EUR", "JPY", "HKD", "GBP"]
    usd = next(r for r in result.data["rates"] if r["code"] == "USD")
    assert usd["rate"] == pytest.approx(0.1479, abs=0.0001)


@pytest.mark.asyncio
async def test_tech_parse(config, mock_logger) -> None:
    collector = TechCollector(config, mock_logger)
    _install(collector, text_resp=ITHOME_HTML)
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["titles"] == ["余承东更正发布会口误", "长鑫拒绝苹果压价"]


@pytest.mark.asyncio
async def test_dram_parse(config, mock_logger) -> None:
    collector = DramCollector(config, mock_logger)
    _install(collector, text_resp=DRAMX_HTML)
    result = await collector.collect()
    assert result.status == "ok"
    assert result.fetched_at == "2026-08-06 11:00"
    assert len(result.data["items"]) == 2
    first = result.data["items"][0]
    assert first["name"] == "DDR5 16Gb (2Gx8) 4800/5600"
    assert first["avg"] == pytest.approx(51.333)
    assert first["change"] == 0.0
    assert result.data["items"][1]["change"] == 0.3


@pytest.mark.asyncio
async def test_anime_parse(config, mock_logger) -> None:
    collector = AnimeCollector(config, mock_logger)
    _install(collector, json_resp=BGM_CALENDAR)
    result = await collector.collect()
    # 2026-08-06 是星期四（isoweekday=4），fixture 中 weekday.id=4 应命中
    assert result.status == "ok"
    assert result.data["animes"][0]["name"] == "示例新番"
    assert result.data["animes"][0]["score"] == 7.6


@pytest.mark.asyncio
async def test_movie_parse(config, mock_logger) -> None:
    collector = MovieCollector(config, mock_logger)
    _install(collector, text_resp=DOUBAN_HTML)
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["source"] == "douban"
    movie = result.data["movies"][0]
    assert movie["name"] == "去你的岛"
    assert movie["date"] == "08月07日"
    assert movie["wish"] == "5028人想看"


TMDB_RESP = {
    "page": 1,
    "total_pages": 1,
    "results": [
        {
            "id": 1,
            "title": "TMDB 新片",
            "original_title": "TMDB Movie",
            "release_date": "2026-08-10",
            "poster_path": "/abc.jpg",
            "vote_average": 7.8,
        }
    ],
}


@pytest.mark.asyncio
async def test_movie_falls_back_to_tmdb(config, mock_logger) -> None:
    """豆瓣失败（反爬）时自动降级 TMDB。"""
    config.external_api.tmdb_api_key = "tmdb-test-key"
    collector = MovieCollector(config, mock_logger)

    # 豆瓣：403 失败（模拟真实 fetch 转成的 CollectorError）；TMDB：成功
    from DailyMorningReport.collectors.base import CollectorError as CE

    async def fake_text(url, **kwargs):
        del url, kwargs
        raise CE("HTTP 403: movie.douban.com")

    calls = {}

    async def fake_json(url, **kwargs):
        del kwargs
        calls["url"] = url
        if "themoviedb.org" in url:
            return TMDB_RESP
        raise AssertionError(f"unexpected url: {url}")

    collector.fetch_text = fake_text  # type: ignore[method-assign]
    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert result.data["source"] == "tmdb"
    movie = result.data["movies"][0]
    assert movie["name"] == "TMDB 新片"
    assert movie["score"] == 7.8
    assert movie["image_url"] == "https://image.tmdb.org/t/p/w500/abc.jpg"
    assert "primary_release_date.gte" in calls["url"]


@pytest.mark.asyncio
async def test_movie_tmdb_skipped_without_key(config, mock_logger) -> None:
    """豆瓣失败且未配置 TMDB key 时返回豆瓣错误。"""
    from DailyMorningReport.collectors.base import CollectorError as CE

    collector = MovieCollector(config, mock_logger)

    async def fake_text(url, **kwargs):
        del url, kwargs
        raise CE("HTTP 403: movie.douban.com")

    collector.fetch_text = fake_text  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "error"
    assert "豆瓣" in result.error_msg


@pytest.mark.asyncio
async def test_game_parse(config, mock_logger) -> None:
    config.external_api.rawg_api_key = "test-key"
    collector = GameCollector(config, mock_logger)
    _install(collector, json_resp=RAWG_GAMES)
    result = await collector.collect()
    assert result.status == "ok"
    game = result.data["games"][0]
    assert game["name"] == "Sample Game"
    assert game["platforms"] == ["PC"]
    assert game["image_url"].startswith("https://media.rawg.io")


@pytest.mark.asyncio
async def test_game_skipped_without_key(config, mock_logger) -> None:
    collector = GameCollector(config, mock_logger)
    result = await collector.collect()
    assert result.status == "error"
    assert "RAWG" in result.error_msg


@pytest.mark.asyncio
async def test_ai_quota_parse(config, mock_logger) -> None:
    config.ai_quota.openrouter.api_key = "sk-or-1"
    config.ai_quota.deepseek.api_key = "sk-ds-1"
    config.ai_quota.kimi.api_key = "sk-km-1"
    config.ai_quota.siliconflow.api_key = "sk-sf-1"

    collector = AiQuotaCollector(config, mock_logger)
    responses = {
        "https://openrouter.ai/api/v1/auth/key": OPENROUTER_RESP,
        "https://api.deepseek.com/user/balance": DEEPSEEK_RESP,
        "https://api.moonshot.cn/v1/users/me/balance": KIMI_RESP,
        "https://api.siliconflow.cn/v1/user/info": SILICONFLOW_RESP,
    }

    async def fake_json(url, **kwargs):
        del kwargs
        if url in responses:
            return responses[url]
        raise AssertionError(f"unexpected url: {url}")

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    by_provider = {q["provider"]: q for q in result.data["quotas"]}
    assert by_provider["OpenRouter"]["balance"] == pytest.approx(5.0 - 1.234)
    assert by_provider["DeepSeek"]["balance"] == 110.0
    assert by_provider["Kimi"]["balance"] == 88.5
    assert by_provider["SiliconFlow"]["balance"] == 18.0


@pytest.mark.asyncio
async def test_ai_quota_skips_disabled(config, mock_logger) -> None:
    config.ai_quota.deepseek.api_key = "sk-ds-1"
    config.ai_quota.openrouter.enabled = False
    collector = AiQuotaCollector(config, mock_logger)

    async def fake_json(url, **kwargs):
        del url, kwargs
        return DEEPSEEK_RESP

    collector.fetch_json = fake_json  # type: ignore[method-assign]
    result = await collector.collect()
    assert result.status == "ok"
    assert [q["provider"] for q in result.data["quotas"]] == ["DeepSeek"]
