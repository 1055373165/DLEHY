# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from book_agent.core.config import get_settings
from book_agent.domain.enums import ExportType, IssueStatus
from book_agent.domain.models.review import ReviewIssue
from book_agent.domain.models.translation import TargetSegment, TranslationRun
from book_agent.infra.db.session import build_engine, build_session_factory, session_scope
from book_agent.services.workflows import DocumentWorkflowService
from book_agent.workers.factory import build_translation_worker


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "value"):
        return value.value
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def _issue_summary(session, chapter_id: str) -> dict[str, Any]:
    issues = session.scalars(
        select(ReviewIssue)
        .where(
            ReviewIssue.chapter_id == chapter_id,
            ReviewIssue.status == IssueStatus.OPEN,
        )
        .order_by(ReviewIssue.blocking.desc(), ReviewIssue.issue_type.asc(), ReviewIssue.created_at.asc())
    ).all()
    counts_by_type: dict[str, int] = {}
    issue_records: list[dict[str, Any]] = []
    for issue in issues:
        counts_by_type[issue.issue_type] = counts_by_type.get(issue.issue_type, 0) + 1
        issue_records.append(
            {
                "issue_id": issue.id,
                "issue_type": issue.issue_type,
                "packet_id": issue.packet_id,
                "sentence_id": issue.sentence_id,
                "blocking": issue.blocking,
                "severity": issue.severity.value,
                "root_cause_layer": issue.root_cause_layer.value,
                "source_term": str((issue.evidence_json or {}).get("source_term") or "").strip() or None,
                "preferred_hint": str((issue.evidence_json or {}).get("preferred_hint") or "").strip() or None,
                "prompt_guidance": str((issue.evidence_json or {}).get("prompt_guidance") or "").strip() or None,
            }
        )
    return {
        "open_issue_count": len(issues),
        "counts_by_type": counts_by_type,
        "issues": issue_records,
    }


def _chapter_result_for(review_result, chapter_id: str) -> dict[str, Any] | None:
    wanted = str(chapter_id).replace("-", "")
    for chapter_result in review_result.chapter_results:
        current = str(chapter_result.chapter_id).replace("-", "")
        if current == wanted:
            return asdict(chapter_result)
    return None


