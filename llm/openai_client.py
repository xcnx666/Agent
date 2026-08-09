import os
import json
from typing import List, Dict, Any, Optional

from openai import OpenAI
from dotenv import load_dotenv

from logger import logger
from config import ModelResponse, ToolCall, ModelConfig, env_first
from .base import LLM_BASE


class OpenAIClient(LLM_BASE):
    """OpenAI 兼容的流式客户端（也兼容任意 OpenAI 协议网关）。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = True,
    ):
        load_dotenv()  # 从当前工作目录加载 .env（若存在）
        # 统一走 config.env_first 别名表，兼容 LLM_API_BASE / OPENAI_BASE_URL 等写法
        self.api_key = api_key or env_first("api_key")
        self.base_url = base_url or env_first("base_url")
        self.model = model or env_first("model")
        self.stream = stream

        if not self.api_key or not self.model:
            logger.warning(
                "LLM api_key 或 model 未配置（检查 .env 的 LLM_API_KEY / LLM_MODEL），"
                "调用会失败；可用 --mock 测试"
            )

        self.client = OpenAI(api_key=self.api_key or "EMPTY", base_url=self.base_url or None)

    def _convert_tools(self, tools: Optional[list]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for t in tools or []:
            if isinstance(t, dict) and t.get("type") == "function":
                out.append(t)
            elif hasattr(t, "to_openai_schema"):
                out.append(t.to_openai_schema())
            else:
                logger.warning(f"未知工具格式，已跳过: {t!r}")
        return out

    def chat(
        self, messages: List[Dict[str, Any]], tools: Optional[list] = None
    ) -> ModelResponse:
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": self.stream,
        }
        converted = self._convert_tools(tools)
        if converted:
            params["tools"] = converted
            params["tool_choice"] = "auto"

        if self.stream:
            return self._stream(params)
        return self._non_stream(params)

    def _non_stream(self, params: Dict[str, Any]) -> ModelResponse:
        resp = self.client.chat.completions.create(**params)
        msg = resp.choices[0].message
        tool_calls = self._assemble_toolcalls(msg.tool_calls)
        return ModelResponse(content=msg.content or "", tool_calls=tool_calls, raw=resp)

    def _stream(self, params: Dict[str, Any]) -> ModelResponse:
        stream = self.client.chat.completions.create(**params)
        content_parts: List[str] = []
        buf: Dict[int, Dict[str, str]] = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content_parts.append(delta.content)
                print(delta.content, end="", flush=True)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    i = tc.index
                    if i not in buf:
                        buf[i] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        buf[i]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            buf[i]["name"] += tc.function.name
                        if tc.function.arguments:
                            buf[i]["arguments"] += tc.function.arguments

        if content_parts:
            print(flush=True)

        tool_calls = self._assemble_toolcalls_from_buf(buf)
        return ModelResponse(content="".join(content_parts), tool_calls=tool_calls, raw=None)

    @staticmethod
    def _assemble_toolcalls(raw_calls) -> List[ToolCall]:
        out: List[ToolCall] = []
        for tc in raw_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            out.append(
                ToolCall(id=tc.id, type="function", name=tc.function.name, arguments=args)
            )
        return out

    @staticmethod
    def _assemble_toolcalls_from_buf(buf: Dict[int, Dict[str, str]]) -> List[ToolCall]:
        out: List[ToolCall] = []
        for i in sorted(buf):
            b = buf[i]
            try:
                args = json.loads(b["arguments"] or "{}")
            except Exception:
                args = {}
            out.append(
                ToolCall(id=b["id"], type="function", name=b["name"], arguments=args)
            )
        return out
