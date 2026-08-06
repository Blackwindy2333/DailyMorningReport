"""电影采集器（双源：豆瓣主源 + TMDB 降级源）。

豆瓣（主源）：https://movie.douban.com/cinema/later/beijing/
- 已现场验证：带浏览器 UA + Referer 可直接抓取（2026-08 实测无验证码）
- 反爬风险高（验证码/封禁），失败时自动降级到 TMDB

TMDB（降级源）：GET /3/discover/movie
- 端点：https://api.themoviedb.org/3/discover/movie
- 参数：language=zh-CN & primary_release_date.gte/lte=日期 & sort_by=popularity.desc
- 认证：Authorization: Bearer <api_key>（需用户配置）
- 响应：{"page":1, "results":[{title, release_date, poster_path, overview, vote_average}], "total_pages"}
- 海报：https://image.tmdb.org/t/p/w500{poster_path}
"""

from __future__ import annotations

import datetime as dt

from bs4 import BeautifulSoup

from .base import BaseCollector, CollectorError, CollectorResult

DOUBAN_LATER_URL = "https://movie.douban.com/cinema/later/beijing/"
TMDB_DISCOVER_URL = "https://api.themoviedb.org/3/discover/movie"
TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"


class MovieCollector(BaseCollector):
    """近期上映电影（豆瓣主源，TMDB 降级）。"""

    module_id = "movie"
    display_name = "电影"

    async def collect(self) -> CollectorResult:
        # 主源：豆瓣；失败时降级 TMDB
        result = await self._collect_douban()
        if result.status == "ok":
            return result
        self.logger.info("豆瓣电影抓取失败，降级到 TMDB: %s", result.error_msg)
        tmdb_result = await self._collect_tmdb()
        if tmdb_result.status == "ok":
            return tmdb_result
        # 双源均失败：返回豆瓣的错误信息（主源优先展示）
        return result

    async def _collect_douban(self) -> CollectorResult:
        try:
            html = await self.fetch_text(
                DOUBAN_LATER_URL,
                headers={"Referer": "https://movie.douban.com/"},
            )
            soup = BeautifulSoup(html, "html.parser")
            movies = []
            for item in soup.select("div.item.mod"):
                thumb = item.select_one("a.thumb img")
                title_link = item.select_one("div.intro h3 a")
                lis = item.select("div.intro ul li.dt")
                date_text = str(lis[0].get_text(strip=True)) if len(lis) > 0 else ""
                genre_text = str(lis[1].get_text(strip=True)) if len(lis) > 1 else ""
                region_text = str(lis[2].get_text(strip=True)) if len(lis) > 2 else ""
                want_text = str(lis[3].get_text(strip=True)) if len(lis) > 3 else ""
                movies.append(
                    {
                        "name": str(title_link.get_text(strip=True)) if title_link else "",
                        "date": date_text,
                        "genre": genre_text,
                        "region": region_text,
                        "wish": want_text,
                        "image_url": str(thumb.get("src") or "") if thumb else "",
                    }
                )
            if not movies:
                raise CollectorError("豆瓣电影列表为空（可能触发反爬）")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"movies": movies, "source": "douban"},
            )
        except Exception as exc:  # 豆瓣异常统一降级（含未预料的异常类型）
            return self.error_result(f"豆瓣: {exc}")

    async def _collect_tmdb(self) -> CollectorResult:
        api_key = self.config.external_api.tmdb_api_key
        if not api_key:
            return self.error_result("TMDB 降级源未配置 API Key")
        try:
            today = dt.date.today()
            end = today + dt.timedelta(days=14)
            url = (
                f"{TMDB_DISCOVER_URL}?language=zh-CN"
                f"&primary_release_date.gte={today.isoformat()}"
                f"&primary_release_date.lte={end.isoformat()}"
                f"&sort_by=popularity.desc&include_adult=false"
            )
            payload = await self.fetch_json(url, headers={"Authorization": f"Bearer {api_key}"})
            results = payload.get("results") or []
            movies = []
            for item in results:
                poster = str(item.get("poster_path") or "")
                movies.append(
                    {
                        "name": str(item.get("title") or item.get("original_title") or ""),
                        "date": str(item.get("release_date") or ""),
                        "genre": "",
                        "region": "",
                        "wish": "",
                        "image_url": f"{TMDB_POSTER_BASE}{poster}" if poster else "",
                        "score": float(item.get("vote_average") or 0),
                    }
                )
            if not movies:
                raise CollectorError("TMDB 近期无新片数据")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"movies": movies, "source": "tmdb"},
            )
        except CollectorError as exc:
            return self.error_result(f"TMDB: {exc}")
