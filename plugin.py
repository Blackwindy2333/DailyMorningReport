"""每日早报插件入口。

每日定时采集新闻、科技热点、硬件价格、汇率、AI额度、油价金价、影视动漫、游戏发售
等数据，渲染为精美图片推送至 QQ 群。

编排流程（定时触发与 /morning_report 命令共用）：
  collect → render → push

日志：保留 SDK 插件 logger（ctx.logger）+ 独立滚动文件日志（data_dir/logs），双通道并行。
模块开关：config.modules 中关闭的模块不采集、不渲染；组内全部关闭则整图跳过。
"""

from __future__ import annotations

from typing import Any

from maibot_sdk import CONFIG_RELOAD_SCOPE_SELF, Command, MaiBotPlugin

import asyncio
import datetime as dt
import time

from .archive import ArchiveManager
from .collectors import COLLECTORS
from .collectors.base import CollectorResult
from .config_models import DailyMorningReportConfig
from .log_config import close_file_handler, log_run_summary, setup_plugin_file_logging
from .pusher import Pusher
from .render import CoverManager, render_ai_quota_private, render_group1, render_group2, render_group3
from .scheduler import DailyScheduler

# 模块 -> 归属组（决定模块开关与组的关系）
_GROUP1_MODULES = ("holiday", "news", "tech")
_GROUP2_MODULES = ("fx", "fuel", "gold", "dram", "ai_usage")
_GROUP3_MODULES = ("anime", "movie", "game")
# 模块 -> 配置开关字段名（config.modules.<field>）
_MODULE_SWITCH_FIELD = {
    "holiday": "holiday_enabled",
    "news": "news_enabled",
    "tech": "tech_enabled",
    "fx": "fx_enabled",
    "fuel": "fuel_enabled",
    "gold": "gold_enabled",
    "dram": "dram_enabled",
    "ai_usage": "ai_usage_enabled",
    "anime": "anime_enabled",
    "movie": "movie_enabled",
    "game": "game_enabled",
    "ai_quota": "ai_quota_enabled",
}


