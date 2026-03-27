from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.app.runtime.controllers.chapter_controller import ChapterController
from book_agent.domain.enums import JobScopeType, WorkItemScopeType, WorkItemStage
from book_agent.domain.models.ops import ChapterRun, PacketTask, WorkItem
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository
from book_agent.services.recovery_matrix import RecoveryDecision, RecoveryMatrixService
from book_agent.services.runtime_lane_health import LaneHealthResult, RuntimeLaneHealthService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _lane_health_payload(result: LaneHealthResult, *, observed_at: datetime) -> dict[str, object]:
    return {
        "state": result.health_state,
        "healthy": result.healthy,
        "terminal": result.terminal,
        "failure_family": result.failure_family.value if result.failure_family is not None else None,
        "reason_code": result.reason_code,
        "evidence_json": result.evidence_json,
        "observed_at": observed_at.isoformat(),
    }


def _decision_payload(decision: RecoveryDecision | None, *, evaluated_at: datetime) -> dict[str, object] | None:
    if decision is None:
        return None
    payload = asdict(decision)
    payload["failure_family"] = decision.failure_family.value
    payload["evaluated_at"] = evaluated_at.isoformat()
    return payload


@dataclass(frozen=True, slots=True)
class PacketLaneProjection:
    task: PacketTask
    chapter_run: ChapterRun
    work_item: WorkItem | None
    lane_health: LaneHealthResult
    attempt_count: int
    runtime_bundle_revision_id: str | None
    chapter_fingerprint: str | None


def _chapter_fingerprint_basis(
    result: LaneHealthResult,
    *,
    runtime_bundle_revision_id: str | None,
) -> dict[str, object] | None:
    if result.failure_family is None:
        return None
    return {
        "failure_family": result.failure_family.value,
        "reason_code": result.reason_code,
        "lane_health_state": result.health_state,
        "runtime_bundle_revision_id": runtime_bundle_revision_id,
        "last_error_class": result.evidence_json.get("last_error_class"),
        "work_item_status": result.evidence_json.get("work_item_status"),
    }


def _chapter_failure_fingerprint(
    result: LaneHealthResult,
    *,
    runtime_bundle_revision_id: str | None,
) -> str | None:
    basis = _chapter_fingerprint_basis(result, runtime_bundle_revision_id=runtime_bundle_revision_id)
    if basis is None:
        return None
    return json.dumps(basis, sort_keys=True, separators=(",", ":"))


