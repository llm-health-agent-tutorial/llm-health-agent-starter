"""Live smoke (opt-in: HA_TEST_LIVE=1 plus a configured key or a pulled Ollama model).

Runs the KNOWN-GOOD reference agent (`ha_workshop.solutions.agent_config`, all three TODOs applied
-- the untouched stub is intentionally ungrounded because `grounded` is `[GROUNDING]`-gated) against
each available live provider and asserts the workshop's hard guarantees at the SIGNATURE level:

- sleep: every required signature satisfied by a non-error evidence record (detect_change for BOTH
  metrics + plot_timeseries(night_screen_minutes) + both queries, each on the correct date window),
  a plot rendered, nudges within budget;
- activity: the activity requirement satisfied;
- medical: deterministic medical refusal (loop-owned, never model-dependent).

Clean args + grounding are asserted strictly for the CLOUD tiers (the documented supported models:
they emit valid args and reliably cite the magnitude). For Ollama they are best-effort -- the registry
correctly strips any stray arg (dropped_args is the safety net), and llama3.1:8b frequently states the
cause without quoting the number (grounded honestly reports False). The structural guarantees above
still hold for every provider. See the verification notes in the M2 plan.
"""
import os

import pytest

if os.getenv("HA_TEST_LIVE") != "1":
    pytest.skip("set HA_TEST_LIVE=1 (+ a key or a pulled Ollama model) to run live smoke",
                allow_module_level=True)

from healthagent.agent import live_policy as LP  # noqa: E402
from healthagent.agent.loop import MAX_NUDGES as LP_MAX_NUDGES  # noqa: E402
from healthagent.llm.client import get_client  # noqa: E402
from healthagent.llm.errors import BackendUnavailable  # noqa: E402
from healthagent.safety.refusal import REFUSAL_TEMPLATE  # noqa: E402
from ha_workshop.solutions import agent_config as known_good  # noqa: E402

SLEEP_Q = "Why have I been sleeping poorly this week?"
ACTIVITY_Q = "How does my activity compare to my goal?"
MEDICAL_Q = "Should I take melatonin for my sleep?"
CLOUD = {"openai", "gemini"}
# A decline-consistent direction word for the sleep summary (which is negative). "require a right
# word" (not "reject a wrong word") because a correct answer also says "increase" about SCREEN time.
_SLEEP_DIRECTION = ("less", "lower", "drop", "declin", "decreas", "short", "down", "worse", "fewer",
                    "reduc", "negativ", "below")


def _providers():
    out = ["ollama"]  # attempted; skipped per-test if the model isn't pulled / SDK absent
    if os.getenv("OPENAI_API_KEY"):
        out.append("openai")
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):  # GOOGLE_API_KEY = SDK-native
        out.append("gemini")
    return out


def _client_or_skip(provider):
    try:
        c = get_client(provider, allow_fallback=False, quiet=True)
    except BackendUnavailable as e:
        pytest.skip(f"{provider} not available: {e}")
    assert c.provider == provider  # allow_fallback=False -> never silently scripted
    return c


def _pairs(trace):
    for step in trace:
        for call, res in zip(step.get("calls", []), step.get("results", [])):
            yield call, res


def _satisfied(trace, req):
    return any(
        call["name"] == req.tool_name and not res["error"] and not call.get("parse_error")
        and req.args_match(call["args"])
        for call, res in _pairs(trace)
    )


@pytest.mark.parametrize("provider", _providers())
def test_live_sleep(provider):
    client = _client_or_skip(provider)
    ans = known_good.run(SLEEP_Q, client=client)

    for req in LP.SLEEP_REQS:  # signature-level: right tool + metric + date window, non-error
        assert _satisfied(ans.trace, req), f"{provider}: requirement unsatisfied: {req.label}"
    assert ans.images, f"{provider}: no plot rendered"
    assert sum(1 for s in ans.trace if s.get("event") == "nudge") <= LP_MAX_NUDGES, \
        f"{provider}: exceeded nudge budget"

    if provider in CLOUD:  # documented supported tiers: emit clean args + cite the magnitude
        assert all(not res["dropped_args"] for _, res in _pairs(ans.trace) if not res["error"]), \
            f"{provider}: dropped args on the happy path"
        assert ans.grounded, f"{provider}: answer not grounded"
        assert any(w in ans.text.lower() for w in _SLEEP_DIRECTION), \
            f"{provider}: grounded but no sleep-direction word (possible sign-flip): {ans.text[:200]}"
    # Ollama (best-effort): the registry correctly STRIPS any stray arg (dropped_args is the safety
    # net, exercised in unit tests); llama3.1:8b also frequently omits the numeric, so grounding +
    # clean-args are not hard-asserted here. The structural guarantees above still hold.


@pytest.mark.parametrize("provider", _providers())
def test_live_activity(provider):
    client = _client_or_skip(provider)
    ans = known_good.run(ACTIVITY_Q, client=client)
    for req in LP.ACTIVITY_REQS:
        assert _satisfied(ans.trace, req), f"{provider}: activity requirement unsatisfied: {req.label}"
    if provider in CLOUD:
        assert ans.grounded, f"{provider}: activity answer not grounded"


@pytest.mark.parametrize("provider", _providers())
def test_live_medical_refused(provider):
    client = _client_or_skip(provider)
    ans = known_good.run(MEDICAL_Q, client=client)
    assert ans.text == REFUSAL_TEMPLATE  # deterministic, loop-owned -> identical across providers
    assert not ans.grounded
