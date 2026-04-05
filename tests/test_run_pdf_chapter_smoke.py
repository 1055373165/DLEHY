from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from book_agent.domain.enums import DocumentStatus, SourceType
from book_agent.domain.models import Document
from book_agent.domain.enums import PacketStatus
from book_agent.infra.db.base import Base
from book_agent.infra.db.session import build_engine, build_session_factory, session_scope
from scripts.run_pdf_chapter_smoke import (
    _auto_select_chapter_ordinal,
    _resolve_document_id,
    _select_packet_ids_for_translation,
)


class RunPdfChapterSmokeTests(unittest.TestCase):
    def test_select_packet_ids_for_translation_prefers_next_built_packets(self) -> None:
        packet_rows = [
            ("p1", PacketStatus.TRANSLATED),
            ("p2", PacketStatus.TRANSLATED),
            ("p3", PacketStatus.BUILT),
            ("p4", PacketStatus.RUNNING),
            ("p5", PacketStatus.BUILT),
            ("p6", PacketStatus.BUILT),
        ]

        all_packet_ids, selected_packet_ids = _select_packet_ids_for_translation(
            packet_rows,
            packet_limit=2,
        )

        self.assertEqual(all_packet_ids, ["p1", "p2", "p3", "p4", "p5", "p6"])
        self.assertEqual(selected_packet_ids, ["p3", "p5"])

    def test_select_packet_ids_for_translation_returns_all_remaining_built_packets_without_limit(self) -> None:
        packet_rows = [
            ("p1", PacketStatus.TRANSLATED),
            ("p2", PacketStatus.BUILT),
            ("p3", PacketStatus.BUILT),
            ("p4", PacketStatus.FAILED),
        ]

        _, selected_packet_ids = _select_packet_ids_for_translation(
            packet_rows,
            packet_limit=None,
        )

        self.assertEqual(selected_packet_ids, ["p2", "p3"])

    def test_resolve_document_id_reuses_existing_document_when_source_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_url = f"sqlite+pysqlite:///{Path(temp_dir) / 'smoke.db'}"
            engine = build_engine(database_url=database_url)
            Base.metadata.create_all(engine)
            session_factory = build_session_factory(engine=engine)
            missing_source = Path("/Volumes/XY_IMG/zlibrary/missing-book.pdf")

            with session_scope(session_factory) as session:
                session.add(
                    Document(
                        id="a" * 32,
                        source_type=SourceType.PDF_TEXT,
                        file_fingerprint="fingerprint-1",
                        source_path=str(missing_source),
                        src_lang="en",
                        tgt_lang="zh",
                        status=DocumentStatus.ACTIVE,
                        parser_version=1,
                        segmentation_version=1,
                        metadata_json={},
                    )
                )

            with session_scope(session_factory) as session:
                document_id, source_missing_resumed = _resolve_document_id(session, missing_source)

            self.assertEqual(document_id, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            self.assertTrue(source_missing_resumed)

    def test_auto_select_chapter_ordinal_prefers_first_non_frontmatter_structural_chapter(self) -> None:
        chapters = [
            SimpleNamespace(chapter_id="front", ordinal=1, title_src="Contents", sentence_count=3),
            SimpleNamespace(chapter_id="preface", ordinal=2, title_src="Preface", sentence_count=9),
            SimpleNamespace(
                chapter_id="main",
                ordinal=10,
                title_src="1 Introduction to AI agents and applications",
                sentence_count=22,
            ),
            SimpleNamespace(chapter_id="late", ordinal=11, title_src="2 Agent frameworks", sentence_count=20),
        ]
        packet_counts_by_chapter_id = {
            "front": {PacketStatus.BUILT.value: 2},
            "preface": {PacketStatus.BUILT.value: 4},
            "main": {PacketStatus.BUILT.value: 10},
            "late": {PacketStatus.BUILT.value: 8},
        }

        selected = _auto_select_chapter_ordinal(
            chapters,
            packet_counts_by_chapter_id=packet_counts_by_chapter_id,
        )

        self.assertEqual(selected, 10)

    def test_auto_select_chapter_ordinal_returns_none_when_no_built_packets_remain(self) -> None:
        chapters = [
            SimpleNamespace(chapter_id="c1", ordinal=1, title_src="1 Introduction", sentence_count=20),
            SimpleNamespace(chapter_id="c2", ordinal=2, title_src="2 Models", sentence_count=20),
        ]
        packet_counts_by_chapter_id = {
            "c1": {PacketStatus.TRANSLATED.value: 5},
            "c2": {PacketStatus.FAILED.value: 1},
        }

        selected = _auto_select_chapter_ordinal(
            chapters,
            packet_counts_by_chapter_id=packet_counts_by_chapter_id,
        )

        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
