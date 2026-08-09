from typing import List, Dict, Any, Optional

from config import ModelResponse, ToolCall
from .base import LLM_BASE


class MockLLM(LLM_BASE):
    """可脚本化的假 LLM，用于测试与演示（无需 API key）。"""

    def __init__(
        self,
        scripted: Optional[List[ModelResponse]] = None,
        final_text: str = "[Mock] 任务已完成。",
    ):
        self.scripted = list(scripted or [])
        self.final_text = final_text
        self.calls = 0
        self.last_messages: List[Dict[str, Any]] = []

    def chat(
        self, messages: List[Dict[str, Any]], tools: Optional[list] = None
    ) -> ModelResponse:
        self.calls += 1
        self.last_messages = messages
        if self.scripted:
            return self.scripted.pop(0)
        return ModelResponse(content=self.final_text, tool_calls=[])
