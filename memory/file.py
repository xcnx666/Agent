import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class FileMemory:
    """文件持久化的长期记忆：结构化笔记 + 轻量关键词检索（跨会话可用）。"""

    def __init__(self, path: str):
        self.path = path
        self._notes: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._notes = data.get("notes", [])
            except Exception:
                self._notes = []

    def add_note(self, key: str, content: str, tags: Optional[List[str]] = None) -> None:
        self._notes.append(
            {
                "key": key,
                "content": content,
                "tags": tags or [],
                "ts": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._save()

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """按关键词简单打分检索，返回最相关的笔记。"""
        keywords = [kw for kw in query.lower().split() if kw]
        if not keywords:
            return []
        scored: List[tuple] = []
        for n in self._notes:
            text = (
                f"{n.get('key','')} {n.get('content','')} {' '.join(n.get('tags',[]))}"
            ).lower()
            score = sum(1 for kw in keywords if kw in text)
            if score:
                scored.append((score, n))
        scored.sort(key=lambda x: -x[0])
        return [n for _, n in scored[:limit]]

    def all(self) -> List[Dict[str, Any]]:
        return list(self._notes)

    def clear(self) -> None:
        self._notes = []
        self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"notes": self._notes}, f, ensure_ascii=False, indent=2)
