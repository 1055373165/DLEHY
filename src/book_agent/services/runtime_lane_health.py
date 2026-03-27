from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from book_agent.domain.enums import (
    PacketTaskStatus,
    ReviewSessionStatus,
    ReviewTerminalityState,
    RootCauseLayer,
    WorkItemStatus,
)
from book_agent.domain.models.ops import PacketTask, ReviewSession, WorkItem


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _age_seconds(reference: datetime | None, *, now: datetime) -> float | None:
    normalized = _coerce_datetime(reference)
    if normalized is None:
        return None
    return max((now - normalized).total_seconds(), 0.0)


def _latest_timestamp(*values: datetime | None) -> datetime | None:
    normalized = [candidate for candidate in (_coerce_datetime(value) for value in values) if candidate is not None]
    return max(normalized) if normalized else None


@dataclass(frozen=True, slots=True)
class LaneHealthThresholds:
    packet_starvation_seconds: int = 1800
    review_starvation_seconds: int = 1800
    heartbeat_stale_seconds: int = 300
    non_terminal_grace_seconds: int = 300


@dataclass(frozen=True, slots=True)
class LaneHealthResult:
    scope_kind: str
    scope_id: str
    health_state: str
    healthy: bool
    terminal: bool
    failure_family: RootCauseLayer | None
    reason_code: str | None
    evidence_json: dict[str, Any]


