import os
import sys

# 确保项目根目录在 sys.path 上（从任意位置运行测试都能 import）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import ToolRegistry, ALL_TOOLS
from memory import BufferMemory
from agent import Agent
from llm import MockLLM
from prompt import SYSTEM_PROMPT
from core.guardrail import Guardrail
from config import ToolCall, ModelResponse


def test_registry_schemas():
    reg = ToolRegistry()
    for t in ALL_TOOLS:
        reg.register(t)
    schemas = reg.schemas()
    names = {s["function"]["name"] for s in schemas}
    assert {"read", "write", "edit", "bash"} <= names


def test_registry_execute_unknown():
    reg = ToolRegistry()
    assert "unknown tool" in reg.execute("nope", {})


def test_agent_runs_with_mock():
    reg = ToolRegistry()
    for t in ALL_TOOLS:
        reg.register(t)
    agent = Agent(
        llm=MockLLM(final_text="ok"),
        registry=reg,
        memory=BufferMemory(system_prompt=SYSTEM_PROMPT),
        guardrail=Guardrail(),
    )
    resp = agent.run("hello")
    assert resp.content == "ok"


def test_agent_tool_loop_with_mock():
    # 脚本化 Mock：先调 write，再给最终回复
    reg = ToolRegistry()
    for t in ALL_TOOLS:
        reg.register(t)

    scripted = [
        ModelResponse(
            content="",
            tool_calls=[
                ToolCall(
                    id="c1",
                    name="write",
                    arguments={"file_path": "/tmp/koda_test.txt", "content": "hi"},
                )
            ],
        ),
        ModelResponse(content="完成", tool_calls=[]),
    ]
    agent = Agent(
        llm=MockLLM(scripted=scripted),
        registry=reg,
        memory=BufferMemory(system_prompt=SYSTEM_PROMPT),
        guardrail=Guardrail(),
    )
    resp = agent.run("写个文件")
    assert resp.content == "完成"
    assert os.path.exists("/tmp/koda_test.txt")
    with open("/tmp/koda_test.txt") as f:
        assert f.read() == "hi"


def test_guardrail_blocks_rm_rf():
    g = Guardrail()
    allowed, reason = g.check("bash", {"command": "rm -rf /"})
    assert allowed is False
    assert "拦截" in reason


def test_guardrail_allows_normal_bash():
    g = Guardrail()
    allowed, _ = g.check("bash", {"command": "ls -la"})
    assert allowed is True
