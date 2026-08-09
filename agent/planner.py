import json
from typing import Any, List, Type

from .base import AgentBase
from .react import ReActAgent
from config import ModelResponse, Plan, PlanStep
from prompt import SYSTEM_PROMPT, PLANNER_PROMPT_TEMPLATE
from logger import logger


def _parse_plan(content: str, fallback: str) -> Plan:
    """从 LLM 回复中解析 JSON 步骤数组；失败则回退为单步任务。"""
    text = (content or "").strip()

    def steps_from(data) -> List[str]:
        return [
            s if isinstance(s, str) else s.get("description", str(s))
            for s in data
        ]

    # 1) 直接是 JSON 数组
    try:
        data = json.loads(text)
        if isinstance(data, list) and data:
            return Plan(goal=fallback, steps=[PlanStep(description=d) for d in steps_from(data)])
    except Exception:
        pass

    # 2) 内嵌 JSON 数组（如 ```json [...] ``` 或前后有解释文字）
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, list) and data:
                return Plan(goal=fallback, steps=[PlanStep(description=d) for d in steps_from(data)])
        except Exception:
            pass

    # 3) 回退：整件事作为单步
    logger.warning("无法解析计划，回退为单步执行")
    return Plan(goal=fallback, steps=[PlanStep(description=fallback)])


class PlannerAgent(AgentBase):
    """规划式编排：先产出计划，再为每个步骤派生一个 ReAct 子任务执行并汇总。"""

    def __init__(
        self,
        llm,
        registry,
        memory=None,
        guardrail=None,
        tracer=None,
        max_llm_steps: int = 25,
        max_tool_steps: int = 60,
        system_prompt: str = "",
        worker_cls: Type[AgentBase] = None,
        worker_prompt: str = "",
    ):
        super().__init__(
            llm=llm,
            registry=registry,
            memory=memory,
            guardrail=guardrail,
            tracer=tracer,
            max_llm_steps=max_llm_steps,
            max_tool_steps=max_tool_steps,
            system_prompt=system_prompt,
        )
        self.worker_cls = worker_cls or ReActAgent
        self.worker_prompt = worker_prompt or SYSTEM_PROMPT

    def _build_plan(self, question: str) -> Plan:
        prompt = (
            PLANNER_PROMPT_TEMPLATE
            + "\n\n用户目标："
            + question
            + "\n\n请只输出一个 JSON 数组，数组元素为步骤描述字符串，例如：[\"步骤一\", \"步骤二\"]。不要输出其他内容。"
        )
        messages = [{"role": "user", "content": prompt}]
        resp = self.llm.chat(messages=messages, tools=[])
        if self.tracer:
            self.tracer.record_llm(
                messages, resp, model=getattr(self.llm, "model", None)
            )
        return _parse_plan(resp.content, question)

    def run(self, question: str) -> ModelResponse:
        if self.tracer:
            self.tracer.record_user(question)

        plan = self._build_plan(question)
        if self.tracer:
            self.tracer.record_plan(plan.model_dump())

        logger.info(f"📋 计划已生成：{len(plan.steps)} 步")
        sections: List[str] = []

        for i, step in enumerate(plan.steps):
            step.status = "running"
            logger.info(f"🚀 执行步骤 {i + 1}/{len(plan.steps)}: {step.description}")

            worker = self.worker_cls(
                llm=self.llm,
                registry=self.registry,
                guardrail=self.guardrail,
                tracer=self.tracer,
                system_prompt=self.worker_prompt,
            )
            resp = worker.run(
                f"[子任务 {i + 1}/{len(plan.steps)}] {step.description}\n[总体目标] {question}"
            )

            step.status = "done"
            step.result = resp.content
            sections.append(f"## 步骤 {i + 1}: {step.description}\n\n{resp.content}")

        if self.tracer:
            self.tracer.record_final("计划执行完成")

        body = "\n\n---\n\n".join(sections)
        return ModelResponse(content=f"[计划执行完成]\n\n{body}", tool_calls=[])
