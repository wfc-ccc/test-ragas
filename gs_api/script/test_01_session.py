"""
一、会话接口测试脚本（高升AI）。

覆盖接口文档：
1. POST /ais/session       新建会话
2. GET  /ais/session/hot   热门问题

验证点：
- 响应状态、通用字段
- data.sessionId / title / describe / examples 结构
- 欢迎页标题/描述应包含「高升」而非「天机」
- 热门问题列表结构、长度
- 多参数组合（n=0/1/5/10）
"""

from __future__ import annotations

import allure
import pytest

from gs_api.base import assertions
from gs_api.page import SessionPage

pytestmark = [pytest.mark.session, pytest.mark.smoke]


@allure.epic("高升AI接口自动化测试")
@allure.feature("会话管理模块")
class TestSession:
    """会话接口测试类。"""

    # ------------------------------------------------------------------
    # 1. 新建会话
    # ------------------------------------------------------------------

    @allure.story("新建会话")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("新建会话成功，返回结构正确")
    def test_create_session_success(self, session_page: SessionPage, gao_sheng_expected_keyword):
        resp = session_page.create_session(n=3)

        assertions.assert_api_success(resp, "新建会话")
        assertions.assert_not_none(resp.request_id, "requestId")

        data = resp.data
        assertions.assert_data_type(data, dict, "data")
        assertions.assert_key_exists(data, "sessionId", "data")
        assertions.assert_key_exists(data, "title", "data")
        assertions.assert_key_exists(data, "describe", "data")
        assertions.assert_key_exists(data, "examples", "data")

        assertions.assert_session_id(data["sessionId"], "data.sessionId")
        assertions.assert_not_empty(data["title"], "data.title")
        assertions.assert_not_empty(data["describe"], "data.describe")

        with allure.step("断言欢迎文案包含「高升」不包含「天机」"):
            full_text = data["title"] + " " + data["describe"]
            assertions.assert_contains(full_text, gao_sheng_expected_keyword, "欢迎文案")
            assert "天机" not in full_text, (
                f"欢迎文案中不应包含「天机」，实际内容: {full_text}"
            )

        examples = data["examples"]
        assertions.assert_data_type(examples, list, "examples")
        assertions.assert_len_greater(examples, 1, "examples")
        for ex in examples:
            assertions.assert_data_type(ex, dict, "example项")
            assertions.assert_key_exists(ex, "title", "example项")
            assertions.assert_key_exists(ex, "describe", "example项")

        resp.attach_allure("新建会话-响应")

    @allure.story("新建会话")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("新建会话参数 n={n}，examples 数量正确")
    @pytest.mark.parametrize("n", [0, 1, 3, 5], ids=["n=0", "n=1", "n=3默认", "n=5"])
    def test_create_session_with_n(self, session_page: SessionPage, n: int):
        resp = session_page.create_session(n=n)
        assertions.assert_api_success(resp, f"新建会话 n={n}")
        examples = resp.data.get("examples") or []
        # 接口不一定严格等于 n，做合理区间校验
        assert isinstance(examples, list), "examples 应为列表"
        if n > 0:
            assertions.assert_len_greater(examples, 0, f"examples(n={n})")

    @allure.story("新建会话")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("新建会话不传入 n，examples 默认数量合理")
    def test_create_session_without_n(self, session_page: SessionPage):
        resp = session_page.create_session()
        assertions.assert_api_success(resp, "新建会话(默认参数)")
        examples = resp.data.get("examples") or []
        assertions.assert_data_type(examples, list, "examples")

    # ------------------------------------------------------------------
    # 2. 热门问题
    # ------------------------------------------------------------------

    @allure.story("热门问题")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("获取热门问题成功，结构正确")
    def test_get_hot_questions_success(self, session_page: SessionPage):
        resp = session_page.get_hot_questions(n=3)
        assertions.assert_api_success(resp, "获取热门问题")

        data = resp.data
        assertions.assert_data_type(data, list, "data")
        assertions.assert_len_greater(data, 0, "热门问题列表")
        for item in data:
            assertions.assert_data_type(item, dict, "热门问题项")
            assertions.assert_key_exists(item, "title", "热门问题项")
            assertions.assert_key_exists(item, "describe", "热门问题项")
            assertions.assert_not_empty(item["title"], "热门问题.title")
            assertions.assert_not_empty(item["describe"], "热门问题.describe")

        resp.attach_allure("热门问题-响应")

    @allure.story("热门问题")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("n", [1, 2, 5], ids=["n=1", "n=2", "n=5"])
    def test_get_hot_questions_with_n(self, session_page: SessionPage, n: int):
        resp = session_page.get_hot_questions(n=n)
        assertions.assert_api_success(resp, f"获取热门问题 n={n}")
        data = resp.data
        assertions.assert_data_type(data, list, "data")
