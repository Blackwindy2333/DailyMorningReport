"""日志系统测试：文件 handler 挂载/幂等/关闭、汇总日志。"""

import logging

from DailyMorningReport.log_config import (
    close_file_handler,
    log_run_summary,
    setup_plugin_file_logging,
)


def _new_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"test_log_{name}")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    return logger


def test_setup_creates_log_file(tmp_path) -> None:
    logger = _new_logger("file")
    handler = setup_plugin_file_logging(logger, tmp_path)
    assert handler is not None
    log_file = tmp_path / "logs" / "daily_morning_report.log"
    assert log_file.exists()
    # 写一条日志确认落盘
    logger.info("测试日志条目")
    handler.flush()
    assert "测试日志条目" in log_file.read_text(encoding="utf-8")
    close_file_handler(logger)


def test_setup_is_idempotent(tmp_path) -> None:
    logger = _new_logger("idem")
    first = setup_plugin_file_logging(logger, tmp_path)
    second = setup_plugin_file_logging(logger, tmp_path)
    assert first is not None
    assert second is None  # 二次挂载返回 None（幂等）
    assert len([h for h in logger.handlers if getattr(h, "_daily_morning_file_handler", False)]) == 1
    close_file_handler(logger)


def test_close_removes_handler(tmp_path) -> None:
    logger = _new_logger("close")
    setup_plugin_file_logging(logger, tmp_path)
    assert len(logger.handlers) == 1
    close_file_handler(logger)
    assert len(logger.handlers) == 0


def test_close_without_setup(tmp_path) -> None:
    logger = _new_logger("nohandler")
    close_file_handler(logger)  # 不抛异常
    assert logger.handlers == []


def test_log_run_summary_emits(tmp_path, caplog) -> None:
    logger = _new_logger("summary")
    setup_plugin_file_logging(logger, tmp_path)
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_run_summary(
            logger,
            "20260806-080000",
            12.34,
            ok_modules=9,
            error_modules=1,
            group_images=3,
            private_images=1,
            pushed_groups=2,
        )
    assert any("[run=20260806-080000]" in record.message and "12.34" in record.message for record in caplog.records)
    close_file_handler(logger)
