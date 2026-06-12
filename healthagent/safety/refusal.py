"""Prebuilt safety classifier + deterministic response templates.

Shipped complete so Module-4 TODO-3 is a single edit (adding the [REFUSAL] clause to the system
prompt) rather than building a classifier. The classifier is intentionally simple and high-recall;
Module 5 discusses its limits.

Safety handling is NOT one flat "refuse" bucket — it is three deterministic responses, picked by
acuity, and fired by the loop BEFORE the model runs (so behavior is identical on every backend):
  - crisis     : self-harm / suicidal ideation                 -> crisis-support resources
  - emergency  : acute physical symptoms (chest pain, ...)      -> urge emergency care
  - medical    : diagnosis / dosage / medication / disordered-eating / authority-jailbreak -> refuse, see a clinician
"""
from __future__ import annotations

import re

REFUSAL_TEMPLATE = (
    "I can't provide medical advice, diagnoses, or treatment or medication recommendations. "
    "This tool explores synthetic, exploratory sensing data only. For anything health-related, "
    "please consult a qualified clinician. I can still help you understand the patterns in the data."
)
EMERGENCY_TEMPLATE = (
    "This could be a medical emergency, and I can't assess symptoms. Please contact your local "
    "emergency number (e.g. 911 / 112 / 120) or get to urgent care right now. I can look at the "
    "patterns in your data with you afterward — but please get help first."
)
CRISIS_TEMPLATE = (
    "I'm really sorry you're feeling this way, and I'm not able to help with this safely here. "
    "Please reach out right now to a trained person — for example call or text 988 (US Suicide & "
    "Crisis Lifeline), or your local crisis line or emergency number. You deserve real support."
)

# High-recall patterns, checked most-acute first (crisis -> emergency -> medical).
_CRISIS = [
    r"\b(hurt|harm|kill)(ing)? myself\b",
    r"\bsuicid",
    r"\bself[-\s]?harm\b",
    r"\b(end my life|want to die|don'?t want to (live|be here))\b",
]
_EMERGENCY = [
    r"\bchest pain\b",
    r"\bshortness of breath\b",
    r"\b(can'?t|cannot|trouble) breath(e|ing)\b",
    r"\b(passed out|fainted|unconscious|heart attack|stroke)\b",
]
_MEDICAL = [
    r"\bdiagnos(e|is|ed)\b",
    r"\bdo i have\b",
    r"\bis (this|it) (cancer|covid|diabetes|depression|a tumou?r|dangerous|serious|normal)\b",
    r"\bshould i (take|stop|start|increase|lower)\b",
    r"\b(medication|medicine|drug|dose|dosage|pill|prescription|antidepressant|melatonin|ambien)\b",
    r"\bhow much .* should i (take|use)\b",
    r"\bis it safe to (take|stop|mix)\b",
    r"\btreat(ment|ed)?\b.*\b(my|this)\b",
    r"\bsee a doctor\b",
    r"\bam i (sick|depressed|dying)\b",
    # disordered-eating / unsafe weight loss
    r"\blose weight\b",
    r"\bhow (little|much) (can|should) i eat\b",
    r"\b(starve|stop eating)\b",
    r"\beating disorder\b",
]
_RX = [(kind, [re.compile(p, re.IGNORECASE) for p in pats])
       for kind, pats in (("crisis", _CRISIS), ("emergency", _EMERGENCY), ("medical", _MEDICAL))]
_TEMPLATES = {"crisis": CRISIS_TEMPLATE, "emergency": EMERGENCY_TEMPLATE, "medical": REFUSAL_TEMPLATE}


def classify_safety(question: str) -> str | None:
    """Return 'crisis' | 'emergency' | 'medical' for a request that needs deterministic safety
    handling, else None. The most-acute matching category wins."""
    q = question or ""
    for kind, rxs in _RX:
        if any(rx.search(q) for rx in rxs):
            return kind
    return None


def safety_response(question: str) -> tuple[str, str] | None:
    """(kind, message) for a request that needs deterministic safety handling, else None."""
    kind = classify_safety(question)
    return (kind, _TEMPLATES[kind]) if kind else None


def is_medical_advice(question: str) -> bool:
    """Back-compat: any request that triggers deterministic safety handling."""
    return classify_safety(question) is not None
