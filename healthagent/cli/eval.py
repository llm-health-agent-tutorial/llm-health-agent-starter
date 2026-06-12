"""``ha-eval`` — run the red-team probe set across one or more backends and print a scorecard.

  ha-eval                                   # scripted only
  ha-eval --providers scripted,openai,gemini --out report.md
"""
from __future__ import annotations

import argparse


def score(providers: list[str]) -> dict[str, list[dict]]:
    """{provider: probe-rows}. Builds each backend's client ONCE; skips unavailable backends."""
    from ..agent.reference import run_reference_agent  # lazy
    from ..llm.client import get_client
    from ..llm.errors import BackendUnavailable
    from ..safety import probes

    results: dict[str, list[dict]] = {}
    for p in providers:
        try:
            client = get_client(p, allow_fallback=False, quiet=True)
        except BackendUnavailable as exc:
            print(f"skip {p}: {type(exc).__name__}: {exc}")
            continue
        results[p] = probes.run_all(lambda q: run_reference_agent(q, client=client))
    return results


def scorecard_md(results: dict[str, list[dict]]) -> str:
    if not results:
        return "(no backends available)"
    provs = list(results)
    ids = [r["id"] for r in next(iter(results.values()))]
    head = "| probe | expected | " + " | ".join(provs) + " |"
    sep = "|---|---|" + "|".join(["---"] * len(provs)) + "|"
    lines = [head, sep]
    for i, pid in enumerate(ids):
        exp = results[provs[0]][i]["expectation"]
        cells = [_cell(results[p][i]) for p in provs]
        lines.append(f"| {pid} | {exp} | " + " | ".join(cells) + " |")
    rates = [f"{sum(r['passed'] for r in results[p]) / len(results[p]):.0%}" for p in provs]
    lines.append("| **pass rate** |  | " + " | ".join(rates) + " |")
    return "\n".join(lines)


def _cell(row: dict) -> str:
    status = "PASS" if row["passed"] else "FAIL"
    if row["expectation"] == "grounded":
        detail = "grounded" if row["grounded"] else "not grounded"
    else:
        detail = row.get("kind") or "not safety-handled"
    return f"{status} ({detail})"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ha-eval", description="Red-team probe scorecard across backends.")
    p.add_argument("--providers", default="scripted",
                   help="comma-separated: scripted,openai,gemini,ollama (default: scripted)")
    p.add_argument("--out", help="also write the markdown scorecard to this path")
    args = p.parse_args(argv)

    results = score([x.strip() for x in args.providers.split(",")])
    md = scorecard_md(results)
    print(md)
    if args.out:
        from pathlib import Path
        Path(args.out).write_text(md + "\n")
        print(f"\nwrote {args.out}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
