"""
向量数据库封装模块。

基于 ChromaDB 实现文档的向量化存储和相似度检索。
"""

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# 默认分块参数
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100


def create_text_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """创建文本分块器。

    Args:
        chunk_size: 每个分块的最大字符数
        chunk_overlap: 相邻分块之间的重叠字符数

    Returns:
        RecursiveCharacterTextSplitter 实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", "，", ",", " ", ""],
    )


def split_documents(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """将文档列表分块。

    Args:
        documents: LangChain Document 列表
        chunk_size: 分块大小
        chunk_overlap: 分块重叠

    Returns:
        分块后的 Document 列表
    """
    splitter = create_text_splitter(chunk_size, chunk_overlap)
    return splitter.split_documents(documents)


def create_vector_store(
    documents: list[Document],
    embedding_model,
    persist_directory: str = "./chroma_db",
    collection_name: str = "rag_docs",
) -> Chroma:
    """创建向量数据库并索引文档。

    Args:
        documents: 要索引的 Document 列表
        embedding_model: Embedding 模型实例
        persist_directory: 持久化目录
        collection_name: 集合名称

    Returns:
        已索引的 Chroma 向量库
    """
    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )


def load_vector_store(
    embedding_model,
    persist_directory: str = "./chroma_db",
    collection_name: str = "rag_docs",
) -> Chroma:
    """加载已有的向量数据库。

    Args:
        embedding_model: Embedding 模型实例
        persist_directory: 持久化目录
        collection_name: 集合名称

    Returns:
        已加载的 Chroma 向量库
    """
    return Chroma(
        embedding_function=embedding_model,
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
