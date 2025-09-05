#!/usr/bin/env python3
"""
Configuration file for Claude Code Proxy Pool
This file replaces the .env file with a Python-based configuration approach
"""

# ModelScope API Keys (JSON array format)
OPENAI_API_KEY = [
    "ms-11111",
    "ms-22222"
]

# Client API Key for authentication (optional)
ANTHROPIC_API_KEY = ""

# ModelScope API endpoint
OPENAI_BASE_URL = "https://api-inference.modelscope.cn/v1/"

# Model configuration (JSON array format)
BIG_MODEL = [
    "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "moonshotai/Kimi-K2-Instruct-0905"
]

# Optional: Server settings
HOST = "0.0.0.0"
PORT = 8082
LOG_LEVEL = "INFO"
# DEBUG, INFO, WARNING, ERROR, CRITICAL

# API Configuration
MAX_TOKENS_LIMIT = 65535
MIN_TOKENS_LIMIT = 4096
REQUEST_TIMEOUT = 90
MAX_RETRIES = 2

# ModelScope API Key Validation
# Enable automatic validation of API keys on startup
ENABLE_API_VALIDATION = False

# Keep invalid API keys for debugging - set to true to see all keys in validation results
# When false, only valid keys are retained for actual API use
KEEP_INVALID_KEYS = True