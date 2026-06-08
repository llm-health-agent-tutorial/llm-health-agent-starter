"""Loop-level completion behavior with a controllable fake client (no network):
- nudge repairs early finalization (and passes force_tool when a single tool is missing);
- ignored nudges -> deterministic fail-safe (hard gate), grounded=False;
- no required tools registered -> unavailable -> immediate fail-safe;
- grounded flag is gated by [GROUNDING];
- ScriptedBackend keys intent off the FIRST user message (nudge-proof).
"""
from healthagent.agent import live_policy as LP
from healthagent.agent.loop import run_agent
from healthagent.agent.prompts import SOLUTION_SYSTEM, BASE_SYSTEM, GROUNDING_CLAUSE
from healthagent.llm.client import LLMClient, get_client
from healthagent.llm.schemas import ChatResponse, ToolCall
from healthagent.tools import retrieval, visualization
from healthagent.tools.builtin import compare_window
from healthagent.tools.registry import ToolRegistry
from ha_workshop.solutions import student_tools as good

R0, R1 = LP._R0, LP._R1
SLEEP_Q = "Why have I been sleeping poorly this week?"


def _obs(client, tc, result):
    return client.serialize_tool_result(tc, result)


def _full_registry():
    reg = ToolRegistry()
    reg.register(compare_window)
    reg.register_all([retrieval.query_sleep, good.query_screen_time, good.detect_change,
                      visualization.plot_timeseries])
    return reg


def _sleep_calls():
    """The five correct tool calls, one per turn."""
    return [
        ToolCall("a", "query_screen_time", {"user_id": "u01", "start_date": R0, "end_date": R1}),
        ToolCall("b", "query_sleep", {"user_id": "u01", "start_date": R0, "end_date": R1}),
        ToolCall("c", "detect_change", {"user_id": "u01", "metric": "night_screen_minutes"}),
        ToolCall("d", "detect_change", {"user_id": "u01", "metric": "total_sleep_hours"}),
        ToolCall("e", "plot_timeseries", {"user_id": "u01", "metric": "night_screen_minutes",
                                          "start_date": R0, "end_date": R1}),
    ]


class FakeClient(LLMClient):
    """Emits a scripted sequence of ChatResponses; records force_tool per turn."""
    provider = "fake"
    supports_force_tool = True

    def __init__(self, script):
        self.script = script
        self.i = 0
        self.forced = []

    def chat(self, messages, tools=None, *, force_tool=None):
        self.forced.append(force_tool)
        r = self.script[self.i] if self.i < len(self.script) else ChatResponse("done", [])
        self.i += 1
        return r


def test_ignored_nudge_fails_safe():
    # never calls a tool -> nudged twice -> hard fail-safe
    client = FakeClient([ChatResponse("here's my guess", [])] * 6)
    _, check = LP.augment(SOLUTION_SYSTEM)
    ans = run_agent(SLEEP_Q, client=client, registry=_full_registry(), observe=_obs,
                    system_prompt=SOLUTION_SYSTEM + LP.TOOL_POLICY, completion_check=check, max_steps=10)
    assert not ans.grounded
    assert "could not gather enough evidence" in ans.text.lower()
    assert any(e.get("event") == "fail_safe" for e in ans.trace)
    assert sum(1 for e in ans.trace if e.get("event") == "nudge") == 2  # nudge budget


def test_no_required_tools_unavailable_failsafe():
    reg = ToolRegistry()
    reg.register(compare_window)  # no sleep tools registered
    client = FakeClient([ChatResponse("answer", [])])
    _, check = LP.augment(SOLUTION_SYSTEM)
    ans = run_agent(SLEEP_Q, client=client, registry=reg, observe=_obs,
                    system_prompt=SOLUTION_SYSTEM + LP.TOOL_POLICY, completion_check=check, max_steps=10)
    assert not ans.grounded and any(e.get("event") == "fail_safe" for e in ans.trace)
    assert not any(e.get("event") == "nudge" for e in ans.trace)  # unavailable -> no pointless nudge


def test_nudge_repairs_early_finalization():
    calls = _sleep_calls()
    # turn0: finalize early (no tools) -> nudge; then emit the 5 tools one per turn; then finalize
    script = [ChatResponse("early answer", [])] + [ChatResponse("", [c]) for c in calls] + [ChatResponse("final", [])]
    client = FakeClient(script)
    _, check = LP.augment(SOLUTION_SYSTEM)
    ans = run_agent(SLEEP_Q, client=client, registry=_full_registry(), observe=_obs,
                    system_prompt=SOLUTION_SYSTEM + LP.TOOL_POLICY, completion_check=check, max_steps=12)
    assert any(e.get("event") == "nudge" for e in ans.trace)         # nudge fired
    assert not any(e.get("event") == "fail_safe" for e in ans.trace)  # ... and was repaired
    assert ans.images  # plot rendered


def test_grounded_gated_by_grounding_marker():
    client = get_client("scripted", quiet=True)
    reg = _full_registry()
    # WITHOUT [GROUNDING]: real tools + observe, useful answer, but grounded must be False
    _, check = LP.augment(BASE_SYSTEM)
    a = run_agent(SLEEP_Q, client=client, registry=reg, observe=_obs,
                  system_prompt=BASE_SYSTEM + LP.TOOL_POLICY, completion_check=check, max_steps=10)
    assert not a.grounded
    # WITH [GROUNDING]: flips to grounded
    prompt = BASE_SYSTEM + "\n" + GROUNDING_CLAUSE
    b = run_agent(SLEEP_Q, client=client, registry=reg, observe=_obs,
                  system_prompt=prompt + LP.TOOL_POLICY, completion_check=check, max_steps=10)
    assert b.grounded


def test_scripted_intent_is_nudge_proof():
    from healthagent.llm.scripted_client import ScriptedBackend

    be = ScriptedBackend()
    messages = [
        {"role": "system", "content": "[GROUNDING]"},
        {"role": "user", "content": "[user_id=u01] " + SLEEP_Q},   # the ORIGINAL task
        {"role": "user", "content": "You still need to call: detect_change"},  # a later nudge
    ]
    tools = [{"name": "query_screen_time"}, {"name": "query_sleep"}, {"name": "detect_change"},
             {"name": "plot_timeseries"}]
    resp = be.chat(messages, tools)
    # still plans a SLEEP tool (intent from first message), not derailed by the nudge text
    assert resp.tool_calls and resp.tool_calls[0].name in {t["name"] for t in tools}
