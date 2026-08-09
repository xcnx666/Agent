import re
from typing import Tuple, Dict, Any, List, Optional, Callable

# 危险命令模式（bash 工具执行前会被拦截）
DESTRUCTIVE_PATTERNS: List[str] = [
    r"\brm\s+-rf\b",
    r"\brm\s+-fr\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-z]*f",
    r"\bdd\b\s+if=",
    r":\(\)\s*\{",
    r"\bchmod\s+-R\s+000\b",
    r"\bmkfs\b",
    r"\bshutdown\b",
    r"\bhalt\b",
    r"\breboot\b",
]


class Guardrail:
    """工具执行前的安全检查。

    行为优先级：命中危险命令时，
      1) allow_destructive=True -> 直接放行（记录警告）
      2) 提供了 approver 回调 -> 交给回调裁决（人工审批）
      3) 否则拦截
    """

    def __init__(
        self,
        allow_destructive: bool = False,
        approver: Optional[Callable[[str], bool]] = None,
    ):
        self.allow_destructive = allow_destructive
        self.approver = approver

    def check(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        """返回 (是否放行, 原因)。"""
        if tool_name == "bash":
            cmd = (arguments or {}).get("command", "")
            for pat in DESTRUCTIVE_PATTERNS:
                if re.search(pat, cmd):
                    if self.allow_destructive:
                        return (
                            True,
                            f"⚠️ 检测到危险命令，已放行(allow_destructive=True): {pat}",
                        )
                    if self.approver is not None:
                        if self.approver(cmd):
                            return True, f"✅ 人工审批通过: {cmd[:80]}"
                        return False, f"🛡️ 人工拒绝: {cmd[:80]}"
                    return False, f"🛡️ 拦截危险命令(匹配 {pat}): {cmd[:80]}"
        return True, ""
