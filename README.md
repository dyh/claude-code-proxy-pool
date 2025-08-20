# Claude Code Proxy Pool

## 多 API Key 轮询增强版 | Multi-Key Edition

Claude Code Proxy Pool 是对原项目 [claude-code-proxy](https://github.com/fuergaosi233/claude-code-proxy) 的改进版本，新增了支持多个 API Key 轮询的功能。通过在 `.env` 文件中配置多个 API Key，可以实现调用次数的叠加，突破单个 Key 的限制（例如免费 Key 的 500 次调用限制）。

## 主要特性 | Features

- **多 API Key 轮询** | Multi API Key Polling: 支持配置多个 API Key，系统会自动轮询使用，最大化调用次数。
- **多进程支持** | Multi-Process Support: 支持配置多个工作进程，提升服务并发能力。
- **兼容原项目** | Compatible with Original Project: 保留原项目的所有功能和配置方式，易于上手。

## 快速开始 | Quick Start

### 1. 配置多个 API Key | Configure Multiple API Keys

在 `.env` 文件中，通过逗号（,）分隔多个 API Key。目前支持 `OPENAI_API_KEY` 和 `ANTHROPIC_API_KEY` 的配置。

示例 | Example:

```bash
OPENAI_API_KEY="ms-111111111111111,ms-22222222222222,ms-333333333333333,ms-4444444444444444"
ANTHROPIC_API_KEY=""
```

> 注意：系统会自动轮询使用配置的多个 Key，无需额外设置。

> Note: The system will automatically poll the configured keys without additional setup.

### 2. 配置多进程服务 | Configure Multi-Process Service

在 `src/main.py` 中，可以通过 `workers` 参数指定启动的工作进程数量，以提升服务处理能力。

示例代码 | Example code:

```python
# 启动服务器 | Start server
uvicorn.run(
    "src.main:app",
    host=config.host,
    port=config.port,
    workers=4,  # 指定启动 4 个工作进程 | Specify 4 worker processes
    log_level=log_level,
    reload=False,
)
```

## 配置文件说明 (.env) | Configuration File (.env)

以下是 `.env` 文件的完整示例及参数说明：

Below is a complete example of the `.env` file and parameter descriptions:

```bash
# API Key 配置，支持多个 Key 用逗号分隔 | API Key configuration, supports multiple keys separated by commas
OPENAI_API_KEY="ms-111111111111111,ms-22222222222222,ms-333333333333333,ms-4444444444444444"
ANTHROPIC_API_KEY=""

# API 基础地址 | API base URL
OPENAI_BASE_URL="https://api-inference.modelscope.cn/v1/"

# 模型配置 | Model configuration
BIG_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct"
MIDDLE_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct"
SMALL_MODEL="Qwen/Qwen3-Coder-480B-A35B-Instruct"

# 可选：服务器设置 | Optional: Server settings
HOST="0.0.0.0"               # 服务器主机地址 | Server host address
PORT="8082"                  # 服务器端口 | Server port
LOG_LEVEL="INFO"             # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL | Log level
MAX_TOKENS_LIMIT="65535"     # 最大 Token 限制 | Maximum token limit
MIN_TOKENS_LIMIT="4096"      # 最小 Token 限制 | Minimum token limit
REQUEST_TIMEOUT="90"         # 请求超时时间（秒） | Request timeout (seconds)
MAX_RETRIES="2"              # 最大重试次数 | Maximum retry attempts
```

> 提示：根据你的需求调整上述参数，确保 API Key 和模型配置正确无误。

> Tip: Adjust the above parameters according to your needs, ensuring that the API Key and model configuration are correct.

## 贡献与支持 | Contribution & Support

本项目是基于 MIT 许可证的开源项目，欢迎社区贡献代码或提出改进建议。

This project is an open-source project licensed under the MIT License. Community contributions and improvement suggestions are welcome.

如果有问题或功能建议，请在 GitHub 仓库提交 Issue。

If you have any issues or feature suggestions, please submit an Issue in the GitHub repository.

## 致谢 | Acknowledgements

感谢原作者 [fuergaosi233](https://github.com/fuergaosi233) 提供的优秀项目 claude-code-proxy，本项目在其基础上进行了增强。

Thanks to the original author [fuergaosi233](https://github.com/fuergaosi233) for providing the excellent claude-code-proxy project, which this project enhances.

---

# Claude Code Proxy

A proxy server that enables **Claude Code** to work with OpenAI-compatible API providers. Convert Claude API requests to OpenAI API calls, allowing you to use various LLM providers through the Claude Code CLI.

## Features

- **Full Claude API Compatibility**: Complete `/v1/messages` endpoint support
- **Multiple Provider Support**: OpenAI, Azure OpenAI, local models (Ollama), and any OpenAI-compatible API
- **Smart Model Mapping**: Configure BIG and SMALL models via environment variables
- **Function Calling**: Complete tool use support with proper conversion
- **Streaming Responses**: Real-time SSE streaming support
- **Image Support**: Base64 encoded image input
- **Error Handling**: Comprehensive error handling and logging

## Quick Start

### 1. Install Dependencies

```bash
# Using UV (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your API configuration
```

### 3. Start Server

```bash
# Direct run
source .env
python start_proxy.py

# Or with UV
source .env
uv run claude-code-proxy

# Or with docker compose
docker compose up -d
```

### 4. Use with Claude Code

```bash
# If ANTHROPIC_API_KEY is not set in the proxy:
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="any-value" claude

# If ANTHROPIC_API_KEY is set in the proxy:
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="exact-matching-key" claude
```

## Configuration

### Environment Variables

**Required:**

- `OPENAI_API_KEY` - Your API key for the target provider

**Security:**

- `ANTHROPIC_API_KEY` - Expected Anthropic API key for client validation
  - If set, clients must provide this exact API key to access the proxy
  - If not set, any API key will be accepted

**Model Configuration:**

- `BIG_MODEL` - Model for Claude opus requests (default: `gpt-4o`)
- `MIDDLE_MODEL` - Model for Claude opus requests (default: `gpt-4o`)
- `SMALL_MODEL` - Model for Claude haiku requests (default: `gpt-4o-mini`)

**API Configuration:**

- `OPENAI_BASE_URL` - API base URL (default: `https://api.openai.com/v1`)

**Server Settings:**

- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8082`)
- `LOG_LEVEL` - Logging level (default: `WARNING`)

**Performance:**

- `MAX_TOKENS_LIMIT` - Token limit (default: `4096`)
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: `90`)

### Model Mapping

The proxy maps Claude model requests to your configured models:

| Claude Request                 | Mapped To     | Environment Variable   |
| ------------------------------ | ------------- | ---------------------- |
| Models with "haiku"            | `SMALL_MODEL` | Default: `gpt-4o-mini` |
| Models with "sonnet"           | `MIDDLE_MODEL`| Default: `BIG_MODEL`   |
| Models with "opus"             | `BIG_MODEL`   | Default: `gpt-4o`      |

### Provider Examples

#### OpenAI

```bash
OPENAI_API_KEY="sk-your-openai-key"
OPENAI_BASE_URL="https://api.openai.com/v1"
BIG_MODEL="gpt-4o"
MIDDLE_MODEL="gpt-4o"
SMALL_MODEL="gpt-4o-mini"
```

#### Azure OpenAI

```bash
OPENAI_API_KEY="your-azure-key"
OPENAI_BASE_URL="https://your-resource.openai.azure.com/openai/deployments/your-deployment"
BIG_MODEL="gpt-4"
MIDDLE_MODEL="gpt-4"
SMALL_MODEL="gpt-35-turbo"
```

#### Local Models (Ollama)

```bash
OPENAI_API_KEY="dummy-key"  # Required but can be dummy
OPENAI_BASE_URL="http://localhost:11434/v1"
BIG_MODEL="llama3.1:70b"
MIDDLE_MODEL="llama3.1:70b"
SMALL_MODEL="llama3.1:8b"
```

#### Other Providers

Any OpenAI-compatible API can be used by setting the appropriate `OPENAI_BASE_URL`.

## Usage Examples

### Basic Chat

```python
import httpx

response = httpx.post(
    "http://localhost:8082/v1/messages",
    json={
        "model": "claude-3-5-sonnet-20241022",  # Maps to MIDDLE_MODEL
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello!"}
        ]
    }
)
```

## Integration with Claude Code

This proxy is designed to work seamlessly with Claude Code CLI:

```bash
# Start the proxy
python start_proxy.py

# Use Claude Code with the proxy
ANTHROPIC_BASE_URL=http://localhost:8082 claude

# Or set permanently
export ANTHROPIC_BASE_URL=http://localhost:8082
claude
```

## Testing

Test the proxy functionality:

```bash
# Run comprehensive tests
python src/test_claude_to_openai.py
```

## Development

### Using UV

```bash
# Install dependencies
uv sync

# Run server
uv run claude-code-proxy

# Format code
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/
```

### Project Structure

```
claude-code-proxy/
├── src/
│   ├── main.py  # Main server
│   ├── test_claude_to_openai.py    # Tests
│   └── [other modules...]
├── start_proxy.py                  # Startup script
├── .env.example                    # Config template
└── README.md                       # This file
```

## Performance

- **Async/await** for high concurrency
- **Connection pooling** for efficiency
- **Streaming support** for real-time responses
- **Configurable timeouts** and retries
- **Smart error handling** with detailed logging

## License

MIT License