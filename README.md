# Simple Agent

一个基于 DeepSeek 模型的轻量级 Agent，支持命令行交互、工具调用和结构化日志记录。

## 功能特性

- 命令行交互模式
- 工具调用（read_file, write_file）
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

## 项目结构

```
├── main.py        # 入口
├── agent.py       # Agent 核心
├── tools.py       # 工具定义
├── config.py      # 配置管理
├── logger.py      # 日志记录
└── config.json    # 配置文件
```

## 测试

```bash
python -m pytest tests/ -v
```
