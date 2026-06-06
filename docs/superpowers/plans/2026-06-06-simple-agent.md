# Simple Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个基于 DeepSeek 模型的轻量级 Agent，支持命令行交互、工具调用和结构化日志记录

**Architecture:** 模块化设计，每个文件职责单一。`config.py` 管理配置，`tools.py` 注册工具，`logger.py` 记录交互，`agent.py` 编排对话，`main.py` 启动交互循环

**Tech Stack:** Python 3.8+, requests, pytest

---

## 文件结构

```
agent-demo/
├── main.py              # 入口：启动交互循环
├── agent.py             # 核心：编排对话和工具调用
├── tools.py             # 工具：定义和注册工具函数
├── config.py            # 配置：读取和管理配置
├── logger.py            # 日志：结构化记录交互过程
├── config.json          # 配置文件
├── requirements.txt     # 依赖声明
├── tests/
│   ├── test_config.py   # 配置模块测试
│   ├── test_tools.py    # 工具模块测试
│   ├── test_logger.py   # 日志模块测试
│   └── test_agent.py    # Agent模块测试
└── logs/                # 日志目录（运行时创建）
```

---

## Task 1: 项目初始化和依赖配置

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: 创建 requirements.txt**

```text
requests>=2.25.0
pytest>=7.0.0
```

- [ ] **Step 2: 安装依赖**

```bash
pip install -r requirements.txt
```

Expected: 安装成功，无报错

- [ ] **Step 3: 创建项目目录结构**

```bash
mkdir -p tests logs
```

---

## Task 2: 配置模块 (config.py)

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 编写测试 - 配置加载成功**

```python
# tests/test_config.py
import json
import pytest
import tempfile
import os
from config import load_config, Config

def test_load_config_success():
    """测试成功加载配置"""
    config_data = {
        "api_key": "test-key-123",
        "base_url": "https://test.com",
        "model": "test-model",
        "temperature": 0.5,
        "max_tokens": 2048,
        "log_dir": "test_logs"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config_path = f.name
    
    try:
        config = load_config(config_path)
        assert config.api_key == "test-key-123"
        assert config.base_url == "https://test.com"
        assert config.model == "test-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.log_dir == "test_logs"
    finally:
        os.unlink(config_path)
```

- [ ] **Step 2: 运行测试 - 确认失败**

```bash
python -m pytest tests/test_config.py::test_load_config_success -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'config'"

- [ ] **Step 3: 实现 config.py**

```python
# config.py
import json
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """配置数据类"""
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    log_dir: str = "logs"

def load_config(config_path: str = "config.json") -> Config:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config 对象
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: api_key 为空
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    api_key = data.get('api_key', '').strip()
    if not api_key:
        raise ValueError("api_key 是必填项")
    
    return Config(
        api_key=api_key,
        base_url=data.get('base_url', Config.base_url),
        model=data.get('model', Config.model),
        temperature=data.get('temperature', Config.temperature),
        max_tokens=data.get('max_tokens', Config.max_tokens),
        log_dir=data.get('log_dir', Config.log_dir)
    )
```

- [ ] **Step 4: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_config.py::test_load_config_success -v
```

Expected: PASS

- [ ] **Step 5: 编写测试 - 配置缺失 api_key**

```python
# tests/test_config.py (追加)

def test_load_config_missing_api_key():
    """测试缺失 api_key 时抛出异常"""
    config_data = {"model": "test-model"}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config_path = f.name
    
    try:
        with pytest.raises(ValueError, match="api_key 是必填项"):
            load_config(config_path)
    finally:
        os.unlink(config_path)
```

- [ ] **Step 6: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 2 tests PASS

- [ ] **Step 7: 提交**

```bash
git add config.py tests/test_config.py requirements.txt
git commit -m "feat: 添加配置模块，支持加载 config.json"
```

---

## Task 3: 工具模块 (tools.py)

**Files:**
- Create: `tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: 编写测试 - 工具注册和发现**

```python
# tests/test_tools.py
import pytest
import tempfile
import os
from tools import register_tool, get_tools_schema, execute_tool

