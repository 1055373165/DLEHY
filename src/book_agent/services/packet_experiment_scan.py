from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from book_agent.domain.enums import IssueStatus
from book_agent.domain.models.review import ReviewIssue
from book_agent.domain.models.translation import TranslationPacket
from book_agent.infra.repositories.translation import TranslationRepository
from book_agent.services.packet_experiment import PacketExperimentOptions, PacketExperimentService


def _memory_gain(payload: dict[str, Any]) -> int:
    context_sources = payload.get("context_sources") or {}
    compiled = int(context_sources.get("compiled_prev_translated_count") or 0)
    raw = int(context_sources.get("raw_prev_translated_count") or 0)
    return compiled - raw


def _concept_gain(payload: dict[str, Any]) -> int:
    context_sources = payload.get("context_sources") or {}
    compiled = int(context_sources.get("compiled_chapter_concept_count") or 0)
    raw = int(context_sources.get("raw_chapter_concept_count") or 0)
    return compiled - raw


def _brief_from_memory(payload: dict[str, Any]) -> bool:
    context_sources = payload.get("context_sources") or {}
    return context_sources.get("chapter_brief_source") == "memory"


def _current_sentence_count(payload: dict[str, Any]) -> int:
    context_packet = payload.get("context_packet") or {}
    current_blocks = context_packet.get("current_blocks") or []
    return sum(
        len(list(block.get("sentence_ids") or []))
        for block in current_blocks
        if isinstance(block, dict)
    )


def _memory_signal_score(payload: dict[str, Any]) -> int:
    return (
        _memory_gain(payload) * 100
        + _concept_gain(payload) * 20
        + (10 if _brief_from_memory(payload) else 0)
        + _current_sentence_count(payload)
    )


def _packet_issue_summary(issues: list[ReviewIssue]) -> dict[str, Any]:
    issue_types = sorted({str(issue.issue_type or "").strip() for issue in issues if str(issue.issue_type or "").strip()})
    unresolved_issue_count = len(issues)
    style_drift_issue_count = sum(1 for issue in issues if issue.issue_type == "STYLE_DRIFT")
    non_style_issue_count = unresolved_issue_count - style_drift_issue_count
    has_non_style_issue = non_style_issue_count > 0
    mixed_issue_types = len(issue_types) >= 2
    if mixed_issue_types or has_non_style_issue:
        issue_priority_tier = 0
        issue_priority_reason = "mixed_or_non_style"
    elif style_drift_issue_count > 0:
        issue_priority_tier = 1
        issue_priority_reason = "style_only"
    else:
        issue_priority_tier = 2
        issue_priority_reason = "no_unresolved_issues"
    return {
        "unresolved_issue_count": unresolved_issue_count,
        "unresolved_issue_types": issue_types,
        "style_drift_issue_count": style_drift_issue_count,
        "non_style_issue_count": non_style_issue_count,
        "has_non_style_issue": has_non_style_issue,
        "mixed_issue_types": mixed_issue_types,
        "issue_priority_tier": issue_priority_tier,
        "issue_priority_reason": issue_priority_reason,
    }


@dataclass(slots=True)
class PacketExperimentScanArtifacts:
    payload: dict[str, Any]


class PacketExperimentScanService:
    def __init__(
        self,
        repository: TranslationRepository,
        experiment_service: PacketExperimentService,
    ):
        self.repository = repository
        self.experiment_service = experiment_service

    def scan_chapter(
        self,
        chapter_id: str,
        *,
        options: PacketExperimentOptions | None = None,
    ) -> PacketExperimentScanArtifacts:
        experiment_options = options or PacketExperimentOptions(execute=False)
        unresolved_issues = self.repository.session.scalars(
            select(ReviewIssue).where(
                ReviewIssue.chapter_id == chapter_id,
                ReviewIssue.packet_id.is_not(None),
                ReviewIssue.status.in_([IssueStatus.OPEN, IssueStatus.TRIAGED]),
            )
        ).all()
        issues_by_packet: dict[str, list[ReviewIssue]] = {}
        for issue in unresolved_issues:
            if not issue.packet_id:
                continue
            issues_by_packet.setdefault(issue.packet_id, []).append(issue)
        packets = self.repository.session.scalars(
            select(TranslationPacket)
            .where(TranslationPacket.chapter_id == chapter_id)
            .order_by(TranslationPacket.created_at.asc())
        ).all()

        entries: list[dict[str, Any]] = []
        for packet in packets:
            experiment = self.experiment_service.run(packet.id, experiment_options)
            payload = experiment.payload
            issue_summary = _packet_issue_summary(issues_by_packet.get(packet.id, []))
            entries.append(
                {
                    "packet_id": packet.id,
                    "packet_type": packet.packet_type.value,
                    "current_block_type": ((payload.get("context_packet") or {}).get("current_blocks") or [{}])[0].get(
                        "block_type"
                    ),
                    "current_sentence_count": _current_sentence_count(payload),
                    "memory_gain": _memory_gain(payload),
                    "concept_gain": _concept_gain(payload),
                    "brief_from_memory": _brief_from_memory(payload),
                    "memory_signal_score": _memory_signal_score(payload),
                    "chapter_brief_source": (payload.get("context_sources") or {}).get("chapter_brief_source"),
                    "context_sources": payload.get("context_sources"),
                    **issue_summary,
                }
            )

        entries.sort(
            key=lambda item: (
                -int(item["memory_signal_score"]),
                -int(item["memory_gain"]),
                -int(item["concept_gain"]),
                -int(item["current_sentence_count"]),
                str(item["packet_id"]),
            )
        )

        top_candidate = entries[0] if entries else None
        return PacketExperimentScanArtifacts(
            payload={
                "chapter_id": chapter_id,
                "options": {
                    "include_memory_blocks": experiment_options.include_memory_blocks,
                    "include_chapter_concepts": experiment_options.include_chapter_concepts,
                    "prefer_memory_chapter_brief": experiment_options.prefer_memory_chapter_brief,
                    "prompt_layout": experiment_options.prompt_layout,
                    "execute": experiment_options.execute,
                },
                "packet_count": len(entries),
                "unresolved_packet_issue_count": len(unresolved_issues),
                "mixed_issue_packet_count": sum(1 for entry in entries if bool(entry.get("mixed_issue_types"))),
                "non_style_issue_packet_count": sum(1 for entry in entries if bool(entry.get("has_non_style_issue"))),
                "top_candidate": top_candidate,
                "entries": entries,
            }
        )
