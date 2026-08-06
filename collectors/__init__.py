"""采集器注册表：模块 ID -> 采集器类。"""

from .ai_quota import AiQuotaCollector
from .anime import AnimeCollector
from .base import BaseCollector, CollectorResult
from .dram import DramCollector
from .fuel import FuelCollector
from .fx import FxCollector
from .game import GameCollector
from .gold import GoldCollector
from .movie import MovieCollector
from .news import NewsCollector
from .tech import TechCollector

COLLECTORS: dict[str, type[BaseCollector]] = {
    cls.module_id: cls
    for cls in (
        NewsCollector,
        TechCollector,
        DramCollector,
        FxCollector,
        AiQuotaCollector,
        AnimeCollector,
        MovieCollector,
        GameCollector,
        FuelCollector,
        GoldCollector,
    )
}

__all__ = ["BaseCollector", "CollectorResult", "COLLECTORS"]
