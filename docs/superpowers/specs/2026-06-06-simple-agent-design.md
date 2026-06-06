# Simple Agent 设计文档

## 1. 项目概述

一个基于 DeepSeek 模型的轻量级 Agent，支持命令行交互、工具调用和结构化日志记录。用于帮助开发者理解 Agent 与大模型的交互过程。

## 2. 设计目标

- **教育性**：清晰的日志让开发者能看到完整的请求/响应/工具调用链路
- **轻量**：最小依赖，仅使用 Python 标准库 + `requests`（或 `httpx`）调用 API
- **可扩展**：通过装饰器注册新工具，无需修改核心逻辑

## 3. 架构设计

### 3.1 模块划分

```
agent-demo/
├── main.py           # 入口：启动交互循环
├── agent.py          # 核心：编排对话和工具调用
├── tools.py          # 工具：定义和注册工具函数
├── config.py         # 配置：读取和管理配置
├── logger.py         # 日志：结构化记录交互过程
├── config.json       # 配置文件
└── logs/             # 日志目录
    └── agent-YYYY-MM-DD.jsonl
```

### 3.2 模块职责

| 模块 | 职责 | 不做什么 |
|------|------|----------|
| `config.py` | 读取 `config.json`，提供配置对象 | 不参与业务逻辑 |
| `tools.py` | 定义工具函数，通过装饰器自动注册 | 不知道谁调用它 |
| `agent.py` | 构造 API 请求，调度工具，处理响应 | 不直接操作文件 |
| `logger.py` | 记录请求、响应、工具调用等事件 | 不关心记录内容的意义 |
| `main.py` | 启动循环，接收输入，输出结果 | 不直接调用 API |

## 4. 数据流

### 4.1 单次对话完整流程

```
用户输入
    ↓
main.py 接收输入
    ↓
agent.chat(user_input)
    ↓
构造 API 请求（messages + tools schema）
    ↓
发送请求到 DeepSeek API
    ↓
接收响应
    ├── 如果是文本 → 直接输出给用户
    └── 如果是 tool_calls → 解析并调用对应工具
            ↓
        工具执行（tools.execute）
            ↓
        构造第二次请求（追加 tool_calls + tool_result）
            ↓
        发送请求到 DeepSeek API
            ↓
        接收最终文本响应
            ↓
        输出给用户
```

### 4.2 消息格式

每次用户输入都是独立的单次对话，`messages` 列表只包含当前轮次：

1. `user` 消息（用户输入）
2. `assistant` 消息（模型的 tool_calls，如果有）
3. `tool` 消息（工具执行结果，如果有）
4. `assistant` 消息（模型的最终回复）

## 5. 工具设计

### 5.1 内置工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `read_file` | 读取文件内容 | `path`: 文件路径 |
| `write_file` | 写入文件内容 | `path`: 文件路径, `content`: 文件内容 |

### 5.2 工具注册机制

使用 Python 装饰器注册工具：

```python
@register_tool(description="读取文件内容")
def read_file(path: str) -> str:
    ...
```

`tools.py` 自动收集所有带装饰器的函数，生成 OpenAI 格式的 `tools` schema。

### 5.3 安全限制

- 文件路径限制在工作目录内，禁止越界访问（如 `/etc/passwd`）
- 路径使用 `os.path.abspath` + `os.path.commonpath` 校验

## 6. 配置设计

### 6.1 config.json 格式

```json
{
  "api_key": "sk-...",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "max_tokens": 4096,
  "log_dir": "logs"
}
```

### 6.2 配置加载

- 启动时读取 `config.json`
- `api_key` 为必填项，缺失则报错退出
- 默认值：
  - `base_url`: `https://api.deepseek.com/v1`
  - `model`: `deepseek-chat`
  - `temperature`: `0.7`
  - `max_tokens`: `4096`
  - `log_dir`: `logs`

## 7. 日志设计

### 7.1 日志格式

JSON Lines 格式，每行一条 JSON 对象：

```json
{
  "timestamp": "2026-06-06T10:30:00",
  "type": "request|response|tool_call|tool_result|error",
  "data": { ... }
}
```

### 7.2 日志事件类型

| 类型 | 记录内容 |
|------|----------|
| `request` | 完整的 API 请求体（messages, tools, model 等） |
| `response` | 完整的 API 响应体 |
| `tool_call` | 工具名称和参数 |
| `tool_result` | 工具执行结果 |
| `error` | 错误信息和堆栈 |

### 7.3 日志文件

- 文件名：`logs/agent-YYYY-MM-DD.jsonl`
- 按天滚动，自动创建目录
- 日志写入失败不中断程序，仅打印终端警告

## 8. 错误处理

### 8.1 网络/API 层

- 请求失败（超时、HTTP 错误）：重试 2 次，仍失败则报错
- API key 无效：启动时直接报错退出

### 8.2 工具执行层

- 文件不存在：返回错误信息给模型
- 路径越界：拒绝执行，返回权限错误
- 写入失败：返回具体错误信息

### 8.3 交互层

- 用户输入为空：直接忽略，等待下一次输入
- `Ctrl+C`：优雅退出，关闭日志文件

## 9. 依赖

```
Python >= 3.8
requests >= 2.25.0  # 或 httpx
```

仅一个外部依赖，便于理解和部署。

## 10. 成功标准

- [ ] 能通过配置文件连接 DeepSeek API 并进行对话
- [ ] 模型能正确调用 `read_file` 和 `write_file` 工具
- [ ] 每次交互的完整链路都被记录到 JSON Lines 日志
- [ ] 代码结构清晰，每个模块职责单一
- [ ] 添加新工具只需在 `tools.py` 中定义函数并加装饰器
