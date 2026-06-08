"""Soft guard: the Module-4 'read the loop' core stays legible — the five step markers are present
and the function body is under a line budget, so robustness helpers don't sprawl into the core."""
import inspect

from healthagent.agent.loop import run_agent

CORE_LINE_BUDGET = 130


def test_five_step_markers_present():
    src = inspect.getsource(run_agent).upper()
    for marker in ("PLAN", "SELECT", "EXECUTE", "OBSERVE", "RESPOND"):
        assert marker in src, f"missing step marker {marker} in run_agent"


def test_core_under_line_budget():
    body = [ln for ln in inspect.getsource(run_agent).splitlines() if ln.strip()]
    assert len(body) <= CORE_LINE_BUDGET, f"run_agent core is {len(body)} lines (budget {CORE_LINE_BUDGET})"
