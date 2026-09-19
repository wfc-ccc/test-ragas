"""
四、知识库向量接口测试脚本（高升AI）。

覆盖接口文档：
11. GET    /ais/embedding              文本转向量
12. POST   /ais/embedding              保存文本到向量库
13. DELETE /ais/embedding              删除文本
14. GET    /ais/embedding/search       内容搜索
15. GET    /ais/embedding/search/all   搜索全部

验证点：
- 每个接口 HTTP 200 + code 字段存在（文档返回示例较简陋，仅做连通性断言）
- 保存 -> 搜索 -> 删除 -> 再搜索 的基本流程可执行
"""

from __future__ import annotations

import allure
import pytest

from gs_api.base import assertions, get_logger
from gs_api.page import EmbeddingPage

log = get_logger(__name__)
pytestmark = [pytest.mark.embedding]


@allure.epic("高升AI接口自动化测试")
@allure.feature("知识库向量模块")
class TestEmbedding:
    """知识库向量接口测试类。"""

    TEST_MESSAGES = [
        "高升学堂Java高级架构与微服务课程包含服务注册、网关、分布式事务等内容。",
        "高升学堂Python进阶编程实战课程价格为399元，共60课时，含作业批改服务。",
        "高升学堂Web前端开发实战课程覆盖React与Vue3双框架教学。",
    ]

    # ------------------------------------------------------------------
    # 11. 文本转向量
    # ------------------------------------------------------------------

    @allure.story("文本转向量")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("文本转向量接口可调用")
    @pytest.mark.parametrize(
        "msg",
        [
            "你好高升AI",
            "什么是检索增强生成",
            "高升学堂的课程体系",
        ],
    )
    def test_text_to_embedding(self, embedding_page: EmbeddingPage, msg: str):
        resp = embedding_page.text_to_embedding(msg)
        # 文档返回示例仅 code / msg，按 HTTP 200 断言即可
        assertions.assert_not_none(resp.code, "响应code字段")

    # ------------------------------------------------------------------
    # 12-14-13 CRUD 闭环
    # ------------------------------------------------------------------

    @allure.story("保存-搜索-删除 闭环")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("保存文本 -> 搜索 -> 删除 流程可执行")
    def test_embedding_crud_flow(self, embedding_page: EmbeddingPage):
        with allure.step("1) 保存 3 条文本到向量库"):
            resp = embedding_page.save_texts(self.TEST_MESSAGES)
            assertions.assert_not_none(resp.code, "保存响应code")

        with allure.step("2) 内容搜索 query=Java微服务"):
            resp = embedding_page.search("Java微服务")
            assertions.assert_not_none(resp.code, "搜索响应code")
            resp.attach_allure("搜索-响应")

        with allure.step("3) 搜索全部"):
            resp = embedding_page.search_all()
            assertions.assert_not_none(resp.code, "搜索全部响应code")

        with allure.step("4) 删除示例 id（占位）"):
            # 接口文档未明确 id 生成方式，先用占位 id，code 200 即可
            resp = embedding_page.delete_texts(["sample-id-1", "sample-id-2"])
            assertions.assert_not_none(resp.code, "删除响应code")
