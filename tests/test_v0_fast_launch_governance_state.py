from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_PATH = ROOT / "governance" / "V0_FAST_LAUNCH_PROGRAM.json"
STATE_PATH = ROOT / "governance" / "PROJECT_STATE.json"
SCHEMA_PATH = ROOT / "schemas" / "governance" / "V0FastLaunchProgram.schema.json"

BASE_SHA = "c507e2fc1bad6aca175cf833e5bcca63224c3e5f"
TASK_ID = "V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE"
NEXT_GATE = "V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE"

UPDATED_DOCS = (
    ROOT / "README.md",
    ROOT / "CODEX.md",
    ROOT / "docs" / "V0_01_SCOPE.md",
    ROOT / "docs" / "architecture" / "V0_01_DATA_PLANE.md",
    ROOT / "docs" / "architecture" / "AUTHORITY_BOUNDARY.md",
    ROOT / "docs" / "PROJECT_CONTROL_WORKFLOW.md",
    ROOT / "docs" / "V0_FAST_LAUNCH_PROGRAM.md",
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


def test_program_and_project_state_identity_parity() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)

    assert program["program_id"] == state["program"] == "V0-FAST-LAUNCH"
    assert program["project"] == state["project"] == "Trader Assist V0"
    assert program["repository"] == state["repository"]
    assert program["state_base_sha"] == state["state_base_sha"] == BASE_SHA
    assert program["task_id"] == state["active_task_id"] == TASK_ID
    assert "current_head_sha" not in state
    assert state["state_kind"] == "SAFE_STOP_SNAPSHOT"
    assert state["next_gate"] == NEXT_GATE


def test_completed_authority_and_false_gates_are_preserved() -> None:
    program = _load_json(PROGRAM_PATH)
    state = _load_json(STATE_PATH)
    authority = program["authority"]

    assert authority["last_completed_implementation_pr"] == 11
    assert authority["last_policy_state_pr"] == 12
    assert state["last_completed_implementation_pr"] == 11
    assert state["last_policy_state_pr"] == 12
    assert authority["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert state["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"

    false_gates = (
        "live_transport_authorized",
        "account_readonly_runtime_authorized",
        "testnet_execution_authorized",
        "mainnet_execution_authorized",
        "flp1_implementation_authorized",
    )
    for gate in false_gates:
        assert authority[gate] is False
        assert state[gate] is False

    assert state["active_write_lease"]["status"] == "NONE"


def test_first_release_and_signal_speed_policy_are_frozen() -> None:
    program = _load_json(PROGRAM_PATH)
    release = program["first_release"]
    speed = program["signal_speed_policy"]

    assert release["release_id"] == "V0-R0"
    assert release["primary_asset"] == "ETH"
    assert release["active_strategy_count"] == 1
    assert release["active_strategy"] == "ETH-LDAR-v0.1"
    assert release["all_valid_signals_visible"] is True
    assert release["automatic_exchange_write"] == "PROHIBITED"

    assert speed["speed_classes_are_not_strategies"] is True
    assert speed["classes"]["FAST"]["all_valid_signals_alerted"] is True
    assert speed["classes"]["FAST"]["execution_optional"] is True
    assert speed["classes"]["FAST"]["missed_execution_is_strategy_failure"] is False
    assert speed["classes"]["STANDARD"]["all_valid_signals_alerted"] is True
    assert {
        "LIQUIDITY_SWEEP_RECLAIM_FAST",
        "LIQUIDITY_SWEEP_PULLBACK_STANDARD",
    } <= set(speed["required_patterns"])


def test_lifecycles_learning_loop_and_roadmap_are_frozen() -> None:
    program = _load_json(PROGRAM_PATH)
    strategy = program["strategy_lifecycle"]
    data = program["data_product_lifecycle"]
    learning = program["learning_loop"]

    assert "required_data_products" in strategy["manifest_required_fields"]
    assert "replay_compatible" in strategy["manifest_required_fields"]
    assert data["strategy_raw_exchange_json_dependency"] == "PROHIBITED"
    assert data["new_data_auto_affects_existing_strategy"] is False
    assert learning["online_learning"] == "PROHIBITED"
    assert learning["automatic_production_rule_mutation"] == "PROHIBITED"

    assert program["capability_milestones"] == {
        "FL1": "TRUSTED_DATA_RUNTIME",
        "FL2": "SIGNAL_AND_RISK_ENGINE",
        "FL3": "HUMAN_REVIEW_SURFACE",
        "FL4": "HUMAN_CONFIRMED_EXECUTION",
    }
    assert program["releases"]["R1"]["autonomous_entry"] == "PROHIBITED"
    assert program["releases"]["R1"]["human_confirmation_required"] is True


def test_governance_and_rotation_policy_are_frozen() -> None:
    program = _load_json(PROGRAM_PATH)
    levels = program["governance_levels"]
    route = program["development_route"]
    review = program["review_finalization_policy"]
    rotation = program["recursive_rotation"]

    assert levels["flp1_minimum"] == "G3"
    assert levels["fl4_requirement"] == "SEPARATE_G4_EXECUTION_AND_SECURITY_REVIEW"
    assert route["finding_classes"] == ["BLOCKER", "FOLLOW_UP"]
    assert route["only_blocker_prevents_merge"] is True
    assert review["external_independent_review_required"] is True
    assert review["mark_ready_prohibited"] is True
    assert review["merge_prohibited"] is True
    assert rotation["required"] is True
    assert rotation["next_window_permission"] == "STRICT_READ_ONLY"
    assert rotation["post_merge_next_gate"] == NEXT_GATE


def test_updated_documents_agree_and_remove_ambiguous_state_wording() -> None:
    required_markers = (
        "V0-FAST-LAUNCH",
        "LAST_COMPLETED_IMPLEMENTATION_PR: 11",
        "LAST_POLICY_STATE_PR: 12",
    )
    combined = ""
    for path in UPDATED_DOCS:
        text = path.read_text(encoding="utf-8")
        combined += text
        if path.name in {"README.md", "CODEX.md", "V0_01_SCOPE.md"}:
            for marker in required_markers:
                assert marker in text

    assert "LAST_MERGED_PR" not in combined
    assert "A7 scope-freeze planning only" not in combined
    assert "LIVE_TRANSPORT_AUTHORIZED: TRUE" not in combined
    assert "TESTNET_EXECUTION_AUTHORIZED: TRUE" not in combined
    assert "MAINNET_EXECUTION_AUTHORIZED: TRUE" not in combined
    assert "FLP1_IMPLEMENTATION_AUTHORIZED: TRUE" not in combined
