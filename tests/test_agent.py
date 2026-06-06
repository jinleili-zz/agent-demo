import pytest
from unittest.mock import Mock, patch
from agent import Agent
from config import Config


def test_agent_init():
    """测试 Agent 初始化"""
    config = Config(api_key="test-key")
    agent = Agent(config)
    assert agent.config == config


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
