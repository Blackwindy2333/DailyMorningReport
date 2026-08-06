"""早报历史存档：把每日生成的数据与图片写入 data_dir。

结构：data_dir/archive/YYYY-MM-DD.json
{
  "date": "2026-08-06",
  "created_at": "2026-08-06T08:00:00+08:00",
  "modules": {"news": {...}, ...},          # 各采集器数据（CollectorResult.data）
  "status": {"news": "ok", ...}             # 各模块状态
}
图片 base64 体积大，不随存档保存（避免膨胀）；如需回看可后续扩展。
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any


class ArchiveManager:
    """早报存档管理器。"""

    def __init__(self, data_dir: Path, logger: logging.Logger, max_files: int = 30) -> None:
        self._archive_dir = data_dir / "archive"
        self._logger = logger
        self._max_files = max_files

    def save(self, results: dict[str, Any]) -> None:
        """保存当日早报数据（含各模块状态）。"""
        try:
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            today = dt.date.today().isoformat()
            payload = {
                "date": today,
                "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                "modules": {module_id: result.data for module_id, result in results.items()},
                "status": {module_id: result.status for module_id, result in results.items()},
            }
            path = self._archive_dir / f"{today}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self._prune()
            self._logger.info("早报已存档: %s", path)
        except OSError as exc:
            self._logger.warning("早报存档失败: %s", exc)

    def _prune(self) -> None:
        """清理超出保留数量的旧存档。"""
        files = sorted(self._archive_dir.glob("*.json"))
        for old in files[: -self._max_files]:
            try:
                old.unlink()
            except OSError:
                pass
