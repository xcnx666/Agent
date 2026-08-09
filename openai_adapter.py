"""Koda 的 OpenAI 兼容适配端点。

让 Open WebUI 等任何 OpenAI 兼容客户端，把 Koda 智能体当"模型"使用：
  GET  /v1/models            -> 列出 koda-react / koda-planner
  POST /v1/chat/completions  -> 接收 OpenAI 消息历史，交给 Koda Agent 执行，返回 OpenAI 格式

多轮对话：客户端每次携带完整历史，本适配器把历史灌进 Koda 记忆，再用最后一问触发执行。
"""

import json
import time
import uuid
from typing import Any, Dict, Optional, Tuple

from llm import LLM, MockLLM
from tools import ToolRegistry, ALL_TOOLS
from memory import BufferMemory
from agent import Agent, PlannerAgent
from core.guardrail import Guardrail
from core.tracer import Tracer
from prompt import SYSTEM_PROMPT

MODEL_REACT = "koda-react"
MODEL_PLANNER = "koda-planner"

MODELS = [
    {
        "id": MODEL_REACT,
        "object": "model",
        "created": 0,
        "owned_by": "koda",
        "name": "Koda Agent（ReAct）",
        "supported_parameters": ["stream"],
    },
    {
        "id": MODEL_PLANNER,
        "object": "model",
        "created": 0,
        "owned_by": "koda",
        "name": "Koda Agent（规划编排）",
        "supported_parameters": ["stream"],
    },
]


def handle_models() -> Tuple[int, dict]:
    return 200, {"object": "list", "data": MODELS}


def _build_agent(model: str, mock: bool):
    registry = ToolRegistry()
    for t in ALL_TOOLS:
        registry.register(t)
    guardrail = Guardrail()
    tracer = Tracer()
    llm = MockLLM(final_text="[Mock] 任务已完成。") if mock else LLM(stream=False)
    cls = PlannerAgent if model == MODEL_PLANNER else Agent
    return cls(
        llm=llm,
        registry=registry,
        memory=BufferMemory(),
        guardrail=guardrail,
        tracer=tracer,
    )


def _extract_text(content) -> str:
    """OpenAI 消息 content 可能是字符串或多模态数组，只取文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for seg in content:
            if isinstance(seg, dict) and seg.get("type") == "text":
                parts.append(seg.get("text", ""))
        return "".join(parts)
    return str(content or "")


def _load_history(messages: list) -> Tuple[BufferMemory, str, str]:
    """把 OpenAI 消息历史转换为 Koda 记忆。

    返回 (memory, 最后一问, system_prompt)。最后一问不预置进 memory，
    由 Agent.run 追加，避免重复。
    """
    history = list(messages or [])
    last_user_idx = None
    for i, m in enumerate(history):
        if m.get("role") == "user":
            last_user_idx = i

    question = _extract_text(history[last_user_idx].get("content")) if last_user_idx is not None else ""

    memory = BufferMemory()
    system_prompt = ""
    for i, m in enumerate(history):
        if i == last_user_idx:
            continue
        role = m.get("role")
        if role == "system":
            system_prompt = _extract_text(m.get("content"))
            memory.set_system(system_prompt)
        elif role in ("user", "assistant", "tool"):
            content = _extract_text(m.get("content"))
            entry: Dict[str, Any] = {"role": role, "content": content}
            if role == "tool" and m.get("tool_call_id"):
                entry["tool_call_id"] = m["tool_call_id"]
            memory.add(entry)
    return memory, question, system_prompt


def handle_chat_completions(payload: dict, mock: bool = False):
    model = payload.get("model", MODEL_REACT)
    stream = bool(payload.get("stream", False))
    messages = payload.get("messages", [])
    if not messages:
        return 400, {"error": {"message": "messages is required", "type": "invalid_request_error"}}

    memory, question, system_prompt = _load_history(messages)
    if not question:
        return 400, {"error": {"message": "no user message found", "type": "invalid_request_error"}}

    agent = _build_agent(model, mock)
    agent.memory = memory
    if not system_prompt:
        agent.memory.set_system(SYSTEM_PROMPT)

    resp = agent.run(question)
    content = resp.content or ""
    s = agent.tracer.summary()
    usage = {
        "prompt_tokens": s["input_tokens"],
        "completion_tokens": s["output_tokens"],
        "total_tokens": s["input_tokens"] + s["output_tokens"],
    }

    if stream:
        return _sse_response(model, content)

    body = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": usage,
    }
    return 200, body


def _sse_response(model: str, content: str):
    """以 SSE 流式格式输出（一次性输出 + [DONE]，兼容多数客户端）。"""
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    chunks = [
        {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": content},
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        },
    ]
    lines = "".join(
        f"data: {json.dumps(c, ensure_ascii=False)}\n\n" for c in chunks
    ) + "data: [DONE]\n\n"
    return 200, lines
