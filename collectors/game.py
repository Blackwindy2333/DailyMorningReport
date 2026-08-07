"""游戏发售采集器（多数据源：RAWG / EPIC，可配置 auto 自动降级）。

数据源：
- RAWG：需 API Key，全平台数据，国内需代理
- EPIC：免 Key，国内直连，来自 Epic 商店 new-releases 模块（游戏名/发售日期/图片）

配置 `render.game_source`：
- auto（默认）：优先 EPIC（免 Key 国内直连），失败自动降级 RAWG
- rawg / epic：仅用指定源（失败不降级，尊重用户选择）
"""

from __future__ import annotations

import datetime as dt
import logging
from abc import ABC, abstractmethod
from typing import Any

from .base import BaseCollector, CollectorError, CollectorResult

RAWG_API_URL = "https://api.rawg.io/api/games"
EPIC_LAYOUT_URL = (
    "https://store-site-backend-static-ipv4.ak.epicgames.com/storefrontLayout"
    "?locale=zh-CN&country=CN"
)
_EPIC_NEW_RELEASES_MODULE = "branded-list-new-releases"


class GameSource(ABC):
    """游戏发售数据源抽象基类，统一输出近期发售游戏列表。"""

    source_id: str = ""

    def __init__(self, collector: BaseCollector, config: Any) -> None:
        self._c = collector  # 复用 BaseCollector 的 fetch_json/_today/日志
        self.config = config

    @abstractmethod
    async def fetch_upcoming(self, days: int) -> list[dict]:
        """返回近期发售游戏列表：[{name, released, platforms, image_url}]。"""
        raise NotImplementedError


class RawgSource(GameSource):
    """RAWG API 源（需 key）。"""

    source_id = "rawg"

    async def fetch_upcoming(self, days: int) -> list[dict]:
        api_key = self.config.external_api.rawg_api_key
        if not api_key:
            raise CollectorError("未配置 RAWG API Key")
        today = self._c._today()
        end = today + dt.timedelta(days=days)
        params = {
            "key": api_key,
            "dates": f"{today.isoformat()},{end.isoformat()}",
            "ordering": "-added",
            "page_size": 10,
        }
        payload = await self._c.fetch_json(RAWG_API_URL, params=params)
        results = payload.get("results") or []
        games = []
        for item in results:
            platforms = [
                str(plat_obj.get("name") or "")
                for plat in (item.get("platforms") or [])
                if isinstance(plat, dict) and isinstance(plat_obj := plat.get("platform"), dict)
            ]
            games.append(
                {
                    "name": str(item.get("name") or ""),
                    "released": str(item.get("released") or ""),
                    "platforms": [p for p in platforms if p],
                    "image_url": str(item.get("background_image") or ""),
                }
            )
        return games


class EpicSource(GameSource):
    """Epic 商店 new-releases 模块源（免 key，国内直连）。"""

    source_id = "epic"

    async def fetch_upcoming(self, days: int) -> list[dict]:
        payload = await self._c.fetch_json(EPIC_LAYOUT_URL)
        modules = (
            payload.get("data", {})
            .get("Storefront", {})
            .get("storefrontModulesPaginated", {})
            .get("modules", [])
        )
        games = []
        for mod in modules:
            if mod.get("id") != _EPIC_NEW_RELEASES_MODULE:
                continue
            for offer_blob in mod.get("offers", []) or []:
                if not isinstance(offer_blob, dict):
                    continue
                offer = offer_blob.get("offer") or offer_blob
                title = str(offer.get("title") or "")
                if not title:
                    continue
                released = str(
                    offer.get("releaseDate") or offer.get("pcReleaseDate") or ""
                )
                if released:
                    released = released[:10]  # 取 YYYY-MM-DD
                image_url = ""
                for key_image in offer.get("keyImages", []) or []:
                    if key_image.get("type") in ("OfferImageWide", "DieselStoreFrontWide"):
                        image_url = str(key_image.get("url") or "")
                        break
                games.append(
                    {
                        "name": title,
                        "released": released,
                        "platforms": ["PC"],
                        "image_url": image_url,
                    }
                )
        return games


class GameCollector(BaseCollector):
    """近期发售新游（多数据源）。"""

    module_id = "game"
    display_name = "游戏发售"

    def __init__(self, config: Any, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self._days = int(getattr(config.render, "game_days", 7))

    def _source_order(self) -> list[GameSource]:
        """按配置计算数据源顺序（auto 时 epic 优先，失败降级 rawg）。"""
        selected = str(getattr(self.config.render, "game_source", "auto") or "auto")
        if selected == "epic":
            return [EpicSource(self, self.config)]
        if selected == "rawg":
            return [RawgSource(self, self.config)]
        # auto：EPIC 免 key 国内直连优先
        return [EpicSource(self, self.config), RawgSource(self, self.config)]

    async def collect(self) -> CollectorResult:
        sources = self._source_order()
        errors: list[str] = []
        for source in sources:
            try:
                games = await source.fetch_upcoming(self._days)
                if games:
                    return CollectorResult(
                        module_id=self.module_id,
                        status="ok",
                        data={"games": games, "source": source.source_id},
                    )
                errors.append(f"{source.source_id}: 近期待发售无数据")
            except CollectorError as exc:
                errors.append(f"{source.source_id}: {exc}")
                self.logger.warning("游戏发售源 %s 失败: %s", source.source_id, exc)
            except Exception as exc:
                errors.append(f"{source.source_id}: {exc}")
                self.logger.exception("游戏发售源 %s 异常", source.source_id)
        return self.error_result("全部数据源失败: " + "; ".join(errors))