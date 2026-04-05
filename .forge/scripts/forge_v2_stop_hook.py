#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
AUTO_COMMIT_SCRIPT = CODEX_HOME / "hooks" / "git-auto-commit" / "auto_commit.py"
HOOK_LOG = CODEX_HOME / "hooks" / "git-auto-commit" / "hook.log"


def _log(message: str) -> None:
    try:
        HOOK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HOOK_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"forge_v2_stop_hook {message}\n")
    except OSError:
        pass


def _load_stop_guard():
    from book_agent.forge_v2_stop_guard import (  # noqa: E402
        evaluate_stop_legality,
        find_forge_repo_root,
        parse_forge_state,
        stop_block_output,
    )

    return evaluate_stop_legality, find_forge_repo_root, parse_forge_state, stop_block_output


def _delegate_to_auto_commit(raw_input: str) -> int:
    if not AUTO_COMMIT_SCRIPT.exists():
        _log("delegate skipped: auto_commit.py missing")
        return 0
    try:
        proc = subprocess.run(
            [sys.executable, str(AUTO_COMMIT_SCRIPT)],
            input=raw_input,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:  # pragma: no cover - hook hardening
        _log(f"delegate subprocess failed: {exc}")
        return 0

    if proc.returncode == 0:
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        return 0

    _log(f"delegate returned rc={proc.returncode} stderr={proc.stderr.strip()!r}")
    # Stop legality is the primary contract. Auto-commit remains best effort.
    return 0


def main() -> int:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _log("empty stdin")
            return 0

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            _log(f"invalid json: {exc}")
            return 0

        if payload.get("hook_event_name") != "Stop":
            return _delegate_to_auto_commit(raw)

        evaluate_stop_legality, find_forge_repo_root, parse_forge_state, stop_block_output = _load_stop_guard()

        cwd = payload.get("cwd") or os.getcwd()
        repo_root = find_forge_repo_root(cwd)
        if repo_root is None:
            _log(f"no forge repo root for cwd={cwd}")
            return _delegate_to_auto_commit(raw)

        state_path = repo_root / ".forge" / "STATE.md"
        if not state_path.exists():
            _log(f"missing state file at {state_path}")
            return _delegate_to_auto_commit(raw)

        legality = evaluate_stop_legality(parse_forge_state(state_path))
        if legality.should_block:
            sys.stdout.write(stop_block_output(legality.reason))
            return 0

        return _delegate_to_auto_commit(raw)
    except Exception as exc:  # pragma: no cover - hook hardening
        _log(f"unexpected wrapper failure: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
