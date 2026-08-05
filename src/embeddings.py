"""
Embedding 模型封装模块。

支持两种方式:
1. 本地模型: sentence-transformers 开源模型（需联网下载，仅首次）
2. 远程 API: 硅基流动 (SiliconFlow) 等 OpenAI 兼容的 Embedding API
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()


def create_remote_embeddings(
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> OpenAIEmbeddings:
    """创建远程 Embedding 实例（OpenAI 兼容 API）。

    默认使用硅基流动 (SiliconFlow) 的 BGE 中文模型，
    也可接入任何 OpenAI 兼容的 Embedding 服务。

    Args:
        model: 模型名称，默认读取 EMBEDDING_MODEL 环境变量
        api_key: API Key，默认读取 EMBEDDING_API_KEY 环境变量
        base_url: API 端点，默认读取 EMBEDDING_BASE_URL 环境变量

    Returns:
        OpenAIEmbeddings 实例
    """
    return OpenAIEmbeddings(
        model=model or os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B"),
        api_key=api_key or os.getenv("EMBEDDING_API_KEY"),
        base_url=base_url or os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
    )


def create_local_embeddings(
    model_name: str = "all-MiniLM-L6-v2",
    device: str = "cpu",
):
    """创建本地 Embedding 模型实例（已废弃，保留供参考）。

    需要联网下载 HuggingFace 模型，网络受限环境请使用 create_remote_embeddings()。
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )