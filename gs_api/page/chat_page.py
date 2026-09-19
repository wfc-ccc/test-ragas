"""
聊天接口 Page 层封装（高升AI）。

对应接口文档第二章：
3. POST /ais/chat              流式聊天（SSE）
4. POST /ais/chat/stop         停止生成
5. POST /ais/chat/text         文本聊天（不保存记录）
6. GET  /ais/chat/templates    模版列表
"""

from pathlib import Path
from typing import Generator, Optional

import allure

from ..base import HttpClient, http_client, ApiResponse, StreamEvent, get_logger, assertions

log = get_logger(__name__)


class ChatPage:
    """聊天相关接口封装。"""

    PATH_CHAT = "/ais/chat"
    PATH_CHAT_STOP = "/ais/chat/stop"
    PATH_CHAT_TEXT = "/ais/chat/text"
    PATH_TEMPLATES = "/ais/chat/templates"

    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or http_client

    # ------------------------------------------------------------------
    # 3. 流式聊天
    # ------------------------------------------------------------------

    @allure.step("流式聊天 sessionId={session_id} question={question}")
    def chat_stream(
        self,
        question: str,
        session_id: str,
        token: Optional[str] = None,
    ) -> Generator[StreamEvent, None, None]:
        """流式聊天 POST /ais/chat，返回事件生成器。"""
        body = {"question": question, "sessionId": session_id}
        return self.client.post_stream(self.PATH_CHAT, json_body=body, token=token)

    @allure.step("流式聊天（完整收集） question={question}")
    def chat_stream_full(
        self,
        question: str,
        session_id: str,
        token: Optional[str] = None,
    ) -> tuple[str, list[StreamEvent]]:
        """流式聊天并完整收集，返回 (完整文本, 事件列表)。"""
        events: list[StreamEvent] = []
        text_parts: list[str] = []
        for ev in self.chat_stream(question, session_id, token=token):
            events.append(ev)
            if ev.is_data:
                text_parts.append(ev.event_data)
        full_text = "".join(text_parts)
        log.info(
            "流式聊天完成 sessionId=%s 事件数=%d 回答长度=%d",
            session_id, len(events), len(full_text),
        )
        return full_text, events

    # ------------------------------------------------------------------
    # 4. 停止生成
    # ------------------------------------------------------------------

    @allure.step("停止生成 sessionId={session_id}")
    def stop_chat(
        self,
        session_id: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """停止对话生成 POST /ais/chat/stop?sessionId=xxx。"""
        params = {"sessionId": session_id}
        resp = self.client.post(self.PATH_CHAT_STOP, params=params, token=token)
        log.info("停止生成 code=%s sessionId=%s", resp.code, session_id)
        return resp

    # ------------------------------------------------------------------
    # 5. 文本聊天（不保存记录）
    # ------------------------------------------------------------------

    @allure.step("文本聊天（不保存记录）question={question}")
    def chat_text(
        self,
        question: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """文本聊天 POST /ais/chat/text，body 为纯字符串。"""
        resp = self.client.post(
            self.PATH_CHAT_TEXT,
            data=question,
            headers={"Content-Type": "text/plain"},
            token=token,
        )
        log.info(
            "文本聊天 code=%s answer_len=%s",
            resp.code,
            len(resp.data) if isinstance(resp.data, str) else None,
        )
        return resp

    def chat_text_get_answer(
        self,
        question: str,
        token: Optional[str] = None,
    ) -> str:
        resp = self.chat_text(question, token=token)
        assertions.assert_api_success(resp, "文本聊天")
        answer = resp.data
        assertions.assert_not_empty(answer, "回答文本")
        return answer

    # ------------------------------------------------------------------
    # 6. 模版列表
    # ------------------------------------------------------------------

    @allure.step("获取模版列表")
    def get_templates(self, token: Optional[str] = None) -> ApiResponse:
        """获取系统设定的模版列表 GET /ais/chat/templates。"""
        resp = self.client.get(self.PATH_TEMPLATES, token=token)
        keys = list(resp.data.keys()) if isinstance(resp.data, dict) else []
        log.info("获取模版列表 code=%s keys=%s", resp.code, keys)
        return resp