def test_register_tool_decorator():
    """测试工具注册装饰器"""
    @register_tool(description="测试工具")
    def test_tool(name: str) -> str:
        return f"Hello {name}"
    
    schema = get_tools_schema()
    assert len(schema) == 1
    assert schema[0]["function"]["name"] == "test_tool"
    assert schema[0]["function"]["description"] == "测试工具"
```

- [ ] **Step 2: 运行测试 - 确认失败**

```bash
python -m pytest tests/test_tools.py::test_register_tool_decorator -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'tools'"

- [ ] **Step 3: 实现 tools.py**

```python
# tools.py
import os
import json
from typing import Callable, Dict, List, Any
from functools import wraps

# 工具注册表
_registry: Dict[str, Callable] = {}
_schemas: List[Dict] = []

def register_tool(description: str = ""):
    """工具注册装饰器
    
    Args:
        description: 工具描述
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        tool_name = func.__name__
        _registry[tool_name] = func
        
        # 生成 OpenAI 格式的工具 schema
        import inspect
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            
            properties[param_name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        _schemas.append(schema)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_tools_schema() -> List[Dict]:
    """获取所有已注册工具的 schema"""
    return _schemas.copy()

def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """执行指定工具
    
    Args:
        name: 工具名称
        arguments: 工具参数
        
    Returns:
        工具执行结果
        
    Raises:
        ValueError: 工具不存在
    """
    if name not in _registry:
        raise ValueError(f"工具不存在: {name}")
    
    func = _registry[name]
    return func(**arguments)

def _validate_path(path: str) -> str:
    """验证文件路径，确保在工作目录内
    
    Args:
        path: 文件路径
        
    Returns:
        绝对路径
        
    Raises:
        ValueError: 路径越界
    """
    abs_path = os.path.abspath(path)
    cwd = os.path.abspath(os.getcwd())
    
    if not abs_path.startswith(cwd):
        raise ValueError(f"路径越界: {path} 不在工作目录内")
    
    return abs_path

@register_tool(description="读取文件内容")
def read_file(path: str) -> str:
    """读取文件内容
    
    Args:
        path: 文件路径
        
    Returns:
        文件内容
        
    Raises:
        ValueError: 路径越界
        FileNotFoundError: 文件不存在
    """
    abs_path = _validate_path(path)
    
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"文件不存在: {path}")
    
    with open(abs_path, 'r', encoding='utf-8') as f:
        return f.read()

@register_tool(description="写入文件内容")
def write_file(path: str, content: str) -> str:
    """写入文件内容
    
    Args:
        path: 文件路径
        content: 文件内容
        
    Returns:
        操作结果
        
    Raises:
        ValueError: 路径越界
    """
    abs_path = _validate_path(path)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(abs_path) or '.', exist_ok=True)
    
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return f"文件已写入: {path}"
```

- [ ] **Step 4: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_tools.py::test_register_tool_decorator -v
```

Expected: PASS

- [ ] **Step 5: 编写测试 - 工具执行**

```python
# tests/test_tools.py (追加)

def test_execute_tool_read_file():
    """测试读取文件工具"""
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Hello World")
        temp_path = f.name
    
    try:
        result = execute_tool("read_file", {"path": temp_path})
        assert result == "Hello World"
    finally:
        os.unlink(temp_path)

