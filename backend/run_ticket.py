"""CLI: run Boss (and delegates) on one ticket via MCP + gpt-6-luna."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from llm import MODEL_NAME, MissingModelKey
from team import run_boss_on_ticket


def main() -> int:
    parser = argparse.ArgumentParser(description="Campus Customs ops team — one ticket")
    parser.add_argument("--ticket", type=int, required=True, help="Ticket id (101/102/103)")
    parser.add_argument(
        "--extra",
        default="",
        help="Optional human instructions (e.g. approved_by=Jane Doe)",
    )
    args = parser.parse_args()

    try:
        decision = asyncio.run(run_boss_on_ticket(args.ticket, extra=args.extra))
    except MissingModelKey as exc:
        print(exc, file=sys.stderr)
        return 2

    print(json.dumps(decision.model_dump(), indent=2))
    print(f"\nmodel={MODEL_NAME}  audit=output/audit_trail.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
