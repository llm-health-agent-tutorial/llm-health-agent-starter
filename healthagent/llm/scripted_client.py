"""ScriptedBackend — a deterministic, rule-based teaching backend (NOT a real LLM, NOT a
transcript replayer).

It implements the same LLMClient seam as the live adapters, and genuinely drives the loop:
- READS the registered tools each turn (so TODO-1 registration has a visible effect),
- CONSUMES the observations appended after each tool call (so TODO-2 has a visible effect:
  with the default placeholder observe, every observation is failed evidence -> ungrounded),
- honors the explicit [GROUNDING]/[REFUSAL] markers in the system prompt (so TODO-3 has a
  visible effect), parsed exactly,
- templates its final answer over the REAL numbers in the tool summaries (never hardcoded,
  never keyed on participant tool output), and never fabricates a finding from failed/missing
  evidence (the safety crux).
"""
from __future__ import annotations

from .. import config
from ..safety.refusal import REFUSAL_TEMPLATE, is_medical_advice
from .client import LLMClient
from .evidence import is_failed_observation_message
from .schemas import GROUNDING_MARKER, REFUSAL_MARKER, ChatResponse, ToolCall

_ACTIVITY_KW = ("activity", "active", "steps", "step ", "goal", "exercise", "walk", "move", "fitness")
_SLEEP_KW = ("sleep", "slept", "sleeping", "tired", "rest", "insomnia", "bed", "fatigue")


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _system_text(messages: list[dict]) -> str:
    return " ".join(m.get("content", "") for m in messages if m.get("role") == "system")


def _executed_signatures(messages: list[dict]) -> set:
    """(tool_name, discriminator) pairs already requested, read from assistant tool_calls."""
    sigs = set()
    for m in messages:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls", []):
                args = tc.get("args", {})
                disc = args.get("metric") or args.get("metric_a") or ""
                sigs.add((tc.get("name"), disc))
    return sigs


def _observations(messages: list[dict]) -> list[dict]:
    """Map each tool-role message back to its (name, args) via tool_call_id; flag failed ones."""
    id_to_call = {}
    for m in messages:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls", []):
                id_to_call[tc.get("id")] = (tc.get("name"), tc.get("args", {}))
    obs = []
    for m in messages:
        if m.get("role") == "tool":
            name, args = id_to_call.get(m.get("tool_call_id"), (m.get("name", ""), {}))
            obs.append({
                "name": name,
                "args": args,
                "content": m.get("content", ""),
                "failed": is_failed_observation_message(m),
            })
    return obs


def _plan(question: str, available: set) -> list[tuple[str, dict]]:
    q = question.lower()
    uid = _user_id_from(question)
    r_start, r_end = config.recent_window()
    activity = any(k in q for k in _ACTIVITY_KW)
    sleep = any(k in q for k in _SLEEP_KW)

    steps: list[tuple[str, dict]] = []
    if sleep:
        steps += [
            ("query_screen_time", {"user_id": uid, "start_date": r_start, "end_date": r_end}),
            ("query_sleep", {"user_id": uid, "start_date": r_start, "end_date": r_end}),
            ("detect_change", {"user_id": uid, "metric": "night_screen_minutes"}),
            ("detect_change", {"user_id": uid, "metric": "total_sleep_hours"}),
            ("correlate_metrics", {"user_id": uid, "metric_a": "total_sleep_hours",
                                   "metric_b": "night_screen_minutes"}),
            ("plot_timeseries", {"user_id": uid, "metric": "night_screen_minutes",
                                 "start_date": r_start, "end_date": r_end}),
        ]
    if activity or (not sleep and not activity):
        steps += [("compare_window", {"user_id": uid})]
    # keep only steps whose tool is actually registered
    return [(name, args) for (name, args) in steps if name in available]


def _user_id_from(question: str) -> str:
    import re

    m = re.search(r"user_id\s*=\s*([A-Za-z0-9_]+)", question)
    return m.group(1) if m else config.DEMO_USER


