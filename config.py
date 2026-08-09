from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel


@dataclass
class ModelConfig:
    """LLM 连接配置（可由环境变量或代码注入）。"""

    provider: str = "openai"
    model: str = ""
    api_key: str = ""
    base_url: str = ""


class ToolCall(BaseModel):
    """模型返回的工具调用，统一为可属性访问 + 可序列化结构。"""

    id: str = ""
    type: str = "function"
    name: str = ""
    arguments: dict = {}


class ModelResponse(BaseModel):
    """LLM 一次推理的统一返回。"""

    content: str = ""
    tool_calls: list[ToolCall] = []
    raw: Any = None


class PlanStep(BaseModel):
    """规划中的一个步骤。"""

    description: str
    status: str = "pending"  # pending | running | done | failed
    result: str = ""


class Plan(BaseModel):
    """由 Planner 产出的任务计划。"""

    goal: str
    steps: list[PlanStep] = []

    def mark_done(self, index: int, result: str) -> None:
        if 0 <= index < len(self.steps):
            self.steps[index].status = "done"
            self.steps[index].result = result


# 环境变量别名表：按顺序取第一个非空值，兼容常见写法
ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "model": ("LLM_MODEL", "OPENAI_MODEL", "MODEL_NAME", "model"),
    "api_key": ("LLM_API_KEY", "OPENAI_API_KEY", "API_KEY", "api_key"),
    "base_url": (
        "LLM_BASE_URL",
        "LLM_API_BASE",  # 用户 .env 中的写法
        "OPENAI_BASE_URL",
        "OPENAI_API_BASE",
        "base_url",
    ),
    "api_version": ("LLM_API_VERSION", "OPENAI_API_VERSION", "api_version"),
}


def env_first(field: str, default: str = "") -> str:
    """按别名表依次查找环境变量，返回第一个非空值。"""
    import os

    for name in ENV_ALIASES.get(field, ()):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return default


def load_model_config() -> ModelConfig:
    """从环境变量读取配置，兼容多种命名。"""
    import os

    return ModelConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=env_first("model"),
        api_key=env_first("api_key"),
        base_url=env_first("base_url"),
    )
