import json
import re
import time
from typing import List, Dict, Any, Optional

import requests

from config import Config
from logger import AgentLogger
from tools import get_tools_schema, execute_tool, _geocode
from mcp_client import MCPClientManager


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
        self.mcp_manager: Optional[MCPClientManager] = None

        # 初始化 MCP 客户端
        if config.mcp_servers:
            self._init_mcp(config.mcp_servers)

    def _init_mcp(self, servers_config: Dict[str, Any]) -> None:
        """初始化 MCP 客户端连接"""
        try:
            self.mcp_manager = MCPClientManager()
            self.mcp_manager.start(servers_config)

            # 合并 MCP 工具到本地工具 schema
            mcp_schemas = self.mcp_manager.get_tools_schema()
            self.tools_schema.extend(mcp_schemas)

            if mcp_schemas:
                print(f"[Agent] MCP 工具已加载: {[s['function']['name'] for s in mcp_schemas]}")
        except Exception as e:
            print(f"[Agent] MCP 初始化失败: {e}")
            self.mcp_manager = None

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
            except (requests.RequestException, ValueError) as e:
                if attempt == max_retries - 1:
                    self.logger.log_error(e)
                    raise
                time.sleep(2 ** attempt)  # 指数退避

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具调用（本地工具或 MCP 工具）

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        # 检查是否是 MCP 工具（以 server__ 前缀标识）
        if "__" in tool_name and self.mcp_manager:
            # MCP 不支持中文城市名，自动转换
            self._translate_location(arguments)
            return self.mcp_manager.call_tool(tool_name, arguments)

        # 本地工具
        return execute_tool(tool_name, arguments)

    @staticmethod
    def _translate_location(arguments: Dict[str, Any]) -> None:
        """将 MCP 工具参数中的中文城市名转换为英文"""
        location = arguments.get("location")
        if not location or not isinstance(location, str):
            return

        # 检测是否包含中文字符
        if not re.search(r"[\u4e00-\u9fff]", location):
            return

        try:
            results = _geocode(location, language="en")
            if results:
                arguments["location"] = results[0].get("name", location)
                print(f"[Agent] 城市名转换: {location} → {arguments['location']}")
        except Exception as e:
            print(f"[Agent] 城市名转换失败: {e}")

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
                result = self._execute_tool(tool_name, arguments)
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
            {"role": "system", "content": "你是一个有帮助的助手，可以使用工具帮助用户完成任务。"},
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

    def cleanup(self) -> None:
        """清理资源"""
        if self.mcp_manager:
            self.mcp_manager.cleanup()
