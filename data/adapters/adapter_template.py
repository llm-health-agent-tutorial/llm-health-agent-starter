"""Bring-your-own-data adapter TEMPLATE.

Copy this, fill in ``read_my_export()``, then write your data to a directory you choose (it will NOT
write into the repo's committed ``data/``) and point the agent at it:

    python data/adapters/adapter_template.py --out ~/my_dataset
    HA_DATA_DIR=~/my_dataset ha-data-check
    HA_DATA_DIR=~/my_dataset ha-chat --backend openai

Target schema = ``data/codebook.csv`` (the canonical columns per table) + table-specific keys
(``users`` -> ``user_id``; ``heart_rate_hourly`` -> ``user_id``+``datetime``; the daily metric tables
-> ``user_id``+``date``). Partial data is fine — include only the tables/metrics you have.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

REPO_DATA = Path(__file__).resolve().parents[1]  # the repo's data/ (the committed demo dataset)


def read_my_export() -> dict[str, pd.DataFrame]:
    """TODO: read your wearable export and return ``{table_name: DataFrame}``.

    Each daily table needs ``user_id``, ``date`` (ISO YYYY-MM-DD), plus the codebook metrics for that
    table. For example a ``sleep`` frame: ``user_id, date, total_sleep_hours, sleep_efficiency, ...``.
    """
    raise NotImplementedError("fill in read_my_export()")


def write(tables: dict[str, pd.DataFrame], out_root) -> None:
    processed = Path(out_root) / "processed"
    if processed.resolve() == (REPO_DATA / "processed").resolve():
        raise SystemExit("refusing to overwrite the committed demo data/processed — "
                         "pass --out <dir> or set HA_DATA_DIR")
    processed.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(processed / f"{name}.parquet", index=False)
        df.to_csv(processed / f"{name}.csv", index=False)
        print(f"wrote {name}: {len(df)} rows -> {processed}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BYOD adapter template")
    ap.add_argument("--out", default=os.getenv("HA_DATA_DIR", "my_dataset"),
                    help="directory to write processed/ into (default: $HA_DATA_DIR or ./my_dataset)")
    args = ap.parse_args(argv)
    write(read_my_export(), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
