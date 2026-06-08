"""LLMClient seam + get_client() factory.

In Milestone 1 the seam (chat + serialize_assistant + serialize_tool_result) is implemented by
ScriptedBackend, using a neutral message shape. Live Gemini/OpenAI/Ollama adapters arrive in
Milestone 2 and conform to the same seam (with provider message-shape contract tests); until
then get_client() falls back to ScriptedBackend with a loud banner, so the offline tier is the
always-available floor.
"""
from __future__ import annotations

from .. import config
from .schemas import ChatResponse, ToolResult


def system(text: str) -> dict:
    return {"role": "system", "content": text}


def user(text: str) -> dict:
    return {"role": "user", "content": text}


class LLMClient:
    """Base seam. Neutral message shapes; live adapters override the serialize_* methods."""

    provider: str = "base"

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        raise NotImplementedError

    def serialize_assistant(self, resp: ChatResponse) -> dict:
        return {
            "role": "assistant",
            "content": resp.text or "",
            "tool_calls": [{"id": tc.id, "name": tc.name, "args": tc.args} for tc in resp.tool_calls],
        }

    def serialize_tool_result(self, call_id: str, result: ToolResult) -> dict:
        return {"role": "tool", "tool_call_id": call_id, "name": getattr(result, "name", ""),
                "content": result.summary}


def _banner(active: str, reason: str) -> None:
    line = "─" * 64
    print(f"┌{line}\n│ healthagent backend: {active.upper()}  ({reason})\n└{line}")


def get_client(provider: str = "auto", quiet: bool = False):
    """Return an LLMClient. ``auto`` uses config.resolve_backend(); live adapters fall back to
    ScriptedBackend in Milestone 1."""
    from .scripted_client import ScriptedBackend

    desired = config.resolve_backend() if provider == "auto" else provider.lower()

    if desired == "scripted":
        if not quiet:
            _banner("scripted", "deterministic teaching backend; no API key or network needed")
        return ScriptedBackend()

    # Milestone 2: try the live adapter; fall back to scripted if not yet available.
    try:
        if desired == "openai":
            from .openai_client import OpenAIBackend

            client = OpenAIBackend()
        elif desired == "gemini":
            from .gemini_client import GeminiBackend

            client = GeminiBackend()
        elif desired == "ollama":
            from .ollama_client import OllamaBackend

            client = OllamaBackend()
        else:
            raise ImportError(f"unknown backend '{desired}'")
        if not quiet:
            _banner(desired, "live model")
        return client
    except Exception as exc:  # not implemented yet (M1) or misconfigured
        if not quiet:
            _banner("scripted", f"'{desired}' unavailable ({type(exc).__name__}); using the offline floor")
        return ScriptedBackend()
