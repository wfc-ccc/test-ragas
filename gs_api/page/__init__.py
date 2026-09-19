"""
page 层：接口与 UI 操作封装。

按高升AI接口文档模块划分：
- SessionPage   会话管理（新建 / 热门问题）
- ChatPage      聊天（流式 / 停止 / 文本 / 模版）
- HistoryPage   历史会话（详情 / 列表 / 更新 / 删除）
- EmbeddingPage 知识库向量（embedding CRUD / 搜索）
- AudioPage     语音（STT / TTS / TTS-Stream）
- GaoShengWebPage  Web UI 辅助操作
"""

from .session_page import SessionPage
from .chat_page import ChatPage
from .history_page import HistoryPage
from .embedding_page import EmbeddingPage
from .audio_page import AudioPage
from .web_page import GaoShengWebPage

__all__ = [
    "SessionPage",
    "ChatPage",
    "HistoryPage",
    "EmbeddingPage",
    "AudioPage",
    "GaoShengWebPage",
]
