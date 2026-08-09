from .base import ToolBase


class Edit(ToolBase):
    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return (
            "将文件中的 old_text 精确替换为 new_text（仅替换第一处匹配）。"
            " Args: file_path (str), old_text (str), new_text (str)。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
                "old_text": {"type": "string", "description": "要被替换的文本"},
                "new_text": {"type": "string", "description": "替换后的新文本"},
            },
            "required": ["file_path", "old_text", "new_text"],
        }

    def execute(self, file_path: str, old_text: str, new_text: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_text not in content:
                return "Error: old_text not found."
            content = content.replace(old_text, new_text, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return "Successfully edited file."
        except Exception as e:
            return f"Error: {e}"
