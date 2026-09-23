#!/usr/bin/env python3
"""Minimal V4 PreToolUse guard for clear destructive/main-history commands."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any

BLOCKED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?:^|[;&|]\s*)git\s+reset\s+--hard(?:\s|$)"),
        "git reset --hard is prohibited in the trusted project",
    ),
    (
        re.compile(r"(?:^|[;&|]\s*)git\s+clean\s+-[^\s;&|]*f[^\s;&|]*(?:\s|$)"),
        "forced git clean is prohibited in the trusted project",
    ),
    (
        re.compile(r"(?:^|[;&|]\s*)git\s+push\b[^\n;&|]*(?:--force(?:-with-lease)?|-f)(?:\s|$)"),
        "force-push is prohibited",
    ),
    (
        re.compile(
            r"(?:^|[;&|]\s*)git\s+push\b[^\n;&|]*"
            r"(?:\s|:)(?:refs/heads/)?main(?:\s|$)"
        ),
        "direct push to main is prohibited",
    ),
    (
        re.compile(r"(?:^|[;&|]\s*)git\s+branch\s+-D\s+(?:refs/heads/)?main(?:\s|$)"),
        "deleting main is prohibited",
    ),
    (
        re.compile(
            r"(?:^|[;&|]\s*)rm\s+-(?=[^\s;&|]*r)(?=[^\s;&|]*f)[^\s;&|]+\s+"
            r"(?:/|\.|\.\.|~|\$HOME)(?:\s|$)"
        ),
        "broad recursive deletion is prohibited",
    ),
)


def block_reason(event: Mapping[str, Any]) -> str | None:
    """Return a reason only for an unambiguously prohibited Bash command."""
    if event.get("hook_event_name") != "PreToolUse" or event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, Mapping):
        return None
    command = tool_input.get("command")
    if not isinstance(command, str):
        return None
    for pattern, reason in BLOCKED_PATTERNS:
        if pattern.search(command):
            return reason
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(event, Mapping):
        return 0
    reason = block_reason(event)
    if reason is None:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
