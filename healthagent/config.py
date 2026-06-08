"""Paths, constants, and backend resolution. Single source of truth at runtime."""
from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Repo root = parent of the healthagent package directory.
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROCESSED = DATA_DIR / "processed"
CODEBOOK = DATA_DIR / "codebook.csv"
GOLDEN = DATA_DIR / "golden"
CACHE = ROOT / "cache"
FIGURES = CACHE / "figures"

load_dotenv(ROOT / ".env")

# Dataset epoch + windows (mirror data/generate_dataset.py).
SEED = 2026
DEMO_USER = "u01"
DEMO_TODAY = date(2026, 6, 5)          # fixed dataset epoch; "the final week of the dataset"
RECENT_DAYS = 7
BASELINE_DAYS = 21

TABLES = (
    "users", "sleep", "heart_rate", "heart_rate_hourly",
    "steps", "location", "screen_time", "ema", "context",
)


def recent_window() -> tuple[str, str]:
    """(start, end) ISO strings for the dataset's final RECENT_DAYS days, inclusive."""
    end = DEMO_TODAY
    start = end - timedelta(days=RECENT_DAYS - 1)
    return start.isoformat(), end.isoformat()


def baseline_window() -> tuple[str, str]:
    """(start, end) ISO strings for the BASELINE_DAYS window immediately before the recent week."""
    r_start = DEMO_TODAY - timedelta(days=RECENT_DAYS - 1)
    b_end = r_start - timedelta(days=1)
    b_start = b_end - timedelta(days=BASELINE_DAYS - 1)
    return b_start.isoformat(), b_end.isoformat()


def dataset_today() -> str:
    return DEMO_TODAY.isoformat()


def resolve_backend() -> str:
    """Desired backend tier. Order: explicit env > Gemini key > OpenAI key > Ollama > scripted.

    Milestone 1 only implements ``scripted``; the live adapters arrive in Milestone 2.
    ``get_client`` falls back to ``scripted`` (with a banner) if a desired live adapter is
    not yet available, so the offline tier is always the floor.
    """
    explicit = os.getenv("HA_BACKEND", "").strip().lower()
    if explicit:
        return explicit
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if _ollama_reachable():
        return "ollama"
    return "scripted"


def _ollama_reachable(host: str | None = None) -> bool:
    host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        import urllib.request

        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=0.4) as r:
            return r.status == 200
    except Exception:
        return False