def _num_from(content: str, *keys: str) -> str:
    """Return the tool summary string (which already contains the real numbers) for templating."""
    return content.strip().rstrip(".")


def _render(question: str, obs: list[dict], grounding_on: bool) -> str:
    usable = [o for o in obs if not o["failed"]]
    q = question.lower()
    sleep = any(k in q for k in _SLEEP_KW)

    if not usable:
        return ("I could not gather enough evidence to answer that. The tools I tried did not "
                "return usable data (they may not be implemented or wired up yet).")

    def find(name, kw=None):
        for o in usable:
            if o["name"] == name and (kw is None or kw in o["content"].lower()):
                return o["content"].rstrip(".")
        return None

    if sleep:
        # Require usable evidence from EVERY assigned tool before making any attribution.
        # A single unfilled/broken tool (its observation is failed -> not in `usable`) leaves one
        # of these None, so the agent fails safe instead of templating a confident answer from
        # whichever tool happened to work. This is the safety crux.
        required = {
            "query_screen_time": find("query_screen_time"),
            "query_sleep": find("query_sleep"),
            "detect_change(night_screen)": find("detect_change", "night_screen"),
            "detect_change(total_sleep)": find("detect_change", "total_sleep"),
            "plot_timeseries": find("plot_timeseries"),  # the demo must render a plot (TODO-1 list)
        }
        missing = [name for name, got in required.items() if not got]
        if missing:
            return ("I could not gather enough evidence to answer that confidently. "
                    "Some required tools did not return usable data (they may not be implemented "
                    "or wired up yet), so I won't guess at a cause.")
        dc_night = required["detect_change(night_screen)"]
        dc_sleep = required["detect_change(total_sleep)"]
        if grounding_on:
            parts = [
                f"In the final week of the dataset your sleep declined: {dc_sleep}.",
                f"The most plausible contributor in this synthetic dataset is night-time "
                f"screen use: {dc_night}.",
            ]
            corr = find("correlate_metrics")
            if corr:
                parts.append(f"They move together ({corr}).")
            if any(o["name"] == "plot_timeseries" for o in usable):
                parts.append("See the attached night-screen-time plot.")
            parts.append("Note: this is an association in synthetic data, not proof of cause; "
                         "other factors could contribute.")
            return " ".join(parts)
        # grounding clause not added yet (TODO-3): a vaguer answer with no cited figures
        return ("Your sleep looks worse over the recent window and your night-time screen use "
                "looks higher. They appear related, but I'm not citing specifics here.")

    # activity / general
    cw = find("compare_window")
    if cw:
        if grounding_on:
            return f"{cw}. (Synthetic data; for context only.)"
        return "Your recent activity is below your step goal; check the steps trend for details."
    return "; ".join(o["content"].rstrip(".") for o in usable[:2]) + "."


class ScriptedBackend(LLMClient):
    provider = "scripted"

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResponse:
        tools = tools or []
        available = {t.get("name") for t in tools}
        question = _last_user_text(messages)
        sys = _system_text(messages)
        grounding_on = GROUNDING_MARKER in sys
        refusal_on = REFUSAL_MARKER in sys

        # Safety: refuse medical-advice probes only once the [REFUSAL] clause is present.
        if refusal_on and is_medical_advice(question):
            return ChatResponse(text=REFUSAL_TEMPLATE, tool_calls=[], provider_raw={"scripted": "refusal"})

        plan = _plan(question, available)
        executed = _executed_signatures(messages)
        for name, args in plan:
            disc = args.get("metric") or args.get("metric_a") or ""
            if (name, disc) not in executed:
                call_id = f"call_{len(executed) + 1}_{name}"
                return ChatResponse(text="", tool_calls=[ToolCall(call_id, name, args)],
                                    provider_raw={"scripted": "tool_call"})

        # Plan complete (or empty) -> final answer templated over real observations.
        obs = _observations(messages)
        text = _render(question, obs, grounding_on)
        return ChatResponse(text=text, tool_calls=[], provider_raw={"scripted": "final"})
