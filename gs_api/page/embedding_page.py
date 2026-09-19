"""
知识库（向量）Page 层封装（高升AI）。

对应接口文档第四章：
11. GET    /ais/embedding              文本转向量
12. POST   /ais/embedding              保存文本到向量库
13. DELETE /ais/embedding              删除文本
14. GET    /ais/embedding/search       内容搜索
15. GET    /ais/embedding/search/all   搜索全部
"""

from typing import Optional

import allure

from ..base import HttpClient, http_client, ApiResponse, get_logger

log = get_logger(__name__)


class EmbeddingPage:
    """向量知识库接口封装。"""

    PATH_EMBEDDING = "/ais/embedding"
    PATH_SEARCH = "/ais/embedding/search"
    PATH_SEARCH_ALL = "/ais/embedding/search/all"

    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or http_client

    # ------------------------------------------------------------------
    # 11. 文本转向量
    # ------------------------------------------------------------------

    @allure.step("文本转向量 message={message}")
    def text_to_embedding(
        self,
        message: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """GET /ais/embedding?message=xxx 文本转向量。"""
        params = {"message": message}
        resp = self.client.get(self.PATH_EMBEDDING, params=params, token=token)
        log.info("文本转向量 code=%s", resp.code)
        return resp

    # ------------------------------------------------------------------
    # 12. 保存文本到向量库
    # ------------------------------------------------------------------

    @allure.step("保存文本到向量库 messages_count={len(messages)}")
    def save_texts(
        self,
        messages: list[str],
        token: Optional[str] = None,
    ) -> ApiResponse:
        """POST /ais/embedding 保存文本到向量库。

        注：接口文档中 messages 为 query 参数 array[string]。
        """
        params = [("messages", m) for m in messages]
        resp = self.client.post(self.PATH_EMBEDDING, params=params, token=token)
        log.info("保存文本到向量库 code=%s count=%d", resp.code, len(messages))
        return resp

    # ------------------------------------------------------------------
    # 13. 删除文本
    # ------------------------------------------------------------------

    @allure.step("删除向量文本 ids_count={len(ids)}")
    def delete_texts(
        self,
        ids: list[str],
        token: Optional[str] = None,
    ) -> ApiResponse:
        """DELETE /ais/embedding 删除指定 id 的文本。

        注：ids 为 query 参数 array[string]。
        """
        params = [("ids", i) for i in ids]
        resp = self.client.delete(self.PATH_EMBEDDING, params=params, token=token)
        log.info("删除向量文本 code=%s count=%d", resp.code, len(ids))
        return resp

    # ------------------------------------------------------------------
    # 14. 内容搜索
    # ------------------------------------------------------------------

    @allure.step("向量内容搜索 message={message}")
    def search(
        self,
        message: str,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """GET /ais/embedding/search?message=xxx 内容搜索。"""
        params = {"message": message}
        resp = self.client.get(self.PATH_SEARCH, params=params, token=token)
        log.info("向量搜索 code=%s query=%s", resp.code, message)
        return resp

    # ------------------------------------------------------------------
    # 15. 搜索全部
    # ------------------------------------------------------------------

    @allure.step("向量搜索全部")
    def search_all(self, token: Optional[str] = None) -> ApiResponse:
        """GET /ais/embedding/search/all 搜索全部向量内容。"""
        resp = self.client.get(self.PATH_SEARCH_ALL, token=token)
        log.info("向量搜索全部 code=%s", resp.code)
        return resp
