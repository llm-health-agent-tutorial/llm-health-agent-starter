from healthagent.llm.evidence import is_failed_observation_message, is_failed_tool_result
from healthagent.llm.schemas import OBSERVATION_NOT_ATTACHED, TODO_SENTINEL, ToolResult


def test_failed_tool_result_cases():
    assert is_failed_tool_result(ToolResult("text", "tool error: x", {}, error=True))
    assert is_failed_tool_result(ToolResult("text", TODO_SENTINEL, {}))
    assert is_failed_tool_result(ToolResult("text", "ok", None))
    assert is_failed_tool_result(ToolResult("text", "ok", {}))
    assert is_failed_tool_result("not a toolresult")  # type: ignore[arg-type]


def test_good_tool_result_passes():
    assert not is_failed_tool_result(ToolResult("text", "sleep 5.7h", {"mean": 5.7}))
    assert not is_failed_tool_result(ToolResult("image", "plotted", "/tmp/x.png"))  # image value ok


def test_failed_observation_message_cases():
    assert is_failed_observation_message({"role": "tool", "content": OBSERVATION_NOT_ATTACHED})
    assert is_failed_observation_message({"role": "tool", "content": "tool error: boom"})
    assert is_failed_observation_message({"role": "tool", "content": f"... {TODO_SENTINEL} ..."})
    assert is_failed_observation_message({"role": "tool", "content": ""})


def test_good_or_nontool_message():
    assert not is_failed_observation_message({"role": "tool", "content": "night screen 89 min"})
    assert not is_failed_observation_message({"role": "assistant", "content": ""})  # not an observation
