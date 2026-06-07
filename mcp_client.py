"""MCP 客户端管理模块

使用官方 mcp Python SDK，通过 stdio 连接外部 MCP Server，
发现并加载其工具，注册到本地工具系统中。

使用后台线程运行事件循环，保持 MCP 连接在整个会话期间存活。
"""

import asyncio
import json
import threading
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClientManager:
    """管理多个 MCP Server 连接"""

    def __init__(self):
        self._tool_map: Dict[str, str] = {}  # prefixed_tool_name -> server_name
        self._cached_schemas: List[Dict] = []
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack: Optional[AsyncExitStack] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, servers_config: Dict[str, Dict]) -> None:
        """启动后台事件循环并连接所有 MCP Server"""
        if not servers_config:
            return

        # 在后台线程中运行事件循环
        self._loop = asyncio.new_event_loop()
        ready = threading.Event()

        def _run_loop():
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._run(servers_config, ready))
            # 保持事件循环运行，直到被关闭
            self._loop.run_forever()

        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
        ready.wait(timeout=30)  # 等待连接完成

    async def _run(self, servers_config: Dict[str, Dict], ready: threading.Event) -> None:
        """在事件循环中连接所有 MCP Server"""
        self._exit_stack = AsyncExitStack()

        try:
            await self._exit_stack.__aenter__()

            for server_name, config in servers_config.items():
                try:
                    await self._connect_server(server_name, config)
                except Exception as e:
                    print(f"[MCP] 连接 {server_name} 失败: {e}")

            # 缓存工具 schema
            await self._cache_tools()

        finally:
            ready.set()  # 无论成功失败，都通知主线程

    async def _connect_server(self, server_name: str, config: Dict) -> None:
        """连接单个 MCP Server"""
        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
        )

        # 通过 AsyncExitStack 管理上下文生命周期
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[server_name] = session

        # 发现并映射工具
        result = await session.list_tools()
        for tool in result.tools:
            prefixed_name = f"{server_name}__{tool.name}"
            self._tool_map[prefixed_name] = server_name

        print(f"[MCP] 已连接 {server_name}，发现 {len(result.tools)} 个工具:")
        for tool in result.tools:
            print(f"  - {server_name}__{tool.name}: {tool.description or '无描述'}")

    async def _cache_tools(self) -> None:
        """缓存所有 MCP Server 的工具 schema"""
        self._cached_schemas = []

        for server_name, session in self._sessions.items():
            try:
                result = await session.list_tools()
                for tool in result.tools:
                    prefixed_name = f"{server_name}__{tool.name}"
                    self._tool_map[prefixed_name] = server_name

                    schema = {
                        "type": "function",
                        "function": {
                            "name": prefixed_name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema,
                        },
                    }
                    self._cached_schemas.append(schema)
            except Exception as e:
                print(f"[MCP] 获取 {server_name} 工具列表失败: {e}")

    def get_tools_schema(self) -> List[Dict]:
        """获取所有 MCP 工具的 OpenAI 格式 schema"""
        return self._cached_schemas

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """同步调用 MCP 工具

        Args:
            name: 工具名（带前缀，如 "weather__get_forecast"）
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if not self._loop or not self._loop.is_running():
            raise RuntimeError("MCP 客户端未启动")

        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(name, arguments), self._loop
        )
        return future.result(timeout=30)

    async def _call_tool_async(self, name: str, arguments: Dict[str, Any]) -> Any:
        """异步调用 MCP 工具"""
        server_name = self._tool_map.get(name)
        if not server_name:
            raise ValueError(f"未知的 MCP 工具: {name}")

        session = self._sessions.get(server_name)
        if not session:
            raise ValueError(f"MCP Server 未连接: {server_name}")

        original_name = name.split("__", 1)[1]
        result = await session.call_tool(original_name, arguments)

        if result.content:
            return "\n".join(
                item.text for item in result.content if hasattr(item, "text")
            )
        return str(result)

    def cleanup(self) -> None:
        """关闭所有 MCP Server 连接"""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._cleanup_async(), self._loop)
            try:
                future.result(timeout=10)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=5)

        self._sessions.clear()
        self._tool_map.clear()
        print("[MCP] 所有连接已关闭")

    async def _cleanup_async(self) -> None:
        """异步关闭所有上下文"""
        if self._exit_stack:
            await self._exit_stack.__aexit__(None, None, None)
