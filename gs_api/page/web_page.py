"""
高升AI Web 端 UI Page 层封装。

基于 SeleniumBase 提供的公共方法，封装高升AI前台页面常见操作：
- 打开首页
- 点击新建会话
- 发送问题 / 读取回答
- 历史会话侧边栏操作

注：该模块为 UI 辅助测试用，主流程仍以 API 接口测试为主。
"""

from typing import Optional

import allure

from ..base import SeleniumBase, get_logger, config

log = get_logger(__name__)


class GaoShengWebPage(SeleniumBase):
    """高升AI Web 端页面操作封装。"""

    def __init__(self, driver=None):
        super().__init__(driver=driver)
        self.base_url = config.base_url.replace(":10010", ":8080") if False else config.base_url

    # ------------------------------------------------------------------
    # 导航
    # ------------------------------------------------------------------

    @allure.step("打开高升AI首页")
    def open_home(self, web_base_url: Optional[str] = None) -> None:
        url = web_base_url or getattr(self, "base_url", config.base_url)
        self.open(url)

    # ------------------------------------------------------------------
    # 元素定位占位（根据实际前端 DOM 调整）
    # ------------------------------------------------------------------

    NEW_SESSION_BTN = ("css", "[data-testid='new-session-btn']")
    QUESTION_INPUT = ("css", "[data-testid='question-input']")
    SEND_BTN = ("css", "[data-testid='send-btn']")
    ANSWER_LAST = ("css", "[data-testid='message-item']:last-child .answer-content")
    HISTORY_ITEMS = ("css", "[data-testid='history-item']")

    @allure.step("UI: 点击新建会话")
    def ui_new_session(self) -> None:
        if self.is_element_present(*self.NEW_SESSION_BTN):
            self.click(*self.NEW_SESSION_BTN)
            self.sleep(0.5)

    @allure.step("UI: 发送问题 question={question}")
    def ui_send_question(self, question: str, wait_sec: float = 3.0) -> str:
        self.type(*self.QUESTION_INPUT, question)
        self.click(*self.SEND_BTN)
        self.sleep(wait_sec)
        if self.is_element_present(*self.ANSWER_LAST):
            return self.get_text(*self.ANSWER_LAST)
        return ""

    @allure.step("UI: 获取历史会话数量")
    def ui_get_history_count(self) -> int:
        if self.is_element_present(*self.HISTORY_ITEMS):
            return len(self.find_elements(*self.HISTORY_ITEMS))
        return 0
