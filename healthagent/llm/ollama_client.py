"""Ollama adapter. Neutral history is translated to Ollama's (OpenAI-ish) message shape in chat();
neutral serialize_* (from the base) are reused. The SDK import is lazy so this module imports
without `ollama` installed.

Ollama's native API can't force a *named* tool, so `supports_force_tool=False` and `force_tool` is a
no-op here (the text nudge still applies); the signature-level completion check + hard fail-safe
remain the guarantee.
"""
from __future__ import annotations

import os

from .client import LLMClient
from .errors import MissingSDK, ModelUnavailable
from .schemas import ChatResponse, ToolCall

DEFAULT_MODEL = "llama3.1:8b"  # tool-capable; qwen2.5:7b / llama3.2:3b are smaller documented options


def to_ollama_request(messages: list[dict]) -> list[dict]:
    """Neutral messages -> Ollama messages (pure; no SDK)."""
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            out.append({
                "role": "assistant",
                "content": m.get("content", ""),
                "tool_calls": [{"function": {"name": tc["name"], "arguments": tc.get("args", {})}}
                               for tc in m["tool_calls"]],
            })
        elif role == "tool":
            out.append({"role": "tool", "content": m.get("content", ""), "name": m.get("name", "")})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def parse_ollama_response(message) -> ChatResponse:
    """Ollama message (obj or dict) -> neutral ChatResponse. Synthesizes ids (Ollama omits them)."""
    content = _attr(message, "content") or ""
    raw_calls = _attr(message, "tool_calls") or []
    tool_calls = []
    for i, tc in enumerate(raw_calls):
        fn = _attr(tc, "function") or {}
        name = _attr(fn, "name") or ""
        args = _attr(fn, "arguments")
        parse_error = None
        if isinstance(args, str):  # some models emit a JSON string
            import json
            try:
                args = json.loads(args)
            except (ValueError, TypeError) as exc:
                parse_error, args = f"invalid JSON arguments: {exc}", {}
        if not isinstance(args, dict):
            args = {}
        tool_calls.append(ToolCall(id=f"call_{i}_{name}", name=name, args=args, parse_error=parse_error))
    return ChatResponse(text=content, tool_calls=tool_calls, provider_raw=message)


def _attr(obj, name):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


class OllamaBackend(LLMClient):
    provider = "ollama"
    supports_force_tool = False

    def __init__(self) -> None:
        try:
            import ollama  # lazy: module imports fine without the SDK
        except ImportError as exc:
            raise MissingSDK("ollama SDK not installed — run `make live-install`") from exc
        self._ollama = ollama
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._client = ollama.Client(host=self.host)
        try:
            self._client.show(self.model)  # verify the model is actually pulled
        except Exception as exc:  # noqa: BLE001 - any failure means unusable
            raise ModelUnavailable(f"Ollama model '{self.model}' not available — run `ollama pull {self.model}`") from exc

    def chat(self, messages, tools=None, *, force_tool=None) -> ChatResponse:
        resp = self._client.chat(model=self.model, messages=to_ollama_request(messages), tools=tools or None)
        return parse_ollama_response(_attr(resp, "message") or resp)
