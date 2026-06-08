"""Reference solution for ha_workshop/student_tools.py (the M3 tool bodies, filled)."""
from __future__ import annotations

from healthagent import data
from healthagent.catalog import CATALOG
from healthagent.llm.schemas import ToolResult
from healthagent.tools.analysis import _series, _windows
from healthagent.tools.registry import tool


@tool
def query_steps(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily steps, active minutes and distance for a user over an inclusive date range."""
    df = data.load_user_metric(user_id, "steps", ["steps", "active_minutes", "distance_km"], start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_steps = int(df["steps"].mean()) if len(df) else 0
    return ToolResult("table", f"{len(df)} days: mean {mean_steps} steps/day.", rows)


@tool
def query_screen_time(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily total and night-time (22:00-02:00) screen-time minutes for a user over an inclusive date range."""
    df = data.load_user_metric(
        user_id, "screen_time", ["total_screen_minutes", "night_screen_minutes"], start_date, end_date
    )
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_night = round(df["night_screen_minutes"].mean(), 1) if len(df) else float("nan")
    return ToolResult("table", f"{len(df)} days: mean night screen {mean_night} min.", rows)


@tool
def detect_change(user_id: str, metric: str, recent_days: int = 7, baseline_days: int = 21) -> ToolResult:
    """Compare a metric's recent-window mean to its prior baseline-window mean; report delta, percent change, direction, and a significance flag."""
    r_start, r_end, b_start, b_end = _windows(recent_days, baseline_days)
    canonical, recent = _series(user_id, metric, r_start, r_end)
    _, base = _series(user_id, metric, b_start, b_end)
    if len(recent) == 0 or len(base) == 0:
        return ToolResult("text", f"tool error: no data for {canonical} in the requested windows", {}, error=True)

    recent_mean = float(recent.mean())
    baseline_mean = float(base.mean())

    delta = recent_mean - baseline_mean
    pct = (delta / baseline_mean * 100) if baseline_mean else float("nan")
    z = delta / (float(base.std()) or 1e-9)
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
    unit = CATALOG.unit_for(canonical)
    out = {
        "metric": canonical, "recent_mean": round(recent_mean, 2), "baseline_mean": round(baseline_mean, 2),
        "delta": round(delta, 2), "pct_change": round(pct, 1), "direction": direction,
        "significant": bool(abs(z) > 1.5), "unit": unit,
        "recent_window": [r_start, r_end], "baseline_window": [b_start, b_end],
    }
    sig = "significant" if out["significant"] else "not significant"
    return ToolResult(
        "text",
        f"{canonical} {direction} {out['pct_change']}% (recent {out['recent_mean']} vs "
        f"baseline {out['baseline_mean']} {unit}; {sig}).",
        out,
    )
