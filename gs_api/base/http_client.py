"""
HTTP 请求客户端封装。

基于 requests 库封装统一的 HTTP 请求方法，
支持自动重试、鉴权、日志记录、流式响应解析。
"""

import json
import time
from typing import Any, Generator, Optional

import requests
import allure

from .config import config


def _default_headers(token: Optional[str] = None) -> dict:
    """构造默认请求头。"""
    headers = {
        "Accept": "application/json, text/event-stream",
        "User-Agent": "GaoSheng-AI-Test-Framework/1.0.0",
    }
    auth_token = token if token is not None else config.token
    if auth_token:
        headers["Authorization"] = auth_token
    return headers


class ApiResponse:
    """统一 API 响应封装。"""

    def __init__(self, raw: requests.Response):
        self.raw = raw
        self.status_code: int = raw.status_code
        self.headers: dict = dict(raw.headers)
        self.text: str = raw.text
        self._json: Optional[dict] = None

    @property
    def json(self) -> dict:
        if self._json is None:
            try:
                self._json = self.raw.json()
            except (json.JSONDecodeError, ValueError):
                self._json = {}
        return self._json

    @property
    def code(self) -> Optional[int]:
        return self.json.get("code")

    @property
    def msg(self) -> Optional[str]:
        return self.json.get("msg")

    @property
    def data(self) -> Any:
        return self.json.get("data")

    @property
    def request_id(self) -> Optional[str]:
        return self.json.get("requestId")

    @property
    def is_success(self) -> bool:
        return self.status_code == 200 and self.code == 200

    def attach_allure(self, name: str = "API响应") -> None:
        allure.attach(
            json.dumps(self.json, ensure_ascii=False, indent=2),
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )


class StreamEvent:
    """流式聊天事件封装。"""

    EVENT_DATA = "1001"
    EVENT_STOP = "1002"
    EVENT_PARAM = "1003"

    def __init__(self, event_type: str, event_data: str):
        self.event_type = event_type
        self.event_data = event_data

    @property
    def is_data(self) -> bool:
        return self.event_type == self.EVENT_DATA

    @property
    def is_stop(self) -> bool:
        return self.event_type == self.EVENT_STOP

    @property
    def is_param(self) -> bool:
        return self.event_type == self.EVENT_PARAM


class HttpClient:
    """高升AI接口 HTTP 客户端。"""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = base_url or config.base_url
        self.timeout = timeout or config.timeout
        self.retries = config.get("api.retries", 3)
        self.retry_delay = config.get("api.retry_delay", 1)
        self._session = requests.Session()

    def _url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        data: Any = None,
        json_body: Any = None,
        headers: Optional[dict] = None,
        files: Any = None,
        token: Optional[str] = None,
        timeout: Optional[int] = None,
        stream: bool = False,
    ) -> ApiResponse:
        """通用请求方法，含自动重试。"""
        url = self._url(path)
        merged_headers = _default_headers(token)
        if headers:
            merged_headers.update(headers)

        _timeout = timeout or self.timeout
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            try:
                with allure.step(f"HTTP {method} {path} (第{attempt}次)"):
                    resp = self._session.request(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json=json_body,
                        headers=merged_headers,
                        files=files,
                        timeout=_timeout,
                        stream=stream,
                    )
                    api_resp = ApiResponse(resp)
                    allure.attach(
                        f"{method} {url}\nStatus: {resp.status_code}",
                        name="请求概要",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                    return api_resp
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exc = e
                if attempt < self.retries:
                    time.sleep(self.retry_delay * attempt)
                    continue
                raise

        if last_exc:
            raise last_exc
        raise RuntimeError("请求失败")

    def get(
        self,
        path: str,
        params: Optional[dict] = None,
        **kwargs,
    ) -> ApiResponse:
        return self._request("GET", path, params=params, **kwargs)

    def post(
        self,
        path: str,
        json_body: Any = None,
        data: Any = None,
        params: Optional[dict] = None,
        files: Any = None,
        **kwargs,
    ) -> ApiResponse:
        return self._request(
            "POST", path, json_body=json_body, data=data, params=params, files=files, **kwargs
        )

    def put(
        self,
        path: str,
        json_body: Any = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> ApiResponse:
        return self._request("PUT", path, json_body=json_body, params=params, **kwargs)

    def delete(
        self,
        path: str,
        params: Optional[dict] = None,
        **kwargs,
    ) -> ApiResponse:
        return self._request("DELETE", path, params=params, **kwargs)

    def post_stream(
        self,
        path: str,
        json_body: Any = None,
        **kwargs,
    ) -> Generator[StreamEvent, None, None]:
        """发送流式 POST 请求，逐行解析 SSE 事件。"""
        url = self._url(path)
        merged_headers = _default_headers(kwargs.pop("token", None))
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            merged_headers.update(extra_headers)

        resp = self._session.post(
            url,
            json=json_body,
            headers=merged_headers,
            stream=True,
            timeout=kwargs.get("timeout") or self.timeout,
        )
        resp.raise_for_status()

        buffer = ""
        for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
            if not chunk:
                continue
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                et = str(obj.get("eventType", ""))
                ed = str(obj.get("eventData", ""))
                yield StreamEvent(event_type=et, event_data=ed)


http_client = HttpClient()
