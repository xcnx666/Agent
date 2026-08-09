#!/usr/bin/env bash
# 一键启动：Koda OpenAI 兼容后端 + Open WebUI（简体中文界面）
#
# 用法:
#   ./scripts/start_webui.sh              # 前台启动（Ctrl+C 一起停止）
#   ./scripts/start_webui.sh --daemon     # 后台启动，日志写入 runtime/logs/
#
# 所有环境配置集中在 config/webui.env，数据落在项目内 data/webui。
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

DAEMON=0
case "${1:-}" in
  --daemon|-d) DAEMON=1 ;;
esac

# ---------- 1. 加载项目内配置 ----------
if [ -f "config/webui.env" ]; then
  set -a; . ./config/webui.env; set +a
fi
KODA_PORT="${KODA_PORT:-8321}"
WEBUI_PORT="${WEBUI_PORT:-3000}"
WEBUI_PY="${WEBUI_PY:-$ROOT/.venvs/webui-venv/bin/python}"

# ---------- 2. 环境自检 ----------
if [ ! -x "$WEBUI_PY" ]; then
  echo "❌ 未找到 Python 环境: $WEBUI_PY"
  echo "   请先执行: ./scripts/setup_env.sh"
  exit 1
fi
if [ ! -f "webui/build/index.html" ]; then
  echo "❌ 前端未构建（缺 webui/build/index.html）"
  echo "   请先执行: ./scripts/setup_env.sh"
  exit 1
fi

# ---------- 3. 目录（全部在项目内） ----------
mkdir -p "$ROOT/data/webui/cache" "$ROOT/runtime/logs"
export DATA_DIR="$ROOT/data/webui"
export FRONTEND_BUILD_DIR="$ROOT/webui/build"
# 所有缓存目录也收进项目内，绝不写用户主目录
export HF_HOME="$ROOT/data/webui/cache/huggingface"
export SENTENCE_TRANSFORMERS_HOME="$ROOT/data/webui/cache/sentence_transformers"
export TIKTOKEN_CACHE_DIR="$ROOT/data/webui/cache/tiktoken"

# ---------- 4. Python 路径：源码后端优先，依赖从 target 目录补齐 ----------
PP="$ROOT/webui/backend"
[ -d "$ROOT/.venvs/webui-target" ] && PP="$PP:$ROOT/.venvs/webui-target"
export PYTHONPATH="$PP${PYTHONPATH:+:$PYTHONPATH}"

# ---------- 5. 让 Open WebUI 把 Koda 当作模型后端 ----------
export OPENAI_API_BASE_URL="http://127.0.0.1:${KODA_PORT}/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-koda-local}"
export ENABLE_OLLAMA_API="${ENABLE_OLLAMA_API:-false}"
export DEFAULT_LOCALE="${DEFAULT_LOCALE:-zh-CN}"

echo "────────────────────────────────────────────"
echo " Koda × Open WebUI（简体中文）"
echo " 数据目录 : $DATA_DIR"
echo " 前端目录 : $FRONTEND_BUILD_DIR"
echo " 后端源码 : $ROOT/webui/backend"
echo " 模型策略 : 零本地下载（嵌入/语音全走 API，OFFLINE_MODE=${OFFLINE_MODE:-false}）"
echo "────────────────────────────────────────────"

# ---------- 6. 启动 Koda 后端 ----------
echo "[1/2] 启动 Koda OpenAI 兼容后端 :${KODA_PORT}"
if [ "$DAEMON" = "1" ]; then
  # nohup + disown：脱离当前终端会话，关掉终端也继续运行
  KODA_PORT="$KODA_PORT" nohup ./scripts/start_koda_backend.sh \
    > "$ROOT/runtime/logs/koda-backend.log" 2>&1 &
  KODA_PID=$!
  disown "$KODA_PID" 2>/dev/null || true
else
  KODA_PORT="$KODA_PORT" ./scripts/start_koda_backend.sh &
  KODA_PID=$!
fi
echo "$KODA_PID" > "$ROOT/runtime/koda-backend.pid"

for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${KODA_PORT}/health" >/dev/null 2>&1 && break
  sleep 0.5
done
if curl -sf "http://127.0.0.1:${KODA_PORT}/health" >/dev/null 2>&1; then
  echo "      ✔ Koda 后端就绪"
else
  echo "      ⚠ Koda 后端未就绪，请查看 runtime/logs/koda-backend.log"
fi

# ---------- 7. 启动 Open WebUI ----------
echo "[2/2] 启动 Open WebUI :${WEBUI_PORT}"
if [ "$DAEMON" = "1" ]; then
  # nohup + disown：脱离当前 shell 会话，脚本退出后进程继续存活
  nohup "$WEBUI_PY" -m uvicorn open_webui.main:app \
    --host 127.0.0.1 --port "${WEBUI_PORT}" \
    > "$ROOT/runtime/logs/open-webui.log" 2>&1 &
  WEBUI_PID=$!
  disown "$WEBUI_PID" 2>/dev/null || true
  echo "$WEBUI_PID" > "$ROOT/runtime/open-webui.pid"

  for i in $(seq 1 90); do
    curl -sf "http://127.0.0.1:${WEBUI_PORT}/health" >/dev/null 2>&1 && break
    kill -0 "$WEBUI_PID" 2>/dev/null || break
    sleep 1
  done
  if curl -sf "http://127.0.0.1:${WEBUI_PORT}/health" >/dev/null 2>&1; then
    echo ""
    echo "✅ 启动完成 → http://127.0.0.1:${WEBUI_PORT}"
    echo "   账号: ${WEBUI_ADMIN_EMAIL:-admin@koda.local} / ${WEBUI_ADMIN_PASSWORD:-koda-local-1}"
    echo "   模型: koda-react（单循环） / koda-planner（规划编排）"
    echo "   停止: ./scripts/stop_webui.sh"
  else
    echo "❌ Open WebUI 启动失败，日志: runtime/logs/open-webui.log"
    kill "$KODA_PID" 2>/dev/null || true
    exit 1
  fi
else
  trap 'echo ""; echo "正在停止..."; kill $KODA_PID 2>/dev/null || true' EXIT
  echo ""
  echo "✅ 界面地址 → http://127.0.0.1:${WEBUI_PORT}"
  echo "   账号: ${WEBUI_ADMIN_EMAIL:-admin@koda.local} / ${WEBUI_ADMIN_PASSWORD:-koda-local-1}"
  echo ""
  exec "$WEBUI_PY" -m uvicorn open_webui.main:app --host 127.0.0.1 --port "${WEBUI_PORT}"
fi
