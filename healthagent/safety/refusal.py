"""Prebuilt medical-advice classifier + refusal template.

Shipped complete so Module-4 TODO-3 is a single edit (adding the [REFUSAL] clause to the
system prompt) rather than building a classifier. The classifier is intentionally simple and
high-recall; Module 5 discusses its limits.
"""
from __future__ import annotations

import re

REFUSAL_TEMPLATE = (
    "I can't provide medical advice, diagnoses, or treatment or medication recommendations. "
    "This tool explores synthetic, exploratory sensing data only. For anything health-related, "
    "please consult a qualified clinician. I can still help you understand the patterns in the data."
)

# High-recall patterns for medical-advice / diagnostic / treatment requests.
_PATTERNS = [
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
]
_RX = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def is_medical_advice(question: str) -> bool:
    q = question or ""
    return any(rx.search(q) for rx in _RX)
