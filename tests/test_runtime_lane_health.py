import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from book_agent.app.runtime.controllers.packet_controller import PacketController
from book_agent.domain.enums import (
    ChapterRunPhase,
    ChapterRunStatus,
    ChapterStatus,
    DocumentRunType,
    DocumentStatus,
    DocumentRunStatus,
    JobScopeType,
    PacketTaskAction,
    PacketTaskStatus,
    PacketStatus,
    PacketType,
    ReviewSessionStatus,
    ReviewTerminalityState,
    RootCauseLayer,
    SourceType,
    WorkItemScopeType,
    WorkItemStage,
    WorkItemStatus,
)
from book_agent.domain.models import Chapter, Document
from book_agent.domain.models.ops import ChapterRun, DocumentRun, PacketTask, RuntimeCheckpoint, ReviewSession, WorkItem
from book_agent.domain.models.translation import TranslationPacket
from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository
from book_agent.services.runtime_lane_health import LaneHealthThresholds, RuntimeLaneHealthService


class RuntimeLaneHealthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)
        self.service = RuntimeLaneHealthService(
            LaneHealthThresholds(
                packet_starvation_seconds=600,
                review_starvation_seconds=600,
                heartbeat_stale_seconds=120,
                non_terminal_grace_seconds=60,
            )
        )

    def _packet_task(self, *, status: PacketTaskStatus = PacketTaskStatus.RUNNING) -> PacketTask:
        return PacketTask(
            id=str(uuid4()),
            chapter_run_id=str(uuid4()),
            packet_id=str(uuid4()),
            packet_generation=1,
            desired_action=PacketTaskAction.TRANSLATE,
            status=status,
            input_version_bundle_json={},
            attempt_count=1,
            conditions_json={},
            status_detail_json={},
            created_at=self.now - timedelta(minutes=20),
            updated_at=self.now - timedelta(minutes=20),
        )

    def _review_session(
        self,
        *,
        status: ReviewSessionStatus = ReviewSessionStatus.ACTIVE,
        terminality_state: ReviewTerminalityState = ReviewTerminalityState.OPEN,
    ) -> ReviewSession:
        return ReviewSession(
            id=str(uuid4()),
            chapter_run_id=str(uuid4()),
            desired_generation=1,
            observed_generation=1,
            status=status,
            terminality_state=terminality_state,
            scope_json={},
            conditions_json={},
            status_detail_json={},
            created_at=self.now - timedelta(minutes=20),
            updated_at=self.now - timedelta(minutes=20),
        )

    def _work_item(
        self,
        *,
        status: WorkItemStatus,
        stage: WorkItemStage,
        scope_type: WorkItemScopeType,
    ) -> WorkItem:
        return WorkItem(
            id=str(uuid4()),
            run_id=str(uuid4()),
            stage=stage,
            scope_type=scope_type,
            scope_id=str(uuid4()),
            attempt=1,
            priority=100,
            status=status,
            lease_owner="worker-a" if status in {WorkItemStatus.LEASED, WorkItemStatus.RUNNING} else None,
            lease_expires_at=self.now - timedelta(minutes=1),
            last_heartbeat_at=self.now - timedelta(minutes=5),
            started_at=self.now - timedelta(minutes=25),
            updated_at=self.now - timedelta(minutes=5),
            finished_at=self.now - timedelta(minutes=5)
            if status in {WorkItemStatus.RETRYABLE_FAILED, WorkItemStatus.TERMINAL_FAILED}
            else None,
            input_version_bundle_json={},
            output_artifact_refs_json={},
            error_detail_json={},
        )

    def test_packet_lane_detects_expired_lease_starvation(self) -> None:
        result = self.service.evaluate_packet_task(
            self._packet_task(),
            self._work_item(
                status=WorkItemStatus.RUNNING,
                stage=WorkItemStage.TRANSLATE,
                scope_type=WorkItemScopeType.PACKET,
            ),
            now=self.now,
        )

        self.assertEqual(result.health_state, "starved")
        self.assertFalse(result.healthy)
        self.assertEqual(result.reason_code, "lease_expired")
        self.assertEqual(result.failure_family, RootCauseLayer.TRANSLATION)
        self.assertEqual(result.evidence_json["work_item_status"], WorkItemStatus.RUNNING.value)

    def test_packet_lane_treats_recent_retryable_failure_as_recovering(self) -> None:
        work_item = self._work_item(
            status=WorkItemStatus.RETRYABLE_FAILED,
            stage=WorkItemStage.TRANSLATE,
            scope_type=WorkItemScopeType.PACKET,
        )
        work_item.finished_at = self.now - timedelta(seconds=30)
        work_item.updated_at = self.now - timedelta(seconds=30)

        result = self.service.evaluate_packet_task(self._packet_task(), work_item, now=self.now)

        self.assertEqual(result.health_state, "recovering")
        self.assertTrue(result.healthy)
        self.assertIsNone(result.failure_family)

    def test_review_lane_detects_non_terminal_closure(self) -> None:
        review_session = self._review_session(status=ReviewSessionStatus.SUCCEEDED)
        review_session.last_reconciled_at = self.now - timedelta(minutes=5)

        result = self.service.evaluate_review_session(review_session, now=self.now)

        self.assertEqual(result.health_state, "deadlocked")
        self.assertFalse(result.healthy)
        self.assertEqual(result.reason_code, "non_terminal_closure")
        self.assertEqual(result.failure_family, RootCauseLayer.REVIEW)

    def test_review_lane_treats_blocked_terminal_state_as_healthy_terminal(self) -> None:
        review_session = self._review_session(
            status=ReviewSessionStatus.FAILED,
            terminality_state=ReviewTerminalityState.BLOCKED,
        )

        result = self.service.evaluate_review_session(review_session, now=self.now)

        self.assertEqual(result.health_state, "terminal")
        self.assertTrue(result.healthy)
        self.assertTrue(result.terminal)


class PacketControllerLaneHealthProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = build_session_factory(engine=self.engine)

    def test_packet_controller_projects_lane_health_and_recovery_checkpoint(self) -> None:
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            document = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"packet-controller-{uuid4()}",
                source_path="/tmp/packet-controller.epub",
                title="Packet Controller",
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

            packet = TranslationPacket(
                chapter_id=chapter.id,
                block_start_id=None,
                block_end_id=None,
                packet_type=PacketType.TRANSLATE,
                book_profile_version=1,
                chapter_brief_version=1,
                termbase_version=1,
                entity_snapshot_version=1,
                style_snapshot_version=1,
                packet_json={"packet_ordinal": 1},
                risk_score=0.1,
                status=PacketStatus.BUILT,
            )
            session.add(packet)
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
                desired_phase=ChapterRunPhase.TRANSLATE,
                observed_phase=ChapterRunPhase.TRANSLATE,
                status=ChapterRunStatus.ACTIVE,
                generation=1,
                observed_generation=1,
                conditions_json={},
                status_detail_json={},
            )
            session.add(chapter_run)
            session.flush()

            packet_task = PacketTask(
                chapter_run_id=chapter_run.id,
                packet_id=packet.id,
                packet_generation=1,
                desired_action=PacketTaskAction.TRANSLATE,
                status=PacketTaskStatus.RUNNING,
                input_version_bundle_json={},
                attempt_count=1,
                conditions_json={},
                status_detail_json={},
                created_at=now - timedelta(minutes=30),
                updated_at=now - timedelta(minutes=30),
            )
            session.add(packet_task)
            session.flush()

            work_item = WorkItem(
                run_id=run.id,
                stage=WorkItemStage.TRANSLATE,
                scope_type=WorkItemScopeType.PACKET,
                scope_id=packet.id,
                attempt=1,
                priority=100,
                status=WorkItemStatus.RUNNING,
                lease_owner="worker-a",
                lease_expires_at=now - timedelta(seconds=1),
                last_heartbeat_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=20),
                updated_at=now - timedelta(minutes=5),
                input_version_bundle_json={},
                output_artifact_refs_json={},
                error_detail_json={},
            )
            session.add(work_item)
            session.commit()

            controller = PacketController(session=session)
            projected = controller.project_lane_health(run_id=run.id)
            session.commit()

            self.assertEqual(projected, 1)

            persisted = RuntimeResourcesRepository(session).get_packet_task(packet_task.id)
            self.assertEqual(persisted.last_work_item_id, work_item.id)
            self.assertEqual(persisted.conditions_json["lane_health"]["state"], "starved")
            runtime_v2 = persisted.status_detail_json["runtime_v2"]
            self.assertEqual(runtime_v2["lane_health"]["reason_code"], "lease_expired")
            self.assertEqual(runtime_v2["recovery_decision"]["recommended_action"], "rerun_packet")

            checkpoint = session.query(RuntimeCheckpoint).filter(
                RuntimeCheckpoint.run_id == run.id,
                RuntimeCheckpoint.scope_id == packet.id,
                RuntimeCheckpoint.checkpoint_key == "packet_controller.lane_health",
            ).one()
            self.assertEqual(checkpoint.checkpoint_json["lane_health"]["state"], "starved")

    def test_packet_controller_escalates_repeated_packet_failures_to_chapter_hold(self) -> None:
        now = datetime.now(timezone.utc)
        bundle_revision_id = str(uuid4())
        with self.session_factory() as session:
            document = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"packet-chapter-hold-{uuid4()}",
                source_path="/tmp/packet-chapter-hold.epub",
                title="Packet Chapter Hold",
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

            packet_a = TranslationPacket(
                chapter_id=chapter.id,
                block_start_id=None,
                block_end_id=None,
                packet_type=PacketType.TRANSLATE,
                book_profile_version=1,
                chapter_brief_version=1,
                termbase_version=1,
                entity_snapshot_version=1,
                style_snapshot_version=1,
                packet_json={"packet_ordinal": 1},
                risk_score=0.1,
                status=PacketStatus.BUILT,
            )
            packet_b = TranslationPacket(
                chapter_id=chapter.id,
                block_start_id=None,
                block_end_id=None,
                packet_type=PacketType.TRANSLATE,
                book_profile_version=1,
                chapter_brief_version=1,
                termbase_version=1,
                entity_snapshot_version=1,
                style_snapshot_version=1,
                packet_json={"packet_ordinal": 2},
                risk_score=0.1,
                status=PacketStatus.BUILT,
            )
            session.add_all([packet_a, packet_b])
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
                desired_phase=ChapterRunPhase.TRANSLATE,
                observed_phase=ChapterRunPhase.TRANSLATE,
                status=ChapterRunStatus.ACTIVE,
                generation=1,
                observed_generation=1,
                conditions_json={},
                status_detail_json={},
            )
            session.add(chapter_run)
            session.flush()

            packet_task_a = PacketTask(
                chapter_run_id=chapter_run.id,
                packet_id=packet_a.id,
                packet_generation=1,
                desired_action=PacketTaskAction.TRANSLATE,
                status=PacketTaskStatus.RUNNING,
                input_version_bundle_json={},
                attempt_count=3,
                conditions_json={},
                status_detail_json={},
                created_at=now - timedelta(minutes=30),
                updated_at=now - timedelta(minutes=30),
            )
            packet_task_b = PacketTask(
                chapter_run_id=chapter_run.id,
                packet_id=packet_b.id,
                packet_generation=1,
                desired_action=PacketTaskAction.TRANSLATE,
                status=PacketTaskStatus.RUNNING,
                input_version_bundle_json={},
                attempt_count=3,
                conditions_json={},
                status_detail_json={},
                created_at=now - timedelta(minutes=29),
                updated_at=now - timedelta(minutes=29),
            )
            session.add_all([packet_task_a, packet_task_b])
            session.flush()

            work_item_a = WorkItem(
                run_id=run.id,
                stage=WorkItemStage.TRANSLATE,
                scope_type=WorkItemScopeType.PACKET,
                scope_id=packet_a.id,
                attempt=3,
                priority=100,
                status=WorkItemStatus.RUNNING,
                lease_owner="worker-a",
                lease_expires_at=now - timedelta(seconds=1),
                last_heartbeat_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=20),
                updated_at=now - timedelta(minutes=5),
                runtime_bundle_revision_id=bundle_revision_id,
                input_version_bundle_json={},
                output_artifact_refs_json={},
                error_detail_json={},
            )
            work_item_b = WorkItem(
                run_id=run.id,
                stage=WorkItemStage.TRANSLATE,
                scope_type=WorkItemScopeType.PACKET,
                scope_id=packet_b.id,
                attempt=3,
                priority=100,
                status=WorkItemStatus.RUNNING,
                lease_owner="worker-b",
                lease_expires_at=now - timedelta(seconds=1),
                last_heartbeat_at=now - timedelta(minutes=10),
                started_at=now - timedelta(minutes=19),
                updated_at=now - timedelta(minutes=4),
                runtime_bundle_revision_id=bundle_revision_id,
                input_version_bundle_json={},
                output_artifact_refs_json={},
                error_detail_json={},
            )
            session.add_all([work_item_a, work_item_b])
            session.commit()

            controller = PacketController(session=session)
            projected = controller.project_lane_health(run_id=run.id)
            session.commit()

            self.assertEqual(projected, 2)

            persisted_chapter_run = session.get(ChapterRun, chapter_run.id)
            persisted_tasks = session.query(PacketTask).filter(PacketTask.chapter_run_id == chapter_run.id).all()
            chapter_hold = persisted_chapter_run.conditions_json["chapter_hold"]
            self.assertEqual(persisted_chapter_run.status, ChapterRunStatus.PAUSED)
            self.assertEqual(persisted_chapter_run.pause_reason, "repair_exhausted")
            self.assertEqual(chapter_hold["next_action"], "manual_review")
            self.assertEqual(chapter_hold["evidence_json"]["fingerprint_occurrences"], 2)
            self.assertEqual(chapter_hold["evidence_json"]["retry_cap"], 3)
            self.assertEqual(chapter_hold["evidence_json"]["next_boundary"], "chapter")
            self.assertCountEqual(
                chapter_hold["evidence_json"]["affected_packet_ids"],
                [packet_a.id, packet_b.id],
            )
            self.assertEqual(
                persisted_chapter_run.status_detail_json["runtime_v2"]["chapter_hold"]["scope_boundary"],
                "chapter",
            )
            self.assertTrue(
                all(
                    task.status_detail_json["runtime_v2"]["recovery_decision"]["recommended_action"] == "chapter_hold"
                    for task in persisted_tasks
                )
            )

            chapter_checkpoint = session.query(RuntimeCheckpoint).filter(
                RuntimeCheckpoint.run_id == run.id,
                RuntimeCheckpoint.scope_type == JobScopeType.CHAPTER,
                RuntimeCheckpoint.scope_id == chapter.id,
                RuntimeCheckpoint.checkpoint_key == "chapter_controller.chapter_hold",
            ).one()
            self.assertEqual(chapter_checkpoint.checkpoint_json["hold_reason"], "repair_exhausted")
            self.assertEqual(chapter_checkpoint.checkpoint_json["scope_boundary"], "chapter")
            self.assertCountEqual(
                chapter_checkpoint.checkpoint_json["evidence_json"]["affected_packet_ids"],
                [packet_a.id, packet_b.id],
            )
