#!/usr/bin/env bash
# 测试版启动：免密登录 + 自动写入模拟数据
set -e
cd "$(dirname "$0")"
OPS_TEST_MODE=1 OPS_SEED_TEST_DATA=1 exec ./start.sh