def test_execute_tool_write_file():
    """测试写入文件工具"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "test.txt")
        result = execute_tool("write_file", {"path": file_path, "content": "Test Content"})
        assert "文件已写入" in result
        
        # 验证写入内容
        with open(file_path, 'r') as f:
            assert f.read() == "Test Content"

def test_execute_tool_path_traversal():
    """测试路径越界检测"""
    with pytest.raises(ValueError, match="路径越界"):
        execute_tool("read_file", {"path": "/etc/passwd"})
```

- [ ] **Step 6: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_tools.py -v
```

Expected: 4 tests PASS

- [ ] **Step 7: 提交**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: 添加工具模块，支持 read_file/write_file 和装饰器注册"
```

---

## Task 4: 日志模块 (logger.py)

**Files:**
- Create: `logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: 编写测试 - 日志记录**

```python
# tests/test_logger.py
import json
import os
import tempfile
from logger import AgentLogger

def test_log_request():
    """测试记录请求日志"""
    with tempfile.TemporaryDirectory() as log_dir:
        logger = AgentLogger(log_dir)
        
        request_data = {"model": "test", "messages": [{"role": "user", "content": "hi"}]}
        logger.log_request(request_data)
        
        # 读取日志文件
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
        assert len(log_files) == 1
        
        with open(os.path.join(log_dir, log_files[0]), 'r') as f:
            log_entry = json.loads(f.readline())
        
        assert log_entry["type"] == "request"
        assert log_entry["data"] == request_data
        assert "timestamp" in log_entry
```

- [ ] **Step 2: 运行测试 - 确认失败**

```bash
python -m pytest tests/test_logger.py::test_log_request -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'logger'"

- [ ] **Step 3: 实现 logger.py**

```python
# logger.py
import json
import os
from datetime import datetime
from typing import Any, Dict

class AgentLogger:
    """Agent 交互日志记录器"""
    
    def __init__(self, log_dir: str = "logs"):
        """初始化日志记录器
        
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 按天创建日志文件
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.log_file = os.path.join(log_dir, f"agent-{date_str}.jsonl")
    
    def _write_log(self, log_type: str, data: Any) -> None:
        """写入日志
        
        Args:
            log_type: 日志类型
            data: 日志数据
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type,
            "data": data
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            # 日志写入失败不中断程序
            print(f"[警告] 日志写入失败: {e}")
    
    def log_request(self, request_data: Dict[str, Any]) -> None:
        """记录 API 请求
        
        Args:
            request_data: 请求数据
        """
        self._write_log("request", request_data)
    
    def log_response(self, response_data: Dict[str, Any]) -> None:
        """记录 API 响应
        
        Args:
            response_data: 响应数据
        """
        self._write_log("response", response_data)
    
    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """记录工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        """
        self._write_log("tool_call", {
            "name": tool_name,
            "arguments": arguments
        })
    
    def log_tool_result(self, tool_name: str, result: Any) -> None:
        """记录工具执行结果
        
        Args:
            tool_name: 工具名称
            result: 执行结果
        """
        self._write_log("tool_result", {
            "name": tool_name,
            "result": result
        })
    
    def log_error(self, error: Exception) -> None:
        """记录错误
        
        Args:
            error: 异常对象
        """
        import traceback
        self._write_log("error", {
            "message": str(error),
            "traceback": traceback.format_exc()
        })
```

- [ ] **Step 4: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_logger.py::test_log_request -v
```

Expected: PASS

- [ ] **Step 5: 编写测试 - 日志类型覆盖**

```python
# tests/test_logger.py (追加)

def test_log_all_types():
    """测试所有日志类型"""
    with tempfile.TemporaryDirectory() as log_dir:
        logger = AgentLogger(log_dir)
        
        logger.log_request({"test": "request"})
        logger.log_response({"test": "response"})
        logger.log_tool_call("test_tool", {"arg": "value"})
        logger.log_tool_result("test_tool", "result")
        logger.log_error(ValueError("test error"))
        
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
        assert len(log_files) == 1
        
        with open(os.path.join(log_dir, log_files[0]), 'r') as f:
            lines = f.readlines()
        
        assert len(lines) == 5
        
        types = [json.loads(line)["type"] for line in lines]
        assert types == ["request", "response", "tool_call", "tool_result", "error"]
```

- [ ] **Step 6: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_logger.py -v
```

Expected: 2 tests PASS

- [ ] **Step 7: 提交**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: 添加日志模块，支持结构化 JSON Lines 日志"
```

---

## Task 5: Agent 核心模块 (agent.py)

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: 编写测试 - Agent 初始化**

```python
# tests/test_agent.py
import pytest
from unittest.mock import Mock, patch
from agent import Agent
from config import Config

def test_agent_init():
    """测试 Agent 初始化"""
    config = Config(api_key="test-key")
    agent = Agent(config)
    assert agent.config == config
```

- [ ] **Step 2: 运行测试 - 确认失败**

```bash
python -m pytest tests/test_agent.py::test_agent_init -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'agent'"

- [ ] **Step 3: 实现 agent.py**

```python
# agent.py
import json
import time
from typing import List, Dict, Any, Optional

import requests

from config import Config
from logger import AgentLogger
from tools import get_tools_schema, execute_tool

class Agent:
    """Agent 核心类"""
    
    def __init__(self, config: Config):
        """初始化 Agent
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.logger = AgentLogger(config.log_dir)
        self.tools_schema = get_tools_schema()
    
    def _call_api(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """调用 DeepSeek API
        
        Args:
            messages: 消息列表
            tools: 工具 schema（可选）
            
        Returns:
            API 响应数据
            
        Raises:
            requests.RequestException: 请求失败
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # 记录请求
        self.logger.log_request(payload)
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                # 记录响应
                self.logger.log_response(data)
                
                return data
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    self.logger.log_error(e)
                    raise
                time.sleep(2 ** attempt)  # 指数退避
    
    def _handle_tool_calls(self, tool_calls: List[Dict], messages: List[Dict[str, Any]]) -> None:
        """处理工具调用
        
        Args:
            tool_calls: 工具调用列表
            messages: 消息列表（会被修改）
        """
        for tool_call in tool_calls:
            function = tool_call["function"]
            tool_name = function["name"]
            arguments = json.loads(function["arguments"])
            
            # 记录工具调用
            self.logger.log_tool_call(tool_name, arguments)
            
            try:
                result = execute_tool(tool_name, arguments)
                self.logger.log_tool_result(tool_name, result)
            except Exception as e:
                result = f"错误: {str(e)}"
                self.logger.log_error(e)
            
            # 添加工具调用结果到消息列表
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })
    
    def chat(self, user_input: str) -> str:
        """处理用户输入
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            模型回复文本
        """
        messages = [
            {"role": "system", "content": "你是一个 helpful 的助手，可以使用工具帮助用户完成任务。"},
            {"role": "user", "content": user_input}
        ]
        
        # 第一次请求，带上工具
        response = self._call_api(messages, self.tools_schema)
        
        # 获取 assistant 的消息
        assistant_message = response["choices"][0]["message"]
        
        # 检查是否有工具调用
        if "tool_calls" in assistant_message and assistant_message["tool_calls"]:
            # 添加 assistant 的消息到消息列表
            messages.append({
                "role": "assistant",
                "content": assistant_message.get("content", ""),
                "tool_calls": assistant_message["tool_calls"]
            })
            
            # 处理工具调用
            self._handle_tool_calls(assistant_message["tool_calls"], messages)
            
            # 第二次请求，不带工具，获取最终回复
            response = self._call_api(messages)
            assistant_message = response["choices"][0]["message"]
        
        return assistant_message.get("content", "")
```

- [ ] **Step 4: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_agent.py::test_agent_init -v
```

Expected: PASS

- [ ] **Step 5: 编写测试 - Agent chat 流程（Mock API）**

```python
# tests/test_agent.py (追加)

@patch('agent.requests.post')
def test_chat_simple_response(mock_post):
    """测试无工具调用的对话"""
    mock_post.return_value.json.return_value = {
        "choices": [{
            "message": {"role": "assistant", "content": "Hello!"}
        }]
    }
    mock_post.return_value.raise_for_status = Mock()
    
    config = Config(api_key="test-key")
    agent = Agent(config)
    
    result = agent.chat("Hi")
    assert result == "Hello!"

@patch('agent.requests.post')
def test_chat_with_tool_call(mock_post):
    """测试带工具调用的对话"""
    # 第一次响应：模型要求调用工具
    mock_post.return_value.json.side_effect = [
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "test.txt"}'
                        }
                    }]
                }
            }]
        },
        # 第二次响应：最终回复
        {
            "choices": [{
                "message": {"role": "assistant", "content": "File content is test"}
            }]
        }
    ]
    mock_post.return_value.raise_for_status = Mock()
    
    config = Config(api_key="test-key")
    agent = Agent(config)
    
    result = agent.chat("Read test.txt")
    assert result == "File content is test"
```

- [ ] **Step 6: 运行测试 - 确认通过**

```bash
python -m pytest tests/test_agent.py -v
```

Expected: 3 tests PASS

- [ ] **Step 7: 提交**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: 添加 Agent 核心模块，支持对话和工具调用"
```

---

## Task 6: 入口模块 (main.py)

**Files:**
- Create: `main.py`

- [ ] **Step 1: 实现 main.py**

```python
# main.py
import sys
from config import load_config
from agent import Agent

def main():
    """主函数"""
    try:
        config = load_config()
        agent = Agent(config)
        
        print("=" * 50)
        print("Simple Agent - 基于 DeepSeek")
        print("输入 'exit' 或 'quit' 退出")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ('exit', 'quit'):
                    print("再见！")
                    break
                
                print("\nAgent: ", end="", flush=True)
                response = agent.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                print(f"\n错误: {e}")
    
    except FileNotFoundError:
        print("错误: 配置文件 config.json 不存在")
        print("请创建 config.json，格式如下:")
        print('  {"api_key": "your-api-key"}')
        sys.exit(1)
    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试入口模块（手动测试）**

```bash
python main.py
```

Expected: 提示配置文件不存在，并显示配置示例

- [ ] **Step 3: 创建配置文件示例**

```bash
cat > config.json << 'EOF'
{
  "api_key": "your-deepseek-api-key",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "max_tokens": 4096
}
EOF
```

- [ ] **Step 4: 提交**

```bash
git add main.py config.json
git commit -m "feat: 添加入口模块和配置文件示例"
```

---

## Task 7: 集成测试和运行验证

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: 编写集成测试**

```python
# tests/test_integration.py
import json
import os
import tempfile
from unittest.mock import patch, Mock

from agent import Agent
from config import Config

def test_full_workflow():
    """测试完整工作流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        test_file = os.path.join(tmpdir, "hello.txt")
        with open(test_file, 'w') as f:
            f.write("Hello World")
        
        # Mock API 响应
        with patch('agent.requests.post') as mock_post:
            mock_post.return_value.json.side_effect = [
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": test_file})
                                }
                            }]
                        }
                    }]
                },
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "文件内容是: Hello World"
                        }
                    }]
                }
            ]
            mock_post.return_value.raise_for_status = Mock()
            
            # 创建 Agent
            config = Config(
                api_key="test-key",
                log_dir=os.path.join(tmpdir, "logs")
            )
            agent = Agent(config)
            
            # 执行对话
            result = agent.chat(f"读取文件 {test_file}")
            assert "Hello World" in result
            
            # 验证日志
            log_dir = os.path.join(tmpdir, "logs")
            log_files = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
            assert len(log_files) == 1
            
            with open(os.path.join(log_dir, log_files[0]), 'r') as f:
                logs = [json.loads(line) for line in f]
            
            # 验证日志包含所有事件类型
            log_types = [log["type"] for log in logs]
            assert "request" in log_types
            assert "response" in log_types
            assert "tool_call" in log_types
            assert "tool_result" in log_types
```

- [ ] **Step 2: 运行集成测试**

```bash
python -m pytest tests/test_integration.py -v
```

Expected: PASS

- [ ] **Step 3: 运行全部测试**

```bash
python -m pytest tests/ -v
```

Expected: 所有测试 PASS

- [ ] **Step 4: 提交**

```bash
git add tests/test_integration.py
git commit -m "test: 添加集成测试，验证完整工作流程"
```

---

## Task 8: 创建 README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 编写 README**

```markdown
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
```

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 添加 README 文档"
```

---

## 自检清单

- [x] **Spec coverage:** 所有设计文档中的功能都已实现
- [x] **Placeholder scan:** 无 TBD/TODO/占位符
- [x] **Type consistency:** 所有函数签名和类型一致
