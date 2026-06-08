"""@tool decorator + ToolRegistry.

Registering a tool with an LLM is a one-liner: ``REGISTRY.register(fn)`` (or ``@REGISTRY.tool``).
The decorator introspects the signature + type hints + docstring into a JSON schema, so
participants never hand-write provider JSON. ``call()`` validates/coerces LLM-supplied args
(the trust boundary) and wraps None/exceptions into a visible tool-error ToolResult so a bad
tool degrades rather than crashes the loop.
"""
from __future__ import annotations

import inspect
import re
from typing import Any, Callable, get_type_hints

from ..llm.schemas import ToolResult

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}
_METRIC_PARAMS = {"metric", "metric_a", "metric_b"}


def _parse_args_doc(doc: str) -> dict[str, str]:
    """Pull per-param descriptions from a Google-style ``Args:`` block (best-effort)."""
    out: dict[str, str] = {}
    m = re.search(r"\n\s*Args:\s*\n(.*?)(\n\s*\n|\Z)", doc, re.DOTALL)
    if not m:
        return out
    for line in m.group(1).splitlines():
        am = re.match(r"\s+(\w+)\s*:\s*(.+)", line)
        if am:
            out[am.group(1)] = am.group(2).strip()
    return out


def _metric_enum() -> list[str]:
    from ..catalog import CATALOG  # lazy to avoid import cycles

    names = set(CATALOG.metrics())
    for m in CATALOG.metrics():  # include accepted aliases so the model has the full vocabulary
        names.update(a for a in _aliases_of(m))
    return sorted(names)


def _aliases_of(metric: str) -> list[str]:
    from ..catalog import CATALOG

    return [a for a, canon in CATALOG._alias_to_metric.items() if canon == metric]  # noqa: SLF001


def _build_spec(fn: Callable) -> dict:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    doc = inspect.getdoc(fn) or ""
    param_docs = _parse_args_doc(doc)
    props: dict[str, dict] = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        py_t = hints.get(name, str)
        json_t = _PY_TO_JSON.get(py_t, "string")
        prop: dict[str, Any] = {"type": json_t}
        if name in param_docs:
            prop["description"] = param_docs[name]
        if name in _METRIC_PARAMS:
            try:
                prop["enum"] = _metric_enum()
            except Exception:  # noqa: BLE001 - catalog optional at schema-build time
                pass
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default
        props[name] = prop
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
            params = {k: v for k, v in s["parameters"].items() if k != "_py_types"}
            clean = {"name": s["name"], "description": s["description"], "parameters": params}
            if provider in {"openai", "ollama"}:
                # OpenAI-style tools list; both OpenAI and Ollama accept it. additionalProperties:
                # false rejects unknown args (defense-in-depth; the registry strips them anyway).
                fn_params = {**params, "additionalProperties": False}
                specs.append({"type": "function", "function": {**clean, "parameters": fn_params}})
            else:  # scripted / gemini / generic — bare declaration (gemini adapter wraps it)
                specs.append(clean)
        return specs

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        """Dispatch by name; strip unknown kwargs at the trust boundary (recording them), coerce
        types, and wrap None/exceptions. Never raises — a bad tool degrades the loop, not crashes it."""
        fn = self._tools.get(name)
        if fn is None:
            return ToolResult("text", f"tool error: unknown tool '{name}'", {}, error=True)
        spec = fn._tool_spec  # type: ignore[attr-defined]
        py_types = spec["_py_types"]
        declared = set(spec["parameters"]["properties"])
        # Trust boundary: drop args the tool doesn't declare (a stray LLM arg must not raise a
        # TypeError tool-error or run the tool on bad input); record them for auditability.
        dropped = sorted(k for k in kwargs if k not in declared)
        kwargs = {k: v for k, v in kwargs.items() if k in declared}
        required = spec["parameters"]["required"]
        missing = [r for r in required if r not in kwargs]
        if missing:
            return ToolResult(
                "text", f"tool error: {name} missing required args {missing}", {}, error=True,
                dropped_args=dropped,
            )
        coerced = {k: _coerce(v, py_types.get(k, str)) for k, v in kwargs.items()}
        try:
            result = fn(**coerced)
        except Exception as exc:  # degrade, don't crash the loop
            return ToolResult("text", f"tool error: {name} raised {type(exc).__name__}: {exc}", {},
                              error=True, dropped_args=dropped)
        if result is None:
            return ToolResult(
                "text", f"tool error: {name} returned None (not implemented?)", {}, error=True,
                dropped_args=dropped,
            )
        if not isinstance(result, ToolResult):
            result = ToolResult("text", str(result), result)
        result.dropped_args = dropped
        return result


# Module-level registry used by the notebooks.
REGISTRY = ToolRegistry()
