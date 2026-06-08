"""LLMClient seam + get_client() factory.

The neutral message shape is shared by ScriptedBackend and the loop. Live adapters (M2) override
chat()/serialize_* to round-trip provider metadata. get_client() falls back to ScriptedBackend
ONLY on typed availability errors (MissingSDK/MissingCredential/ModelUnavailable); unexpected
adapter bugs propagate. Adapter modules import without their SDK (the SDK import is lazy inside the
constructor/available()), so importing them here never raises ModuleNotFoundError.
"""
from __future__ import annotations

from .. import config
from .errors import BackendUnavailable
from .schemas import ChatResponse, ToolCall, ToolResult


def system(text: str) -> dict:
    return {"role": "system", "content": text}


def user(text: str) -> dict:
    return {"role": "user", "content": text}


class LLMClient:
    """Base seam. Neutral message shapes; live adapters override chat()/serialize_* as needed.

    ``fallback_reason`` is set by get_client() on the returned client when a live backend was
    requested but unavailable (so ha-check can explain why it landed on scripted)."""

    provider: str = "base"
    fallback_reason: str | None = None
    supports_force_tool: bool = False

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             *, force_tool: str | None = None) -> ChatResponse:
        raise NotImplementedError

    def serialize_assistant(self, resp: ChatResponse) -> dict:
        return {
            "role": "assistant",
            "content": resp.text or "",
            "tool_calls": [{"id": tc.id, "name": tc.name, "args": tc.args} for tc in resp.tool_calls],
        }

    def serialize_tool_result(self, tool_call: ToolCall, result: ToolResult) -> dict:
        # Neutral tool message carrying BOTH id and name (Gemini/Ollama need the name).
        return {"role": "tool", "tool_call_id": tool_call.id, "name": tool_call.name,
                "content": result.summary}


def _banner(active: str, reason: str) -> None:
    line = "─" * 64
    print(f"┌{line}\n│ healthagent backend: {active.upper()}  ({reason})\n└{line}")


def get_client(provider: str = "auto", *, allow_fallback: bool = True, quiet: bool = False):
    """Return an LLMClient.

    ``auto`` uses config.resolve_backend(). With ``allow_fallback`` (the workshop default), a live
    backend that is unavailable for a *typed* reason falls back to ScriptedBackend (recording
    ``fallback_reason``); unexpected errors always propagate. ``allow_fallback=False`` (tests) raises
    the typed error so a broken adapter can't masquerade as scripted.
    """
    from .scripted_client import ScriptedBackend

    desired = config.resolve_backend() if provider == "auto" else provider.lower()

    if desired == "scripted":
        if not quiet:
            _banner("scripted", "deterministic teaching backend; no API key or network needed")
        return ScriptedBackend()

    ctors = {
        "openai": lambda: __import__("healthagent.llm.openai_client", fromlist=["OpenAIBackend"]).OpenAIBackend(),
        "gemini": lambda: __import__("healthagent.llm.gemini_client", fromlist=["GeminiBackend"]).GeminiBackend(),
        "ollama": lambda: __import__("healthagent.llm.ollama_client", fromlist=["OllamaBackend"]).OllamaBackend(),
    }
    if desired not in ctors:
        if allow_fallback:
            fb = ScriptedBackend()
            fb.fallback_reason = f"unknown backend '{desired}'"
            if not quiet:
                _banner("scripted", fb.fallback_reason)
            return fb
        raise BackendUnavailable(f"unknown backend '{desired}'")

    try:
        client = ctors[desired]()  # constructor does the lazy SDK import + availability checks
    except BackendUnavailable as exc:
        if not allow_fallback:
            raise
        fb = ScriptedBackend()
        fb.fallback_reason = f"{desired} unavailable: {type(exc).__name__}: {exc}"
        if not quiet:
            _banner("scripted", f"'{desired}' unavailable ({type(exc).__name__}); using the offline floor")
        return fb
    # NOTE: any non-typed exception (a real adapter bug) propagates — never silently masked.
    if not quiet:
        _banner(desired, "live model")
    return client
