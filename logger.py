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
