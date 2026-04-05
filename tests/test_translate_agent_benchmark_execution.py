from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fitz

from artifacts.review.scripts.run_translate_agent_benchmark_execution import (
    _find_best_match,
    _gold_slice_pages,
    _localize_gold_label_for_pdf_slice,
    _materialize_pdf_slice,
    PredictedBlock,
)


class TranslateAgentBenchmarkExecutionTests(unittest.TestCase):
    def test_gold_slice_pages_returns_sorted_unique_positive_pages(self) -> None:
        gold_label = {
            "slice_scope": {
                "pages": [20, 1, 20, -1, 0, 240],
            }
        }
        self.assertEqual(_gold_slice_pages(gold_label), [1, 20, 240])

    def test_localize_gold_label_for_pdf_slice_remaps_pages(self) -> None:
        gold_label = {
            "slice_scope": {"pages": [1, 20, 240]},
            "blocks": [
                {"block_ref": "p1", "page_number": 1},
                {"block_ref": "p20", "page_number": 20},
                {"block_ref": "p240", "page_number": 240},
            ],
        }
        localized = _localize_gold_label_for_pdf_slice(
            gold_label,
            {1: 1, 2: 20, 3: 240},
        )
        self.assertEqual(localized["slice_scope"]["pages"], [1, 2, 3])
        self.assertEqual(
            [block["page_number"] for block in localized["blocks"]],
            [1, 2, 3],
        )

    def test_materialize_pdf_slice_keeps_only_requested_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.pdf"
            with fitz.open() as source_doc:
                for _ in range(5):
                    page = source_doc.new_page(width=300, height=400)
                    page.insert_text((72, 72), f"page {source_doc.page_count}")
                source_doc.save(str(source_path))

            slice_tempdir, slice_path, page_map = _materialize_pdf_slice(source_path, [2, 5])
            try:
                self.assertEqual(page_map, {1: 2, 2: 5})
                with fitz.open(str(slice_path)) as sliced_doc:
                    self.assertEqual(sliced_doc.page_count, 2)
            finally:
                slice_tempdir.cleanup()

    def test_find_best_match_falls_back_to_role_compatible_list_item_when_section_anchor_points_to_heading(self) -> None:
        gold_block = {
            "gold_role": "list",
            "source_selector": "OEBPS/ch12.xhtml :: section#Sec2 div.OrderedList > ol",
        }
        predicted_blocks = [
            PredictedBlock(
                global_index=0,
                block_id="heading-1",
                ordinal=1,
                block_type="heading",
                protected_policy="translate",
                source_anchor="OEBPS/ch12.xhtml#Sec2",
                source_path="OEBPS/ch12.xhtml",
                page_number=None,
                regions=[],
                text="12.1.1 Accidental Failures",
                heading_level=3,
                metadata={},
            ),
            PredictedBlock(
                global_index=1,
                block_id="list-1",
                ordinal=2,
                block_type="list_item",
                protected_policy="protect",
                source_anchor="OEBPS/ch12.xhtml#Par34",
                source_path="OEBPS/ch12.xhtml",
                page_number=None,
                regions=[],
                text="Implementing robust data validation and cleaning pipelines",
                heading_level=None,
                metadata={},
            ),
        ]

        matched, score = _find_best_match(gold_block, predicted_blocks, {})
        self.assertIsNotNone(matched)
        assert matched is not None
        self.assertEqual(matched.block_type, "list_item")
        self.assertEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
