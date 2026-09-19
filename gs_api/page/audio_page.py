"""
语音接口 Page 层封装（高升AI）。

对应接口文档第五章：
16. POST /ais/audio/stt         语音转文字（wav）
17. POST /ais/audio/tts         文本转语音
18. POST /ais/audio/tts-stream  文本转语音（流式）
"""

from pathlib import Path
from typing import Generator, Optional

import allure

from ..base import HttpClient, http_client, ApiResponse, get_logger

log = get_logger(__name__)


class AudioPage:
    """语音（STT / TTS）接口封装。"""

    PATH_STT = "/ais/audio/stt"
    PATH_TTS = "/ais/audio/tts"
    PATH_TTS_STREAM = "/ais/audio/tts-stream"

    def __init__(self, client: Optional[HttpClient] = None):
        self.client = client or http_client

    # ------------------------------------------------------------------
    # 16. 语音转文字（wav）
    # ------------------------------------------------------------------

    @allure.step("语音转文字 audio={audio_path}")
    def speech_to_text(
        self,
        audio_path: str | Path,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """POST /ais/audio/stt 上传 wav 转文本。"""
        fpath = Path(audio_path)
        if not fpath.exists():
            raise FileNotFoundError(f"音频文件不存在: {fpath}")
        with open(fpath, "rb") as f:
            files = {"audioFile": (fpath.name, f, "audio/wav")}
            resp = self.client.post(self.PATH_STT, files=files, token=token)
        log.info("语音转文字 code=%s file=%s", resp.code, fpath.name)
        return resp

    # ------------------------------------------------------------------
    # 17. 文本转语音
    # ------------------------------------------------------------------

    @allure.step("文本转语音 text={text}")
    def text_to_speech(
        self,
        text: str,
        save_path: Optional[str | Path] = None,
        token: Optional[str] = None,
    ) -> ApiResponse:
        """POST /ais/audio/tts text -> 语音二进制。

        Args:
            text: 要转语音的文字（body 为纯字符串）
            save_path: 若提供，会将响应原始内容保存为文件
        """
        resp = self.client.post(
            self.PATH_TTS,
            data=text,
            headers={"Content-Type": "text/plain"},
            token=token,
        )
        log.info("文本转语音 code=%s text_len=%d", resp.code, len(text))
        if save_path and resp.raw.content:
            Path(save_path).write_bytes(resp.raw.content)
        return resp

    # ------------------------------------------------------------------
    # 18. 文本转语音（流式）
    # ------------------------------------------------------------------

    @allure.step("文本转语音（流式） text={text}")
    def text_to_speech_stream(
        self,
        text: str,
        token: Optional[str] = None,
    ) -> Generator[bytes, None, None]:
        """POST /ais/audio/tts-stream 流式返回音频字节块。

        Yields:
            bytes: 音频数据 chunk
        """
        url = f"{self.client.base_url.rstrip('/')}/{self.PATH_TTS_STREAM.lstrip('/')}"
        headers = {"Content-Type": "text/plain"}
        if token or self.client.base_url:
            auth = token or self.client._session.headers.get("Authorization")
            if auth:
                headers["Authorization"] = auth
        import requests as _req
        with _req.post(url, data=text, headers=headers, stream=True, timeout=self.client.timeout) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

    def text_to_speech_stream_full(
        self,
        text: str,
        save_path: Optional[str | Path] = None,
        token: Optional[str] = None,
    ) -> bytes:
        """完整收集流式 TTS，返回拼接后的字节。"""
        buf: list[bytes] = []
        for chunk in self.text_to_speech_stream(text, token=token):
            buf.append(chunk)
        data = b"".join(buf)
        log.info("流式 TTS 完成 total_bytes=%d", len(data))
        if save_path and data:
            Path(save_path).write_bytes(data)
        return data
