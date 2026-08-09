import os
import uuid
import tempfile
import subprocess
from typing import Optional

from .base import ToolBase
from logger import logger


class Bash(ToolBase):
    """执行 Shell 命令。默认走 Docker 沙箱；Docker 不可用时回退本地执行。"""

    def __init__(
        self,
        sandbox: bool = True,
        timeout: int = 60,
        workspace: Optional[str] = None,
    ):
        self.sandbox = sandbox
        self.timeout = timeout
        self.workspace = workspace
        self._docker = None
        if sandbox:
            try:
                import docker

                self._docker = docker.from_env()
            except Exception as e:
                logger.warning(f"Docker 不可用，Bash 回退到本地执行: {e}")
                self.sandbox = False

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "执行 Shell/Bash 命令，返回 stdout/stderr 与退出码。"
            " 危险命令（如 rm -rf /）会被护栏拦截。默认在 Docker 沙箱中运行。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 Shell 命令"}
            },
            "required": ["command"],
        }

    def execute(self, command: str) -> str:
        if self.sandbox and self._docker is not None:
            return self._run_sandbox(command)
        return self._run_local(command)

    def _run_local(self, command: str) -> str:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return f"[exit {proc.returncode}]\n{out}"
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {self.timeout}s"
        except Exception as e:
            return f"Error: {e}"

    def _run_sandbox(self, command: str) -> str:
        try:
            image = "python:3.11-slim"
            try:
                self._docker.images.get(image)
            except Exception:
                self._docker.images.pull(image)

            workspace = self.workspace or tempfile.mkdtemp(prefix="koda_sandbox_")
            container = self._docker.containers.create(
                image,
                name=f"koda-sandbox-{uuid.uuid4().hex[:8]}",
                command=["sleep", "30"],
                tty=True,
                working_dir="/workspace",
                volumes={os.path.abspath(workspace): {"bind": "/workspace", "mode": "rw"}},
            )
            container.start()
            try:
                res = container.exec_run(["bash", "-c", command], workdir="/workspace")
                return f"[exit {res.exit_code}]\n{res.output.decode('utf-8', 'replace')}"
            finally:
                try:
                    container.stop()
                    container.remove(force=True)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"沙箱执行失败，回退本地: {e}")
            return self._run_local(command)
