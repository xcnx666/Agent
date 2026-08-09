from abc import ABC, abstractmethod
from typing import Any, Dict


class ToolBase(ABC):
    """所有工具的抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（模型据此调用）。"""

    @property
    @abstractmethod
    def description(self) -> str:
        """给模型看的工具说明。"""

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """输入参数的 JSON Schema。"""

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具，返回字符串结果（出错也返回字符串错误信息）。"""
