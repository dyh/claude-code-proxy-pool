#!/bin/bash

cd /mnt/data/workspace/claude-code-proxy-pool/

/mnt/data/workspace/claude-code-proxy-pool/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8082 --workers 8
