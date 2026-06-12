# Roadmap

This repo is a small, readable scaffold for prototyping personal LLM health agents. The aim is to keep
the core minimal and grow value through **docs, adapters, and thin CLIs** — not a big framework.

## Done
- Offline-complete tutorial (scripted floor) + live backends (Ollama / OpenAI / Gemini).
- Notebooks for Modules 2–5 with optional "🚀 Advanced" exercises.
- Eval/safety harness (red-team probes; deterministic safety handling; marker-gated grounding).
- **CLIs:** `ha-chat`, `ha-eval` (cross-model scorecard), `ha-data-check`.
- **Bring-your-own-data:** `HA_DATA_DIR` + codebook schema + adapter template.

## Next (community-friendly)
- **Data adapters** for real exports (Apple Health, Fitbit, GLOBEM, RAPIDS) under `data/adapters/`.
- **More tools/metrics**: richer analysis (trend/seasonality, simple anomaly), additional modalities.
- **Eval depth**: more probe categories (overconfidence, longitudinal drift), grounding/faithfulness
  scores in `ha-eval`.
- **Optional chat UI** (Streamlit) behind a `ui` extra; a public browser demo at launch.
- **Multi-turn / memory** in the agent loop (kept legible).

## Later / research directions
- Longitudinal reasoning beyond a single window; confound-aware analysis.
- A hosted demo + an archived release with a citable DOI.

Have an idea? Open an issue or a Discussion — see [CONTRIBUTING.md](CONTRIBUTING.md).
