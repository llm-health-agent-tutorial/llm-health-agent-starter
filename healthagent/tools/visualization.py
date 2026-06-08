"""Visualization tools — save a PNG and return an image reference PLUS a numeric summary, so a
figure genuinely grounds the answer (the LLM cites the summary, not just a file path).

``plot_timeseries`` is the worked reference; ``plot_two_metrics`` is the advanced reference.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: no display needed in the workshop / CI
import matplotlib.pyplot as plt  # noqa: E402

from .. import config, data  # noqa: E402
from ..catalog import CATALOG  # noqa: E402
from ..llm.schemas import ToolResult  # noqa: E402
from .registry import tool  # noqa: E402


def _fig_path(name: str) -> str:
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    return str(config.FIGURES / name)


@tool
def plot_timeseries(user_id: str, metric: str, start_date: str, end_date: str) -> ToolResult:
    """Plot one metric over a date range; save a PNG and return its path plus a numeric summary (min/max/mean/last)."""
    canonical = CATALOG.resolve(metric)
    table = CATALOG.table_for(canonical)
    df = data.load_user_metric(user_id, table, [canonical], start_date, end_date).dropna()
    if df.empty:
        return ToolResult("text", f"tool error: no data to plot for {canonical}", {}, error=True)
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(df["date"], df[canonical], marker="o", ms=3)
    ax.set_title(f"{user_id}: {canonical}")
    ax.set_ylabel(CATALOG.unit_for(canonical))
    fig.autofmt_xdate()
    fig.tight_layout()
    path = _fig_path(f"{user_id}_{canonical}_{start_date}_{end_date}.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    s = df[canonical]
    summary = {"metric": canonical, "min": round(float(s.min()), 2), "max": round(float(s.max()), 2),
               "mean": round(float(s.mean()), 2), "last": round(float(s.iloc[-1]), 2), "n": int(len(s))}
    return ToolResult(
        kind="image",
        summary=f"Plotted {canonical} ({summary['n']} pts): mean {summary['mean']}, "
                f"range [{summary['min']}, {summary['max']}], last {summary['last']} {CATALOG.unit_for(canonical)}.",
        value=path,
    )


@tool
def plot_two_metrics(
    user_id: str, metric_a: str, metric_b: str, start_date: str, end_date: str
) -> ToolResult:
    """Dual-axis overlay of two metrics over a date range; save a PNG and return its path, a paired numeric summary, and the observed direction of co-movement."""
    ca, cb = CATALOG.resolve(metric_a), CATALOG.resolve(metric_b)
    da = data.load_user_metric(user_id, CATALOG.table_for(ca), [ca], start_date, end_date)
    db = data.load_user_metric(user_id, CATALOG.table_for(cb), [cb], start_date, end_date)
    m = da.merge(db, on="date").dropna()
    if m.empty:
        return ToolResult("text", f"tool error: no overlapping data to plot for {ca}/{cb}", {}, error=True)
    fig, ax1 = plt.subplots(figsize=(7, 3))
    ax2 = ax1.twinx()
    ax1.plot(m["date"], m[ca], color="tab:blue", marker="o", ms=3, label=ca)
    ax2.plot(m["date"], m[cb], color="tab:red", marker="s", ms=3, label=cb)
    ax1.set_ylabel(ca, color="tab:blue")
    ax2.set_ylabel(cb, color="tab:red")
    ax1.set_title(f"{user_id}: {ca} vs {cb}")
    fig.autofmt_xdate()
    fig.tight_layout()
    path = _fig_path(f"{user_id}_{ca}_vs_{cb}_{start_date}_{end_date}.png")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    import numpy as np

    r = float(np.corrcoef(m[ca], m[cb])[0, 1]) if len(m) > 2 else float("nan")
    co = "opposite directions" if r < 0 else "the same direction"
    return ToolResult(
        kind="image",
        summary=f"Overlaid {ca} and {cb} (n={len(m)}); they move in {co} (r={round(r, 2)}). Association only.",
        value=path,
    )
