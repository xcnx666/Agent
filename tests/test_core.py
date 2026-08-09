import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from memory import FileMemory
from core.tracer import Tracer
from core.guardrail import Guardrail
from core.session import Session
from config import ModelResponse, ToolCall
from llm import MockLLM
from tools import ToolRegistry, Write
from agent import ReActAgent


def test_file_memory_roundtrip(tmp_path):
    p = str(tmp_path / "mem.json")
    m = FileMemory(p)
    m.add_note("python", "用户偏好 Python 开发", tags=["lang"])

    m2 = FileMemory(p)  # 重新加载
    assert len(m2.all()) == 1
    hits = m2.search("python 开发")
    assert hits and hits[0]["key"] == "python"
    assert m2.search("不存在的词") == []


def test_tracer_records_and_summary(tmp_path):
    t = Tracer()
    t.record_user("hi")
    t.record_llm([{"role": "user", "content": "hi"}], ModelResponse(content="ok"))
    t.record_tool("bash", {"command": "ls"}, result="ok")
    t.record_tool("bash", {"command": "rm -rf /"}, blocked=True, reason="blocked")

    s = t.summary()
    assert s["llm_calls"] == 1
    assert s["tool_calls"] == 1
    assert s["blocked_tools"] == 1
    assert s["estimated_cost_usd"] >= 0

    p = str(tmp_path / "trace.json")
    t.save(p)
    assert os.path.exists(p)
    import json

    with open(p) as f:
        assert json.load(f)["summary"]["llm_calls"] == 1


def test_session_save_restore(tmp_path):
    reg = ToolRegistry()
    reg.register(Write())

    llm = MockLLM(final_text="done")
    agent = ReActAgent(llm=llm, registry=reg)
    sess = Session(agent)
    sess.run("你好")

    p = str(tmp_path / "session.json")
    sess.save(p)

    restored = Session.restore(p, llm=MockLLM(final_text="done2"), registry=reg)
    msgs = restored.agent.memory.get_messages()
    assert any(m["role"] == "user" and m["content"] == "你好" for m in msgs)
    assert restored.run("继续").content == "done2"


def test_guardrail_approver():
    # 人工审批通过 -> 放行
    g_yes = Guardrail(approver=lambda cmd: True)
    allowed, _ = g_yes.check("bash", {"command": "rm -rf /tmp/x"})
    assert allowed is True

    # 人工拒绝 -> 拦截
    g_no = Guardrail(approver=lambda cmd: False)
    allowed, reason = g_no.check("bash", {"command": "rm -rf /tmp/x"})
    assert allowed is False
    assert "拒绝" in reason
