"""The agent loop — single, canonical. The readable core (`run_agent`) is the five steps
participants study in Module 4: PLAN -> SELECT -> EXECUTE -> OBSERVE -> RESPOND. Live-robustness
concerns (refusal preflight, completion-check nudge + force_tool, hard fail-safe) are single
named helper calls defined BELOW the core, so the M4 "read the loop" cell stays legible.

The three workshop pieces are INJECTED: which tools are in ``registry`` (TODO-1), the ``observe``
callable (TODO-2), and the ``system_prompt`` (TODO-3). An optional ``completion_check`` (read-only
workshop plumbing) makes live tool-use reliable; it is None for the generic/unknown case.
"""
from __future__ import annotations

from typing import Callable

from . import grounding
from .. import config
from ..llm.client import LLMClient, system, user
from ..llm.schemas import GROUNDING_MARKER, AgentAnswer, EvidenceRecord, ToolResult
from ..safety.refusal import safety_response

Observe = Callable[[LLMClient, object, ToolResult], dict]
MAX_NUDGES = 2
INSUFFICIENT_EVIDENCE = (
    "I could not gather enough evidence to answer that confidently. Some required tools did not "
    "return usable data (they may not be implemented or wired up yet), so I won't guess at a cause."
)


def run_agent(
    question: str,
    *,
    client: LLMClient,
    registry,
    observe: Observe,
    system_prompt: str,
    user_id: str = "u01",
    max_steps: int = 6,
    completion_check: Callable | None = None,
    verbose: bool = False,
) -> AgentAnswer:
    images: list[str] = []
    trace: list[dict] = []
    evidence: list[EvidenceRecord] = []

    refusal = _refusal_preflight(question, system_prompt, trace)        # deterministic, loop-owned
    if refusal is not None:
        return refusal

    messages = [
        system(system_prompt),
        user(f"[user_id={user_id}] [dataset_today={config.dataset_today()}] {question}"),
    ]
    grounding_on = GROUNDING_MARKER in system_prompt
    nudges_used = 0
    force_tool: str | None = None

    for step in range(max_steps):
        resp = client.chat(messages, tools=registry.schemas(client.provider), force_tool=force_tool)  # PLAN + SELECT
        force_tool = None

        if not resp.tool_calls:                                         # RESPOND (gated)
            verdict = _check_completion(question, evidence, registry, completion_check, nudges_used)
            if verdict["action"] == "nudge":
                nudges_used += 1
                force_tool = verdict["force_tool"]
                trace.append({"event": "nudge", "missing": verdict["missing"], "force_tool": force_tool})
                messages.append(user(verdict["nudge_text"]))
                continue
            if verdict["action"] == "fail_safe":
                trace.append({"event": "fail_safe", "reason": verdict["reason"],
                              "missing": verdict["missing"], "unavailable": verdict["unavailable"]})
                return AgentAnswer(INSUFFICIENT_EVIDENCE, images, trace, grounded=False)
            grounded = grounding_on and grounding.check(resp.text, evidence)
            trace.append({"step": step, "text": resp.text, "tool_calls": [], "calls": [], "results": []})
            return AgentAnswer(resp.text, images, trace, grounded)

        messages.append(client.serialize_assistant(resp))              # EXECUTE
        calls, results = [], []
        for tc in resp.tool_calls:
            result = _run_one(tc, registry)
            if result.kind == "image" and not result.error:
                images.append(result.value)
            evidence.append(EvidenceRecord(tc, result))
            messages.append(observe(client, tc, result))               # OBSERVE (TODO-2)
            calls.append({"id": tc.id, "name": tc.name, "args": tc.args, "parse_error": tc.parse_error})
            results.append({"name": tc.name, "error": result.error, "summary": result.summary,
                            "dropped_args": result.dropped_args})
        trace.append({"step": step, "text": resp.text, "tool_calls": [tc.name for tc in resp.tool_calls],
                      "calls": calls, "results": results})

    return _finalize_or_failsafe(messages, client, registry, images, trace, evidence,
                                 question, completion_check, grounding_on)


# ---------------------------------------------------------------- helpers (skippable on a first read)

def _refusal_preflight(question, system_prompt, trace) -> AgentAnswer | None:
    """Deterministic safety handling — active only when the [REFUSAL] clause is present (TODO-3).
    Three responses by acuity: medical refusal, emergency escalation, crisis support. Room safety
    must not depend on a live model choosing to comply."""
    from ..llm.schemas import REFUSAL_MARKER

    if REFUSAL_MARKER in system_prompt:
        resp = safety_response(question)
        if resp is not None:
            kind, message = resp
            trace.append({"event": "safety", "kind": kind})
            return AgentAnswer(message, [], trace, grounded=False)
    return None


def _run_one(tc, registry) -> ToolResult:
    """Execute one tool call. Malformed model args (parse_error) short-circuit — never executed,
    so a default-arg tool can't run on {} and fabricate evidence."""
    if tc.parse_error:
        return ToolResult("text", f"tool error: invalid tool arguments: {tc.parse_error}", {}, error=True)
    return registry.call(tc.name, **tc.args)


def _check_completion(question, evidence, registry, completion_check, nudges_used) -> dict:
    """Decide whether a no-tool-call turn may finalize. No completion_check -> always allow."""
    if completion_check is None:
        return {"action": "allow"}
    res = completion_check(question, evidence, registry.names())
    missing = [r.tool_name for r in res.missing]
    if res.missing and nudges_used < MAX_NUDGES:
        force = res.missing[0].tool_name if len(res.missing) == 1 else None
        nudge_text = "You still need to call: " + "; ".join(r.nudge_text for r in res.missing)
        return {"action": "nudge", "missing": missing, "force_tool": force, "nudge_text": nudge_text}
    if res.missing or res.unavailable:
        return {"action": "fail_safe", "reason": "required evidence incomplete",
                "missing": missing, "unavailable": [r.tool_name for r in res.unavailable]}
    return {"action": "allow"}


def _finalize_or_failsafe(messages, client, registry, images, trace, evidence,
                          question, completion_check, grounding_on) -> AgentAnswer:
    """max_steps guard. If requirements are still unsatisfied, fail safe; else ask once for a
    best-effort final answer (no further tools)."""
    verdict = _check_completion(question, evidence, registry, completion_check, nudges_used=MAX_NUDGES)
    if verdict["action"] != "allow":
        trace.append({"event": "fail_safe", "reason": "max_steps reached with incomplete evidence",
                      "missing": verdict.get("missing", []), "unavailable": verdict.get("unavailable", [])})
        return AgentAnswer(INSUFFICIENT_EVIDENCE, images, trace, grounded=False)
    messages.append(user("Please give your best final answer now using only what you have gathered."))
    resp = client.chat(messages, tools=[])
    trace.append({"step": "final", "text": resp.text, "tool_calls": [], "calls": [], "results": []})
    grounded = grounding_on and grounding.check(resp.text, evidence)
    return AgentAnswer(resp.text, images, trace, grounded)
