"""
会话接口 Page 层封装（高升AI）。

对应接口文档第一章：
1. POST /ais/session  新建会话
2. GET  /ais/session/hot  热门问题
"""

from typing import Optional

import allure

from ..base import HttpClient, http_client, ApiResponse, get_logger, assertions

log = get_logger(__name__)


class SessionPage:
    """会话管理接口封装。"""

    PATH_SESSION = "/ais/session"
    PATH_HOT = "/ais/session/hot"

    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or http_client

    # ------------------------------------------------------------------
    # 1. 新建会话
    # ------------------------------------------------------------------

    @allure.step("新建会话 n={n}")
    def create_session(
        self,
        n: Optional[int] = None,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """新建会话 POST /ais/session。

        Args:
            n: 生成热门示例问题的数量，默认 3
            token: 登录 token，为空则用全局配置的 token

        Returns:
            ApiResponse: 响应对象，data 含 sessionId / title / describe / examples
        """
        params = {}
        if n is not None:
            params["n"] = n
        resp = self.client.post(self.PATH_SESSION, params=params, token=token)
        log.info(
            "新建会话 code=%s sessionId=%s requestId=%s",
            resp.code,
            resp.data.get("sessionId") if resp.data else None,
            resp.request_id,
        )
        return resp

    def create_session_and_get_id(
        self,
        n: Optional[int] = None,
        token: Optional[str] = None,
    ) -> str:
        """新建会话并直接返回 sessionId（断言成功）。"""
        resp = self.create_session(n=n, token=token)
        assertions.assert_api_success(resp, "新建会话")
        sid = resp.data.get("sessionId")
        assertions.assert_session_id(sid)
        return sid

    # ------------------------------------------------------------------
    # 2. 热门问题
    # ------------------------------------------------------------------

    @allure.step("获取热门问题 n={n}")
    def get_hot_questions(
        self,
        n: Optional[int] = None,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """获取热门问题 GET /ais/session/hot。

        Returns:
            data 为 list[{title, describe}]
        """
        params = {}
        if n is not None:
            params["n"] = n
        resp = self.client.get(self.PATH_HOT, params=params, token=token)
        log.info(
            "获取热门问题 code=%s count=%s",
            resp.code,
            len(resp.data) if isinstance(resp.data, list) else None,
        )
        return resp
