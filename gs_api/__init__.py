"""
高升（GaoSheng）AI 接口自动化测试框架。

四层架构：
- base/    公共基础（config/http_client/selenium_base/logger/assertions/data_loader）
- page/    接口与 UI 操作封装（Session/Chat/History/Embedding/Web）
- script/  pytest 自动化脚本（6 个 test_*.py + conftest）
- report/  Allure 报告管理 + Ragas 评估器

全局配置 / 测试数据默认目录：
- gs_api/config/config.yaml
- gs_api/data/*.yaml / *.csv

在使用前请配置环境变量或 config.yaml：
- AIS_TOKEN            登录鉴权 token（部分接口需要）
- DEEPSEEK_API_KEY     评估 LLM 的 API Key（Ragas 需要）
- EMBEDDING_API_KEY    Embedding API Key（Ragas AnswerRelevancy 需要）

执行示例：
    pytest gs_api/script -m smoke --alluredir gs_api/report/output/allure_results
    allure generate gs_api/report/output/allure_results -o gs_api/report/output/allure_html --clean
"""

__version__ = "1.0.0"
__project__ = "GaoSheng AI API Test Framework"
__brand__ = "高升"

# 统一导出各层公共入口，便于在外部脚本使用
from .base import (  # noqa: E402
    config,
    HttpClient,
    http_client,
    ApiResponse,
    StreamEvent,
    SeleniumBase,
    assertions,
    get_logger,
    load_yaml,
    load_csv,
    load_qa_pairs,
)
from .page import (  # noqa: E402
    SessionPage,
    ChatPage,
    HistoryPage,
    EmbeddingPage,
    GaoShengWebPage,
)
from .report import (  # noqa: E402
    AllureManager,
    GaoShengRagasEvaluator,
    RagasEvalItem,
    ALLURE_RESULTS,
)

__all__ = [
    "__version__",
    "__project__",
    "__brand__",
    "config",
    "HttpClient",
    "http_client",
    "ApiResponse",
    "StreamEvent",
    "SeleniumBase",
    "assertions",
    "get_logger",
    "load_yaml",
    "load_csv",
    "load_qa_pairs",
    "SessionPage",
    "ChatPage",
    "HistoryPage",
    "EmbeddingPage",
    "GaoShengWebPage",
    "AllureManager",
    "GaoShengRagasEvaluator",
    "RagasEvalItem",
    "ALLURE_RESULTS",
]
