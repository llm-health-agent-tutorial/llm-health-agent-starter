"""OpenAI adapter (Chat Completions function-calling). Neutral history -> OpenAI messages in chat()
(neutral serialize_* reused; ids are preserved). Lazy SDK import; key checked without a network call.
`force_tool` maps to a named `tool_choice`."""
from __future__ import annotations

import json
import os

from .client import LLMClient
from .errors import MissingCredential, MissingSDK
from .schemas import ChatResponse, ToolCall

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"  # pinned snapshot; override via OPENAI_MODEL


def to_openai_messages(messages: list[dict]) -> list[dict]:
    """Neutral -> OpenAI Chat Completions messages (pure; no SDK)."""
    out = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            out.append({
                "role": "assistant",
                "content": m.get("content") or "",
                "tool_calls": [{
                    "id": tc["id"], "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc.get("args", {}))},
                } for tc in m["tool_calls"]],
            })
        elif role == "tool":
            out.append({"role": "tool", "tool_call_id": m.get("tool_call_id", ""),
                        "content": m.get("content", "")})
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


def tool_choice_for(force_tool: str | None):
    return {"type": "function", "function": {"name": force_tool}} if force_tool else "auto"


def parse_openai_response(message) -> ChatResponse:
    """OpenAI message (obj or dict) -> neutral ChatResponse."""
    content = _attr(message, "content") or ""
    tool_calls = []
    for tc in (_attr(message, "tool_calls") or []):
        fn = _attr(tc, "function")
        name = _attr(fn, "name") or ""
        raw_args = _attr(fn, "arguments")
        args, parse_error = {}, None
        if isinstance(raw_args, dict):
            args = raw_args
        elif raw_args:
            try:
                args = json.loads(raw_args)
            except (ValueError, TypeError) as exc:
                parse_error = f"invalid JSON arguments: {exc}"
        tool_calls.append(ToolCall(id=_attr(tc, "id") or f"call_{name}", name=name, args=args,
                                   parse_error=parse_error))
    return ChatResponse(text=content, tool_calls=tool_calls, provider_raw=message)


def _attr(obj, name):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


class OpenAIBackend(LLMClient):
    provider = "openai"
    supports_force_tool = True

    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise MissingSDK("openai SDK not installed — run `make live-install`") from exc
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise MissingCredential("OPENAI_API_KEY not set")
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        kwargs = {"api_key": key}
        if os.getenv("OPENAI_BASE_URL"):
            kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")
        self._client = OpenAI(**kwargs)  # no network at construction

    def chat(self, messages, tools=None, *, force_tool=None) -> ChatResponse:
        kwargs = {"model": self.model, "messages": to_openai_messages(messages)}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice_for(force_tool)
        resp = self._client.chat.completions.create(**kwargs)
        return parse_openai_response(resp.choices[0].message)
