"""get_client fallback semantics (no network). Typed availability errors fall back when allowed
and raise when not; unexpected adapter bugs always propagate; SDK hidden via an import hook."""
import builtins
import contextlib

import pytest

from healthagent.llm import client as C
from healthagent.llm.errors import MissingCredential, MissingSDK


@contextlib.contextmanager
def _hide_modules(*names):
    """Make `import <name>` raise ImportError even though the package is installed (sys.modules
    deletion alone can't prevent reimport)."""
    blocked = set(names)
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        top = name.split(".")[0]
        if name in blocked or top in blocked:
            raise ImportError(f"blocked: {name}")
        return real_import(name, *a, **k)

    builtins.__import__ = fake_import
    try:
        yield
    finally:
        builtins.__import__ = real_import


def test_scripted_is_scripted():
    assert C.get_client("scripted", quiet=True).provider == "scripted"


def test_missing_credential(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("HA_BACKEND", raising=False)
    fb = C.get_client("openai", allow_fallback=True, quiet=True)
    assert fb.provider == "scripted" and "MissingCredential" in (fb.fallback_reason or "")
    with pytest.raises(MissingCredential):
        C.get_client("openai", allow_fallback=False, quiet=True)


def test_missing_sdk_import_hook(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")  # key present, but SDK "missing"
    with _hide_modules("openai"):
        fb = C.get_client("openai", allow_fallback=True, quiet=True)
        assert fb.provider == "scripted" and "MissingSDK" in (fb.fallback_reason or "")
        with pytest.raises(MissingSDK):
            C.get_client("openai", allow_fallback=False, quiet=True)


def test_unexpected_bug_propagates(monkeypatch):
    import healthagent.llm.openai_client as oc

    def boom():
        raise ValueError("adapter bug")

    monkeypatch.setattr(oc, "OpenAIBackend", boom)
    with pytest.raises(ValueError):  # NOT swallowed as scripted fallback
        C.get_client("openai", allow_fallback=True, quiet=True)
