"""
RAG 系统主模块。

整合文档加载、向量化、检索、生成等环节，
提供统一的 RAG 查询接口。
"""

from pathlib import Path
from typing import TypedDict
from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .llm import create_deepseek_llm
from .embeddings import create_remote_embeddings
from .vector_store import split_documents, create_vector_store, load_vector_store


# RAG Prompt 模板：强调仅基于检索到的上下文回答
RAG_PROMPT_TEMPLATE = """你是一个基于知识库的问答助手。请仅根据以下提供的上下文来回答问题。
如果上下文中没有足够的信息来回答问题，请明确说"根据已有资料无法回答"，不要编造答案。

上下文：
{context}

问题：{question}
"""


# 带上下文记忆的多轮对话 Prompt 模板
MEMORY_PROMPT_TEMPLATE = """你是码上学院编程教育平台的智能助手。请结合以下检索到的上下文与之前的对话历史回答用户最新问题。
如果上下文中没有足够的信息来回答问题，请明确说"根据已有资料无法回答"，不要编造答案。

上下文：
{context}

对话历史：
{history}

用户最新问题：{question}
"""


class QueryResult(TypedDict):
    """RAG 查询返回结构。"""

    answer: str
    question: str
    contexts: list[str]
    source_documents: list[Document]


class MemoryQueryResult(TypedDict):
    """带上下文记忆的 RAG 查询返回结构。"""

    answer: str
    question: str
    contexts: list[str]
    source_documents: list[Document]
    history: list[tuple[str, str]]


class RAGSystem:
    """简易 RAG 系统。

    整合 DeepSeek LLM + 开源 Embedding + ChromaDB 向量库，
    支持文档加载、索引构建、检索增强生成。

    Usage:
        rag = RAGSystem()
        rag.load_and_index("data/sample_docs/")
        result = rag.query("什么是 RAG？")
        print(result["answer"])
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        top_k: int = 4,
        temperature: float = 0.0,
    ):
        """初始化 RAG 系统。

        Args:
            persist_dir: 向量库持久化目录
            chunk_size: 文档分块大小
            chunk_overlap: 分块重叠大小
            top_k: 检索返回的文档数量
            temperature: LLM 生成温度
        """
        self.persist_dir = persist_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        # 延迟初始化——首次使用时才加载模型
        self._llm = None
        self._embeddings = None
        self._vector_store = None
        self._temperature = temperature

    @property
    def llm(self):
        if self._llm is None:
            self._llm = create_deepseek_llm(temperature=self._temperature)
        return self._llm

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = create_remote_embeddings()
        return self._embeddings

    @property
    def vector_store(self):
        if self._vector_store is None:
            raise RuntimeError("向量库未初始化，请先调用 load_and_index() 或 load_existing_index()")
        return self._vector_store

    def load_and_index(self, docs_path: str) -> int:
        """加载目录下的所有 .txt 文件并构建索引。

        Args:
            docs_path: 文档目录路径

        Returns:
            索引的文档块数量
        """
        loader = DirectoryLoader(
            docs_path,
            glob="**/*.txt",
            loader_cls=lambda fp: TextLoader(fp, encoding="utf-8"),
            show_progress=False,
        )
        documents = loader.load()

        if not documents:
            raise ValueError(f"目录 {docs_path} 中没有找到 .txt 文件")

        chunks = split_documents(documents, self.chunk_size, self.chunk_overlap)
        self._vector_store = create_vector_store(
            chunks,
            self.embeddings,
            persist_directory=self.persist_dir,
        )
        return len(chunks)

    def load_existing_index(self) -> None:
        """加载已有的向量库索引，不重新构建。"""
        self._vector_store = load_vector_store(
            self.embeddings,
            persist_directory=self.persist_dir,
        )

    def _build_chain(self):
        """构建 LangChain RAG chain。"""
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        chain = (
            {
                "context": self._retrieve_context,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        return chain

    def _retrieve_context(self, question: str) -> str:
        """检索相关文档并拼接为上下文字符串。"""
        docs = self.vector_store.similarity_search(question, k=self.top_k)
        return "\n\n---\n\n".join(doc.page_content for doc in docs)

    def _retrieve_documents(self, question: str) -> list[Document]:
        """检索相关文档，返回 Document 列表。"""
        return self.vector_store.similarity_search(question, k=self.top_k)

    def query(self, question: str) -> QueryResult:
        """执行 RAG 查询。

        Args:
            question: 用户问题

        Returns:
            QueryResult: 包含 answer、question、contexts、source_documents
        """
        source_docs = self._retrieve_documents(question)
        contexts = [doc.page_content for doc in source_docs]
        context_str = "\n\n---\n\n".join(contexts)

        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        chain = prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"context": context_str, "question": question})

        return QueryResult(
            answer=answer,
            question=question,
            contexts=contexts,
            source_documents=source_docs,
        )

    def query_batch(self, questions: list[str]) -> list[QueryResult]:
        """批量查询。

        Args:
            questions: 问题列表

        Returns:
            QueryResult 列表
        """
        return [self.query(q) for q in questions]

    def query_stream(self, question: str):
        """流式 RAG 查询，逐块返回生成内容。

        Args:
            question: 用户问题

        Yields:
            str: 生成内容的增量片段
        """
        source_docs = self._retrieve_documents(question)
        context_str = "\n\n---\n\n".join(doc.page_content for doc in source_docs)

        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        chain = prompt | self.llm | StrOutputParser()
        for chunk in chain.stream({"context": context_str, "question": question}):
            yield chunk

    def query_with_memory(
        self,
        question: str,
        history: list[tuple[str, str]] | None = None,
    ) -> MemoryQueryResult:
        """带上下文记忆的多轮对话查询。

        Args:
            question: 用户最新问题
            history: 之前的对话历史，每项为 (用户提问, 助手回答)

        Returns:
            MemoryQueryResult: 包含 answer、contexts、history 等
        """
        history = list(history or [])
        source_docs = self._retrieve_documents(question)
        contexts = [doc.page_content for doc in source_docs]
        context_str = "\n\n---\n\n".join(contexts)

        history_text = "\n".join(
            f"用户：{u}\n助手：{a}" for u, a in history
        ) or "（无）"

        prompt = ChatPromptTemplate.from_template(MEMORY_PROMPT_TEMPLATE)
        chain = prompt | self.llm | StrOutputParser()
        answer = chain.invoke({
            "context": context_str,
            "history": history_text,
            "question": question,
        })

        new_history = history + [(question, answer)]
        return MemoryQueryResult(
            answer=answer,
            question=question,
            contexts=contexts,
            source_documents=source_docs,
            history=new_history,
        )
