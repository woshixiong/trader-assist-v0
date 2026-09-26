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
