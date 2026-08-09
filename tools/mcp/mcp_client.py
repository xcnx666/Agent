import asyncio
import json
from typing import Any, Dict, List, Optional

from logger import logger

from ..base import ToolBase
from ..registry import ToolRegistry


def _run(coro):
    """在已有/新建事件循环中运行协程（让 sync Agent 也能调 async MCP）。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class MCPClient:
    """MCP (Model Context Protocol) 客户端。

    依赖 `mcp` 包（stdio 传输）。未安装时 connect/list_tools/call_tool 会给出明确错误。
    """

    def __init__(self):
        self._session = None
        self._tools: List[dict] = []

    async def connect(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as e:
            raise RuntimeError("未安装 mcp 包，请运行: pip install mcp") from e

        params = StdioServerParameters(command=command, args=args or [], env=env)
        read, write = await stdio_client(params)
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def list_tools(self) -> List[dict]:
        if not self._session:
            raise RuntimeError("尚未连接，请先调用 connect()")
        resp = await self._session.list_tools()
        self._tools = [self._to_schema(t) for t in resp.tools]
        return self._tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        if not self._session:
            raise RuntimeError("尚未连接")
        result = await self._session.call_tool(name, arguments)
        texts = []
        for item in getattr(result, "content", []) or []:
            if getattr(item, "type", None) == "text":
                texts.append(item.text)
        return "\n".join(texts) if texts else str(result)

    async def close(self):
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass

    @staticmethod
    def _to_schema(tool) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
                or {"type": "object", "properties": {}},
            },
        }


class _MCPTool(ToolBase):
    """把单个 MCP 工具包装成同步 ToolBase。"""

    def __init__(self, client: MCPClient, schema: dict):
        self._client = client
        self._schema = schema

    @property
    def name(self) -> str:
        return self._schema["function"]["name"]

    @property
    def description(self) -> str:
        return self._schema["function"]["description"]

    @property
    def parameters(self) -> dict:
        return self._schema["function"]["parameters"]

    def execute(self, **kwargs) -> str:
        return _run(self._client.call_tool(self.name, kwargs))


def load_mcp_registry(config_path: str) -> ToolRegistry:
    """读取 MCP config.json，连接各 server，返回已注册工具的 ToolRegistry。

    若 mcp 未安装或某 server 启动失败，会记录警告并跳过该项。
    """
    reg = ToolRegistry()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        logger.warning(f"读取 MCP 配置失败: {e}")
        return reg

    for name, spec in cfg.get("servers", {}).items():
        try:
            client = MCPClient()
            _run(
                client.connect(
                    spec.get("command"), spec.get("args"), spec.get("env")
                )
            )
            schemas = _run(client.list_tools())
            for s in schemas:
                reg.register(_MCPTool(client, s))
            logger.info(f"MCP server '{name}' 加载了 {len(schemas)} 个工具")
        except Exception as e:
            logger.warning(f"MCP server '{name}' 加载失败，已跳过: {e}")
    return reg
