import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from book_agent.cli import main
from book_agent.tools.forge_migrate import migrate_autopilot_round_to_forge


def _progress_text() -> str:
    return """# Project Progress

## Autopilot State
- current_state: PHASE_CHECKPOINT
- current_phase: 5
- current_batch: 4
- completion_pct: 44
- completed_mdu: 8
- total_mdu: 18
- last_updated: 2026-03-27T12:17:38+0800

## Project Info
- Name: AI Agent Runtime V2 Round 2 (book-agent)
- Goal: Expand Runtime V2 from the REQ-EX-02 export self-heal slice into a broader self-healing matrix.

## Phase Overview
| Phase | Status | MDUs | Done | Pct | Est. Batches | Health Check |
|-------|--------|------|------|-----|--------------|--------------|
| 1: Review Runtime Resources | done | 4 | 4 | 100 | 2 | PASS: okay |
| 2: Lane Health + Recovery Matrix | active | 4 | 4 | 100 | 2 | FAIL: Phase-2 checkpoint stable subset hit `tests/test_app_runtime.py::ControllerRunnerReviewSessionTests::test_controller_runner_ensures_one_review_session_per_chapter_generation` (`MultipleResultsFound` on chapter-scoped checkpoints) |

## Batch Dispatch Log
| Batch | MDUs | Status | Envelope | Delivery Report | Verified |
|-------|------|--------|----------|-----------------|----------|
| 4 | MDU-2.2.1, MDU-2.2.2 | verified | envelopes/batch-4-v2.md | deliveries/batch-4-report.md | yes |
"""


class ForgeMigrateTests(unittest.TestCase):
    def _workspace(self) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        autopilot_root = root / ".autopilot"
        (autopilot_root / "envelopes").mkdir(parents=True)
        (autopilot_root / "deliveries").mkdir(parents=True)
        (autopilot_root / "PROGRESS.md").write_text(_progress_text(), encoding="utf-8")
        (autopilot_root / "DECISIONS.md").write_text("# Decisions\n\n- keep: additive\n", encoding="utf-8")
        (autopilot_root / "session-log.md").write_text(
            "# Session Log\n\n## 2026-03-27T12:17:38+08:00\n- Batch 4 harvested.\n",
            encoding="utf-8",
        )
        (autopilot_root / "envelopes" / "batch-4-v2.md").write_text("# batch\n", encoding="utf-8")
        (autopilot_root / "deliveries" / "batch-4-report.md").write_text("# report\n", encoding="utf-8")
        return root

    def test_migration_imports_state_and_syncs_framework_docs(self) -> None:
        workspace = self._workspace()

        result = migrate_autopilot_round_to_forge(workspace)

        self.assertEqual(result.current_step, "recovery")
        self.assertEqual(result.imported_batches, 1)
        self.assertEqual(result.imported_reports, 1)
        self.assertTrue((workspace / ".forge" / "STATE.md").exists())
        self.assertTrue((workspace / ".forge" / "DECISIONS.md").exists())
        self.assertTrue((workspace / ".forge" / "log.md").exists())
        self.assertTrue((workspace / ".forge" / "batches" / "batch-4-v2.md").exists())
        self.assertTrue((workspace / ".forge" / "reports" / "batch-4-report.md").exists())
        self.assertTrue((workspace / ".forge" / "imports" / "autopilot" / "PROGRESS.md").exists())
        self.assertTrue((workspace / "forge" / "SKILL.md").exists())
        self.assertTrue((workspace / "forge" / "RUNBOOK.md").exists())

        state_text = (workspace / ".forge" / "STATE.md").read_text(encoding="utf-8")
        self.assertIn("- current_step: recovery", state_text)
        self.assertIn("- active_batch: 4", state_text)
        self.assertIn("- active_batch_contract: .forge/batches/batch-4-v2.md", state_text)
        self.assertIn("- expected_report: none", state_text)
        self.assertIn("- failed_items: phase-2-checkpoint", state_text)
        self.assertIn("- next_action: repair tests/test_app_runtime.py checkpoint multiplicity regression", state_text)

    def test_cli_forge_migrate_outputs_json(self) -> None:
        workspace = self._workspace()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["forge-migrate-autopilot", "--workspace", str(workspace)])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["current_step"], "recovery")
        self.assertTrue(payload["forge_root"].endswith("/.forge"))
        self.assertTrue(payload["framework_root"].endswith("/forge"))


if __name__ == "__main__":
    unittest.main()
