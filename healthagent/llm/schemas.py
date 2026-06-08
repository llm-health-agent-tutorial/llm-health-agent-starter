"""Provider-agnostic dataclasses passed around the agent loop."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Sentinel used by the default (unfilled) M4 observe(): a valid tool-result message whose
# summary is this string. is_failed_observation_message() treats it as failed evidence so a
# blank TODO-2 yields an ungrounded answer rather than a confident-but-false one.
OBSERVATION_NOT_ATTACHED = "OBSERVATION_NOT_ATTACHED"

# Marker the stub tool bodies return until a participant implements them.
TODO_SENTINEL = "TODO not implemented"

# Explicit system-prompt markers (TODO-3). Parsed exactly (never as loose substrings) so a
# participant adding these clauses produces a visible behavior change even on ScriptedBackend.
GROUNDING_MARKER = "[GROUNDING]"
REFUSAL_MARKER = "[REFUSAL]"


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]
    # Set by a provider parser when the model emitted invalid JSON arguments (model-bad input,
    # not an adapter bug). The loop short-circuits on this and never executes the tool.
    parse_error: str | None = None


@dataclass
class ChatResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_raw: Any = None  # original assistant message/parts; enables faithful reconstruction


@dataclass
class ToolResult:
    kind: str            # 'text' | 'table' | 'image'
    summary: str         # the short text the LLM sees
    value: Any = None    # full payload (dict / list / image path)
    error: bool = False  # True if the tool failed
    dropped_args: list[str] = field(default_factory=list)  # unknown kwargs stripped at the boundary


@dataclass
class EvidenceRecord:
    """A tool call paired with its result, so grounding and the completion check know which tool
    (and which args) produced each summary."""
    tool_call: ToolCall
    result: ToolResult


@dataclass
class AgentAnswer:
    text: str
    images: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    grounded: bool = False
