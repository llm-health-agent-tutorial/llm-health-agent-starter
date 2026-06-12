"""CLI behavior on the scripted floor: ha-chat / ha-eval / ha-data-check + the packaging guard."""
import inspect
import shutil
from pathlib import Path

import pandas as pd
import pytest

from healthagent import config
from healthagent.agent import reference
from healthagent.cli import chat, datacheck
from healthagent.cli import eval as ha_eval  # `eval` is a builtin — alias to avoid shadowing
from healthagent.llm.client import get_client
from healthagent.safety import probes

SHIP = config.PROCESSED


@pytest.fixture
def scripted():
    return get_client("scripted", quiet=True)


def _copy(tables, dest: Path) -> Path:
    proc = dest / "processed"
    proc.mkdir(parents=True)
    for t in tables:
        shutil.copy(SHIP / f"{t}.parquet", proc / f"{t}.parquet")
    return proc


# ---- ha-chat ----
def test_chat_once_grounded(scripted):
    ans = chat.chat_once("Why have I been sleeping poorly this week?", scripted)
    assert ans.grounded and ans.images  # grounded sleep answer + a rendered plot


# ---- ha-eval ----
def test_eval_scorecard_scripted(scripted):
    results = ha_eval.score(["scripted"])
    rows = results["scripted"]
    assert len(rows) == len(probes.PROBES)  # one row per probe (count-agnostic)
    assert all(r["passed"] for r in rows if r["expectation"] == "refuse")  # deterministic safety handling
    md = ha_eval.scorecard_md(results)
    assert "pass rate" in md and "scripted" in md


# ---- ha-data-check ----
def test_datacheck_shipped_pass():
    _, tools, ok = datacheck.check_dataset(SHIP)
    assert ok and "compare_window" in tools and "query_sleep" in tools


def test_datacheck_partial_pass(tmp_path):
    proc = _copy(["sleep", "steps", "users"], tmp_path)
    _, tools, ok = datacheck.check_dataset(proc)
    assert ok                                   # partial dataset is fine
    assert "compare_window" in tools            # steps + users present
    assert "query_screen_time" not in tools     # screen_time absent


def test_datacheck_malformed_fails(tmp_path):
    proc = tmp_path / "processed"
    proc.mkdir(parents=True)
    pd.read_parquet(SHIP / "sleep.parquet").drop(columns=["user_id"]).to_parquet(proc / "sleep.parquet")
    _, _, ok = datacheck.check_dataset(proc)
    assert not ok                               # present table missing its required key


def test_datacheck_requested_absent_fails(tmp_path):
    proc = _copy(["sleep"], tmp_path)           # steps absent
    _, _, ok = datacheck.check_dataset(proc, tables=["sleep", "steps"])
    assert not ok                               # a --tables-requested table must exist


def test_datacheck_steps_without_users_no_compare_window(tmp_path):
    proc = _copy(["steps"], tmp_path)
    _, tools, _ = datacheck.check_dataset(proc)
    assert "compare_window" not in tools        # compare_window needs BOTH steps and users


# ---- packaging guard ----
def test_clis_and_reference_never_import_ha_workshop():
    for mod in (chat, datacheck, ha_eval, reference):
        assert "ha_workshop" not in inspect.getsource(mod), mod.__name__
