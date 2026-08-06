"""DRAM 颗粒现货价采集器（DRAMeXchange）。

已现场验证：DSD.html 为 UTF-8 静态页面，
<table class="price-table"> 内每行 <tr>：
  <td class="table-list-title"><a title="厂商"> DDR5 16Gb (2Gx8) 4800/5600</a></td>
  <td>盘高点</td> <td>盘低点</td> <td>盘平均</td> <td><img>0.00%</td>
更新时间在 <div class="table-title"><time>2026-08-06 11:00</time></div>。
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from .base import BaseCollector, CollectorError, CollectorResult

DRAMX_URL = "https://www.dramx.com/Price/DSD.html"


class DramCollector(BaseCollector):
    """国际 DRAM 颗粒现货价格。"""

    module_id = "dram"
    display_name = "DRAM 价格"

    async def collect(self) -> CollectorResult:
        try:
            html = await self.fetch_text(DRAMX_URL)
            soup = BeautifulSoup(html, "html.parser")

            time_tag = soup.select_one(".table-title time")
            updated_at = str(time_tag.get_text(strip=True)) if time_tag else ""

            table = soup.select_one("table.price-table")
            if table is None:
                raise CollectorError("DRAM 表格结构变化（找不到 price-table）")
            items = []
            for row in table.select("tr"):
                title_cell = row.select_one("td.table-list-title")
                if title_cell is None:
                    continue
                name = str(title_cell.get_text(" ", strip=True))
                cells = row.select("td")
                if len(cells) < 4:
                    continue
                high = _to_float(cells[1].get_text(strip=True))
                low = _to_float(cells[2].get_text(strip=True))
                avg = _to_float(cells[3].get_text(strip=True))
                change_text = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                change = _parse_change(change_text)
                items.append(
                    {
                        "name": name,
                        "high": high,
                        "low": low,
                        "avg": avg,
                        "change": change,
                    }
                )
            if not items:
                raise CollectorError("DRAM 数据行为空")
            return CollectorResult(
                module_id=self.module_id,
                status="ok",
                fetched_at=updated_at,
                data={"items": items},
            )
        except CollectorError as exc:
            return self.error_result(str(exc))


def _to_float(text: str) -> float:
    """解析表格数值，解析失败返回 0.0。"""
    try:
        return float(text.strip().replace(",", ""))
    except ValueError:
        return 0.0


def _parse_change(text: str) -> float:
    """解析涨幅度文本（如 "0.30%" / "0.00%"），返回数值（百分数）。"""
    stripped = text.strip().replace("%", "")
    try:
        return float(stripped)
    except ValueError:
        return 0.0
