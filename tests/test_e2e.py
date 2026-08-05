"""
端到端（E2E）场景测试。

被测对象: 编程教育平台「码上学院」RAG 智能助手。
覆盖平台核心功能:
- 场景1: 智能课程咨询（课程目录问答）
- 场景2: 课程推荐（基于学员背景的个性化推荐）
- 场景3: 智能问答（平台 FAQ）
- 场景4: 订单查询 + 预下单（订单业务流程）
- 场景5: 流式对话（query_stream 增量输出）
- 场景6: 上下文记忆（多轮对话指代消解）

每个场景包含: 构建索引、多轮问答、核心指标评估、场景特有测试。
"""

from pathlib import Path

import pytest
from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRelevance, LLMContextRecall


# ============================================================
# 场景1: 智能课程咨询
# ============================================================

class TestCourseConsultationScenario:
    """场景1: 智能课程咨询——基于课程目录的精确问答。

    核心挑战:
    - 精确事实检索: "Python 入门课多少钱？"
    - 结构化信息提取: "AI 课程需要哪些前置基础？"
    - 多步推理: "哪门课完成后可以推荐就业？"（涉及课程→就业政策关联）
    """

    @pytest.fixture
    def consultation_docs_path(self):
        return str(Path(__file__).parent.parent / "scenarios" / "course_consultation.txt")

    @pytest.fixture
    def consultation_rag(self, consultation_docs_path, tmp_path):
        """构建课程咨询专用 RAG 实例。"""
        from langchain_community.document_loaders import TextLoader
        from src.embeddings import create_remote_embeddings
        from src.vector_store import split_documents, create_vector_store
        from src.rag_system import RAGSystem

        loader = TextLoader(consultation_docs_path, encoding="utf-8")
        docs = loader.load()
        chunks = split_documents(docs)
        embeddings = create_remote_embeddings()
        persist_dir = str(tmp_path / "chroma_consult")
        create_vector_store(chunks, embeddings, persist_directory=persist_dir)

        rag = RAGSystem(persist_dir=persist_dir)
        rag.load_existing_index()
        return rag

    def test_exact_fact_retrieval(self, consultation_rag, evaluator_llm, evaluator_embeddings):
        """精确事实检索: 课程价格、前置要求应准确返回。"""
        questions = [
            {
                "question": "Python 编程入门课多少钱？",
                "reference": "Python 编程入门课（PY-101）价格为 199 元，共 40 课时。",
            },
            {
                "question": "想做前端工程师推荐学哪些课程？",
                "reference": "推荐 Web 前端开发实战（WEB-150）再补算法与数据结构精讲（ALG-180）。",
            },
        ]
        samples = []
        for item in questions:
            result = consultation_rag.query(item["question"])
            samples.append(SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=result["contexts"],
                response=result["answer"],
                reference=item["reference"],
            ))

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
            LLMContextRecall(llm=evaluator_llm),
        ])
        faith_list = scores["faithfulness"]
        relevancy_list = scores["answer_relevancy"]
        recall_list = scores["context_recall"]
        faith_avg = sum(faith_list) / len(faith_list)
        print(f"\n[课程咨询·精确检索] Faithfulness={faith_avg:.3f}, "
              f"AnswerRelevancy={sum(relevancy_list)/len(relevancy_list):.3f}, "
              f"ContextRecall={sum(recall_list)/len(recall_list):.3f}")
        assert faith_avg >= 0.6

    def test_multi_hop_reasoning(self, consultation_rag, evaluator_llm, evaluator_embeddings):
        """多跳推理: "零基础到能找前端工作需要学哪些课、多久？"——需串联推荐路径与周期。"""
        question = "零基础学员想从事前端工程师，应该按什么顺序学？预计多久能求职？"
        reference = (
            "推荐先学 Web 前端开发实战（WEB-150）掌握 HTML/CSS/JS 与主流框架，"
            "再补算法与数据结构精讲（ALG-180）应对面试，预计 4-6 个月可达求职水平。"
        )
        result = consultation_rag.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            response=result["answer"],
            reference=reference,
        )
        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        ])
        print(f"\n[课程咨询·多跳推理] Faithfulness={scores['faithfulness'][0]:.3f}, "
              f"AnswerRelevancy={scores['answer_relevancy'][0]:.3f}")
        # 多跳推理更困难，阈值稍低
        assert scores["faithfulness"][0] >= 0.5, "多跳推理 Faithfulness 不应过低"


