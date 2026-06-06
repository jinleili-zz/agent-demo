# MCP 天气查询集成设计

## 背景

项目是一个基于 DeepSeek API 的简单 Agent demo，已有自定义工具注册系统（`@register_tool` 装饰器），目前支持 `read_file` 和 `write_file` 两个工具。`.mcp.json` 已配置了 `openmeteo-mcp-server`，但仅对 Claude Code 生效，Agent 本身无 MCP 能力。

## 目标

1. 在现有工具系统中添加天气查询工具，直接调用 Open-Meteo 免费 API
2. 添加 MCP 客户端能力，让 Agent 能通过 stdio 连接外部 MCP Server 并动态加载其工具

## 第一部分：天气查询工具

### 实现

在 `tools.py` 中添加 `get_weather` 工具函数：

- 使用 `@register_tool(description="查询指定城市的当前天气")` 注册
- 调用 Open-Meteo Geocoding API（`https://geocoding-api.open-meteo.com/v1/search`）将城市名转为经纬度
- 调用 Open-Meteo Forecast API（`https://api.open-meteo.com/v1/forecast`）获取天气数据
- 返回格式化的天气信息（温度、湿度、风速、天气描述等）
- 无需 API Key，仅需 `requests`（已有依赖）

### 函数签名

```python
@register_tool(description="查询指定城市的当前天气")
def get_weather(city: str) -> str:
```

## 第二部分：MCP 客户端

### 架构

新建 `mcp_client.py` 模块，使用官方 `mcp` Python SDK（`pip install mcp`）：

1. 从 `config.json` 读取 `mcp_servers` 配置段
2. 通过 stdio 连接 MCP Server（如 `uvx openmeteo-mcp-server`）
3. 调用 `list_tools()` 发现 MCP Server 提供的工具
4. 将每个 MCP 工具包装后注册到 `tools.py` 的工具注册表中
5. 工具执行时，通过 MCP 客户端转发调用并返回结果

### 配置格式

`config.json` 新增 `mcp_servers` 字段：

```json
{
  "api_key": "...",
  "mcp_servers": {
    "weather": {
      "command": "uvx",
      "args": ["--from", "openmeteo-mcp-server", "weather-server"]
    }
  }
}
```

### 文件变更

| 文件 | 变更 |
|------|------|
| `tools.py` | 添加 `get_weather` 工具函数 |
| `mcp_client.py` | 新建，MCP 客户端封装 |
| `config.py` | `Config` 类添加 `mcp_servers` 字段 |
| `config.json` | 添加 `mcp_servers` 配置段 |
| `agent.py` | 启动时初始化 MCP 客户端，加载 MCP 工具 |
| `requirements.txt` | 添加 `mcp` 依赖 |

### MCP 客户端核心接口

```python
class MCPClientManager:
    """管理多个 MCP Server 连接"""

    async def connect_all(self, servers_config: dict) -> None
    async def load_tools(self) -> list[dict]  # 返回 OpenAI 格式的工具 schema
    async def call_tool(self, name: str, arguments: dict) -> Any
    async def cleanup(self) -> None
```

### Agent 集成

`agent.py` 中：
- 初始化时创建 `MCPClientManager`，连接所有配置的 MCP Server
- 将 MCP 工具的 schema 合并到 `self.tools_schema`
- 在 `_handle_tool_calls` 中，如果工具名匹配 MCP 工具，通过 MCP 客户端执行
- 退出时调用 `cleanup()` 关闭连接

### 依赖

- `mcp` - 官方 MCP Python SDK（包含 stdio transport）

## 限制与注意事项

- MCP 客户端使用 asyncio，而当前 Agent 是同步代码，需要用 `asyncio.run()` 或事件循环桥接
- MCP Server 进程需要 `uvx`（uv 工具）来运行，用户需确保环境中有 `uv` 安装
- 工具名冲突处理：MCP 工具以 `{server_name}__{tool_name}` 格式注册，避免与本地工具冲突
