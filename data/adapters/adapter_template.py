"""Bring-your-own-data adapter TEMPLATE.

Copy this, fill in ``read_my_export()``, and run it to emit ``data/processed/{table}.{parquet,csv}``
that ``ha-data-check`` accepts. Then point the agent at your data:

    HA_DATA_DIR=<dir containing processed/> ha-data-check
    HA_DATA_DIR=<dir containing processed/> ha-chat --backend openai

Target schema = ``data/codebook.csv`` (the canonical columns per table) + table-specific keys
(``users`` -> ``user_id``; ``heart_rate_hourly`` -> ``user_id``+``datetime``; the daily metric tables
-> ``user_id``+``date``). Partial data is fine — include only the tables/metrics you have.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "processed"  # data/processed


def read_my_export() -> dict[str, pd.DataFrame]:
    """TODO: read your wearable export and return ``{table_name: DataFrame}``.

    Each daily table needs ``user_id``, ``date`` (ISO YYYY-MM-DD), plus the codebook metrics for that
    table. For example a ``sleep`` frame: ``user_id, date, total_sleep_hours, sleep_efficiency, ...``.
    """
    raise NotImplementedError("fill in read_my_export()")


def write(tables: dict[str, pd.DataFrame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"wrote {name}: {len(df)} rows")


if __name__ == "__main__":
    write(read_my_export())
