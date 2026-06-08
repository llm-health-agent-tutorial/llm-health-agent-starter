"""YOUR Module-4 agent configuration. Edit THIS file (the notebook prints its exact path).

Three small TODOs wire your agent together. The loop itself (healthagent/agent/loop.py) is
complete and read-only — you only supply these three pieces. ``compare_window`` is always
pre-registered by make_registry(), so the activity-vs-goal question works out of the box; your
TODO-1 list is what unlocks the sleep question.
"""
from __future__ import annotations

from healthagent.agent.loop import run_agent
from healthagent.agent.prompts import BASE_SYSTEM
from healthagent.llm.schemas import OBSERVATION_NOT_ATTACHED, ToolResult
from healthagent.tools import retrieval, visualization  # noqa: F401  (you'll use these in TODO-1)
from healthagent.tools.builtin import compare_window
from healthagent.tools.registry import ToolRegistry

from . import student_tools  # noqa: F401  (you'll use student_tools.* in TODO-1)

# === TODO-1: register the tools needed to answer the sleep question. ===
# Add: retrieval.query_sleep, student_tools.query_screen_time, student_tools.detect_change,
#      visualization.plot_timeseries
WORKSHOP_TOOLS: list = [
    # TODO: list the four tools here
]
# === END TODO-1 ===


# === TODO-2: build the observation message the model sees after each tool call. ===
def observe(client, tool_call, result):
    # TODO: replace the placeholder line below with the real serialized tool result:
    #     return client.serialize_tool_result(tool_call.id, result)
    return client.serialize_tool_result(tool_call.id, ToolResult("text", OBSERVATION_NOT_ATTACHED, {}))
# === END TODO-2 ===


# === TODO-3: the system prompt. Start from BASE_SYSTEM and append the [GROUNDING] and
#     [REFUSAL] clauses (see healthagent/agent/prompts.py for ready-made clause text). ===
SYSTEM_PROMPT = BASE_SYSTEM
# === END TODO-3 ===


def make_registry() -> ToolRegistry:
    """compare_window is always available; WORKSHOP_TOOLS adds your Module-3 tools (TODO-1)."""
    reg = ToolRegistry()
    reg.register(compare_window)
    reg.register_all(WORKSHOP_TOOLS)
    return reg


def run(question: str, *, client, user_id: str = "u01", verbose: bool = False):
    return run_agent(
        question,
        client=client,
        registry=make_registry(),
        observe=observe,
        system_prompt=SYSTEM_PROMPT,
        user_id=user_id,
        verbose=verbose,
    )
