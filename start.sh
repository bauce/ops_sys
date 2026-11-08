#!/usr/bin/env bash
# 启动信息化运维管理系统（后端 + 已构建的前端）
set -e
cd "$(dirname "$0")"

PORT="${PORT:-8008}"

if [ ! -d .venv ]; then
  echo "首次运行：创建 Python 虚拟环境..."
  python3 -m venv .venv
  ./.venv/bin/pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple \
    -r backend/requirements.txt
fi

if [ ! -f frontend/dist/index.html ]; then
  echo "首次运行：构建前端..."
  (cd frontend && npm install --registry=https://registry.npmmirror.com --no-audit --no-fund \
    && npm run build)
fi

LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
echo "=============================================="
echo "  信息化运维管理系统"
echo "  本机访问：http://127.0.0.1:${PORT}"
if [ -n "$LAN_IP" ]; then
  echo "  局域网访问：http://${LAN_IP}:${PORT}"
  echo "  （手机需与本机在同一局域网，扫码报障请使用此地址）"
fi
echo "  运维后台：http://127.0.0.1:${PORT}/login"
echo "  按 Ctrl+C 停止服务"
echo "=============================================="

cd backend
exec ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
