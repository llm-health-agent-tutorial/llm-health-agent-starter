"""Packaged known-good reference agent — the library twin of the teaching copy under the workshop
``solutions/`` package.

The CLIs (``ha-chat``, ``ha-eval``) use THIS so they work from a wheel / non-editable install: it
imports only packaged modules and never touches the unpackaged workshop tree (intentionally outside
the setuptools package list). Same wiring as the solution — register the four reference tools + the
pre-wired ``compare_window``, feed real observations back, use the grounding/refusal system prompt,
and run under the live-reliability completion check.
"""
from __future__ import annotations

from . import live_policy
from .loop import run_agent
from .prompts import SOLUTION_SYSTEM
from ..tools import analysis, retrieval, visualization
from ..tools.builtin import compare_window
from ..tools.registry import ToolRegistry

# Packaged reference implementations of the tools participants build in Modules 3–4.
REFERENCE_TOOLS = [
    retrieval.query_sleep,
    retrieval.query_screen_time,
    analysis.detect_change,
    visualization.plot_timeseries,
]


def _observe(client, tool_call, result):
    return client.serialize_tool_result(tool_call, result)


def make_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(compare_window)
    reg.register_all(REFERENCE_TOOLS)
    return reg


def run_reference_agent(question: str, *, client, user_id: str = "u01", verbose: bool = False):
    """Answer a question with the full known-good agent on the given backend. Returns AgentAnswer."""
    prompt, check = live_policy.augment(SOLUTION_SYSTEM)
    return run_agent(
        question,
        client=client,
        registry=make_registry(),
        observe=_observe,
        system_prompt=prompt,
        user_id=user_id,
        max_steps=10,
        completion_check=check,
        verbose=verbose,
    )
