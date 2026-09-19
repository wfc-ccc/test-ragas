# 高升 AI 接口自动化测试框架

> 版本：v1.0.0 · 接口文档：v1.0.0  
> Base URL：`http://127.0.0.1:10010`  

---

## 一、项目简介

本项目是针对 **高升AI 智能助理接口** 的自动化测试框架，严格遵循用户偏好的**四层自动化架构**：

```
gs_api/
├── base/      # 公共基础层：配置、HTTP 客户端、Selenium 基类、日志、断言、数据加载
├── page/      # 接口 / UI 操作层：会话、聊天、历史会话、知识库、语音、Web UI
├── script/    # pytest 测试脚本层：7 套测试脚本 + conftest 共享 fixtures
└── report/    # 报告层：Allure 报告管理 + Ragas AI 回答质量评估
```

### 设计理念

| 特性 | 说明 |
|---|---|
| **四层架构** | base → page → script → report 清晰分层，便于维护与扩展 |
| **数据驱动** | 采用 **YAML + CSV** 双格式管理测试数据，符合用户数据驱动偏好 |
| **AI 质量评估** | 深度集成项目原有的 **Ragas** 框架，对高升AI回答做 Faithfulness / AnswerRelevancy / ContextRecall 多维度评估 |
| **Allure 报告** | 自动生成环境信息、缺陷分类、Ragas 评估明细、截图等富媒体附件 |
| **Selenium 辅助** | base 层提供完整的 Selenium 公共方法，支撑后续 Web UI 冒烟测试 |

---

## 二、目录结构

```
test-ragas/
├── gs_api/                              # ★ 高升AI测试框架根目录
│   ├── __init__.py                      #   框架元信息 + 各层统一导出
│   ├── base/                            #   base 层：公共基础封装
│   │   ├── config.py                    #     全局配置管理（默认值 → YAML → 环境变量）
│   │   ├── http_client.py               #     HTTP 客户端 + 流式 SSE（1001/1002/1003）解析
│   │   ├── selenium_base.py             #     ★ Selenium 公共方法基类
│   │   ├── logger.py                    #     统一日志（控制台 + 文件 + Allure 挂载）
│   │   ├── assertions.py                #     通用断言集合 + Ragas 阈值断言
│   │   ├── data_loader.py               #     ★ YAML / CSV 数据驱动加载器
│   │   └── __init__.py
│   ├── page/                            #   page 层：接口与 UI 操作封装
│   │   ├── session_page.py              #     会话接口（新建 / 热门问题）
│   │   ├── chat_page.py                 #     聊天接口（流式 / 停止 / 文本 / 模版）
│   │   ├── history_page.py              #     历史会话（详情 / 列表 / 更新标题 / 删除）
│   │   ├── embedding_page.py            #     知识库向量（embedding CRUD / 搜索）
│   │   ├── audio_page.py                #     语音接口（STT / TTS / TTS-Stream）
│   │   ├── web_page.py                  #     ★ 高升AI Web UI 辅助操作
│   │   └── __init__.py
│   ├── report/                          #   report 层：报告 + AI 质量评估
│   │   ├── allure_manager.py            #     Allure 环境、分类、HTML 报告生成
│   │   ├── ragas_evaluator.py           #     ★ Ragas 多维度评估（阈值断言 + DataFrame 输出）
│   │   └── __init__.py
│   ├── script/                          #   script 层：pytest 自动化脚本
│   │   ├── conftest.py                  #     ★ 共享 fixtures + pytest 生命周期钩子
│   │   ├── test_01_session.py           #     一、会话接口测试
│   │   ├── test_02_chat.py              #     二、聊天接口测试（含流式+Ragas）
│   │   ├── test_03_history.py           #     三、历史会话测试（CRUD 闭环）
│   │   ├── test_04_embedding.py         #     四、知识库向量接口测试
│   │   ├── test_05_audio.py             #     五、语音接口测试（STT/TTS/TTS-Stream）
│   │   ├── test_06_ragas_quality.py     #     ★ 六、Ragas AI 质量评估套件（核心）
│   │   ├── test_07_web_ui_smoke.py      #     七、Web UI 冒烟（默认跳过）
│   │   └── __init__.py
│   ├── config/
│   │   └── config.yaml                  # 全局配置文件（可被环境变量覆盖）
│   └── data/
│       ├── test_data.yaml               # ★ YAML 测试数据（课程咨询 / FAQ / 向量 / 语音）
│       └── qa_data.csv                  # ★ CSV 问答对（数据驱动 + Ragas 批量评估）
│
├── src/                                 # 原有 RAG 系统（被 Ragas 复用为上下文检索）
│   ├── rag_system.py
│   ├── llm.py
│   ├── embeddings.py
│   └── vector_store.py
├── tests/                               # 原有 RAG 单元测试（不影响 gs_api）
├── data/sample_docs/                    # 原有知识库文档（Ragas Context 使用）
├── scenarios/                           # 原有场景文档
├── pytest.ini                           # pytest markers / addopts 配置
├── requirements.txt                     # 项目依赖（新增 allure-pytest / selenium / pyyaml 等）
├── .env.example                         # 环境变量示例
├── run_gs_api_tests.ps1                 # Windows PowerShell 一键运行
└── run_gs_api_tests.sh                  # macOS / Linux bash 一键运行
```

