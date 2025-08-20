#!/bin/bash

# 设置工作目录
WORK_DIR="/mnt/data/workspace/claude-code-proxy"

# 执行 Python脚本
PYTHONPATH="$WORK_DIR" "$WORK_DIR/.venv/bin/python" "$WORK_DIR/start_proxy.py"
