#!/usr/bin/env bash
# 一键在【项目文件夹内】准备 Koda × Open WebUI 运行环境
#
#   .venvs/webui-venv     Python 3.12 虚拟环境（运行 Open WebUI + Koda 后端）
#   .venvs/webui-target   依赖隔离目录（部分环境下 pip 直装受限时的兜底）
#   webui/build           前端构建产物（简体中文界面）
#   data/webui            运行数据（SQLite / 缓存 / 上传）
#   runtime/logs          运行日志
#
# 用法: ./scripts/setup_env.sh
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "════════════════════════════════════════════"
echo " Koda × Open WebUI 环境准备（全部位于项目内）"
echo "════════════════════════════════════════════"

# ---------- 1. 定位 Python 3.12（open-webui 要求 >=3.11,<3.13） ----------
find_py312() {
  for c in "$ROOT/.venvs/webui-venv/bin/python" "$ROOT/.venvs/webui/bin/python" \
           "$(command -v python3.12 2>/dev/null)" "$(command -v python3.11 2>/dev/null)"; do
    [ -n "$c" ] && [ -x "$c" ] || continue
    v="$("$c" -c 'import sys;print(f"{sys.version_info[0]}{sys.version_info[1]}")' 2>/dev/null || echo 0)"
    if [ "$v" = "312" ] || [ "$v" = "311" ]; then echo "$c"; return; fi
  done
}

PY312="$(find_py312 || true)"
if [ -z "$PY312" ]; then
  echo "→ 未找到 Python 3.11/3.12，尝试用 conda 在项目内创建..."
  CONDA="$(command -v conda || echo /opt/anaconda3/bin/conda)"
  if [ ! -x "$CONDA" ]; then
    echo "❌ 需要 Python 3.11/3.12（open-webui 不支持 3.13）。"
    echo "   请安装后重跑，或手动创建: python3.12 -m venv .venvs/webui-venv"
    exit 1
  fi
  "$CONDA" create --solver classic -p "$ROOT/.venvs/webui" python=3.12 -y
  PY312="$ROOT/.venvs/webui/bin/python"
fi
echo "✔ Python: $PY312 ($("$PY312" --version 2>&1))"

# ---------- 2. 创建运行 venv ----------
if [ ! -x "$ROOT/.venvs/webui-venv/bin/python" ]; then
  echo "→ 创建 .venvs/webui-venv"
  "$PY312" -m venv "$ROOT/.venvs/webui-venv"
fi
VENV_PY="$ROOT/.venvs/webui-venv/bin/python"
echo "✔ venv: $VENV_PY ($("$VENV_PY" --version 2>&1))"

# ---------- 3. 安装后端依赖 ----------
need_deps() { ! "$VENV_PY" -c "import uvicorn, fastapi" >/dev/null 2>&1 && \
              ! PYTHONPATH="$ROOT/.venvs/webui-target" "$VENV_PY" -c "import uvicorn, fastapi" >/dev/null 2>&1; }
if need_deps; then
  echo "→ 安装 Open WebUI 后端依赖（较大，请耐心等待）"
  REQ="$ROOT/webui/backend/requirements.txt"
  if [ -f "$REQ" ]; then
    "$ROOT/.venvs/webui-venv/bin/pip" install -q -r "$REQ" || {
      echo "  直装失败，改用隔离目录安装（--target）"
      mkdir -p "$ROOT/.venvs/webui-target"
      "$ROOT/.venvs/webui-venv/bin/pip" install -q --target "$ROOT/.venvs/webui-target" -r "$REQ"
    }
  else
    "$ROOT/.venvs/webui-venv/bin/pip" install -q open-webui || {
      mkdir -p "$ROOT/.venvs/webui-target"
      "$ROOT/.venvs/webui-venv/bin/pip" install -q --target "$ROOT/.venvs/webui-target" open-webui
    }
  fi
fi
echo "✔ 后端依赖就绪"

# ---------- 4. 构建前端（简体中文） ----------
if [ ! -f "$ROOT/webui/build/index.html" ]; then
  echo "→ 构建前端（首次约 5-10 分钟）"
  if ! command -v npm >/dev/null 2>&1; then
    echo "❌ 缺少 npm，请先安装 Node.js 18+"; exit 1
  fi
  cd "$ROOT/webui"
  npm install --no-audit --no-fund
  # 跳过 pyodide 预下载（仅影响"代码执行"功能，聊天不受影响；需要时执行 npm run pyodide:fetch）
  npx vite build
  cd "$ROOT"
fi
[ -f "$ROOT/webui/build/index.html" ] && echo "✔ 前端已构建: webui/build" || { echo "❌ 前端构建失败"; exit 1; }

# ---------- 5. 运行目录 ----------
mkdir -p "$ROOT/data/webui" "$ROOT/runtime/logs"
echo "✔ 数据目录: data/webui   日志目录: runtime/logs"

echo ""
echo "🎉 环境已就绪，启动命令："
echo "   ./scripts/start_webui.sh            # 前台"
echo "   ./scripts/start_webui.sh --daemon   # 后台"