def _collect_rerun_samples(session, translation_run_ids: list[str]) -> list[dict[str, Any]]:
    if not translation_run_ids:
        return []
    runs = session.scalars(
        select(TranslationRun)
        .where(TranslationRun.id.in_(translation_run_ids))
        .order_by(TranslationRun.created_at.asc(), TranslationRun.id.asc())
    ).all()
    sample_rows = session.execute(
        select(
            TargetSegment.translation_run_id,
            TargetSegment.ordinal,
            TargetSegment.text_zh,
        )
        .where(
            TargetSegment.translation_run_id.in_(translation_run_ids),
        )
        .order_by(TargetSegment.translation_run_id.asc(), TargetSegment.ordinal.asc())
    ).all()
    segments_by_run: dict[str, list[str]] = {}
    for run_id, _ordinal, text_zh in sample_rows:
        normalized = str(text_zh or "").strip()
        if not normalized:
            continue
        segments = segments_by_run.setdefault(run_id, [])
        if len(segments) < 6:
            segments.append(normalized)

    samples: list[dict[str, Any]] = []
    for run in runs:
        samples.append(
            {
                "translation_run_id": run.id,
                "packet_id": run.packet_id,
                "model_name": run.model_name,
                "prompt_version": run.prompt_version,
                "attempt": run.attempt,
                "status": run.status.value,
                "token_in": run.token_in,
                "token_out": run.token_out,
                "cost_usd": float(run.cost_usd or 0),
                "latency_ms": run.latency_ms,
                "sample_segments": segments_by_run.get(run.id, []),
            }
        )
    return samples


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a real chapter review auto-followup smoke and export the chapter outputs."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--chapter-id", required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--report-path", type=Path, required=True)
    parser.add_argument("--max-auto-followup-attempts", type=int, default=3)
    parser.add_argument("--include-merged-markdown", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    engine = build_engine(database_url=args.database_url)
    session_factory = build_session_factory(engine=engine)
    export_root = args.export_root.resolve()
    report_path = args.report_path.resolve()
    export_root.mkdir(parents=True, exist_ok=True)

    try:
        with session_scope(session_factory) as session:
            workflow = DocumentWorkflowService(
                session,
                export_root=str(export_root),
                translation_worker=build_translation_worker(settings),
            )

            before_summary = _issue_summary(session, args.chapter_id)
            review_result = workflow.review_document(
                args.document_id,
                auto_execute_packet_followups=True,
                max_auto_followup_attempts=args.max_auto_followup_attempts,
            )
            after_summary = _issue_summary(session, args.chapter_id)
            chapter_result = _chapter_result_for(review_result, args.chapter_id)
            review_package = workflow.export_service.export_chapter(args.chapter_id, ExportType.REVIEW_PACKAGE)
            bilingual = workflow.export_service.export_chapter(args.chapter_id, ExportType.BILINGUAL_HTML)
            merged_markdown = (
                workflow.export_service.export_document_merged_markdown(args.document_id)
                if args.include_merged_markdown
                else None
            )

            rerun_translation_run_ids: list[str] = []
            for execution in review_result.auto_followup_executions or []:
                rerun_translation_run_ids.extend(execution.rerun_translation_run_ids)

            payload = {
                "generated_at": datetime.now().isoformat(),
                "database_url": args.database_url,
                "document_id": args.document_id,
                "chapter_id": args.chapter_id,
                "max_auto_followup_attempts": args.max_auto_followup_attempts,
                "before_review": before_summary,
                "review_result": {
                    "document_id": review_result.document_id,
                    "total_issue_count": review_result.total_issue_count,
                    "total_action_count": review_result.total_action_count,
                    "chapter_result": chapter_result,
                    "chapter_results": [asdict(result) for result in review_result.chapter_results],
                    "auto_followup_requested": review_result.auto_followup_requested,
                    "auto_followup_applied": review_result.auto_followup_applied,
                    "auto_followup_attempt_count": review_result.auto_followup_attempt_count,
                    "auto_followup_attempt_limit": review_result.auto_followup_attempt_limit,
                    "auto_followup_executions": [
                        asdict(execution) for execution in (review_result.auto_followup_executions or [])
                    ],
                },
                "after_review": after_summary,
                "issue_delta": {
                    "before_open_issue_count": before_summary["open_issue_count"],
                    "after_open_issue_count": after_summary["open_issue_count"],
                    "resolved_open_issue_count": (
                        before_summary["open_issue_count"] - after_summary["open_issue_count"]
                    ),
                },
                "rerun_samples": _collect_rerun_samples(
                    session,
                    list(dict.fromkeys(rerun_translation_run_ids)),
                ),
                "exports": {
                    "review_package": {
                        "export_id": review_package.export_record.id,
                        "status": review_package.export_record.status.value,
                        "file_path": str(review_package.file_path),
                        "manifest_path": (
                            str(review_package.manifest_path) if review_package.manifest_path is not None else None
                        ),
                    },
                    "bilingual_html": {
                        "export_id": bilingual.export_record.id,
                        "status": bilingual.export_record.status.value,
                        "file_path": str(bilingual.file_path),
                        "manifest_path": (
                            str(bilingual.manifest_path) if bilingual.manifest_path is not None else None
                        ),
                    },
                    "merged_markdown": (
                        {
                            "export_id": merged_markdown.export_record.id,
                            "status": merged_markdown.export_record.status.value,
                            "file_path": str(merged_markdown.file_path),
                            "manifest_path": (
                                str(merged_markdown.manifest_path)
                                if merged_markdown.manifest_path is not None
                                else None
                            ),
                        }
                        if merged_markdown is not None
                        else None
                    ),
                },
            }

        _write_report(report_path, payload)
        print(report_path)
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
