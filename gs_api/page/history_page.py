"""
历史会话 Page 层封装（高升AI）。

对应接口文档第三章：
7. GET  /ais/session/{sessionId}   查询会话详情
8. GET  /ais/session/history       查询历史会话（分组）
9. PUT  /ais/session/history       更新历史会话标题
10. DELETE /ais/session/history    删除历史会话
"""

from typing import Optional

import allure

from ..base import HttpClient, http_client, ApiResponse, get_logger

log = get_logger(__name__)


class HistoryPage:
    """历史会话管理接口封装。"""

    PATH_SESSION_DETAIL = "/ais/session/{sessionId}"
    PATH_HISTORY = "/ais/session/history"

    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or http_client

    # ------------------------------------------------------------------
    # 7. 查询会话详情（聊天记录）
    # ------------------------------------------------------------------

    @allure.step("查询会话详情 sessionId={session_id}")
    def get_session_detail(
        self,
        session_id: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """查询某会话的完整聊天记录 GET /ais/session/{sessionId}。

        Returns:
            data 为 list[{type: USER|ASSISTANT, content: str}]
        """
        path = self.PATH_SESSION_DETAIL.format(sessionId=session_id)
        resp = self.client.get(path, token=token)
        cnt = len(resp.data) if isinstance(resp.data, list) else None
        log.info("查询会话详情 code=%s 消息数=%s sessionId=%s", resp.code, cnt, session_id)
        return resp

    # ------------------------------------------------------------------
    # 8. 查询历史会话列表（分组）
    # ------------------------------------------------------------------

    @allure.step("查询历史会话列表（分组）")
    def get_history_list(self, token: Optional[str] = None) -> ApiResponse:
        """查询最近历史会话 GET /ais/session/history。

        Returns:
            data 为 dict，key 如 "当天"、"最近30天"、"最近1年"、"1年以上"
        """
        resp = self.client.get(self.PATH_HISTORY, token=token)
        keys = list(resp.data.keys()) if isinstance(resp.data, dict) else []
        log.info("查询历史会话 code=%s 分组=%s", resp.code, keys)
        return resp

    # ------------------------------------------------------------------
    # 9. 更新历史会话标题
    # ------------------------------------------------------------------

    @allure.step("更新会话标题 sessionId={session_id} -> {title}")
    def update_history_title(
        self,
        session_id: str,
        title: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """更新某会话标题 PUT /ais/session/history。"""
        params = {"sessionId": session_id, "title": title}
        resp = self.client.put(self.PATH_HISTORY, params=params, token=token)
        log.info(
            "更新会话标题 code=%s sessionId=%s title=%s",
            resp.code, session_id, title,
        )
        return resp

    # ------------------------------------------------------------------
    # 10. 删除历史会话
    # ------------------------------------------------------------------

    @allure.step("删除历史会话 sessionId={session_id}")
    def delete_history(
        self,
        session_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """删除历史会话 DELETE /ais/session/history。

        注：接口文档中 sessionId 为可选（query 参数）。
        """
        params: dict = {}
        if session_id:
            params["sessionId"] = session_id
        resp = self.client.delete(self.PATH_HISTORY, params=params, token=token)
        log.info("删除历史会话 code=%s sessionId=%s", resp.code, session_id)
        return resp
