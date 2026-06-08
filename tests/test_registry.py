from healthagent.llm.schemas import ToolResult
from healthagent.tools.registry import ToolRegistry, tool


@tool
def sample(user_id: str, n: int = 3) -> ToolResult:
    """A sample tool. Returns n doubled."""
    return ToolResult("text", f"n*2={n * 2}", {"n2": n * 2})


def test_decorator_builds_schema():
    spec = sample._tool_spec
    assert spec["name"] == "sample"
    assert spec["parameters"]["properties"]["user_id"]["type"] == "string"
    assert spec["parameters"]["properties"]["n"]["type"] == "integer"
    assert spec["parameters"]["required"] == ["user_id"]  # n has a default
    assert "A sample tool." in spec["description"]


def test_openai_schema_shape():
    reg = ToolRegistry()
    reg.register(sample)
    s = reg.schemas("openai")[0]
    assert s["type"] == "function"
    assert s["function"]["name"] == "sample"
    assert "_py_types" not in s["function"]["parameters"]  # internal key stripped


def test_call_coerces_str_to_int():
    reg = ToolRegistry()
    reg.register(sample)
    r = reg.call("sample", user_id="u01", n="5")  # LLM may pass strings
    assert r.value == {"n2": 10}


def test_call_wraps_none_and_errors():
    reg = ToolRegistry()

    @reg.tool
    def returns_none(user_id: str) -> ToolResult:
        """Returns None (simulating an unfinished tool)."""
        return None

    @reg.tool
    def raises(user_id: str) -> ToolResult:
        """Raises."""
        raise ValueError("boom")

    assert reg.call("returns_none", user_id="u01").error
    assert reg.call("raises", user_id="u01").error
    assert reg.call("nope", user_id="u01").error  # unknown tool
    assert reg.call("sample").error  # missing required arg
