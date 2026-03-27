import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from book_agent.app.runtime.controllers.review_controller import ReviewController
from book_agent.app.runtime.controllers.run_controller import RunController
from book_agent.domain.enums import (
    ChapterRunPhase,
    ChapterRunStatus,
    ChapterStatus,
    DocumentRunStatus,
    DocumentRunType,
    DocumentStatus,
    JobScopeType,
    ReviewSessionStatus,
    ReviewTerminalityState,
    RootCauseLayer,
    SourceType,
    WorkItemScopeType,
    WorkItemStage,
    WorkItemStatus,
)
from book_agent.domain.models import Chapter, Document
from book_agent.domain.models.ops import ChapterRun, DocumentRun, RuntimeCheckpoint, WorkItem
from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository
from book_agent.services.recovery_matrix import RecoveryMatrixService


class RecoveryMatrixServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RecoveryMatrixService()

    def test_translation_policy_stays_packet_local_before_exhaustion(self) -> None:
        policy = self.service.get_policy("translate")
        decision = self.service.evaluate(
            "translate",
            signal="lease_expired",
            attempt_count=1,
            fingerprint_occurrences=1,
        )

        self.assertEqual(policy.failure_family, RootCauseLayer.TRANSLATION)
        self.assertEqual(policy.default_action, "rerun_packet")
        self.assertEqual(policy.replay_scope, "packet")
        self.assertEqual(policy.retry_cap, 3)
        self.assertEqual(decision.recommended_action, "rerun_packet")
        self.assertTrue(decision.should_retry)
        self.assertFalse(decision.open_incident)
        self.assertFalse(decision.escalate_scope)
        self.assertEqual(decision.next_boundary, "packet")

    def test_review_decision_escalates_to_chapter_hold_after_exhaustion(self) -> None:
        decision = self.service.evaluate(
            RootCauseLayer.REVIEW,
            signal="non_terminal_closure",
            attempt_count=2,
            fingerprint_occurrences=2,
        )

        self.assertEqual(decision.recommended_action, "chapter_hold")
        self.assertFalse(decision.should_retry)
        self.assertTrue(decision.open_incident)
        self.assertTrue(decision.escalate_scope)
        self.assertEqual(decision.next_boundary, "chapter")
        self.assertEqual(decision.replay_scope, "review_session")

    def test_ops_decision_freezes_and_rolls_back_bundle_when_exhausted(self) -> None:
        decision = self.service.evaluate(
            "ops",
            signal="canary_regression",
            attempt_count=1,
            fingerprint_occurrences=1,
        )

        self.assertEqual(decision.failure_family, RootCauseLayer.OPS)
        self.assertEqual(decision.recommended_action, "freeze_and_rollback_bundle")
        self.assertFalse(decision.should_retry)
        self.assertTrue(decision.open_incident)
        self.assertTrue(decision.escalate_scope)
        self.assertEqual(decision.next_boundary, "runtime_bundle")

    def test_unknown_family_raises_clear_error(self) -> None:
        with self.assertRaises(ValueError):
            self.service.get_policy("unknown-family")


class ReviewAndRunProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = build_session_factory(engine=self.engine)

    def test_review_and_run_controllers_project_recovery_state(self) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            document = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"review-run-projection-{uuid4()}",
                source_path="/tmp/review-run-projection.epub",
                title="Review Run Projection",
                author="Tester",
                src_lang="en",
                tgt_lang="zh",
                status=DocumentStatus.ACTIVE,
                parser_version=1,
                segmentation_version=1,
            )
            session.add(document)
            session.flush()

            chapter = Chapter(
                document_id=document.id,
                ordinal=1,
                title_src="Chapter 1",
                status=ChapterStatus.PACKET_BUILT,
                metadata_json={},
            )
            session.add(chapter)
            session.flush()

            run = DocumentRun(
                document_id=document.id,
                run_type=DocumentRunType.TRANSLATE_FULL,
                status=DocumentRunStatus.RUNNING,
                requested_by="test",
                priority=100,
                status_detail_json={},
            )
            session.add(run)
            session.flush()

            chapter_run = ChapterRun(
                run_id=run.id,
                document_id=document.id,
                chapter_id=chapter.id,
                desired_phase=ChapterRunPhase.REVIEW,
                observed_phase=ChapterRunPhase.REVIEW,
                status=ChapterRunStatus.ACTIVE,
                generation=1,
                observed_generation=1,
                conditions_json={},
                status_detail_json={},
            )
            session.add(chapter_run)
            session.flush()

            repo = RuntimeResourcesRepository(session)
            review_session = repo.ensure_review_session(
                chapter_run_id=chapter_run.id,
                desired_generation=1,
                observed_generation=1,
                scope_json={"run_id": run.id, "document_id": document.id, "chapter_id": chapter.id},
                runtime_bundle_revision_id=None,
            )
            work_item = WorkItem(
                run_id=run.id,
                stage=WorkItemStage.REVIEW,
                scope_type=WorkItemScopeType.CHAPTER,
                scope_id=chapter.id,
                attempt=2,
                priority=100,
                status=WorkItemStatus.RETRYABLE_FAILED,
                lease_owner=None,
                lease_expires_at=None,
                last_heartbeat_at=now - timedelta(minutes=40),
                started_at=now - timedelta(minutes=45),
                updated_at=now - timedelta(minutes=40),
                finished_at=now - timedelta(minutes=40),
                input_version_bundle_json={},
                output_artifact_refs_json={},
                error_detail_json={},
            )
            session.add(work_item)
            session.commit()

            review_controller = ReviewController(session=session)
            review_controller.reconcile_review_session(chapter_run_id=chapter_run.id)
            projection = RunController(session=session).project_run_health(run_id=run.id)
            session.commit()

            self.assertEqual(projection.updated_chapter_runs, 1)
            self.assertEqual(projection.unhealthy_packet_tasks, 0)
            self.assertEqual(projection.unhealthy_review_sessions, 1)

            updated_review = repo.get_review_session(review_session.id)
            runtime_v2 = updated_review.status_detail_json["runtime_v2"]
            self.assertEqual(updated_review.conditions_json["lane_health"]["state"], "deadlocked")
            self.assertEqual(runtime_v2["recovery_decision"]["recommended_action"], "replay_review_session")
            self.assertEqual(runtime_v2["recovery_decision"]["next_boundary"], "review_session")

            updated_chapter = repo.get_chapter_run(chapter_run.id)
            summary = updated_chapter.conditions_json["lane_health_summary"]
            self.assertEqual(summary["unhealthy_review_count"], 1)
            self.assertEqual(summary["review_states"], ["deadlocked"])

            review_checkpoint = session.query(RuntimeCheckpoint).filter(
                RuntimeCheckpoint.run_id == run.id,
                RuntimeCheckpoint.scope_type == JobScopeType.CHAPTER,
                RuntimeCheckpoint.scope_id == chapter.id,
                RuntimeCheckpoint.checkpoint_key == "review_controller.lane_health",
            ).one()
            self.assertEqual(review_checkpoint.checkpoint_json["lane_health"]["state"], "deadlocked")

            run_checkpoint = session.query(RuntimeCheckpoint).filter(
                RuntimeCheckpoint.run_id == run.id,
                RuntimeCheckpoint.scope_type == JobScopeType.DOCUMENT,
                RuntimeCheckpoint.scope_id == document.id,
                RuntimeCheckpoint.checkpoint_key == "run_controller.phase2.health",
            ).one()
            self.assertEqual(run_checkpoint.checkpoint_json["unhealthy_review_sessions"], 1)
