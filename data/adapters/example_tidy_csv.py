"""Worked BYOD example: a generic *tidy / long* CSV -> this repo's per-table schema.

Input CSV columns: ``user_id, date, metric, value`` (``metric`` may be a codebook name OR an alias).
Run it, then validate:

    python data/adapters/example_tidy_csv.py my_export.csv
    ha-data-check

It maps each metric to its codebook (table, canonical name), pivots to one wide frame per table, and
writes ``data/processed/{table}.{parquet,csv}``. Unknown metrics are skipped (with a count).
"""
from __future__ import annotations

import csv as _csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CODEBOOK = ROOT / "data" / "codebook.csv"
OUT = ROOT / "data" / "processed"


def _alias_map() -> dict[str, tuple[str, str]]:
    """{name_or_alias: (table, canonical_metric)} from the codebook."""
    out: dict[str, tuple[str, str]] = {}
    with open(CODEBOOK, newline="") as fh:
        for row in _csv.DictReader(fh):
            out[row["metric"]] = (row["table"], row["metric"])
            for alias in (row["aliases"] or "").split(";"):
                alias = alias.strip()
                if alias:
                    out[alias] = (row["table"], row["metric"])
    return out


def convert(tidy_csv: str) -> dict[str, pd.DataFrame]:
    df = pd.read_csv(tidy_csv)  # user_id, date, metric, value
    amap = _alias_map()
    known = df["metric"].isin(amap)
    if (~known).any():
        print(f"skipping {int((~known).sum())} rows with metrics not in the codebook")
    df = df[known].copy()
    df["table"] = df["metric"].map(lambda m: amap[m][0])
    df["canonical"] = df["metric"].map(lambda m: amap[m][1])
    tables: dict[str, pd.DataFrame] = {}
    for table, group in df.groupby("table"):
        wide = group.pivot_table(index=["user_id", "date"], columns="canonical",
                                 values="value", aggfunc="first")
        tables[table] = wide.reset_index()
    return tables


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python data/adapters/example_tidy_csv.py <tidy.csv>")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    for table, frame in convert(argv[0]).items():
        frame.to_parquet(OUT / f"{table}.parquet", index=False)
        frame.to_csv(OUT / f"{table}.csv", index=False)
        print(f"wrote {table}: {len(frame)} rows, cols={list(frame.columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
