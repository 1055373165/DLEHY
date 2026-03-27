from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

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


class PacketController:
    """
    Packet-scoped controller (Phase A mirror-only).

    Responsibility:
    - mirror-bind PacketTask rows to already-existing WorkItem attempts
    - do not create new work items or infer health/state yet
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)
        self._lane_health = RuntimeLaneHealthService()
        self._recovery_matrix = RecoveryMatrixService()

    def mirror_bind_work_items(self, *, run_id: str) -> int:
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
            projections.append(
                PacketLaneProjection(
                    task=task,
                    chapter_run=chapter_run,
                    work_item=work_item,
                    lane_health=result,
                    attempt_count=attempt_count,
                )
            )

        projected = 0
        for projection in projections:
            task = projection.task
            work_item = projection.work_item
            result = projection.lane_health
            decision = (
                self._recovery_matrix.evaluate(
                    result.failure_family,
                    signal=result.reason_code or "unknown",
                    attempt_count=projection.attempt_count,
                )
                if result.failure_family is not None
                else None
            )
            self._runtime_repo.update_packet_task(
                task.id,
                last_work_item_id=work_item.id if work_item is not None else None,
                attempt_count=projection.attempt_count,
                last_error_class=work_item.error_class if work_item is not None else task.last_error_class,
                runtime_bundle_revision_id=(
                    work_item.runtime_bundle_revision_id if work_item is not None else task.runtime_bundle_revision_id
                ),
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
                    "chapter_run_id": projection.chapter_run.id,
                    "chapter_id": projection.chapter_run.chapter_id,
                    "lane_health": _lane_health_payload(result, observed_at=observed_at),
                    "recovery_decision": decision_payload,
                },
                generation=int(task.packet_generation or 1),
            )
            projected += 1

        self._session.flush()
        return projected
