from abc import ABC, abstractmethod
from typing import Any, Optional

from llm.base import LLM_BASE
from tools.registry import ToolRegistry
from memory.buffer import BufferMemory
from memory.base import Memory
from core.guardrail import Guardrail
from core.tracer import Tracer


class AgentBase(ABC):
    """所有 Agent 的基类：统一注入 LLM / 工具 / 记忆 / 护栏 / 轨迹 / 步数限制。"""

    def __init__(
        self,
        llm: LLM_BASE,
        registry: ToolRegistry,
        memory: Optional[Memory] = None,
        guardrail: Optional[Guardrail] = None,
        tracer: Optional[Tracer] = None,
        max_llm_steps: int = 25,
        max_tool_steps: int = 60,
        system_prompt: str = "",
    ):
        self.llm = llm
        self.registry = registry
        self.memory = memory or BufferMemory()
        if system_prompt:
            self.memory.set_system(system_prompt)
        self.guardrail = guardrail or Guardrail()
        self.tracer = tracer
        self.max_llm_steps = max_llm_steps
        self.max_tool_steps = max_tool_steps

    @abstractmethod
    def run(self, question: str) -> Any:
        raise NotImplementedError
