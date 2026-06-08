"""grounding.check — is the answer actually supported by retrieved evidence?

Prebuilt (Module-4 TODO-3 edits only the prompt, not this). The loop gates the public flag on the
`[GROUNDING]` marker (`grounded = (GROUNDING_MARKER in prompt) and grounding.check(...)`), so adding
the clause in TODO-3 is what makes the flag flip. The check itself is evidence-based: a number in
the answer must match (normalized) a number in a non-failed tool summary.

Matching rules (avoid false-pass AND false-fail):
- magnitude match within tolerance (so "dropped 24%" matches a "-23.9%" summary);
- a LITERAL signed contradiction is rejected (answer "+24" vs summary "-24");
- window/sample/date numbers are ignored ("7 days", "n=28", "2026-05-30") so they can't ground.
Direction-word correctness (e.g. "increased 24%" vs a -24% summary) is asserted test-side in live
smoke, which knows the expected direction; the generic flag stays robust to phrasing.
"""
from __future__ import annotations

import re

from ..llm.evidence import is_failed_tool_result
from ..llm.schemas import EvidenceRecord

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_WINDOW = re.compile(r"(\b\d+(?:\.\d+)?\s*(?:day|days|night|nights)\b)|(\bn\s*=\s*\d+\b)", re.IGNORECASE)
_NUM = re.compile(r"([+-]?)(\d+(?:\.\d+)?)")


def _numbers(text: str) -> list[tuple[float, int]]:
    """Return (magnitude, sign) pairs; sign in {-1, 0, +1} (0 = no explicit sign). Date and
    window/sample numbers are stripped first so they can't be used as evidence."""
    text = _DATE.sub(" ", text or "")
    text = _WINDOW.sub(" ", text)
    out: list[tuple[float, int]] = []
    for m in _NUM.finditer(text):
        s, n = m.group(1), m.group(2)
        sign = -1 if s == "-" else (1 if s == "+" else 0)
        out.append((float(n), sign))
    return out


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.5, 0.02 * max(abs(a), abs(b), 1.0))


def check(answer_text: str, evidence: list[EvidenceRecord]) -> bool:
    usable = [e for e in (evidence or []) if not is_failed_tool_result(e.result)]
    if not usable:
        return False
    answer_nums = _numbers(answer_text)
    if not answer_nums:
        return False
    summary_nums: list[tuple[float, int]] = []
    for e in usable:
        summary_nums.extend(_numbers(e.result.summary or ""))
    for a_mag, a_sign in answer_nums:
        for s_mag, s_sign in summary_nums:
            if _close(a_mag, s_mag):
                if a_sign and s_sign and a_sign != s_sign:
                    continue  # literal signed contradiction — not a match
                return True
    return False
