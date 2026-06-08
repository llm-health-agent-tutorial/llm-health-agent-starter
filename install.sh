#!/usr/bin/env bash
# One-command install. uv-first: provisions Python 3.11 regardless of the system Python
# (fresh 2026 laptops ship 3.13/3.14, which have no wheels for the pinned scientific stack).
# Falls back to python -m venv ONLY if the system Python is 3.10-3.12.
set -euo pipefail
cd "$(dirname "$0")"

KERNEL="health-agent"
echo "==> healthagent installer"

if command -v uv >/dev/null 2>&1; then
  echo "==> uv found: provisioning Python 3.11 and syncing from uv.lock (locked)"
  uv sync --locked --extra notebooks --extra dev --python 3.11
  # shellcheck disable=SC1091
  source .venv/bin/activate
else
  echo "==> uv not found; checking system Python"
  PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
  case "$PYV" in
    3.10|3.11|3.12)
      echo "==> pip fallback: installing pinned deps from requirements.txt"
      python3 -m venv .venv
      # shellcheck disable=SC1091
      source .venv/bin/activate
      python -m pip install --upgrade pip
      pip install -r requirements.txt   # pinned deps (derived from uv.lock; includes Jupyter)
      pip install -e . --no-deps        # the project only; deps already pinned above
      ;;
    *)
      echo "ERROR: system Python is $PYV; this project pins 3.10-3.12."
      echo "Install uv (https://docs.astral.sh/uv/) or conda, then re-run. With conda:"
      echo "    conda env create -f environment.yml && conda activate health-agent && pip install -e ."
      exit 1
      ;;
  esac
fi

echo "==> registering Jupyter kernel '$KERNEL'"
python -m ipykernel install --user --name "$KERNEL" --display-name "$KERNEL" >/dev/null 2>&1 || true

[ -f .env ] || { cp .env.example .env; echo "==> wrote .env (HA_BACKEND=auto; scripted is the floor)"; }

echo "==> verifying"
ha-check   # exits non-zero (and aborts here) if a hard check fails — no false "Done."
echo
echo "Done. Activate with:  source .venv/bin/activate"
echo "Then:                 jupyter lab notebooks/   (pick the '$KERNEL' kernel)"
