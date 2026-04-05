#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from book_agent.services.translate_benchmark_draft_generator import (
    auto_annotate_and_write,
    build_pdf_mixed_layout_draft,
    write_draft_files,
)
from book_agent.services.translate_rollout_supervisor import load_queue_profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate auto benchmark drafts for benchmark-first books that still lack manifests."
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
        "--queue-index",
        type=int,
        action="append",
        help="Optional queue index filter; may be passed multiple times.",
    )
    parser.add_argument(
        "--auto-annotate",
        action="store_true",
        help="Auto-annotate existing stub_pending_annotation gold labels by parsing PDF probe pages.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    queue_profile_path = Path(args.queue_profile).resolve()
    review_root = Path(args.review_root).resolve()
    queue_items = load_queue_profile(queue_profile_path)
    selected_indices = set(args.queue_index or [])
    generated: list[dict[str, str]] = []
    annotated: list[dict[str, str]] = []

    if args.auto_annotate:
        # Auto-annotate existing stub gold labels
        gold_labels_dir = review_root / "gold-labels"
        if gold_labels_dir.exists():
            for gl_path in sorted(gold_labels_dir.glob("*.json")):
                try:
                    gl = json.loads(gl_path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if gl.get("status") != "stub_pending_annotation":
                    continue
                if selected_indices:
                    # Match by document_path against queue items
                    matching = [item for item in queue_items if item.path == gl.get("document_path")]
                    if not any(item.queue_index in selected_indices for item in matching):
                        continue
                try:
                    result = auto_annotate_and_write(gl_path)
                    annotated.append({
                        "sample_id": result.get("sample_id", ""),
                        "gold_label_path": str(gl_path.resolve()),
                        "status": result.get("status", ""),
                        "block_count": str(len(result.get("blocks", []))),
                    })
                except FileNotFoundError as exc:
                    annotated.append({
                        "sample_id": gl.get("sample_id", ""),
                        "gold_label_path": str(gl_path.resolve()),
                        "status": "error",
                        "error": str(exc),
                    })
        print(json.dumps({"annotated": annotated}, ensure_ascii=False))
        return 0

    for item in queue_items:
        if selected_indices and item.queue_index not in selected_indices:
            continue
        if item.recommended_next_step != "benchmark_first":
            continue
        if item.suffix.lower() != ".pdf":
            continue
        manifest, gold_label = build_pdf_mixed_layout_draft(
            document_path=Path(item.path),
            lane_id=item.lane_guess or "L5",
            family_guess=item.family_guess or "PDF-mixed-layout-book",
            risk_tags=item.risk_tags,
            queue_profile_path=queue_profile_path,
        )
        manifest_path, gold_label_path = write_draft_files(
            manifest=manifest,
            gold_label=gold_label,
            review_root=review_root,
        )
        generated.append(
            {
                "queue_index": str(item.queue_index),
                "source_path": item.path,
                "manifest_path": str(manifest_path.resolve()),
                "gold_label_path": str(gold_label_path.resolve()),
            }
        )
    print(json.dumps({"generated": generated}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
