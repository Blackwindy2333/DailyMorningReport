"""HTML 模板：把 CollectorResult 渲染为三组长图 HTML + AI 额度私聊图 HTML。

设计：白底圆角卡片风格，容器宽度 card_width，每个模块一张卡片；
失败模块渲染醒目占位卡片。全部使用 f-string 生成（不引入 jinja2）。
"""

from __future__ import annotations

import html as html_mod
from typing import Any

from ..collectors.base import CollectorResult
from .fonts import get_font_faces, get_font_stack


def _esc(value: Any) -> str:
    """HTML 转义（防注入）。"""
    return html_mod.escape(str(value), quote=True)


def _num(value: Any, digits: int = 2) -> str:
    """数值格式化：保留 digits 位小数并去尾零。"""
    try:
        return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "-"


def render_page(
    title: str,
    subtitle: str,
    cards: list[str],
    card_width: int = 750,
) -> str:
    """组装完整 HTML 文档。"""
    body = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<style>
  {get_font_faces()}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {card_width}px;
    background: #f4f6f8;
    font-family: {get_font_stack()};
    color: #1f2937;
    padding: 20px 16px 28px;
  }}
  .header {{
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #3b82f6 100%);
    border-radius: 16px;
    color: #ffffff;
    padding: 24px 26px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.18);
  }}
  .header h1 {{ font-size: 27px; font-weight: 800; letter-spacing: 0.5px; }}
  .header p {{ font-size: 13px; opacity: 0.9; margin-top: 7px; }}
  .card {{
    background: #ffffff;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 10px rgba(31, 41, 55, 0.07);
    border: 1px solid #f1f5f9;
  }}
  .card h2 {{
    font-size: 18px;
    font-weight: 700;
    color: #1e3a8a;
    padding-bottom: 10px;
    margin-bottom: 12px;
    border-bottom: 2px solid #e5e7eb;
    display: flex;
    align-items: baseline;
  }}
  .card h2 .time {{ font-size: 12px; font-weight: 400; color: #9ca3af; margin-left: auto; }}
  .sub-title {{ font-size: 13px; font-weight: 600; color: #374151; margin: 12px 0 4px; }}
  .error-card {{
    background: #fff7ed;
    border: 1px solid #fdba74;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 16px;
  }}
  .error-card h2 {{ color: #c2410c; font-size: 16px; margin-bottom: 8px; }}
  .error-card p {{ color: #9a3412; font-size: 13px; }}
  .news-item {{ display: flex; align-items: baseline; padding: 7px 0; border-bottom: 1px dashed #f3f4f6; }}
  .news-item:last-child {{ border-bottom: none; }}
  .news-item .idx {{ flex: none; width: 26px; color: #3b82f6; font-weight: 700; font-size: 14px; }}
  .news-item .txt {{ font-size: 14px; line-height: 1.55; }}
  .tip {{ background: #eff6ff; border-radius: 10px; padding: 10px 14px; font-size: 13px; color: #1e40af; margin-top: 10px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 6px; text-align: left; border-bottom: 1px solid #f3f4f6; }}
  th {{ color: #6b7280; font-weight: 600; font-size: 12px; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .up {{ color: #dc2626; }}
  .down {{ color: #16a34a; }}
  .movie-item {{ display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px dashed #f3f4f6; }}
  .movie-item:last-child {{ border-bottom: none; }}
  .movie-item img {{ width: 64px; height: 90px; object-fit: cover; border-radius: 6px; flex: none; }}
  .movie-item .meta {{ flex: 1; }}
  .movie-item .name {{ font-size: 15px; font-weight: 600; }}
  .movie-item .tags {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  .game-item {{ display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px dashed #f3f4f6; }}
  .game-item:last-child {{ border-bottom: none; }}
  .game-item img {{ width: 88px; height: 50px; object-fit: cover; border-radius: 6px; flex: none; }}
  .game-item .meta {{ flex: 1; }}
  .game-item .name {{ font-size: 15px; font-weight: 600; }}
  .game-item .tags {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  .anime-item {{ display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px dashed #f3f4f6; }}
  .anime-item:last-child {{ border-bottom: none; }}
  .anime-item img {{ width: 64px; height: 90px; object-fit: cover; border-radius: 6px; flex: none; }}
  .anime-item .meta {{ flex: 1; }}
  .anime-item .name {{ font-size: 15px; font-weight: 600; }}
  .anime-item .tags {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
  .img-placeholder {{
    width: 64px; height: 90px; border-radius: 6px; flex: none;
    background: #e5e7eb; display: flex; align-items: center; justify-content: center;
    color: #9ca3af; font-size: 11px;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{_esc(title)}</h1>
    <p>{_esc(subtitle)}</p>
  </div>
{body}
</body>
</html>
"""


def error_card(module_id: str, display_name: str, error_msg: str) -> str:
    """失败模块占位卡片。"""
    return f"""  <div class="error-card">
    <h2>⚠️ {_esc(display_name)}获取失败</h2>
    <p>{_esc(error_msg)}</p>
  </div>"""


def card_wrapper(module_id: str, display_name: str, fetched_at: str, inner: str) -> str:
    """标准卡片外壳。"""
    time_html = f'<span class="time">{_esc(fetched_at)}</span>' if fetched_at else ""
    return f"""  <div class="card">
    <h2>{_esc(display_name)}{time_html}</h2>
{inner}
  </div>"""


def news_card(result: CollectorResult, limit: int = 10) -> str:
    """新闻速读卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "新闻速读", result.error_msg)
    data = result.data
    items = "".join(
        f'    <div class="news-item"><span class="idx">{i + 1}</span><span class="txt">{_esc(text)}</span></div>'
        for i, text in enumerate(data.get("news", [])[:limit])
    )
    tip = data.get("tip") or ""
    tip_html = f'    <div class="tip">💡 {_esc(tip)}</div>' if tip else ""
    extra = ""
    if data.get("day_of_week"):
        extra = f" · {_esc(data['day_of_week'])}"
    if data.get("lunar_date"):
        extra += f" · {_esc(data['lunar_date'])}"
    inner = f"{items}{tip_html}"
    return card_wrapper(result.module_id, "新闻速读" + extra, result.fetched_at, inner)


def tech_card(result: CollectorResult, limit: int = 15) -> str:
    """科技热点卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "科技热点", result.error_msg)
    items = "".join(
        f'    <div class="news-item"><span class="idx">{i + 1}</span><span class="txt">{_esc(text)}</span></div>'
        for i, text in enumerate(result.data.get("titles", [])[:limit])
    )
    return card_wrapper(result.module_id, "科技热点", result.fetched_at, items)


def dram_card(result: CollectorResult) -> str:
    """DRAM 价格卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "DRAM 价格", result.error_msg)
    rows = "".join(
        f"    <tr><td>{_esc(item['name'])}</td>"
        f'<td class="num">{_num(item["avg"])}</td>'
        f'<td class="num">{_num(item["high"])}</td>'
        f'<td class="num">{_num(item["low"])}</td>'
        f'<td class="num {_change_class(item["change"])}">{_num(item["change"])}%</td></tr>'
        for item in result.data.get("items", [])
    )
    inner = f"""    <table>
      <tr><th>颗粒型号</th><th class="num">均价</th><th class="num">高点</th><th class="num">低点</th><th class="num">涨跌</th></tr>
{rows}
    </table>"""
    return card_wrapper(result.module_id, "DRAM 颗粒现货价（美元）", result.fetched_at, inner)


def fx_card(result: CollectorResult) -> str:
    """汇率卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "实时汇率", result.error_msg)
    rows = "".join(
        f'    <tr><td>{_esc(item["code"])}</td><td class="num">{_num(item["rate"], 4)}</td></tr>'
        for item in result.data.get("rates", [])
    )
    inner = f"""    <table>
      <tr><th>币种</th><th class="num">1 CNY =</th></tr>
{rows}
    </table>"""
    return card_wrapper(result.module_id, "实时汇率（CNY 基准）", result.fetched_at, inner)


def fuel_card(result: CollectorResult) -> str:
    """油价卡片（多地区）。"""
    if result.status == "error":
        return error_card(result.module_id, "油价", result.error_msg)
    regions = result.data.get("regions") or []
    blocks = []
    for region in regions:
        rows = "".join(
            f'    <tr><td>{_esc(item["name"])}</td><td class="num">{_num(item["price"])} 元/升</td></tr>'
            for item in region.get("items", [])
        )
        blocks.append(
            f"""    <div class="sub-title">📍 {_esc(region.get("region") or "")}</div>
    <table>
      <tr><th>油品</th><th class="num">价格</th></tr>
{rows}
    </table>"""
        )
    trend = result.data.get("trend") or {}
    trend_desc = trend.get("description") or ""
    trend_html = f'    <div class="tip">⛽ {_esc(trend_desc)}</div>' if trend_desc else ""
    inner = "\n".join(blocks) + ("\n" + trend_html if trend_html else "")
    return card_wrapper(result.module_id, "油价", result.fetched_at, inner)


def gold_card(result: CollectorResult) -> str:
    """金价卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "金价", result.error_msg)
    rows = "".join(
        f'    <tr><td>{_esc(item["name"])}</td><td class="num">{_num(item["price"])} {_esc(item["unit"])}</td></tr>'
        for item in result.data.get("metals", [])
    )
    inner = f"""    <table>
      <tr><th>品种</th><th class="num">价格</th></tr>
{rows}
    </table>"""
    return card_wrapper(result.module_id, "金价", result.fetched_at, inner)


def ai_quota_card(result: CollectorResult, public: bool = False) -> str:
    """AI 额度卡片（私聊图 / 公开图共用）。"""
    if result.status == "error":
        return error_card(result.module_id, "AI 额度", result.error_msg)
    rows = "".join(
        f"    <tr><td>{_esc(q['provider'])}</td>"
        f'<td class="num">{_quota_balance(q["balance"])} {_esc(q["currency"])}</td>'
        f"<td>{_esc(q.get('note') or '')}</td></tr>"
        for q in result.data.get("quotas", [])
    )
    inner = f"""    <table>
      <tr><th>服务商</th><th class="num">余额</th><th>备注</th></tr>
{rows}
    </table>"""
    return card_wrapper(result.module_id, "AI 额度", result.fetched_at, inner)


def ai_usage_card(result: CollectorResult) -> str:
    """昨日 AI 消费卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "昨日 AI 消费", result.error_msg)
    rows = "".join(
        f'    <tr><td>{_esc(item["model"])}</td><td class="num">{_fmt_tokens(item["total_tokens"])}</td></tr>'
        for item in result.data.get("models", [])
    )
    totals = result.data.get("totals") or {}
    inner = f"""    <table>
      <tr><th>模型</th><th class="num">Tokens</th></tr>
{rows}
    </table>
    <div class="tip">昨日共消耗 {_fmt_tokens(totals.get("total_tokens", 0))} Tokens</div>"""
    return card_wrapper(
        result.module_id, f"昨日 AI 消费（{_esc(result.data.get('date') or '')}）", result.fetched_at, inner
    )


def _fmt_tokens(value: Any) -> str:
    """Token 数量格式化（千分位）。"""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def _quota_balance(balance: Any) -> str:
    """余额显示：None（无上限）显示为'无上限'。"""
    if balance is None:
        return "无上限"
    return _num(balance)


def anime_card(result: CollectorResult, cover_base64: dict[str, str]) -> str:
    """新番卡片（封面 data URL 由调用方传入）。"""
    if result.status == "error":
        return error_card(result.module_id, "新番放送", result.error_msg)
    items = []
    for anime in result.data.get("animes", []):
        img = _cover_img(anime.get("image_url") or "", cover_base64, "anime")
        score = ""
        if anime.get("score") is not None:
            score = f" · ⭐ {_num(anime['score'])}"
        items.append(
            f'    <div class="anime-item">{img}'
            f'<div class="meta"><div class="name">{_esc(anime["name"])}</div>'
            f'<div class="tags">{_esc(anime.get("air_date") or "")}{score}</div></div></div>'
        )
    return card_wrapper(result.module_id, "今日新番", result.fetched_at, "\n".join(items))


def movie_card(result: CollectorResult, cover_base64: dict[str, str]) -> str:
    """电影卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "电影", result.error_msg)
    source = result.data.get("source", "douban")
    title = "近期上映" if source == "douban" else "近期上映（TMDB）"
    items = []
    for movie in result.data.get("movies", []):
        img = _cover_img(movie.get("image_url") or "", cover_base64, "movie")
        score = ""
        if movie.get("score"):
            score = f" · ⭐ {_num(movie['score'])}"
        tags = " / ".join(str(movie.get(k) or "") for k in ("date", "genre", "region", "wish") if movie.get(k))
        items.append(
            f'    <div class="movie-item">{img}'
            f'<div class="meta"><div class="name">{_esc(movie["name"])}{score}</div>'
            f'<div class="tags">{_esc(tags)}</div></div></div>'
        )
    return card_wrapper(result.module_id, title, result.fetched_at, "\n".join(items))


def game_card(result: CollectorResult, cover_base64: dict[str, str]) -> str:
    """游戏发售卡片。"""
    if result.status == "error":
        return error_card(result.module_id, "游戏发售", result.error_msg)
    items = []
    for game in result.data.get("games", []):
        img = _cover_img(game.get("image_url") or "", cover_base64, "game")
        tags = " / ".join(str(game.get(k) or "") for k in ("released", "platforms") if game.get(k))
        items.append(
            f'    <div class="game-item">{img}'
            f'<div class="meta"><div class="name">{_esc(game["name"])}</div>'
            f'<div class="tags">{_esc(tags)}</div></div></div>'
        )
    return card_wrapper(result.module_id, "近期新游", result.fetched_at, "\n".join(items))


def _cover_img(url: str, cover_base64: dict[str, str], kind: str) -> str:
    """封面图 HTML：有 data URL 用 img，否则占位色块。"""
    data_url = cover_base64.get(url)
    if data_url:
        return f'<img src="{data_url}" alt="" />'
    return '<div class="img-placeholder">暂无图</div>'


def _change_class(change: float) -> str:
    """涨跌颜色 class。"""
    if change > 0:
        return "up"
    if change < 0:
        return "down"
    return ""


def holiday_card(result: CollectorResult, history_limit: int = 6) -> str:
    """今日节日/纪念日卡片（组 1 顶部）。"""
    if result.status == "error":
        return error_card(result.module_id, "今日提醒", result.error_msg)
    holidays = result.data.get("holidays") or []
    history = result.data.get("history") or []
    lines: list[str] = []
    if holidays:
        lines.append(f'    <div class="tip">🎉 今日节日：{"、".join(_esc(h) for h in holidays)}</div>')
    history_lines = []
    for event in history[:history_limit]:
        year = f"[{_esc(event['year'])}年]" if event.get("year") else ""
        history_lines.append(
            f'    <div class="news-item"><span class="idx">{len(history_lines) + 1}</span>'
            f'<span class="txt">{year} {_esc(event["title"])}</span></div>'
        )
    inner = "\n".join(lines + history_lines)
    if not inner.strip():
        inner = '    <div class="tip">今日无特别节日或历史事件</div>'
    return card_wrapper(result.module_id, "今日提醒", result.fetched_at, inner)


def render_group1(
    news_result: CollectorResult,
    tech_result: CollectorResult,
    holiday_result: CollectorResult | None,
    enabled_modules: set[str],
    config: Any,
) -> str:
    """组 1 资讯速览：节日提醒 + 新闻 + 科技。

    enabled_modules: 启用的模块 ID 集合，禁用的模块不渲染其卡片。
    """
    cards = []
    if holiday_result is not None and "holiday" in enabled_modules:
        cards.append(holiday_card(holiday_result))
    if "news" in enabled_modules:
        cards.append(news_card(news_result, limit=int(getattr(config.render, "news_count", 10))))
    if "tech" in enabled_modules:
        cards.append(tech_card(tech_result, limit=int(getattr(config.render, "tech_count", 15))))
    return render_page(
        title="每日早报 · 资讯速览",
        subtitle="新闻速读与科技热点",
        cards=cards,
        card_width=int(getattr(config.render, "card_width", 750)),
    )


def render_group2(
    fx_result: CollectorResult,
    fuel_result: CollectorResult,
    gold_result: CollectorResult,
    dram_result: CollectorResult,
    ai_quota_result: CollectorResult | None,
    ai_usage_result: CollectorResult | None,
    enabled_modules: set[str],
    config: Any,
) -> str:
    """组 2 行情财经：汇率 + 油价 + 金价 + DRAM（+ 公开 AI 额度 + 昨日 AI 消费）。"""
    cards = []
    if "fx" in enabled_modules:
        cards.append(fx_card(fx_result))
    if "fuel" in enabled_modules:
        cards.append(fuel_card(fuel_result))
    if "gold" in enabled_modules:
        cards.append(gold_card(gold_result))
    if "dram" in enabled_modules:
        cards.append(dram_card(dram_result))
    if ai_quota_result is not None and "ai_quota" in enabled_modules:
        cards.append(ai_quota_card(ai_quota_result, public=True))
    if ai_usage_result is not None and "ai_usage" in enabled_modules:
        cards.append(ai_usage_card(ai_usage_result))
    return render_page(
        title="每日早报 · 行情财经",
        subtitle="汇率、油价、金价与硬件行情",
        cards=cards,
        card_width=int(getattr(config.render, "card_width", 750)),
    )


def render_group3(
    anime_result: CollectorResult,
    movie_result: CollectorResult,
    game_result: CollectorResult,
    cover_base64: dict[str, str],
    enabled_modules: set[str],
    config: Any,
) -> str:
    """组 3 文娱生活：新番 + 电影 + 游戏。"""
    cards = []
    if "anime" in enabled_modules:
        cards.append(anime_card(anime_result, cover_base64))
    if "movie" in enabled_modules:
        cards.append(movie_card(movie_result, cover_base64))
    if "game" in enabled_modules:
        cards.append(game_card(game_result, cover_base64))
    return render_page(
        title="每日早报 · 文娱生活",
        subtitle="新番、电影与游戏",
        cards=cards,
        card_width=int(getattr(config.render, "card_width", 750)),
    )


def render_ai_quota_private(ai_quota_result: CollectorResult, config: Any) -> str:
    """AI 额度私聊图。"""
    return render_page(
        title="AI 服务额度",
        subtitle="各厂商 API 余额（请及时充值）",
        cards=[ai_quota_card(ai_quota_result)],
        card_width=int(getattr(config.render, "card_width", 750)),
    )
