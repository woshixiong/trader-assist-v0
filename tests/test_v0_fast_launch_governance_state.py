from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / "governance" / "V0_FAST_LAUNCH_PROGRAM.json"
STATE_PATH = ROOT / "governance" / "PROJECT_STATE.json"
SCHEMA_PATH = ROOT / "schemas" / "governance" / "V0FastLaunchProgram.schema.json"

TASK_ID = "V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT"
BASE_SHA = "78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae"
NEXT_GATE = "V0-FLP1B0B-EXTERNAL-INDEPENDENT-REVIEW"
AUTHORITY_HASH = "0e327e566589d8030ff00d4d009eb4b6827679ab508133d66840b2c245dc53df"
SOURCE_CATALOG_HASH = "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"

EXPECTED_CHANGED_FILES = {
    ".github/workflows/ci.yml",
    "README.md",
    "docs/V0_01_SCOPE.md",
    "docs/V0_FAST_LAUNCH_PROGRAM.md",
    "docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
    "docs/architecture/V0_01_DATA_PLANE.md",
    "docs/architecture/AUTHORITY_BOUNDARY.md",
    "docs/architecture/STRATEGY_AND_DATA_LIFECYCLE.md",
    "docs/architecture/PILOT_LEARNING_LOOP.md",
    "governance/V0_FAST_LAUNCH_PROGRAM.json",
    "governance/PROJECT_STATE.json",
    "schemas/governance/V0FastLaunchProgram.schema.json",
    "src/trader_assist_v0/contracts/capture.py",
    "src/trader_assist_v0/contracts/__init__.py",
    "scripts/export_schemas.py",
    "schemas/v0/CaptureRecordV0.schema.json",
    "tests/test_v0_flp1b0b_capture_now_authority.py",
    "tests/test_v0_fast_launch_governance_state.py",
}

FORBIDDEN_FILES = {
    "CODEX.md",
    "docs/PROJECT_CONTROL_WORKFLOW.md",
    "docs/V0_01_OFFICIAL_SOURCE_CATALOG.md",
    "src/trader_assist_v0/contracts/common.py",
    "src/trader_assist_v0/contracts/events.py",
    "src/trader_assist_v0/contracts/source_catalog.py",
    "src/trader_assist_v0/contracts/rate_limits.py",
    "pyproject.toml",
    "requirements-dev.lock",
    "requirements-runtime.lock",
}

DOC_PATHS = (
    ROOT / "README.md",
    ROOT / "docs" / "V0_01_SCOPE.md",
    ROOT / "docs" / "V0_FAST_LAUNCH_PROGRAM.md",
    ROOT / "docs" / "V0_FLP0_CAPTURE_NOW_AUTHORITY.md",
    ROOT / "docs" / "architecture" / "V0_01_DATA_PLANE.md",
    ROOT / "docs" / "architecture" / "AUTHORITY_BOUNDARY.md",
    ROOT / "docs" / "architecture" / "STRATEGY_AND_DATA_LIFECYCLE.md",
    ROOT / "docs" / "architecture" / "PILOT_LEARNING_LOOP.md",
)


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_schema_self_validation_and_instances() -> None:
    schema = _load_json(SCHEMA_PATH)
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(program)
    state_schema = schema["$defs"]["ProjectState"]
    assert isinstance(state_schema, dict)
    Draft202012Validator.check_schema(state_schema)
    Draft202012Validator(state_schema).validate(state)


def test_program_state_and_release_authority_parity() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)

    assert program["task_id"] == state["active_task_id"] == TASK_ID
    assert program["state_base_sha"] == state["state_base_sha"] == BASE_SHA
    assert state["active_write_lease"]["status"] == "NONE"
    assert state["active_write_lease"]["final_status"] == (
        "CONSUMED_PENDING_PROJECT_CONTROL_ACCEPTANCE"
    )
    assert state["next_gate"] == NEXT_GATE
    assert program["recursive_rotation"]["post_merge_next_gate"] == NEXT_GATE

    release_authority = program["release_authority"]
    assert release_authority == {
        "R0": "CAPTURE_ONLY",
        "R1": "ETH_OPERATOR_ASSIST",
        "FIRST_LAUNCH_PRIMARY_ASSET": "ETH",
        "BTC_FIRST_LAUNCH_REQUIREMENT": "NONE",
        "BTC_FIRST_LAUNCH_BLOCKER": "NO",
        "T1": "CONTRACT_SCHEMA_GOVERNANCE_ONLY",
        "T2": "SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME",
    }


