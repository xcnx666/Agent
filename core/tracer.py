import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# 近似成本参数（USD / 1M tokens），仅用于估算，可在 README 中按实际模型调整
DEFAULT_COST_PER_1M = {"input": 0.15, "output": 0.60}


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


class Tracer:
    """运行轨迹记录：llm 调用 / 工具调用 / 计划 / 最终回复，并估算 token 成本。"""

    def __init__(self, cost_per_1m: Optional[Dict[str, float]] = None):
        self.cost_per_1m = cost_per_1m or DEFAULT_COST_PER_1M
        self.events: List[Dict[str, Any]] = []
        self._input_tokens = 0
        self._output_tokens = 0
        self.started = _ts()
        self.finished: Optional[str] = None

    # ---------- 记录 ----------
    def record(self, kind: str, **data) -> None:
        self.events.append({"kind": kind, "ts": _ts(), **data})

    def record_user(self, question: str) -> None:
        self.record("user", question=question)

    def record_final(self, content: str) -> None:
        self.finished = _ts()
        self.record("final", content=content)

    def record_llm(
        self,
        messages: List[Dict[str, Any]],
        response: Any,
        model: Optional[str] = None,
    ) -> None:
        # 优先取真实 usage（非流式时 openai 会返回）
        usage = getattr(getattr(response, "raw", None), "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None)
        out_tok = getattr(usage, "completion_tokens", None)
        content = getattr(response, "content", "") or ""
        if in_tok is None:
            in_tok = sum(_estimate_tokens(str(m)) for m in messages)
        if out_tok is None:
            out_tok = _estimate_tokens(content)
        self._input_tokens += in_tok
        self._output_tokens += out_tok
        n_calls = len(getattr(response, "tool_calls", []) or [])
        self.record(
            "llm",
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            tool_calls=n_calls,
        )

    def record_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        result: Optional[str] = None,
        blocked: bool = False,
        reason: Optional[str] = None,
    ) -> None:
        self.record(
            "tool",
            name=name,
            arguments=arguments,
            result=result,
            blocked=blocked,
            reason=reason,
        )

    def record_plan(self, plan: Dict[str, Any]) -> None:
        self.record("plan", plan=plan)

    # ---------- 汇总 / 导出 ----------
    def summary(self) -> Dict[str, Any]:
        llm_calls = sum(1 for e in self.events if e["kind"] == "llm")
        tool_calls = sum(1 for e in self.events if e["kind"] == "tool" and not e.get("blocked"))
        blocked = sum(1 for e in self.events if e["kind"] == "tool" and e.get("blocked"))
        cost = (
            self._input_tokens / 1e6 * self.cost_per_1m["input"]
            + self._output_tokens / 1e6 * self.cost_per_1m["output"]
        )
        return {
            "llm_calls": llm_calls,
            "tool_calls": tool_calls,
            "blocked_tools": blocked,
            "input_tokens": self._input_tokens,
            "output_tokens": self._output_tokens,
            "estimated_cost_usd": round(cost, 6),
            "started": self.started,
            "finished": self.finished,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {"summary": self.summary(), "events": self.events}

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path
