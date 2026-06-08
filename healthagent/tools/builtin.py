"""The prebuilt baseline tool wired into the shipped agent at Module-4 start.

``compare_window`` covers ONLY the activity-vs-goal question, so the agent answers
"How does my activity compare to my goal?" out of the box, while the sleep question still
requires the tools participants register in TODO-1 (giving that step a visible effect).
"""
from __future__ import annotations

from datetime import timedelta

from .. import config, data
from ..llm.schemas import ToolResult
from .registry import tool


@tool
def compare_window(user_id: str = "u01", recent_days: int = 7) -> ToolResult:
    """Compare a user's recent average daily steps to their step goal and to their prior baseline. Answers the activity-vs-goal question out of the box."""
    end = config.DEMO_TODAY
    r_start = end - timedelta(days=recent_days - 1)
    b_end = r_start - timedelta(days=1)
    b_start = b_end - timedelta(days=config.BASELINE_DAYS - 1)

    recent = data.load_user_metric(user_id, "steps", ["steps"], r_start.isoformat(), end.isoformat())["steps"]
    base = data.load_user_metric(user_id, "steps", ["steps"], b_start.isoformat(), b_end.isoformat())["steps"]
    users = data.load_table("users")
    goal_row = users[users["user_id"] == user_id]
    goal = int(goal_row["steps_goal"].iloc[0]) if len(goal_row) else 8000

    if len(recent) == 0:
        return ToolResult("text", f"tool error: no recent steps for {user_id}", {}, error=True)
    recent_mean = float(recent.mean())
    baseline_mean = float(base.mean()) if len(base) else float("nan")
    gap = (recent_mean - goal) / goal * 100
    vs_goal = "below" if gap < 0 else "above"
    out = {
        "recent_avg_steps": int(recent_mean),
        "steps_goal": goal,
        "pct_vs_goal": round(gap, 1),
        "vs_goal": vs_goal,
        "baseline_avg_steps": int(baseline_mean) if baseline_mean == baseline_mean else None,
        "recent_window": [r_start.isoformat(), end.isoformat()],
    }
    return ToolResult(
        kind="table",
        summary=f"Activity: recent avg {out['recent_avg_steps']} steps/day is {abs(out['pct_vs_goal'])}% "
                f"{vs_goal} the goal of {goal} (baseline avg {out['baseline_avg_steps']}).",
        value=out,
    )
