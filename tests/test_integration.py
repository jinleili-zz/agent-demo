import json
import os
import tempfile
from unittest.mock import patch, Mock

from agent import Agent
from config import Config


def test_full_workflow():
    """测试完整工作流程"""
    # 在工作目录内创建临时目录，确保路径验证通过
    workspace = os.getcwd()
    with tempfile.TemporaryDirectory(dir=workspace) as tmpdir:
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
