import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from openai_adapter import (
    handle_models,
    handle_chat_completions,
    MODEL_REACT,
    MODEL_PLANNER,
)


def test_models_endpoint():
    code, body = handle_models()
    assert code == 200
    ids = [m["id"] for m in body["data"]]
    assert MODEL_REACT in ids and MODEL_PLANNER in ids


def test_chat_completions_mock_non_stream():
    code, body = handle_chat_completions(
        {
            "model": MODEL_REACT,
            "messages": [{"role": "user", "content": "你好"}],
        },
        mock=True,
    )
    assert code == 200
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"]
    assert body["usage"]["total_tokens"] > 0


def test_chat_completions_with_history():
    # 历史上下文应被带入，且最后一问只执行一次
    code, body = handle_chat_completions(
        {
            "model": MODEL_PLANNER,
            "messages": [
                {"role": "system", "content": "你是测试助手"},
                {"role": "user", "content": "第一问"},
                {"role": "assistant", "content": "第一答"},
                {"role": "user", "content": "第二问"},
            ],
        },
        mock=True,
    )
    assert code == 200
    assert body["model"] == MODEL_PLANNER


def test_chat_completions_stream():
    code, body = handle_chat_completions(
        {
            "model": MODEL_REACT,
            "stream": True,
            "messages": [{"role": "user", "content": "hi"}],
        },
        mock=True,
    )
    assert code == 200
    assert isinstance(body, str)
    assert "data: [DONE]" in body
    assert "chat.completion.chunk" in body


def test_chat_completions_missing_messages():
    code, body = handle_chat_completions({}, mock=True)
    assert code == 400
    assert "error" in body
