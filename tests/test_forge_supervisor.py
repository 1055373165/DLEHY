import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from book_agent.cli import main
from book_agent.tools.forge_supervisor import ForgeSupervisor


class _FakeProcess:
    def __init__(self, pid: int = 4242) -> None:
        self.pid = pid


def _state_text(
    *,
    current_step: str = "executing",
    active_batch: str = "4",
    active_batch_contract: str = ".forge/batches/batch-4.md",
    expected_report: str = ".forge/reports/batch-4-report.md",
    active_worker_pid: str = "7777",
) -> str:
    return (
        "# Forge State\n\n"
        "## State\n"
        f"- mode: resume\n"
        f"- current_step: {current_step}\n"
        f"- active_batch: {active_batch}\n"
        f"- active_batch_contract: {active_batch_contract}\n"
        f"- expected_report: {expected_report}\n"
        f"- active_worker_pid: {active_worker_pid}\n"
        f"- last_updated: 2026-03-27T12:00:00+08:00\n"
    )


class ForgeSupervisorTests(unittest.TestCase):
    def _workspace(self) -> Path:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        forge_root = root / ".forge"
        forge_root.mkdir(parents=True, exist_ok=True)
        (forge_root / "batches").mkdir()
        (forge_root / "reports").mkdir()
        return root

    def test_run_once_spawns_harvest_when_report_exists(self) -> None:
        workspace = self._workspace()
        state_path = workspace / ".forge" / "STATE.md"
        state_path.write_text(_state_text(active_worker_pid="none"), encoding="utf-8")
        report_path = workspace / ".forge" / "reports" / "batch-4-report.md"
        report_path.write_text("# ready\n", encoding="utf-8")

        popen_calls: list[list[str]] = []

        def _fake_popen(command, **kwargs):
            popen_calls.append(command)
            return _FakeProcess()

        supervisor = ForgeSupervisor(
            workspace,
            pid_probe=lambda pid: False,
            popen_factory=_fake_popen,
            cooldown_seconds=0.0,
        )

        result = supervisor.run_once()

        self.assertTrue(result.spawned)
        self.assertEqual(result.reason, "harvest-report-ready")
        self.assertEqual(result.pid, 4242)
        self.assertEqual(popen_calls[0][:2], ["codex", "exec"])
        self.assertIn("--full-auto", popen_calls[0])
        self.assertIn("-c", popen_calls[0])
        self.assertIn('model_reasoning_effort="high"', popen_calls[0])
        updated = state_path.read_text(encoding="utf-8")
        self.assertIn("- supervisor_child_pid: 4242", updated)

    def test_run_once_spawns_recovery_when_worker_is_stale(self) -> None:
        workspace = self._workspace()
        state_path = workspace / ".forge" / "STATE.md"
        state_path.write_text(_state_text(active_worker_pid="7777"), encoding="utf-8")

        supervisor = ForgeSupervisor(
            workspace,
            pid_probe=lambda pid: False,
            popen_factory=lambda *args, **kwargs: _FakeProcess(31337),
            cooldown_seconds=0.0,
        )

        result = supervisor.run_once()

        self.assertTrue(result.spawned)
        self.assertEqual(result.reason, "recover-stale-worker-completion")
        updated = state_path.read_text(encoding="utf-8")
        self.assertIn("- supervisor_child_pid: 31337", updated)
        self.assertIn("- supervisor_last_reason: recover-stale-worker-completion", updated)

    def test_run_once_noops_while_worker_is_alive(self) -> None:
        workspace = self._workspace()
        state_path = workspace / ".forge" / "STATE.md"
        state_path.write_text(_state_text(active_worker_pid="7777"), encoding="utf-8")

        supervisor = ForgeSupervisor(
            workspace,
            pid_probe=lambda pid: pid == 7777,
            popen_factory=lambda *args, **kwargs: _FakeProcess(1),
            cooldown_seconds=0.0,
        )

        result = supervisor.run_once()

        self.assertFalse(result.spawned)
        self.assertEqual(result.action, "noop")
        self.assertEqual(result.reason, "no-trigger")
        updated = state_path.read_text(encoding="utf-8")
        self.assertNotIn("supervisor_child_pid", updated)

    def test_run_once_spawns_when_state_is_planning(self) -> None:
        workspace = self._workspace()
        state_path = workspace / ".forge" / "STATE.md"
        state_path.write_text(_state_text(current_step="planning", active_worker_pid="none"), encoding="utf-8")

        popen_calls: list[list[str]] = []

        def _fake_popen(command, **kwargs):
            popen_calls.append(command)
            return _FakeProcess(9191)

        supervisor = ForgeSupervisor(
            workspace,
            pid_probe=lambda pid: False,
            popen_factory=_fake_popen,
            cooldown_seconds=0.0,
        )

        result = supervisor.run_once()

        self.assertTrue(result.spawned)
        self.assertEqual(result.reason, "continue-planning")
        self.assertEqual(result.pid, 9191)
        self.assertIn("--full-auto", popen_calls[0])


class ForgeSupervisorCliTests(unittest.TestCase):
    def test_cli_forge_supervisor_once_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with patch(
                "book_agent.cli.run_supervisor_once",
                return_value={"action": "spawn", "reason": "harvest-report-ready", "spawned": True},
            ):
                with patch("sys.stdout", stdout):
                    exit_code = main(
                        [
                            "forge-supervisor",
                            "--workspace",
                            tmpdir,
                            "--cooldown-seconds",
                            "0",
                            "once",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["action"], "spawn")
            self.assertEqual(payload["reason"], "harvest-report-ready")


if __name__ == "__main__":
    unittest.main()
