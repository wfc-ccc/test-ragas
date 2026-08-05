---
name: git-commit
description: >
  在提交代码时使用此 skill——自动分析 `git diff --staged` 的变更内容，
  生成符合 Conventional Commits 规范的中文 commit message，
  展示给用户确认后执行提交。触发场景：用户提到"提交"、"commit"、"生成 commit message"。
---

# Git 提交规范化

## 核心原则

1. **先分析再生成** — 必须运行 `git diff --staged` 获取实际变更内容
2. **中文描述** — 简短描述使用中文，type 和 scope 保持英文
3. **用户确认** — 绝不自动提交，始终展示后等待确认

## 执行步骤

### 1. 检查暂存区状态

```bash
git diff --staged --stat       # 变更文件概览
git diff --staged              # 变更详情
```

如果暂存区为空，提示用户先 `git add` 相关文件。

### 2. 判断变更类型（type）

| type | 适用场景 |
|------|---------|
| `feat` | 新功能、新模块、新接口 |
| `fix` | 修复 bug、修复测试、解决报错 |
| `refactor` | 重构代码结构，不改变外部行为 |
| `test` | 新增/修改测试用例、fixtures、conftest |
| `docs` | 文档变更（README、CLAUDE.md、注释） |
| `chore` | 依赖更新、环境配置（.env、requirements.txt） |
| `style` | 仅格式/排版变更，不影响逻辑 |

### 3. 确定影响范围（scope）

根据变更文件路径推断 scope，常见映射：

| 路径 | scope |
|------|-------|
| `src/rag_system.py` | `rag` |
| `src/llm.py` | `llm` |
| `src/embeddings.py` | `embeddings` |
| `src/vector_store.py` | `vector-store` |
| `tests/test_retrieval.py` | `retrieval` |
| `tests/test_generation.py` | `generation` |
| `tests/test_stability.py` | `stability` |
| `tests/test_e2e.py` | `e2e` |
| `tests/conftest.py` | `config` |
| `data/`、`scenarios/` | `data` |
| `.env`、`requirements.txt` | `config` |
| 跨模块多文件 | 取主要影响的模块，或用 `core` |

### 4. 生成 commit message

格式：

```
<type>(<scope>): <中文简短描述>

<中文详细说明——做了什么、为什么这样做>
```

**描述注意点：**
- 简短描述控制在 50 字以内，用句号结尾
- 详细说明列出关键变更点，每行一条，用 `- ` 开头
- 如果修复了具体问题，说明原因而非重复代码

### 5. 展示并确认

将生成的 message 展示给用户，明确询问是否提交。用户确认后执行：

```bash
git commit -m "<生成的message>"
```

**绝不**自动 push。用户要求时才 push。

## 示例

### 示例 1：新增功能

```
feat(embeddings): 新增硅基流动远程 Embedding API 支持

- 新增 create_remote_embeddings() 方法，通过 OpenAIEmbeddings 接入硅基流动
- rag_system.py 及 test_e2e.py 同步切换为远程 embedding
- 本地 HuggingFace 方式保留为降级方案
```

### 示例 2：修复测试

```
fix(test): 适配 Ragas 0.4.3 API 变更，修复全部测试

- ContextRelevancy 改名为 ContextRelevance，score key 改为 nv_context_relevance
- evaluate() 返回值由 dict 变为 EvaluationResult，scores[key] 返回 list
- AnswerRelevancy 需显式传入 embeddings 参数
- LangchainLLMWrapper 设置 bypass_n=True 避免 DeepSeek n>1 报错
```

### 示例 3：环境配置

```
chore(config): 修正 DeepSeek 模型名称并新增 Embedding API 配置

- DEEPSEEK_MODEL 修正为 deepseek-v4-pro（去除无效的 [1m] 后缀）
- 新增 EMBEDDING_API_KEY、EMBEDDING_BASE_URL、EMBEDDING_MODEL 配置项
```