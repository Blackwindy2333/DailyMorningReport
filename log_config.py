"""插件日志系统：对接官方 SDK 的 ctx.logger，并附加独立滚动文件持久化。

设计（双通道并行输出到同一 logger）：
- 主通道：SDK 注入的 ``self.ctx.logger``（名称 ``plugin.<plugin_id>``，Runner 自动转发到主进程结构化日志）——日志系统基准
- 持久化通道：为 ``ctx.logger`` 挂载独立文件 handler，写入 ``data_dir/logs/daily_morning_report.log``
  （按天时间滚动，保留 7 天），便于本地按 run_id 排查

两个通道共用同一个 logger，互不干扰；文件 handler 由 on_unload 关闭。
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOG_FILE_NAME = "daily_morning_report.log"
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [%(module)s:%(lineno)d] %(message)s"
_ROTATE_WHEN = "midnight"
_ROTATE_INTERVAL = 1
_BACKUP_COUNT = 7


def setup_plugin_file_logging(
    logger: logging.Logger,
    data_dir: Path,
    level: int = logging.INFO,
) -> logging.Handler | None:
    """为插件 logger 挂载独立文件 handler（幂等）。

    ``logger`` 应传入 ``self.ctx.logger``（官方 SDK 日志，名称 ``plugin.<plugin_id>``），
    使其同时具备主进程转发与本地文件持久化能力。

    返回文件 handler，供 on_unload 关闭；logger 已挂同源 handler 时返回 None。
    """
    # 避免重复挂载（on_config_update 多次调用时）
    for existing in logger.handlers:
        if getattr(existing, "_daily_morning_file_handler", False):
            return None

    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        logs_dir / _LOG_FILE_NAME,
        when=_ROTATE_WHEN,
        interval=_ROTATE_INTERVAL,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.setLevel(level)
    # 标记位：识别本插件挂载的文件 handler（动态属性，供幂等检查与关闭）
    handler._daily_morning_file_handler = True
    logger.addHandler(handler)
    return handler


def close_file_handler(logger: logging.Logger) -> None:
    """关闭并移除插件挂载的文件 handler（on_unload 调用）。"""
    for handler in list(logger.handlers):
        if getattr(handler, "_daily_morning_file_handler", False):
            handler.close()
            logger.removeHandler(handler)


def log_run_summary(
    logger: logging.Logger,
    run_id: str,
    total_seconds: float,
    *,
    ok_modules: int = 0,
    error_modules: int = 0,
    group_images: int = 0,
    private_images: int = 0,
    pushed_groups: int = 0,
) -> None:
    """执行结束汇总日志（结构化、便于按 run_id 检索）。"""
    logger.info(
        "[run=%s] 早报执行完成: 总耗时 %.2fs, 成功模块 %d, 失败模块 %d, 群图 %d 张, 私聊图 %d 张, 推送群 %d 个",
        run_id,
        total_seconds,
        ok_modules,
        error_modules,
        group_images,
        private_images,
        pushed_groups,
    )
