"""Notebook regression (opt-in: HA_TEST_NOTEBOOKS=1). Executes the four core notebooks headless
with FAKE live keys set and HA_TRY_LIVE unset, proving:
- the core cells run on the deterministic `scripted` backend (no key/network needed), and
- the optional 'try live' cell is gated off (prints "Skipping ..."), so nbconvert never hits the
  network even though OPENAI_API_KEY / GEMINI_API_KEY look configured.

Opt-in so the fast core matrix (`pytest -m "not provider_contract"`) stays quick and kernel-flake
free; a dedicated CI step sets HA_TEST_NOTEBOOKS=1. Skips cleanly if nbconvert/nbformat are absent.
"""
import os
import sys
from pathlib import Path

import pytest

if os.getenv("HA_TEST_NOTEBOOKS") != "1":
    pytest.skip("set HA_TEST_NOTEBOOKS=1 to run the notebook regression", allow_module_level=True)

nbformat = pytest.importorskip("nbformat")
ep_mod = pytest.importorskip("nbconvert.preprocessors")

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
CORE_NOTEBOOKS = ["00_preflight.ipynb", "02_setting_up.ipynb",
                  "04_wiring_the_agent.ipynb", "05_eval_safety.ipynb"]


@pytest.fixture(autouse=True)
def _fake_live_env(monkeypatch):
    # The kernel subprocess inherits this env. Prepend the venv bin dir so the `python3`
    # kernelspec's bare `python` resolves to THIS interpreter (the one with healthagent installed).
    monkeypatch.setenv("PATH", os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("HA_BACKEND", "auto")            # auto is configured ...
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")     # ... and keys LOOK present ...
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.delenv("HA_TRY_LIVE", raising=False)    # ... but the live cell stays gated off


@pytest.mark.parametrize("name", CORE_NOTEBOOKS)
def test_core_notebook_runs_on_scripted(name):
    nb = nbformat.read(NB_DIR / name, as_version=4)
    ep = ep_mod.ExecutePreprocessor(timeout=300, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(NB_DIR)}})  # raises if any cell errors

    texts = []
    for cell in nb.cells:
        for out in cell.get("outputs", []):
            texts.append(out.get("text") or "")
            data = out.get("data", {})
            if isinstance(data, dict):
                texts.append(str(data.get("text/plain", "")))
    blob = "\n".join(texts)
    assert "Skipping live backend cell" in blob, f"{name}: optional live cell was not gated off"
    assert "Traceback" not in blob, f"{name}: a cell raised"
