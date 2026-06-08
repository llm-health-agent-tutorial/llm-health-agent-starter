"""Dataset loading. Date-dtype bulletproofed: every loader normalizes dates to datetime,
and date_range() parses string args before comparing, so participant tools never compare a
raw string to a date column.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from . import config

_DATE_COL = "date"


@lru_cache(maxsize=None)
def load_table(name: str) -> pd.DataFrame:
    """Load one committed table (parquet, CSV fallback). Dates normalized to datetime64."""
    if name not in config.TABLES:
        raise KeyError(f"Unknown table '{name}'. Valid: {', '.join(config.TABLES)}")
    pq = config.PROCESSED / f"{name}.parquet"
    csv = config.PROCESSED / f"{name}.csv"
    if pq.exists():
        df = pd.read_parquet(pq)
    elif csv.exists():
        df = pd.read_csv(csv)
    else:
        raise FileNotFoundError(
            f"Dataset table '{name}' not found in {config.PROCESSED}. "
            "Run `python data/generate_dataset.py` (or `make data`)."
        )
    if _DATE_COL in df.columns:
        df[_DATE_COL] = pd.to_datetime(df[_DATE_COL])
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_dataset() -> dict[str, pd.DataFrame]:
    """All tables as a name -> DataFrame dict."""
    return {name: load_table(name) for name in config.TABLES}


def date_range(df: pd.DataFrame, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """Inclusive filter on the 'date' column. String args are parsed with pd.to_datetime."""
    if _DATE_COL not in df.columns:
        return df
    out = df
    if start is not None:
        out = out[out[_DATE_COL] >= pd.to_datetime(start)]
    if end is not None:
        out = out[out[_DATE_COL] <= pd.to_datetime(end)]
    return out


def load_user_metric(
    user_id: str,
    table: str,
    columns: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """The single retrieval path used by all tools. Returns a copy filtered to one user and an
    inclusive date range, sorted by date, with 'date' kept alongside the requested columns.
    """
    df = load_table(table)
    df = df[df["user_id"] == user_id]
    df = date_range(df, start, end)
    if _DATE_COL in df.columns:
        df = df.sort_values(_DATE_COL)
    if columns is not None:
        keep = [c for c in ([_DATE_COL] if _DATE_COL in df.columns else []) + list(columns) if c in df.columns]
        df = df[keep]
    return df.reset_index(drop=True).copy()
