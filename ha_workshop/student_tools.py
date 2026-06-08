"""YOUR Module-3 tools. Edit THIS file (the notebook prints its exact path).

- query_steps is PREFILLED as a second worked example.
- query_screen_time and detect_change have small TODOs. Until you fill them they return a
  "TODO not implemented" result, so the agent will say it lacks evidence rather than make
  something up. Fill the TODO lines, then re-run the smoke-test cell in 03_designing_tools.ipynb.

Provided helpers (already imported): data.load_user_metric(...), and for detect_change the
window/series helpers _windows() and _series().
"""
from __future__ import annotations

from healthagent import data
from healthagent.catalog import CATALOG
from healthagent.llm.schemas import TODO_SENTINEL, ToolResult
from healthagent.tools.analysis import _series, _windows
from healthagent.tools.registry import tool


@tool
def query_steps(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily steps, active minutes and distance for a user over an inclusive date range. (PREFILLED example.)"""
    df = data.load_user_metric(user_id, "steps", ["steps", "active_minutes", "distance_km"], start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_steps = int(df["steps"].mean()) if len(df) else 0
    return ToolResult("table", f"{len(df)} days: mean {mean_steps} steps/day.", rows)


@tool
def query_screen_time(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily total and night-time (22:00-02:00) screen-time minutes for a user over an inclusive date range."""
    # === TODO-M3 (≈2 lines): load total_screen_minutes and night_screen_minutes for this
    #     user/date range, then return them. Hint:
    #   df = data.load_user_metric(user_id, "screen_time",
    #                              ["total_screen_minutes", "night_screen_minutes"], start_date, end_date)
    #   rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    #   return ToolResult("table", f"{len(df)} days: mean night screen "
    #                              f"{round(df['night_screen_minutes'].mean(),1)} min.", rows)
    return ToolResult("text", TODO_SENTINEL, {})
    # === END TODO-M3 ===


@tool
def detect_change(user_id: str, metric: str, recent_days: int = 7, baseline_days: int = 21) -> ToolResult:
    """Compare a metric's recent-window mean to its prior baseline-window mean; report delta, percent change, direction, and a significance flag."""
    r_start, r_end, b_start, b_end = _windows(recent_days, baseline_days)
    canonical, recent = _series(user_id, metric, r_start, r_end)
    _, base = _series(user_id, metric, b_start, b_end)
    if len(recent) == 0 or len(base) == 0:
        return ToolResult("text", f"tool error: no data for {canonical} in the requested windows", {}, error=True)

    # === TODO-M3 (exactly 2 lines): compute the two window means ===
    recent_mean = None    # TODO: float(recent.mean())
    baseline_mean = None  # TODO: float(base.mean())
    # === END TODO-M3 ===

    if recent_mean is None or baseline_mean is None:
        return ToolResult("text", TODO_SENTINEL, {})

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
