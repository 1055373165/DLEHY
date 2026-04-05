from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LEGAL_COMPLETE_STEPS = {"mainline_complete"}
LEGAL_PAUSE_STEPS = {
    "paused",
    "pause_requested",
    "awaiting_review",
    "review_requested",
    "framework_edit",
    "framework_only",
    "framework_update_only",
    "diagnosis_only",
    "postmortem",
}
BLOCKED_STEP_MARKERS = {"blocked", "blocker"}


@dataclass(frozen=True)
class StopLegality:
    should_block: bool
    reason: str


def find_forge_repo_root(start: str | Path) -> Path | None:
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".forge" / "STATE.md").exists() and (candidate / "forge-v2" / "SKILL.md").exists():
            return candidate
    return None


def parse_forge_state(path: str | Path) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_key: str | None = None
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("- ") and current_key:
            parsed.setdefault(current_key, [])
            parsed[current_key].append(line[2:].strip())
            continue
        if ":" not in line:
            current_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            parsed[key] = value
            current_key = None
        else:
            parsed[key] = []
            current_key = key
    return parsed


def _non_none_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip() and str(item).strip().lower() != "none"]
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() == "none":
        return []
    return [text]


def evaluate_stop_legality(state: dict[str, Any]) -> StopLegality:
    current_step = str(state.get("current_step", "")).strip()
    normalized_step = current_step.lower()
    active_batch = str(state.get("active_batch", "")).strip().lower()
    failed_items = _non_none_items(state.get("failed_items"))
    next_items = _non_none_items(state.get("next_items"))

    if normalized_step in LEGAL_COMPLETE_STEPS and active_batch in {"", "none"}:
        return StopLegality(
            should_block=False,
            reason=f"legal stop: current_step={current_step} and active_batch={active_batch or 'none'}",
        )

    if any(marker in normalized_step for marker in BLOCKED_STEP_MARKERS) and failed_items:
        return StopLegality(
            should_block=False,
            reason=f"legal stop: blocker recorded under current_step={current_step}",
        )

    if normalized_step in LEGAL_PAUSE_STEPS:
        return StopLegality(
            should_block=False,
            reason=f"legal stop: current_step={current_step} is an explicit pause/review/framework boundary",
        )

    next_hint = next_items[0] if next_items else "no next_items recorded"
    return StopLegality(
        should_block=True,
        reason=(
            "Forge v2 stop blocked: current_step="
            f"{current_step or 'unknown'} is not a legal stop state. "
            f"active_batch={active_batch or 'none'}. "
            f"Next queued work from file truth: {next_hint}. "
            "Continue execution instead of waiting for the user to send another continue."
        ),
    )


def stop_block_output(reason: str) -> str:
    return json.dumps(
        {
            "continue": True,
            "decision": "block",
            "reason": reason,
        },
        ensure_ascii=False,
    )
