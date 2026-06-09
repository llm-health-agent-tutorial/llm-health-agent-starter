"""``ha-data-check`` — validate a dataset against the codebook for bring-your-own-data use.

Partial data is fine: each table is classified ok / partial / absent, and the report says **which
tools become usable**. Point it at your own data with ``HA_DATA_DIR=<dir containing processed/>``.
See ``BRING_YOUR_OWN_DATA.md``.
"""
from __future__ import annotations

import argparse
import csv as _csv

# Explicit map of which (table, columns) each tool needs — NOT inferred from the codebook, so a
# dependency like compare_window needing BOTH steps and users (the step goal) can't be missed.
TOOL_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "compare_window":    {"steps": ["steps"], "users": ["steps_goal"]},
    "query_sleep":       {"sleep": ["total_sleep_hours", "sleep_efficiency"]},
    "query_screen_time": {"screen_time": ["total_screen_minutes", "night_screen_minutes"]},
    "query_steps":       {"steps": ["steps", "active_minutes"]},
    "query_heart_rate":  {"heart_rate": ["resting_hr_bpm", "hrv_rmssd_ms"]},
    "query_ema":         {"ema": ["mood", "stress"]},
}


def _required_keys(table: str) -> list[str]:
    if table == "users":
        return ["user_id"]
    if table == "heart_rate_hourly":
        return ["user_id", "datetime"]
    return ["user_id", "date"]


def _codebook_schema(codebook_path) -> dict[str, dict[str, str]]:
    """{table: {metric: dtype}} from data/codebook.csv (the canonical columns per table)."""
    schema: dict[str, dict[str, str]] = {}
    with open(codebook_path, newline="") as fh:
        for row in _csv.DictReader(fh):
            schema.setdefault(row["table"], {})[row["metric"]] = row["dtype"]
    return schema


def _load(processed, table):
    import pandas as pd

    pq, csvp = processed / f"{table}.parquet", processed / f"{table}.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    if csvp.exists():
        return pd.read_csv(csvp)
    return None


def _key_ok(df, key) -> bool:
    import pandas as pd

    if key not in df.columns:
        return False
    if key in ("date", "datetime"):  # must be parseable wherever non-null
        parsed = pd.to_datetime(df[key], errors="coerce")
        return not (parsed.isna() & df[key].notna()).any()
    return True  # user_id just needs to exist


def _dtype_ok(series, dtype: str) -> bool:
    """Coercion-based (not exact pandas dtype): int = numeric + integer-valued; float = numeric."""
    import pandas as pd

    s = series.dropna()
    if len(s) == 0:
        return True  # all-null can't be disproven
    if dtype in ("int", "float"):
        num = pd.to_numeric(s, errors="coerce")
        if num.isna().any():
            return False
        return bool((num == num.round()).all()) if dtype == "int" else True
    return True  # strings/bools accepted


def check_dataset(processed, tables: list[str] | None = None):
    """Validate ``processed/`` against the codebook. Returns (rows, usable_tools, ok).

    ``rows``: [{table, status, note}]; ``ok``: False iff a present table is malformed, or any
    explicitly ``--tables``-requested table is not fully ok.
    """
    from pathlib import Path

    from .. import config

    processed = Path(processed)
    schema = _codebook_schema(config.CODEBOOK)
    all_tables = list(config.TABLES)

    rows, status_by, cols_by = [], {}, {}
    for table in all_tables:
        df = _load(processed, table)
        if df is None:
            status_by[table] = "absent"
            rows.append({"table": table, "status": "absent", "note": "file not found"})
            continue
        cols_by[table] = set(df.columns)
        bad_keys = [k for k in _required_keys(table) if not _key_ok(df, k)]
        canon = schema.get(table, {})
        present = [m for m in canon if m in df.columns]
        missing = [m for m in canon if m not in df.columns]
        bad_dtype = [m for m in present if not _dtype_ok(df[m], canon[m])]
        if bad_keys or bad_dtype:
            status, note = "malformed", "; ".join(
                ([f"bad/missing keys: {bad_keys}"] if bad_keys else [])
                + ([f"non-coercible: {bad_dtype}"] if bad_dtype else []))
        elif missing:
            status, note = "partial", f"missing columns: {missing}"
        else:
            status, note = "ok", "all codebook columns present"
        status_by[table] = status
        rows.append({"table": table, "status": status, "note": note})

    def usable(tool: str) -> bool:
        for t, need in TOOL_REQUIREMENTS[tool].items():
            if status_by.get(t) == "malformed" or t not in cols_by or not set(need) <= cols_by[t]:
                return False
        return True

    usable_tools = [t for t in TOOL_REQUIREMENTS if usable(t)]
    n_metrics = sum(1 for tbl, mets in schema.items() for m in mets
                    if tbl in cols_by and m in cols_by[tbl] and status_by.get(tbl) != "malformed")
    if n_metrics:
        usable_tools.append(f"detect_change/plot_timeseries/describe_metric (on {n_metrics} metrics)")

    fail = any(s == "malformed" for s in status_by.values())
    if tables:  # requested tables must be fully ok
        fail = fail or any(status_by.get(t, "absent") != "ok" for t in tables)
    return rows, usable_tools, (not fail)


def _print(rows, usable_tools, ok, processed):
    mark = {"ok": "✓", "partial": "~", "absent": "·", "malformed": "✗"}
    table = [[mark.get(r["status"], "?"), r["table"], r["status"], r["note"]] for r in rows]
    try:
        from tabulate import tabulate
        print(tabulate(table, headers=["", "table", "status", "note"], tablefmt="github"))
    except Exception:  # noqa: BLE001
        for m, t, s, n in table:
            print(f"[{m}] {t:18s} {s:9s} {n}")
    print(f"\nUsable tools: {', '.join(usable_tools) or '(none)'}")
    print("\n" + ("✓ Dataset OK." if ok else "✗ Dataset has problems — see the rows above."))
    print(f"(checked: {processed})")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ha-data-check",
                                description="Validate a dataset against the codebook (BYOD).")
    p.add_argument("--tables", help="comma-separated subset that MUST be fully valid (e.g. sleep,steps)")
    args = p.parse_args(argv)
    requested = [t.strip() for t in args.tables.split(",")] if args.tables else None

    from .. import config  # imported here (after arg parse) so --help never opens the codebook

    rows, usable_tools, ok = check_dataset(config.PROCESSED, requested)
    _print(rows, usable_tools, ok, config.PROCESSED)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
