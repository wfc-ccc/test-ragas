# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 运行全部测试
pytest tests/ -v

# 按文件运行
pytest tests/test_retrieval.py -v
pytest tests/test_generation.py -v
pytest tests/test_stability.py -v
pytest tests/test_e2e.py -v

# 运行单个测试
pytest tests/test_stability.py::TestEmptyIndex::test_query_empty_index -v
```

测试耗时较长（每个用例 30-120 秒，LLM API 调用链），建议用 `-v` 看实时进度。

## 架构概览

```
用户提问 → Embedding(硅基流动API) → ChromaDB检索 → 拼接上下文 → DeepSeek LLM 生成回答
```

### 核心模块

| 文件 | 职责 |
|------|------|
| `src/rag_system.py` | RAG 主控：延迟初始化 LLM/Embedding/VectorStore，提供 `query()` / `query_batch()` |
| `src/llm.py` | 通过 `ChatOpenAI` 封装 DeepSeek API（兼容 OpenAI 接口格式） |
| `src/embeddings.py` | `create_remote_embeddings()` 使用硅基流动 API；`create_local_embeddings()` 已废弃保底 |
| `src/vector_store.py` | ChromaDB 封装：文档分块、向量库创建/加载 |

### 测试文件

| 文件 | 测试内容 |
|------|---------|
| `tests/conftest.py` | 共享 fixtures：`rag_with_docs`、`evaluator_llm`、`evaluator_embeddings`、测试问题集 |
| `tests/test_retrieval.py` | Context Recall/Precision、Top-K 敏感性 |
| `tests/test_generation.py` | Faithfulness、Answer Relevancy、Context Relevance、三指标联合评估 |
| `tests/test_stability.py` | 重复调用一致性、边界输入、空索引降级 |
| `tests/test_e2e.py` | 技术文档问答 + 客服知识库问答，两个完整场景 |

## 关键环境变量

`.env` 中配置（参考 `.env.example`）：

```
DEEPSEEK_API_KEY=xxx              # DeepSeek LLM API Key
DEEPSEEK_MODEL=deepseek-v4-pro    # 模型名（不支持 deepseek-chat 别名）
EMBEDDING_API_KEY=xxx             # 硅基流动 API Key（与 DeepSeek Key 不同）
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
```

## 重要注意事项

### Ragas 0.4.3 兼容性问题

当前环境安装的是 Ragas 0.4.3，存在以下 API 变更：

1. **`ContextRelevancy` 改名为 `ContextRelevance`**，score key 变为 `nv_context_relevance`
2. **`evaluate()` 返回 `EvaluationResult`**（非 dict），`scores["metric_name"]` 返回 `list[float]` 而非 `float`——单样本取 `[0]`，批量取平均
3. **`AnswerRelevancy` 需要 `embeddings` 参数**：`AnswerRelevancy(llm=..., embeddings=...)`，否则内部默认走 OpenAI 会因无 Key 报错
4. **`LangchainLLMWrapper` 需设 `bypass_n=True`**：DeepSeek 不支持 `n > 1`，Ragas 默认对 `ChatOpenAI` 类型启用多补全，必须 bypass

### DeepSeek API 限制

- `deepseek-v4-pro` `[1m]` 后缀是 Claude Code 的模型标识符，不能出现在 `.env` 中
- 不支持 `n > 1` 参数
- 当前环境无法访问 HuggingFace，所有 embedding 必须走远程 API

### 测试数据

- `data/sample_docs/` 包含智能音箱 X1 Pro 和远程办公政策两份文档
- `scenarios/` 包含电商 API 文档和退换货政策两份场景文档
- 测试 fixtures 中的问题集（`smart_speaker_questions`、`remote_policy_questions`）与上述文档对应