"""Provider message-shape contract tests (no network). Marked provider_contract; skips cleanly at
collection when the SDKs are absent (it constructs real provider type objects)."""
import json

import pytest

pytest.importorskip("openai")
pytest.importorskip("google.genai")
pytest.importorskip("ollama")

pytestmark = pytest.mark.provider_contract

from healthagent.llm import gemini_client as G  # noqa: E402
from healthagent.llm import ollama_client as O  # noqa: E402
from healthagent.llm import openai_client as OA  # noqa: E402
from healthagent.llm.client import LLMClient  # noqa: E402
from healthagent.llm.schemas import ToolCall, ToolResult  # noqa: E402
from healthagent.tools.registry import ToolRegistry  # noqa: E402

NEUTRAL = [
    {"role": "system", "content": "sys"},
    {"role": "user", "content": "why poor sleep"},
    {"role": "assistant", "content": "", "tool_calls": [
        {"id": "c1", "name": "detect_change", "args": {"metric": "night_screen_minutes"}},
        {"id": "c2", "name": "query_sleep", "args": {"start_date": "2026-05-30"}}]},
    {"role": "tool", "tool_call_id": "c1", "name": "detect_change", "content": "night up 855%"},
    {"role": "tool", "tool_call_id": "c2", "name": "query_sleep", "content": "7 nights"},
]


# ---- seam: tool-result message carries the tool NAME (Gemini/Ollama need it) ----
def test_serialize_tool_result_has_name():
    msg = LLMClient().serialize_tool_result(ToolCall("c1", "detect_change", {}),
                                            ToolResult("text", "s", {}))
    assert msg["name"] == "detect_change" and msg["tool_call_id"] == "c1"


# ---- OpenAI ----
def test_openai_messages_shape_and_ids():
    msgs = OA.to_openai_messages(NEUTRAL)
    asst = [m for m in msgs if m["role"] == "assistant"][0]
    assert asst["tool_calls"][0]["id"] == "c1"
    assert json.loads(asst["tool_calls"][0]["function"]["arguments"]) == {"metric": "night_screen_minutes"}
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert tool_msgs[0]["tool_call_id"] == "c1"


def test_openai_tool_choice_force():
    assert OA.tool_choice_for("detect_change") == {"type": "function", "function": {"name": "detect_change"}}
    assert OA.tool_choice_for(None) == "auto"


def test_openai_parse_multi_and_malformed():
    good = {"content": "", "tool_calls": [
        {"id": "a", "function": {"name": "f", "arguments": '{"x": 1}'}},
        {"id": "b", "function": {"name": "g", "arguments": "{bad json"}}]}
    resp = OA.parse_openai_response(good)
    assert resp.tool_calls[0].args == {"x": 1} and resp.tool_calls[0].parse_error is None
    assert resp.tool_calls[1].args == {} and resp.tool_calls[1].parse_error  # malformed -> parse_error, not raise


def test_openai_parse_no_tool_calls_and_text():
    resp = OA.parse_openai_response({"content": "just text", "tool_calls": None})
    assert resp.text == "just text" and resp.tool_calls == []


# ---- Ollama ----
def test_ollama_schema_is_openai_style():
    reg = ToolRegistry()

    @reg.tool
    def query_sleep(user_id: str) -> ToolResult:
        """q"""
        return ToolResult("text", "", {})

    s = reg.schemas("ollama")[0]
    assert s["type"] == "function" and s["function"]["name"] == "query_sleep"
    assert s["function"]["parameters"]["additionalProperties"] is False


def test_ollama_request_and_parse():
    msgs = O.to_ollama_request(NEUTRAL)
    asst = [m for m in msgs if m["role"] == "assistant"][0]
    assert asst["tool_calls"][0]["function"]["name"] == "detect_change"
    parsed = O.parse_ollama_response({"content": "x", "tool_calls": [
        {"function": {"name": "f", "arguments": {"a": 1}}},
        {"function": {"name": "g", "arguments": "{bad"}}]})
    assert parsed.tool_calls[0].args == {"a": 1}
    assert parsed.tool_calls[1].args == {} and parsed.tool_calls[1].parse_error


# ---- Gemini (state-machine round-trip + ids + tools + force) ----
def test_gemini_contents_grouping_and_ids():
    si, contents = G.to_gemini_contents(NEUTRAL)
    assert si == "sys"
    assert [c.role for c in contents] == ["user", "model", "user"]  # tool results grouped into one user Content
    fr_parts = contents[-1].parts
    assert {p.function_response.name for p in fr_parts} == {"detect_change", "query_sleep"}
    assert contents[-1].parts[0].function_response.id == "c1"  # id echoed


def test_gemini_tools_and_force():
    tools = G.to_gemini_tools([{"name": "detect_change", "description": "d",
                                "parameters": {"type": "object",
                                               "properties": {"metric": {"type": "string", "enum": ["a"]}},
                                               "required": ["metric"]}}])
    fd = tools[0].function_declarations[0]
    assert fd.name == "detect_change" and str(fd.parameters.type) .endswith("OBJECT")
    assert G.tool_config_for("detect_change").function_calling_config.allowed_function_names == ["detect_change"]


def test_gemini_parse_roundtrip():
    from google.genai import types as T

    content = T.Content(role="model", parts=[
        T.Part(function_call=T.FunctionCall(id="c9", name="detect_change", args={"metric": "x"}))])

    class _Resp:
        candidates = [type("C", (), {"content": content})()]

    resp = G.parse_gemini_response(_Resp())
    assert resp.tool_calls[0].name == "detect_change" and resp.tool_calls[0].args == {"metric": "x"}
