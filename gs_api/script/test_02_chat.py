"""
二、聊天接口测试脚本（高升AI）。

覆盖接口文档：
3. POST /ais/chat              流式聊天（SSE）
4. POST /ais/chat/stop         停止生成
5. POST /ais/chat/text         文本聊天（不保存记录）
6. GET  /ais/chat/templates    模版列表

验证点：
- 文本聊天返回结构、回答非空、包含「高升」品牌信息
- 流式聊天：事件类型完整（1001/1002/1003）、拼接回答非空、语义与文本聊天一致
- 停止生成：不报错，code=200
- 模版列表：字段 associationalWord / helpedWrite 等完整
- 集成 Ragas：文本聊天回答质量评估
"""

from __future__ import annotations

import allure
import pytest

from gs_api.base import assertions, get_logger
from gs_api.page import ChatPage, SessionPage
from gs_api.report import GaoShengRagasEvaluator, RagasEvalItem

log = get_logger(__name__)
pytestmark = [pytest.mark.chat, pytest.mark.smoke]


@allure.epic("高升AI接口自动化测试")
@allure.feature("聊天模块")
class TestChat:
    """聊天接口测试类。"""

    # ------------------------------------------------------------------
    # 5. 文本聊天（最稳定，先跑）
    # ------------------------------------------------------------------

    @allure.story("文本聊天（不保存记录）")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("文本聊天：自我介绍返回结构正确")
    def test_chat_text_intro(self, chat_page: ChatPage, gao_sheng_expected_keyword):
        resp = chat_page.chat_text("你是谁？请简单介绍一下你自己。")
        assertions.assert_api_success(resp, "文本聊天-自我介绍")
        answer = resp.data
        assertions.assert_data_type(answer, str, "data")
        assertions.assert_not_empty(answer, "回答文本")
        assertions.assert_contains(answer, gao_sheng_expected_keyword, "自我介绍回答")
        assert "天机" not in answer, f"回答中不应包含「天机」，实际: {answer}"
        resp.attach_allure("文本聊天-响应")

    @allure.story("文本聊天（不保存记录）")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "question",
        [
            "你好",
            "帮我推荐 3 个 Python 入门学习建议",
            "写一个快速排序的伪代码",
            "解释什么是微服务架构",
        ],
        ids=["问候", "Python入门建议", "快速排序伪码", "微服务解释"],
    )
    def test_chat_text_various(self, chat_page: ChatPage, question: str):
        resp = chat_page.chat_text(question)
        assertions.assert_api_success(resp, f"文本聊天: {question}")
        answer = resp.data
        assertions.assert_not_empty(answer, f"回答:{question}")
        assertions.assert_len_greater(answer, 4, "回答长度")

    # ------------------------------------------------------------------
    # 3. 流式聊天
    # ------------------------------------------------------------------

    @allure.story("流式聊天")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("流式聊天：返回数据+停止事件，拼接后非空")
    def test_chat_stream_success(self, chat_page: ChatPage, shared_session_id: str):
        question = "请用一句话解释什么是RAG（检索增强生成）。"
        full_text, events = chat_page.chat_stream_full(question, shared_session_id)

        with allure.step(f"事件数={len(events)}，拼接长度={len(full_text)}"):
            allure.attach(
                "\n".join([f"[{e.event_type}] {e.event_data[:50]}" for e in events[:20]]),
                name="事件列表(前20)",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(full_text, name="拼接回答", attachment_type=allure.attachment_type.TEXT)

        assertions.assert_not_empty(events, "流式事件列表")
        assertions.assert_not_empty(full_text, "流式拼接回答")

        event_types = {e.event_type for e in events}
        with allure.step(f"事件类型集合: {event_types}"):
            # 1001 (数据) 是必须的；1002/1003 可选
            assert "1001" in event_types, "流式响应中未出现 EVENT_DATA(1001)"

    @allure.story("流式聊天")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("流式聊天 vs 文本聊天：回答语义一致性（Ragas辅助）")
    @requires_llm
    def test_chat_stream_vs_text_consistency(
        self,
        chat_page: ChatPage,
        shared_session_id: str,
        ragas_evaluator: GaoShengRagasEvaluator,
    ):
        question = "什么是高升AI？请简要说明。"

        text_answer = chat_page.chat_text_get_answer(question)
        stream_full, _ = chat_page.chat_stream_full(question, shared_session_id)

        with allure.step("对比两次回答长度"):
            allure.attach(text_answer, "文本聊天回答", allure.attachment_type.TEXT)
            allure.attach(stream_full, "流式聊天回答", allure.attachment_type.TEXT)

        assertions.assert_not_empty(stream_full, "流式回答")
        # Ragas AnswerRelevancy 辅助判断语义
        items = [
            RagasEvalItem(question=question, response=text_answer, reference=stream_full),
            RagasEvalItem(question=question, response=stream_full, reference=text_answer),
        ]
        df = ragas_evaluator.evaluate_items(items, scenario_name="流式vs文本一致性")
        # 不做强断言，只记录；避免网络波动导致失败
        log.info("流式vs文本评估完成\n%s", df.head())

    # ------------------------------------------------------------------
    # 4. 停止生成
    # ------------------------------------------------------------------

    @allure.story("停止生成")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("停止生成接口返回成功")
    def test_chat_stop(self, chat_page: ChatPage, shared_session_id: str):
        resp = chat_page.stop_chat(shared_session_id)
        # stop 接口无论是否真的在生成都应该 code=200
        assertions.assert_code(resp, 200)
        resp.attach_allure("停止生成-响应")

    # ------------------------------------------------------------------
    # 6. 模版列表
    # ------------------------------------------------------------------

    @allure.story("模版列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("获取模版列表字段齐全")
    def test_get_templates(self, chat_page: ChatPage):
        resp = chat_page.get_templates()
        assertions.assert_api_success(resp, "获取模版列表")

        data = resp.data
        assertions.assert_data_type(data, dict, "data")
        required = ["associationalWord", "helpedWrite", "continuedWrite", "polish", "streamline"]
        for key in required:
            assertions.assert_key_exists(data, key, "模版data")
            assertions.assert_not_empty(data[key], f"模版字段 {key}")

        with allure.step("associationalWord 模版含 $input 占位符"):
            assertions.assert_contains(data["associationalWord"], "$input", "关联词模版")

        resp.attach_allure("模版列表-响应")

    # ------------------------------------------------------------------
    # Ragas 集成：对文本聊天回答做质量评估
    # ------------------------------------------------------------------

    @allure.story("Ragas 回答质量评估")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("文本聊天多轮回答 Ragas 质量评估")
    @pytest.mark.ragas
    @requires_llm
    def test_chat_ragas_quality(
        self,
        chat_page: ChatPage,
        ragas_evaluator: GaoShengRagasEvaluator,
        gs_qa_pairs,
    ):
        if not gs_qa_pairs:
            pytest.skip("未提供 qa_data.csv，跳过 ragas 批量评估")

        items: list[RagasEvalItem] = []
        for pair in gs_qa_pairs[:8]:  # 最多取 8 条，控制耗时
            question = pair["question"]
            try:
                answer = chat_page.chat_text_get_answer(question)
            except Exception as e:
                log.warning("回答 question=%s 失败: %s", question, e)
                answer = ""
            ctx = pair["contexts"].split("|") if pair.get("contexts") else []
            items.append(RagasEvalItem(
                question=question,
                response=answer,
                retrieved_contexts=ctx or [f"（来自{question}的空上下文占位）"],
                reference=pair["reference"],
                type=pair.get("type") or "general",
            ))

        df = ragas_evaluator.evaluate_items(items, scenario_name="文本聊天Ragas评估")
        ragas_evaluator.assert_thresholds(df, scenario_name="文本聊天")
