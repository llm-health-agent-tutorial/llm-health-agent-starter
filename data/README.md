# Teaching dataset

Fully **synthetic, de-identified** multimodal sensing data — 12 users (`u01`–`u12`), 112 days each
(16 weeks), ending on the fixed epoch `DEMO_TODAY = 2026-06-05`. It exists only to teach LLM-agent
design; it describes no real person and is not clinical data.

| File | What |
|------|------|
| [`DATA_CARD.md`](DATA_CARD.md) | **Start here** — contents, the seeded teaching signal + confound, and the honesty notes |
| [`codebook.csv`](codebook.csv) | schema: every metric → table, unit, dtype, aliases (the `MetricCatalog` reads this) |
| [`generate_dataset.py`](generate_dataset.py) | the deterministic generator (run offline; the output is committed) |
| [`processed/`](processed/) | the data: 9 tables as `*.parquet` (+ a `.csv` mirror) |
| [`MANIFEST.sha256`](MANIFEST.sha256) | integrity hashes (CI regenerates + re-checks the signal) |
| [`golden/`](golden/) | pre-rendered reference answers/plot for **instructor rescue only** (never used by tests) |

Regenerate with `python generate_dataset.py` (or `make data` from the repo root). Reproducible
byte-for-byte via the fixed `SEED = 2026`.

**The seeded story (disclosed):** in `u01`'s final 7 days, night-time screen use is ~6–10× baseline
and total sleep is generated causally downstream of it (≈ 5.65 h vs ≈ 7.44 h baseline) — alongside a
**collinear `deadline` confound** that *independently* costs sleep. See [`DATA_CARD.md`](DATA_CARD.md)
for why, and how it drives the Module-5 correlation-≠-causation discussion.
