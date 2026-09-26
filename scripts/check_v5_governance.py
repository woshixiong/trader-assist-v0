#!/usr/bin/env python3
"""Fail-closed consistency check for the V5 governance lifecycle."""

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
    status = m.get("status")
    if m.get("governance_version") != "V5" or status not in {
        "PRE_MERGE_CANDIDATE",
        "POST_MERGE_QUALIFICATION",
        "ACTIVE",
    }:
        raise CheckFailure("manifest is not in a valid V5 lifecycle state")
    if m.get("sole_project_wide_constitution") != CANONICAL:
        raise CheckFailure("sole V5 constitution mismatch")

    stale_main_authority = m.get("main_governance_until_activation_merge")
    if status == "PRE_MERGE_CANDIDATE":
        if not isinstance(stale_main_authority, dict):
            raise CheckFailure("pre-merge candidate must retain V4 main authority")
        main_governance = cast(dict[str, object], stale_main_authority)
        if main_governance.get("version") != "V4":
            raise CheckFailure("pre-merge candidate must retain V4 main authority")
    elif stale_main_authority is not None:
        raise CheckFailure("post-merge V5 state must not retain stale V4 main authority")

    codex = cast(dict[str, object], m.get("codex", {}))
    expected_runtime = (
        "NOT_YET_PROVEN" if status == "PRE_MERGE_CANDIDATE" else "BASELINE_QUALIFIED"
    )
    if codex.get("runtime_qualification") != expected_runtime:
        raise CheckFailure("runtime qualification does not match V5 lifecycle state")

    if status in {"POST_MERGE_QUALIFICATION", "ACTIVE"}:
        evidence = m.get("activation_merge_evidence")
        if evidence != {
            "merge_commit": "07eaa624d24973a9fd48fd15957f3ee60550bc4e",
            "reviewed_head": "7444ab6506ae740f1d151bb8fa8cb09f33215fd5",
            "reviewed_tree": "a1bad58b29479a06d4c007d2bf63b5ac5cef0de5",
        }:
            raise CheckFailure("activation merge evidence mismatch")

        deterministic = cast(dict[str, object], m.get("deterministic_runtime", {}))
        required_runtime = {
            "v5_bootstrap",
            "v5_governance_consistency_validator",
            "v5_controller_and_package_state",
            "exact_head_ci_waiter",
        }
        if any(deterministic.get(key) != "PASS" for key in required_runtime):
            raise CheckFailure("post-merge deterministic runtime qualification is incomplete")

        activation = cast(dict[str, object], m.get("activation_requirements", {}))
        passed = (
            "v5_b_controller_bootstrap_validator",
            "cli_and_gpt6_runtime_identity_qualification",
            "permission_auto_review_network_qualification",
            "protected_action_nonregression",
            "controller_and_failure_class_tests",
            "exact_head_ci",
            "fresh_independent_review",
            "project_instruction_replaced_with_version_agnostic_bridge",
        )
        if any(activation.get(key) != "PASS" for key in passed):
            raise CheckFailure("post-merge activation prerequisite is not PASS")
        canary = activation.get("first_real_nonproduction_v5_canary")
        if status == "POST_MERGE_QUALIFICATION" and canary != "PENDING":
            raise CheckFailure("qualification mode requires first V5 canary PENDING")
        if status == "ACTIVE" and canary != "PASS":
            raise CheckFailure("ACTIVE requires first V5 canary PASS")

    relay = m.get("execution_relay", {})
    if relay != {
        "preferred": "REMOTE_DESKTOP_COMMANDER_WHEN_CONNECTED_AND_QUOTA_AVAILABLE",
        "authority": "EXECUTION_TRANSPORT_ONLY",
        "hard_dependency": False,
    }:
        raise CheckFailure("execution relay metadata mismatch")

    protected = [
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
    ]
    if m.get("protected_actions") != protected:
        raise CheckFailure("protected-action authority changed")


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
        (
            "SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED",
            "REMOTE_DESKTOP_OFFLINE_OR_QUOTA_EXHAUSTED",
            "EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY",
            "FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED",
            "BROAD_ISSUE_OR_PR_HISTORY=>CONTROL_ESCALATION_ONLY",
        ),
        "bridge",
    )
    require(
        text(root, ".agents/skills/trade-os-v5-bootstrap/SKILL.md"),
        (
            "EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY",
            "FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED",
            "BROAD_ISSUE_OR_PR_HISTORY=>CONTROL_ESCALATION_ONLY",
        ),
        "V5 bootstrap skill",
    )
    require(
        text(root, ".agents/skills/trade-os-v5-review/SKILL.md"),
        (
            "PR_BOOTSTRAP=>METADATA_FIRST",
            "PR_SCOPE=>LIST_ALL_CHANGED_FILENAMES_FIRST",
            "FINAL_REVIEW=>REVIEW_EVERY_CHANGED_FILE",
            "PR_PATCH_IO=>FETCH_PER_FILE_OR_BOUNDED_CHUNK",
            "FULL_PR_TIMELINE=>NOT_ROUTINE_REVIEW_INPUT",
            "CI_SUCCESS=>STATUS_AND_LOCATOR_ONLY",
            "RAW_SUCCESS_LOG_INGESTION=PROHIBITED",
            "CI_FAILURE=>MINIMUM_DECISIVE_FAILING_EVIDENCE_ONLY",
        ),
        "V5 review skill",
    )
    require(
        text(root, ".agents/skills/trade-os-v5-handoff/SKILL.md"),
        (
            "EXACT_CANONICAL_LOCATOR_AVAILABLE=>HANDOFF_MUST_CARRY_EXACT_OBJECT",
            "GENERIC_ISSUE_OR_PR_HISTORY_INSTRUCTION_WHEN_EXACT_LOCATOR_KNOWN=PROHIBITED",
        ),
        "V5 handoff skill",
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
