import json
from datetime import datetime
from typing import Any, Dict, Optional

from memory import BufferMemory


class Session:
    """会话状态机：created -> running -> finished / error，支持 save/restore 暂停恢复。

    保存的内容包括对话消息（可完整恢复上下文）与运行轨迹。
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self.state = "created"
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.last_response = None

    def run(self, question: str):
        self.state = "running"
        try:
            self.last_response = self.agent.run(question)
            self.state = "finished"
        except Exception as e:
            self.state = "error"
            raise
        return self.last_response

    def save(self, path: str) -> str:
        tracer = getattr(self.agent, "tracer", None)
        data = {
            "state": self.state,
            "created_at": self.created_at,
            "messages": self.agent.memory.get_messages(),
            "tracer": tracer.to_dict() if tracer else None,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def restore(
        cls,
        path: str,
        llm,
        registry,
        guardrail=None,
        tracer=None,
        system_prompt: str = "",
    ) -> "Session":
        # 惰性导入，避免与 core/__init__ 循环依赖
        from agent import ReActAgent

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        memory = BufferMemory()
        for m in data.get("messages", []):
            if m.get("role") == "system":
                memory.set_system(m.get("content", ""))
            else:
                memory.add(m)

        agent = ReActAgent(
            llm=llm,
            registry=registry,
            memory=memory,
            guardrail=guardrail,
            tracer=tracer,
            system_prompt=system_prompt,
        )
        session = cls(agent)
        session.state = data.get("state", "created")
        return session
