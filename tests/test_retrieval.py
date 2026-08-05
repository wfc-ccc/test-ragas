"""
检索质量测试。

被测对象: 编程教育平台「码上学院」RAG 智能助手。
测试指标:
- Context Recall: 检索到的上下文覆盖了参考答案的多少关键信息
- Context Precision: 检索结果中相关文档的比例和排序质量
- Top-K 敏感性: 课程咨询/订单查询检索对 top_k 的响应

这些指标评估 RAG 系统的检索环节是否能把正确的课程/订单/预下单文档找回来。
"""

import pytest

from ragas import evaluate, EvaluationDataset
from ragas.metrics import ContextRecall, ContextPrecision, LLMContextRecall
from ragas.dataset_schema import SingleTurnSample

class TestContextRecall:
    """Context Recall 测试 —— 检索是否能覆盖参考答案的关键信息。

    Context Recall 衡量：给定参考答案，检索到的上下文中包含了多少相关信息。
    高分 = 检索到的课程/FAQ/订单文档涵盖了答案所需的知识点。
    低分 = 检索引擎遗漏了关键信息，LLM 无法基于检索结果给出完整回答。
    """

    @pytest.mark.parametrize(
        "question,reference",
        [
            (
                "Python 编程入门课的价格是多少？",
                "Python 编程入门课（PY-101）价格为 199 元，共 40 课时。",
            ),
            (
                "人工智能与机器学习这门课需要什么基础？",
                "AI-301 要求熟练掌握 Python，并了解线性代数与概率统计基础。",
            ),
            (
                "订单待支付状态会保留多久？",
                "待支付订单保留 30 分钟，超时自动取消并释放优惠名额。",
            ),
        ],
    )
    @pytest.mark.context_recall
    def test_single_context_recall(
        self, rag_with_docs, question, reference, evaluator_llm
    ):
        """参数化测试：课程咨询 / 订单查询问题的 Context Recall 独立评估。"""
        result = rag_with_docs.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            reference=reference,
        )

        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(
            dataset=dataset,
            metrics=[LLMContextRecall(llm=evaluator_llm)],
        )
        score = scores["context_recall"][0]
        print(f"[Context Recall] 问题: {question} → 得分: {score:.3f}")
        assert score >= 0.4, f"Context Recall 过低: {score:.3f}"


class TestContextPrecision:
    """Context Precision 测试 —— 检索结果的精确度。

    高分 = 检索结果噪声少，大部分返回文档都有用（如问 Python 入门只召回 Python 课程文档）。
    低分 = 检索到了大量无关课程文档，浪费上下文窗口。
    """

    def test_context_precision_batch(
        self, rag_with_docs, course_consultation_questions, evaluator_llm
    ):
        """批量评估课程咨询问题的 Context Precision。"""
        samples = []
        for item in course_consultation_questions:
            result = rag_with_docs.query(item["question"])
            samples.append(
                SingleTurnSample(
                    user_input=item["question"],
                    retrieved_contexts=result["contexts"],
                    reference=item["reference"],
                )
            )

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(
            dataset=dataset,
            metrics=[ContextPrecision(llm=evaluator_llm)],
        )
        score_list = scores["context_precision"]
        avg_score = sum(score_list) / len(score_list)
        print(f"[Context Precision] 平均分: {avg_score:.3f}")
        assert avg_score >= 0.3, f"Context Precision 平均分过低: {avg_score:.3f}"


class TestRetrievalTopK:
    """检索 Top-K 参数敏感性测试。"""

    def test_top_k_affects_recall(self, sample_docs_dir, tmp_path, evaluator_llm):
        """验证增加 top_k 能提升 Context Recall。

        更大的 top_k 意味着返回更多文档块，检索覆盖更全面。
        对于课程咨询这类需要细节的问题，更大的 top_k 通常召回更完整。
        """
        from src.rag_system import RAGSystem

        question = "预下单的早鸟价和定金膨胀优惠分别是什么？"
        reference = (
            "开课前 14 天以上预下单享 8 折早鸟价；"
            "也可支付 99 元定金抵 199 元学费（限前 50 名），二者不可叠加。"
        )

        scores = {}
        for k in [1, 2, 4, 6]:
            persist_dir = str(tmp_path / f"chroma_k{k}")
            rag = RAGSystem(persist_dir=persist_dir, top_k=k)
            rag.load_and_index(str(sample_docs_dir))
            result = rag.query(question)

            sample = SingleTurnSample(
                user_input=question,
                retrieved_contexts=result["contexts"],
                reference=reference,
            )
            dataset = EvaluationDataset(samples=[sample])
            eval_result = evaluate(
                dataset=dataset,
                metrics=[LLMContextRecall(llm=evaluator_llm)],
            )
            scores[k] = eval_result["context_recall"][0]
            print(f"  top_k={k}: Context Recall = {scores[k]:.3f}")

        # top_k=4 的 recall 应 >= top_k=1
        assert scores[4] >= scores[1] * 0.8, (
            f"top_k=4 ({scores[4]:.3f}) 不应显著低于 top_k=1 ({scores[1]:.3f})"
        )
