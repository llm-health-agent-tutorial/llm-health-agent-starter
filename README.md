# Prototyping Your Personal LLM Health Agent — Starter Repo

Hands-on starter code for the **UbiComp/ISWC 2026** half-day tutorial *"From Multimodal Sensing
Data to Actionable Health Insights."* You build a single LLM **health agent** from a minimal
scaffold and ask it open-ended questions over a synthetic multimodal sensing dataset, e.g.
*"Why have I been sleeping poorly this week?"*

> Part 1 of a two-part track (Part 2 is the GLOSS multi-agent tutorial). This repo builds **one**
> agent from scratch; multi-agent is discussed, not built.

## Quickstart (5 min)
```bash
git clone https://github.com/llm-health-agent-tutorial/llm-health-agent-starter.git && cd llm-health-agent-starter
bash install.sh          # uv-first; provisions Python 3.11, installs, registers a Jupyter kernel
ha-check                 # preflight: python / libs / data / backend tier
make lab                 # JupyterLab on notebooks/  (pick the "health-agent" kernel)
```
No API key? No network? You're still fine: the deterministic **scripted** backend runs the entire
tutorial offline. See [SETUP.md](SETUP.md) (do this at home ~2 weeks before).

## Run in your browser (no install)
Laptop trouble, or just want to peek? Two zero-install options *(active once the repo is public)*:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/llm-health-agent-tutorial/llm-health-agent-starter)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/llm-health-agent-tutorial/llm-health-agent-starter/main?urlpath=lab/tree/notebooks/00_preflight.ipynb)

- **Codespaces** — full VS Code in the browser with the environment pre-installed (needs a GitHub
  account + free-tier hours). Open the notebooks directly, or run `make lab` / `ha-check` in the terminal.
- **Binder** — opens JupyterLab, no account needed. Good as a backup, but **ephemeral** (edits are lost
  when the session times out) and the first launch can take a few minutes.

Both boot on the **scripted** backend (no key needed); for live models, run `make live-install` in the
browser terminal. **Local install (above) is still the recommended path** — do it at home beforehand.

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
`HA_BACKEND` env → `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) → `OPENAI_API_KEY` → local Ollama →
**scripted** (always-works
floor). All four backends are implemented; the live ones need their SDKs (`make live-install`) — if a
key/model is configured but the SDK is missing, `ha-check` prints the exact fix. The **scripted**
backend is a *deterministic teaching backend*, not a real LLM: it drives the loop (reads your
registered tools, consumes observations, honors the `[GROUNDING]` clause) so your Module-4 edits
produce visible behavior changes with no key or network. **Medical-advice refusal is loop-owned** (a
deterministic preflight in `run_agent`, active once TODO-3 adds the `[REFUSAL]` clause), so it behaves
identically on every backend rather than depending on a live model's compliance.

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
