#!/usr/bin/env python3
"""Fail-closed consistency check for the V5 candidate/active governance layer."""

from __future__ import annotations

import json
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import cast

CANONICAL = "governance/ENGINEERING_GOVERNANCE_V5_CONSOLIDATED_FINAL.md"


class CheckFailure(RuntimeError):
    pass


def text(root: Path, path: str) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckFailure(f"missing required file: {path}") from exc


def require(value: str, needles: tuple[str, ...], label: str) -> None:
    missing = [n for n in needles if n not in value]
    if missing:
        raise CheckFailure(f"{label} missing: {', '.join(missing)}")


def manifest(root: Path) -> dict[str, object]:
    try:
        loaded = json.loads(text(root, "governance/ACTIVE_GOVERNANCE_MANIFEST.json"))
    except json.JSONDecodeError as exc:
        raise CheckFailure("invalid manifest JSON") from exc
    if not isinstance(loaded, dict):
        raise CheckFailure("manifest must be an object")
    return cast(dict[str, object], loaded)


def check_manifest(root: Path) -> None:
    m = manifest(root)
    if m.get("governance_version") != "V5" or m.get("status") not in {
        "CANDIDATE_PENDING_ACTIVATION",
        "ACTIVE",
    }:
        raise CheckFailure("manifest is not V5 candidate/active")
    if m.get("sole_project_wide_constitution") != CANONICAL:
        raise CheckFailure("sole V5 constitution mismatch")
    if m.get("status") == "CANDIDATE_PENDING_ACTIVATION" and not isinstance(
        m.get("main_governance_until_activation_merge"), dict
    ):
        raise CheckFailure("candidate must retain V4 main authority")
    main_governance = cast(dict[str, object], m.get("main_governance_until_activation_merge", {}))
    if m.get("status") == "CANDIDATE_PENDING_ACTIVATION" and main_governance.get("version") != "V4":
        raise CheckFailure("candidate must retain V4 main authority")
    codex = cast(dict[str, object], m.get("codex", {}))
    if codex.get("runtime_qualification") != "NOT_YET_PROVEN":
        raise CheckFailure("false runtime qualification claim")
    relay = m.get("execution_relay", {})
    if relay != {
        "preferred": "REMOTE_DESKTOP_COMMANDER_WHEN_CONNECTED_AND_QUOTA_AVAILABLE",
        "authority": "EXECUTION_TRANSPORT_ONLY",
        "hard_dependency": False,
    }:
        raise CheckFailure("execution relay metadata mismatch")


def check_documents(root: Path) -> None:
    require(
        text(root, CANONICAL),
        (
            "candidate sole manually authored project-wide engineering",
            "MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT",
            "GH_WORKFLOW_SCOPE_REQUIRED=YES",
            "REMOTE_DESKTOP_COMMANDER_STATUS=FORMAL_V5_EXECUTION_RELAY",
        ),
        "V5 constitution",
    )
    require(
        text(root, "governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md"),
        ("SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED", "REMOTE_DESKTOP_OFFLINE_OR_QUOTA_EXHAUSTED"),
        "bridge",
    )
    require(
        text(root, "docs/engineering/CODEX_V5_OPERATING_GUIDE.md"),
        ("FORMAL_V5_EXECUTION_RELAY", "ONE_EXACT_GENERATED_HUMAN_TERMINAL_COMMAND_OR_BLOCK"),
        "V5 guide",
    )
    for path in (
        ".agents/skills/trade-os-v5-bootstrap/SKILL.md",
        ".agents/skills/trade-os-v5-development/SKILL.md",
        ".agents/skills/trade-os-v5-handoff/SKILL.md",
    ):
        require(text(root, path), ("MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT",), path)


def check_config(root: Path) -> None:
    with (root / ".codex/config.toml").open("rb") as f:
        c = tomllib.load(f)
    if c.get("model") != "gpt-6-sol" or c.get("model_reasoning_effort") != "medium":
        raise CheckFailure("V5 intended GPT-6 Sol routing mismatch")
    if c.get("approvals_reviewer") != "auto_review" or c.get("web_search") != "disabled":
        raise CheckFailure("V5 config safety mismatch")


def check_controller(root: Path) -> None:
    require(
        text(root, "scripts/control/v5_controller.py"),
        (
            "MODEL_EXECUTOR_STDIN_SOURCE",
            "GH_WORKFLOW_SCOPE_VERIFIED=YES",
            "PAUSED_CAPABILITY",
            "COMMENT_ONLY",
        ),
        "V5 controller",
    )


def checks() -> tuple[tuple[str, Callable[[Path], None]], ...]:
    return (
        ("V5_MANIFEST", check_manifest),
        ("V5_DOCUMENTS", check_documents),
        ("V5_CONFIG", check_config),
        ("V5_CONTROLLER", check_controller),
    )


def run(root: Path) -> list[str]:
    failures = []
    for label, check in checks():
        try:
            check(root)
            print(f"{label}=PASS")
        except CheckFailure as exc:
            failures.append(f"{label}=FAIL: {exc}")
    return failures


def main() -> int:
    failures = run(Path(__file__).resolve().parents[1])
    print(*failures, sep="\n", file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
