# Contributing

Thanks for your interest! This started as a UbiComp/ISWC 2026 tutorial scaffold and is meant to stay
**small and readable**. Contributions that keep it that way — especially **data adapters** and **docs**
— are very welcome.

## Dev setup
```bash
git clone https://github.com/llm-health-agent-tutorial/llm-health-agent-starter.git
cd llm-health-agent-starter
make install          # uv-first; provisions Python 3.11
make test             # offline-core suite (no API keys needed)
.venv/bin/ruff check .   # lint
```
Live-backend / provider-contract tests need the SDKs: `make live-install`, then
`pytest tests/test_client_factory.py tests/test_provider_contract.py tests/test_verify.py`.

## What goes where
- **`healthagent/`** — the packaged library (tools, registry, agent loop, LLM clients, CLIs). Keep new
  console-script logic in `healthagent/cli/` and **never import `ha_workshop`** from packaged code (CI
  guards this) — use `healthagent.agent.reference` instead.
- **`ha_workshop/`** — the *teaching* scaffold (student stubs + reference solutions). It is intentionally
  **not** packaged. Don't make library code depend on it.
- **`data/`** — the committed synthetic dataset, the codebook (the schema), and `data/adapters/`.

## Good first contributions
- **A data adapter** for a real export (Apple Health, Fitbit, GLOBEM, RAPIDS) under `data/adapters/`,
  mapping it to the codebook schema — see [BRING_YOUR_OWN_DATA.md](BRING_YOUR_OWN_DATA.md) and
  `data/adapters/adapter_template.py`. Validate with `ha-data-check`.
- **A new tool / metric / red-team probe** — see [EXTENDING.md](EXTENDING.md).
- **Docs / recipes** in `docs/cookbook.md`.

## PRs
- Run `make test` and `ruff check .` before opening a PR (CI runs the same across macOS/Windows/Linux).
- Keep the readable agent loop legible and the "two editable files" tutorial invariant intact.
- One focused change per PR; describe what and why. See the PR template.

By contributing you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and that your contributions are
licensed under the repository's [MIT License](LICENSE).
