#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from book_agent.services.translate_rollout_supervisor import run_supervisor


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the unattended translate-agent rollout supervisor for the delegated 10-book queue."
    )
    parser.add_argument(
        "--queue-profile",
        default="artifacts/review/translate-agent-book-queue-profiling-20260405.json",
    )
    parser.add_argument(
        "--review-root",
        default="artifacts/review",
    )
    parser.add_argument(
        "--real-book-root",
        default="artifacts/real-book-live",
    )
    parser.add_argument(
        "--state-json",
        default="artifacts/review/translate-agent-rollout-state-current.json",
    )
    parser.add_argument(
        "--state-md",
        default="artifacts/review/translate-agent-rollout-state-current.md",
    )
    parser.add_argument("--packet-limit", type=int, default=4)
    parser.add_argument("--execute", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_supervisor(
        queue_profile_path=Path(args.queue_profile).resolve(),
        review_root=Path(args.review_root).resolve(),
        real_book_root=Path(args.real_book_root).resolve(),
        state_json_path=Path(args.state_json).resolve(),
        state_md_path=Path(args.state_md).resolve(),
        packet_limit=args.packet_limit,
        execute=args.execute,
    )
    print(json.dumps(payload.get("selected_action"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
