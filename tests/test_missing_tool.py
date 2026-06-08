"""测试 LLM 调用不存在的工具时，Agent 的容错处理。

覆盖场景：
1. LLM 调用一个完全不存在的工具（如 send_email）
2. LLM 同时调用多个工具，其中部分不存在
3. 错误信息正确回传给 LLM，LLM 可据此回复用户
4. MCP 工具不存在时的处理
"""

import json
import os
import tempfile
from unittest.mock import patch, Mock

import pytest

from agent import Agent
from config import Config
from tools import execute_tool


# ──────────────────────────────────────────────
# 1. 工具层：调用不存在的工具抛出 ValueError
# ──────────────────────────────────────────────

def test_execute_tool_nonexistent_raises():
    """execute_tool 对不存在的工具应抛出 ValueError"""
    with pytest.raises(ValueError, match="工具不存在: search_web"):
        execute_tool("search_web", {"query": "test"})


# ──────────────────────────────────────────────
# 2. Agent 层：LLM 调用不存在的工具，Agent 不会崩溃
# ──────────────────────────────────────────────

@patch('agent.requests.post')
def test_chat_with_nonexistent_tool(mock_post):
    """LLM 请求调用一个不存在的工具时，错误被优雅地返回给 LLM"""
    # 第一次 API 响应：LLM 试图调用 search_web（不存在）
    first_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_missing_1",
                    "type": "function",
                    "function": {
                        "name": "search_web",
                        "arguments": '{"query": "Python tutorial"}'
                    }
                }]
            }
        }]
    }

    # 第二次 API 响应：LLM 根据错误信息回复用户
    second_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "抱歉，我目前没有搜索功能。"
            }
        }]
    }

    mock_post.return_value.json.side_effect = [first_response, second_response]
    mock_post.return_value.raise_for_status = Mock()

    config = Config(api_key="test-key")
    agent = Agent(config)

    result = agent.chat("帮我搜索 Python 教程")
    assert result == "抱歉，我目前没有搜索功能。"

    # 验证 API 被调用了两次（第一次带工具调用，第二次获取最终回复）
    assert mock_post.call_count == 2

    # 第二次调用的 messages 中应包含工具错误信息
    second_call_args = mock_post.call_args_list[1]
    messages_sent = second_call_args[1]["json"]["messages"]
    tool_message = [m for m in messages_sent if m["role"] == "tool"]
    assert len(tool_message) == 1
    assert "错误" in tool_message[0]["content"]
    assert "search_web" in tool_message[0]["content"]


# ──────────────────────────────────────────────
# 3. Agent 层：LLM 同时调用多个工具，部分不存在
# ──────────────────────────────────────────────

@patch('agent.requests.post')
def test_chat_with_mixed_tool_calls(mock_post):
    """LLM 同时调用多个工具，部分存在、部分不存在，各自独立处理"""
    workspace = os.getcwd()
    with tempfile.TemporaryDirectory(dir=workspace) as tmpdir:
        # 创建一个真实文件，让 read_file 工具能成功
        test_file = os.path.join(tmpdir, "note.txt")
        with open(test_file, 'w') as f:
            f.write("Good morning")

        # 第一次 API 响应：同时调用 read_file（存在）和 translate_text（不存在）
        first_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_ok_1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": json.dumps({"path": test_file})
                            }
                        },
                        {
                            "id": "call_fail_1",
                            "type": "function",
                            "function": {
                                "name": "translate_text",
                                "arguments": '{"text": "Hello", "target_lang": "ja"}'
                            }
                        }
                    ]
                }
            }]
        }

        second_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "文件内容是 Good morning，但翻译功能暂不可用。"
                }
            }]
        }

        mock_post.return_value.json.side_effect = [first_response, second_response]
        mock_post.return_value.raise_for_status = Mock()

        config = Config(api_key="test-key", log_dir=os.path.join(tmpdir, "logs"))
        agent = Agent(config)

        result = agent.chat(f"读取 {test_file} 并翻译成日语")
        assert "Good morning" in result
        assert "翻译功能暂不可用" in result

        # 验证两条工具结果都被传回给 LLM
        second_call_args = mock_post.call_args_list[1]
        messages_sent = second_call_args[1]["json"]["messages"]
        tool_messages = [m for m in messages_sent if m["role"] == "tool"]
        assert len(tool_messages) == 2

        # read_file 成功，translate_text 失败
        success_msgs = [m for m in tool_messages if "Good morning" in m["content"]]
        error_msgs = [m for m in tool_messages if "错误" in m["content"]]
        assert len(success_msgs) == 1
        assert len(error_msgs) == 1
        assert "translate_text" in error_msgs[0]["content"]


# ──────────────────────────────────────────────
# 4. Agent 层：LLM 调用不存在的 MCP 工具
# ──────────────────────────────────────────────

@patch('agent.requests.post')
def test_chat_with_nonexistent_mcp_tool(mock_post):
    """LLM 调用不存在的 MCP 工具时，Agent 正确处理错误"""
    first_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_mcp_1",
                    "type": "function",
                    "function": {
                        "name": "weather__get_forecast",
                        "arguments": '{"location": "Beijing"}'
                    }
                }]
            }
        }]
    }

    second_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "抱歉，天气服务当前不可用。"
            }
        }]
    }

    mock_post.return_value.json.side_effect = [first_response, second_response]
    mock_post.return_value.raise_for_status = Mock()

    config = Config(api_key="test-key")
    agent = Agent(config)  # 没有 MCP 配置，mcp_manager 为 None

    # _execute_tool 中，工具名含 "__" 但 mcp_manager 为 None，
    # 会走本地工具路径，本地也不存在 → ValueError
    result = agent.chat("查询北京的天气预报")
    assert result == "抱歉，天气服务当前不可用。"

    second_call_args = mock_post.call_args_list[1]
    messages_sent = second_call_args[1]["json"]["messages"]
    tool_message = [m for m in messages_sent if m["role"] == "tool"]
    assert len(tool_message) == 1
    assert "错误" in tool_message[0]["content"]


# ──────────────────────────────────────────────
# 5. 集成层：验证错误日志被正确记录
# ──────────────────────────────────────────────

@patch('agent.requests.post')
def test_missing_tool_error_is_logged(mock_post):
    """调用不存在的工具时，错误应被记录到日志文件"""
    workspace = os.getcwd()
    with tempfile.TemporaryDirectory(dir=workspace) as tmpdir:
        log_dir = os.path.join(tmpdir, "logs")

        first_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_log_1",
                        "type": "function",
                        "function": {
                            "name": "search_web",
                            "arguments": '{"query": "Python tutorial"}'
                        }
                    }]
                }
            }]
        }

        second_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "搜索功能暂不可用。"
                }
            }]
        }

        mock_post.return_value.json.side_effect = [first_response, second_response]
        mock_post.return_value.raise_for_status = Mock()

        config = Config(api_key="test-key", log_dir=log_dir)
        agent = Agent(config)
        agent.chat("搜索 Python 教程")

        # 检查日志文件
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.jsonl')]
        assert len(log_files) == 1

        with open(os.path.join(log_dir, log_files[0]), 'r') as f:
            logs = [json.loads(line) for line in f]

        log_types = [log["type"] for log in logs]
        assert "tool_call" in log_types, "应记录工具调用日志"
        assert "error" in log_types, "应记录错误日志"

        # 找到 error 日志，验证内容
        error_logs = [log for log in logs if log["type"] == "error"]
        assert any("search_web" in str(log.get("data", "")) for log in error_logs), \
            "错误日志应包含不存在的工具名称"
