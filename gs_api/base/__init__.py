"""
base 层：公共基础封装。

包含：
- config: 全局配置管理
- http_client: 高升AI接口 HTTP 客户端（含流式解析）
- selenium_base: Selenium Web UI 操作基类
- logger: 统一日志工具
- assertions: 通用断言集合
- data_loader: YAML / CSV 测试数据加载器
"""

from .config import config, Config
from .http_client import HttpClient, http_client, ApiResponse, StreamEvent
from .selenium_base import SeleniumBase
from .logger import get_logger, attach_log_to_allure
from .assertions import assertions, Assertions
from .data_loader import load_yaml, load_csv, load_qa_pairs

__all__ = [
    "config",
    "Config",
    "HttpClient",
    "http_client",
    "ApiResponse",
    "StreamEvent",
    "SeleniumBase",
    "get_logger",
    "attach_log_to_allure",
    "assertions",
    "Assertions",
    "load_yaml",
    "load_csv",
    "load_qa_pairs",
]
