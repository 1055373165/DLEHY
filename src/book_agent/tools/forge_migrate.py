from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(value: datetime | None = None) -> str:
    return (value or _utcnow()).astimezone().isoformat(timespec="seconds")


def _parse_markdown_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _extract_phase_overview_row(text: str, phase_number: int) -> str | None:
    needle = f"| {phase_number}: "
    for line in text.splitlines():
        if line.startswith(needle):
            return line.strip()
    return None


def _extract_batch_log_row(text: str, batch_id: str) -> str | None:
    needle = f"| {batch_id} |"
    for line in text.splitlines():
        if line.startswith(needle):
            return line.strip()
    return None


def _markdown_row_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _extract_last_session_entry(session_log: str) -> str:
    chunks = [chunk.strip() for chunk in session_log.split("\n## ") if chunk.strip()]
    if not chunks:
        return ""
    last = chunks[-1]
    return ("## " + last) if not last.startswith("## ") else last


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass(slots=True)
class ForgeMigrationResult:
    workspace: str
    forge_root: str
    framework_root: str
    imported_batches: int
    imported_reports: int
    current_step: str
    next_action: str


def migrate_autopilot_round_to_forge(workspace: str | Path) -> ForgeMigrationResult:
    workspace_path = Path(workspace).resolve()
    autopilot_root = workspace_path / ".autopilot"
    forge_root = workspace_path / ".forge"
    if not autopilot_root.exists():
        raise FileNotFoundError(f"Missing .autopilot root under {workspace_path}")

    progress_path = autopilot_root / "PROGRESS.md"
    decisions_path = autopilot_root / "DECISIONS.md"
    session_log_path = autopilot_root / "session-log.md"
    progress_text = progress_path.read_text(encoding="utf-8")
    decisions_text = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else "# Forge Decisions\n"
    session_log_text = session_log_path.read_text(encoding="utf-8") if session_log_path.exists() else "# Session Log\n"
    fields = _parse_markdown_fields(progress_text)

    forge_root.mkdir(parents=True, exist_ok=True)
    batches_dir = forge_root / "batches"
    reports_dir = forge_root / "reports"
    imports_dir = forge_root / "imports" / "autopilot"
    framework_source = _repo_root() / "forge"
    framework_target = workspace_path / "forge"
    batches_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    imports_dir.mkdir(parents=True, exist_ok=True)
    if framework_source.exists():
        shutil.copytree(
            framework_source,
            framework_target,
            dirs_exist_ok=True,
        )

    imported_batches = 0
    for source in sorted((autopilot_root / "envelopes").glob("*.md")):
        shutil.copy2(source, batches_dir / source.name)
        imported_batches += 1

    imported_reports = 0
    for source in sorted((autopilot_root / "deliveries").glob("*.md")):
        shutil.copy2(source, reports_dir / source.name)
        imported_reports += 1

    shutil.copy2(progress_path, imports_dir / "PROGRESS.md")
    if decisions_path.exists():
        shutil.copy2(decisions_path, imports_dir / "DECISIONS.md")
    if session_log_path.exists():
        shutil.copy2(session_log_path, imports_dir / "session-log.md")

    current_state = fields.get("current_state", "resume")
    current_phase = fields.get("current_phase", "0")
    current_batch = fields.get("current_batch", "none")
    completion_pct = fields.get("completion_pct", "0")
    completed_mdu = fields.get("completed_mdu", "0")
    total_mdu = fields.get("total_mdu", "0")
    batch_row = _extract_batch_log_row(progress_text, current_batch)
    active_contract = "none"
    expected_report = "none"
    if batch_row:
        parts = _markdown_row_cells(batch_row)
        if len(parts) >= 5:
            envelope_value = parts[3]
            report_value = parts[4]
            if envelope_value and envelope_value != "pending":
                active_contract = f".forge/batches/{Path(envelope_value).name}"
            if report_value and report_value != "pending":
                expected_report = f".forge/reports/{Path(report_value).name}"

    phase_row = _extract_phase_overview_row(progress_text, 2)
    phase_two_health = _markdown_row_cells(phase_row)[-1] if phase_row else "unknown"
    current_step = "resume"
    if current_state == "PHASE_CHECKPOINT" and phase_two_health.startswith("FAIL:"):
        current_step = "recovery"
    elif current_state == "PHASE_CHECKPOINT":
        current_step = "checkpoint"
    elif current_state == "BATCH_EXECUTING":
        current_step = "executing"
    elif current_state == "BATCH_VERIFYING":
        current_step = "verifying"
    elif current_state == "DISPATCHING":
        current_step = "dispatching"
    elif current_state == "COMPLETE":
        current_step = "complete"

    blocker_match = re.search(
        r"tests/test_app_runtime\.py::ControllerRunnerReviewSessionTests::test_controller_runner_ensures_one_review_session_per_chapter_generation",
        progress_text,
    )
    blocker = (
        "repair tests/test_app_runtime.py checkpoint multiplicity regression"
        if blocker_match
        else "continue current Forge run from imported autopilot snapshot"
    )

    state_text = (
        "# Forge State\n\n"
        "## State\n"
        "- mode: resume\n"
        f"- run_name: {fields.get('Name', 'migrated-autopilot-round')}\n"
        f"- goal: {fields.get('Goal', 'migrated from .autopilot')}\n"
        f"- current_step: {current_step}\n"
        f"- active_batch: {current_batch}\n"
        f"- active_batch_contract: {active_contract}\n"
        f"- expected_report: {'none' if current_step == 'recovery' else expected_report}\n"
        "- active_worker_pid: none\n"
        "- active_worker_name: none\n"
        "- active_worker_model: none\n"
        "- active_worker_reasoning: none\n"
        "- supervisor_child_pid: none\n"
        "- supervisor_child_status: none\n"
        "- supervisor_last_reason: none\n"
        "- supervisor_last_spawn_at: none\n"
        "- last_supervisor_poll_at: none\n"
        f"- completed_items: {completed_mdu}/{total_mdu}\n"
        f"- failed_items: {'phase-2-checkpoint' if current_step == 'recovery' else 'none'}\n"
        "- last_verified_test_baseline: batch-4 verification `25 passed`; phase-2 checkpoint `73 passed, 1 failed`\n"
        f"- next_action: {blocker}\n"
        "- imported_from: .autopilot\n"
        f"- imported_autopilot_state: {current_state}\n"
        f"- imported_autopilot_phase: {current_phase}\n"
        f"- imported_autopilot_completion_pct: {completion_pct}\n"
        f"- imported_snapshot_dir: {imports_dir.relative_to(workspace_path)}\n"
        f"- last_updated: {_format_ts()}\n\n"
        "## Current Blocker\n"
        f"- blocker: {blocker}\n"
        f"- phase_two_health: {phase_two_health}\n"
    )
    (forge_root / "STATE.md").write_text(state_text, encoding="utf-8")

    decisions_output = (
        "# Forge Decisions\n\n"
        f"- imported_from: {imports_dir.relative_to(workspace_path) / 'DECISIONS.md'}\n"
        "- migration_note: imported from an in-flight `.autopilot` round so Forge can take over execution\n\n"
        + decisions_text
    )
    (forge_root / "DECISIONS.md").write_text(decisions_output, encoding="utf-8")

    last_session_entry = _extract_last_session_entry(session_log_text)
    log_text = (
        "# Forge Log\n\n"
        f"## {_format_ts()}\n"
        f"- Migrated the active `.autopilot` round into `.forge`.\n"
        f"- Imported {imported_batches} envelopes and {imported_reports} delivery reports.\n"
        f"- Current step: `{current_step}`.\n"
        f"- Next action: {blocker}.\n"
        f"- Historical snapshot: `{imports_dir.relative_to(workspace_path)}`.\n\n"
        "## Imported Latest Session Entry\n\n"
        f"{last_session_entry}\n"
    )
    (forge_root / "log.md").write_text(log_text, encoding="utf-8")

    return ForgeMigrationResult(
        workspace=str(workspace_path),
        forge_root=str(forge_root),
        framework_root=str(framework_target),
        imported_batches=imported_batches,
        imported_reports=imported_reports,
        current_step=current_step,
        next_action=blocker,
    )
