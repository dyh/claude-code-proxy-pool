# Claude Code Proxy Pool

多 API Key 轮询增强版 | Multi-Key Edition

基于 [claude-code-proxy](https://github.com/fuergaosi233/claude-code-proxy) 的改进版本，支持多个 API Key 轮询，突破单个 Key 的调用限制。

## 主要特性 | Features

- **多 API Key 轮询** | Multi API Key Polling: 使用 Python 列表格式配置多个 API Key，系统自动轮询使用
- **Python 配置格式** | Python Configuration: 使用 `config.py` 配置文件替代传统 `.env` 文件
- **智能模型映射** | Smart Model Mapping: 支持 ModelScope、Kimi、Qwen 等多种国产大模型
- **API Key 验证** | API Key Validation: 自动验证 API Key 有效性

## 快速开始 | Quick Start

### 1. 配置 config.py

```python
# ModelScope API Keys (Python 列表格式)
OPENAI_API_KEY = [
    "ms-your-api-key-1",
    "ms-your-api-key-2"
]

# 客户端 API Key 验证（可选）
ANTHROPIC_API_KEY = ""

# ModelScope API 端点
OPENAI_BASE_URL = "https://api-inference.modelscope.cn/v1/"

# 主模型列表（支持轮询）
BIG_MODEL = [
    "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "moonshotai/Kimi-K2-Instruct-0905"
]

# 服务器设置
HOST = "0.0.0.0"
PORT = 8082
LOG_LEVEL = "INFO"
```

### 2. 启动服务

```bash
# 使用启动脚本
python start_proxy.py

# 或直接运行
python src/main.py
```

### 3. 与 Claude Code 集成

```bash
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY="any-value" claude
```

## 配置说明

核心配置项：
- `OPENAI_API_KEY`: API Key 列表（Python 列表格式）
- `BIG_MODEL`: 模型列表（支持轮询选择）
- `ANTHROPIC_API_KEY`: 客户端验证密钥（可选）
- `ENABLE_API_VALIDATION`: 自动验证 API Key（默认：False）

完整配置示例和更多选项请参考项目中的配置模板。

## 致谢 | Acknowledgements

感谢原作者 [fuergaosi233](https://github.com/fuergaosi233) 提供的优秀项目 claude-code-proxy，本项目在其基础上进行了增强。

Thanks to the original author [fuergaosi233](https://github.com/fuergaosi233) for providing the excellent claude-code-proxy project, which this project enhances.

## 许可证 | License

MIT License