"""每日早报插件入口。

每日定时采集新闻、科技热点、硬件价格、汇率、AI额度、油价金价、影视动漫、游戏发售
等数据，渲染为精美图片推送至 QQ 群。

编排流程（定时触发与 /morning_report 命令共用）：
  collect → render → push
"""

from __future__ import annotations

from typing import Any

from maibot_sdk import CONFIG_RELOAD_SCOPE_SELF, Command, MaiBotPlugin

import asyncio

from .collectors import COLLECTORS
from .collectors.base import CollectorResult
from .config_models import DailyMorningReportConfig
from .pusher import Pusher
from .render import CoverManager, render_ai_quota_private, render_group1, render_group2, render_group3
from .scheduler import DailyScheduler


class DailyMorningReportPlugin(MaiBotPlugin):
    """每日早报主插件类。"""

    config_model = DailyMorningReportConfig

    def __init__(self) -> None:
        super().__init__()
        self._scheduler: DailyScheduler | None = None
        self._collectors: list[Any] = []
        self._cover_manager: CoverManager | None = None
        self._pusher: Pusher | None = None
        self._running_lock = asyncio.Lock()

    # ── 生命周期 ──

    async def on_load(self) -> None:
        self._pusher = Pusher(self.ctx, self.ctx.logger)
        self._cover_manager = CoverManager(
            self.ctx.paths.runtime_dir, self.ctx.logger, self.config.basic.request_timeout
        )
        self._scheduler = DailyScheduler(
            timezone=self.config.basic.timezone,
            push_time=self.config.basic.push_time,
            job=self._run_daily_job,
            logger=self.ctx.logger,
        )
        if self.config.basic.enabled:
            self._scheduler.start()
        self.ctx.logger.info("每日早报插件已加载（下次推送 %s）", self.config.basic.push_time)

    async def on_unload(self) -> None:
        if self._scheduler is not None:
            await self._scheduler.stop()
            self._scheduler = None
        await self._close_collectors()
        if self._cover_manager is not None:
            await self._cover_manager.close()
            self._cover_manager = None
        self.ctx.logger.info("每日早报插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        del config_data, version
        if scope != CONFIG_RELOAD_SCOPE_SELF:
            return
        # self.config 已由 SDK 自动更新，重启调度循环使时间/开关即时生效
        if self._scheduler is not None:
            await self._scheduler.stop()
        self._scheduler = DailyScheduler(
            timezone=self.config.basic.timezone,
            push_time=self.config.basic.push_time,
            job=self._run_daily_job,
            logger=self.ctx.logger,
        )
        if self.config.basic.enabled:
            self._scheduler.start()
        self.ctx.logger.info("每日早报配置已更新并重启调度")

    # ── 编排 ──

    def _build_collectors(self) -> list[Any]:
        """按当前配置实例化采集器（每次执行重建，配置变化即生效）。"""
        return [cls(self.config, self.ctx.logger) for cls in COLLECTORS.values()]

    async def _close_collectors(self) -> None:
        for collector in self._collectors:
            try:
                await collector.close()
            except Exception:
                self.ctx.logger.exception("关闭采集器异常: %s", collector.module_id)
        self._collectors = []

    async def _run_daily_job(self) -> None:
        """完整流程：采集 → 渲染 → 推送。持锁防止定时与手动命令并发。"""
        if self._running_lock.locked():
            self.ctx.logger.info("早报生成中，跳过本次触发")
            return
        async with self._running_lock:
            await self._execute()

    async def _execute(self) -> None:
        self.ctx.logger.info("开始生成每日早报")
        self._collectors = self._build_collectors()

        # 1. 并发采集（每个模块独立失败隔离）
        results: dict[str, CollectorResult] = {}
        tasks = [asyncio.create_task(c.collect()) for c in self._collectors]
        for collector, task in zip(self._collectors, tasks, strict=True):
            try:
                results[collector.module_id] = await task
            except Exception as exc:  # 兜底：异常也不中断整体
                self.ctx.logger.exception("采集器异常: %s", collector.module_id)
                results[collector.module_id] = CollectorResult(
                    module_id=collector.module_id, status="error", error_msg=str(exc)
                )

        # 2. 渲染
        images = await self._render(results)
        if not images:
            self.ctx.logger.error("本次早报无任何可推送图片")
            return

        # 3. 推送
        group_images = images["groups"]
        private_images = images["private"]
        for group_id in self.config.basic.target_groups:
            ok, total = await self._pusher.push_group_images(group_images, group_id)
            self.ctx.logger.info("群 %s 推送完成: %d/%d", group_id, ok, total)
        if self.config.basic.admin_qq and private_images:
            for image in private_images:
                await self._pusher.push_private_image(image, self.config.basic.admin_qq)
        await self._close_collectors()
        self.ctx.logger.info("每日早报生成完成")

    async def _render(self, results: dict[str, CollectorResult]) -> dict[str, list[str]]:
        """渲染 3 组群图 + AI 额度私聊图。"""
        cfg = self.config
        groups = cfg.groups
        images: dict[str, list[str]] = {"groups": [], "private": []}

        # 组 1：资讯速览
        if groups.group1_enabled:
            html = render_group1(
                results.get("news", self._missing("news")),
                results.get("tech", self._missing("tech")),
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group1"))

        # 组 2：行情财经
        if groups.group2_enabled:
            ai_quota_public = results.get("ai_quota") if groups.ai_quota_public else None
            html = render_group2(
                results.get("fx", self._missing("fx")),
                results.get("fuel", self._missing("fuel")),
                results.get("gold", self._missing("gold")),
                results.get("dram", self._missing("dram")),
                ai_quota_public,
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group2"))

        # 组 3：文娱生活（封面下载内嵌）
        if groups.group3_enabled:
            covers = await self._collect_covers(results)
            html = render_group3(
                results.get("anime", self._missing("anime")),
                results.get("movie", self._missing("movie")),
                results.get("game", self._missing("game")),
                covers,
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group3"))

        # AI 额度私聊图（默认仅私发管理员；公开进群后不再重复私发）
        if self.config.basic.admin_qq and not groups.ai_quota_public:
            ai_quota = results.get("ai_quota")
            if ai_quota is not None and ai_quota.status == "ok":
                html = render_ai_quota_private(ai_quota, cfg)
                images["private"].append(await self._render_image(html, "ai_quota"))

        # 过滤渲染失败产生的空串，避免推送空图
        images["groups"] = [img for img in images["groups"] if img]
        images["private"] = [img for img in images["private"] if img]

        return images

    async def _render_image(self, html: str, name: str) -> str:
        """调用 ctx.render.html2png 渲染 HTML 为 PNG base64。"""
        try:
            result = await self.ctx.render.html2png(
                html,
                viewport={"width": int(self.config.render.card_width), "height": 800},
                device_scale_factor=float(self.config.render.device_scale_factor),
                full_page=True,
                wait_until="load",
                omit_background=False,
            )
            image_base64 = result.get("image_base64") or ""
            if not image_base64:
                self.ctx.logger.error("渲染 %s 返回空图片", name)
                return ""
            return image_base64
        except Exception:
            self.ctx.logger.exception("渲染 %s 异常", name)
            return ""

    async def _collect_covers(self, results: dict[str, CollectorResult]) -> dict[str, str]:
        """收集组 3 各模块封面 URL → 下载 → data URL 映射。"""
        covers: dict[str, str] = {}
        if not self.config.render.covers_enabled or self._cover_manager is None:
            return covers
        urls: list[str] = []
        for module_id in ("anime", "movie", "game"):
            result = results.get(module_id)
            if result is None or result.status != "ok":
                continue
            for item in result.data.get("animes", result.data.get("movies", result.data.get("games", []))):
                url = str(item.get("image_url") or "")
                if url:
                    urls.append(url)
        for url in urls:
            data_url = await self._cover_manager.ensure_cover(url)
            if data_url:
                covers[url] = data_url
        return covers

    @staticmethod
    def _missing(module_id: str) -> CollectorResult:
        """构造缺失模块的失败结果。"""
        return CollectorResult(module_id=module_id, status="error", error_msg="模块未执行")

    # ── 命令 ──

    @Command("morning_report", pattern=r"^/morning_report$", aliases=["/早报"])
    async def handle_morning_report(self, **kwargs: Any) -> tuple[bool, str, int]:
        stream_id = kwargs.get("stream_id", "")
        if self._running_lock.locked():
            return True, "日报生成中，请稍候", 1
        async with self._running_lock:
            await self._execute()
        if stream_id:
            try:
                await self.ctx.send.text("日报已生成并推送", stream_id)
            except Exception:
                self.ctx.logger.exception("命令文本回发异常")
        return True, "日报已生成并推送", 1


def create_plugin() -> DailyMorningReportPlugin:
    """创建插件实例。"""
    return DailyMorningReportPlugin()
