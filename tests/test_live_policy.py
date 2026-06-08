"""live_policy: intent detection, alias resolution, SIGNATURE matching (metric + date window),
missing vs unavailable, failed-then-success, and unknown-intent (never gated). No network."""
from healthagent.agent import live_policy as LP
from healthagent.agent.live_policy import completion_check, requirements_for
from healthagent.llm.schemas import EvidenceRecord, ToolCall, ToolResult

R0, R1 = LP._R0, LP._R1
ALL = ["query_screen_time", "query_sleep", "detect_change", "plot_timeseries", "compare_window"]


def _ev(name, args, ok=True):
    # non-empty value on the happy path; an empty value is (correctly) treated as failed evidence
    res = ToolResult("text", "summary" if ok else "tool error", {"ok": True} if ok else {}, error=not ok)
    return EvidenceRecord(ToolCall("id", name, args), res)


def test_intent_detection():
    assert requirements_for("why have I been sleeping poorly") is LP.SLEEP_REQS
    assert requirements_for("how does my activity compare to my goal") is LP.ACTIVITY_REQS
    assert requirements_for("what's the weather like") == []  # unknown -> no requirements


def test_unknown_intent_never_gated():
    res = completion_check("tell me a joke", [], ALL)
    assert not res.missing and not res.unavailable  # final answer allowed


def _full_sleep_evidence():
    return [
        _ev("query_screen_time", {"user_id": "u01", "start_date": R0, "end_date": R1}),
        _ev("query_sleep", {"user_id": "u01", "start_date": R0, "end_date": R1}),
        _ev("detect_change", {"user_id": "u01", "metric": "night_screen_minutes"}),
        _ev("detect_change", {"user_id": "u01", "metric": "total_sleep_hours"}),
        _ev("plot_timeseries", {"user_id": "u01", "metric": "night_screen_minutes", "start_date": R0, "end_date": R1}),
    ]


def test_full_signatures_satisfied():
    res = completion_check("why poor sleep", _full_sleep_evidence(), ALL)
    assert not res.missing and not res.unavailable


def test_alias_resolution_in_signature():
    ev = _full_sleep_evidence()
    ev[2] = _ev("detect_change", {"user_id": "u01", "metric": "night_screen"})  # alias of night_screen_minutes
    res = completion_check("why poor sleep", ev, ALL)
    assert not res.missing  # alias resolves -> satisfied


def test_wrong_metric_not_satisfied():
    ev = _full_sleep_evidence()
    ev[3] = _ev("detect_change", {"user_id": "u01", "metric": "steps"})  # wrong metric for the sleep req
    res = completion_check("why poor sleep", ev, ALL)
    assert any(r.tool_name == "detect_change" for r in res.missing)


def test_wrong_window_not_satisfied():
    ev = _full_sleep_evidence()
    ev[1] = _ev("query_sleep", {"user_id": "u01", "start_date": "2026-01-01", "end_date": "2026-01-07"})
    res = completion_check("why poor sleep", ev, ALL)
    assert any(r.tool_name == "query_sleep" for r in res.missing)


def test_missing_vs_unavailable():
    # plot_timeseries NOT registered -> unavailable; detect_change registered but absent -> missing
    avail = ["query_screen_time", "query_sleep", "detect_change", "compare_window"]
    ev = [_ev("query_screen_time", {"user_id": "u01", "start_date": R0, "end_date": R1}),
          _ev("query_sleep", {"user_id": "u01", "start_date": R0, "end_date": R1})]
    res = completion_check("why poor sleep", ev, avail)
    assert any(r.tool_name == "detect_change" for r in res.missing)
    assert any(r.tool_name == "plot_timeseries" for r in res.unavailable)


def test_failed_then_success():
    ev = _full_sleep_evidence()
    # an earlier FAILED detect_change(night) then a later SUCCESS -> satisfied
    ev.insert(2, _ev("detect_change", {"user_id": "u01", "metric": "night_screen_minutes"}, ok=False))
    res = completion_check("why poor sleep", ev, ALL)
    assert not res.missing
