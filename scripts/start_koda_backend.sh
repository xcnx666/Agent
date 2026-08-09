#!/usr/bin/env bash
# 启动 Koda OpenAI 兼容后端（Open WebUI 的"模型"来源）
#
# 用法:
#   ./scripts/start_koda_backend.sh
# 环境变量:
#   KODA_PY            指定运行 Koda 的 Python（可选，优先级最高）
#   KODA_PORT          监听端口（默认 8321）
#   KODA_OPENAI_MOCK   1 = mock 模式 / 0 = 真实模型 / auto = 有 key 就用真实模型
set -e
cd "$(dirname "$0")/.."

KODA_PORT="${KODA_PORT:-8321}"

pick_python() {
  # 1) 显式指定
  if [ -n "$KODA_PY" ] && [ -x "$KODA_PY" ]; then echo "$KODA_PY"; return; fi
  # 2) 项目内 webui venv（已含 pydantic / openai / dotenv）
  if [ -x ".venvs/webui-venv/bin/python" ] && \
     .venvs/webui-venv/bin/python -c "import pydantic" >/dev/null 2>&1; then
    echo ".venvs/webui-venv/bin/python"; return
  fi
  # 3) 受管 Python 环境
  MANAGED="$HOME/.workbuddy/binaries/python/envs/default/bin/python"
  if [ -x "$MANAGED" ] && "$MANAGED" -c "import pydantic" >/dev/null 2>&1; then
    echo "$MANAGED"; return
  fi
  # 4) 系统 python
  command -v python3 >/dev/null 2>&1 && echo "python3" || echo "python"
}

# ---- mock 模式判定：auto = .env 里有 LLM_API_KEY 就走真实模型 ----
resolve_mock() {
  local m="${KODA_OPENAI_MOCK:-auto}"
  if [ "$m" = "1" ] || [ "$m" = "0" ]; then echo "$m"; return; fi
  # auto：探测 .env 中的 key 是否非空
  local key=""
  if [ -f ".env" ]; then
    key="$(grep -E '^[[:space:]]*(LLM_API_KEY|OPENAI_API_KEY)[[:space:]]*=' .env 2>/dev/null \
           | head -1 | cut -d= -f2- | tr -d ' \r\"'"'")"
  fi
  [ -z "$key" ] && key="${LLM_API_KEY:-}"
  if [ -n "$key" ]; then echo "0"; else echo "1"; fi
}

MOCK="$(resolve_mock)"
export KODA_OPENAI_MOCK="$MOCK"

PY="$(pick_python)"
echo "Koda 后端 Python: $PY"
echo "Koda OpenAI 兼容端点 -> http://127.0.0.1:${KODA_PORT}/v1"
if [ "$MOCK" = "1" ]; then
  echo "模式: mock（.env 里未检测到 LLM_API_KEY）"
  echo "      → 填好 .env 的 LLM_API_KEY / LLM_API_BASE / LLM_MODEL 后重启即自动切真实模型"
else
  echo "模式: 真实模型（读取 .env 的 LLM_API_KEY / LLM_API_BASE / LLM_MODEL）"
fi

exec "$PY" server.py --port "${KODA_PORT}"
