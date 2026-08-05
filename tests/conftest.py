"""
pytest 共享 fixtures 配置。

被测对象: 编程教育平台「码上学院」RAG 智能助手。
覆盖功能: 智能课程咨询、课程推荐、智能问答、订单查询、预下单、流式对话、上下文记忆。

提供:
- 平台知识库文档 fixtures
- RAG 系统实例 fixture
- 标准测试问题集（课程咨询 / 智能问答 / 订单 / 预下单）
- Ragas 评估器 LLM / Embedding fixture
"""

import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

# 跳过标记：没有 API Key 时跳过需要 LLM 的测试
requires_deepseek = pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要设置 DEEPSEEK_API_KEY 环境变量",
)


# ============================================================
# 样例文档 fixtures
# ============================================================

@pytest.fixture
def sample_docs_dir():
    """指向预制的平台知识库文档目录（课程目录 + 平台 FAQ）。"""
    return Path(__file__).parent.parent / "data" / "sample_docs"


@pytest.fixture
def scenarios_dir():
    """指向场景文档目录（课程咨询 / 订单预下单流程）。"""
    return Path(__file__).parent.parent / "scenarios"


@pytest.fixture
def temp_docs_dir():
    """创建临时文档目录，用于隔离测试。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        doc = tmp_path / "test.txt"
        doc.write_text(
            """# 码上学院测试课程规格

## 基本参数
- 课程名称: 测试课程 T1
- 课程编号: T1-2024
- 课时: 30 课时
- 价格: 299 元
- 难度: 入门
- 适合人群: 零基础学员
- 学习模式: 录播 + 直播答疑

## 功能特性
1. 录播视频: 永久有效，支持离线缓存
2. 直播答疑: 每周一次，错过可看回放
3. 作业批改: 助教 24 小时内反馈

## 常见问题
**Q: 如何获得结业证书？**
A: 完成全部课时与作业并通过结业考试后，在「我的证书」中下载电子证书。

**Q: 退课政策？**
A: 7 天试学期内全额退款；超过试学期且进度未超 30% 退 70%；超过 30% 不退款。

