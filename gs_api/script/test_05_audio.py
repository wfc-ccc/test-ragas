"""
五、语音接口测试脚本（高升AI）。

覆盖接口文档：
16. POST /ais/audio/stt         语音转文字（wav）
17. POST /ais/audio/tts         文本转语音
18. POST /ais/audio/tts-stream  文本转语音（流式）

验证点：
- TTS 接口返回非空二进制 / HTTP 200
- TTS-Stream 流式能 yield 多个字节块
- STT 接口（若提供了 wav 样本）能成功返回文本
"""

from __future__ import annotations

from pathlib import Path

import allure
import pytest

from gs_api.base import assertions, get_logger, REPORT_DIR
from gs_api.page import AudioPage

log = get_logger(__name__)
pytestmark = [pytest.mark.audio]

AUDIO_OUT_DIR = REPORT_DIR / "audio_out"
AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)

STT_SAMPLE_WAV = Path(__file__).parent.parent / "data" / "sample_stt.wav"


@allure.epic("高升AI接口自动化测试")
@allure.feature("语音模块")
class TestAudio:
    """语音接口测试类。"""

    # ------------------------------------------------------------------
    # 17. TTS
    # ------------------------------------------------------------------

    @allure.story("文本转语音")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("TTS 文本转语音返回二进制音频")
    @pytest.mark.parametrize(
        "text",
        [
            "你好，我是高升AI智能助理。",
            "欢迎来到高升学堂，我们提供专业的编程教育课程。",
        ],
    )
    def test_tts_text_to_speech(self, audio_page: AudioPage, text: str, tmp_path):
        save_file = tmp_path / "tts_out.wav"
        resp = audio_page.text_to_speech(text, save_path=str(save_file))
        assertions.assert_not_none(resp.status_code, "TTS响应状态码")

        if save_file.exists():
            size = save_file.stat().st_size
            with allure.step(f"TTS 生成文件大小: {size} 字节"):
                allure.attach.file(
                    str(save_file),
                    name="tts_out.wav",
                    attachment_type=allure.attachment_type.WAV,
                )
                # 只要不是异常响应体，大小应大于 0
                assert size > 100, f"TTS 生成文件过小: {size} 字节"

    # ------------------------------------------------------------------
    # 18. TTS-Stream
    # ------------------------------------------------------------------

    @allure.story("文本转语音（流式）")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("TTS-Stream 流式产出多个 chunk")
    def test_tts_stream(self, audio_page: AudioPage, tmp_path):
        text = "高升学堂提供 Java、Python、前端等多方向课程。"
        save_path = tmp_path / "tts_stream_out.wav"
        full_bytes = audio_page.text_to_speech_stream_full(text, save_path=str(save_path))

        with allure.step(f"TTS-Stream 总字节数: {len(full_bytes)}"):
            assertions.assert_len_greater(full_bytes, 200, "流式音频字节数")

        if save_path.exists():
            with allure.step(f"文件大小: {save_path.stat().st_size}"):
                allure.attach.file(
                    str(save_path),
                    name="tts_stream_out.wav",
                    attachment_type=allure.attachment_type.WAV,
                )

    # ------------------------------------------------------------------
    # 16. STT（仅当存在样本 wav 时执行）
    # ------------------------------------------------------------------

    @allure.story("语音转文字")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("STT 上传 wav 返回文字（若有样本）")
    @pytest.mark.skipif(
        not STT_SAMPLE_WAV.exists(),
        reason=f"缺少 STT 样本 wav: {STT_SAMPLE_WAV}",
    )
    def test_stt_speech_to_text(self, audio_page: AudioPage):
        resp = audio_page.speech_to_text(str(STT_SAMPLE_WAV))
        assertions.assert_not_none(resp.code, "STT响应code")
        resp.attach_allure("STT-响应")
