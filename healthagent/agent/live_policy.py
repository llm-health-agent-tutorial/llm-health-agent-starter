"""Read-only workshop plumbing that makes LIVE tool-use reliable, wired by `agent_config.run()`
in one line so the participant file keeps exactly three TODO blanks.

- `TOOL_POLICY`: tool-selection/order guidance only (NOT grounding — that stays the participant's
  `[GROUNDING]` clause, so TODO-3 still visibly matters).
- `completion_check`: SIGNATURE-level requirements (tool name + metric + date window), partitioned
  into `missing` (registered but not satisfied -> nudgeable) vs `unavailable` (not registered ->
  fail safe). Unrecognized intents return NO requirements (never gated).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .. import config
from ..catalog import CATALOG, UnknownMetric
from ..llm.evidence import is_failed_tool_result
from ..llm.schemas import EvidenceRecord

_R0, _R1 = config.recent_window()
_SLEEP_KW = ("sleep", "slept", "sleeping", "tired", "rest", "insomnia", "bed", "fatigue")
_ACTIVITY_KW = ("activity", "active", "steps", "step ", "goal", "exercise", "walk", "move", "fitness")


@dataclass
class EvidenceRequirement:
    label: str
    tool_name: str
    args_match: Callable[[dict], bool]
    nudge_text: str


@dataclass
class CompletionCheckResult:
    missing: list[EvidenceRequirement] = field(default_factory=list)       # registered, not satisfied
    unavailable: list[EvidenceRequirement] = field(default_factory=list)   # tool not registered


def _metric_is(args: dict, target: str) -> bool:
    try:
        return CATALOG.resolve(args.get("metric", "")) == target
    except UnknownMetric:
        return False


def _recent_window(args: dict) -> bool:
    return args.get("start_date") == _R0 and args.get("end_date") == _R1


def _detect(args: dict, target: str) -> bool:
    return (_metric_is(args, target)
            and int(args.get("recent_days", 7)) == 7
            and int(args.get("baseline_days", 21)) == 21)


SLEEP_REQS = [
    EvidenceRequirement("screen retrieval", "query_screen_time", _recent_window,
                        "call query_screen_time for the recent week (the dataset's final 7 days)"),
    EvidenceRequirement("sleep retrieval", "query_sleep", _recent_window,
                        "call query_sleep for the recent week"),
    EvidenceRequirement("night-screen change", "detect_change",
                        lambda a: _detect(a, "night_screen_minutes"),
                        "call detect_change with metric=night_screen_minutes"),
    EvidenceRequirement("sleep change", "detect_change",
                        lambda a: _detect(a, "total_sleep_hours"),
                        "call detect_change with metric=total_sleep_hours"),
    EvidenceRequirement("night-screen plot", "plot_timeseries",
                        lambda a: _recent_window(a) and _metric_is(a, "night_screen_minutes"),
                        "call plot_timeseries with metric=night_screen_minutes for the recent week"),
]
ACTIVITY_REQS = [
    EvidenceRequirement("activity vs goal", "compare_window", lambda a: True, "call compare_window"),
]


def requirements_for(question: str) -> list[EvidenceRequirement]:
    q = (question or "").lower()
    if any(k in q for k in _SLEEP_KW):
        return SLEEP_REQS
    if any(k in q for k in _ACTIVITY_KW):
        return ACTIVITY_REQS
    return []  # unrecognized intent -> no requirements -> never completion-gated


def completion_check(question: str, evidence: list[EvidenceRecord], available_tools) -> CompletionCheckResult:
    avail = set(available_tools)
    res = CompletionCheckResult()
    for req in requirements_for(question):
        satisfied = any(
            ev.tool_call.name == req.tool_name
            and not is_failed_tool_result(ev.result)
            and req.args_match(ev.tool_call.args)
            for ev in evidence
        )
        if satisfied:
            continue
        (res.missing if req.tool_name in avail else res.unavailable).append(req)
    return res


TOOL_POLICY = (
    "\n\nTool use: to explain a change in sleep, call query_screen_time and query_sleep for the recent "
    "week, quantify both night_screen_minutes and total_sleep_hours with detect_change, and render "
    "plot_timeseries for night_screen_minutes before concluding. For an activity-vs-goal question, call "
    "compare_window. Use ISO YYYY-MM-DD dates; 'this week' means the dataset's final 7 days."
)


def augment(system_prompt: str) -> tuple[str, Callable]:
    """Return (policy-augmented prompt, completion_check). One-line plumbing for agent_config.run()."""
    return system_prompt + TOOL_POLICY, completion_check