---

## 三、接口覆盖清单

对照 **aitj v1.0.0 接口文档**，18 个接口全覆盖：

| 编号 | 模块 | 方法 · 路径 | 测试脚本 |
|---|---|---|---|
| 1  | 会话 | `POST /ais/session` 新建会话 | [test_01_session.py](gs_api/script/test_01_session.py) |
| 2  | 会话 | `GET  /ais/session/hot` 热门问题 | [test_01_session.py](gs_api/script/test_01_session.py) |
| 3  | 聊天 | `POST /ais/chat` 流式聊天（SSE 1001/1002/1003） | [test_02_chat.py](gs_api/script/test_02_chat.py) |
| 4  | 聊天 | `POST /ais/chat/stop` 停止生成 | [test_02_chat.py](gs_api/script/test_02_chat.py) |
| 5  | 聊天 | `POST /ais/chat/text` 文本聊天（不保存） | [test_02_chat.py](gs_api/script/test_02_chat.py) |
| 6  | 聊天 | `GET  /ais/chat/templates` 模版列表 | [test_02_chat.py](gs_api/script/test_02_chat.py) |
| 7  | 历史 | `GET  /ais/session/{sessionId}` 会话详情 | [test_03_history.py](gs_api/script/test_03_history.py) |
| 8  | 历史 | `GET  /ais/session/history` 历史会话列表 | [test_03_history.py](gs_api/script/test_03_history.py) |
| 9  | 历史 | `PUT  /ais/session/history` 更新标题 | [test_03_history.py](gs_api/script/test_03_history.py) |
| 10 | 历史 | `DELETE /ais/session/history` 删除会话 | [test_03_history.py](gs_api/script/test_03_history.py) |
| 11 | 知识库 | `GET    /ais/embedding` 文本转向量 | [test_04_embedding.py](gs_api/script/test_04_embedding.py) |
| 12 | 知识库 | `POST   /ais/embedding` 保存文本 | [test_04_embedding.py](gs_api/script/test_04_embedding.py) |
| 13 | 知识库 | `DELETE /ais/embedding` 删除文本 | [test_04_embedding.py](gs_api/script/test_04_embedding.py) |
| 14 | 知识库 | `GET    /ais/embedding/search` 内容搜索 | [test_04_embedding.py](gs_api/script/test_04_embedding.py) |
| 15 | 知识库 | `GET    /ais/embedding/search/all` 搜索全部 | [test_04_embedding.py](gs_api/script/test_04_embedding.py) |

---

## 四、快速开始

### 4.1 环境准备

```bash
# 1. 进入项目目录
cd test-ragas

# 2. 推荐使用 Python 3.10+ 创建虚拟环境
python -m venv .venv

# 3. Windows 激活
.venv\Scripts\Activate.ps1
#    或 macOS/Linux
source .venv/bin/activate

# 4. 安装依赖（新增 allure-pytest / selenium / pyyaml / pandas 等）
pip install -r requirements.txt
```

