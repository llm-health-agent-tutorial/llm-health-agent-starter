# Setup (please do this ~2 weeks before the tutorial, on good wifi)

The room has limited time and flaky wifi, so **install at home**. In the session, Module 2 is
just a quick *verification*, not a first install.

## 1. Install
```bash
git clone https://github.com/llm-health-agent-tutorial/llm-health-agent-starter.git && cd llm-health-agent-starter
bash install.sh                  # macOS/Linux
# Windows:  powershell -ExecutionPolicy Bypass -File .\install.ps1
```
The installer uses **uv** to provision **Python 3.11** (fresh 2026 laptops often ship 3.13/3.14,
which lack wheels for the pinned scientific stack). If you don't have `uv`, install it from
<https://docs.astral.sh/uv/> (one line) or use conda: `conda env create -f environment.yml`.

## 2. Verify
```bash
ha-check
```
You should see PASS for Python, Core libraries, and Teaching dataset. The Backend row will say
`scripted` unless you set up a key/model (next, optional).

## 3. (Optional) a live model
Everything works on the **scripted** backend with no key or extra install. For the full live
experience, **first add the provider SDKs** — they are *not* in the default install:
```bash
make live-install                       # adds the openai / google-genai / ollama SDKs (uv users)
# pip users:  pip install -r requirements-live.txt
```
Then pick a backend:
- **API key** — set `OPENAI_API_KEY`, or `GEMINI_API_KEY` (alias: `GOOGLE_API_KEY`) in `.env`.
- **Local model** — install [Ollama](https://ollama.com), then **on home wifi** `make ollama-pull`
  (pulls `llama3.1:8b`; `qwen2.5:7b` is a smaller alternative). Don't pull at the venue.

Re-run `ha-check` to confirm the active tier. If a key/model is set but the SDK is missing, it
falls back to scripted and prints the exact fix (`make live-install`).

## 4. Open the notebooks
```bash
make lab        # or: jupyter lab notebooks/
```
Pick the **health-agent** kernel. Run `00_preflight.ipynb` top to bottom — if the last cell prints
a grounded answer, you're ready. 🎉

Problems? See the troubleshooting table in the [README](README.md).
