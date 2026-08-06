"""pytest 共享夹具：默认配置实例。"""

import sys
from pathlib import Path

import pytest

# 使 DailyMorningReport 包可导入（包目录 = tests 上级的上级，即外层插件目录）
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from DailyMorningReport.config_models import DailyMorningReportConfig  # noqa: E402


@pytest.fixture
def config() -> DailyMorningReportConfig:
    """默认配置实例（嵌套分组）。"""
    return DailyMorningReportConfig()


@pytest.fixture
def mock_logger():
    """测试用 logger。"""
    import logging

    return logging.getLogger("test")