### 4.2 环境变量配置

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 必须 | 说明 |
|---|---|---|
| `AIS_TOKEN` | 部分接口需要 | 高升AI登录 token，通过 `Authorization` header 传递 |
| `DEEPSEEK_API_KEY` | **Ragas 需要** | 评估 LLM 的 DeepSeek API Key（用于 Faithfulness 等指标） |
| `DEEPSEEK_BASE_URL` | 可选 | 默认 `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 可选 | 默认 `deepseek-chat` |
| `EMBEDDING_API_KEY` | Ragas 推荐 | 硅基流动/SiliconFlow Embedding Key（用于 AnswerRelevancy 语义相似度） |
| `EMBEDDING_BASE_URL` | 可选 | 默认 `https://api.siliconflow.cn/v1` |
| `EMBEDDING_MODEL` | 可选 | 默认 `Qwen/Qwen3-Embedding-0.6B` |

或直接修改 [gs_api/config/config.yaml](gs_api/config/config.yaml)（YAML 优先级低于环境变量）。

### 4.3 Allure 命令行安装（可选，用于生成 HTML 报告）

- Windows：`scoop install allure` 或从 <https://allurereport.org/docs/getting-started-installation/> 下载
- macOS：`brew install allure`
- Linux：`sudo apt-get install allure`

---

## 五、运行测试

### 5.1 一键运行（推荐）

**Windows PowerShell：**
```powershell
# 冒烟用例（会话+聊天+历史+Ragas），默认生成 Allure 结果
.\run_gs_api_tests.ps1

# 全量用例（含语音 / 向量 / Web UI）
.\run_gs_api_tests.ps1 -All

# 运行后自动用浏览器打开 Allure HTML
.\run_gs_api_tests.ps1 -OpenReport

# 自定义 markers
.\run_gs_api_tests.ps1 -Markers "session and chat"
```

**macOS / Linux bash：**
```bash
bash run_gs_api_tests.sh         # 冒烟
bash run_gs_api_tests.sh all     # 全量
MARKERS="ragas" bash run_gs_api_tests.sh   # 仅跑 Ragas
```

### 5.2 直接使用 pytest

```bash
# 冒烟（含 Ragas AI 质量评估）
pytest gs_api/script -m smoke -v \
       --alluredir gs_api/report/output/allure_results \
       --clean-alluredir

# 仅跑会话接口
pytest gs_api/script/test_01_session.py -v

# 仅跑 Ragas AI 质量评估（需要 DEEPSEEK_API_KEY）
pytest gs_api/script/test_06_ragas_quality.py -v -s

# 跑全量（不做任何过滤）
pytest gs_api/script -v

# 生成 Allure HTML 报告
allure generate gs_api/report/output/allure_results \
       -o gs_api/report/output/allure_html --clean

# 直接用浏览器打开 Allure 报告
allure open gs_api/report/output/allure_html
```

### 5.3 pytest markers 清单

| marker | 说明 | 覆盖脚本 |
|---|---|---|
| `smoke` | 冒烟测试（核心必跑） | test_01 / test_02 / test_03 / test_06 |
| `session` | 会话接口 | test_01_session.py |
| `chat` | 聊天接口 | test_02_chat.py |
| `history` | 历史会话接口 | test_03_history.py |
| `embedding` | 知识库向量接口 | test_04_embedding.py |
| `audio` | 语音接口 | test_05_audio.py |
| `ragas` | **Ragas AI 回答质量评估** | test_02 / test_06_ragas_quality.py |
| `webui` | Web UI 冒烟（默认跳过） | test_07_web_ui_smoke.py |

---

## 六、Ragas AI 回答质量评估

本框架深度集成项目原有的 **Ragas** 评估机制，核心逻辑位于 [gs_api/report/ragas_evaluator.py](gs_api/report/ragas_evaluator.py)。

### 6.1 评估指标

| 指标 | 说明 | 阈值 |
|---|---|---|
| **Faithfulness** | 回答忠实度：基于上下文不编造事实 | ≥ 0.6 |
| **AnswerRelevancy** | 回答与问题的语义相关性 | ≥ 0.6 |
| **ContextRecall** | 上下文召回：回答是否充分覆盖参考答案 | ≥ 0.6 |
| ContextRelevance | 检索到的上下文是否与问题相关 | 可选 |

