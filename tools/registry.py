import json
from typing import Any, Dict, List, Optional

from .base import ToolBase
from logger import logger


class ToolRegistry:
    """工具注册表：注册、按名查找、导出 OpenAI schema、统一执行。"""

    def __init__(self):
        self._tools: Dict[str, ToolBase] = {}

    def register(self, tool: ToolBase) -> "ToolRegistry":
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，已覆盖")
        self._tools[tool.name] = tool
        return self

    def get(self, name: str) -> Optional[ToolBase]:
        return self._tools.get(name)

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def execute(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        tool = self.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        try:
            result = tool.execute(**(arguments or {}))
        except TypeError as e:
            return f"Error: invalid arguments for '{name}': {e}"
        except Exception as e:
            return f"Error: tool '{name}' failed: {e}"

        if not isinstance(result, str):
            try:
                result = json.dumps(result, ensure_ascii=False)
            except Exception:
                result = str(result)
        return result
