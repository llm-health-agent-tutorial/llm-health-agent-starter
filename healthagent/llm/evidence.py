"""Two typed predicates that decide whether the agent actually has evidence.

Used by BOTH ScriptedBackend (so it never templates a finding from failed/missing evidence)
and grounding.check (so the grounded flag is honest). This is the safety crux: an incomplete
participant edit must yield an ungrounded "couldn't gather evidence" answer, never a polished
but false health explanation.
"""
from __future__ import annotations

from .schemas import OBSERVATION_NOT_ATTACHED, TODO_SENTINEL, ToolResult

_EMPTY = (None, {}, [], "")


def is_failed_tool_result(result: ToolResult) -> bool:
    """True if a ToolResult carries no usable evidence (error, TODO stub, or empty value)."""
    if not isinstance(result, ToolResult):
        return True
    if result.error:
        return True
    if TODO_SENTINEL.lower() in (result.summary or "").lower():
        return True
    if result.kind != "image" and result.value in _EMPTY:
        return True
    return False


def is_failed_observation_message(message: dict) -> bool:
    """True if a serialized tool-role message carries no usable observation."""
    if not isinstance(message, dict) or message.get("role") != "tool":
        return False  # not an observation message at all
    content = (message.get("content") or "").strip()
    if not content:
        return True
    low = content.lower()
    return (
        OBSERVATION_NOT_ATTACHED.lower() in low
        or TODO_SENTINEL.lower() in low
        or low.startswith("tool error")
    )
