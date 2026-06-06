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