class DailyMorningReportPlugin(MaiBotPlugin):
    """每日早报主插件类。"""

    config_model = DailyMorningReportConfig

    def __init__(self) -> None:
        super().__init__()
        self._scheduler: DailyScheduler | None = None
        self._collectors: list[Any] = []
        self._cover_manager: CoverManager | None = None
        self._pusher: Pusher | None = None
        self._archive: ArchiveManager | None = None
        self._running_lock = asyncio.Lock()

    # ── 生命周期 ──

    async def on_load(self) -> None:
        # 双通道日志：保留 ctx.logger（主进程转发）+ 独立滚动文件
        setup_plugin_file_logging(self.ctx.logger, self.ctx.paths.data_dir)
        self._pusher = Pusher(self.ctx, self.ctx.logger)
        self._cover_manager = CoverManager(
            self.ctx.paths.runtime_dir, self.ctx.logger, self.config.basic.request_timeout
        )
        self._archive = ArchiveManager(self.ctx.paths.data_dir, self.ctx.logger)
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
        close_file_handler(self.ctx.logger)  # 关闭独立文件日志，释放句柄
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

    def _module_enabled(self, module_id: str) -> bool:
        """模块开关：关掉的模块不采集、不渲染。"""
        field = _MODULE_SWITCH_FIELD.get(module_id)
        if field is None:
            return True
        return bool(getattr(self.config.modules, field))

    def _enabled_group_modules(self, group_modules: tuple[str, ...]) -> set[str]:
        """组内启用的模块集合（执行时按模块开关推导，决定组是否渲染）。"""
        return {module_id for module_id in group_modules if self._module_enabled(module_id)}

    def _build_collectors(self) -> list[Any]:
        """按当前配置实例化采集器（每次执行重建，配置变化即生效）。

        被模块开关关闭的采集器不实例化 —— 完全不做网络请求。
        """
        from .collectors.ai_usage import AiUsageCollector

        collectors = []
        for module_id, cls in COLLECTORS.items():
            if not self._module_enabled(module_id):
                self.ctx.logger.info("模块 %s 已被禁用，跳过采集", module_id)
                continue
            # ai_usage 依赖 ctx.statistics，单独注入上下文
            if cls is AiUsageCollector:
                collectors.append(cls(self.config, self.ctx.logger, ctx=self.ctx))
            else:
                collectors.append(cls(self.config, self.ctx.logger))
        return collectors

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
        run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        started = time.perf_counter()
        self.ctx.logger.info("[run=%s] 开始生成每日早报", run_id)

        # 1. 并发采集（每个模块独立失败隔离；被禁用的模块不采集）
        self._collectors = self._build_collectors()
        results: dict[str, CollectorResult] = {}
        collect_started = time.perf_counter()
        tasks = [asyncio.create_task(c.collect()) for c in self._collectors]
        for collector, task in zip(self._collectors, tasks, strict=True):
            try:
                results[collector.module_id] = await task
            except Exception as exc:  # 兜底：异常也不中断整体
                self.ctx.logger.exception("[run=%s] 采集器异常: %s", run_id, collector.module_id)
                results[collector.module_id] = CollectorResult(
                    module_id=collector.module_id, status="error", error_msg=str(exc)
                )
        collect_seconds = time.perf_counter() - collect_started
        ok_modules = sum(1 for r in results.values() if r.status == "ok")
        error_modules = len(results) - ok_modules
        self.ctx.logger.info(
            "[run=%s] 采集完成: 耗时 %.2fs, 成功 %d, 失败 %d",
            run_id,
            collect_seconds,
            ok_modules,
            error_modules,
        )

        # 2. 渲染（组内全部禁用则跳过整图）
        render_started = time.perf_counter()
        images = await self._render(results)
        render_seconds = time.perf_counter() - render_started
        self.ctx.logger.info(
            "[run=%s] 渲染完成: 耗时 %.2fs, 群图 %d 张, 私聊图 %d 张",
            run_id,
            render_seconds,
            len(images["groups"]),
            len(images["private"]),
        )
        if not images["groups"] and not images["private"]:
            self.ctx.logger.error("[run=%s] 本次早报无任何可推送图片", run_id)
            await self._close_collectors()
            log_run_summary(
                self.ctx.logger,
                run_id,
                time.perf_counter() - started,
                ok_modules=ok_modules,
                error_modules=error_modules,
            )
            return

        # 3. 推送
        group_images = images["groups"]
        private_images = images["private"]
        pushed_groups = 0
        for group_id in self.config.basic.target_groups:
            ok, total = await self._pusher.push_group_images(group_images, group_id)
            if ok > 0:
                pushed_groups += 1
            self.ctx.logger.info("[run=%s] 群 %s 推送完成: %d/%d", run_id, group_id, ok, total)
        if self.config.basic.admin_qqs and private_images:
            pushed_private = 0
            for image in private_images:
                for admin_qq in self.config.basic.admin_qqs:
                    if await self._pusher.push_private_image(image, admin_qq):
                        pushed_private += 1
            self.ctx.logger.info(
                "[run=%s] 管理员私聊推送完成: %d/%d",
                run_id,
                pushed_private,
                len(private_images) * len(self.config.basic.admin_qqs),
            )

        # 4. 存档（早报历史）
        self._archive.save(results)

        await self._close_collectors()
        total_seconds = time.perf_counter() - started
        log_run_summary(
            self.ctx.logger,
            run_id,
            total_seconds,
            ok_modules=ok_modules,
            error_modules=error_modules,
            group_images=len(group_images),
            private_images=len(private_images),
            pushed_groups=pushed_groups,
        )

    async def _render(self, results: dict[str, CollectorResult]) -> dict[str, list[str]]:
        """渲染 3 组群图 + AI 额度私聊图。

        整图跳过：组内所有模块均被禁用时，该组不渲染不推送（执行时按模块开关推导，无设置项控制）。
        """
        cfg = self.config
        images: dict[str, list[str]] = {"groups": [], "private": []}

        # 组 1：资讯速览（节日提醒 + 新闻 + 科技）
        enabled = self._enabled_group_modules(_GROUP1_MODULES)
        if enabled:  # 组内至少一个模块启用才渲染
            html = render_group1(
                results.get("news", self._missing("news")),
                results.get("tech", self._missing("tech")),
                results.get("holiday", self._missing("holiday")),
                enabled,
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group1"))
        else:
            self.ctx.logger.info("组 1 全部模块已禁用，跳过该组渲染")

        # 组 2：行情财经（汇率 + 油价 + 金价 + DRAM + 公开 AI 额度 + 昨日 AI 消费）
        enabled = self._enabled_group_modules(_GROUP2_MODULES)
        if cfg.modules.ai_quota_public and self._module_enabled("ai_quota"):
            enabled.add("ai_quota")
        if enabled:
            ai_quota_public = results.get("ai_quota") if "ai_quota" in enabled else None
            html = render_group2(
                results.get("fx", self._missing("fx")),
                results.get("fuel", self._missing("fuel")),
                results.get("gold", self._missing("gold")),
                results.get("dram", self._missing("dram")),
                ai_quota_public,
                results.get("ai_usage", self._missing("ai_usage")),
                enabled,
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group2"))
        else:
            self.ctx.logger.info("组 2 全部模块已禁用，跳过该组渲染")

        # 组 3：文娱生活（新番 + 电影 + 游戏，封面下载内嵌）
        enabled = self._enabled_group_modules(_GROUP3_MODULES)
        if enabled:
            covers = await self._collect_covers(results)
            html = render_group3(
                results.get("anime", self._missing("anime")),
                results.get("movie", self._missing("movie")),
                results.get("game", self._missing("game")),
                covers,
                enabled,
                cfg,
            )
            images["groups"].append(await self._render_image(html, "group3"))
        else:
            self.ctx.logger.info("组 3 全部模块已禁用，跳过该组渲染")

        # AI 额度私聊图（默认仅私发管理员；公开进群后不再重复私发）
        if self.config.basic.admin_qqs and not cfg.modules.ai_quota_public and self._module_enabled("ai_quota"):
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
        """收集组 3 各模块封面 URL → 下载 → data URL 映射（仅启用模块）。"""
        covers: dict[str, str] = {}
        if not self.config.render.covers_enabled or self._cover_manager is None:
            return covers
        urls: list[str] = []
        for module_id in _GROUP3_MODULES:
            if not self._module_enabled(module_id):
                continue
            result = results.get(module_id)
            if result is None or result.status != "ok":
                continue
            for item in result.data.get("animes", result.data.get("movies", result.data.get("games", []))):
                url = str(item.get("image_url") or "")
                if url:
                    urls.append(url)
        # 并发下载封面（CoverManager 内部信号量限流），避免串行拖慢渲染
        tasks = [self._cover_manager.ensure_cover(url) for url in urls]
        data_urls = await asyncio.gather(*tasks)
        for url, data_url in zip(urls, data_urls, strict=True):
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
