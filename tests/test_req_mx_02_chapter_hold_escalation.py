import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from book_agent.app.runtime.controllers.packet_controller import PacketController
from book_agent.domain.enums import (
    ChapterRunPhase,
    ChapterRunStatus,
    ChapterStatus,
    DocumentRunStatus,
    DocumentRunType,
    DocumentStatus,
    JobScopeType,
    PacketTaskAction,
    PacketTaskStatus,
    PacketStatus,
    PacketType,
    SourceType,
    WorkItemScopeType,
    WorkItemStage,
    WorkItemStatus,
)
from book_agent.domain.models import Chapter, Document
from book_agent.domain.models.ops import ChapterRun, DocumentRun, PacketTask, RunAuditEvent, RuntimeCheckpoint, WorkItem
from book_agent.domain.models.translation import TranslationPacket
from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory


class ReqMx02ChapterHoldEscalationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = build_session_factory(engine=self.engine)

    def test_req_mx_02_repeated_packet_runtime_failure_escalates_to_chapter_boundary(self) -> None:
        now = datetime.now(timezone.utc)
        bundle_revision_id = str(uuid4())

        with self.session_factory() as session:
            document = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"req-mx-02-{uuid4()}",
                source_path="/tmp/req-mx-02.epub",
                title="REQ-MX-02",
                author="Tester",
                src_lang="en",
                tgt_lang="zh",
                status=DocumentStatus.ACTIVE,
                parser_version=1,
                segmentation_version=1,
            )
            session.add(document)
            session.flush()

            target_chapter = Chapter(
                document_id=document.id,
                ordinal=1,
                title_src="Target Chapter",
                status=ChapterStatus.PACKET_BUILT,
                metadata_json={},
            )
            untouched_chapter = Chapter(
                document_id=document.id,
                ordinal=2,
                title_src="Untouched Chapter",
                status=ChapterStatus.PACKET_BUILT,
                metadata_json={},
            )
            session.add_all([target_chapter, untouched_chapter])
            session.flush()

            packet_a = TranslationPacket(
                chapter_id=target_chapter.id,
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
                chapter_id=target_chapter.id,
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
            untouched_packet = TranslationPacket(
                chapter_id=untouched_chapter.id,
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
            session.add_all([packet_a, packet_b, untouched_packet])
            session.flush()

            run = DocumentRun(
                document_id=document.id,
                run_type=DocumentRunType.TRANSLATE_FULL,
                status=DocumentRunStatus.RUNNING,
                requested_by="tester",
                priority=100,
                status_detail_json={},
            )
            session.add(run)
            session.flush()

            target_chapter_run = ChapterRun(
                run_id=run.id,
                document_id=document.id,
                chapter_id=target_chapter.id,
                desired_phase=ChapterRunPhase.TRANSLATE,
                observed_phase=ChapterRunPhase.TRANSLATE,
                status=ChapterRunStatus.ACTIVE,
                generation=1,
                observed_generation=1,
                conditions_json={},
                status_detail_json={},
            )
            untouched_chapter_run = ChapterRun(
                run_id=run.id,
                document_id=document.id,
                chapter_id=untouched_chapter.id,
                desired_phase=ChapterRunPhase.TRANSLATE,
                observed_phase=ChapterRunPhase.TRANSLATE,
                status=ChapterRunStatus.ACTIVE,
                generation=1,
                observed_generation=1,
                conditions_json={},
                status_detail_json={},
            )
            session.add_all([target_chapter_run, untouched_chapter_run])
            session.flush()

            packet_task_a = PacketTask(
                chapter_run_id=target_chapter_run.id,
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
                chapter_run_id=target_chapter_run.id,
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
            untouched_packet_task = PacketTask(
                chapter_run_id=untouched_chapter_run.id,
                packet_id=untouched_packet.id,
                packet_generation=1,
                desired_action=PacketTaskAction.TRANSLATE,
                status=PacketTaskStatus.PENDING,
                input_version_bundle_json={},
                attempt_count=0,
                conditions_json={},
                status_detail_json={},
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=5),
            )
            session.add_all([packet_task_a, packet_task_b, untouched_packet_task])
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
            untouched_work_item = WorkItem(
                run_id=run.id,
                stage=WorkItemStage.TRANSLATE,
                scope_type=WorkItemScopeType.PACKET,
                scope_id=untouched_packet.id,
                attempt=1,
                priority=100,
                status=WorkItemStatus.PENDING,
                runtime_bundle_revision_id=None,
                input_version_bundle_json={},
                output_artifact_refs_json={},
                error_detail_json={},
            )
            session.add_all([work_item_a, work_item_b, untouched_work_item])
            session.commit()

            projected = PacketController(session=session).project_lane_health(run_id=run.id)
            session.commit()

            target_chapter_run = session.get(ChapterRun, target_chapter_run.id)
            untouched_chapter_run = session.get(ChapterRun, untouched_chapter_run.id)
            audit_events = session.query(RunAuditEvent).filter(RunAuditEvent.run_id == run.id).all()
            chapter_checkpoint = (
                session.query(RuntimeCheckpoint)
                .filter(
                    RuntimeCheckpoint.run_id == run.id,
                    RuntimeCheckpoint.scope_type == JobScopeType.CHAPTER,
                    RuntimeCheckpoint.scope_id == target_chapter.id,
                    RuntimeCheckpoint.checkpoint_key == "chapter_controller.chapter_hold",
                )
                .one()
            )
            packet_checkpoints = (
                session.query(RuntimeCheckpoint)
                .filter(
                    RuntimeCheckpoint.run_id == run.id,
                    RuntimeCheckpoint.scope_type == JobScopeType.PACKET,
                )
                .all()
            )

        self.assertEqual(projected, 3)
        self.assertIsNotNone(target_chapter_run)
        self.assertIsNotNone(untouched_chapter_run)
        assert target_chapter_run is not None and untouched_chapter_run is not None

        chapter_hold = target_chapter_run.conditions_json["chapter_hold"]
        self.assertEqual(target_chapter_run.status, ChapterRunStatus.PAUSED)
        self.assertEqual(target_chapter_run.pause_reason, "repair_exhausted")
        self.assertEqual(chapter_hold["hold_reason"], "repair_exhausted")
        self.assertEqual(chapter_hold["next_action"], "manual_review")
        self.assertEqual(chapter_hold["evidence_json"]["next_boundary"], "chapter")
        self.assertEqual(chapter_hold["evidence_json"]["runtime_bundle_revision_id"], bundle_revision_id)
        self.assertCountEqual(
            chapter_hold["evidence_json"]["affected_packet_ids"],
            [packet_a.id, packet_b.id],
        )
        self.assertEqual(target_chapter_run.status_detail_json["runtime_v2"]["chapter_hold"]["scope_boundary"], "chapter")
        self.assertEqual(untouched_chapter_run.conditions_json, {})
        self.assertEqual(untouched_chapter_run.status, ChapterRunStatus.ACTIVE)

        self.assertEqual(chapter_checkpoint.checkpoint_json["scope_boundary"], "chapter")
        self.assertEqual(chapter_checkpoint.checkpoint_json["next_action"], "manual_review")
        self.assertCountEqual(
            chapter_checkpoint.checkpoint_json["evidence_json"]["affected_packet_ids"],
            [packet_a.id, packet_b.id],
        )
        self.assertCountEqual(
            [checkpoint.scope_id for checkpoint in packet_checkpoints],
            [packet_a.id, packet_b.id, untouched_packet.id],
        )
        self.assertFalse(any(event.event_type == "run.scope_replay_ensured" for event in audit_events))
        self.assertFalse(any(event.payload_json.get("scope_type") == WorkItemScopeType.DOCUMENT.value for event in audit_events))


if __name__ == "__main__":
    unittest.main()