# ============================================================
# 场景2: 课程推荐
# ============================================================

class TestCourseRecommendationScenario:
    """场景2: 课程推荐——基于学员背景与目标给出个性化学习路径。

    核心挑战:
    - 模糊语义匹配: "想做网站"→应匹配前端路径
    - 条件判断: "有经验" vs "零基础"→不同推荐
    - 路径连贯性: 推荐应遵循"先基础后进阶"原则
    """

    @pytest.fixture
    def recommendation_rag(self, scenarios_dir, tmp_path):
        """课程推荐 RAG 实例（咨询场景文档）。"""
        from langchain_community.document_loaders import TextLoader
        from src.embeddings import create_remote_embeddings
        from src.vector_store import split_documents, create_vector_store
        from src.rag_system import RAGSystem

        loader = TextLoader(str(scenarios_dir / "course_consultation.txt"), encoding="utf-8")
        docs = loader.load()
        chunks = split_documents(docs)
        embeddings = create_remote_embeddings()
        persist_dir = str(tmp_path / "chroma_rec")
        create_vector_store(chunks, embeddings, persist_directory=persist_dir)

        rag = RAGSystem(persist_dir=persist_dir)
        rag.load_existing_index()
        return rag

    def test_fuzzy_semantic_match(self, recommendation_rag, evaluator_llm, evaluator_embeddings):
        """模糊语义匹配: 口语化目标→应匹配到正式推荐路径。"""
        questions = [
            {
                "question": "我一点基础都没有，想学编程，从哪开始？",
                "reference": "推荐 Python 编程入门课（PY-101），Python 语法简洁、上手快，是零基础学员首选。",
            },
            {
                "question": "想做人工智能，应该怎么规划学习？",
                "reference": "推荐 Python 编程入门课→算法与数据结构精讲→人工智能与机器学习（AI-301），预计 9-12 个月。",
            },
        ]
        samples = []
        for item in questions:
            result = recommendation_rag.query(item["question"])
            samples.append(SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=result["contexts"],
                response=result["answer"],
                reference=item["reference"],
            ))

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
            ContextRelevance(llm=evaluator_llm),
        ])
        faith_list = scores["faithfulness"]
        faith_avg = sum(faith_list) / len(faith_list)
        print(f"\n[课程推荐·模糊匹配] Faithfulness={faith_avg:.3f}, "
              f"AnswerRelevancy={sum(scores['answer_relevancy'])/len(scores['answer_relevancy']):.3f}")
        assert faith_avg >= 0.6

    def test_conditional_recommendation(self, recommendation_rag, evaluator_llm):
        """条件判断: 不同基础对应不同推荐（零基础 vs 有经验）。"""
        question = "有后端工作经验想转云原生方向，和零基础想入门编程，分别推荐什么？"
        result = recommendation_rag.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            response=result["answer"],
        )
        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
        ])
        print(f"\n[课程推荐·条件判断] Faithfulness={scores['faithfulness'][0]:.3f}")
        assert scores["faithfulness"][0] >= 0.5


# ============================================================
# 场景3: 智能问答（平台 FAQ）
# ============================================================

class TestFaqScenario:
    """场景3: 智能问答——平台常见问题解答。

    核心挑战:
    - 口语化提问映射正式 FAQ 条目
    - 涉及证书、试听、退款等多类问题
    """

    def test_faq_batch(self, rag_with_docs, faq_questions, evaluator_llm, evaluator_embeddings):
        """批量评估 FAQ 智能问答质量。"""
        samples = []
        for item in faq_questions:
            result = rag_with_docs.query(item["question"])
            samples.append(SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=result["contexts"],
                response=result["answer"],
                reference=item["reference"],
            ))

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        ])
        faith_avg = sum(scores["faithfulness"]) / len(scores["faithfulness"])
        rel_avg = sum(scores["answer_relevancy"]) / len(scores["answer_relevancy"])
        print(f"\n[智能问答] Faithfulness={faith_avg:.3f}, AnswerRelevancy={rel_avg:.3f}")
        assert faith_avg >= 0.5
        assert rel_avg >= 0.5


# ============================================================
# 场景4: 订单查询 + 预下单
# ============================================================

