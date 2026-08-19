#!/bin/zsh
set -e

PROJECT_DIR="/Users/xuting/Projects/AI Customer Service"
cd "$PROJECT_DIR"

cleanup() {
  [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "正在启动 SmartCare 后端…"
cd "$PROJECT_DIR/backend"
../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "正在启动 Vue3 前端…"
cd "$PROJECT_DIR/frontend"
pnpm exec vite --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

sleep 2
open "http://127.0.0.1:5173/"

echo ""
echo "项目已启动：http://127.0.0.1:5173/"
echo "请保持此窗口打开；按 Control+C 停止项目。"
wait
