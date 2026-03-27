from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from book_agent.domain.enums import (
    JobScopeType,
    ReviewSessionStatus,
    ReviewTerminalityState,
    WorkItemScopeType,
    WorkItemStage,
)
from book_agent.domain.models.ops import DocumentRun, WorkItem
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


@dataclass(slots=True)
class ReviewSessionReconcileResult:
    review_session_id: str
    created: bool


class ReviewController:
    """
    Review-plane scaffold for explicit ReviewSession resources.

    Phase A behavior is intentionally narrow:
    - ensure one ReviewSession exists for the active ChapterRun generation
    - keep scope/runtime-bundle metadata mirrored from the owning run
    - materialize a chapter-scoped checkpoint for later review-lane controllers
    """

    def __init__(self, *, session: Session):
        self._session = session
        self._runtime_repo = RuntimeResourcesRepository(session)
        self._lane_health = RuntimeLaneHealthService()
        self._recovery_matrix = RecoveryMatrixService()

    def reconcile_review_session(self, *, chapter_run_id: str) -> ReviewSessionReconcileResult:
        chapter_run = self._runtime_repo.get_chapter_run(chapter_run_id)
        run = self._session.get(DocumentRun, chapter_run.run_id)
        if run is None:
            raise ValueError(f"DocumentRun not found for ChapterRun: {chapter_run.run_id}")

        desired_generation = int(chapter_run.generation or 1)
        observed_generation = int(chapter_run.observed_generation or desired_generation)
        scope_json = {
            "run_id": chapter_run.run_id,
            "document_id": chapter_run.document_id,
            "chapter_id": chapter_run.chapter_id,
        }

        existing = self._runtime_repo.get_review_session_by_identity(
            chapter_run_id=chapter_run.id,
            desired_generation=desired_generation,
        )
        created = existing is None
        review_session = self._runtime_repo.ensure_review_session(
            chapter_run_id=chapter_run.id,
            desired_generation=desired_generation,
            observed_generation=observed_generation,
            scope_json=scope_json,
            runtime_bundle_revision_id=run.runtime_bundle_revision_id,
        )
        review_session = self._runtime_repo.update_review_session(
            review_session.id,
            observed_generation=observed_generation,
            scope_json=scope_json,
            runtime_bundle_revision_id=run.runtime_bundle_revision_id,
            last_reconciled_at=_utcnow(),
        )
        work_item = self._session.scalar(
            select(WorkItem)
            .where(
                WorkItem.run_id == chapter_run.run_id,
                WorkItem.stage == WorkItemStage.REVIEW,
                WorkItem.scope_type == WorkItemScopeType.CHAPTER,
                WorkItem.scope_id == chapter_run.chapter_id,
            )
            .order_by(WorkItem.attempt.desc(), WorkItem.updated_at.desc(), WorkItem.id.desc())
        )
        should_project = (
            review_session.status == ReviewSessionStatus.ACTIVE
            or work_item is not None
            or review_session.terminality_state == ReviewTerminalityState.OPEN
        )
        if should_project:
            observed_at = _utcnow()
            result = self._lane_health.evaluate_review_session(review_session, work_item, now=observed_at)
            decision = (
                self._recovery_matrix.evaluate(
                    result.failure_family,
                    signal=result.reason_code or "unknown",
                    attempt_count=int(work_item.attempt or 0) if work_item is not None else 0,
                )
                if result.failure_family is not None
                else None
            )
            self._runtime_repo.update_review_session(
                review_session.id,
                last_work_item_id=work_item.id if work_item is not None else None,
                last_reconciled_at=observed_at,
            )
            self._runtime_repo.merge_review_session_conditions(
                review_session.id,
                {"lane_health": _lane_health_payload(result, observed_at=observed_at)},
            )
            status_patch = {"runtime_v2": {"lane_health": _lane_health_payload(result, observed_at=observed_at)}}
            decision_payload = _decision_payload(decision, evaluated_at=observed_at)
            if decision_payload is not None:
                status_patch["runtime_v2"]["recovery_decision"] = decision_payload
            self._runtime_repo.merge_review_session_status_detail(review_session.id, status_patch)
            self._runtime_repo.upsert_checkpoint(
                run_id=chapter_run.run_id,
                scope_type=JobScopeType.CHAPTER,
                scope_id=chapter_run.chapter_id,
                checkpoint_key="review_controller.lane_health",
                checkpoint_json={
                    "chapter_run_id": chapter_run.id,
                    "review_session_id": review_session.id,
                    "lane_health": _lane_health_payload(result, observed_at=observed_at),
                    "recovery_decision": decision_payload,
                },
                generation=desired_generation,
            )
            return ReviewSessionReconcileResult(review_session_id=review_session.id, created=created)
        self._runtime_repo.upsert_checkpoint(
            run_id=chapter_run.run_id,
            scope_type=JobScopeType.CHAPTER,
            scope_id=chapter_run.chapter_id,
            checkpoint_key="review_controller.lane_health",
            checkpoint_json={
                "chapter_run_id": chapter_run.id,
                "review_session_id": review_session.id,
                "review_desired_generation": desired_generation,
                "review_observed_generation": observed_generation,
                "runtime_bundle_revision_id": run.runtime_bundle_revision_id,
            },
            generation=desired_generation,
        )
        return ReviewSessionReconcileResult(review_session_id=review_session.id, created=created)
