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


def test_skill_injected_into_system_prompt():
    """触发词命中时，skill 正文应出现在发给 API 的 system prompt 中。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("agent.SkillManager") as MockManager:
            instance = MockManager.return_value
            instance.start.return_value = None
            instance.get_active_instructions.return_value = "记笔记专属规则 XYZ"

            with patch("agent.requests.post") as mock_post:
                mock_post.return_value.json.return_value = {
                    "choices": [{"message": {"role": "assistant", "content": "ok"}}]
                }
                mock_post.return_value.raise_for_status = Mock()

                config = Config(
                    api_key="test-key",
                    log_dir=os.path.join(tmpdir, "logs"),
                )
                agent = Agent(config)
                agent.chat("帮我记个笔记")

                # 第一次 POST 的 payload 中，messages[0] 应是 system，且包含 skill 正文
                first_payload = mock_post.call_args_list[0].kwargs["json"]
                assert first_payload["messages"][0]["role"] == "system"
                assert "记笔记专属规则 XYZ" in first_payload["messages"][0]["content"]
