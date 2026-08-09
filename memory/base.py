from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class Memory(ABC):
    """对话记忆接口。"""

    @abstractmethod
    def set_system(self, prompt: str) -> None:
        """设置/更新 system 提示词。"""

    @abstractmethod
    def add(self, message: Dict[str, Any]) -> None:
        """追加一条消息（user / assistant / tool 等）。"""

    @abstractmethod
    def get_messages(self) -> List[Dict[str, Any]]:
        """返回完整消息列表（含 system）。"""

    @abstractmethod
    def clear(self) -> None:
        """清空对话历史（保留 system）。"""
