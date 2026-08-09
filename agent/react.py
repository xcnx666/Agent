import json
from typing import Any

from .base import AgentBase
from config import ModelResponse
from logger import logger


class ReActAgent(AgentBase):
    """ReAct 单循环 Agent：思考 → 工具调用 → 观察 → 重复，直到给出最终回复。"""

    def run(self, question: str) -> ModelResponse:
        if self.tracer:
            self.tracer.record_user(question)

        self.memory.add({"role": "user", "content": question})
        llm_step = 0
        tool_step = 0

        while True:
            if llm_step >= self.max_llm_steps:
                logger.warning("已达到最大推理步数，终止")
                resp = ModelResponse(content="[已达到最大推理步数，任务终止]", tool_calls=[])
                if self.tracer:
                    self.tracer.record_final(resp.content)
                return resp
            llm_step += 1

            messages = self.memory.get_messages()
            response = self.llm.chat(messages=messages, tools=self.registry.schemas())
            if self.tracer:
                self.tracer.record_llm(
                    messages, response, model=getattr(self.llm, "model", None)
                )

            if response is None:
                logger.warning("模型返回为空，重试")
                continue

            # 没有工具调用 → 视为最终回复
            if not response.tool_calls:
                self.memory.add({"role": "assistant", "content": response.content})
                if self.tracer:
                    self.tracer.record_final(response.content)
                return response

            # 构造 assistant 消息（含 tool_calls），回灌给模型
            assistant_msg = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
            self.memory.add(assistant_msg)

            # 逐个执行工具调用
            for tc in response.tool_calls:
                tool_step += 1
                if tool_step >= self.max_tool_steps:
                    logger.warning("已达到最大工具步数")

                allowed, reason = self.guardrail.check(tc.name, tc.arguments)
                if not allowed:
                    logger.warning(reason)
                    if self.tracer:
                        self.tracer.record_tool(
                            tc.name, tc.arguments, blocked=True, reason=reason
                        )
                    self.memory.add(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Tool blocked by guardrail: {reason}",
                        }
                    )
                    continue

                logger.info(f"🔧 调用工具 {tc.name} 参数={tc.arguments}")
                result = self.registry.execute(tc.name, tc.arguments)
                if self.tracer:
                    self.tracer.record_tool(tc.name, tc.arguments, result=result)
                self.memory.add(
                    {"role": "tool", "tool_call_id": tc.id, "content": result}
                )