def test_r0_r1_and_deferred_g4_migration() -> None:
    program = _load_json(PROGRAM_PATH)
    r0 = program["first_release"]
    r1 = program["releases"]["R1"]
    deferred = program["future_human_confirmed_execution"]

    assert r0["release_id"] == "V0-R0"
    assert r0["release_authority"] == "CAPTURE_ONLY"
    assert r0["primary_asset"] == "ETH"
    assert r0["active_strategy_count"] == 0
    assert r0["capture_contracts_authorized"] is True
    for gate in (
        "network_runtime_authorized",
        "strategy_runtime_authorized",
        "signal_recommendation_authorized",
        "risk_sizing_authorized",
        "trade_plan_authorized",
        "account_runtime_authorized",
        "exchange_execution_authorized",
    ):
        assert r0[gate] is False

    assert r1["release_id"] == "V0-R1"
    assert r1["scope"] == "ETH_OPERATOR_ASSIST"
    assert r1["status"] == "FUTURE_NOT_IMPLEMENTED_NOT_AUTHORIZED"
    assert r1["primary_asset"] == "ETH"
    assert r1["signal_outputs"] == ["LONG", "SHORT", "WAIT"]
    assert r1["deterministic_risk"] is True
    assert r1["trade_plan"] is True
    assert r1["presentation"] == ["FAST", "STANDARD"]
    assert r1["manual_execution"] is True
    assert r1["readonly_account_order_fill_observation"] is True
    assert r1["implementation_authorized"] is False
    assert r1["exchange_execution_authorized"] is False

    assert deferred["assigned_release_id"] is None
    assert deferred["release_id_authorized"] is False
    assert deferred["status"] == "DEFERRED_SEPARATE_G4_GATE"
    assert deferred["autonomous_entry"] == "PROHIBITED"
    assert deferred["human_confirmation_required"] is True
    assert deferred["implementation_authorized"] is False
    assert deferred["testnet_execution_authorized"] is False
    assert deferred["mainnet_execution_authorized"] is False
    assert "OFFICIAL_SDK_SIGNING" in deferred["required_controls"]
    assert "SEPARATE_MAINNET_AUTHORIZATION" in deferred["required_controls"]
    assert "required_controls" not in r1


def test_rate_limit_authority_immutability_and_false_gates() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)
    authority = program["authority"]

    for document in (authority, state):
        assert document["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"
        assert document["conflict_state"] == "OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED"
        assert document["supersession_state"] == "EFFECTIVE_VARIANT_UNDETERMINED"
        assert document["authority_hash"] == AUTHORITY_HASH
        assert document["source_catalog_hash"] == SOURCE_CATALOG_HASH
        assert document["source_count"] == 2
        assert document["fact_count"] == 25
        assert document["unknown_count"] == 14
        for gate in (
            "transition_eligible",
            "live_transport_authorized",
            "account_readonly_runtime_authorized",
            "testnet_execution_authorized",
            "mainnet_execution_authorized",
            "flp1_implementation_authorized",
        ):
            assert document[gate] is False


def test_docs_share_capture_now_semantics() -> None:
    required_tokens = (
        "CAPTURE_ONLY",
        "ETH_OPERATOR_ASSIST",
        "CONTRACT_SCHEMA_GOVERNANCE_ONLY",
        "SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME",
    )
    for path in DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        for token in required_tokens:
            assert token in text, path

    capture_doc = (ROOT / "docs" / "V0_FLP0_CAPTURE_NOW_AUTHORITY.md").read_text(
        encoding="utf-8"
    )
    assert "RAW_PUBLIC_EVIDENCE_PLANE" in capture_doc
    assert "CAPTURE_AUTHORITY_PLANE" in capture_doc
    assert AUTHORITY_HASH in capture_doc
    assert SOURCE_CATALOG_HASH in capture_doc


def test_exact_changed_file_scope_and_forbidden_boundaries() -> None:
    try:
        committed_result = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACMRT",
                f"{BASE_SHA}...HEAD",
                "--",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise AssertionError(
            f"cannot compare BASE_SHA to HEAD: {exc.stderr.strip()}"
        ) from exc
    unstaged_result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMRT", "HEAD", "--"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    staged_result = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--diff-filter=ACMRT",
            "HEAD",
            "--",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    changed = {
        line
        for line in (
            *committed_result.stdout.splitlines(),
            *unstaged_result.stdout.splitlines(),
            *staged_result.stdout.splitlines(),
            *untracked_result.stdout.splitlines(),
        )
        if line
    }
    assert changed == EXPECTED_CHANGED_FILES
    assert not (changed & FORBIDDEN_FILES)
    assert not any(path.startswith("src/trader_assist_v0/data/") for path in changed)
    assert {
        path for path in changed if path.startswith(".github/workflows/")
    } == {".github/workflows/ci.yml"}
