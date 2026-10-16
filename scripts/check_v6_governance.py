#!/usr/bin/env python3
"""Fail-closed consistency gate for V6 PILOT_ACTIVE; V5 remains archived."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CANONICAL = "governance/ENGINEERING_GOVERNANCE_V6_PILOT.md"
V5_ARCHIVE = "governance/ENGINEERING_GOVERNANCE_V5_CONSOLIDATED_FINAL.md"
SKILL = ".agents/skills/trade-os-v6/SKILL.md"
MANIFEST = "governance/ACTIVE_GOVERNANCE_MANIFEST.json"
PROTECTED = (
    "MARK_READY",
    "MERGE",
    "BRANCH_DELETION",
    "DEPLOYMENT",
    "PRODUCTION_RUNTIME_OR_CLOUD_MUTATION",
    "SERVICE_START_RESTART_ENABLE_REBOOT",
    "CREDENTIAL_OR_PRIVATE_API",
    "WALLET_OR_SIGNING",
    "EXCHANGE_WRITE_OR_ORDER_ACTION",
    "AUTONOMOUS_OR_REAL_CAPITAL_TRADING",
)
FOUR_GATES = (
    "MATURE_FRAMEWORK_FIRST=HARD_GATE",
    "OFFICIAL_SOURCE_BEFORE_CUSTOM_ADAPTER=HARD_GATE",
    "ROOT_CAUSE_BEFORE_PATCH=HARD_GATE",
    "END_TO_END_FUNCTIONAL_ACCEPTANCE=HARD_GATE",
)
CONTEXT_MARKERS = (
    "EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY",
    "FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED",
)
TWO_FIX = "TWO_FAILED_SEMANTIC_REMEDIES=>STOP_USER_PLUS_ORDINARY_CHATGPT"
USER_OVERRIDE = "USER_ROUTINE_OVERRIDE=EXPLICIT_SCOPED_GITHUB_RECORD"


class CheckFailure(RuntimeError):
    """The current governance is inconsistent or weakened."""


def content(root: Path, path: str) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckFailure(f"missing required file {path}") from exc


def require(text: str, tokens: tuple[str, ...], where: str) -> None:
    for token in tokens:
        if token not in text:
            raise CheckFailure(f"{where}: missing {token}")


def load_manifest(root: Path) -> dict[str, Any]:
    try:
        obj = json.loads(content(root, MANIFEST))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CheckFailure("malformed V6 manifest") from exc
    if not isinstance(obj, dict):
        raise CheckFailure("manifest must be an object")
    return obj


def check_manifest(m: dict[str, Any]) -> None:
    if m.get("governance_version") != "V6" or m.get("status") != "PILOT_ACTIVE":
        raise CheckFailure("V6 must be the only PILOT_ACTIVE governance")
    if m.get("sole_project_wide_constitution") != CANONICAL:
        raise CheckFailure("wrong sole V6 constitution")
    if m.get("repository") != "woshixiong/trader-assist-v0":
        raise CheckFailure("wrong canonical repository")
    if m.get("active_skills") != [SKILL]:
        raise CheckFailure("V5 or competing active skill not permitted")
    if m.get("protected_actions") != list(PROTECTED):
        raise CheckFailure("protected-action authority changed")
    if m.get("archived_governance", {}).get("constitution") != V5_ARCHIVE:
        raise CheckFailure("V5 archive locator missing")
    if m.get("codex", {}).get("execution_surface") != "PER_TASK_SINGLE_SESSION":
        raise CheckFailure("single-session executor choice not enforced")
    if m.get("codex", {}).get("semantic_session_continuity") != "REQUIRED_FAIL_CLOSED":
        raise CheckFailure("session continuity not fail closed")
    if m.get("user_decision", {}).get("protected_actions_require_current_authority") is not True:
        raise CheckFailure("human protected actions weakened")
    if m.get("user_decision", {}).get("two_failed_semantic_fixes") != (
        "STOP_USER_PLUS_ORDINARY_CHATGPT_DIRECTION"
    ):
        raise CheckFailure("two-fix stop weakened")
    required_entrypoints = {
        "AGENTS.md",
        "governance/PROJECT_RULES_INDEX.md",
        "governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md",
    }
    if set(m.get("entrypoints", [])) != required_entrypoints:
        raise CheckFailure("governance entrypoints incomplete")


def check_documents(root: Path) -> None:
    agent = content(root, "AGENTS.md")
    constitution = content(root, CANONICAL)
    bridge = content(root, "governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md")
    index = content(root, "governance/PROJECT_RULES_INDEX.md")
    skill = content(root, SKILL)
    workflow = content(root, ".github/workflows/ci.yml")
    _archive = content(root, V5_ARCHIVE)
    require(agent, FOUR_GATES + CONTEXT_MARKERS + (TWO_FIX, USER_OVERRIDE), "AGENTS")
    require(constitution, FOUR_GATES + CONTEXT_MARKERS + (TWO_FIX, USER_OVERRIDE), "constitution")
    require(bridge, FOUR_GATES + CONTEXT_MARKERS + (TWO_FIX, USER_OVERRIDE), "Project bridge")
    require(index, (CANONICAL, MANIFEST, SKILL, V5_ARCHIVE, TWO_FIX), "Rules Index")
    require(skill, CONTEXT_MARKERS + (TWO_FIX,), "V6 skill")
    require(constitution, (
        "PROTECTED_ACTIONS_REQUIRE_EXPLICIT_CURRENT_HUMAN_AUTHORITY=YES",
        "PAUSED_CAPABILITY", "systemd-journal", "FinalShell",
    ), "V6 protected/host policy")
    require(bridge, ("Mark Ready", "Merge", "RDC", "FinalShell"), "Project bridge")
    require(workflow, (
        "check_v6_governance.py",
        "V6 candidate/main governance downgrade",
        "CI_BASE_SHA", "CI_BEFORE_SHA", "governance/v6-min-migration-20261016",
        "--ignore=tests/control/test_v4_governance.py",
        "--ignore=tests/control/test_v5_governance.py",
        "subprocess.run(cmd, check=True)",
    ), "CI fail-closed selector")


def run(root: Path) -> list[str]:
    check_manifest(load_manifest(root))
    check_documents(root)
    return ["V6_MANIFEST", "V6_AUTHORITY", "V6_PROTECTED_GATES", "V6_CI_SELECTOR"]


if __name__ == "__main__":
    try:
        for result in run(Path(__file__).resolve().parents[1]):
            print("PASS " + result)
    except CheckFailure as exc:
        raise SystemExit("FAIL " + str(exc)) from exc
