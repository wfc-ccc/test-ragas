"""
通用断言工具。

封装高升AI接口的通用响应断言、字段校验、ragas 分数阈值断言。
"""

from typing import Any, Optional

import allure
import pytest

from .http_client import ApiResponse
from .logger import get_logger

log = get_logger(__name__)


class Assertions:
    """断言方法集合。"""

    @staticmethod
    def assert_api_success(response: ApiResponse, msg: str = "") -> None:
        """断言接口调用成功（HTTP 200 且业务 code=200）。"""
        with allure.step(f"断言接口调用成功: {msg or 'API'}"):
            assert response.status_code == 200, (
                f"HTTP 状态码异常: {response.status_code}, body={response.text[:500]}"
            )
            assert response.code == 200, (
                f"业务状态码异常: code={response.code}, msg={response.msg}"
            )
            log.info("接口调用成功 [%s] requestId=%s", msg, response.request_id)

    @staticmethod
    def assert_code(response: ApiResponse, expected: int) -> None:
        with allure.step(f"断言业务 code={expected}"):
            assert response.code == expected, (
                f"期望 code={expected}, 实际 code={response.code}, msg={response.msg}"
            )

    @staticmethod
    def assert_msg_contains(response: ApiResponse, keyword: str) -> None:
        with allure.step(f"断言 msg 包含 '{keyword}'"):
            assert keyword in (response.msg or ""), (
                f"msg 未包含关键字 '{keyword}'，实际 msg={response.msg}"
            )

    @staticmethod
    def assert_data_type(data: Any, expected_type: type, name: str = "data") -> None:
        with allure.step(f"断言 {name} 类型为 {expected_type.__name__}"):
            assert isinstance(data, expected_type), (
                f"{name} 类型错误: 期望 {expected_type.__name__}, 实际 {type(data).__name__}"
            )

    @staticmethod
    def assert_not_none(value: Any, name: str = "value") -> None:
        with allure.step(f"断言 {name} 不为 None"):
            assert value is not None, f"{name} 不应当为 None"

    @staticmethod
    def assert_not_empty(value: Any, name: str = "value") -> None:
        with allure.step(f"断言 {name} 非空"):
            assert value, f"{name} 不应当为空, 实际={value}"

    @staticmethod
    def assert_key_exists(obj: dict, key: str, name: str = "对象") -> None:
        with allure.step(f"断言 {name} 含字段 {key}"):
            assert key in obj, f"{name} 中缺少字段 '{key}'，keys={list(obj.keys())}"

    @staticmethod
    def assert_list_not_empty(lst: list, name: str = "列表") -> None:
        with allure.step(f"断言 {name} 非空列表"):
            assert isinstance(lst, list) and len(lst) > 0, (
                f"{name} 为空或不是列表，实际={lst}"
            )

    @staticmethod
    def assert_len_greater(value: list | str, min_len: int, name: str = "value") -> None:
        with allure.step(f"断言 {name} 长度 >= {min_len}"):
            assert len(value) >= min_len, (
                f"{name} 长度不足: 期望>={min_len}, 实际={len(value)}"
            )

    @staticmethod
    def assert_equal(actual: Any, expected: Any, name: str = "值") -> None:
        with allure.step(f"断言 {name} == {expected}"):
            assert actual == expected, (
                f"{name} 不相等: 期望={expected}, 实际={actual}"
            )

    @staticmethod
    def assert_contains(text: str, keyword: str, name: str = "文本") -> None:
        with allure.step(f"断言 {name} 包含 '{keyword}'"):
            assert keyword in text, (
                f"{name} 未包含关键字 '{keyword}'，实际内容={text[:300]}"
            )

    @staticmethod
    def assert_ragas_score(score: float, threshold: float, metric_name: str = "metric") -> None:
        """断言 ragas 指标得分达到阈值。"""
        with allure.step(f"断言 {metric_name} >= {threshold}"):
            log.info("Ragas 指标 %s = %.4f (阈值 %.2f)", metric_name, score, threshold)
            assert score >= threshold, (
                f"Ragas 指标 {metric_name} 低于阈值: {score:.4f} < {threshold}"
            )

    @staticmethod
    def assert_session_id(sid: Any, name: str = "sessionId") -> None:
        """断言 sessionId 为非空字符串。"""
        with allure.step(f"断言 {name} 格式正确"):
            assert isinstance(sid, str) and len(sid) >= 8, (
                f"{name} 格式异常: {sid}"
            )


assertions = Assertions()
