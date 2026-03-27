from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.app.runtime.controllers.review_controller import ReviewController
from book_agent.domain.enums import ChapterRunStatus, JobScopeType, PacketTaskAction, PacketType
from book_agent.domain.models.ops import ChapterRun
from book_agent.domain.models.translation import TranslationPacket
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChapterController:
    """
    Chapter-scoped controller.

    Current responsibility:
    - ensure PacketTask rows exist for TranslationPacket rows in the chapter
    - ensure ReviewSession rows exist for the active ChapterRun generation
    - record explicit chapter-boundary hold facts when packet repair is exhausted
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)
        self._review_controller = ReviewController(session=session)

    def ensure_packet_tasks(self, *, run_id: str) -> int:
        chapter_runs = self._session.scalars(select(ChapterRun).where(ChapterRun.run_id == run_id)).all()
        created = 0
        for chapter_run in chapter_runs:
            packet_rows = self._session.execute(
                select(TranslationPacket.id, TranslationPacket.packet_type).where(
                    TranslationPacket.chapter_id == chapter_run.chapter_id
                )
            ).all()
            for packet_id, packet_type in packet_rows:
                desired_action = _packet_task_action_for_packet_type(packet_type)
                existing = self._runtime_repo.get_packet_task_by_identity(
                    chapter_run_id=chapter_run.id,
                    packet_id=packet_id,
                    packet_generation=1,
                )
                if existing is not None:
                    continue
                self._runtime_repo.ensure_packet_task(
                    chapter_run_id=chapter_run.id,
                    packet_id=packet_id,
                    packet_generation=1,
                    desired_action=desired_action,
                )
                created += 1
        return created

    def ensure_review_sessions(self, *, run_id: str) -> int:
        chapter_runs = self._session.scalars(select(ChapterRun).where(ChapterRun.run_id == run_id)).all()
        created = 0
        for chapter_run in chapter_runs:
            result = self._review_controller.reconcile_review_session(chapter_run_id=chapter_run.id)
            created += int(result.created)
        return created

    def record_runtime_chapter_hold(
        self,
        *,
        chapter_run_id: str,
        hold_reason: str,
        next_action: str,
        evidence_json: dict[str, object],
    ) -> ChapterRun:
        chapter_run = self._runtime_repo.get_chapter_run(chapter_run_id)
        existing_hold = chapter_run.chapter_hold
        if (
            chapter_run.chapter_hold_active
            and chapter_run.status == ChapterRunStatus.PAUSED
            and chapter_run.pause_reason == hold_reason
            and isinstance(existing_hold, dict)
            and existing_hold.get("next_action") == next_action
            and dict(existing_hold.get("evidence_json") or {}) == dict(evidence_json)
        ):
            self._upsert_chapter_hold_checkpoint(
                chapter_run=chapter_run,
                hold_reason=hold_reason,
                next_action=next_action,
                evidence_json=dict(evidence_json),
                recorded_at=existing_hold.get("recorded_at"),
            )
            return chapter_run

        updated = self._runtime_repo.record_chapter_hold(
            chapter_run_id=chapter_run_id,
            hold_reason=hold_reason,
            evidence_json=dict(evidence_json),
            next_action=next_action,
        )
        now = _utcnow()
        hold = updated.chapter_hold or {}
        runtime_v2 = dict((updated.status_detail_json or {}).get("runtime_v2") or {})
        runtime_v2["chapter_hold"] = {
            "hold_reason": hold_reason,
            "next_action": next_action,
            "scope_boundary": "chapter",
            "evidence_json": dict(evidence_json),
            "recorded_at": hold.get("recorded_at", now.isoformat()),
        }
        updated.status = ChapterRunStatus.PAUSED
        updated.pause_reason = hold_reason
        updated.last_reconciled_at = now
        updated.status_detail_json = {
            **dict(updated.status_detail_json or {}),
            "runtime_v2": runtime_v2,
        }
        self._session.add(updated)
        self._session.flush()
        self._upsert_chapter_hold_checkpoint(
            chapter_run=updated,
            hold_reason=hold_reason,
            next_action=next_action,
            evidence_json=dict(evidence_json),
            recorded_at=runtime_v2["chapter_hold"]["recorded_at"],
        )
        return updated

    def _upsert_chapter_hold_checkpoint(
        self,
        *,
        chapter_run: ChapterRun,
        hold_reason: str,
        next_action: str,
        evidence_json: dict[str, object],
        recorded_at: str | None,
    ) -> None:
        self._runtime_repo.upsert_checkpoint(
            run_id=chapter_run.run_id,
            scope_type=JobScopeType.CHAPTER,
            scope_id=chapter_run.chapter_id,
            checkpoint_key="chapter_controller.chapter_hold",
            checkpoint_json={
                "chapter_run_id": chapter_run.id,
                "chapter_id": chapter_run.chapter_id,
                "generation": int(chapter_run.generation or 1),
                "hold_reason": hold_reason,
                "next_action": next_action,
                "scope_boundary": "chapter",
                "recorded_at": recorded_at,
                "evidence_json": dict(evidence_json),
            },
            generation=int(chapter_run.generation or 1),
        )


def _packet_task_action_for_packet_type(packet_type: PacketType) -> PacketTaskAction:
    if packet_type == PacketType.RETRANSLATE:
        return PacketTaskAction.RETRANSLATE
    return PacketTaskAction.TRANSLATE
