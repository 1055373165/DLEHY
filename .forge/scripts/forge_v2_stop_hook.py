#!/usr/bin/env python3
"""Compatibility no-op for stale Codex Stop hook sessions.

Older sessions may still try to execute this path from an in-memory hook
configuration. Returning success prevents the hook error from leaking into
chat output after the hook was removed from the persisted config.
"""

from __future__ import annotations


def main() -> int:
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
