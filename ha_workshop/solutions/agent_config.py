"""Reference solution for ha_workshop/agent_config.py (the three M4 seams, filled)."""
from __future__ import annotations

from healthagent.agent.loop import run_agent
from healthagent.agent.prompts import SOLUTION_SYSTEM
from healthagent.tools import retrieval, visualization
from healthagent.tools.builtin import compare_window
from healthagent.tools.registry import ToolRegistry

from . import student_tools

# TODO-1 (filled): the four tools that unlock the sleep question.
WORKSHOP_TOOLS = [
    retrieval.query_sleep,
    student_tools.query_screen_time,
    student_tools.detect_change,
    visualization.plot_timeseries,
]


# TODO-2 (filled): feed the real serialized tool result back to the model.
def observe(client, tool_call, result):
    return client.serialize_tool_result(tool_call.id, result)


# TODO-3 (filled): base prompt + the [GROUNDING] and [REFUSAL] clauses.
SYSTEM_PROMPT = SOLUTION_SYSTEM


def make_registry() -> ToolRegistry:
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
