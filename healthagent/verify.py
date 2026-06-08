"""`ha-check` — preflight: Python version, imports, committed-data integrity, backend tier.

Prints a PASS/FAIL table and the active backend. Exit code 0 iff the essentials pass (the
scripted floor always works, so a missing API key is a WARN, not a failure).
"""
from __future__ import annotations

import hashlib
import importlib
import sys


def _check_python() -> tuple[bool, str]:
    v = sys.version_info
    ok = (3, 10) <= (v.major, v.minor) <= (3, 12)
    return ok, f"{v.major}.{v.minor}.{v.micro}" + ("" if ok else "  (need 3.10-3.12; see SETUP.md)")


def _check_imports() -> tuple[bool, str]:
    missing = [m for m in ("pandas", "numpy", "matplotlib", "pyarrow") if not importlib.util.find_spec(m)]
    return (not missing), ("all core libs present" if not missing else f"missing: {missing}")


def _check_data() -> tuple[bool, str]:
    from . import config

    manifest = config.DATA_DIR / "MANIFEST.sha256"
    if not manifest.exists():
        return False, "data/MANIFEST.sha256 missing — run `python data/generate_dataset.py`"
    bad = []
    for line in manifest.read_text().splitlines():
        if not line.strip():
            continue
        want, rel = line.split("  ", 1)
        path = config.DATA_DIR / rel
        if not path.exists():
            bad.append(f"{rel} missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != want:
            bad.append(f"{rel} hash mismatch")
    return (not bad), ("9 tables present, hashes OK" if not bad else "; ".join(bad))


def _check_backend() -> tuple[bool, str]:
    from . import config
    from .llm.client import get_client

    desired = config.resolve_backend()
    client = get_client("auto", quiet=True)
    note = f"desired={desired}, active={client.provider}"
    if client.provider == "scripted" and desired != "scripted":
        note += "  (live adapter arrives in Milestone 2; using offline floor)"
    return True, note  # scripted floor always works -> never fails the gate


def main() -> int:
    checks = [
        ("Python 3.10-3.12", _check_python),
        ("Core libraries", _check_imports),
        ("Teaching dataset", _check_data),
        ("Backend", _check_backend),
    ]
    rows, hard_ok = [], True
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        rows.append((("PASS" if ok else "FAIL"), name, detail))
        if name != "Backend":
            hard_ok = hard_ok and ok

    try:
        from tabulate import tabulate

        print(tabulate(rows, headers=["status", "check", "detail"], tablefmt="github"))
    except Exception:  # noqa: BLE001
        for s, n, d in rows:
            print(f"[{s}] {n}: {d}")

    print("\n" + ("✓ Ready." if hard_ok else "✗ Not ready — see the failing rows and README troubleshooting."))
    return 0 if hard_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
