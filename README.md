# Simple Agent

一个基于 DeepSeek 模型的轻量级 Agent，支持命令行交互、工具调用和结构化日志记录。

## 功能特性

- 命令行交互模式
- 工具调用（read_file, write_file, get_weather）
- 天气查询（内置 get_weather 工具 + 外部 MCP Server）
- MCP 客户端支持（通过 stdio 连接外部 MCP Server）
- 结构化 JSON Lines 日志
- 通过装饰器扩展工具

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `config.json`：

```json
{
  "api_key": "your-deepseek-api-key"
}
```

### 3. 运行

```bash
python main.py
```

## 配置文件说明

`config.json` 支持以下字段：

| 字段 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| api_key | 是 | - | DeepSeek API Key |
| base_url | 否 | https://api.deepseek.com/v1 | API 地址 |
| model | 否 | deepseek-chat | 模型名称 |
| temperature | 否 | 0.7 | 温度参数 |
| max_tokens | 否 | 4096 | 最大 token 数 |
| log_dir | 否 | logs | 日志目录 |
| mcp_servers | 否 | {} | MCP Server 配置 |

## 日志查看

日志文件位于 `logs/agent-YYYY-MM-DD.jsonl`，每行一条 JSON：

```json
{"timestamp":"2026-06-06T10:30:00","type":"request","data":{...}}
{"timestamp":"2026-06-06T10:30:01","type":"response","data":{...}}
```

## 扩展工具

在 `tools.py` 中使用装饰器注册新工具：

```python
@register_tool(description="你的工具描述")
def my_tool(param: str) -> str:
    return f"结果: {param}"
```

## 天气查询

### 内置天气工具

`get_weather` 工具直接调用 Open-Meteo 免费 API，无需 API Key，开箱即用：

```
You: 帮我查一下北京的天气
Agent: 北京, 中国
天气: 晴
温度: 15.0°C
湿度: 78%
风速: 1.0 km/h
```

支持中英文城市名（如 "北京"、"Tokyo"、"New York"）。

### MCP 天气服务

通过 MCP 客户端连接外部 `openmeteo-mcp-server`，获取更丰富的天气数据（7 天预报、空气质量、海洋天气等）。

**前置条件**：安装 `uv` 工具

```bash
pip install uv
```

**配置**：`config.json` 中已默认配置：

```json
{
  "mcp_servers": {
    "weather": {
      "command": "uvx",
      "args": ["--from", "openmeteo-mcp-server", "weather-server"]
    }
  }
}
```

Agent 启动时会自动连接 MCP Server 并加载其工具，工具名格式为 `weather__xxx`（如 `weather__get_forecast`）。如果环境中没有 `uv`，MCP 连接会失败但不影响本地工具的正常使用。

## 项目结构

```
├── main.py         # 入口
├── agent.py        # Agent 核心
├── tools.py        # 工具定义（含 get_weather）
├── mcp_client.py   # MCP 客户端管理
├── config.py       # 配置管理
├── logger.py       # 日志记录
└── config.json     # 配置文件
```

## 测试

```bash
python -m pytest tests/ -v
```
