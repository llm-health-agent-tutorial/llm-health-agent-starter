# Prototyping Your Personal LLM Health Agent — Starter Repo

Hands-on starter code for the **UbiComp/ISWC 2026** half-day tutorial *"From Multimodal Sensing
Data to Actionable Health Insights."* You build a single LLM **health agent** from a minimal
scaffold and ask it open-ended questions over a synthetic multimodal sensing dataset, e.g.
*"Why have I been sleeping poorly this week?"*

> Part 1 of a two-part track (Part 2 is the GLOSS multi-agent tutorial). This repo builds **one**
> agent from scratch; multi-agent is discussed, not built.

## Quickstart (5 min)
```bash
git clone <this repo> && cd <this repo>
bash install.sh          # uv-first; provisions Python 3.11, installs, registers a Jupyter kernel
ha-check                 # preflight: python / libs / data / backend tier
make lab                 # JupyterLab on notebooks/  (pick the "health-agent" kernel)
```
No API key? No network? You're still fine: the deterministic **scripted** backend runs the entire
tutorial offline. See [SETUP.md](SETUP.md) (do this at home ~2 weeks before).

## What you'll do (by module)
| Module | You do | Output |
| --- | --- | --- |
| 2 · Setting Up | verify env, load data, run a first tool-using call | working notebook on your backend |
| 3 · Designing Tools | fill two tools in `ha_workshop/student_tools.py` | a registered toolkit |
| 4 · Wiring the Agent | fill three seams in `ha_workshop/agent_config.py` | an agent that answers grounded questions |
| 5 · Eval & Safety | run the red-team probe harness; walk the checklist | an evaluation & safety checklist |

**You edit only two files**, both top-level (printed by the notebooks):
`ha_workshop/student_tools.py` and `ha_workshop/agent_config.py`. The loop and the rest of
`healthagent/` are complete and read-only.

## Layout
```
healthagent/        # the library (read-only): data, tools, registry, LLM clients, the agent loop
ha_workshop/        # YOUR code: student_tools.py, agent_config.py (+ solutions/)
data/               # committed synthetic dataset + codebook + DATA_CARD + generator
notebooks/          # 00 preflight, 02 setup, 03 tools, 04 agent, 05 eval/safety
tests/              # contract + safety + workshop-flow tests
```

## Backends
`get_client("auto")` resolves in this order and prints a loud banner of the active tier:
`HA_BACKEND` env → `GEMINI_API_KEY` → `OPENAI_API_KEY` → local Ollama → **scripted** (always-works
floor). In this release the **scripted** backend is fully implemented; live Gemini/OpenAI/Ollama
adapters land in the next milestone. The scripted backend is a *deterministic teaching backend*,
not a real LLM: it genuinely drives the loop (reads your registered tools, consumes observations,
honors the grounding/refusal prompt) so your Module-4 edits produce visible behavior changes
offline.

## Safety
Incomplete edits **fail safe**: if a tool isn't implemented or the observation step isn't wired,
the agent says *"I could not gather enough evidence"* rather than inventing an answer. See
[RESPONSIBLE_USE.md](RESPONSIBLE_USE.md). This is research tooling on synthetic data — **not**
medical advice.

## Troubleshooting
| `ha-check` row | Fix |
| --- | --- |
| Python 3.10-3.12 FAIL | install `uv` or conda; we pin 3.11 (system 3.13/3.14 lack wheels) |
| Core libraries FAIL | re-run `bash install.sh`; ensure the `.venv` is active |
| Teaching dataset FAIL | `python data/generate_dataset.py` (or `make data`) |
| kernel not in venv (notebook) | pick the **health-agent** Jupyter kernel (cell prints `sys.executable`) |

## License
MIT — see [LICENSE](LICENSE).
