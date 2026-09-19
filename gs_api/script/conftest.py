"""
gs_api/script 层共享 conftest。

提供 pytest fixtures：
- Page 对象（Session / Chat / History / Embedding / Web）
- 共享会话 sessionId（用于多接口串联用例）
- Ragas 评估器（复用原有 tests/conftest 中的 evaluator_llm / evaluator_embeddings）
- Allure 生命周期钩子（结果目录初始化、环境信息写入）
- 测试数据 fixtures（YAML / CSV 加载）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

# 将项目根目录加入 sys.path，便于导入 src / tests 模块
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gs_api.base import (
    HttpClient,
    config,
    assertions,
    get_logger,
    load_qa_pairs,
    load_yaml,
)
from gs_api.page import (
    SessionPage,
    ChatPage,
    HistoryPage,
    EmbeddingPage,
    GaoShengWebPage,
)
from gs_api.report import AllureManager, GaoShengRagasEvaluator, RagasEvalItem

log = get_logger("gs_api.script.conftest")

requires_llm = pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要设置 DEEPSEEK_API_KEY 环境变量以启用 Ragas 评估",
)

requires_ais_token = pytest.mark.skipif(
    not config.token,
    reason="需要设置 AIS_TOKEN 环境变量或配置 auth.token 以访问鉴权接口",
)


# ============================================================
# Allure 生命周期：会话级钩子
# ============================================================


def pytest_configure(config_pytest):
    """pytest 启动时初始化 Allure 目录。"""
    # 仅在非 collector 阶段执行
    if config_pytest.option.markexpr and "collect" in config_pytest.option.markexpr:
        return
    try:
        AllureManager.clean_results()
        AllureManager.write_environment()
        AllureManager.write_categories()
        log.info("Allure 报告环境初始化完成")
    except Exception as e:
        log.warning("Allure 环境初始化失败: %s", e)

    config_pytest.addinivalue_line(
        "markers", "session: 会话接口"
    )
    config_pytest.addinivalue_line(
        "markers", "chat: 聊天接口"
    )
    config_pytest.addinivalue_line(
        "markers", "history: 历史会话接口"
    )
    config_pytest.addinivalue_line(
        "markers", "embedding: 知识库向量接口"
    )
    config_pytest.addinivalue_line(
        "markers", "ragas: AI 回答质量评估"
    )
    config_pytest.addinivalue_line(
        "markers", "webui: Web UI 冒烟测试"
    )
    config_pytest.addinivalue_line(
        "markers", "smoke: 冒烟测试"
    )


# ============================================================
# Page 层 fixtures
# ============================================================


@pytest.fixture(scope="session")
def http_client() -> HttpClient:
    """共享 HTTP 客户端（会话级）。"""
    return HttpClient()


@pytest.fixture(scope="session")
def session_page(http_client: HttpClient) -> SessionPage:
    return SessionPage(client=http_client)


@pytest.fixture(scope="session")
def chat_page(http_client: HttpClient) -> ChatPage:
    return ChatPage(client=http_client)


@pytest.fixture(scope="session")
def history_page(http_client: HttpClient) -> HistoryPage:
    return HistoryPage(client=http_client)


@pytest.fixture(scope="session")
def embedding_page(http_client: HttpClient) -> EmbeddingPage:
    return EmbeddingPage(client=http_client)


@pytest.fixture
def web_page():
    """每个用例独立的 Web 浏览器实例，自动 quit。"""
    page = GaoShengWebPage()
    yield page
    try:
        page.quit()
    except Exception:
        pass


# ============================================================
# 共享会话：新建会话 -> 提供 sessionId 供后续接口复用
# ============================================================


@pytest.fixture(scope="module")
def shared_session_id(session_page: SessionPage) -> str:
    """模块级共享会话：每个测试模块新建一次会话。"""
    try:
        resp = session_page.create_session(n=3)
        assertions.assert_api_success(resp, "新建共享会话")
        sid = resp.data.get("sessionId")
        assertions.assert_session_id(sid)
        log.info("共享会话已创建: %s", sid)
        return sid
    except Exception as e:
        log.warning("创建共享会话失败（接口可能不可达）: %s", e)
        pytest.skip(f"创建共享会话失败，跳过模块: {e}")


# ============================================================
# Ragas 评估器 fixtures（复用 src.llm / embeddings 模块）
# ============================================================


@pytest.fixture(scope="session")
def evaluator_llm():
    """复用原有 conftest 的方式：构造 Ragas 评估 LLM。"""
    try:
        from src.llm import create_deepseek_llm
        from ragas.llms import LangchainLLMWrapper
        return LangchainLLMWrapper(create_deepseek_llm(temperature=0.0), bypass_n=True)
    except Exception as e:
        log.warning("evaluator_llm 构造失败: %s", e)
        return None


@pytest.fixture(scope="session")
def evaluator_embeddings():
    """复用原有 conftest 的方式：构造 Ragas 评估 Embedding。"""
    try:
        from src.embeddings import create_remote_embeddings
        from ragas.embeddings.base import LangchainEmbeddingsWrapper
        return LangchainEmbeddingsWrapper(create_remote_embeddings())
    except Exception as e:
        log.warning("evaluator_embeddings 构造失败: %s", e)
        return None


@pytest.fixture(scope="session")
def ragas_evaluator(evaluator_llm, evaluator_embeddings) -> GaoShengRagasEvaluator:
    """构造高升AI Ragas 评估器。"""
    return GaoShengRagasEvaluator(
        evaluator_llm=evaluator_llm,
        evaluator_embeddings=evaluator_embeddings,
    )


# ============================================================
# 测试数据 fixtures
# ============================================================


@pytest.fixture(scope="session")
def gs_test_data():
    """加载 gs_api/data/test_data.yaml（若存在），返回顶层 dict。"""
    return load_yaml("test_data.yaml") or {}


@pytest.fixture(scope="session")
def gs_qa_pairs():
    """加载高升AI Q&A 对 CSV（用于 ragas 评估）。"""
    return load_qa_pairs("qa_data.csv")


@pytest.fixture
def gao_sheng_expected_keyword() -> str:
    """欢迎页文案里应包含「高升」而非「天机」。"""
    return "高升"
