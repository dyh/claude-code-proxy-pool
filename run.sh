#!/bin/bash

cd /srv/workspace/claude-code-proxy-pool/

/srv/workspace/claude-code-proxy-pool/.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8082 --workers 4
