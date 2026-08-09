from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from config import ModelResponse


class LLM_BASE(ABC):
    """所有 LLM 提供方的统一抽象。"""

    @abstractmethod
    def chat(
        self, messages: List[Dict[str, Any]], tools: Optional[list] = None
    ) -> ModelResponse:
        """执行一次推理，返回统一的 ModelResponse。"""
        raise NotImplementedError
