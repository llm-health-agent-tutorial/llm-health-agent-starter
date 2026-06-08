#!/usr/bin/env bash
# Build a per-platform OFFLINE install pack (pre-event ops task; run on good wifi).
# Produces a wheelhouse + bundle so a cold/locked-down laptop can install with NO network.
# Run this once per target platform (macOS-arm64, macOS-x86_64, Windows, Linux).
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="offline-pack-$(uname -s)-$(uname -m)"
mkdir -p "$OUT/wheelhouse"

echo "==> downloading wheels for Python 3.11 into $OUT/wheelhouse (incl. build deps)"
# Include build-system deps (setuptools/wheel) so the editable install works fully offline.
uv pip download -r requirements.txt "setuptools>=68" wheel --python-version 3.11 -d "$OUT/wheelhouse" 2>/dev/null \
  || pip download -r requirements.txt "setuptools>=68" wheel -d "$OUT/wheelhouse"

echo "==> copying repo essentials (code + committed data + notebooks + installers)"
cp -r healthagent ha_workshop data notebooks templates pyproject.toml requirements.txt uv.lock \
      install.sh install.ps1 Makefile .env.example \
      README.md SETUP.md RESPONSIBLE_USE.md LICENSE "$OUT/"

cat > "$OUT/INSTALL_OFFLINE.md" <<'EOF'
# Offline install (no network)
1. Install Python 3.11 (carry the installer on the USB stick if needed).
2. python3.11 -m venv .venv && source .venv/bin/activate   (Windows: .venv\Scripts\activate)
3. pip install --no-index --find-links wheelhouse -r requirements.txt
4. pip install --no-index --find-links wheelhouse "setuptools>=68" wheel   # build deps
5. pip install --no-index --find-links wheelhouse --no-build-isolation -e . --no-deps
6. python -m healthagent.verify
Optionally: carry the Ollama model (`ollama pull llama3.1:8b` at home) on the USB stick too.
EOF

echo "==> done: $OUT/  (zip it onto USB sticks for the room)"
