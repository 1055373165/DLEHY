from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from book_agent.domain.enums import RootCauseLayer


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    failure_family: RootCauseLayer
    default_action: str
    replay_scope: str
    retry_cap: int
    incident_threshold: int
    escalation_boundary: str
    exhaustion_action: str


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    failure_family: RootCauseLayer
    source_signal: str
    recommended_action: str
    replay_scope: str
    retry_cap: int
    incident_threshold: int
    escalation_boundary: str
    attempt_count: int
    fingerprint_occurrences: int
    should_retry: bool
    open_incident: bool
    escalate_scope: bool
    next_boundary: str


class RecoveryMatrixService:
    def __init__(self, policies: Mapping[RootCauseLayer, RecoveryPolicy] | None = None):
        self._policies = dict(policies or self._default_policies())

    def get_policy(self, failure_family: RootCauseLayer | str) -> RecoveryPolicy:
        normalized = self._normalize_family(failure_family)
        try:
            return self._policies[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported recovery family: {failure_family}") from exc

    def evaluate(
        self,
        failure_family: RootCauseLayer | str,
        *,
        signal: str,
        attempt_count: int,
        fingerprint_occurrences: int = 1,
    ) -> RecoveryDecision:
        policy = self.get_policy(failure_family)
        normalized_attempts = max(int(attempt_count), 0)
        normalized_occurrences = max(int(fingerprint_occurrences), 0)
        should_retry = normalized_attempts < policy.retry_cap
        open_incident = normalized_occurrences >= policy.incident_threshold
        escalate_scope = not should_retry and open_incident
        recommended_action = policy.exhaustion_action if escalate_scope else policy.default_action
        next_boundary = policy.escalation_boundary if escalate_scope else policy.replay_scope
        return RecoveryDecision(
            failure_family=policy.failure_family,
            source_signal=signal,
            recommended_action=recommended_action,
            replay_scope=policy.replay_scope,
            retry_cap=policy.retry_cap,
            incident_threshold=policy.incident_threshold,
            escalation_boundary=policy.escalation_boundary,
            attempt_count=normalized_attempts,
            fingerprint_occurrences=normalized_occurrences,
            should_retry=should_retry,
            open_incident=open_incident,
            escalate_scope=escalate_scope,
            next_boundary=next_boundary,
        )

    def _normalize_family(self, failure_family: RootCauseLayer | str) -> RootCauseLayer:
        if isinstance(failure_family, RootCauseLayer):
            return failure_family
        normalized = failure_family.strip().lower()
        alias_map = {
            "translate": RootCauseLayer.TRANSLATION,
            "translation": RootCauseLayer.TRANSLATION,
            "review": RootCauseLayer.REVIEW,
            "export": RootCauseLayer.EXPORT,
            "ops": RootCauseLayer.OPS,
        }
        try:
            return alias_map[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported recovery family: {failure_family}") from exc

    def _default_policies(self) -> dict[RootCauseLayer, RecoveryPolicy]:
        return {
            RootCauseLayer.TRANSLATION: RecoveryPolicy(
                failure_family=RootCauseLayer.TRANSLATION,
                default_action="rerun_packet",
                replay_scope="packet",
                retry_cap=3,
                incident_threshold=2,
                escalation_boundary="chapter",
                exhaustion_action="chapter_hold",
            ),
            RootCauseLayer.REVIEW: RecoveryPolicy(
                failure_family=RootCauseLayer.REVIEW,
                default_action="replay_review_session",
                replay_scope="review_session",
                retry_cap=2,
                incident_threshold=2,
                escalation_boundary="chapter",
                exhaustion_action="chapter_hold",
            ),
            RootCauseLayer.EXPORT: RecoveryPolicy(
                failure_family=RootCauseLayer.EXPORT,
                default_action="reexport_scope",
                replay_scope="export_scope",
                retry_cap=2,
                incident_threshold=1,
                escalation_boundary="run",
                exhaustion_action="escalate_export_scope",
            ),
            RootCauseLayer.OPS: RecoveryPolicy(
                failure_family=RootCauseLayer.OPS,
                default_action="open_runtime_incident",
                replay_scope="failed_scope",
                retry_cap=1,
                incident_threshold=1,
                escalation_boundary="runtime_bundle",
                exhaustion_action="freeze_and_rollback_bundle",
            ),
        }
