"""CI guard: schema matches the codebook and the embedded teaching signal still holds."""
import csv

import numpy as np
import pandas as pd
import pytest

from healthagent import config, data


@pytest.fixture(scope="module")
def tables():
    return data.load_dataset()


def test_shape(tables):
    assert len(tables["users"]) == config.N_USERS if hasattr(config, "N_USERS") else True
    for name in ("sleep", "steps", "screen_time", "heart_rate"):
        assert len(tables[name]) == 12 * 112
    assert len(tables["users"]) == 12


def test_codebook_columns_exist(tables):
    with open(config.CODEBOOK, newline="") as fh:
        for row in csv.DictReader(fh):
            assert row["metric"] in tables[row["table"]].columns, row["metric"]


def _u01(df):
    d = df[df.user_id == "u01"].copy()
    d["date"] = pd.to_datetime(d["date"])
    return d.sort_values("date")


def test_night_screen_spike(tables):
    sc = _u01(tables["screen_time"])
    r_lo = sc.date.max() - pd.Timedelta(days=6)
    b_lo = r_lo - pd.Timedelta(days=21)
    recent = sc[sc.date >= r_lo]["night_screen_minutes"].mean()
    base = sc[(sc.date >= b_lo) & (sc.date < r_lo)]["night_screen_minutes"].mean()
    assert recent / base > 5.0


def test_recent_sleep_low(tables):
    s = _u01(tables["sleep"])
    r_lo = s.date.max() - pd.Timedelta(days=6)
    assert s[s.date >= r_lo]["total_sleep_hours"].mean() < 6.0


def test_correlation_on_28_day_window(tables):
    s, sc = _u01(tables["sleep"]), _u01(tables["screen_time"])
    r_lo = s.date.max() - pd.Timedelta(days=6)
    b_lo = r_lo - pd.Timedelta(days=21)
    win = s[s.date >= b_lo][["date", "total_sleep_hours"]].merge(
        sc[sc.date >= b_lo][["date", "night_screen_minutes"]], on="date"
    )
    r = np.corrcoef(win.total_sleep_hours, win.night_screen_minutes)[0, 1]
    assert len(win) == 28
    assert r < -0.5


def test_steps_gap(tables):
    stp = _u01(tables["steps"])
    goal = int(tables["users"].set_index("user_id").loc["u01", "steps_goal"])
    r_lo = stp.date.max() - pd.Timedelta(days=6)
    gap = (goal - stp[stp.date >= r_lo]["steps"].mean()) / goal
    assert 0.15 <= gap <= 0.30


def test_non_causes_flat(tables):
    """Plausible non-drivers must stay within ~1 SD of baseline in the recent window."""
    hr = _u01(tables["heart_rate"])
    r_lo = hr.date.max() - pd.Timedelta(days=6)
    b_lo = r_lo - pd.Timedelta(days=21)
    for df, col in [(hr, "resting_hr_bpm"), (hr, "hrv_rmssd_ms")]:
        base = df[(df.date >= b_lo) & (df.date < r_lo)][col]
        recent = df[df.date >= r_lo][col]
        assert abs(recent.mean() - base.mean()) / (base.std() + 1e-9) < 1.0, col
