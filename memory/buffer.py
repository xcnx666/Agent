from typing import Dict, List, Optional, Any

from .base import Memory


class BufferMemory(Memory):
    """简单的缓冲式记忆：保留 system + 最近 N 条消息。"""

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        max_messages: int = 100,
    ):
        self._system = system_prompt
        self._messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages

    def set_system(self, prompt: str) -> None:
        self._system = prompt

    def add(self, message: Dict[str, Any]) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            self._messages.pop(0)

    def get_messages(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if self._system:
            out.append({"role": "system", "content": self._system})
        out.extend(self._messages)
        return out

    def clear(self) -> None:
        self._messages = []
