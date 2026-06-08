"""grounding.check: magnitude match, literal sign-flip rejection, window/date numbers ignored."""
from healthagent.agent import grounding
from healthagent.llm.schemas import EvidenceRecord, ToolCall, ToolResult


def _ev(summary, error=False):
    # non-empty value so a non-error record reads as usable evidence (empty value == failed)
    return EvidenceRecord(ToolCall("i", "detect_change", {}),
                          ToolResult("text", summary, {"ok": True}, error=error))


SUMMARY = "total_sleep_hours down -23.9% (recent 5.69 vs baseline 7.47 hours; significant)."


def test_positive_phrasing_matches_negative_summary():
    # correct live phrasing states magnitude positively with a direction word
    assert grounding.check("your sleep dropped 24% this week", [_ev(SUMMARY)])


def test_exact_quote_grounds():
    assert grounding.check("sleep is down -23.9%", [_ev(SUMMARY)])


def test_literal_sign_flip_rejected():
    # answer claims +24 while summary is -24: a literal signed contradiction -> not grounded
    assert not grounding.check("sleep went +24% (i.e. up)", [_ev("change -24% down")])


def test_window_only_number_not_grounding():
    # "7 days" is a window count, not evidence
    assert not grounding.check("I looked at the last 7 days.", [_ev(SUMMARY)])


def test_number_absent_from_summary():
    assert not grounding.check("your sleep changed by 99 hours", [_ev(SUMMARY)])


def test_failed_evidence_never_grounds():
    assert not grounding.check("sleep down 23.9%", [_ev("tool error: boom", error=True)])
