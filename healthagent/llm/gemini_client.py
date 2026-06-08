"""Gemini adapter (unified google-genai). The module imports without the SDK; `google.genai.types`
is imported lazily inside the helpers/constructor.

History reconstruction is a specified state machine (`to_gemini_contents`): each assistant turn
becomes a `model` Content reusing its ORIGINAL parts (preserving `function_call.id` and, when
present, `thought_signature`); all consecutive tool results for that turn are grouped into ONE
`user` Content of `function_response` parts echoing the matching name (+ id when supported).
`force_tool` maps to function-calling mode ANY with `allowed_function_names`.
"""
from __future__ import annotations

import os

from .client import LLMClient
from .errors import MissingCredential, MissingSDK
from .schemas import ChatResponse, ToolCall

DEFAULT_MODEL = "gemini-2.5-flash"  # override via GEMINI_MODEL


def _set_if(obj_kwargs: dict, key: str, value) -> None:
    if value is not None:
        obj_kwargs[key] = value


def to_gemini_contents(messages: list[dict]):
    """Neutral messages -> (system_instruction, [Content]). Lazy types import."""
    from google.genai import types as T

    system_instruction = None
    contents = []
    pending_tool_parts = []  # group consecutive tool results into one user Content

    def flush_tools():
        nonlocal pending_tool_parts
        if pending_tool_parts:
            contents.append(T.Content(role="user", parts=pending_tool_parts))
            pending_tool_parts = []

    for m in messages:
        role = m.get("role")
        if role == "system":
            system_instruction = (system_instruction + "\n" if system_instruction else "") + m.get("content", "")
            continue
        if role == "tool":
            resp = m.get("content", "")
            fr_kwargs = {"name": m.get("name", ""), "response": {"result": resp}}
            _set_if(fr_kwargs, "id", m.get("tool_call_id"))
            pending_tool_parts.append(T.Part(function_response=_make(T.FunctionResponse, fr_kwargs)))
            continue
        flush_tools()
        if role == "assistant":
            raw = m.get("_provider")
            if raw is not None:  # reuse original model Content (preserves thought_signature + ids)
                contents.append(raw)
                continue
            parts = []
            if m.get("content"):
                parts.append(T.Part(text=m["content"]))
            for tc in m.get("tool_calls", []):
                fc_kwargs = {"name": tc["name"], "args": tc.get("args", {})}
                _set_if(fc_kwargs, "id", tc.get("id"))
                parts.append(T.Part(function_call=_make(T.FunctionCall, fc_kwargs)))
            contents.append(T.Content(role="model", parts=parts or [T.Part(text="")]))
        else:  # user
            contents.append(T.Content(role="user", parts=[T.Part(text=m.get("content", ""))]))
    flush_tools()
    return system_instruction, contents


def _make(cls, kwargs):
    """Construct a types object, dropping kwargs the installed SDK version doesn't accept (e.g. id)."""
    try:
        return cls(**kwargs)
    except TypeError:
        kwargs.pop("id", None)
        return cls(**kwargs)


def to_gemini_tools(tool_schemas):
    from google.genai import types as T

    if not tool_schemas:
        return None
    decls = [T.FunctionDeclaration(name=s["name"], description=s["description"],
                                   parameters=_clean_params(s["parameters"])) for s in tool_schemas]
    return [T.Tool(function_declarations=decls)]


_JSON_TO_GEMINI_TYPE = {
    "object": "OBJECT", "string": "STRING", "integer": "INTEGER",
    "number": "NUMBER", "boolean": "BOOLEAN", "array": "ARRAY",
}


def _clean_params(params: dict) -> dict:
    """JSON-schema -> Gemini Schema dict: uppercase TYPE enums, drop unsupported keys
    (additionalProperties/default)."""
    props = {}
    for name, p in params.get("properties", {}).items():
        sp = {"type": _JSON_TO_GEMINI_TYPE.get(p.get("type", "string"), "STRING")}
        if "description" in p:
            sp["description"] = p["description"]
        if "enum" in p:
            sp["enum"] = p["enum"]
        props[name] = sp
    return {"type": "OBJECT", "properties": props, "required": params.get("required", [])}


def tool_config_for(force_tool: str | None):
    from google.genai import types as T

    if not force_tool:
        return None
    cfg = T.FunctionCallingConfig(mode="ANY", allowed_function_names=[force_tool])
    return T.ToolConfig(function_calling_config=cfg)


def parse_gemini_response(response) -> ChatResponse:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ChatResponse(text="", tool_calls=[], provider_raw=response)
    content = candidates[0].content
    text_parts, tool_calls = [], []
    for i, part in enumerate(getattr(content, "parts", None) or []):
        fc = getattr(part, "function_call", None)
        if fc is not None:
            name = getattr(fc, "name", "") or ""
            args = getattr(fc, "args", None) or {}
            cid = getattr(fc, "id", None) or f"call_{i}_{name}"
            tool_calls.append(ToolCall(id=cid, name=name, args=dict(args)))
        elif getattr(part, "text", None):
            text_parts.append(part.text)
    return ChatResponse(text="".join(text_parts), tool_calls=tool_calls, provider_raw=content)


class GeminiBackend(LLMClient):
    provider = "gemini"
    supports_force_tool = True

    def __init__(self) -> None:
        try:
            from google import genai  # noqa: F401  (lazy)
        except ImportError as exc:
            raise MissingSDK("google-genai SDK not installed — run `make live-install`") from exc
        from .. import config
        key = config.gemini_api_key()  # GEMINI_API_KEY or GOOGLE_API_KEY (SDK-native)
        if not key:
            raise MissingCredential("GEMINI_API_KEY (or GOOGLE_API_KEY) not set")
        from google import genai
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._client = genai.Client(api_key=key)  # no network at construction

    def serialize_assistant(self, resp: ChatResponse) -> dict:
        d = super().serialize_assistant(resp)
        d["_provider"] = resp.provider_raw  # raw model Content -> faithful history reconstruction
        return d

    def chat(self, messages, tools=None, *, force_tool=None) -> ChatResponse:
        from google.genai import types as T

        system_instruction, contents = to_gemini_contents(messages)
        cfg_kwargs = {}
        _set_if(cfg_kwargs, "system_instruction", system_instruction)
        gem_tools = to_gemini_tools(tools)
        if gem_tools:
            cfg_kwargs["tools"] = gem_tools
            tc = tool_config_for(force_tool)
            if tc is not None:
                cfg_kwargs["tool_config"] = tc
        config = T.GenerateContentConfig(**cfg_kwargs) if cfg_kwargs else None
        resp = self._client.models.generate_content(model=self.model, contents=contents, config=config)
        return parse_gemini_response(resp)
