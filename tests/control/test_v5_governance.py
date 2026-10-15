from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_v5", ROOT / "scripts/check_v5_governance.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


def manifest() -> dict[str, Any]:
    return copy.deepcopy(checker.manifest(ROOT))


def install(monkeypatch: pytest.MonkeyPatch, value: dict[str, Any]) -> None:
    monkeypatch.setattr(checker, "manifest", lambda _: value)


def test_v5_active_consistency() -> None:
    assert checker.run(ROOT) == []


def test_qualification_requires_proven_prerequisites(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["status"] = "POST_MERGE_QUALIFICATION"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PENDING"
    value["activation_requirements"]["exact_head_ci"] = "PENDING"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="prerequisite"):
        checker.check_manifest(ROOT)


def test_qualification_rejects_stale_v4_until_merge_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["status"] = "POST_MERGE_QUALIFICATION"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PENDING"
    value["main_governance_until_activation_merge"] = {
        "version": "V4",
        "constitution": "governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md",
    }
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="stale V4"):
        checker.check_manifest(ROOT)


def test_qualification_requires_canary_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["status"] = "POST_MERGE_QUALIFICATION"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PENDING"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PASS"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="canary PENDING"):
        checker.check_manifest(ROOT)


def test_active_requires_canary_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["status"] = "ACTIVE"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PENDING"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="ACTIVE requires"):
        checker.check_manifest(ROOT)


def test_active_with_required_facts_pass_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["status"] = "ACTIVE"
    value["activation_requirements"]["first_real_nonproduction_v5_canary"] = "PASS"
    install(monkeypatch, value)
    checker.check_manifest(ROOT)


def test_runtime_qualification_must_match_active_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["codex"]["runtime_qualification"] = "NOT_YET_PROVEN"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="runtime qualification"):
        checker.check_manifest(ROOT)


def test_protected_action_authority_cannot_change(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["protected_actions"] = value["protected_actions"][:-1]
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="protected-action authority changed"):
        checker.check_manifest(ROOT)


@pytest.mark.parametrize(
    ("path", "needle"),
    [
        (
            "governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md",
            "EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY",
        ),
        (
            ".agents/skills/trade-os-v5-bootstrap/SKILL.md",
            "FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED",
        ),
        (
            ".agents/skills/trade-os-v5-review/SKILL.md",
            "PR_SCOPE=>LIST_ALL_CHANGED_FILENAMES_FIRST",
        ),
        (
            ".agents/skills/trade-os-v5-review/SKILL.md",
            "FINAL_REVIEW=>REVIEW_EVERY_CHANGED_FILE",
        ),
        (
            ".agents/skills/trade-os-v5-review/SKILL.md",
            "PR_PATCH_IO=>FETCH_PER_FILE_OR_BOUNDED_CHUNK",
        ),
        (
            ".agents/skills/trade-os-v5-handoff/SKILL.md",
            "EXACT_CANONICAL_LOCATOR_AVAILABLE=>HANDOFF_MUST_CARRY_EXACT_OBJECT",
        ),
    ],
)
def test_context_io_document_invariants_are_required(
    monkeypatch: pytest.MonkeyPatch, path: str, needle: str
) -> None:
    original_text = checker.text

    def without_invariant(root: Path, requested: str) -> str:
        value = original_text(root, requested)
        return value.replace(needle, "REMOVED_CONTEXT_IO_INVARIANT") if requested == path else value

    monkeypatch.setattr(checker, "text", without_invariant)
    with pytest.raises(checker.CheckFailure):
        checker.check_documents(ROOT)



def test_transient_network_recovery_contract_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["network_resilience"]["transient_fast_max_attempts"] = 0
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="network resilience"):
        checker.check_manifest(ROOT)


def test_unknown_network_write_must_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    value = manifest()
    value["network_resilience"]["ambiguous_write"] = "BLIND_RETRY"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="network resilience"):
        checker.check_manifest(ROOT)



@pytest.mark.parametrize(
    "rule_name",
    [
        "FRAMEWORK_NATIVE_REUSE_REQUIRED",
        "OFFICIAL_COMMUNITY_SEARCH_BEFORE_PATCH",
        "ROOT_CAUSE_BEFORE_CODE",
        "SYSTEM_WIDE_CAUSAL_VERIFICATION",
    ],
)
def test_all_four_native_first_invariants_are_mandatory(
    monkeypatch: pytest.MonkeyPatch, rule_name: str
) -> None:
    value = manifest()
    value["engineering_invariants"][rule_name] = "OPTIONAL"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="mandatory framework-native"):
        checker.check_manifest(ROOT)


def test_cannot_reenable_duplicate_commodity_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["engineering_invariants"]["NEW_COMMODITY_ENGINE"] = "ALLOWED"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="commodity duplicate"):
        checker.check_manifest(ROOT)


def test_pinned_native_version_cannot_silently_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["engineering_invariants"]["PINNED_NATIVE_VERSION"] = "LATEST"
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="pinned native API"):
        checker.check_manifest(ROOT)


@pytest.mark.parametrize(
    "path",
    [
        "AGENTS.md",
        "governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md",
        ".agents/skills/trade-os-v5-development/SKILL.md",
        ".agents/skills/trade-os-v5-review/SKILL.md",
    ],
)
def test_native_first_four_rules_present_across_router_and_skills(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    original = checker.text

    def drop_rule(root: Path, requested: str) -> str:
        body = original(root, requested)
        if requested == path:
            return body.replace("ROOT_CAUSE_BEFORE_CODE", "ROOT_CAUSE_MISSING")
        return body

    monkeypatch.setattr(checker, "text", drop_rule)
    with pytest.raises(checker.CheckFailure, match="native-first routing"):
        checker.check_documents(ROOT)



def test_explicit_user_review_waiver_requires_verifiable_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["user_workflow_override"]["requires_independent_provenance_not_writer_string"] = False
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="explicit-user process waiver"):
        checker.check_manifest(ROOT)


def test_waiver_cannot_cancel_correctness_and_deployment_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = manifest()
    value["user_workflow_override"]["mandatory_tests_and_hash_deploy_proof"] = False
    install(monkeypatch, value)
    with pytest.raises(checker.CheckFailure, match="explicit-user process waiver"):
        checker.check_manifest(ROOT)
