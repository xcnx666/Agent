import os

from .base import ToolBase


class Write(ToolBase):
    @property
    def name(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return (
            "将内容写入本地文本文件（覆盖式）。Args: file_path (str), content (str)。"
            " 会自动创建父目录。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "目标文件路径"},
                "content": {"type": "string", "description": "要写入的内容"},
            },
            "required": ["file_path", "content"],
        }

    def execute(self, file_path: str, content: str) -> str:
        try:
            parent = os.path.dirname(file_path) or "."
            os.makedirs(parent, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error: {e}"
