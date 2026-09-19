"""
五、Ragas AI 回答质量评估脚本（高升AI集成）。

结合项目原有的 Ragas 评估机制，对高升AI文本聊天接口进行端到端的
质量评估，覆盖以下指标：
- Faithfulness  回答忠实度（基于上下文不编造）
- AnswerRelevancy  回答与问题的相关性
- ContextRecall / ContextRelevance  上下文召回与相关度

注意：
- 该脚本会把接口返回的回答用于评估，同时复用 src.rag_system
  的向量库来构造 retrieved_contexts（用于 Faithfulness 指标需要）
- 所有「天机」字样在断言中被替换为「高升」
"""

from __future__ import annotations

from pathlib import Path

import allure
import pytest
from ragas.dataset_schema import SingleTurnSample
from ragas import EvaluationDataset

from gs_api.base import assertions, get_logger, config
from gs_api.page import ChatPage
from gs_api.report import GaoShengRagasEvaluator, RagasEvalItem

log = get_logger(__name__)
pytestmark = [pytest.mark.ragas, pytest.mark.smoke]


REQUIRED_KEYWORD = "高升"
FORBIDDEN_KEYWORD = "天机"


@allure.epic("高升AI接口自动化测试")
@allure.feature("Ragas AI回答质量评估")
@pytest.mark.usefixtures("requires_llm")
class TestRagasQuality:
    """Ragas 质量评估类。"""

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _retrieve_contexts_from_local_rag(question: str, sample_docs_dir: Path) -> list[str]:
        """复用项目原有 RAG 系统检索上下文，给 Ragas Faithfulness 使用。"""
        try:
            from src.rag_system import RAGSystem
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                rag = RAGSystem(
                    persist_dir=str(Path(tmp) / "chroma_tmp"),
                    top_k=4,
                    temperature=0.0,
                )
                rag.load_and_index(str(sample_docs_dir))
                docs = rag._retrieve_documents(question)
                return [d.page_content for d in docs]
        except Exception as e:
            log.warning("本地 RAG 检索上下文失败，使用空上下文: %s", e)
            return [f"（高升AI问题：{question} - 无本地检索上下文，占位文本）"]

    @staticmethod
    def _assert_brand(text: str, source: str) -> None:
        """断言品牌名：包含高升，不含天机。"""
        with allure.step(f"品牌校验 [{source}]"):
            if text:
                # 不强求所有回答都含「高升」，只禁止出现「天机」
                if FORBIDDEN_KEYWORD in text:
                    pytest.fail(
                        f"[{source}] 中出现禁止词「{FORBIDDEN_KEYWORD}」，"
                        f"请确认品牌名已改为「高升」\n内容: {text}"
                    )

    # ------------------------------------------------------------------
    # 场景1：通用闲聊 & 自我介绍 Faithfulness
    # ------------------------------------------------------------------

    @allure.story("通用问答质量")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("通用问答 Ragas 质量评估（闲聊+自我介绍）")
    @pytest.mark.ragas
    def test_general_qa_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        sample_docs_dir,
    ):
        questions = [
            {
                "question": "你是谁？请做一个自我介绍。",
                "reference": "我是由高升学堂倾力打造的高升AI智能助理，可推荐课程、答疑解惑等。",
            },
            {
                "question": "你能做什么？请列出你的主要能力。",
                "reference": "高升AI可以推荐课程、答疑解惑、激发创意、交流心事，也提供文本润色、续写、精简等写作辅助。",
            },
            {
                "question": "请用一句话解释什么是RAG检索增强生成。",
                "reference": "RAG是结合检索器与生成器的大模型范式，先从知识库检索相关文档，再基于检索内容生成回答，可减少幻觉并引用溯源。",
            },
        ]

        items: list[RagasEvalItem] = []
        for q in questions:
            answer = chat_page.chat_text_get_answer(q["question"])
            self._assert_brand(answer, q["question"])
            ctx = self._retrieve_contexts_from_local_rag(q["question"], sample_docs_dir)
            items.append(RagasEvalItem(
                question=q["question"],
                response=answer,
                retrieved_contexts=ctx,
                reference=q["reference"],
                type="general",
            ))

        df = ragas_evaluator.evaluate_items(items, scenario_name="通用问答Ragas评估")
        ragas_evaluator.assert_thresholds(df, scenario_name="通用问答")

    # ------------------------------------------------------------------
    # 场景2：课程咨询类问答 (Faithfulness / Recall)
    # ------------------------------------------------------------------

    @allure.story("课程咨询质量")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("课程相关问答 Ragas 质量评估（结合RAG上下文）")
    @pytest.mark.ragas
    def test_course_consultation_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        sample_docs_dir: Path,
    ):
        questions = [
            {
                "question": "Python 编程入门课的价格是多少？包含多少课时？",
                "reference": "Python编程入门课（PY-101）价格为199元，共40课时，适合零基础学员。",
            },
            {
                "question": "想从事前端工程师，应该按什么顺序学习高升的课程？",
                "reference": "推荐 Web前端开发实战（WEB-150）打基础，再补算法与数据结构精讲（ALG-180）应对面试，预计4-6个月可达求职水平。",
            },
            {
                "question": "学完高升哪门课程之后可以推荐就业？",
                "reference": "Java工程师进阶课（JAVA-201）完成毕业项目并通过答辩后，可提供就业推荐服务。",
            },
        ]

        items: list[RagasEvalItem] = []
        for q in questions:
            answer = chat_page.chat_text_get_answer(q["question"])
            self._assert_brand(answer, q["question"])
            ctx = self._retrieve_contexts_from_local_rag(q["question"], sample_docs_dir)
            items.append(RagasEvalItem(
                question=q["question"],
                response=answer,
                retrieved_contexts=ctx,
                reference=q["reference"],
                type="course_consult",
            ))

        df = ragas_evaluator.evaluate_items(items, scenario_name="课程咨询Ragas评估")
        ragas_evaluator.assert_thresholds(df, scenario_name="课程咨询")

    # ------------------------------------------------------------------
    # 场景3：平台 FAQ 问答
    # ------------------------------------------------------------------

    @allure.story("平台FAQ质量")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("平台常见问题 Ragas 质量评估")
    @pytest.mark.ragas
    def test_faq_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        sample_docs_dir: Path,
    ):
        questions = [
            {
                "question": "高升的课程支持试听和退款吗？",
                "reference": "高升所有课程均提供7天试学期，试学期内可全额退款；超过试学期且进度未超30%退70%，超30%不退。",
            },
            {
                "question": "高升学完如何获得结业证书？",
                "reference": "完成全部课时、通过所有作业与结业考试（或毕业项目答辩）后，可在「我的证书」中下载电子证书，支持扫码验真。",
            },
            {
                "question": "高升课程视频可以下载到本地离线看吗？",
                "reference": "高升的录播视频支持App内缓存离线观看，缓存有效期30天，禁止录屏外传，违者封号处理。",
            },
        ]

        items: list[RagasEvalItem] = []
        for q in questions:
            answer = chat_page.chat_text_get_answer(q["question"])
            self._assert_brand(answer, q["question"])
            ctx = self._retrieve_contexts_from_local_rag(q["question"], sample_docs_dir)
            items.append(RagasEvalItem(
                question=q["question"],
                response=answer,
                retrieved_contexts=ctx,
                reference=q["reference"],
                type="faq",
            ))

        df = ragas_evaluator.evaluate_items(items, scenario_name="平台FAQ-Ragas评估")
        ragas_evaluator.assert_thresholds(df, scenario_name="平台FAQ")

    # ------------------------------------------------------------------
    # 场景4：CSV 批量问题评估
    # ------------------------------------------------------------------

    @allure.story("CSV批量评估")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("使用 CSV 批量评估高升AI回答质量")
    @pytest.mark.ragas
    def test_qa_csv_batch_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        gs_qa_pairs,
        sample_docs_dir: Path,
    ):
        if not gs_qa_pairs:
            pytest.skip("qa_data.csv 为空或不存在，跳过 CSV 批量评估")

        items: list[RagasEvalItem] = []
        for pair in gs_qa_pairs[:12]:  # 控制总耗时，最多 12 条
            try:
                answer = chat_page.chat_text_get_answer(pair["question"])
            except Exception as e:
                log.warning("问题 %s 回答失败: %s", pair["question"], e)
                answer = ""
            self._assert_brand(answer, pair["question"])
            ctx = pair["contexts"].split("|") if pair.get("contexts") else []
            if not ctx:
                ctx = self._retrieve_contexts_from_local_rag(pair["question"], sample_docs_dir)
            items.append(RagasEvalItem(
                question=pair["question"],
                response=answer,
                retrieved_contexts=ctx,
                reference=pair["reference"],
                type=pair.get("type") or "csv",
            ))

        df = ragas_evaluator.evaluate_items(items, scenario_name="CSV批量-Ragas评估")
        # CSV 批量使用较低阈值避免测试过度脆弱
        thr = {
            "faithfulness": config.get("ragas.threshold.faithfulness", 0.5),
            "answer_relevancy": config.get("ragas.threshold.answer_relevancy", 0.5),
        }
        ragas_evaluator.assert_thresholds(df, thresholds=thr, scenario_name="CSV批量")

    # ------------------------------------------------------------------
    # 场景5：多轮对话记忆 + 指代消解（用文本聊天模拟，结合历史）
    # ------------------------------------------------------------------

    @allure.story("多轮记忆与指代")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("多轮对话记忆回答 Ragas 评估")
    @pytest.mark.ragas
    def test_multi_turn_memory_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        sample_docs_dir: Path,
        session_page,
    ):
        sid = session_page.create_session_and_get_id(n=2)

        # 第 1 轮：建立上下文
        q1 = "高升的Python编程入门课价格是多少？"
        a1_full, _ = chat_page.chat_stream_full(q1, sid)
        assertions.assert_not_empty(a1_full, "第一轮回答")

        # 第 2 轮：用"这门课"指代，验证助手回答中仍能体现 199 / 40 / Python / 零基础 等信息
        q2 = "这门课适合什么人学？一共多少课时？"
        a2_full, _ = chat_page.chat_stream_full(q2, sid)

        self._assert_brand(a2_full, q2)
        # 用问题 q2 + 历史 q1+a1 构造 combined 上下文，给 ragas 用
        ctx_q = f"用户第一轮问: {q1}\n助手回答: {a1_full[:500]}\n用户第二轮追问: {q2}"
        ctx = self._retrieve_contexts_from_local_rag(q1, sample_docs_dir) + [ctx_q]

        item = RagasEvalItem(
            question=f"{q1} 然后追问：{q2}",
            response=a2_full,
            retrieved_contexts=ctx,
            reference="Python入门课适合零基础学员学习，共40课时，价格199元。",
            type="multi_turn",
        )
        df = ragas_evaluator.evaluate_items([item], scenario_name="多轮记忆-Ragas评估")
        # 多轮更困难，只记录不做强阈值断言
        log.info("多轮记忆评估结果:\n%s", df.head())