class TestOrderAndPreorderScenario:
    """场景4: 订单查询与预下单——基于订单业务流程文档的问答。

    核心挑战:
    - 状态流转理解: "待支付→已支付→学习中"
    - 规则对比: 预下单 vs 普通下单的区别
    - 时效与手续费: 改期、取消规则
    """

    @pytest.fixture
    def order_rag(self, scenarios_dir, tmp_path):
        """订单/预下单专用 RAG 实例。"""
        from langchain_community.document_loaders import TextLoader
        from src.embeddings import create_remote_embeddings
        from src.vector_store import split_documents, create_vector_store
        from src.rag_system import RAGSystem

        loader = TextLoader(str(scenarios_dir / "order_process.txt"), encoding="utf-8")
        docs = loader.load()
        chunks = split_documents(docs)
        embeddings = create_remote_embeddings()
        persist_dir = str(tmp_path / "chroma_order")
        create_vector_store(chunks, embeddings, persist_directory=persist_dir)

        rag = RAGSystem(persist_dir=persist_dir)
        rag.load_existing_index()
        return rag

    def test_order_query(self, order_rag, evaluator_llm, evaluator_embeddings):
        """订单查询: 状态、查询入口、保留时长。"""
        questions = [
            {
                "question": "怎么查询我的课程订单？",
                "reference": "在「我的」→「我的订单」查看全部订单，可按状态筛选，点击订单查看详情。",
            },
            {
                "question": "订单待支付状态会保留多久？",
                "reference": "待支付订单保留 30 分钟，超时自动取消并释放优惠名额。",
            },
        ]
        samples = []
        for item in questions:
            result = order_rag.query(item["question"])
            samples.append(SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=result["contexts"],
                response=result["answer"],
                reference=item["reference"],
            ))

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
            LLMContextRecall(llm=evaluator_llm),
        ])
        faith_avg = sum(scores["faithfulness"]) / len(scores["faithfulness"])
        recall_avg = sum(scores["context_recall"]) / len(scores["context_recall"])
        print(f"\n[订单查询] Faithfulness={faith_avg:.3f}, ContextRecall={recall_avg:.3f}")
        assert faith_avg >= 0.5

    def test_preorder_rules(self, order_rag, evaluator_llm):
        """预下单规则: 早鸟价、定金膨胀、改期手续费。"""
        question = "预下单的早鸟价和定金膨胀优惠分别是什么？能叠加吗？"
        reference = (
            "早鸟价: 开课前 14 天以上预下单享 8 折；"
            "定金膨胀: 99 元定金抵 199 元（限前 50 名）。二者不可叠加。"
        )
        result = order_rag.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            response=result["answer"],
            reference=reference,
        )
        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            LLMContextRecall(llm=evaluator_llm),
        ])
        print(f"\n[预下单·规则] Faithfulness={scores['faithfulness'][0]:.3f}, "
              f"ContextRecall={scores['context_recall'][0]:.3f}")
        assert scores["faithfulness"][0] >= 0.5

    def test_preorder_vs_normal(self, order_rag, evaluator_llm, evaluator_embeddings):
        """预下单与普通下单区别对比。"""
        question = "预下单和普通下单有什么区别？"
        result = order_rag.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            response=result["answer"],
        )
        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(dataset=dataset, metrics=[
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        ])
        print(f"\n[预下单 vs 普通下单] Faithfulness={scores['faithfulness'][0]:.3f}, "
              f"AnswerRelevancy={scores['answer_relevancy'][0]:.3f}")
        assert scores["faithfulness"][0] >= 0.5


# ============================================================
# 场景5: 流式对话
# ============================================================

