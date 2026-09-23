from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".codex" / "hooks" / "pre_tool_use_policy.py"
SPEC = importlib.util.spec_from_file_location("pre_tool_use_policy", SCRIPT)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


def event(command: str) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD^",
        "git clean -fdx",
        "git push --force origin feature",
        "git push origin HEAD:main",
        "git branch -D main",
        "rm -rf /",
        "rm -fr .",
    ],
)
def test_clear_destructive_or_main_history_commands_are_blocked(command: str) -> None:
    assert policy.block_reason(event(command)) is not None


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git push origin codex/issue-232-v4-consolidation",
        "git diff --check",
        "rm -rf /tmp/specific-v4-fixture",
    ],
)
def test_routine_bounded_commands_are_not_blocked(command: str) -> None:
    assert policy.block_reason(event(command)) is None


def test_non_bash_tools_are_ignored() -> None:
    non_bash_event = {"hook_event_name": "PreToolUse", "tool_name": "apply_patch"}
    assert policy.block_reason(non_bash_event) is None
