"""Koda Harness HTTP 服务（标准库实现，无额外依赖）。

启动:  python server.py --port 8321

接口:
  GET  /health                        -> {"status": "ok"}
  GET  /v1/models                     -> OpenAI 兼容：模型列表（koda-react / koda-planner）
  POST /v1/chat/completions           -> OpenAI 兼容：对话（可 stream，供 Open WebUI 等接入）
  POST /chat                          -> {"question": "...", "mode": "react|planner", "mock": false}

说明: /v1/* 由 openai_adapter 实现，把 Koda 智能体包装成 OpenAI 兼容后端。
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import openai_adapter
from main import build_registry
from llm import LLM, MockLLM
from memory import BufferMemory
from agent import Agent, PlannerAgent
from core.guardrail import Guardrail
from core.tracer import Tracer
from prompt import SYSTEM_PROMPT


def build_harness(mode: str = "react", mock: bool = False):
    registry = build_registry(use_mcp=False)
    memory = BufferMemory(system_prompt=SYSTEM_PROMPT)
    guardrail = Guardrail()
    tracer = Tracer()
    llm = MockLLM(final_text="[Mock] 任务已完成。") if mock else LLM(stream=False)
    agent_cls = PlannerAgent if mode == "planner" else Agent
    agent = agent_cls(
        llm=llm,
        registry=registry,
        memory=memory,
        guardrail=guardrail,
        tracer=tracer,
    )
    return agent, tracer


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, code: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self._send_json(200, {"status": "ok", "harness": "koda"})
        if path == "/v1/models":
            code, obj = openai_adapter.handle_models()
            return self._send_json(code, obj)
        self._send_json(404, {"error": "not found"})

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except Exception as e:
            return self._send_json(400, {"error": f"bad request: {e}"})

        if path == "/v1/chat/completions":
            mock = bool(payload.get("mock", os.getenv("KODA_OPENAI_MOCK") == "1"))
            try:
                code, result = openai_adapter.handle_chat_completions(payload, mock=mock)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            if code == 200 and bool(payload.get("stream", False)):
                return self._send_sse(code, result)
            return self._send_json(code, result)

        if path == "/chat":
            question = (payload.get("question") or "").strip()
            if not question:
                return self._send_json(400, {"error": "missing question"})
            mode = payload.get("mode", "react")
            mock = bool(payload.get("mock", False))
            agent, tracer = build_harness(mode=mode, mock=mock)
            try:
                resp = agent.run(question)
                return self._send_json(
                    200,
                    {
                        "content": resp.content,
                        "summary": tracer.summary(),
                        "trace": tracer.to_dict(),
                    },
                )
            except Exception as e:
                return self._send_json(500, {"error": str(e)})

        self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


def main():
    ap = argparse.ArgumentParser(description="Koda Harness HTTP 服务")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8321)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Koda HTTP 服务已启动: http://{args.host}:{args.port}  (OpenAI 兼容端点 /v1)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
