"""每日早报插件入口。

每日定时采集新闻、科技热点、硬件价格、汇率、AI额度、油价金价、影视动漫、游戏发售
等数据，渲染为精美图片推送至 QQ 群。
"""

from __future__ import annotations

import asyncio
from typing import Any

from maibot_sdk import Command, MaiBotPlugin

from .config_models import DailyMorningReportConfig


class DailyMorningReportPlugin(MaiBotPlugin):
    """每日早报主插件类。"""

    config_model = DailyMorningReportConfig

    def __init__(self) -> None:
        super().__init__()
        self._scheduler_task: asyncio.Task | None = None
        self._running_lock = asyncio.Lock()

    # ── 生命周期 ──

    async def on_load(self) -> None:
        self.ctx.logger.info("每日早报插件已加载")

    async def on_unload(self) -> None:
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        self.ctx.logger.info("每日早报插件已卸载")

    async def on_config_update(
        self, scope: str, config_data: dict[str, Any], version: str
    ) -> None:
        del config_data, version
        if scope == "self":
            self.ctx.logger.info("每日早报配置已更新，重启定时调度")
            # 配置热更新：重启调度循环（Phase 6 实现具体逻辑）

    # ── 命令 ──

    @Command("morning_report", pattern=r"^/morning_report$", aliases=["/早报"])
    async def handle_morning_report(self, **kwargs: Any) -> tuple[bool, str, int]:
        del kwargs
        return True, "日报已生成并推送", 1


def create_plugin() -> DailyMorningReportPlugin:
    """创建插件实例。"""
    return DailyMorningReportPlugin()