class RuntimeLaneHealthService:
    def __init__(self, thresholds: LaneHealthThresholds | None = None):
        self.thresholds = thresholds or LaneHealthThresholds()

    def evaluate_packet_task(
        self,
        packet_task: PacketTask,
        work_item: WorkItem | None = None,
        *,
        now: datetime | None = None,
    ) -> LaneHealthResult:
        now = _coerce_datetime(now) or _utcnow()
        evidence = self._packet_evidence(packet_task=packet_task, work_item=work_item, now=now)

        if packet_task.status in {PacketTaskStatus.SUCCEEDED, PacketTaskStatus.CANCELLED}:
            return LaneHealthResult("packet", packet_task.id, "terminal", True, True, None, None, evidence)

        if work_item is None:
            stale_age = _age_seconds(_latest_timestamp(packet_task.updated_at, packet_task.created_at), now=now)
            if stale_age is not None and stale_age >= self.thresholds.packet_starvation_seconds:
                return LaneHealthResult(
                    "packet",
                    packet_task.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.TRANSLATION,
                    "missing_work_item_progress",
                    evidence,
                )
            return LaneHealthResult("packet", packet_task.id, "active", True, False, None, None, evidence)

        if work_item.status == WorkItemStatus.TERMINAL_FAILED:
            return LaneHealthResult(
                "packet",
                packet_task.id,
                "failed",
                False,
                False,
                RootCauseLayer.TRANSLATION,
                "work_item_terminal_failed",
                evidence,
            )

        if work_item.status == WorkItemStatus.RETRYABLE_FAILED:
            stale_age = _age_seconds(_latest_timestamp(work_item.finished_at, work_item.updated_at), now=now)
            if stale_age is not None and stale_age >= self.thresholds.packet_starvation_seconds:
                return LaneHealthResult(
                    "packet",
                    packet_task.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.TRANSLATION,
                    "retryable_failed_without_requeue",
                    evidence,
                )
            return LaneHealthResult("packet", packet_task.id, "recovering", True, False, None, None, evidence)

        if work_item.status in {WorkItemStatus.LEASED, WorkItemStatus.RUNNING}:
            if work_item.lease_expires_at and _coerce_datetime(work_item.lease_expires_at) < now:
                return LaneHealthResult(
                    "packet",
                    packet_task.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.TRANSLATION,
                    "lease_expired",
                    evidence,
                )
            heartbeat_age = _age_seconds(work_item.last_heartbeat_at, now=now)
            if heartbeat_age is not None and heartbeat_age >= self.thresholds.heartbeat_stale_seconds:
                return LaneHealthResult(
                    "packet",
                    packet_task.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.TRANSLATION,
                    "heartbeat_stale",
                    evidence,
                )
            runtime_age = _age_seconds(_latest_timestamp(work_item.started_at, work_item.updated_at), now=now)
            if runtime_age is not None and runtime_age >= self.thresholds.packet_starvation_seconds:
                return LaneHealthResult(
                    "packet",
                    packet_task.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.TRANSLATION,
                    "packet_runtime_stalled",
                    evidence,
                )

        return LaneHealthResult("packet", packet_task.id, "active", True, False, None, None, evidence)

    def evaluate_review_session(
        self,
        review_session: ReviewSession,
        work_item: WorkItem | None = None,
        *,
        now: datetime | None = None,
    ) -> LaneHealthResult:
        now = _coerce_datetime(now) or _utcnow()
        evidence = self._review_evidence(review_session=review_session, work_item=work_item, now=now)

        if (
            review_session.status
            in {ReviewSessionStatus.SUCCEEDED, ReviewSessionStatus.FAILED, ReviewSessionStatus.CANCELLED}
            and review_session.terminality_state
            in {ReviewTerminalityState.APPROVED, ReviewTerminalityState.BLOCKED}
        ):
            return LaneHealthResult("review_session", review_session.id, "terminal", True, True, None, None, evidence)

        if review_session.status != ReviewSessionStatus.ACTIVE and review_session.terminality_state == ReviewTerminalityState.OPEN:
            closure_age = _age_seconds(
                _latest_timestamp(review_session.last_reconciled_at, review_session.updated_at),
                now=now,
            )
            if closure_age is None or closure_age >= self.thresholds.non_terminal_grace_seconds:
                return LaneHealthResult(
                    "review_session",
                    review_session.id,
                    "deadlocked",
                    False,
                    False,
                    RootCauseLayer.REVIEW,
                    "non_terminal_closure",
                    evidence,
                )

        if work_item is None:
            stale_age = _age_seconds(
                _latest_timestamp(review_session.last_reconciled_at, review_session.updated_at, review_session.created_at),
                now=now,
            )
            if (
                review_session.status == ReviewSessionStatus.ACTIVE
                and stale_age is not None
                and stale_age >= self.thresholds.review_starvation_seconds
            ):
                return LaneHealthResult(
                    "review_session",
                    review_session.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.REVIEW,
                    "review_waiting_without_work_item",
                    evidence,
                )
            return LaneHealthResult("review_session", review_session.id, "active", True, False, None, None, evidence)

        if work_item.status in {WorkItemStatus.RETRYABLE_FAILED, WorkItemStatus.TERMINAL_FAILED}:
            stale_age = _age_seconds(_latest_timestamp(work_item.finished_at, work_item.updated_at), now=now)
            if stale_age is None or stale_age >= self.thresholds.review_starvation_seconds:
                return LaneHealthResult(
                    "review_session",
                    review_session.id,
                    "deadlocked",
                    False,
                    False,
                    RootCauseLayer.REVIEW,
                    "review_failed_without_terminality",
                    evidence,
                )

        if work_item.status in {WorkItemStatus.LEASED, WorkItemStatus.RUNNING}:
            if work_item.lease_expires_at and _coerce_datetime(work_item.lease_expires_at) < now:
                return LaneHealthResult(
                    "review_session",
                    review_session.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.REVIEW,
                    "lease_expired",
                    evidence,
                )
            heartbeat_age = _age_seconds(work_item.last_heartbeat_at, now=now)
            if heartbeat_age is not None and heartbeat_age >= self.thresholds.heartbeat_stale_seconds:
                return LaneHealthResult(
                    "review_session",
                    review_session.id,
                    "starved",
                    False,
                    False,
                    RootCauseLayer.REVIEW,
                    "heartbeat_stale",
                    evidence,
                )

        return LaneHealthResult("review_session", review_session.id, "active", True, False, None, None, evidence)

    def _packet_evidence(
        self,
        *,
        packet_task: PacketTask,
        work_item: WorkItem | None,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "evidence_version": 1,
            "captured_at": now.isoformat(),
            "packet_task_id": packet_task.id,
            "packet_status": packet_task.status.value,
            "attempt_count": int(packet_task.attempt_count or 0),
            "last_error_class": packet_task.last_error_class,
            "work_item_status": work_item.status.value if work_item is not None else None,
            "lease_expires_at": _coerce_datetime(work_item.lease_expires_at).isoformat()
            if work_item is not None and work_item.lease_expires_at
            else None,
            "last_heartbeat_at": _coerce_datetime(work_item.last_heartbeat_at).isoformat()
            if work_item is not None and work_item.last_heartbeat_at
            else None,
        }

    def _review_evidence(
        self,
        *,
        review_session: ReviewSession,
        work_item: WorkItem | None,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "evidence_version": 1,
            "captured_at": now.isoformat(),
            "review_session_id": review_session.id,
            "review_status": review_session.status.value,
            "terminality_state": review_session.terminality_state.value,
            "desired_generation": int(review_session.desired_generation or 0),
            "observed_generation": int(review_session.observed_generation or 0),
            "work_item_status": work_item.status.value if work_item is not None else None,
            "lease_expires_at": _coerce_datetime(work_item.lease_expires_at).isoformat()
            if work_item is not None and work_item.lease_expires_at
            else None,
            "last_heartbeat_at": _coerce_datetime(work_item.last_heartbeat_at).isoformat()
            if work_item is not None and work_item.last_heartbeat_at
            else None,
        }