阈值可在 [gs_api/config/config.yaml](gs_api/config/config.yaml) → `ragas.threshold` 中调整。

### 6.2 评估场景（test_06_ragas_quality.py）

| 场景 | 说明 | 数据来源 |
|---|---|---|
| **通用问答** | 自我介绍 / 能力介绍 / RAG 概念 | 内置 3 条 |
| **课程咨询** | 价格 / 课时 / 学习路径 / 就业推荐 | `data/sample_docs/*.txt` 向量检索作为上下文 |
| **平台 FAQ** | 试听退款 / 结业证书 / 视频下载 | 内置 3 条 + RAG 上下文 |
| **CSV 批量** | 最多 12 条 Q&A 对 | [gs_api/data/qa_data.csv](gs_api/data/qa_data.csv) |
| **多轮记忆** | 第 2 轮用「这门课」指代 + 指代消解 | 流式会话串联 |

### 6.3 上下文复用项目原有 RAG 系统

为了让 Faithfulness 得分准确，Ragas 需要 retrieved_contexts。框架自动复用 `src.rag_system.RAGSystem` 的向量库：

```python
# 伪代码示意（真实实现位于 test_06_ragas_quality.py）
from src.rag_system import RAGSystem
rag = RAGSystem(...)
rag.load_and_index("data/sample_docs/")
contexts = rag._retrieve_documents(question)  # 作为 Ragas 的 retrieved_contexts
```

### 6.4 Allure 报告中的 Ragas 结果

每个 Ragas 用例会自动挂载两份附件：
- **Ragas评估明细-CSV / HTML**：每个问题的每个指标的得分表格
- **Ragas评估汇总**：每个指标的均值 + 样本数

---


## 七、四层架构详解

### 8.1 base 层：公共基础

| 模块 | 关键方法 / 能力 |
|---|---|
| [config.py](gs_api/base/config.py) | `config.base_url` / `config.token` / `config.get("ragas.threshold.faithfulness")` 三层优先级 |
| [http_client.py](gs_api/base/http_client.py) | `get / post / put / delete` + `post_stream()` 流式 SSE 逐行解析 → `StreamEvent(1001/1002/1003)` |
| [selenium_base.py](gs_api/base/selenium_base.py) | 8 种定位方式 + `wait_visible / wait_clickable` + 截图 + iframe + Alert + JS 滚动 |
| [assertions.py](gs_api/base/assertions.py) | `assert_api_success()` + 字段类型断言 + `assert_ragas_score()` |
| [data_loader.py](gs_api/base/data_loader.py) | `load_yaml("test_data.yaml")` / `load_csv("qa_data.csv")` / `load_qa_pairs()` |
| [logger.py](gs_api/base/logger.py) | INFO 级控制台 + DEBUG 级文件，同时支持 `attach_log_to_allure()` |

### 7.2 page 层：接口封装（示例：聊天流式）

```python
# 示例：聊天接口 page 使用
from gs_api.page import ChatPage

chat = ChatPage()

# ① 文本聊天（不保存记录）
resp = chat.chat_text("你好高升AI")
answer = chat.chat_text_get_answer("《Java高级架构与微服务》学到什么？")

# ② 流式聊天 → 拼接成完整回答 + 事件列表
full_text, events = chat.chat_stream_full(
    question="解释微服务和单体的区别",
    session_id="xxx-session-id",
)
for ev in events:
    if ev.is_data:       # eventType == 1001
        print(ev.event_data, end="")
    elif ev.is_stop:     # eventType == 1002
        print("\n[停止]")
```

### 7.3 script 层：conftest fixtures 一览

在 [gs_api/script/conftest.py](gs_api/script/conftest.py) 中提供以下共享 fixtures：

