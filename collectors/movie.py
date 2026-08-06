"""电影采集器（豆瓣即将上映）。

已现场验证：带浏览器 UA + Referer 可直接抓取（2026-08 实测无验证码）。
页面结构：
  <div class="item mod">
    <a class="thumb" href="..."><img src="海报URL" /></a>
    <div class="intro">
      <h3><a href="...">片名</a></h3>
      <ul>
        <li class="dt">08月07日</li>
        <li class="dt">爱情 / 动画</li>
        <li class="dt">中国大陆</li>
        <li class="dt last"><span>5028人想看</span></li>
      </ul>
    </div>
  </div>
风险：豆瓣可能加强反爬（验证码/封禁），届时该模块渲染失败占位卡片。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseCollector, CollectorError, CollectorResult

DOUBAN_LATER_URL = "https://movie.douban.com/cinema/later/beijing/"


class MovieCollector(BaseCollector):
    """近期上映电影。"""

    module_id = "movie"
    display_name = "电影"

    async def collect(self) -> CollectorResult:
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
                data={"movies": movies},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
