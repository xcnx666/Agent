from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def _read(name: str) -> str:
    p = _PROMPT_DIR / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


# 默认系统提示词（Alpha Agent persona）
SYSTEM_PROMPT = _read("alpha.md")

# ReAct / 规划模板（可选增强，默认系统提示词已包含执行原则）
REACT_PROMPT_TEMPLATE = _read("react_prompt.md")
PLANNER_PROMPT_TEMPLATE = _read("plan_prompt.md")
PLAN_PROMPT = PLANNER_PROMPT_TEMPLATE

__all__ = [
    "SYSTEM_PROMPT",
    "REACT_PROMPT_TEMPLATE",
    "PLANNER_PROMPT_TEMPLATE",
    "PLAN_PROMPT",
]
