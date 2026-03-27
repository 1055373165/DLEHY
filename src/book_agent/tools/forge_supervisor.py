from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(value: datetime | None = None) -> str:
    return (value or _utcnow()).astimezone().isoformat(timespec="seconds")


def _normalize_step(value: str | None) -> str:
    return (value or "").strip().lower().replace("_", "-")


def _parse_markdown_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _replace_or_append_field_lines(text: str, updates: dict[str, str]) -> str:
    lines = text.splitlines()
    remaining = dict(updates)
    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, _ = stripped[2:].split(":", 1)
        key = key.strip()
        if key not in remaining:
            continue
        indent = raw_line[: len(raw_line) - len(raw_line.lstrip(" "))]
        lines[index] = f"{indent}- {key}: {remaining.pop(key)}"
    if remaining:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(f"- {key}: {value}" for key, value in remaining.items())
    return "\n".join(lines) + "\n"


def _is_pid_alive(pid: int | None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@dataclass(slots=True)
class ForgePaths:
    workspace: Path

    @property
    def root(self) -> Path:
        return self.workspace / ".forge"

    @property
    def state(self) -> Path:
        return self.root / "STATE.md"

    @property
    def decisions(self) -> Path:
        return self.root / "DECISIONS.md"

    @property
    def log(self) -> Path:
        return self.root / "log.md"

    @property
    def batches(self) -> Path:
        return self.root / "batches"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def supervisor_output(self) -> Path:
        return self.root / "supervisor-output.log"


@dataclass(slots=True)
class ForgeState:
    path: Path
    raw_text: str
    fields: dict[str, str]

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.fields.get(key, default)

    @property
    def current_step(self) -> str:
        return _normalize_step(self.get("current_step") or self.get("current_state") or "")

    @property
    def active_batch(self) -> str | None:
        return self.get("active_batch")

    @property
    def active_batch_contract(self) -> str | None:
        return self.get("active_batch_contract") or self.get("active_envelope")

    @property
    def expected_report(self) -> str | None:
        return self.get("expected_report")

    @property
    def active_worker_pid(self) -> int | None:
        value = self.get("active_worker_pid")
        if not value or value == "none":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @property
    def supervisor_child_pid(self) -> int | None:
        value = self.get("supervisor_child_pid")
        if not value or value == "none":
            return None
        try:
            return int(value)
        except ValueError:
            return None

    @property
    def last_updated(self) -> str | None:
        return self.get("last_updated")


class ForgeStateStore:
    def __init__(self, paths: ForgePaths):
        self.paths = paths

    def read(self) -> ForgeState:
        text = self.paths.state.read_text(encoding="utf-8")
        return ForgeState(path=self.paths.state, raw_text=text, fields=_parse_markdown_fields(text))

    def update(self, updates: dict[str, str]) -> ForgeState:
        current = self.read()
        new_text = _replace_or_append_field_lines(current.raw_text, updates)
        current.path.write_text(new_text, encoding="utf-8")
        return self.read()

    def append_log(self, message: str) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        with self.paths.log.open("a", encoding="utf-8") as handle:
            if self.paths.log.stat().st_size == 0:
                handle.write("# Forge Log\n\n")
            handle.write(f"## {_format_ts()}\n- {message}\n\n")


@dataclass(slots=True)
class SupervisorTickResult:
    action: str
    reason: str
    spawned: bool
    command: list[str] = field(default_factory=list)
    pid: int | None = None
    report_exists: bool = False
    active_worker_alive: bool = False


class ForgeSupervisor:
    def __init__(
        self,
        workspace: str | Path,
        *,
        codex_command: list[str] | None = None,
        codex_reasoning_effort: str = "high",
        cooldown_seconds: float = 15.0,
        pid_probe: Callable[[int | None], bool] = _is_pid_alive,
        popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        self.paths = ForgePaths(Path(workspace).resolve())
        self.store = ForgeStateStore(self.paths)
        self.codex_command = list(codex_command or ["codex", "exec"])
        self.codex_reasoning_effort = codex_reasoning_effort.strip()
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self._pid_probe = pid_probe
        self._popen_factory = popen_factory

    def run_once(self) -> SupervisorTickResult:
        state = self.store.read()
        now = _format_ts()
        report_exists = self._report_exists(state)
        active_worker_alive = self._pid_probe(state.active_worker_pid)
        supervisor_alive = self._pid_probe(state.supervisor_child_pid)

        updates = {
            "last_supervisor_poll_at": now,
            "last_updated": now,
        }

        if not supervisor_alive and state.supervisor_child_pid is not None:
            updates["supervisor_child_pid"] = "none"
            updates["supervisor_child_status"] = "exited"

        reason = self._determine_reason(
            state=state,
            report_exists=report_exists,
            active_worker_alive=active_worker_alive,
            supervisor_alive=supervisor_alive,
        )

        if reason is None:
            self.store.update(updates)
            return SupervisorTickResult(
                action="noop",
                reason="no-trigger",
                spawned=False,
                report_exists=report_exists,
                active_worker_alive=active_worker_alive,
            )

        if supervisor_alive:
            self.store.update(updates)
            return SupervisorTickResult(
                action="noop",
                reason="supervisor-child-running",
                spawned=False,
                pid=state.supervisor_child_pid,
                report_exists=report_exists,
                active_worker_alive=active_worker_alive,
            )

        if self._in_cooldown(state=state, reason=reason):
            self.store.update(updates)
            return SupervisorTickResult(
                action="noop",
                reason="cooldown",
                spawned=False,
                report_exists=report_exists,
                active_worker_alive=active_worker_alive,
            )

        command = self._spawn_command(self._build_resume_prompt(state=state, reason=reason))
        self.paths.root.mkdir(parents=True, exist_ok=True)
        output_handle = self.paths.supervisor_output.open("a", encoding="utf-8")
        process = self._popen_factory(
            command,
            cwd=str(self.paths.workspace),
            stdout=output_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        updates.update(
            {
                "supervisor_child_pid": str(process.pid),
                "supervisor_child_status": "running",
                "supervisor_last_reason": reason,
                "supervisor_last_spawn_at": now,
                "supervisor_last_command": shlex.join(command),
            }
        )
        self.store.update(updates)
        self.store.append_log(f"Supervisor spawned Codex resume child for `{reason}` (pid={process.pid}).")
        return SupervisorTickResult(
            action="spawn",
            reason=reason,
            spawned=True,
            command=command,
            pid=process.pid,
            report_exists=report_exists,
            active_worker_alive=active_worker_alive,
        )

    def loop(self, *, poll_interval_seconds: float = 5.0) -> None:
        interval = max(0.2, float(poll_interval_seconds))
        while True:
            self.run_once()
            time.sleep(interval)

    def _determine_reason(
        self,
        *,
        state: ForgeState,
        report_exists: bool,
        active_worker_alive: bool,
        supervisor_alive: bool,
    ) -> str | None:
        step = state.current_step
        if not step:
            return None
        if report_exists:
            return "harvest-report-ready"
        if step in {"planning", "dispatching", "verifying", "checkpoint", "recovery", "resume"}:
            return f"continue-{step}"
        if step in {"executing", "batch-executing", "running"}:
            if state.active_worker_pid is not None and not active_worker_alive:
                return "recover-stale-worker-completion"
            if state.active_worker_pid is None and state.active_batch_contract and not supervisor_alive:
                return "recover-stale-executing-without-worker"
        return None

    def _report_exists(self, state: ForgeState) -> bool:
        report = state.expected_report
        if not report or report == "none":
            return False
        path = Path(report)
        if not path.is_absolute():
            path = self.paths.workspace / report
        return path.exists()

    def _in_cooldown(self, *, state: ForgeState, reason: str) -> bool:
        previous_reason = state.get("supervisor_last_reason")
        last_spawn_raw = state.get("supervisor_last_spawn_at")
        if previous_reason != reason or not last_spawn_raw:
            return False
        try:
            last_spawn = datetime.fromisoformat(last_spawn_raw)
        except ValueError:
            return False
        elapsed = (_utcnow().astimezone(last_spawn.tzinfo or timezone.utc) - last_spawn).total_seconds()
        return elapsed < self.cooldown_seconds

    def _build_resume_prompt(self, *, state: ForgeState, reason: str) -> str:
        return (
            "Resume the Forge run in this workspace. Read .forge/STATE.md, .forge/DECISIONS.md, "
            "the active batch contract, .forge/reports/, and .forge/log.md first. If forge/ exists, "
            "also read forge/SKILL.md, forge/ARTIFACTS.md, and forge/RUNBOOK.md before acting. "
            "Use file truth as the source of truth. Harvest, verify, recover, or continue dispatching as needed. "
            "Do not stop at a prose summary. If the blocker is cleared and the run is in planning, "
            "you must create the next authoritative batch contract, update .forge/STATE.md and .forge/log.md, "
            "and dispatch the next worker when write ownership is clear. "
            f"Supervisor reason: {reason}. "
            f"Active batch: {state.active_batch or 'none'}. "
            f"Expected report: {state.expected_report or 'none'}."
        )

    def _spawn_command(self, prompt: str) -> list[str]:
        command = list(self.codex_command)
        if (
            len(command) >= 2
            and command[0] == "codex"
            and command[1] == "exec"
        ):
            if "--full-auto" not in command:
                command.append("--full-auto")
            if self.codex_reasoning_effort:
                command.extend(
                    [
                        "-c",
                        f'model_reasoning_effort="{self.codex_reasoning_effort}"',
                    ]
                )
        command.append(prompt)
        return command


def _tick_payload(result: SupervisorTickResult) -> dict[str, object]:
    return {
        "action": result.action,
        "reason": result.reason,
        "spawned": result.spawned,
        "pid": result.pid,
        "command": result.command,
        "report_exists": result.report_exists,
        "active_worker_alive": result.active_worker_alive,
    }


def run_supervisor_once(
    workspace: str | Path,
    *,
    codex_command: list[str] | None = None,
    codex_reasoning_effort: str = "high",
    cooldown_seconds: float = 15.0,
) -> dict[str, object]:
    result = ForgeSupervisor(
        workspace,
        codex_command=codex_command,
        codex_reasoning_effort=codex_reasoning_effort,
        cooldown_seconds=cooldown_seconds,
    ).run_once()
    return _tick_payload(result)


def run_supervisor_loop(
    workspace: str | Path,
    *,
    codex_command: list[str] | None = None,
    codex_reasoning_effort: str = "high",
    cooldown_seconds: float = 15.0,
    poll_interval_seconds: float = 5.0,
) -> None:
    ForgeSupervisor(
        workspace,
        codex_command=codex_command,
        codex_reasoning_effort=codex_reasoning_effort,
        cooldown_seconds=cooldown_seconds,
    ).loop(poll_interval_seconds=poll_interval_seconds)


def dump_tick_payload(workspace: str | Path, *, codex_command: list[str] | None = None) -> None:
    print(json.dumps(run_supervisor_once(workspace, codex_command=codex_command), ensure_ascii=False, indent=2))