| fixture | scope | 说明 |
|---|---|---|
| `http_client` | session | 共享 `HttpClient` 实例（连接池） |
| `session_page` / `chat_page` / `history_page` / `embedding_page` / `audio_page` | session | 5 大 Page 实例 |
| `web_page` | function | 每个用例独立 Selenium 浏览器，自动 quit |
| `shared_session_id` | module | 模块级共享会话 ID：模块开始新建一次会话，供所有接口串联 |
| `evaluator_llm` / `evaluator_embeddings` | session | 复用项目原有的 DeepSeek LLM + 硅基流动 Embeddings（Ragas 评估） |
| `ragas_evaluator` | session | 构造好的 `GaoShengRagasEvaluator` 实例 |
| `gs_test_data` | session | `test_data.yaml` 顶层 dict |
| `gs_qa_pairs` | session | `qa_data.csv` Q&A 对列表 |
| `gao_sheng_expected_keyword` | function | 固定值 `"高升"`，用于断言 |

生命周期钩子：
- `pytest_configure`：启动时自动清空 Allure 结果、写入 `environment.properties` + `categories.json`
- markers 注册：8 种接口 + 级别 marker

### 7.4 report 层：Allure + Ragas 协同

```
pytest --alluredir → 生成 JSON/TXT/附件
        ↓
AllureManager.write_environment() → 环境信息
AllureManager.write_categories()  → 缺陷分类
AllureManager.attach_ragas_table(df) → Ragas DataFrame → CSV + HTML
        ↓
allure generate → 生成 HTML 报告（可 allure open 打开）
```

---

## 八、数据驱动（YAML + CSV）

### 8.1 YAML：复杂结构数据

[gs_api/data/test_data.yaml](gs_api/data/test_data.yaml) 按模块组织：

```yaml
sessions:
  default_n: 3
  expected_title_keyword: "高升"

questions:
  course_consultation:
    - question: "Python 编程入门课的价格是多少？"
      reference: "高升Python编程入门课（PY-101）价格199元..."
      type: "course"

history:
  update_titles: ["高升AI-自动化测试-会话A", "高升AI-自动化测试-会话B"]

embedding:
  save_messages:
    - "高升Python编程入门课..."
    - "高升Web前端开发实战..."
```

### 8.2 CSV：扁平 Q&A 列表

[gs_api/data/qa_data.csv](gs_api/data/qa_data.csv) 格式：

```csv
question,contexts,reference,type
"高升Python编程入门课的价格是多少？","PY-101|199元|40课时","价格199元，共40课时。",course
```

`data_loader.load_qa_pairs()` 会自动清洗并返回 list[dict]，直接喂给 Ragas 批量评估。

---

## 九、常见问题

**Q1：运行报错缺少 `DEEPSEEK_API_KEY`？**
A：没有 Key 时，标记 `@requires_llm` 的用例会自动 skip。若只想跑接口功能（不含 Ragas），请用 `-m "smoke and not ragas"`。

**Q2：流式聊天接口返回的每行 JSON 格式不同？**
A：`http_client.post_stream()` 已做容错，解析失败的行会被跳过并继续，不会抛出异常。可通过返回的 `events` 列表查看所有解析到的事件。

**Q3：STT（语音转文字）用例总是被跳过？**
A：需要把待识别的 wav 文件放到 `gs_api/data/sample_stt.wav`；否则自动 skip，避免误报。

**Q4：如何调整 Ragas 的通过阈值？**
A：编辑 `gs_api/config/config.yaml` 中 `ragas.threshold.*` 字段，或者直接用环境变量对应配置。

**Q5：Allure 报告中文显示乱码？**
A：请确保系统安装 `allure 2.20+`，并使用 PowerShell 7+ 或新版终端，UTF-8 编码已在所有写入中强制启用。

---

## 十、扩展指南

### 新增接口测试

1. 在对应 `page/*.py` 中添加接口方法，使用 `@allure.step` 标注
2. 在 `script/test_*.py` 中新增用例类，使用 `assertions` 断言
3. 在 `pytest.ini` + `conftest.py` 中注册 marker（如果是新模块）

### 新增 Ragas 自定义指标

```python
from ragas.metrics.base import Metric
class MyMetric(Metric):
    name = "my_custom_score"
    def score(self, ...): return 0.95

# 在 conftest 中注入 GaoShengRagasEvaluator
evaluator = GaoShengRagasEvaluator(metric_names=["faithfulness", "my_custom_score"])
```

---

**© 高升AI 接口自动化测试框架 v1.0.0 · 基于 RAGAS + Allure + Selenium 四层架构**
