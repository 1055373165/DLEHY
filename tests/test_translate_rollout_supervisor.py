from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from book_agent.services.translate_rollout_supervisor import (
    BenchmarkManifestState,
    BenchmarkState,
    LivePilotState,
    QueueItem,
    _next_report_path,
    discover_benchmark_states,
    discover_live_pilots,
    plan_rollout_actions,
)


class TranslateRolloutSupervisorTests(unittest.TestCase):
    def test_next_report_path_advances_past_suffix_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "report.json").write_text("{}", encoding="utf-8")
            (root / "report-slice2.json").write_text("{}", encoding="utf-8")
            (root / "report-slice20-deepseek.json").write_text("{}", encoding="utf-8")

            report_path = _next_report_path(root)

            self.assertEqual(report_path.name, "report-slice21.json")

    def test_discover_live_pilots_prefers_latest_slice_per_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pilot_root = root / "pilot-book"
            pilot_root.mkdir(parents=True)
            source_path = "/books/example.epub"
            base_payload = {
                "source_path": source_path,
                "selected_chapter": {
                    "ordinal": 10,
                    "title_src": "1 Introduction",
                    "fully_translated": False,
                    "packet_status_snapshot": {"counts": {"translated": 4, "built": 8}},
                },
            }
            (pilot_root / "report.json").write_text(json.dumps(base_payload), encoding="utf-8")
            newer = dict(base_payload)
            newer["selected_chapter"] = {
                "ordinal": 10,
                "title_src": "1 Introduction",
                "fully_translated": False,
                "packet_status_snapshot": {"counts": {"translated": 12, "built": 4}},
            }
            (pilot_root / "report-slice4.json").write_text(json.dumps(newer), encoding="utf-8")

            states = discover_live_pilots(root)

            self.assertIn(source_path, states)
            self.assertEqual(states[source_path].latest_sequence, 4)
            self.assertEqual(states[source_path].translated_count, 12)
            self.assertEqual(states[source_path].built_count, 4)

    def test_discover_benchmark_states_maps_summary_back_to_document_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "sample-wave.yaml"
            manifest_path.write_text(
                "\n".join(
                    [
                        "schema_version: 1",
                        "samples:",
                        "  - sample_id: sample-1",
                        "    document_path: /books/mixed.pdf",
                        "    gold_label_path: /tmp/label.json",
                    ]
                ),
                encoding="utf-8",
            )
            summary_path = root / "sample-wave-execution-summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "manifest_path": str(manifest_path),
                        "overall_verdict": "go",
                        "sample_results": [{"sample_id": "sample-1", "verdict": "go"}],
                    }
                ),
                encoding="utf-8",
            )

            states = discover_benchmark_states(root)

            self.assertIn("/books/mixed.pdf", states)
            self.assertEqual(states["/books/mixed.pdf"].verdict, "go")

    def test_plan_rollout_actions_prioritizes_existing_live_pilot_before_new_starts(self) -> None:
        queue_items = [
            QueueItem(
                queue_index=0,
                path="/books/a.pdf",
                exists=True,
                suffix=".pdf",
                lane_guess="L2",
                family_guess="PDF-text-tech-book",
                recommended_next_step="chapter_pilot_ready",
                risk_tags=[],
            ),
            QueueItem(
                queue_index=1,
                path="/books/b.pdf",
                exists=True,
                suffix=".pdf",
                lane_guess="L5",
                family_guess="PDF-mixed-layout-book",
                recommended_next_step="benchmark_first",
                risk_tags=[],
            ),
        ]
        live_states = {
            "/books/a.pdf": LivePilotState(
                source_path="/books/a.pdf",
                root="/tmp/pilot-a",
                latest_report_path="/tmp/pilot-a/report-slice4.json",
                latest_sequence=4,
                latest_report_mtime=100.0,
                chapter_ordinal=1,
                chapter_title="1 Intro",
                fully_translated=False,
                translated_count=20,
                built_count=12,
                running_count=0,
                no_work_remaining=False,
            )
        }
        benchmark_states = {
            "/books/b.pdf": BenchmarkState(
                source_path="/books/b.pdf",
                verdict="go",
                summary_path="/tmp/b-summary.json",
                manifest_path="/tmp/b.yaml",
                sample_ids=["sample-b"],
            )
        }

        actions = plan_rollout_actions(
            queue_items=queue_items,
            queue_profile_path=Path("/tmp/queue.json"),
            live_states=live_states,
            benchmark_states=benchmark_states,
            benchmark_manifests={},
            real_book_root=Path("/tmp/real-book-live"),
            packet_limit=4,
        )

        self.assertGreaterEqual(len(actions), 2)
        self.assertEqual(actions[0].action, "continue_live_chapter_pilot")
        self.assertEqual(actions[0].source_path, "/books/a.pdf")

    def test_plan_rollout_actions_rotates_to_oldest_live_pilot(self) -> None:
        queue_items = [
            QueueItem(
                queue_index=1,
                path="/books/a.pdf",
                exists=True,
                suffix=".pdf",
                lane_guess="L2",
                family_guess="PDF-text-tech-book",
                recommended_next_step="chapter_pilot_ready",
                risk_tags=[],
            ),
            QueueItem(
                queue_index=2,
                path="/books/b.epub",
                exists=True,
                suffix=".epub",
                lane_guess="L1",
                family_guess="EPUB-reflowable-tech-book",
                recommended_next_step="chapter_pilot_ready",
                risk_tags=[],
            ),
        ]
        live_states = {
            "/books/a.pdf": LivePilotState(
                source_path="/books/a.pdf",
                root="/tmp/pilot-a",
                latest_report_path="/tmp/pilot-a/report-slice22.json",
                latest_sequence=22,
                latest_report_mtime=200.0,
                chapter_ordinal=1,
                chapter_title="1 Intro",
                fully_translated=False,
                translated_count=89,
                built_count=177,
                running_count=0,
                no_work_remaining=False,
            ),
            "/books/b.epub": LivePilotState(
                source_path="/books/b.epub",
                root="/tmp/pilot-b",
                latest_report_path="/tmp/pilot-b/report-slice19.json",
                latest_sequence=19,
                latest_report_mtime=100.0,
                chapter_ordinal=10,
                chapter_title="1 Introduction",
                fully_translated=False,
                translated_count=80,
                built_count=93,
                running_count=0,
                no_work_remaining=False,
            ),
        }

        actions = plan_rollout_actions(
            queue_items=queue_items,
            queue_profile_path=Path("/tmp/queue.json"),
            live_states=live_states,
            benchmark_states={},
            benchmark_manifests={},
            real_book_root=Path("/tmp/real-book-live"),
            packet_limit=4,
        )

        self.assertEqual(actions[0].action, "continue_live_chapter_pilot")
        self.assertEqual(actions[0].source_path, "/books/b.epub")

    def test_plan_rollout_actions_generates_benchmark_draft_when_missing(self) -> None:
        queue_items = [
            QueueItem(
                queue_index=6,
                path="/books/deep-learning.pdf",
                exists=True,
                suffix=".pdf",
                lane_guess="L5",
                family_guess="PDF-mixed-layout-book",
                recommended_next_step="benchmark_first",
                risk_tags=["mixed_layout"],
            )
        ]

        actions = plan_rollout_actions(
            queue_items=queue_items,
            queue_profile_path=Path("/tmp/queue.json"),
            live_states={},
            benchmark_states={},
            benchmark_manifests={},
            real_book_root=Path("/tmp/real-book-live"),
            packet_limit=4,
        )

        self.assertEqual(actions[0].action, "generate_benchmark_draft")
        self.assertIn("generate_translate_agent_benchmark_draft.py", " ".join(actions[0].command or []))

    def test_plan_rollout_actions_marks_stub_manifest_as_annotation_pending(self) -> None:
        queue_items = [
            QueueItem(
                queue_index=6,
                path="/books/deep-learning.pdf",
                exists=True,
                suffix=".pdf",
                lane_guess="L5",
                family_guess="PDF-mixed-layout-book",
                recommended_next_step="benchmark_first",
                risk_tags=["mixed_layout"],
            )
        ]
        benchmark_manifests = {
            "/books/deep-learning.pdf": BenchmarkManifestState(
                source_path="/books/deep-learning.pdf",
                manifest_path="/tmp/auto.yaml",
                gold_label_path="/tmp/auto.json",
                gold_label_status="stub_pending_annotation",
                sample_id="sample-1",
            )
        }

        actions = plan_rollout_actions(
            queue_items=queue_items,
            queue_profile_path=Path("/tmp/queue.json"),
            live_states={},
            benchmark_states={},
            benchmark_manifests=benchmark_manifests,
            real_book_root=Path("/tmp/real-book-live"),
            packet_limit=4,
        )

        self.assertEqual(actions[0].action, "benchmark_annotation_pending")


if __name__ == "__main__":
    unittest.main()
