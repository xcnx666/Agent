from .base import ToolBase


class Read(ToolBase):
    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return (
            "读取本地文本文件内容。Args: file_path (str) 文件路径。"
            " 成功返回文件内容，失败返回 Error 信息。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "要读取的文件路径"}
            },
            "required": ["file_path"],
        }

    def execute(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except IsADirectoryError:
            return f"Error: {file_path} is a directory."
        except UnicodeDecodeError:
            return f"Error: {file_path} is not a UTF-8 text file."
        except Exception as e:
            return f"Error: {e}"