class PacketController:
    """
    Packet-scoped controller.

    Current responsibility:
    - mirror-bind PacketTask rows to already-existing WorkItem attempts
    - project packet lane health and bounded recovery decisions
    - escalate repeated same-fingerprint packet failures to explicit chapter hold
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)
        self._chapter_controller = ChapterController(session=session)
        self._lane_health = RuntimeLaneHealthService()
        self._recovery_matrix = RecoveryMatrixService()

    def mirror_bind_work_items(self, *, run_id: str) -> int:
        """
        Returns the number of PacketTask rows updated with a (new) last_work_item_id.
        """
        packet_tasks = self._session.scalars(
            select(PacketTask)
            .join(ChapterRun, ChapterRun.id == PacketTask.chapter_run_id)
            .where(ChapterRun.run_id == run_id)
            .order_by(PacketTask.created_at.asc(), PacketTask.id.asc())
        ).all()

        updated = 0
        for task in packet_tasks:
            work_item = self._session.scalar(
                select(WorkItem)
                .where(
                    WorkItem.run_id == run_id,
                    WorkItem.stage == WorkItemStage.TRANSLATE,
                    WorkItem.scope_type == WorkItemScopeType.PACKET,
                    WorkItem.scope_id == task.packet_id,
                )
                .order_by(WorkItem.attempt.desc(), WorkItem.updated_at.desc(), WorkItem.id.desc())
            )
            if work_item is None:
                continue

            if task.last_work_item_id != work_item.id:
                task.last_work_item_id = work_item.id
                updated += 1
            task.attempt_count = max(int(task.attempt_count or 0), int(work_item.attempt or 0))
            task.last_error_class = work_item.error_class
            task.runtime_bundle_revision_id = work_item.runtime_bundle_revision_id

        self._session.flush()
        return updated

    def project_lane_health(self, *, run_id: str) -> int:
        observed_at = _utcnow()
        packet_tasks = self._session.execute(
            select(PacketTask, ChapterRun)
            .join(ChapterRun, ChapterRun.id == PacketTask.chapter_run_id)
            .where(ChapterRun.run_id == run_id)
            .order_by(PacketTask.created_at.asc(), PacketTask.id.asc())
        ).all()

        projections: list[PacketLaneProjection] = []
        fingerprint_occurrences: dict[tuple[str, str], int] = defaultdict(int)
        fingerprint_attempt_max: dict[tuple[str, str], int] = defaultdict(int)
        fingerprint_packet_ids: dict[tuple[str, str], list[str]] = defaultdict(list)
        for task, chapter_run in packet_tasks:
            work_item = self._session.scalar(
                select(WorkItem)
                .where(
                    WorkItem.run_id == run_id,
                    WorkItem.stage == WorkItemStage.TRANSLATE,
                    WorkItem.scope_type == WorkItemScopeType.PACKET,
                    WorkItem.scope_id == task.packet_id,
                )
                .order_by(WorkItem.attempt.desc(), WorkItem.updated_at.desc(), WorkItem.id.desc())
            )
            result = self._lane_health.evaluate_packet_task(task, work_item, now=observed_at)
            attempt_count = max(int(task.attempt_count or 0), int(work_item.attempt or 0)) if work_item else int(task.attempt_count or 0)
            runtime_bundle_revision_id = (
                work_item.runtime_bundle_revision_id if work_item is not None else task.runtime_bundle_revision_id
            )
            chapter_fingerprint = _chapter_failure_fingerprint(
                result,
                runtime_bundle_revision_id=runtime_bundle_revision_id,
            )
            projections.append(
                PacketLaneProjection(
                    task=task,
                    chapter_run=chapter_run,
                    work_item=work_item,
                    lane_health=result,
                    attempt_count=attempt_count,
                    runtime_bundle_revision_id=runtime_bundle_revision_id,
                    chapter_fingerprint=chapter_fingerprint,
                )
            )
            if chapter_fingerprint is None:
                continue
            fingerprint_key = (chapter_run.id, chapter_fingerprint)
            fingerprint_occurrences[fingerprint_key] += 1
            fingerprint_attempt_max[fingerprint_key] = max(fingerprint_attempt_max[fingerprint_key], attempt_count)
            fingerprint_packet_ids[fingerprint_key].append(task.packet_id)

        projected = 0
        chapter_hold_keys_recorded: set[tuple[str, str]] = set()
        for projection in projections:
            task = projection.task
            chapter_run = projection.chapter_run
            work_item = projection.work_item
            result = projection.lane_health
            fingerprint_key = (
                (chapter_run.id, projection.chapter_fingerprint)
                if projection.chapter_fingerprint is not None
                else None
            )
            decision = (
                self._recovery_matrix.evaluate(
                    result.failure_family,
                    signal=result.reason_code or "unknown",
                    attempt_count=projection.attempt_count,
                    fingerprint_occurrences=(
                        fingerprint_occurrences[fingerprint_key]
                        if fingerprint_key is not None
                        else 1
                    ),
                )
                if result.failure_family is not None
                else None
            )
            self._runtime_repo.update_packet_task(
                task.id,
                last_work_item_id=work_item.id if work_item is not None else None,
                attempt_count=projection.attempt_count,
                last_error_class=work_item.error_class if work_item is not None else task.last_error_class,
                runtime_bundle_revision_id=projection.runtime_bundle_revision_id,
            )
            self._runtime_repo.merge_packet_task_conditions(
                task.id,
                {"lane_health": _lane_health_payload(result, observed_at=observed_at)},
            )
            status_patch = {"runtime_v2": {"lane_health": _lane_health_payload(result, observed_at=observed_at)}}
            decision_payload = _decision_payload(decision, evaluated_at=observed_at)
            if decision_payload is not None:
                status_patch["runtime_v2"]["recovery_decision"] = decision_payload
            self._runtime_repo.merge_packet_task_status_detail(task.id, status_patch)
            self._runtime_repo.upsert_checkpoint(
                run_id=run_id,
                scope_type=JobScopeType.PACKET,
                scope_id=task.packet_id,
                checkpoint_key="packet_controller.lane_health",
                checkpoint_json={
                    "packet_task_id": task.id,
                    "chapter_run_id": chapter_run.id,
                    "chapter_id": chapter_run.chapter_id,
                    "lane_health": _lane_health_payload(result, observed_at=observed_at),
                    "recovery_decision": decision_payload,
                },
                generation=int(task.packet_generation or 1),
            )
            if (
                decision is not None
                and decision.recommended_action == "chapter_hold"
                and fingerprint_key is not None
                and fingerprint_key not in chapter_hold_keys_recorded
            ):
                affected_packet_ids = list(dict.fromkeys(fingerprint_packet_ids[fingerprint_key]))
                self._chapter_controller.record_runtime_chapter_hold(
                    chapter_run_id=chapter_run.id,
                    hold_reason="repair_exhausted",
                    next_action="manual_review",
                    evidence_json={
                        "fingerprint": projection.chapter_fingerprint,
                        "fingerprint_basis": _chapter_fingerprint_basis(
                            result,
                            runtime_bundle_revision_id=projection.runtime_bundle_revision_id,
                        ),
                        "failure_family": result.failure_family.value if result.failure_family is not None else None,
                        "reason_code": result.reason_code,
                        "lane_health_state": result.health_state,
                        "runtime_bundle_revision_id": projection.runtime_bundle_revision_id,
                        "retry_cap": decision.retry_cap,
                        "attempt_count": fingerprint_attempt_max[fingerprint_key],
                        "fingerprint_occurrences": fingerprint_occurrences[fingerprint_key],
                        "replay_scope": decision.replay_scope,
                        "next_boundary": decision.next_boundary,
                        "affected_packet_ids": affected_packet_ids,
                    },
                )
                chapter_hold_keys_recorded.add(fingerprint_key)
            projected += 1

        self._session.flush()
        return projected
