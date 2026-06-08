"""Per-tool contract tests: exact return shapes + behavior on the committed data."""
import os

from healthagent import config
from healthagent.llm.schemas import ToolResult
from healthagent.tools import analysis, builtin, retrieval, visualization

R_START, R_END = config.recent_window()


def test_query_sleep_recent_week():
    r = retrieval.query_sleep("u01", R_START, R_END)
    assert isinstance(r, ToolResult) and r.kind == "table"
    assert len(r.value) == 7
    assert {"date", "total_sleep_hours"} <= set(r.value[0])


def test_query_screen_time_shape():
    r = retrieval.query_screen_time("u01", R_START, R_END)
    assert r.kind == "table" and "night_screen_minutes" in r.value[0]


def test_detect_change_night_screen_up_significant():
    r = analysis.detect_change("u01", "night_screen")
    assert r.kind == "text" and not r.error
    assert r.value["direction"] == "up" and r.value["significant"]


def test_detect_change_sleep_down():
    r = analysis.detect_change("u01", "sleep")
    assert r.value["direction"] == "down" and r.value["recent_mean"] < 6.0


def test_correlate_strong_negative():
    r = analysis.correlate_metrics("u01", "sleep", "night_screen")
    assert r.value["r"] < -0.5 and r.value["n"] == 28
    assert "not proof" in r.summary.lower()


def test_describe_metric():
    r = analysis.describe_metric("u01", "total_sleep_hours", R_START, R_END)
    assert r.value["n"] == 7 and r.value["unit"] == "hours"


def test_compare_window_activity_only():
    r = builtin.compare_window("u01")
    assert r.kind == "table"
    assert r.value["vs_goal"] == "below"
    assert 15 <= abs(r.value["pct_vs_goal"]) <= 30


def test_plot_timeseries_writes_png():
    r = visualization.plot_timeseries("u01", "night_screen", R_START, R_END)
    assert r.kind == "image" and os.path.exists(r.value)
    assert "mean" in r.summary
