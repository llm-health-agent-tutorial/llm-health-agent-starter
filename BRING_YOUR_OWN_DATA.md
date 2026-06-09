# Bring your own data

The tutorial ships a synthetic dataset, but the agent and tools work on **any** dataset that matches
the schema. This is how you point them at your own wearable/sensing data.

> The agent's demo tuning (`live_policy` intents, the seeded sleep story) is built for the synthetic
> data. On real data, ask **open-ended** questions and use a **live backend** (OpenAI/Gemini/Ollama) —
> the deterministic `scripted` backend only knows the two demo questions.

## 1. Match the schema
Your data is a directory of per-table files — `processed/{table}.parquet` (a `.csv` is also accepted):

- **Schema** = [`data/codebook.csv`](data/codebook.csv): every metric → its `table`, `unit`, `dtype`,
  and accepted `aliases`. Each table also needs **keys**:
  - `users` → `user_id`
  - `heart_rate_hourly` → `user_id`, `datetime` (ISO)
  - every daily metric table (`sleep`, `steps`, `screen_time`, `heart_rate`, `location`, `ema`,
    `context`) → `user_id`, `date` (ISO `YYYY-MM-DD`)
- **Partial data is fine.** Bring only the tables you have; `ha-data-check` tells you which tools that
  unlocks. (Note: `compare_window` — the activity-vs-goal tool — needs **both** `steps` and a `users`
  table with a `steps_goal` column.)
- See [`data/DATA_CARD.md`](data/DATA_CARD.md) for the full table/column reference.

Two starting points live in [`data/adapters/`](data/adapters/):
- `adapter_template.py` — a skeleton: fill in `read_my_export()`, then `python … adapter_template.py
  --out ~/my_dataset` writes the per-table files (it refuses to overwrite the repo's committed `data/`).
- `example_tidy_csv.py` — a worked example mapping a long/tidy CSV (`user_id,date,metric,value`,
  aliases allowed) into the per-table schema.

## 2. Point the loader at your data
`HA_DATA_DIR` is the directory that **contains** a `processed/` subdir (i.e. the parent of
`processed/`, mirroring the repo's `data/`). Set it **before** anything loads data:

```bash
export HA_DATA_DIR=/path/to/my_dataset      # which holds my_dataset/processed/*.parquet
ha-data-check                                # validate against the codebook
ha-data-check --tables sleep,steps           # require these tables to be fully valid
```

`ha-data-check` classifies each table **ok / partial / absent**, reports the **usable tools**, and
exits non-zero only when a present table is malformed (bad keys / non-coercible dtype) or a
`--tables`-requested table is missing or partial.

## 3. Ask your agent
```bash
export HA_DATA_DIR=/path/to/my_dataset
ha-chat --backend openai                     # interactive, over your data
ha-chat --backend ollama -q "How did my resting heart rate change this month?"
```

(Need the live SDKs? `make live-install` first. No key? `make ollama-pull` for a local model.)

## Notes & limits
- The committed demo data lives **outside** the Python package, so this BYOD flow assumes the
  **cloned / editable install** (the tutorial's path), not a bare `pip install` wheel. The codebook
  always comes from the repo.
- Keep dtypes sane: codebook `int` columns must be integer-valued, `float` numeric, and `date`/
  `datetime` keys must parse with `pandas.to_datetime`. `ha-data-check` enforces this leniently
  (coercion-based, not exact pandas dtypes).
- Want to contribute a parser for a real export (Apple Health, Fitbit, GLOBEM, RAPIDS)? See
  [`CONTRIBUTING.md`](CONTRIBUTING.md) — adapters are a great first contribution.
