#!/usr/bin/env python3
"""Fail-closed consistency check for the active V4 governance/tooling layer."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

CANONICAL = "governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md"
MANIFEST = "governance/ACTIVE_GOVERNANCE_MANIFEST.json"
SKILLS = (
    ".agents/skills/trade-os-v4-bootstrap/SKILL.md",
    ".agents/skills/trade-os-v4-development/SKILL.md",
    ".agents/skills/trade-os-v4-ci/SKILL.md",
    ".agents/skills/trade-os-v4-review/SKILL.md",
)


class CheckFailure(RuntimeError):
    """Raised when a V4 invariant is missing or contradictory."""


def read_text(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise CheckFailure(f"missing required file: {relative}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needles: tuple[str, ...], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise CheckFailure(f"{label} missing: {', '.join(missing)}")


def load_manifest(root: Path) -> dict[str, object]:
    try:
        value = json.loads(read_text(root, MANIFEST))
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"invalid manifest JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CheckFailure("active manifest must be a JSON object")
    return value


def manifest_str(manifest: dict[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        raise CheckFailure(f"manifest {key} must be a non-empty string")
    return value


def manifest_list(manifest: dict[str, object], key: str) -> tuple[str, ...]:
    value = manifest.get(key)
    if not isinstance(value, list) or not value:
        raise CheckFailure(f"manifest {key} must be a non-empty list")
    strings = tuple(item for item in value if isinstance(item, str))
    if len(strings) != len(value):
        raise CheckFailure(f"manifest {key} must contain only strings")
    return strings


def check_single_constitution(root: Path) -> None:
    manifest = load_manifest(root)
    if manifest_str(manifest, "sole_project_wide_constitution") != CANONICAL:
        raise CheckFailure("manifest canonical constitution mismatch")
    v4 = read_text(root, CANONICAL)
    require_contains(
        v4,
        (
            "SOLE PROJECT-WIDE ENGINEERING CONSTITUTION",
            "V4_SOLE_ACTIVE_CONSTITUTION=YES",
            "No historical file may override V4.",
        ),
        "V4",
    )
    active_files = ("AGENTS.md", "governance/PROJECT_RULES_INDEX.md", *manifest_list(manifest, "entrypoints"))
    banned = (
        "Unified V2 remains the sole project-wide normative engineering constitution",
        "UNIFIED_V2_REMAINS_SINGLE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES",
    )
    for relative in dict.fromkeys(str(item) for item in active_files):
        text = read_text(root, relative)
        if any(phrase in text for phrase in banned):
            raise CheckFailure(f"active file retains a V2 sole-authority claim: {relative}")
    for historical in (
        "governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md",
        "governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md",
    ):
        if "HISTORICAL / SUPERSEDED BY V4" not in read_text(root, historical)[:700]:
            raise CheckFailure(f"missing historical banner: {historical}")


def check_manifest(root: Path) -> None:
    manifest = load_manifest(root)
    if manifest.get("status") != "ACTIVE" or manifest.get("governance_version") != "V4":
        raise CheckFailure("manifest must identify active V4")
    required_lists = (
        "entrypoints",
        "active_checklists",
        "active_subordinate_procedures",
        "active_skills",
        "historical_or_superseded",
        "protected_actions",
    )
    for key in required_lists:
        manifest_list(manifest, key)
    paths = (
        manifest_str(manifest, "sole_project_wide_constitution"),
        *manifest_list(manifest, "entrypoints"),
        *manifest_list(manifest, "active_checklists"),
        *manifest_list(manifest, "active_subordinate_procedures"),
        *manifest_list(manifest, "active_skills"),
    )
    for item in paths:
        if not (root / str(item)).is_file():
            raise CheckFailure(f"manifest path does not exist: {item}")


def check_router(root: Path) -> None:
    agents = read_text(root, "AGENTS.md")
    require_contains(
        agents,
        (
            CANONICAL,
            "A DETERMINISTIC / MECHANICAL",
            "B SMALL / FROZEN / QUICK SEMANTIC",
            "C LARGE / COHERENT / MULTI-STEP CODING",
            "D UNRESOLVED ARCHITECTURE / SECURITY / AUTHORITY",
            "WORK_TO_ABILITY_BOUNDARY=REQUIRED",
        ),
        "AGENTS router",
    )


def check_index(root: Path) -> None:
    index = read_text(root, "governance/PROJECT_RULES_INDEX.md")
    require_contains(index, (MANIFEST, CANONICAL, *SKILLS), "Rules Index")


def load_toml(root: Path, relative: str) -> dict[str, object]:
    try:
        with (root / relative).open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CheckFailure(f"invalid TOML {relative}: {exc}") from exc
    return value


def check_codex_config(root: Path) -> None:
    config = load_toml(root, ".codex/config.toml")
    expected = {
        "model": "gpt-5.6-terra",
        "model_reasoning_effort": "medium",
        "web_search": "disabled",
        "sandbox_mode": "workspace-write",
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise CheckFailure(f"Codex config {key} must equal {value}")
    agents = config.get("agents")
    if not isinstance(agents, dict):
        raise CheckFailure("Codex config agents table missing")
    for role in ("explorer", "code_reviewer"):
        if not isinstance(agents.get(role), dict):
            raise CheckFailure(f"Codex config agent declaration missing: {role}")
    hooks = config.get("hooks")
    if not isinstance(hooks, dict) or not hooks.get("PreToolUse"):
        raise CheckFailure("PreToolUse hook declaration missing")


def check_agent(root: Path, relative: str, model: str, reasoning: str) -> None:
    agent = load_toml(root, relative)
    if agent.get("model") != model:
        raise CheckFailure(f"{relative} model mismatch")
    if agent.get("model_reasoning_effort") != reasoning:
        raise CheckFailure(f"{relative} reasoning must be {reasoning}")
    if agent.get("sandbox_mode") != "read-only":
        raise CheckFailure(f"{relative} must be read-only")
    instructions = agent.get("developer_instructions")
    if not isinstance(instructions, str) or "Do not edit" not in instructions:
        raise CheckFailure(f"{relative} lacks explicit no-edit boundary")


def check_model_routing(root: Path) -> None:
    v4 = read_text(root, CANONICAL)
    require_contains(
        v4,
        (
            "SUBAGENT_MODEL_REASONING_MUST_BE_RUNTIME_VERIFIABLE=YES",
            "UNVERIFIED_SUBAGENT_MODEL_INHERITANCE=PROHIBITED",
            "FALLBACK_TO_PARENT_SOL_HIGH=PROHIBITED",
            "SILENT_REVIEWER_PROFILE_FALLBACK=PROHIBITED",
        ),
        "subagent runtime identity",
    )
    manifest = load_manifest(root)
    codex = manifest.get("codex")
    if not isinstance(codex, dict):
        raise CheckFailure("manifest codex object missing")
    if codex.get("main_writer_model") != "gpt-5.6-terra":
        raise CheckFailure("routine Codex Writer must default to Terra")
    if codex.get("hard_semantic_escalation_model") != "gpt-5.6-sol":
        raise CheckFailure("hard semantic escalation must bind Sol explicitly")
    if codex.get("subagent_runtime_identity_verification_required") is not True:
        raise CheckFailure("subagent runtime identity verification must be required")
    if codex.get("silent_subagent_fallback_prohibited") is not True:
        raise CheckFailure("silent subagent fallback must be prohibited")


def check_transport_nonregression(root: Path) -> None:
    procedure = read_text(
        root,
        "governance/GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md",
    )
    require_contains(
        procedure,
        (
            "GH_WORKFLOW_SCOPE_VERIFIED=YES",
            "git push --dry-run",
            "SSL_ERROR_SYSCALL",
            "LOCAL_PUSH_RETRY=PROHIBITED",
            "CONNECTED_PROVIDER_GITHUB_RECOVERY=REQUIRED_WHEN_AVAILABLE",
            "--insecure-storage",
        ),
        "GitHub local transport",
    )


def check_skills(root: Path) -> None:
    expected = {
        SKILLS[0]: ("trade-os-v4-bootstrap", "PRE_MODEL", "CONTROL_CAPSULE_REF"),
        SKILLS[1]: (
            "trade-os-v4-development",
            "PLAN_BOUNDARY_CHECK=PASS",
            "CI_PENDING",
            "SUBAGENT_MODEL_REASONING_MUST_BE_RUNTIME_VERIFIABLE=YES",
        ),
        SKILLS[2]: ("trade-os-v4-ci", "MODEL_REQUIRED=NO", "MODEL_MEDIATED_CI_POLLING=PROHIBITED"),
        SKILLS[3]: ("trade-os-v4-review", "COMMENT_ONLY", "fresh ordinary ChatGPT"),
    }
    for relative, needles in expected.items():
        require_contains(read_text(root, relative), needles, relative)


def check_bootstrap_surface(root: Path) -> None:
    text = read_text(root, "scripts/control/v4_bootstrap.py")
    require_contains(
        text,
        (
            "remote/base mismatch",
            "worktree HEAD mismatch",
            "worktree is dirty or ambiguous",
            "preflight binding mismatch",
            "model mismatch",
            "reasoning mismatch",
        ),
        "V4 bootstrap",
    )


def check_review_contract(root: Path) -> None:
    v4 = read_text(root, CANONICAL)
    require_contains(
        v4,
        (
            "Codex Code Review",
            "Final independent review",
            "REVIEW_SUBMISSION_MODE=COMMENT_ONLY",
            "MODEL_MEDIATED_CI_POLLING=PROHIBITED",
        ),
        "review/CI contract",
    )


def check_ability_boundary(root: Path) -> None:
    v4 = read_text(root, CANONICAL)
    require_contains(
        v4,
        (
            "WORK_TO_ABILITY_BOUNDARY=REQUIRED",
            "ROUTINE_CONTINUE_CONFIRMATION=PROHIBITED",
            "USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED",
            "NEXT_NODE_DIRECT_HANDOFF=REQUIRED",
            "B. SMALL / FROZEN / QUICK SEMANTIC",
        ),
        "ability boundary",
    )


def check_protected_actions(root: Path) -> None:
    manifest = load_manifest(root)
    required = {
        "MARK_READY",
        "MERGE",
        "DEPLOYMENT",
        "PRODUCTION_RUNTIME_OR_CLOUD_MUTATION",
        "CREDENTIAL_OR_PRIVATE_API",
        "EXCHANGE_WRITE_OR_ORDER_ACTION",
        "AUTONOMOUS_OR_REAL_CAPITAL_TRADING",
    }
    protected = set(manifest_list(manifest, "protected_actions"))
    if not required <= protected:
        raise CheckFailure("protected-action manifest is incomplete")


def checks() -> tuple[tuple[str, Callable[[Path], None]], ...]:
    return (
        ("V4_SINGLE_CONSTITUTION", check_single_constitution),
        ("ACTIVE_GOVERNANCE_MANIFEST", check_manifest),
        ("AGENTS_ROUTER", check_router),
        ("PROJECT_RULES_INDEX", check_index),
        ("CODEX_CONFIG_PARSE", check_codex_config),
        (
            "EXPLORER_READ_ONLY",
            lambda root: check_agent(root, ".codex/agents/explorer.toml", "gpt-5.6-luna", "low"),
        ),
        (
            "CODE_REVIEWER_READ_ONLY",
            lambda root: check_agent(root, ".codex/agents/code-reviewer.toml", "gpt-5.6-terra", "medium"),
        ),
        ("MODEL_ROUTING_POLICY", check_model_routing),
        ("GITHUB_TRANSPORT_NONREGRESSION", check_transport_nonregression),
        ("SKILL_DISCOVERY", check_skills),
        ("EXACT_BASE_BOOTSTRAP", check_bootstrap_surface),
        ("DIRTY_WORKTREE_REJECTION", check_bootstrap_surface),
        ("MODEL_ROUTE_ATTESTATION", check_bootstrap_surface),
        ("CI_ZERO_MODEL_CONTRACT", check_review_contract),
        ("COMMENT_ONLY_REVIEW_FALLBACK", check_review_contract),
        ("ABILITY_BOUNDARY_CONTINUATION", check_ability_boundary),
        ("ORDINARY_CHATGPT_WRITER_BRANCH", check_ability_boundary),
        ("PROTECTED_ACTION_GATE", check_protected_actions),
    )


def run(root: Path) -> list[str]:
    failures: list[str] = []
    for label, check in checks():
        try:
            check(root)
        except (CheckFailure, KeyError, TypeError) as exc:
            failures.append(f"{label}=FAIL: {exc}")
        else:
            print(f"{label}=PASS")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    failures = run(Path(args.repository).resolve())
    for failure in failures:
        print(failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
