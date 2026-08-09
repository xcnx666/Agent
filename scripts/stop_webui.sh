#!/usr/bin/env bash
# 停止后台运行的 Koda 后端 + Open WebUI
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

stop_pidfile() {
  local f="$1" name="$2"
  if [ -f "$f" ]; then
    local pid; pid="$(cat "$f")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "✔ 已停止 $name (pid $pid)"
    else
      echo "· $name 未在运行"
    fi
    rm -f "$f"
  else
    echo "· 未找到 $name 的 pid 文件"
  fi
}

stop_pidfile "$ROOT/runtime/open-webui.pid" "Open WebUI"
stop_pidfile "$ROOT/runtime/koda-backend.pid" "Koda 后端"

# 兜底清理
pkill -f "uvicorn open_webui.main:app" 2>/dev/null || true
pkill -f "$ROOT/server.py" 2>/dev/null || true
sleep 1
echo "完成。"
