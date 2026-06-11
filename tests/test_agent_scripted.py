"""Full-loop behavior on ScriptedBackend, including the safety guarantees."""
from healthagent.agent.baseline import run_baseline_agent
from healthagent.llm.client import get_client
from healthagent.llm.scripted_client import ScriptedBackend
from healthagent.llm.schemas import OBSERVATION_NOT_ATTACHED

SLEEP_Q = "Why have I been sleeping poorly this week?"
ACT_Q = "How does my activity compare to my goal?"
MED_Q = "Should I take melatonin for my sleep?"


def client():
    return get_client("scripted", quiet=True)


# --- baseline (M4-C2 out of the box) ---
def test_baseline_answers_activity_grounded():
    a = run_baseline_agent(ACT_Q, client=client())
    assert a.grounded and "goal" in a.text.lower()


def test_baseline_cannot_answer_sleep_yet():
    a = run_baseline_agent(SLEEP_Q, client=client())
    assert not a.grounded  # no sleep/screen tools registered -> TODO-1 matters


def test_baseline_refuses_medical():
    a = run_baseline_agent(MED_Q, client=client())
    assert "clinician" in a.text.lower() and not a.grounded


# --- solution config (after the three M4 edits) ---
def test_solution_answers_sleep_grounded_with_caveat():
    from ha_workshop.solutions import agent_config as sol

    a = sol.run(SLEEP_Q, client=client())
    assert a.grounded
    low = a.text.lower()
    assert "one data-grounded hypothesis" in low and "synthetic" in low
    assert "not proof of cause" in low  # carries the causation hedge
    assert a.images, "the sleep demo must render a plot (plot_timeseries)"


def test_solution_refuses_medical():
    from ha_workshop.solutions import agent_config as sol

    assert "clinician" in sol.run(MED_Q, client=client()).text.lower()


def test_todo1_canonical_list():
    from ha_workshop.solutions import agent_config as sol

    names = {fn.__name__ for fn in sol.WORKSHOP_TOOLS}
    assert names == {"query_sleep", "query_screen_time", "detect_change", "plot_timeseries"}


# --- stub config (unfilled TODOs) must fail SAFE ---
def test_stub_fails_safe_on_all_questions():
    import ha_workshop.agent_config as stub

    c = client()
    for q in (SLEEP_Q, ACT_Q, MED_Q):
        a = stub.run(q, client=c)
        assert not a.grounded
        # never a fabricated finding:
        assert "one data-grounded hypothesis" not in a.text.lower()


# --- each SINGLE M3 blank left undone must fail safe (not just the all-stub case) ---
import pytest  # noqa: E402

from healthagent.agent.loop import run_agent  # noqa: E402
from healthagent.agent.prompts import SOLUTION_SYSTEM  # noqa: E402
from healthagent.tools import retrieval, visualization  # noqa: E402
from healthagent.tools.builtin import compare_window  # noqa: E402
from healthagent.tools.registry import ToolRegistry  # noqa: E402
from healthagent.llm.schemas import TODO_SENTINEL, ToolResult  # noqa: E402
from ha_workshop.solutions import student_tools as good  # noqa: E402


def _stub(name):
    """A stand-in for an unfilled M3 tool body (returns the TODO sentinel)."""
    def fn(*args, **kwargs):
        return ToolResult("text", TODO_SENTINEL, {})
    fn.__name__ = name
    return fn


def _real_observe(client, tc, result):
    return client.serialize_tool_result(tc, result)


@pytest.mark.parametrize("blank", ["query_screen_time", "detect_change", "query_sleep", "plot_timeseries"])
def test_single_m3_blank_fails_safe(blank):
    """If exactly one assigned tool is still a stub, the sleep answer must be ungrounded."""
    tools = {
        "query_sleep": retrieval.query_sleep,
        "query_screen_time": good.query_screen_time,
        "detect_change": good.detect_change,
        "plot_timeseries": visualization.plot_timeseries,
    }
    tools[blank] = _stub(blank)  # knock out one tool
    reg = ToolRegistry()
    reg.register(compare_window)
    reg.register_all(list(tools.values()))
    ans = run_agent(SLEEP_Q, client=client(), registry=reg, observe=_real_observe,
                    system_prompt=SOLUTION_SYSTEM)
    assert not ans.grounded, f"blanking {blank} still produced a grounded answer"
    assert "one data-grounded hypothesis" not in ans.text.lower()


# --- TODO-2 sentinel is ignored as evidence (unit level) ---
def test_scripted_ignores_sentinel_observations():
    be = ScriptedBackend()
    messages = [
        {"role": "system", "content": "[GROUNDING]"},
        {"role": "user", "content": "[user_id=u01] " + SLEEP_Q},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "c1", "name": "detect_change", "args": {"user_id": "u01", "metric": "night_screen_minutes"}}]},
        {"role": "tool", "tool_call_id": "c1", "name": "detect_change", "content": OBSERVATION_NOT_ATTACHED},
        {"role": "assistant", "content": "",
         "tool_calls": [{"id": "c2", "name": "detect_change", "args": {"user_id": "u01", "metric": "total_sleep_hours"}}]},
        {"role": "tool", "tool_call_id": "c2", "name": "detect_change", "content": OBSERVATION_NOT_ATTACHED},
    ]
    tools = [{"name": "detect_change"}]  # plan exhausted -> must finalize
    resp = be.chat(messages, tools)
    # all observations are sentinels -> ungrounded fallback, no fabricated number
    assert "could not gather enough evidence" in resp.text.lower()
