"""Typed backend-availability errors so get_client can fall back (or report) precisely, and
ha-check can explain *why* a live backend isn't active (vs swallowing real bugs)."""
from __future__ import annotations


class BackendUnavailable(Exception):
    """Base: a live backend is configured-but-not-usable. Caught by get_client(allow_fallback=True)."""


class MissingSDK(BackendUnavailable):
    """The provider's Python SDK isn't installed (run `make live-install`)."""


class MissingCredential(BackendUnavailable):
    """No API key / credential for the provider."""


class ModelUnavailable(BackendUnavailable):
    """The configured model isn't reachable/pulled (e.g. `ollama pull <model>`)."""
