"""The agent loop — single, canonical, read-only. ~110 lines.

plan -> select -> execute -> OBSERVE -> respond. The three workshop pieces are INJECTED, never
edited in place: which tools are in ``registry`` (TODO-1), the ``observe`` callable that builds
the tool-result message (TODO-2), and the ``system_prompt`` (TODO-3). The out-of-box baseline,
the reference solutions, and the M5 known-good agent all call this same function with their
own injected pieces.
"""
from __future__ import annotations

from typing import Callable

from . import grounding
from .. import config
from ..llm.client import LLMClient, system, user
from ..llm.schemas import AgentAnswer, ToolResult

Observe = Callable[[LLMClient, object, ToolResult], dict]


def run_agent(
    question: str,
    *,
    client: LLMClient,
    registry,
    observe: Observe,
    system_prompt: str,
    user_id: str = "u01",
    max_steps: int = 6,
    verbose: bool = False,
) -> AgentAnswer:
    messages = [
        system(system_prompt),
        user(f"[user_id={user_id}] [dataset_today={config.dataset_today()}] {question}"),
    ]
    images: list[str] = []
    trace: list[dict] = []
    collected: list[ToolResult] = []

    for step in range(max_steps):
        resp = client.chat(messages, tools=registry.schemas(client.provider))  # PLAN + SELECT
        trace.append({"step": step, "text": resp.text, "tool_calls": [tc.name for tc in resp.tool_calls]})
        if verbose:
            print(f"[step {step}] tools={[tc.name for tc in resp.tool_calls]} text={resp.text[:80]!r}")

        if not resp.tool_calls:  # RESPOND
            grounded = grounding.check(resp.text, collected)
            return AgentAnswer(text=resp.text, images=images, trace=trace, grounded=grounded)

        messages.append(client.serialize_assistant(resp))  # EXECUTE: record the assistant turn
        for tc in resp.tool_calls:
            result = registry.call(tc.name, **tc.args)
            if result.kind == "image" and not result.error:
                images.append(result.value)
            collected.append(result)
            # === OBSERVE (Module-4 TODO-2 lives in the injected `observe`) ===
            messages.append(observe(client, tc, result))

    return _force_final_answer(messages, client, registry, images, trace, collected)


def _force_final_answer(messages, client, registry, images, trace, collected) -> AgentAnswer:
    """max_steps guard: ask once more for a best-effort answer with no further tool calls."""
    messages.append(user("Please give your best final answer now using only what you have gathered."))
    resp = client.chat(messages, tools=[])
    trace.append({"step": "final", "text": resp.text, "tool_calls": []})
    grounded = grounding.check(resp.text, collected)
    return AgentAnswer(text=resp.text, images=images, trace=trace, grounded=grounded)