**Q: 课程能下载吗？**
A: 录播视频支持 App 内缓存离线观看，有效期 30 天，禁止录屏外传。
""",
            encoding="utf-8",
        )
        yield str(tmp_path)


# ============================================================
# RAG 系统 fixtures
# ============================================================

@pytest.fixture
def rag_with_docs(sample_docs_dir, tmp_path):
    """创建已加载平台知识库（课程目录 + FAQ）的 RAG 系统实例。

    每次测试使用独立的向量库目录，确保隔离。
    """
    from src.rag_system import RAGSystem

    persist_dir = str(tmp_path / "chroma_test")
    rag = RAGSystem(
        persist_dir=persist_dir,
        chunk_size=500,
        chunk_overlap=100,
        top_k=4,
        temperature=0.0,
    )
    rag.load_and_index(str(sample_docs_dir))
    return rag


@pytest.fixture
def rag_with_temp_docs(temp_docs_dir, tmp_path):
    """创建已加载临时文档的 RAG 系统实例。"""
    from src.rag_system import RAGSystem

    persist_dir = str(tmp_path / "chroma_temp")
    rag = RAGSystem(
        persist_dir=persist_dir,
        chunk_size=500,
        chunk_overlap=100,
        top_k=4,
        temperature=0.0,
    )
    rag.load_and_index(temp_docs_dir)
    return rag


@pytest.fixture
def empty_rag(tmp_path):
    """创建一个未加载任何文档的 RAG 实例，用于边界测试。"""
    from src.rag_system import RAGSystem

    persist_dir = str(tmp_path / "chroma_empty")
    return RAGSystem(persist_dir=persist_dir)


# ============================================================
# 测试问题集 fixtures
# ============================================================

@pytest.fixture
def course_consultation_questions():
    """智能课程咨询相关测试问题及参考答案。"""
    return [
        {
            "question": "Python 编程入门课的价格是多少？",
            "reference": "Python 编程入门课（PY-101）价格为 199 元，共 40 课时。",
        },
        {
            "question": "人工智能与机器学习这门课需要什么基础？",
            "reference": "AI-301 要求熟练掌握 Python，并了解线性代数与概率统计基础。零基础建议先学 PY-101 与 ALG-180。",
        },
        {
            "question": "Web 前端开发实战课包含哪些框架？",
            "reference": "包含 React 与 Vue3 双框架，以及 HTML5、CSS3、JavaScript、TypeScript、Webpack 等内容。",
        },
        {
            "question": "哪门课程提供就业推荐？",
            "reference": "Java 工程师进阶课（JAVA-201）完成毕业项目并通过答辩后可推荐就业。",
        },
    ]


@pytest.fixture
def course_recommendation_questions():
    """课程推荐相关测试问题及参考答案。"""
    return [
        {
            "question": "我是零基础，想学编程，应该从哪门课开始？",
            "reference": "推荐 Python 编程入门课（PY-101），Python 语法简洁、上手快，是零基础学员的首选。",
        },
        {
            "question": "想做前端工程师，推荐怎么学？",
            "reference": "推荐 Web 前端开发实战（WEB-150）再补算法与数据结构精讲（ALG-180），预计 4-6 个月可达求职水平。",
        },
        {
            "question": "有后端经验想转云原生方向，学什么？",
            "reference": "推荐 Java 工程师进阶课（JAVA-201）再学 Go 语言后端开发（GO-220），适合云原生与高并发方向。",
        },
    ]


@pytest.fixture
def faq_questions():
    """智能问答（平台 FAQ）相关测试问题及参考答案。"""
    return [
        {
            "question": "课程有试听吗？",
            "reference": "所有课程均提供 7 天试学，试学期内可全额退款，可在详情页免费观看前 3 节。",
        },
        {
            "question": "课程视频能下载吗？",
            "reference": "录播视频支持 App 内缓存离线观看，缓存有效期 30 天，禁止录屏外传，违者封号。",
        },
        {
            "question": "如何获得结业证书？",
            "reference": "完成全部课时、通过所有作业与结业考试（或毕业项目答辩）后，在「我的证书」查看下载电子证书，支持扫码验真。",
        },
        {
            "question": "支持哪些支付方式？",
            "reference": "支持支付宝、微信支付、银行卡、Apple Pay、平台余额，可使用学习券与积分抵扣。",
        },
    ]


@pytest.fixture
def order_questions():
    """订单查询相关测试问题及参考答案。"""
    return [
        {
            "question": "怎么查询我的课程订单？",
            "reference": "在「我的」→「我的订单」查看全部订单，可按状态筛选（待支付/已支付/学习中/已完成/已退款），点击订单查看详情。",
        },
        {
            "question": "订单待支付状态会保留多久？",
            "reference": "待支付订单保留 30 分钟，超时自动取消并释放优惠名额。",
        },
        {
            "question": "找不到订单怎么办？",
            "reference": "确认登录账号与下单账号一致；微信支付订单需确认是否用微信快捷登录。仍找不到请提供支付凭证联系客服。",
        },
    ]


@pytest.fixture
def preorder_questions():
    """预下单（预约报名）相关测试问题及参考答案。"""
    return [
        {
            "question": "什么是预下单？",
            "reference": "预下单是在课程正式开售或开课前提前锁定名额并享受早鸟优惠的报名方式，订单状态为「待开课」，开课前 3 天发送提醒。",
        },
        {
            "question": "预下单的早鸟价优惠是什么？",
            "reference": "开课前 14 天以上预下单享 8 折早鸟价；也可支付 99 元定金抵 199 元学费（限前 50 名），二者不可叠加。",
        },
        {
            "question": "预下单能改班期吗？",
            "reference": "开课前 7 天内可免费改期一次；超过一次或开课前 3 天内改期需补差价的 20% 作为手续费。",
        },
        {
            "question": "预下单开课前取消有手续费吗？",
            "reference": "开课前取消全额退款无手续费；开课后按退课政策处理。",
        },
    ]


@pytest.fixture
def all_test_questions(
    course_consultation_questions,
    course_recommendation_questions,
    faq_questions,
    order_questions,
    preorder_questions,
):
    """所有测试问题合集。"""
    return (
        course_consultation_questions
        + course_recommendation_questions
        + faq_questions
        + order_questions
        + preorder_questions
    )


# ============================================================
# 多轮对话场景 fixtures（用于上下文记忆测试）
# ============================================================

@pytest.fixture
def multi_turn_dialogue():
    """多轮对话场景: 学员咨询课程并追问细节。

    每轮包含 (用户问题, 期望出现的指代/记忆点)。验证助手能否用前文信息回答追问。
    """
    return [
        (
            "Python 编程入门课多少钱？",
            "199",  # 第 1 轮：建立事实
        ),
        (
            "这门课适合什么人学？",  # "这门课"指代上一轮的 Python 入门课
            "零基础",  # 第 2 轮：需记忆上下文
        ),
        (
            "它有几个课时？",  # "它"继续指代 Python 入门课
            "40",  # 第 3 轮：需记忆上下文
        ),
    ]


# ============================================================
# Ragas 评估器 fixtures
# ============================================================

@pytest.fixture
def evaluator_llm():
    """创建用于 Ragas 评估的 LLM 实例。

    Ragas 需要一个独立的 LLM 来评估 Faithfulness/Relevancy 等指标。
    这里复用 DeepSeek API，也可以用其他模型。
    """
    from src.llm import create_deepseek_llm
    from ragas.llms import LangchainLLMWrapper

    llm = create_deepseek_llm(temperature=0.0)
    # DeepSeek 不支持 n > 1，必须 bypass
    return LangchainLLMWrapper(llm, bypass_n=True)


@pytest.fixture
def evaluator_embeddings():
    """创建用于 Ragas 评估的 Embedding 实例。

    AnswerRelevancy 等指标需要 embedding 来计算语义相似度。
    """
    from src.embeddings import create_remote_embeddings
    from ragas.embeddings.base import LangchainEmbeddingsWrapper

    embeddings = create_remote_embeddings()
    return LangchainEmbeddingsWrapper(embeddings)
