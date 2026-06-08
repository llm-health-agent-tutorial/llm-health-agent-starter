"""The out-of-the-box baseline agent (Module-4 cell 2).

Ships working: only ``compare_window`` is registered, with a real observe and the complete
system prompt, so ``run_baseline_agent("How does my activity compare to my goal?")`` returns a
grounded answer BEFORE participants edit anything. It deliberately CANNOT answer the sleep
question (no sleep/screen tools registered), which is what makes Module-4 TODO-1 matter.
"""
from __future__ import annotations

from .loop import run_agent
from .prompts import SOLUTION_SYSTEM
from ..llm.client import LLMClient
from ..llm.schemas import ToolResult
from ..tools.builtin import compare_window
from ..tools.registry import ToolRegistry


def _real_observe(client: LLMClient, tool_call, result: ToolResult) -> dict:
    return client.serialize_tool_result(tool_call.id, result)


def baseline_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(compare_window)
    return reg


def run_baseline_agent(question: str, *, client: LLMClient, user_id: str = "u01"):
    return run_agent(
        question,
        client=client,
        registry=baseline_registry(),
        observe=_real_observe,
        system_prompt=SOLUTION_SYSTEM,
        user_id=user_id,
    )
