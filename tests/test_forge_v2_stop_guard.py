from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from book_agent.forge_v2_stop_guard import (
    evaluate_stop_legality,
    find_forge_repo_root,
    parse_forge_state,
    stop_block_output,
)


class ForgeV2StopGuardTests(unittest.TestCase):
    def test_parse_forge_state_reads_scalars_and_lists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "STATE.md"
            state_path.write_text(
                "# Forge State\n\n"
                "current_step: ready_for_dispatch\n"
                "active_batch: none\n"
                "failed_items:\n"
                "- none\n"
                "next_items:\n"
                "- Continue EPUB expansion\n",
                encoding="utf-8",
            )

            parsed = parse_forge_state(state_path)
            self.assertEqual(parsed["current_step"], "ready_for_dispatch")
            self.assertEqual(parsed["active_batch"], "none")
            self.assertEqual(parsed["failed_items"], ["none"])
            self.assertEqual(parsed["next_items"], ["Continue EPUB expansion"])

    def test_evaluate_stop_legality_blocks_ready_for_dispatch(self) -> None:
        legality = evaluate_stop_legality(
            {
                "current_step": "ready_for_dispatch",
                "active_batch": "none",
                "failed_items": ["none"],
                "next_items": ["Shift the next expansion slice to epub-agentic-theories-001"],
            }
        )

        self.assertTrue(legality.should_block)
        self.assertIn("ready_for_dispatch", legality.reason)
        self.assertIn("epub-agentic-theories-001", legality.reason)

    def test_evaluate_stop_legality_allows_mainline_complete(self) -> None:
        legality = evaluate_stop_legality(
            {
                "current_step": "mainline_complete",
                "active_batch": "none",
                "failed_items": ["none"],
                "next_items": ["Future work should enter through change_request"],
            }
        )

        self.assertFalse(legality.should_block)
        self.assertIn("mainline_complete", legality.reason)

    def test_evaluate_stop_legality_allows_blocked_state_with_failures(self) -> None:
        legality = evaluate_stop_legality(
            {
                "current_step": "blocked",
                "active_batch": "batch-999",
                "failed_items": ["missing external credential"],
                "next_items": ["Retry after credential is supplied"],
            }
        )

        self.assertFalse(legality.should_block)
        self.assertIn("blocker recorded", legality.reason)

    def test_evaluate_stop_legality_blocks_active_review_named_step(self) -> None:
        legality = evaluate_stop_legality(
            {
                "current_step": "review_stop_hook_protocol_fix",
                "active_batch": "none",
                "failed_items": ["none"],
                "next_items": ["Shift the next expansion slice to epub-managing-memory-001"],
            }
        )

        self.assertTrue(legality.should_block)
        self.assertIn("review_stop_hook_protocol_fix", legality.reason)

    def test_find_forge_repo_root_discovers_project_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".forge").mkdir()
            (root / ".forge" / "STATE.md").write_text("current_step: ready_for_dispatch\n", encoding="utf-8")
            (root / "forge-v2").mkdir()
            (root / "forge-v2" / "SKILL.md").write_text("skill\n", encoding="utf-8")
            nested = root / "a" / "b" / "c"
            nested.mkdir(parents=True)

            self.assertEqual(find_forge_repo_root(nested), root.resolve())

    def test_stop_block_output_matches_stop_hook_schema(self) -> None:
        payload = json.loads(stop_block_output("continue now"))
        self.assertTrue(payload["continue"])
        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["reason"], "continue now")
        self.assertNotIn("universal", payload)


if __name__ == "__main__":
    unittest.main()
