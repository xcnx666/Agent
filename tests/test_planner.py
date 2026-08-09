import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent import PlannerAgent
from tools import ToolRegistry, ALL_TOOLS
from llm import MockLLM
from core.guardrail import Guardrail
from config import ModelResponse


def _registry():
    reg = ToolRegistry()
    for t in ALL_TOOLS:
        reg.register(t)
    return reg


def test_planner_parses_and_executes_steps():
    scripted = [
        ModelResponse(content='["步骤一：读取配置", "步骤二：汇总结果"]'),
        ModelResponse(content="步骤一完成"),
        ModelResponse(content="步骤二完成"),
    ]
    llm = MockLLM(scripted=scripted)
    agent = PlannerAgent(llm=llm, registry=_registry(), guardrail=Guardrail())
    resp = agent.run("完成一个演示任务")
    assert "步骤一" in resp.content
    assert "步骤二" in resp.content
    assert "步骤一完成" in resp.content
    assert "步骤二完成" in resp.content
    assert llm.calls == 3  # 1 次计划 + 2 次子任务


def test_planner_fallback_single_step():
    # 计划回复不是 JSON -> 回退为单步，再由 worker 执行一次
    llm = MockLLM(final_text="非 JSON 回复")
    agent = PlannerAgent(llm=llm, registry=_registry(), guardrail=Guardrail())
    resp = agent.run("随便做点事")
    assert llm.calls == 2
    assert resp.content


def test_parse_plan_embedded_json():
    from agent.planner import _parse_plan
    from config import Plan

    plan = _parse_plan('好的，计划如下：```json\n["A", "B"]\n```', "goal")
    assert isinstance(plan, Plan)
    assert [s.description for s in plan.steps] == ["A", "B"]
