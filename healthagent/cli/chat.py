"""``ha-chat`` — a tiny dependency-free terminal chat over the health agent.

  ha-chat                         # interactive REPL on the auto backend
  ha-chat --backend scripted -q "Why have I been sleeping poorly this week?"   # one-shot
"""
from __future__ import annotations

import argparse


def chat_once(question: str, client, user_id: str = "u01"):
    """Answer one question with the packaged reference agent. Returns AgentAnswer."""
    from ..agent.reference import run_reference_agent  # lazy: keeps `ha-chat --help` import-clean
    return run_reference_agent(question, client=client, user_id=user_id)


def _print_answer(ans) -> None:
    print(ans.text)
    tail = f"grounded={ans.grounded}" + (f", plot={ans.images[0]}" if ans.images else "")
    print(f"\n[{tail}]")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ha-chat", description="Chat with the health agent over the dataset.")
    p.add_argument("--backend", default="auto", help="auto | scripted | openai | gemini | ollama")
    p.add_argument("--user", default="u01", help="user id in the dataset")
    p.add_argument("-q", "--question", help="ask one question and exit (default: interactive REPL)")
    args = p.parse_args(argv)

    from ..llm.client import get_client  # lazy (after arg parse)
    client = get_client(args.backend)    # built ONCE

    if args.question:
        _print_answer(chat_once(args.question, client, args.user))
        return 0

    print('Ask about the data (e.g. "Why have I been sleeping poorly this week?").  :q to quit.\n')
    while True:
        try:
            q = input("you> ").strip()
        except EOFError:
            print()
            break
        if q in (":q", ":quit", "quit", "exit"):
            break
        if not q:
            continue
        try:
            _print_answer(chat_once(q, client, args.user))
        except Exception as exc:  # noqa: BLE001
            print(f"[error: {type(exc).__name__}: {exc}]")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
