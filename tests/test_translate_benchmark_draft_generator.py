from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from book_agent.services.translate_benchmark_draft_generator import (
    PageProbe,
    build_pdf_mixed_layout_draft,
    choose_mixed_layout_probe_pages,
    write_draft_files,
)


class TranslateBenchmarkDraftGeneratorTests(unittest.TestCase):
    def test_choose_mixed_layout_probe_pages_prefers_body_then_visual_pages(self) -> None:
        probes = [
            PageProbe(page_number=1, word_count=13, image_count=2, drawing_count=0, preview_lines=["MANNING"]),
            PageProbe(page_number=11, word_count=266, image_count=0, drawing_count=0, preview_lines=["ix", "contents"]),
            PageProbe(
                page_number=31,
                word_count=416,
                image_count=1,
                drawing_count=20,
                preview_lines=["7", "The deep in deep learning"],
            ),
            PageProbe(
                page_number=61,
                word_count=216,
                image_count=0,
                drawing_count=32,
                preview_lines=["37", "Tensor operations"],
            ),
        ]

        pages = choose_mixed_layout_probe_pages(probes)

        self.assertEqual(pages[:2], [31, 32])
        self.assertIn(61, pages)

    def test_write_draft_files_materializes_manifest_and_gold_stub(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            review_root = Path(temp_dir)
            document_path = review_root / "Think Distributed Systems.pdf"
            import fitz

            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "Chapter 1\nDistributed systems introduction")
            document.save(str(document_path))
            document.close()
            manifest, gold = build_pdf_mixed_layout_draft(
                document_path=document_path,
                lane_id="L5",
                family_guess="PDF-mixed-layout-book",
                risk_tags=["mixed_layout"],
                queue_profile_path=Path("/tmp/queue.json"),
            )

            manifest_path, gold_path = write_draft_files(
                manifest=manifest,
                gold_label=gold,
                review_root=review_root,
            )

            self.assertTrue(manifest_path.exists())
            self.assertTrue(gold_path.exists())
            self.assertIn(str(gold_path.resolve()), manifest_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
