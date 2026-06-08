"""@tool decorator + ToolRegistry.

Registering a tool with an LLM is a one-liner: ``REGISTRY.register(fn)`` (or ``@REGISTRY.tool``).
The decorator introspects the signature + type hints + docstring into a JSON schema, so
participants never hand-write provider JSON. ``call()`` validates/coerces LLM-supplied args
(the trust boundary) and wraps None/exceptions into a visible tool-error ToolResult so a bad
tool degrades rather than crashes the loop.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

from ..llm.schemas import ToolResult

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}


def _build_spec(fn: Callable) -> dict:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    props: dict[str, dict] = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        py_t = hints.get(name, str)
        json_t = _PY_TO_JSON.get(py_t, "string")
        props[name] = {"type": json_t}
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            props[name]["default"] = param.default
    doc = inspect.getdoc(fn) or ""
    description = doc.strip().split("\n\n")[0].replace("\n", " ").strip()
    return {
        "name": fn.__name__,
        "description": description,
        "parameters": {"type": "object", "properties": props, "required": required},
        "_py_types": {n: hints.get(n, str) for n in props},
    }


def tool(fn: Callable) -> Callable:
    """Attach a JSON tool-spec to ``fn`` (idempotent)."""
    fn._tool_spec = _build_spec(fn)  # type: ignore[attr-defined]
    return fn


def _coerce(value: Any, py_t: type) -> Any:
    if value is None or isinstance(value, py_t):
        return value
    try:
        if py_t is bool:
            return str(value).strip().lower() in {"1", "true", "yes"}
        return py_t(value)
    except (ValueError, TypeError):
        return value


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}

    def register(self, fn: Callable) -> Callable:
        if not hasattr(fn, "_tool_spec"):
            tool(fn)
        self._tools[fn.__name__] = fn
        return fn

    def register_all(self, fns) -> None:
        for fn in fns:
            self.register(fn)

    # decorator form: @REGISTRY.tool
    def tool(self, fn: Callable) -> Callable:
        return self.register(fn)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def clear(self) -> None:
        self._tools.clear()

    def spec(self, name: str) -> dict:
        return self._tools[name]._tool_spec  # type: ignore[attr-defined]

    def schemas(self, provider: str = "scripted") -> list[dict]:
        """Render per-provider tool specs from the same internal spec."""
        specs = []
        for name in self.names():
            s = self._tools[name]._tool_spec  # type: ignore[attr-defined]
            params = {k: v for k, v in s["parameters"].items()}
            # strip our internal helper key from the public schema
            clean = {"name": s["name"], "description": s["description"], "parameters": params}
            if provider == "openai":
                specs.append({"type": "function", "function": clean})
            elif provider == "gemini":
                specs.append(clean)  # adapter wraps these into function_declarations (M2)
            else:  # scripted / ollama / generic
                specs.append(clean)
        return specs

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        """Dispatch by name with arg validation/coercion; never raises — wraps errors."""
        fn = self._tools.get(name)
        if fn is None:
            return ToolResult("text", f"tool error: unknown tool '{name}'", {}, error=True)
        spec = fn._tool_spec  # type: ignore[attr-defined]
        py_types = spec["_py_types"]
        required = spec["parameters"]["required"]
        missing = [r for r in required if r not in kwargs]
        if missing:
            return ToolResult(
                "text", f"tool error: {name} missing required args {missing}", {}, error=True
            )
        coerced = {k: _coerce(v, py_types.get(k, str)) for k, v in kwargs.items()}
        try:
            result = fn(**coerced)
        except Exception as exc:  # degrade, don't crash the loop
            return ToolResult("text", f"tool error: {name} raised {type(exc).__name__}: {exc}", {}, error=True)
        if result is None:
            return ToolResult(
                "text", f"tool error: {name} returned None (not implemented?)", {}, error=True
            )
        if not isinstance(result, ToolResult):
            return ToolResult("text", str(result), result)
        return result


# Module-level registry used by the notebooks.
REGISTRY = ToolRegistry()
