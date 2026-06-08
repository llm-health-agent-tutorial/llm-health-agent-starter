"""Analysis tools — descriptive stats, change detection, correlation.

``describe_metric`` is the fully-worked reference shown in Module 3. ``detect_change`` is the
workhorse (its Module-3 blank asks only for the two means). ``correlate_metrics`` is the
advanced reference. All accept a flat string ``metric`` resolved via the MetricCatalog.
"""
from __future__ import annotations

from datetime import timedelta

import numpy as np

from .. import config, data
from ..catalog import CATALOG
from ..llm.schemas import ToolResult
from .registry import tool


def _windows(recent_days: int, baseline_days: int):
    """(recent_start, recent_end, base_start, base_end) ISO strings, relative to DEMO_TODAY."""
    end = config.DEMO_TODAY
    r_start = end - timedelta(days=recent_days - 1)
    b_end = r_start - timedelta(days=1)
    b_start = b_end - timedelta(days=baseline_days - 1)
    return r_start.isoformat(), end.isoformat(), b_start.isoformat(), b_end.isoformat()


def _series(user_id: str, metric: str, start: str, end: str):
    canonical = CATALOG.resolve(metric)
    table = CATALOG.table_for(canonical)
    df = data.load_user_metric(user_id, table, [canonical], start, end)
    return canonical, df[canonical].dropna()


@tool
def describe_metric(user_id: str, metric: str, start_date: str, end_date: str) -> ToolResult:
    """Compute descriptive statistics (n, mean, std, min, max, missing%) for one metric over a date range."""
    canonical, s = _series(user_id, metric, start_date, end_date)
    full = data.load_user_metric(user_id, CATALOG.table_for(canonical), [canonical], start_date, end_date)
    n = len(full)
    missing = round(100 * (n - len(s)) / n, 1) if n else 0.0
    stats = {
        "metric": canonical,
        "n": int(len(s)),
        "mean": round(float(s.mean()), 3) if len(s) else None,
        "std": round(float(s.std()), 3) if len(s) else None,
        "min": round(float(s.min()), 3) if len(s) else None,
        "max": round(float(s.max()), 3) if len(s) else None,
        "missing_pct": missing,
        "unit": CATALOG.unit_for(canonical),
    }
    return ToolResult(
        kind="text",
        summary=f"{canonical}: n={stats['n']}, mean={stats['mean']} {stats['unit']}, "
                f"range [{stats['min']}, {stats['max']}], missing {missing}%.",
        value=stats,
    )


@tool
def detect_change(user_id: str, metric: str, recent_days: int = 7, baseline_days: int = 21) -> ToolResult:
    """Compare a metric's recent-window mean to its prior baseline-window mean; report delta, percent change, direction, and a significance flag.

    Defaults (7 recent / 21 baseline) match the teaching dataset's structure.
    """
    r_start, r_end, b_start, b_end = _windows(recent_days, baseline_days)
    canonical, recent = _series(user_id, metric, r_start, r_end)
    _, base = _series(user_id, metric, b_start, b_end)
    if len(recent) == 0 or len(base) == 0:
        return ToolResult("text", f"tool error: no data for {canonical} in the requested windows", {}, error=True)
    recent_mean = float(recent.mean())
    baseline_mean = float(base.mean())
    delta = recent_mean - baseline_mean
    pct = (delta / baseline_mean * 100) if baseline_mean else float("nan")
    base_sd = float(base.std()) or 1e-9
    z = delta / base_sd
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
    out = {
        "metric": canonical,
        "recent_mean": round(recent_mean, 2),
        "baseline_mean": round(baseline_mean, 2),
        "delta": round(delta, 2),
        "pct_change": round(pct, 1),
        "direction": direction,
        "significant": bool(abs(z) > 1.5),
        "recent_window": [r_start, r_end],
        "baseline_window": [b_start, b_end],
        "unit": CATALOG.unit_for(canonical),
    }
    sig = "significant" if out["significant"] else "not significant"
    return ToolResult(
        kind="text",
        summary=f"{canonical} {direction} {out['pct_change']}% (recent {out['recent_mean']} vs "
                f"baseline {out['baseline_mean']} {out['unit']}; {sig}).",
        value=out,
    )


@tool
def correlate_metrics(
    user_id: str, metric_a: str, metric_b: str, recent_days: int = 7, baseline_days: int = 21
) -> ToolResult:
    """Pearson correlation between two metrics over the recent+baseline window (n is larger than the recent week alone, for stability). Returns r and a correlation-not-causation caveat."""
    r_start, r_end, b_start, _ = _windows(recent_days, baseline_days)
    ca = CATALOG.resolve(metric_a)
    cb = CATALOG.resolve(metric_b)
    da = data.load_user_metric(user_id, CATALOG.table_for(ca), [ca], b_start, r_end)
    db = data.load_user_metric(user_id, CATALOG.table_for(cb), [cb], b_start, r_end)
    merged = da.merge(db, on="date").dropna()
    if len(merged) < 3:
        return ToolResult("text", f"tool error: not enough overlapping data for {ca} vs {cb}", {}, error=True)
    r = float(np.corrcoef(merged[ca], merged[cb])[0, 1])
    strength = "strong" if abs(r) >= 0.6 else ("moderate" if abs(r) >= 0.3 else "weak")
    sign = "negative" if r < 0 else "positive"
    out = {"metric_a": ca, "metric_b": cb, "r": round(r, 2), "n": int(len(merged)),
           "interpretation": f"{strength} {sign} association"}
    return ToolResult(
        kind="text",
        summary=f"corr({ca}, {cb}) = {out['r']} over n={out['n']} days: {out['interpretation']}. "
                f"Association only — not proof of cause.",
        value=out,
    )
