# Setup (please do this ~2 weeks before the tutorial, on good wifi)

The room has limited time and flaky wifi, so **install at home**. In the session, Module 2 is
just a quick *verification*, not a first install.

## 1. Install
```bash
git clone <this repo> && cd <this repo>
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
Everything works on the **scripted** backend with no key. For the full live experience either:
- set `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`, **or**
- run a local model: install [Ollama](https://ollama.com), then **on home wifi** `make ollama-pull`
  (pulls `llama3.1:8b`; `qwen2.5:7b` is a smaller alternative). Don't pull at the venue.

## 4. Open the notebooks
```bash
make lab        # or: jupyter lab notebooks/
```
Pick the **health-agent** kernel. Run `00_preflight.ipynb` top to bottom — if the last cell prints
a grounded answer, you're ready. 🎉

Problems? See the troubleshooting table in the [README](README.md).
