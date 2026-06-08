"""grounding.check — is the answer actually supported by retrieved evidence?

Prebuilt (Module-4 TODO-3 only edits the system prompt, not this). Evidence-aware: an answer
is grounded only if at least one tool returned usable evidence AND the answer cites a concrete
number and a data/metric term. This is what flips the AgentAnswer.grounded flag; it never
blocks the loop.
"""
from __future__ import annotations

import re

from ..llm.evidence import is_failed_tool_result
from ..llm.schemas import ToolResult

_TERMS = ("sleep", "screen", "steps", "activity", "heart", "hrv", "mood", "stress",
          "energy", "goal", "minutes", "hours", "bpm")


def check(answer_text: str, results: list[ToolResult]) -> bool:
    if not any(not is_failed_tool_result(r) for r in (results or [])):
        return False
    text = (answer_text or "").lower()
    has_number = bool(re.search(r"\d", text))
    has_term = any(t in text for t in _TERMS)
    return has_number and has_term
