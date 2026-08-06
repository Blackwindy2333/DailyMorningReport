"""插件日志系统：双通道日志。

设计：
- 通道 1：插件原有 logger（SDK 注入的 ctx.logger，自动转发到主进程）——保持不变
- 通道 2：独立日志文件 data_dir/logs/daily_morning_report.log（滚动 7 天 × 5MB）

两个通道通过同一个日志器的 handler 组合并行输出：插件 logger 保持原有链路，
另加文件 handler 实现独立持久化，互不干扰。
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
_MAX_BYTES_CHECK = 5 * 1024 * 1024  # 单日文件超限告警阈值（滚动由时间驱动）


def setup_plugin_file_logging(
    logger: logging.Logger,
    data_dir: Path,
    level: int = logging.INFO,
) -> logging.Handler | None:
    """为插件 logger 挂载独立文件 handler（幂等）。

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


def mask_key(api_key: str) -> str:
    """日志脱敏：仅保留前 4 位，其余打码。"""
    if not api_key:
        return ""
    return api_key[:4] + "****"


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
