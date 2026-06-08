"""ha-check is local-only: fake cloud keys must not trigger a network call, and the backend row
reports configured-not-verified (with the typed fallback reason when it falls back)."""
import contextlib

from healthagent import verify
from healthagent.llm import client as C


@contextlib.contextmanager
def _no_network():
    """Make socket creation raise, so any real network attempt fails loudly."""
    import socket

    real = socket.socket

    def boom(*a, **k):
        raise AssertionError("ha-check made a network call")

    socket.socket = boom
    try:
        yield
    finally:
        socket.socket = real


def test_backend_row_no_network_with_fake_keys(monkeypatch):
    monkeypatch.setenv("HA_BACKEND", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)  # clear BOTH gemini aliases (dev .env may set either)
    with _no_network():
        ok, detail = verify._check_backend()
    assert ok  # the scripted floor never fails the gate
    # configured (key present) but not network-verified
    assert "openai" in detail.lower()
    assert "not checked offline" in detail.lower()


def test_get_client_openai_constructs_without_network(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    with _no_network():
        c = C.get_client("openai", allow_fallback=False, quiet=True)
    assert c.provider == "openai"  # constructed (no network at construction)
