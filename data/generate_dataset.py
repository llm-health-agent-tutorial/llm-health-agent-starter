"""Deterministic synthesizer for the tutorial teaching dataset.

Synthetic, de-identified, GLOBEM/RAPIDS-inspired. Run offline by organizers; the
parquet + CSV output is COMMITTED to the repo (never generated in the room). CI
re-runs this and checks the embedded teaching signal still holds.

Honesty note: the dataset deliberately seeds a single discoverable DRIVER in demo
user u01's final week (night screen-time up -> sleep worse, non-drivers held flat).
This is a teaching device and is disclosed in data/DATA_CARD.md. Participant-facing
code must describe findings as "the most plausible contributor in this synthetic
dataset", never as proven cause.

Usage:  python data/generate_dataset.py        (writes data/processed/*.{parquet,csv})
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (single source of truth; mirrored in healthagent/config.py)
# ---------------------------------------------------------------------------
SEED = 2026
DEMO_TODAY = date(2026, 6, 5)        # Friday; dataset epoch ("the final week of the dataset")
N_DAYS = 112                          # 16 weeks
N_USERS = 12
DEMO_USER = "u01"
RECENT_DAYS = 7                       # "this/final week"
BASELINE_DAYS = 21                    # prior 3 weeks (change-detection baseline)
NIGHT_SCREEN_BASELINE = 15.0          # minutes (22:00-02:00)
STEPS_GOALS = [6000, 8000, 10000]

HERE = Path(__file__).resolve().parent
OUT = HERE / "processed"

CHRONOTYPES = ["early", "intermediate", "late"]
AGE_BANDS = ["18-24", "25-34", "35-44", "45-54"]
SEXES = ["F", "M", "nonbinary"]
WEATHER = ["clear", "cloudy", "rain", "hot", "cold"]
EMA_PHRASES_GOOD = ["slept fine", "decent day", "felt rested", "normal day", "pretty good"]
EMA_PHRASES_POOR = [
    "scrolling late again",
    "couldn't put my phone down",
    "up late on my phone, exhausted",
    "deadline crunch, barely slept",
    "wired and tired",
]


def _dates() -> list[date]:
    start = DEMO_TODAY - timedelta(days=N_DAYS - 1)
    return [start + timedelta(days=i) for i in range(N_DAYS)]


def _rng(user_index: int) -> np.random.Generator:
    return np.random.default_rng(SEED + user_index)


def _ar1(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    """Zero-mean AR(1) noise series for day-to-day autocorrelation."""
    e = rng.normal(0.0, sigma, n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + e[i]
    return out


def _user_traits(uid_index: int, steps_goal: int, rng: np.random.Generator) -> dict:
    chrono = CHRONOTYPES[uid_index % 3]
    onset_shift = {"early": -0.6, "intermediate": 0.0, "late": 0.7}[chrono]
    sleep_goal = float(np.clip(rng.normal(7.5, 0.4), 6.5, 8.5))
    return {
        "chronotype": chrono,
        "onset_shift": onset_shift,
        "sleep_goal_hours": round(sleep_goal, 1),
        "base_onset": 23.0 + onset_shift,                     # decimal hour
        "baseline_sleep_hours": float(np.clip(rng.normal(sleep_goal, 0.6), 5.5, 9.0)),
        "baseline_night_screen": float(np.clip(rng.normal(NIGHT_SCREEN_BASELINE, 5), 9, 32)),
        "baseline_resting_hr": float(np.clip(rng.normal(60, 4), 48, 78)),
        "baseline_hrv": float(np.clip(rng.normal(55, 10), 25, 95)),
        "baseline_steps": float(max(1500, rng.normal(steps_goal * 0.95, 1200))),
    }


def _maybe_impute(rng: np.random.Generator, n: int, rate: float = 0.08) -> np.ndarray:
    """Boolean mask of user-days flagged is_imputed (a single field nudged/NaN-able)."""
    return rng.random(n) < rate


def build() -> dict[str, pd.DataFrame]:
    dates = _dates()
    idx = pd.to_datetime(dates)
    dow = idx.day_name().tolist()
    is_weekend = np.array([d.weekday() >= 5 for d in dates])

    users_rows = []
    sleep, hr, hr_hourly, steps, loc, screen, ema, context = [], [], [], [], [], [], [], []

    for u in range(N_USERS):
        uid = f"u{u + 1:02d}"
        rng = _rng(u)
        steps_goal = 8000 if uid == DEMO_USER else int(rng.choice(STEPS_GOALS))
        t = _user_traits(u, steps_goal, rng)
        enrolled = dates[0] - timedelta(days=int(rng.integers(1, 30)))
        users_rows.append({
            "user_id": uid,
            "age_band": AGE_BANDS[u % len(AGE_BANDS)],
            "sex": SEXES[u % len(SEXES)],
            "chronotype": t["chronotype"],
            "sleep_goal_hours": t["sleep_goal_hours"],
            "steps_goal": steps_goal,
            "enrolled_on": enrolled.isoformat(),
        })

        # --- baseline daily series (before the seeded driver) ---
        weekend_screen_bump = np.where(is_weekend, 6.0, 0.0)
        night_screen = (
            t["baseline_night_screen"]
            + weekend_screen_bump
            + _ar1(rng, N_DAYS, 0.3, 4.0)
        ).clip(min=0)

        # caffeine / events (context) -- a seeded confound for the M5 discussion
        caffeine = rng.random(N_DAYS) < 0.18
        event = np.array([""] * N_DAYS, dtype=object)

        # === SEEDED DRIVER: demo user u01, final 7 days only ===
        if uid == DEMO_USER:
            recent = slice(N_DAYS - RECENT_DAYS, N_DAYS)
            night_screen[recent] = rng.normal(95.0, 12.0, RECENT_DAYS).clip(min=40)
            event[recent] = "deadline"
            caffeine[recent] = caffeine[N_DAYS - 2 * RECENT_DAYS:N_DAYS - RECENT_DAYS]  # held at baseline level

        # --- sleep: causally downstream of night_screen (structural eqs before noise) ---
        base_onset = t["base_onset"] + np.where(is_weekend, 0.4, 0.0)
        sleep_onset = base_onset + 0.018 * (night_screen - NIGHT_SCREEN_BASELINE) + _ar1(rng, N_DAYS, 0.3, 0.2)
        total_sleep = (
            t["baseline_sleep_hours"]
            - 0.02 * (night_screen - NIGHT_SCREEN_BASELINE)
            + _ar1(rng, N_DAYS, 0.3, 0.25)
        ).clip(3.5, 10.0)
        efficiency = (0.90 - 0.0015 * (night_screen - NIGHT_SCREEN_BASELINE) + rng.normal(0, 0.02, N_DAYS)).clip(0.6, 0.99)
        awakenings = np.maximum(0, np.round(1.5 + 0.03 * (night_screen - NIGHT_SCREEN_BASELINE) + rng.normal(0, 0.6, N_DAYS))).astype(int)
        deep_pct = (0.18 + rng.normal(0, 0.02, N_DAYS)).clip(0.08, 0.30)
        rem_pct = (0.22 + rng.normal(0, 0.02, N_DAYS)).clip(0.10, 0.32)
        wake = sleep_onset + total_sleep
        s_imp = _maybe_impute(rng, N_DAYS)

        # --- non-driver modalities: held at baseline (esp. for u01 recent week) ---
        resting_hr = (t["baseline_resting_hr"] + _ar1(rng, N_DAYS, 0.3, 1.5)).round().astype(int)
        avg_hr = (resting_hr + rng.normal(18, 3, N_DAYS)).round().astype(int)
        max_hr = (avg_hr + rng.normal(45, 8, N_DAYS)).round().astype(int)
        hrv = (t["baseline_hrv"] + _ar1(rng, N_DAYS, 0.3, 4.0)).clip(15, 120).round(1)

        steps_series = (t["baseline_steps"] + _ar1(rng, N_DAYS, 0.3, 1500)).clip(min=500)
        # secondary seeded pattern: u01 under-steps its goal in the final week
        if uid == DEMO_USER:
            recent = slice(N_DAYS - RECENT_DAYS, N_DAYS)
            under = rng.normal(6200, 350, RECENT_DAYS)
            under[[d.weekday() >= 5 for d in dates[N_DAYS - RECENT_DAYS:]]] *= 0.85  # weekends worst
            steps_series[recent] = under
        steps_series = steps_series.round().astype(int)
        active_min = (steps_series / 110.0 + rng.normal(0, 5, N_DAYS)).clip(5, 240).round().astype(int)
        sedentary_min = (720 - active_min + rng.normal(0, 20, N_DAYS)).clip(300, 900).round().astype(int)
        distance_km = (steps_series * 0.00075 + rng.normal(0, 0.2, N_DAYS)).clip(0.1, None).round(2)
        floors = rng.integers(2, 20, N_DAYS)

        st_imp = _maybe_impute(rng, N_DAYS)
        total_screen = (night_screen + rng.normal(250, 40, N_DAYS)).clip(60, 700).round().astype(int)
        pickups = (total_screen / 6.0 + rng.normal(0, 8, N_DAYS)).clip(10, 200).round().astype(int)
        social_min = (total_screen * 0.4 + rng.normal(0, 15, N_DAYS)).clip(5, None).round().astype(int)
        first_use = (7.0 + rng.normal(0, 0.6, N_DAYS)).clip(4, 11).round(1)
        last_use = (sleep_onset - 0.1 + rng.normal(0, 0.2, N_DAYS)).clip(20, 27).round(1)

        l_imp = _maybe_impute(rng, N_DAYS)
        home_hours = (np.where(is_weekend, 18.0, 14.0) + rng.normal(0, 1.5, N_DAYS)).clip(6, 24).round(1)
        n_places = (np.where(is_weekend, 2, 4) + rng.integers(-1, 3, N_DAYS)).clip(1, 9)
        entropy = (1.2 - 0.04 * (home_hours - 14) + rng.normal(0, 0.15, N_DAYS)).clip(0.1, 2.2).round(2)
        loc_dist = (n_places * 1.8 + rng.normal(0, 1.0, N_DAYS)).clip(0.2, None).round(2)

        hr_imp = _maybe_impute(rng, N_DAYS)

        for i, d in enumerate(dates):
            ds = d.isoformat()
            sleep.append({
                "user_id": uid, "date": ds,
                "sleep_onset_hhmm": round(float(sleep_onset[i]), 2),
                "wake_hhmm": round(float(wake[i]), 2),
                "total_sleep_hours": round(float(total_sleep[i]), 2),
                "sleep_efficiency": round(float(efficiency[i]), 3),
                "awakenings": int(awakenings[i]),
                "deep_pct": round(float(deep_pct[i]), 3),
                "rem_pct": round(float(rem_pct[i]), 3),
                "is_imputed": bool(s_imp[i]),
                "f_slp:duration": round(float(total_sleep[i]), 2),
                "f_slp:efficiency": round(float(efficiency[i]), 3),
            })
            hr.append({
                "user_id": uid, "date": ds,
                "resting_hr_bpm": int(resting_hr[i]), "avg_hr_bpm": int(avg_hr[i]),
                "max_hr_bpm": int(max_hr[i]), "hrv_rmssd_ms": float(hrv[i]),
                "is_imputed": bool(hr_imp[i]),
            })
            steps.append({
                "user_id": uid, "date": ds,
                "steps": int(steps_series[i]), "active_minutes": int(active_min[i]),
                "sedentary_minutes": int(sedentary_min[i]), "distance_km": float(distance_km[i]),
                "floors": int(floors[i]), "is_imputed": bool(st_imp[i]),
                "f_steps:count": int(steps_series[i]),
            })
            loc.append({
                "user_id": uid, "date": ds,
                "time_at_home_hours": float(home_hours[i]), "num_places_visited": int(n_places[i]),
                "location_entropy": float(entropy[i]), "total_distance_km": float(loc_dist[i]),
                "is_imputed": bool(l_imp[i]),
                "f_loc:home_hours": float(home_hours[i]), "f_loc:entropy": float(entropy[i]),
            })
            screen.append({
                "user_id": uid, "date": ds,
                "total_screen_minutes": int(total_screen[i]),
                "night_screen_minutes": int(round(float(night_screen[i]))),
                "pickups": int(pickups[i]), "social_app_minutes": int(social_min[i]),
                "first_use_hhmm": float(first_use[i]), "last_use_hhmm": float(last_use[i]),
                "is_imputed": bool(st_imp[i]),
                "f_screen:total": int(total_screen[i]), "f_screen:night": int(round(float(night_screen[i]))),
            })
            context.append({
                "user_id": uid, "date": ds, "day_of_week": dow[i],
                "is_weekend": bool(is_weekend[i]), "is_workday": bool(not is_weekend[i]),
                "weather": WEATHER[(u + i) % len(WEATHER)],
                "caffeine_after_6pm": bool(caffeine[i]),
                "event": (str(event[i]) if event[i] else None),
            })
            # EMA ~75% response; poorer mood/energy/sleep-quality when night_screen high
            if rng.random() < 0.75:
                stress_up = 1 if night_screen[i] > 60 else 0
                psq = int(np.clip(round(5 - 0.03 * (night_screen[i] - NIGHT_SCREEN_BASELINE) + rng.normal(0, 0.4)), 1, 5))
                mood = int(np.clip(round(4 - 0.02 * (night_screen[i] - NIGHT_SCREEN_BASELINE) + rng.normal(0, 0.5)), 1, 5))
                energy = int(np.clip(round(4 - 0.02 * (night_screen[i] - NIGHT_SCREEN_BASELINE) + rng.normal(0, 0.5)), 1, 5))
                stress = int(np.clip(round(2 + stress_up + rng.normal(0, 0.5)), 1, 5))
                poor = night_screen[i] > 55
                phrase = str(rng.choice(EMA_PHRASES_POOR if poor else EMA_PHRASES_GOOD))
                ema.append({
                    "user_id": uid, "date": ds,
                    "prompt_hhmm": round(float(20 + rng.normal(0, 0.5)), 2),
                    "mood": mood, "stress": stress, "energy": energy,
                    "perceived_sleep_quality": psq,
                    "phq2_score": int(np.clip(round(rng.normal(1.2, 1.0) + (1 if poor else 0)), 0, 6)),
                    "free_text": phrase, "responded": True,
                })
            else:
                ema.append({
                    "user_id": uid, "date": ds, "prompt_hhmm": None,
                    "mood": None, "stress": None, "energy": None,
                    "perceived_sleep_quality": None, "phq2_score": None,
                    "free_text": None, "responded": False,
                })
            # hourly HR (viz only): smooth diurnal curve around the daily resting/avg
            for h in range(24):
                base = resting_hr[i] + (avg_hr[i] - resting_hr[i]) * np.sin(np.pi * max(0, (h - 6)) / 16) ** 2
                hr_hourly.append({
                    "user_id": uid,
                    "datetime": datetime(d.year, d.month, d.day, h).isoformat(),
                    "hr_bpm": int(np.clip(base + rng.normal(0, 3), 40, 190)),
                })

    return {
        "users": pd.DataFrame(users_rows),
        "sleep": pd.DataFrame(sleep),
        "heart_rate": pd.DataFrame(hr),
        "heart_rate_hourly": pd.DataFrame(hr_hourly),
        "steps": pd.DataFrame(steps),
        "location": pd.DataFrame(loc),
        "screen_time": pd.DataFrame(screen),
        "ema": pd.DataFrame(ema),
        "context": pd.DataFrame(context),
    }


def write(tables: dict[str, pd.DataFrame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        df.to_csv(OUT / f"{name}.csv", index=False)
        h = hashlib.sha256((OUT / f"{name}.parquet").read_bytes()).hexdigest()
        lines.append(f"{h}  processed/{name}.parquet")
    (HERE / "MANIFEST.sha256").write_text("\n".join(sorted(lines)) + "\n")


def main() -> None:
    tables = build()
    write(tables)
    total = sum((OUT / f"{n}.parquet").stat().st_size for n in tables) / 1e6
    print(f"Wrote {len(tables)} tables to {OUT} ({total:.2f} MB parquet). DEMO_TODAY={DEMO_TODAY}.")
    for n, df in tables.items():
        print(f"  {n:18s} {len(df):6d} rows  x {len(df.columns)} cols")


if __name__ == "__main__":
    main()
