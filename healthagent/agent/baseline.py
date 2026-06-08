"""The out-of-the-box baseline agent (Module-4 cell 2).

Ships working: only ``compare_window`` is registered, with a real observe and the complete system
prompt, so the activity question is answered out of the box. The sleep question fails safe (its
required tools aren't registered) — which is exactly what makes Module-4 TODO-1 matter. Uses the
same read-only live-reliability plumbing (TOOL_POLICY + completion_check) as the solution path.
"""
from __future__ import annotations

from . import live_policy
from .loop import run_agent
from .prompts import SOLUTION_SYSTEM
from ..llm.client import LLMClient
from ..llm.schemas import ToolCall, ToolResult
from ..tools.builtin import compare_window
from ..tools.registry import ToolRegistry


def _real_observe(client: LLMClient, tool_call: ToolCall, result: ToolResult) -> dict:
    return client.serialize_tool_result(tool_call, result)


def baseline_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(compare_window)
    return reg


def run_baseline_agent(question: str, *, client: LLMClient, user_id: str = "u01"):
    prompt, check = live_policy.augment(SOLUTION_SYSTEM)
    return run_agent(
        question,
        client=client,
        registry=baseline_registry(),
        observe=_real_observe,
        system_prompt=prompt,
        user_id=user_id,
        max_steps=10,
        completion_check=check,
    )
