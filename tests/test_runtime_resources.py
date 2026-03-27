import unittest
from uuid import uuid4

from book_agent.domain.enums import (
    ChapterStatus,
    DocumentRunStatus,
    DocumentRunType,
    DocumentStatus,
    JobScopeType,
    PacketStatus,
    PacketType,
    SourceType,
)
from book_agent.domain.models import Chapter, Document
from book_agent.domain.models.ops import DocumentRun
from book_agent.domain.models.translation import TranslationPacket
from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory
from book_agent.infra.repositories.run_control import RunControlRepository
from book_agent.infra.repositories.runtime_resources import RuntimeResourcesRepository
from book_agent.services.run_control import RunControlService


class RuntimeResourcesPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session_factory = build_session_factory(engine=self.engine)

    def test_run_summary_includes_runtime_v2_resource_counts(self) -> None:
        with self.session_factory() as session:
            doc = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"runtime-summary-{uuid4()}",
                source_path="/tmp/runtime.epub",
                title="Runtime Summary",
                author="Tester",
                src_lang="en",
                tgt_lang="zh",
                status=DocumentStatus.ACTIVE,
                parser_version=1,
                segmentation_version=1,
            )
            session.add(doc)
            session.flush()

            chapter = Chapter(
                document_id=doc.id,
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
                packet_json={"packet_ordinal": 1, "input_version_bundle": {"chapter_id": chapter.id}},
                risk_score=0.1,
                status=PacketStatus.BUILT,
            )
            session.add(packet)
            session.flush()

            run = DocumentRun(
                document_id=doc.id,
                run_type=DocumentRunType.TRANSLATE_FULL,
                status=DocumentRunStatus.RUNNING,
                requested_by="test",
                priority=100,
                status_detail_json={},
            )
            session.add(run)
            session.commit()

        with self.session_factory() as session:
            runtime_repo = RuntimeResourcesRepository(session)
            chapter_run = runtime_repo.ensure_chapter_run(
                run_id=run.id,
                document_id=doc.id,
                chapter_id=chapter.id,
            )
            runtime_repo.ensure_packet_task(
                chapter_run_id=chapter_run.id,
                packet_id=packet.id,
                packet_generation=1,
            )
            runtime_repo.upsert_checkpoint(
                run_id=run.id,
                scope_type=JobScopeType.CHAPTER,
                scope_id=chapter.id,
                checkpoint_key="controller_runner.v1",
                checkpoint_json={"cursor": 1},
                generation=1,
            )
            session.commit()

        with self.session_factory() as session:
            service = RunControlService(RunControlRepository(session))
            summary = service.get_run_summary(run.id)
            v2 = summary.status_detail_json["runtime_v2"]
            self.assertIsNone(v2["runtime_bundle_revision_id"])
            self.assertEqual(v2["chapter_run_count"], 1)
            self.assertEqual(v2["packet_task_count"], 1)
            self.assertEqual(v2["runtime_checkpoint_count"], 1)

    def test_checkpoint_upsert_updates_in_place(self) -> None:
        with self.session_factory() as session:
            doc = Document(
                source_type=SourceType.EPUB,
                file_fingerprint=f"runtime-checkpoint-{uuid4()}",
                source_path="/tmp/runtime.epub",
                title="Runtime Checkpoint",
                author="Tester",
                src_lang="en",
                tgt_lang="zh",
                status=DocumentStatus.ACTIVE,
                parser_version=1,
                segmentation_version=1,
            )
            session.add(doc)
            session.flush()

            chapter = Chapter(
                document_id=doc.id,
                ordinal=1,
                title_src="Chapter 1",
                status=ChapterStatus.PACKET_BUILT,
                metadata_json={},
            )
            session.add(chapter)
            session.flush()

            run = DocumentRun(
                document_id=doc.id,
                run_type=DocumentRunType.TRANSLATE_FULL,
                status=DocumentRunStatus.RUNNING,
                requested_by="test",
                priority=100,
                status_detail_json={},
            )
            session.add(run)
            session.commit()

        with self.session_factory() as session:
            repo = RuntimeResourcesRepository(session)
            first = repo.upsert_checkpoint(
                run_id=run.id,
                scope_type=JobScopeType.CHAPTER,
                scope_id=chapter.id,
                checkpoint_key="controller_runner.v1",
                checkpoint_json={"cursor": 1},
                generation=1,
            )
            second = repo.upsert_checkpoint(
                run_id=run.id,
                scope_type=JobScopeType.CHAPTER,
                scope_id=chapter.id,
                checkpoint_key="controller_runner.v1",
                checkpoint_json={"cursor": 2},
                generation=2,
            )
            self.assertEqual(first.id, second.id)
            self.assertEqual(second.generation, 2)
            self.assertEqual(second.checkpoint_json["cursor"], 2)
