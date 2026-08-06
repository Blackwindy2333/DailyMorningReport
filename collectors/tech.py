"""科技热点采集器（IT之家热榜·日榜）。

已现场验证：rank.html 为静态 HTML，日榜列表在 <ul class="bd order sel" id="d-1">，
每条 <li><a title="标题" href="...">标题</a></li>。取 a 的 title 属性。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseCollector, CollectorError, CollectorResult

ITHOME_RANK_URL = "https://www.ithome.com/block/rank.html"


class TechCollector(BaseCollector):
    """IT之家热榜（日榜）。"""

    module_id = "tech"
    display_name = "科技热点"

    async def collect(self) -> CollectorResult:
        try:
            html = await self.fetch_text(ITHOME_RANK_URL)
            soup = BeautifulSoup(html, "html.parser")
            daily_list = soup.select_one("ul#d-1")
            if daily_list is None:
                raise CollectorError("IT之家日榜结构变化（找不到 #d-1）")
            titles = []
            for link in daily_list.select("li a[title]"):
                title = str(link.get("title") or "").strip()
                if title:
                    titles.append(title)
            if not titles:
                raise CollectorError("IT之家日榜标题为空")
            limit = int(getattr(self.config.render, "tech_count", 15))
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                data={"titles": titles[:limit]},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))
