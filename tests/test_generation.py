"""
生成质量测试。

被测对象: 编程教育平台「码上学院」RAG 智能助手。
测试指标:
- Faithfulness（忠实度）: 课程咨询/问答答案是否完全基于检索到的上下文，无编造
- Answer Relevancy（答案相关性）: 答案是否直接回答用户问题
- Context Relevancy（上下文相关性）: 检索到的上下文是否与问题相关

这三个是 RAG 评估最核心的指标，分别评估"有没有胡说"、"是否答所问"、"检索对不对"。
"""

import pytest
import numpy as np

from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextRelevance


class TestFaithfulness:
    """Faithfulness（忠实度）测试。

    检测课程咨询/智能问答答案中的每一个断言是否都能在检索到的上下文中找到依据。

    高分 = 答案全部来自知识库，没有幻觉（如不编造课程价格、课时、优惠规则）。
    低分 = 答案包含了上下文中不存在的编造信息。

    典型失败场景:
    - LLM 用自己的训练知识补充了课程信息（而非仅基于检索结果）
    - LLM 把不同课程的参数混淆并编造了一个不存在的"事实"
    """

    def test_faithfulness_individual(
        self, rag_with_docs, course_consultation_questions, evaluator_llm
    ):
        """逐个评估课程咨询回答的 Faithfulness，确保没有幻觉。"""
        scores = []
        for item in course_consultation_questions:
            result = rag_with_docs.query(item["question"])

            sample = SingleTurnSample(
                user_input=item["question"],
                retrieved_contexts=result["contexts"],
                response=result["answer"],
            )
            dataset = EvaluationDataset(samples=[sample])
            eval_result = evaluate(
                dataset=dataset,
                metrics=[Faithfulness(llm=evaluator_llm)],
            )
            score = eval_result["faithfulness"][0]
            scores.append(score)
            print(f"[Faithfulness] {item['question'][:30]}... → {score:.3f}")

        avg = np.mean(scores)
        print(f"\n[Faithfulness] 平均分: {avg:.3f}")

        # Faithfulness 是核心质量指标，阈值设得较高
        assert avg >= 0.6, f"Faithfulness 平均分过低: {avg:.3f}"
        # 每个单项不能出现极低分（<0.3 说明存在严重幻觉）
        for i, s in enumerate(scores):
            assert s >= 0.3, (
                f"问题'{course_consultation_questions[i]['question'][:30]}...' "
                f"Faithfulness 过低: {s:.3f}，可能存在幻觉"
            )


class TestAnswerRelevancy:
    """Answer Relevancy（答案相关性）测试。

    高分 = 答案精准回应问题（如问价格就答价格，不绕到课程大纲）。
    低分 = 答案绕圈子、答非所问、或缺少关键信息。

    典型失败场景:
    - 问"Python 入门课多少钱"却回答"Python 入门课的大纲"
    - 答案中包含大量无关课程信息冲淡了核心回答
    """

    @pytest.mark.parametrize(
        "question,reference",
        [
            ("Python 编程入门课多少钱？", "199 元"),
            ("Web 前端开发实战课包含哪些框架？", "React 与 Vue3"),
            ("预下单的定金能抵多少学费？", "99 元定金抵 199 元学费"),
        ],
    )
    def test_answer_relevance_single(
        self, rag_with_docs, question, reference, evaluator_llm, evaluator_embeddings
    ):
        """参数化测试：课程咨询/预下单具体事实类问题的答案相关性。"""
        result = rag_with_docs.query(question)

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=result["contexts"],
            response=result["answer"],
            reference=reference,
        )
        dataset = EvaluationDataset(samples=[sample])
        scores = evaluate(
            dataset=dataset,
            metrics=[AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings)],
        )
        score = scores["answer_relevancy"][0]
        print(f"[Answer Relevancy] {question} → {score:.3f}")
        assert score >= 0.5, f"Answer Relevancy 过低: {score:.3f}"


class TestContextRelevance:
    """Context Relevancy（上下文相关性）测试。

    衡量检索到的上下文中，有多少内容真正与问题相关。

    高分 = 检索结果精准，没有冗余（问 Python 价格只召回 Python 课程段落）。
    低分 = 检索返回了大量无关内容（如问订单却召回了课程大纲）。

    典型失败场景:
    - 用户问"订单查询"，但检索结果混入了大量课程介绍
    - 分块策略导致检索到了同一文档的大量冗余变体
    """

    def test_context_relevance_batch(
        self, rag_with_docs, all_test_questions, evaluator_llm
    ):
        """批量评估所有功能问题（咨询/推荐/问答/订单/预下单）的 Context Relevancy。"""
        samples = []
        for item in all_test_questions:
            result = rag_with_docs.query(item["question"])
            samples.append(
                SingleTurnSample(
                    user_input=item["question"],
                    retrieved_contexts=result["contexts"],
                    response=result["answer"],
                    reference=item["reference"],
                )
            )

        dataset = EvaluationDataset(samples=samples)
        scores = evaluate(
            dataset=dataset,
            metrics=[ContextRelevance(llm=evaluator_llm)],
        )
        score_list = scores["nv_context_relevance"]
        avg = sum(score_list) / len(score_list)
        print(f"[Context Relevance] 平均分: {avg:.3f}")
        assert avg >= 0.3, f"Context Relevance 平均分过低: {avg:.3f}"


class TestCombinedMetrics:
    """三项核心指标的联合评估。

    一次性对同一批查询计算 Faithfulness + Answer Relevancy + Context Relevancy，
    这是 RAG 系统日常回归测试的标准做法。
    """

    def test_combined_evaluation(
        self, rag_with_docs, all_test_questions, evaluator_llm, evaluator_embeddings
    ):
        """三指标联合评估，验证课程助手整体质量。

        用一次 evaluate() 调用同时评估三个指标，效率更高。
        """
        samples = []
        for item in all_test_questions:
            result = rag_with_docs.query(item["question"])
            samples.append(
                SingleTurnSample(
                    user_input=item["question"],
                    retrieved_contexts=result["contexts"],
                    response=result["answer"],
                    reference=item["reference"],
                )
            )

        dataset = EvaluationDataset(samples=samples)
        metrics = [
            Faithfulness(llm=evaluator_llm),
            AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
            ContextRelevance(llm=evaluator_llm),
        ]
        results = evaluate(dataset=dataset, metrics=metrics)

        print(results)
        # 输出综合报告
        print("\n" + "=" * 60)
        print("码上学院 RAG 助手综合评估报告")
        print("=" * 60)
        faithfulness_list = results["faithfulness"]
        relevancy_list = results["answer_relevancy"]
        context_list = results["nv_context_relevance"]
        faithfulness_avg = sum(faithfulness_list) / len(faithfulness_list)
        relevancy_avg = sum(relevancy_list) / len(relevancy_list)
        context_avg = sum(context_list) / len(context_list)

        print(f"  样本数:              {len(samples)}")
        print(f"  Faithfulness:        {faithfulness_avg:.3f}")
        print(f"  Answer Relevancy:    {relevancy_avg:.3f}")
        print(f"  Context Relevancy:   {context_avg:.3f}")
        print("=" * 60)

        assert faithfulness_avg >= 0.6, "Faithfulness 未达标"
        assert relevancy_avg >= 0.5, "Answer Relevancy 未达标"
        assert context_avg >= 0.3, "Context Relevancy 未达标"
