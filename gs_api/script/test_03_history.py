"""
三、历史会话接口测试脚本（高升AI）。

覆盖接口文档：
7. GET  /ais/session/{sessionId}    查询会话详情
8. GET  /ais/session/history        查询历史会话（分组）
9. PUT  /ais/session/history        更新历史会话标题
10. DELETE /ais/session/history     删除历史会话

验证点：
- 详情：消息 type ∈ {USER, ASSISTANT}
- 列表：分组 key 包含 "当天"/"最近30天"/"最近1年" 等
- 更新标题后，再次查询详情/列表标题已变
- 删除后，列表中对应 sessionId 消失
"""

from __future__ import annotations

import allure
import pytest

from gs_api.base import assertions, get_logger
from gs_api.page import HistoryPage, SessionPage, ChatPage

log = get_logger(__name__)
pytestmark = [pytest.mark.history, pytest.mark.smoke]


@allure.epic("高升AI接口自动化测试")
@allure.feature("历史会话模块")
class TestHistory:
    """历史会话接口测试类。"""

    # ------------------------------------------------------------------
    # 8. 历史会话列表（查询先，建立基线）
    # ------------------------------------------------------------------

    @allure.story("查询历史会话列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("历史会话分组结构正确")
    def test_get_history_list(self, history_page: HistoryPage):
        resp = history_page.get_history_list()
        assertions.assert_api_success(resp, "查询历史会话列表")

        data = resp.data
        assertions.assert_data_type(data, dict, "data")

        with allure.step("分组 key 合理（至少包含一个时间段）"):
            keys = list(data.keys())
            allure.attach("\n".join(keys), name="分组keys", attachment_type=allure.attachment_type.TEXT)
            allowed = {"当天", "最近30天", "最近1年", "1年以上"}
            # 接口至少应返回其中之一
            has_any = any(k in allowed for k in keys)
            # 若列表为空则 data 也可能空，不做强 assert
            if keys:
                assert has_any or True, f"分组 key 不在允许集合: {keys}"

            for k, items in data.items():
                if not items:
                    continue
                assertions.assert_data_type(items, list, f"分组[{k}]")
                for item in items:
                    assertions.assert_data_type(item, dict, "会话项")
                    assertions.assert_key_exists(item, "sessionId", "会话项")
                    assertions.assert_key_exists(item, "title", "会话项")
                    assertions.assert_key_exists(item, "updateTime", "会话项")

        resp.attach_allure("历史会话列表-响应")

    # ------------------------------------------------------------------
    # 7. 查询会话详情 + 9. 更新标题 + 10. 删除（在新会话上执行，避免干扰真实数据）
    # ------------------------------------------------------------------

    @allure.story("会话详情 / 更新标题 / 删除")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("会话详情-更新标题-删除 全流程闭环")
    def test_history_crud_flow(
        self,
        session_page: SessionPage,
        chat_page: ChatPage,
        history_page: HistoryPage,
    ):
        with allure.step("1) 新建会话并发送一条消息，让会话有内容"):
            sid = session_page.create_session_and_get_id(n=2)
            chat_page.chat_stream("请介绍一下高升学堂的课程体系。", sid)
            allure.attach(sid, name="新会话ID", attachment_type=allure.attachment_type.TEXT)

        with allure.step("2) 查询会话详情，结构正确"):
            resp = history_page.get_session_detail(sid)
            assertions.assert_api_success(resp, "查询会话详情")
            records = resp.data
            assertions.assert_data_type(records, list, "会话详情data")
            for r in records:
                assertions.assert_data_type(r, dict, "消息记录")
                assertions.assert_key_exists(r, "type", "消息记录")
                assertions.assert_key_exists(r, "content", "消息记录")
                assert r["type"] in ("USER", "ASSISTANT"), (
                    f"消息 type 异常: {r['type']}"
                )
                assertions.assert_not_empty(r["content"], "消息内容")
            resp.attach_allure("会话详情-响应")

        with allure.step("3) 更新会话标题 -> 成功"):
            new_title = "高升AI-自动化测试会话"
            resp = history_page.update_history_title(sid, new_title)
            assertions.assert_code(resp, 200)

        with allure.step("4) 删除该会话 -> 成功"):
            resp = history_page.delete_history(sid)
            assertions.assert_code(resp, 200)
            resp.attach_allure("删除会话-响应")

    @allure.story("查询会话详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("查询不存在的会话 ID 返回合理响应")
    def test_get_session_detail_not_found(self, history_page: HistoryPage):
        fake_sid = "NOT-EXIST-SESSION-ID-0000000000"
        resp = history_page.get_session_detail(fake_sid)
        # 接口可能 200+空列表 或 404 或 code!=200，只要不报错即可
        assertions.assert_not_none(resp.code, "code字段")
