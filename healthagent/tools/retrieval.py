"""Retrieval tools — return daily records over an inclusive date range.

``query_sleep`` is the fully-worked reference shown complete in Module 3. The others are the
complete reference implementations; the Module-3 blanks (``query_screen_time``) and the
prefilled (``query_steps``) live in ``ha_workshop/`` for participants to edit.
"""
from __future__ import annotations

from .. import data
from ..llm.schemas import ToolResult
from .registry import tool


@tool
def query_sleep(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily sleep metrics (duration, efficiency, onset, awakenings) for a user over an inclusive date range."""
    cols = ["total_sleep_hours", "sleep_efficiency", "sleep_onset_hhmm", "awakenings"]
    df = data.load_user_metric(user_id, "sleep", cols, start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_h = round(df["total_sleep_hours"].mean(), 2) if len(df) else float("nan")
    eff = round(df["sleep_efficiency"].mean(), 3) if len(df) else float("nan")
    return ToolResult(
        kind="table",
        summary=f"{len(df)} nights {start_date}..{end_date}: mean sleep {mean_h} h, mean efficiency {eff}.",
        value=rows,
    )


@tool
def query_steps(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily steps, active minutes and distance for a user over an inclusive date range."""
    cols = ["steps", "active_minutes", "distance_km"]
    df = data.load_user_metric(user_id, "steps", cols, start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_steps = int(df["steps"].mean()) if len(df) else 0
    return ToolResult(
        kind="table",
        summary=f"{len(df)} days {start_date}..{end_date}: mean {mean_steps} steps/day.",
        value=rows,
    )


@tool
def query_screen_time(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily total and night-time (22:00-02:00) screen-time minutes for a user over an inclusive date range."""
    cols = ["total_screen_minutes", "night_screen_minutes", "pickups"]
    df = data.load_user_metric(user_id, "screen_time", cols, start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_night = round(df["night_screen_minutes"].mean(), 1) if len(df) else float("nan")
    return ToolResult(
        kind="table",
        summary=f"{len(df)} days {start_date}..{end_date}: mean night screen {mean_night} min.",
        value=rows,
    )


@tool
def query_heart_rate(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve daily resting/average heart rate and HRV for a user over an inclusive date range."""
    cols = ["resting_hr_bpm", "avg_hr_bpm", "hrv_rmssd_ms"]
    df = data.load_user_metric(user_id, "heart_rate", cols, start_date, end_date)
    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    mean_rhr = int(df["resting_hr_bpm"].mean()) if len(df) else 0
    return ToolResult(
        kind="table",
        summary=f"{len(df)} days {start_date}..{end_date}: mean resting HR {mean_rhr} bpm.",
        value=rows,
    )


@tool
def query_ema(user_id: str, start_date: str, end_date: str) -> ToolResult:
    """Retrieve EMA self-reports (mood, stress, energy, perceived sleep quality, free text) over an inclusive date range."""
    cols = ["mood", "stress", "energy", "perceived_sleep_quality", "free_text", "responded"]
    df = data.load_user_metric(user_id, "ema", cols, start_date, end_date)
    answered = df[df["responded"] == True]  # noqa: E712
    rows = answered.assign(date=answered["date"].dt.strftime("%Y-%m-%d")).to_dict("records")
    psq = round(answered["perceived_sleep_quality"].mean(), 1) if len(answered) else float("nan")
    notable = [r["free_text"] for r in rows if r.get("free_text")][:3]
    return ToolResult(
        kind="table",
        summary=f"{len(answered)} EMA responses {start_date}..{end_date}: mean perceived sleep quality {psq}; notes: {notable}.",
        value=rows,
    )