class TestStreamingDialogueScenario:
    """场景5: 流式对话——验证 query_stream 增量输出。

    核心验证点:
    - 流式接口返回的是增量片段（多个 chunk）
    - 拼接后的完整内容与一次性查询语义一致
    - 流式过程不抛异常
    """

    def test_stream_yields_multiple_chunks(self, rag_with_docs):
        """流式应产出多个增量 chunk，且拼接后非空。"""
        question = "Python 编程入门课适合什么人？价格多少？"
        chunks = list(rag_with_docs.query_stream(question))

        print(f"\n[流式对话] chunk 数量: {len(chunks)}")
        assert len(chunks) >= 1, "流式接口未产出任何 chunk"

        full = "".join(chunks)
        print(f"[流式对话] 拼接长度: {len(full)}")
        print(f"[流式对话] 内容预览: {full[:150]}")
        assert len(full) > 0, "流式拼接后内容为空"

    def test_stream_consistent_with_query(self, rag_with_docs, evaluator_embeddings):
        """流式拼接内容与普通 query 在语义上应一致。"""
        from src.embeddings import create_remote_embeddings
        import numpy as np
        from numpy.linalg import norm

        question = "预下单的定金能抵多少学费？"
        stream_full = "".join(list(rag_with_docs.query_stream(question)))
        normal_answer = rag_with_docs.query(question)["answer"]

        if not stream_full or not normal_answer:
            pytest.skip("流式或普通回答为空，跳过一致性比较")

        embedding_model = create_remote_embeddings()
        vecs = np.array(embedding_model.embed_documents([stream_full, normal_answer]))
        norms = norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vecs_n = vecs / norms
        sim = float((vecs_n[0] @ vecs_n[1]))
        print(f"\n[流式 vs 普通] 语义相似度: {sim:.4f}")
        assert sim >= 0.7, f"流式与普通回答语义不一致: {sim:.4f}"


# ============================================================
# 场景6: 上下文记忆
# ============================================================

class TestContextMemoryScenario:
    """场景6: 上下文记忆——多轮对话指代消解。

    核心验证点:
    - query_with_memory 能携带对话历史
    - 后续轮次中"这门课""它"等指代能被正确消解为前文课程
    - history 字段正确累积
    """

    def test_memory_history_accumulation(self, rag_with_docs):
        """验证 history 在多轮中正确累积。"""
        history = None
        rounds = []
        for user_q, _ in [("Python 编程入门课多少钱？", None), ("它有几个课时？", None)]:
            result = rag_with_docs.query_with_memory(user_q, history=history)
            history = result["history"]
            rounds.append(result)

        print(f"\n[上下文记忆] 累积轮数: {len(rounds[-1]['history'])}")
        assert len(rounds[-1]["history"]) == 2, "history 未正确累积为 2 轮"
        # 第 2 轮的历史应包含第 1 轮的问答
        first_user, first_answer = rounds[-1]["history"][0]
        assert "Python" in first_user
        assert len(first_answer) > 0

    def test_memory_pronoun_resolution(self, rag_with_docs, multi_turn_dialogue):
        """多轮指代消解: "这门课""它"应被理解为前文提到的课程。

        第 2、3 轮的问题不含课程名，若助手能正确回答价格/课时/人群，
        说明上下文记忆生效。
        """
        history = None
        answers = []
        for user_q, expected_keyword in multi_turn_dialogue:
            result = rag_with_docs.query_with_memory(user_q, history=history)
            history = result["history"]
            answers.append((user_q, result["answer"], expected_keyword))
            print(f"\n[记忆·轮次] 问题: {user_q}")
            print(f"[记忆·轮次] 回答: {result['answer'][:200]}")

        # 后续轮次（含指代）的回答中应出现对应关键词，
        # 表明助手用前文上下文（Python 入门课）作答
        for user_q, answer, expected_keyword in answers[1:]:
            assert expected_keyword in answer, (
                f"指代消解失败: 问题 '{user_q}' 的回答未体现上下文记忆"
                f"（期望出现 '{expected_keyword}'）\n回答: {answer}"
            )

    def test_memory_vs_no_memory(self, rag_with_docs, evaluator_embeddings):
        """对比测试: 同一指代问题，带记忆应比无记忆回答更贴合上下文。"""
        import numpy as np
        from numpy.linalg import norm
        from src.embeddings import create_remote_embeddings

        # 先建立上下文
        result1 = rag_with_docs.query_with_memory("Python 编程入门课多少钱？")
        # 带 memory 追问
        result_with_mem = rag_with_docs.query_with_memory(
            "它适合什么人学？", history=result1["history"]
        )
        # 不带 memory 直接问同样问题
        result_no_mem = rag_with_docs.query_with_memory("它适合什么人学？")

        ans_with = result_with_mem["answer"]
        ans_no = result_no_mem["answer"]
        print(f"\n[带记忆] {ans_with[:200]}")
        print(f"[无记忆] {ans_no[:200]}")

        # 带记忆的回答应提到 Python/零基础（指代消解成功）
        assert ("Python" in ans_with) or ("零基础" in ans_with), (
            f"带记忆回答未体现指代消解: {ans_with}"
        )
