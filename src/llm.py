"""
DeepSeek LLM 封装模块。

通过 LangChain 的 ChatOpenAI 兼容 DeepSeek API，
支持自定义 temperature、max_tokens 等参数。
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def create_deepseek_llm(
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> ChatOpenAI:
    """创建 DeepSeek LLM 实例。

    Args:
        model: 模型名称，默认读取 DEEPSEEK_MODEL 环境变量，fallback 为 deepseek-chat
        temperature: 生成温度，0.0 为确定性输出，适合 RAG 场景
        max_tokens: 最大输出 token 数

    Returns:
        ChatOpenAI 实例，已配置 DeepSeek API 端点
    """
    return ChatOpenAI(
        model=model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )
