# Koda — 智能体（Agent）运行框架

Koda 是一个分层、可插拔的 **AI 智能体（Agent）运行框架（Harness）**。它把大语言模型（LLM）封装成能**自主思考、调用工具、执行任务**的智能体，并提供命令行（CLI）、HTTP API 与可视化网页（Web UI）三种使用方式。

一句话概括：**让大模型不再只是"聊天"，而是能真正动手完成任务的助手。**

---

## 一、产品功能

### 1. 智能体核心能力

- **ReAct 单循环执行**：模型按"思考 → 行动 → 观察"的循环反复推理，直到完成任务（如"读取 README 并总结前三行"）。
- **规划式编排（Planner）**：任务先被拆解成"计划 → 子任务 → 汇总"多步执行，适合复杂任务（如"帮我分析这个项目的结构"）。
- **工具调用**：内置读取、写入、编辑文件，以及**沙箱 Bash 执行**等工具，让智能体能操作真实环境完成任务。
- **多模型兼容**：通过统一的 LLM 抽象层，可接入任何 OpenAI 兼容的模型（官方 OpenAI、DeepSeek、通义千问等），也可使用内置 Mock 模型无密钥体验。

### 2. 记忆与会话

- **短期记忆**（对话缓冲）：保留当前会话上下文。
- **长期记忆**（文件持久化）：跨会话记住用户偏好等信息，支持关键词检索。
- **会话暂停/恢复**：任务中断后可保存并恢复上下文继续执行。

### 3. 安全护栏（Guardrail）

- 默认拦截 `rm -rf /`、`git reset --hard`、`mkfs` 等危险命令，防止智能体误操作。
- 三种策略：直接拦截、命中时人工审批（`--ask`）、或放行（`--allow-destructive`）。

### 4. 可观测性

- **运行轨迹（Trace）**：记录完整执行过程，可导出 JSON。
- **执行摘要**：每次运行后展示耗时、LLM 调用数、工具调用数（含拦截数）、token 用量与**估算成本**。

### 5. 接入方式（三选一）

| 方式 | 适用场景 |
|---|---|
| **CLI 命令行** | 快速测试、脚本化执行、自动化任务 |
| **HTTP API** | 作为 OpenAI 兼容服务被其他系统集成 |
| **Web UI（网页界面）** | 图形化对话，开箱即用的中文聊天界面 |

### 6. 可视化网页（Web UI）

基于 **Open WebUI** 打造的简体中文聊天界面，作为 Koda 的图形入口：

- 开箱即用、**零本地模型下载**（嵌入/语音等能力全部走 API）。
- 界面内置两个"模型"：`koda-react`（ReAct 单循环）与 `koda-planner`（规划编排）。
- 支持多轮对话、用户管理、多语言切换等。

### 7. 其他特性

- **MCP（Model Context Protocol）扩展**：可通过配置文件接入 filesystem / github / sqlite 等 MCP 服务器，扩展工具能力。
- **环境零污染**：所有依赖、数据、日志均位于项目文件夹内，不写系统目录。

---

## 二、技术栈

### 后端（Koda 核心）

| 类别 | 技术 |
|---|---|
| 语言 | Python 3（Web UI 要求 3.11/3.12） |
| LLM 接入 | OpenAI 兼容协议（`openai` SDK），流式输出，统一抽象层 `LLM_BASE` |
| 数据模型 | `pydantic` |
| 配置管理 | `python-dotenv`（环境变量），支持多命名别名兼容 |
| 沙箱执行 | `docker`（不可用时自动回退本地执行） |
| HTTP 服务 | Python 标准库 `http.server`（`ThreadingHTTPServer`），无需额外依赖 |
| 可选扩展 | `mcp`（MCP 客户端） |
| 测试 | `pytest` |

### Web UI（Open WebUI）

| 类别 | 技术 |
|---|---|
| 前端框架 | Svelte 5 / SvelteKit，TypeScript |
| 构建工具 | Vite |
| 样式 | Tailwind CSS 4 |
| 编辑器/富文本 | CodeMirror 6、TipTap、ProseMirror |
| 图表/绘图 | Chart.js、Vega、Mermaid、Leaflet |
| 文档处理 | pdf.js、Mammoth、xlsx、jsPDF |
| 代码执行（可选） | Pyodide（WASM 运行 Python） |
| 后端 | FastAPI + Uvicorn |
| 数据存储 | SQLite |

### 部署环境

- **后端**：Python 3（`requirements.txt` 依赖）
- **Web UI**：Python 3.11/3.12 + Node.js 18+（构建前端）
- 跨平台（macOS / Linux / Windows）

---

## 三、如何部署

### 方式 A：仅用 CLI / HTTP API（轻量，无需前端）

```bash
# 1. 安装依赖（建议使用虚拟环境）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置模型（可选；不配置可用 --mock 体验完整流程）
cp .env.example .env
#    编辑 .env，填入 LLM_API_KEY / LLM_MODEL，第三方网关再填 LLM_BASE_URL

# 3. 启动 HTTP 服务（端口 8321）
python server.py --port 8321
```

### 方式 B：完整部署（CLI + API + 中文 Web UI）

项目内置一键脚本，自动完成环境准备与启动：

```bash
# 1. 首次部署：自检并补齐环境（Python venv、后端依赖、前端构建）
./scripts/setup_env.sh

# 2. 一键启动（后端 + 网页界面）
./scripts/start_webui.sh            # 前台运行
./scripts/start_webui.sh --daemon   # 后台运行

# 3. 停止
./scripts/stop_webui.sh
```

启动后浏览器打开 <http://127.0.0.1:3000>，默认管理员账号 `admin@koda.local` / `koda-local-1`（可在 `config/webui.env` 修改）。

### 配置你的模型

Koda 后端默认 `KODA_OPENAI_MOCK=auto`：**填了 key 就走真实模型，没填自动回退 mock**。

```bash
cp .env.example .env
# 编辑 .env：LLM_API_KEY / LLM_MODEL（第三方网关再填 LLM_BASE_URL）
./scripts/stop_webui.sh && ./scripts/start_webui.sh --daemon
```

键名兼容多种写法，可直接从别的项目复制 `.env`：

| 含义 | 依次识别的变量名 |
|---|---|
| 模型 | `LLM_MODEL` → `OPENAI_MODEL` → `MODEL_NAME` |
| 密钥 | `LLM_API_KEY` → `OPENAI_API_KEY` → `API_KEY` |
| 地址 | `LLM_BASE_URL` → `LLM_API_BASE` → `OPENAI_BASE_URL` → `OPENAI_API_BASE` |

### 关键配置一览

**`.env`**（Koda 模型配置）

| 变量 | 说明 |
|---|---|
| `LLM_API_KEY` | API Key；留空则自动回退 mock 模式 |
| `LLM_MODEL` | 模型名，如 `gpt-4o-mini` / `deepseek-chat` / `qwen-plus` |
| `LLM_BASE_URL` | OpenAI 兼容网关地址（需带 `/v1` 后缀）；官方可留空 |
| `LLM_PROVIDER` | 供应商标识（目前仅 openai 兼容协议） |

**`config/webui.env`**（Web UI 界面侧配置）

| 变量 | 说明 |
|---|---|
| `KODA_PORT` / `WEBUI_PORT` | 后端 / 界面端口（默认 8321 / 3000） |
| `KODA_OPENAI_MOCK` | `auto`（推荐）/ `1` 强制 mock / `0` 强制真实模型 |
| `DEFAULT_LOCALE` | 界面默认语言（已设 `zh-CN`） |
| `WEBUI_ADMIN_EMAIL` / `WEBUI_ADMIN_PASSWORD` | 预置管理员账号 |
| `RAG_EMBEDDING_ENGINE` 等 | 零本地模型下载策略 |

### 手动部署（不依赖脚本）

```bash
# 终端 1：Koda 后端
KODA_OPENAI_MOCK=1 python server.py --port 8321   # 无 API key 时用 mock 体验

# 终端 2：Open WebUI（源码后端 + 已构建前端）
export PYTHONPATH="$(pwd)/webui/backend"
export OPENAI_API_BASE_URL=http://127.0.0.1:8321/v1
export OPENAI_API_KEY=koda-local
export ENABLE_OLLAMA_API=false
export DEFAULT_LOCALE=zh-CN
.venvs/webui-venv/bin/python -m uvicorn open_webui.main:app --host 127.0.0.1 --port 3000
```

---

## 四、如何使用

### 1. 命令行（CLI）

```bash
# ReAct 模式：直接下达任务
python main.py "读取 README 并总结前三行"

# 规划模式：先计划后执行
python main.py --planner "帮我分析这个项目的结构"

# 无 API key 体验（Mock LLM）
python main.py --mock "hello"
python main.py --mock --planner "演示"

# 交互模式：不带参数进入对话
python main.py
```

CLI 常用参数：

| 参数 | 说明 |
|---|---|
| `--planner` | 使用规划式编排 |
| `--mock` | 使用 Mock LLM（无需 API key） |
| `--ask` | 命中危险命令时人工确认 |
| `--allow-destructive` | 直接放行危险命令（慎用） |
| `--no-mcp` | 不加载 MCP 工具 |
| `--no-stream` | 关闭流式输出 |
| `--max-steps N` | 最大推理步数 |
| `--trace PATH` | 运行轨迹保存为 JSON（含 token/成本估算） |

执行结束后会打印摘要：耗时、LLM 调用数、工具调用数（含拦截数）、token 与估算成本。

### 2. HTTP API

```bash
python server.py --port 8321
```

```bash
# 健康检查
GET  /health

# OpenAI 兼容：模型列表
GET  /v1/models

# OpenAI 兼容：对话（可 stream）
POST /v1/chat/completions
#   {"model": "koda-react", "messages": [{"role": "user", "content": "..."}], "stream": false}

# Koda 原生接口
POST /chat
#   {"question": "...", "mode": "react|planner", "mock": false}
```

`/chat` 响应包含 `content`（最终回复）、`summary`（执行摘要）与 `trace`（完整轨迹）。

### 3. 网页界面（Web UI）

启动后在浏览器打开 <http://127.0.0.1:3000>，登录后在模型下拉框选择 `koda-react` 或 `koda-planner`，即可像普通 AI 聊天一样下达任务。Koda 会自主调用工具、执行命令并返回结果。

---

## 五、项目结构

```
Koda/
├── main.py                 # CLI 入口
├── server.py               # HTTP API 服务（OpenAI 兼容端点 /v1）
├── openai_adapter.py       # OpenAI 兼容适配层
├── config.py               # 模型配置（环境变量别名解析）
├── agent/                  # 智能体编排（ReAct 单循环 / Planner 规划）
├── llm/                    # LLM 抽象（OpenAI 流式 / Mock）
├── tools/                  # 工具注册表（read/write/edit/bash/MCP）
├── memory/                 # 记忆层（短期缓冲 / 长期文件）
├── core/                   # 安全护栏 / 轨迹追踪 / 会话管理
├── prompt/                 # 人设与提示词模板
├── scripts/                # 一键部署脚本（setup / start / stop）
├── webui/                  # Open WebUI 源码（汉化版）与前端构建产物
├── config/webui.env        # Web UI 界面侧配置
├── data/webui/             # 运行数据（SQLite / 上传 / 缓存）
└── runtime/                # 运行日志与进程号
```

---

## 六、架构概览

```
┌──────────────────────────────────────────────────────────┐
│ 入口层   main.py (CLI)  ·  server.py (HTTP API)           │
├──────────────────────────────────────────────────────────┤
│ 编排层   agent/react.py  ReAct 单循环                     │
│          agent/planner.py 规划式编排（计划→子任务→汇总）   │
├──────────────────────────────────────────────────────────┤
│ 能力层   llm/      LLM_BASE 抽象 · OpenAI 流式 · Mock     │
│          tools/    ToolBase · ToolRegistry · read/write/  │
│                    edit/bash(沙箱) · MCP 客户端            │
│          memory/   BufferMemory(短期) · FileMemory(长期)   │
├──────────────────────────────────────────────────────────┤
│ 横切层   core/guardrail.py  危险命令拦截 + 人工审批        │
│          core/tracer.py     事件轨迹 + token/成本估算      │
│          core/session.py    会话状态机 save/restore        │
│          prompt/            alpha.md persona + 模板        │
└──────────────────────────────────────────────────────────┘
```

---

## 七、测试

```bash
pip install pytest
pytest tests/ -v
```

覆盖：工具注册表与执行、ReAct 工具循环、护栏（拦截/放行/人工审批）、Planner 计划解析与执行、长期记忆持久化、Tracer 汇总与落盘、会话保存/恢复。

---

## 八、路线图（未实现，可扩展）

- 向量检索长期记忆（替换关键词打分）
- 多智能体协作 / 子 Agent 并行
- 结构化可观测性接入（OpenTelemetry 等）
- 异步 Agent（asyncio）
- 模型成本参数按实际供应商配置化