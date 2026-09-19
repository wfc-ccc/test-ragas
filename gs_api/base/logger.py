"""
日志工具。

统一配置测试框架日志格式，同时输出到控制台与文件，
并提供 Allure 附件日志接口。
"""

import logging
import sys
from pathlib import Path

import allure

from .config import REPORT_DIR

LOG_DIR = REPORT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "test_run.log"

_LOGGER_INITIALIZED = False


def get_logger(name: str = "gs_api") -> logging.Logger:
    """获取配置好的 Logger 实例。"""
    global _LOGGER_INITIALIZED
    logger = logging.getLogger(name)
    if _LOGGER_INITIALIZED:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.propagate = False
    _LOGGER_INITIALIZED = True
    return logger


def attach_log_to_allure(message: str, name: str = "日志消息") -> None:
    """将关键日志同时挂载到 Allure 报告。"""
    allure.attach(
        message,
        name=name,
        attachment_type=allure.attachment_type.TEXT,
    )
