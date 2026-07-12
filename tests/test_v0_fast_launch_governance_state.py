from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
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
    assert route["bounded_repairs_same_scope_required"] is True
    assert route["bounded_repairs_original_pr_required"] is True
    assert review["external_independent_review_required"] is True
    assert review["mark_ready_prohibited"] is True
    assert review["merge_prohibited"] is True
    assert review["exact_head_review_required"] is True
    assert review["writer_reviewer_separation_required"] is True
    assert review["finalization_separate_task_required"] is True
    assert review["separate_project_control_finalization_authorization_required"] is True
    assert review["pre_finalization_base_head_state_reverification_required"] is True
    assert review["unresolved_blocker_prevents_merge"] is True
    assert rotation["required"] is True
    assert rotation["next_window_permission"] == "STRICT_READ_ONLY"
    assert rotation["post_merge_next_gate"] == NEXT_GATE
    assert rotation["current_safe_stop_point_required"] is True
    assert rotation["complete_handoff_prompt_required"] is True
    assert all(rotation["recursive_window_rotation_requirement"].values())


Mutation = tuple[str, tuple[str | int, ...], Any]

R1_REQUIRED_CONTROLS = (
    "DEDICATED_LIMITED_CAPITAL_SUBACCOUNT",
    "DEDICATED_API_WALLET",
    "SECRET_ISOLATION",
    "OFFICIAL_SDK_SIGNING",
    "NONCE_AUTHORITY",
    "IMMUTABLE_ORDER_INTENT",
    "ORDER_INTENT_HASH",
    "CLOID_IDEMPOTENCY",
    "EXPIRES_AFTER",
    "PRE_SUBMIT_REVALIDATION",
    "ALO_POST_ONLY",
    "BOUNDED_SLIPPAGE_IOC",
    "SUBMIT_CANCEL",
    "PARTIAL_FILL_HANDLING",
    "ACTUAL_FILLED_POSITION_SIZING",
    "MANDATORY_AUTOMATIC_STOP",
    "FIXED_MULTI_STAGE_AUTOMATIC_TP",
    "REDUCE_ONLY_PROTECTION",
    "EXCHANGE_STATE_PROTECTION_VERIFICATION",
    "POSITION_UNPROTECTED_EMERGENCY_PATH",
    "KILL_SWITCH",
    "DEAD_MAN_PROTECTION",
    "AUDIT",
    "TESTNET",
    "SHADOW",
    "SMALL_CAPITAL_MAINNET_CANARY",
    "SEPARATE_MAINNET_AUTHORIZATION",
)

R2_FINALIZATION_FIELDS = (
    "exact_head_review_required",
    "writer_reviewer_separation_required",
    "finalization_separate_task_required",
    "separate_project_control_finalization_authorization_required",
    "pre_finalization_base_head_state_reverification_required",
    "unresolved_blocker_prevents_merge",
)

R2_REPAIR_ROUTE_FIELDS = (
    "bounded_repairs_same_scope_required",
    "bounded_repairs_original_pr_required",
)

R2_ROTATION_TRIGGERS = (
    "PR_MERGED",
    "ISSUE_OR_EPIC_COMPLETED",
    "STAGE_ENDS_BEFORE_NEW_STAGE",
    "REVIEW_PLUS_REPAIR_EXCEEDS_TWO_ROUNDS",
    "HEAD_DRIFT",
    "WRITER_COLLISION",
    "WRITE_LEASE_REVOKED_OR_PERMISSION_CHANGED",
    "MULTIPLE_PRS_STAGES_OR_STALE_STATES",
    "USER_REPEATEDLY_REQUESTS_PROJECT_STATUS",
    "CONTEXT_LENGTH_RISKS_STALE_FACT_CONTAMINATION",
    "OLD_HEAD_CI_OR_PR_STATE_REUSE_RISK",
    "PROJECT_SWITCH_BETWEEN_TRADER_ASSIST_V0_AND_TRADE_OS",
    "USER_EXPLICITLY_REQUESTS_NEW_WINDOW",
    "MULTIPLE_EXECUTION_REVIEW_REPAIR_OR_FINALIZATION_PROMPTS",
)

R2_REQUIRED_ROTATION_OUTPUT = (
    "WINDOW_ROTATION_REQUIRED",
    "REASON",
    "CURRENT_SAFE_STOP_POINT",
    "NEXT_WINDOW_HANDOFF_PROMPT",
)

R2_ROTATION_FLAGS = (
    "current_safe_stop_point_required",
    "complete_handoff_prompt_required",
)

R2_RECURSIVE_REQUIREMENT_FIELDS = (
    "future_handoffs_must_include_complete_rotation_policy",
    "future_handoffs_must_include_all_rotation_triggers",
    "future_handoffs_must_include_required_rotation_output",
    "future_handoffs_must_include_recursive_requirement_itself",
    "receiving_window_must_propagate_requirement",
    "applies_to_every_later_handoff",
    "one_time_summary_or_non_propagating_simplification_prohibited",
)


def _case(mutation: Mutation, case_id: str) -> Any:
    return pytest.param(mutation, id=case_id)


def _program_mutation_cases() -> list[Any]:
    cases = [
        _case(
            ("set", ("signal_speed_policy", "classes", "FAST", "all_valid_signals_alerted"), False),
            "signals-fast-alert-disabled",
        ),
        _case(
            ("set", ("signal_speed_policy", "classes", "FAST", "short_expiry"), False),
            "signals-fast-short-expiry-disabled",
        ),
        _case(
            ("set", ("signal_speed_policy", "classes", "FAST", "execution_optional"), False),
            "signals-fast-optional-disabled",
        ),
        _case(
            (
                "set",
                ("signal_speed_policy", "classes", "FAST", "max_entry_boundary_required"),
                False,
            ),
            "signals-fast-max-entry-disabled",
        ),
        _case(
            ("set", ("signal_speed_policy", "classes", "FAST", "do_not_chase_required"), False),
            "signals-fast-do-not-chase-disabled",
        ),
        _case(
            (
                "set",
                ("signal_speed_policy", "classes", "FAST", "human_actionability_recorded"),
                False,
            ),
            "signals-fast-actionability-disabled",
        ),
        _case(
            (
                "set",
                ("signal_speed_policy", "classes", "FAST", "missed_execution_is_strategy_failure"),
                True,
            ),
            "signals-fast-missed-becomes-failure",
        ),
        _case(
            (
                "set",
                ("signal_speed_policy", "classes", "STANDARD", "all_valid_signals_alerted"),
                False,
            ),
            "signals-standard-alert-disabled",
        ),
        _case(
            ("set", ("signal_speed_policy", "classes", "STANDARD", "longer_expiry"), False),
            "signals-standard-longer-expiry-disabled",
        ),
        _case(
            (
                "set",
                ("signal_speed_policy", "classes", "STANDARD", "human_check_and_order_expected"),
                False,
            ),
            "signals-standard-human-check-disabled",
        ),
        _case(
            (
                "set",
                (
                    "signal_speed_policy",
                    "classes",
                    "STANDARD",
                    "accepted_signal_execution_expected",
                ),
                False,
            ),
            "signals-standard-accepted-execution-disabled",
        ),
        _case(
            (
                "remove_value",
                ("signal_speed_policy", "required_patterns"),
                "LIQUIDITY_SWEEP_RECLAIM_FAST",
            ),
            "signals-pattern-deleted",
        ),
        _case(
            (
                "replace_value",
                ("signal_speed_policy", "required_patterns"),
                ("LIQUIDITY_SWEEP_RECLAIM_FAST", "HOSTILE_PATTERN"),
            ),
            "signals-pattern-replaced",
        ),
        _case(
            ("append", ("signal_speed_policy", "required_patterns"), "HOSTILE_PATTERN"),
            "signals-pattern-added",
        ),
        _case(
            ("remove_value", ("signal_speed_policy", "lifecycle"), "PREPARE"),
            "signals-lifecycle-stage-deleted",
        ),
        _case(
            ("swap", ("signal_speed_policy", "lifecycle"), (0, 1)), "signals-lifecycle-reordered"
        ),
        _case(
            (
                "remove_value",
                ("strategy_lifecycle", "manifest_required_fields"),
                "strategy_version",
            ),
            "strategy-manifest-field-deleted",
        ),
        _case(
            (
                "replace_value",
                ("strategy_lifecycle", "manifest_required_fields"),
                ("strategy_version", "strategy_name"),
            ),
            "strategy-manifest-field-renamed",
        ),
        _case(
            ("swap", ("strategy_lifecycle", "promotion_pipeline"), (1, 2)),
            "strategy-promotion-pipeline-reordered",
        ),
        _case(
            ("remove_value", ("strategy_lifecycle", "promotion_pipeline"), "INDEPENDENT_REVIEW"),
            "strategy-independent-review-deleted",
        ),
        _case(
            ("set", ("strategy_lifecycle", "disable_policy", "delete_history"), True),
            "strategy-disabled-history-deletable",
        ),
        _case(
            ("set", ("strategy_lifecycle", "disable_policy", "delete_records"), True),
            "strategy-disabled-version-explanation-deletable",
        ),
        _case(
            ("set", ("strategy_lifecycle", "disable_policy", "delete_replay_capability"), True),
            "strategy-disabled-replay-deletable",
        ),
        _case(
            ("append", ("strategy_lifecycle", "first_release"), "COMPLEX_DYNAMIC_HOT_LOADING"),
            "strategy-complex-hot-loading-enabled",
        ),
        _case(
            (
                "remove_value",
                ("strategy_lifecycle", "deferred_strategies"),
                "AUTOMATIC_REGIME_ROUTER",
            ),
            "strategy-deferred-route-item-deleted",
        ),
        _case(
            ("set", ("data_product_lifecycle", "strategy_raw_exchange_json_dependency"), "ALLOWED"),
            "data-raw-exchange-json-allowed",
        ),
        _case(
            ("remove_value", ("data_product_lifecycle", "pipeline"), "VALIDATION"),
            "data-pipeline-stage-deleted",
        ),
        _case(("swap", ("data_product_lifecycle", "pipeline"), (2, 3)), "data-pipeline-reordered"),
        _case(
            (
                "remove_value",
                ("data_product_lifecycle", "manifest_required_fields"),
                "replay_format",
            ),
            "data-manifest-field-deleted",
        ),
        _case(
            ("set", ("data_product_lifecycle", "strategy_dependency_declaration_required"), False),
            "data-dependency-declaration-disabled",
        ),
        _case(
            ("set", ("data_product_lifecycle", "new_data_auto_affects_existing_strategy"), True),
            "data-new-product-auto-affects-old-strategy",
        ),
        _case(
            (
                "remove_value",
                ("data_product_lifecycle", "decommission_gates"),
                "HISTORICAL_DECODER_RETAINED",
            ),
            "data-historical-decoder-gate-deleted",
        ),
        _case(
            ("remove_value", ("data_product_lifecycle", "decommission_gates"), "REPLAY_RETAINED"),
            "data-replay-gate-deleted",
        ),
        _case(
            (
                "remove_value",
                ("data_product_lifecycle", "decommission_gates"),
                "MIGRATION_COMPLETED",
            ),
            "data-migration-gate-deleted",
        ),
        _case(
            ("set", ("data_product_lifecycle", "first_release_scope"), "ALL_DATA_PRODUCTS"),
            "data-r0-scope-expanded",
        ),
        _case(
            ("set", ("learning_loop", "online_learning"), "ALLOWED"),
            "learning-online-learning-allowed",
        ),
        _case(
            ("set", ("learning_loop", "automatic_production_rule_mutation"), "ALLOWED"),
            "learning-automatic-production-mutation-allowed",
        ),
        _case(
            ("remove_value", ("learning_loop", "pipeline"), "DEVIATION_ANALYSIS"),
            "learning-pipeline-stage-deleted",
        ),
        _case(("swap", ("learning_loop", "pipeline"), (5, 6)), "learning-pipeline-reordered"),
        _case(
            ("remove_value", ("learning_loop", "metrics"), "MATCHING_CONFIDENCE"),
            "learning-measurement-deleted",
        ),
        _case(
            ("remove_value", ("learning_loop", "issue_categories"), "RISK"),
            "learning-category-deleted",
        ),
        _case(
            ("append", ("learning_loop", "issue_categories"), "UNAUTHORIZED_CATEGORY"),
            "learning-category-added",
        ),
        _case(("append", ("learning_loop", "severity_levels"), "P4"), "learning-severity-added"),
        _case(
            ("remove_value", ("learning_loop", "improvement_pipeline"), "REPLAY"),
            "learning-improvement-stage-deleted",
        ),
        _case(
            ("swap", ("learning_loop", "improvement_pipeline"), (3, 4)),
            "learning-improvement-pipeline-reordered",
        ),
        _case(("set", ("first_release", "primary_asset"), "BTC"), "release-r0-asset-changed"),
        _case(
            ("set", ("first_release", "active_strategy_count"), 2),
            "release-r0-strategy-count-changed",
        ),
        _case(
            ("set", ("first_release", "active_strategy"), "HOSTILE-v1"),
            "release-r0-strategy-changed",
        ),
        _case(
            ("set", ("first_release", "execution_mode"), "AUTOMATED"),
            "release-r0-manual-execution-changed",
        ),
        _case(
            ("set", ("first_release", "ai_role"), "TRADING_AUTHORITY"), "release-r0-ai-role-changed"
        ),
        _case(
            ("set", ("first_release", "automatic_exchange_write"), "ALLOWED"),
            "release-r0-exchange-write-enabled",
        ),
        _case(
            ("set", ("first_release", "all_valid_signals_visible"), False),
            "release-r0-all-signal-visibility-disabled",
        ),
        _case(("set", ("releases", "R0", "scope"), "FL4"), "release-r0-vertical-scope-changed"),
        _case(
            ("set", ("releases", "R0", "execution"), "AUTOMATED"), "release-r0-manual-only-disabled"
        ),
        _case(
            ("set", ("releases", "R1", "autonomous_entry"), "ALLOWED"),
            "release-r1-autonomous-entry-allowed",
        ),
        _case(
            ("set", ("releases", "R1", "human_confirmation_required"), False),
            "release-r1-human-confirmation-disabled",
        ),
        _case(
            ("set", ("governance_levels", "flp1_minimum"), "G0"),
            "governance-flp1-minimum-lowered-g0",
        ),
        _case(
            ("set", ("governance_levels", "flp1_minimum"), "G1"),
            "governance-flp1-minimum-lowered-g1",
        ),
        _case(
            ("remove_key", ("governance_levels", "fl4_requirement"), None),
            "governance-fl4-execution-security-review-deleted",
        ),
        _case(
            (
                "remove_value",
                ("development_route", "pre_launch_main_prs"),
                "V0-FLP1-DECISION-TO-OUTCOME-OPERATOR-ASSIST-PILOT",
            ),
            "route-two-pr-plan-deleted",
        ),
        _case(
            ("set", ("development_route", "flp1_is_vertical_pilot_pr"), False),
            "route-vertical-pilot-disabled",
        ),
        _case(
            (
                "set",
                ("development_route", "full_independent_review_only_for_final_merge_candidate"),
                False,
            ),
            "route-final-independent-review-disabled",
        ),
        _case(
            ("set", ("development_route", "only_blocker_prevents_merge"), False),
            "route-only-blocker-prevents-merge-disabled",
        ),
        _case(
            ("set", ("review_finalization_policy", "review_permission"), "BOUNDED_WRITE"),
            "finalization-reviewer-permission-changed",
        ),
        _case(
            ("set", ("review_finalization_policy", "exact_head_ci_required"), False),
            "finalization-exact-head-ci-disabled",
        ),
        _case(
            ("set", ("review_finalization_policy", "mark_ready_prohibited"), False),
            "finalization-mark-ready-prohibition-disabled",
        ),
        _case(
            ("set", ("review_finalization_policy", "merge_prohibited"), False),
            "finalization-merge-prohibition-disabled",
        ),
        _case(
            (
                "add_property",
                ("review_finalization_policy",),
                ("separate_project_control_authorization_required", False),
            ),
            "finalization-separate-authorization-bypass-added",
        ),
        _case(
            ("set", ("recursive_rotation", "required"), False),
            "rotation-recursive-required-disabled",
        ),
        _case(
            ("remove_value", ("recursive_rotation", "handoff_required_fields"), "STOP_CONDITIONS"),
            "rotation-handoff-field-deleted",
        ),
        _case(
            ("set", ("recursive_rotation", "post_merge_next_gate"), "V0-FLP1-IMPLEMENTATION"),
            "rotation-next-gate-replaced",
        ),
        _case(
            ("remove_key", ("recursive_rotation", "verification_warning"), None),
            "rotation-verification-warning-deleted",
        ),
        _case(
            ("remove_value", ("deferred_capabilities",), "AUTONOMOUS_ENTRY"),
            "deferred-autonomous-entry-deleted",
        ),
        _case(
            ("remove_value", ("deferred_capabilities",), "ONLINE_LEARNING"),
            "deferred-online-learning-deleted",
        ),
        _case(
            ("remove_value", ("deferred_capabilities",), "AUTOMATIC_PRODUCTION_PARAMETER_MUTATION"),
            "deferred-automatic-mutation-deleted",
        ),
        _case(
            ("remove_value", ("deferred_capabilities",), "MULTI_STRATEGY_PRODUCTION_ROUTING"),
            "deferred-multi-strategy-routing-deleted",
        ),
        _case(
            ("remove_value", ("deferred_capabilities",), "MULTI_ASSET_PRODUCTION_ROUTING"),
            "deferred-multi-asset-routing-deleted",
        ),
    ]
    for severity in ("P0", "P1", "P2", "P3"):
        cases.append(
            _case(
                ("remove_value", ("learning_loop", "severity_levels"), severity),
                f"learning-severity-{severity.lower()}-deleted",
            )
        )
    for control in R1_REQUIRED_CONTROLS:
        cases.append(
            _case(
                ("remove_value", ("releases", "R1", "required_controls"), control),
                f"release-r1-control-{control.lower().replace('_', '-')}-deleted",
            )
        )
    for field in R2_FINALIZATION_FIELDS:
        case_name = field.removesuffix("_required").replace("_", "-")
        cases.extend(
            (
                _case(
                    ("remove_key", ("review_finalization_policy", field), None),
                    f"r2-finalization-{case_name}-deleted",
                ),
                _case(
                    ("set", ("review_finalization_policy", field), False),
                    f"r2-finalization-{case_name}-false",
                ),
            )
        )
    for field in R2_REPAIR_ROUTE_FIELDS:
        case_name = field.removesuffix("_required").replace("_", "-")
        cases.extend(
            (
                _case(
                    ("remove_key", ("development_route", field), None),
                    f"r2-route-{case_name}-deleted",
                ),
                _case(
                    ("set", ("development_route", field), False),
                    f"r2-route-{case_name}-false",
                ),
            )
        )
    for trigger in R2_ROTATION_TRIGGERS:
        cases.append(
            _case(
                ("remove_value", ("recursive_rotation", "rotation_triggers"), trigger),
                f"r2-rotation-trigger-{trigger.lower().replace('_', '-')}-deleted",
            )
        )
    cases.extend(
        (
            _case(
                (
                    "replace_value",
                    ("recursive_rotation", "rotation_triggers"),
                    ("HEAD_DRIFT", "UNAUTHORIZED_TRIGGER"),
                ),
                "r2-rotation-trigger-replaced",
            ),
            _case(
                ("append", ("recursive_rotation", "rotation_triggers"), "UNAUTHORIZED_TRIGGER"),
                "r2-rotation-trigger-added",
            ),
            _case(
                ("swap", ("recursive_rotation", "rotation_triggers"), (0, 1)),
                "r2-rotation-triggers-reordered",
            ),
            _case(
                ("set", ("recursive_rotation", "rotation_triggers"), ["PR_MERGED"]),
                "r2-rotation-triggers-replaced-with-short-open-list",
            ),
        )
    )
    for output_field in R2_REQUIRED_ROTATION_OUTPUT:
        cases.append(
            _case(
                (
                    "remove_value",
                    ("recursive_rotation", "required_rotation_output"),
                    output_field,
                ),
                f"r2-rotation-output-{output_field.lower().replace('_', '-')}-deleted",
            )
        )
    cases.extend(
        (
            _case(
                (
                    "replace_value",
                    ("recursive_rotation", "required_rotation_output"),
                    ("REASON", "UNAUTHORIZED_OUTPUT"),
                ),
                "r2-rotation-output-replaced",
            ),
            _case(
                (
                    "append",
                    ("recursive_rotation", "required_rotation_output"),
                    "UNAUTHORIZED_OUTPUT",
                ),
                "r2-rotation-output-added",
            ),
            _case(
                ("swap", ("recursive_rotation", "required_rotation_output"), (0, 1)),
                "r2-rotation-output-reordered",
            ),
        )
    )
    for field in R2_ROTATION_FLAGS:
        case_name = field.removesuffix("_required").replace("_", "-")
        cases.extend(
            (
                _case(
                    ("remove_key", ("recursive_rotation", field), None),
                    f"r2-rotation-{case_name}-deleted",
                ),
                _case(
                    ("set", ("recursive_rotation", field), False),
                    f"r2-rotation-{case_name}-false",
                ),
            )
        )
    cases.append(
        _case(
            ("remove_key", ("recursive_rotation", "recursive_window_rotation_requirement"), None),
            "r2-recursive-requirement-object-deleted",
        )
    )
    for field in R2_RECURSIVE_REQUIREMENT_FIELDS:
        case_name = field.replace("_", "-")
        path = ("recursive_rotation", "recursive_window_rotation_requirement", field)
        cases.extend(
            (
                _case(("remove_key", path, None), f"r2-recursive-{case_name}-deleted"),
                _case(("set", path, False), f"r2-recursive-{case_name}-false"),
            )
        )
    cases.extend(
        (
            _case(
                (
                    "add_property",
                    ("recursive_rotation", "recursive_window_rotation_requirement"),
                    ("unexpected_authority", True),
                ),
                "r2-recursive-unexpected-property-added",
            ),
            _case(
                (
                    "set",
                    ("recursive_rotation", "recursive_window_rotation_requirement"),
                    "Future handoffs should probably propagate this policy.",
                ),
                "r2-recursive-object-replaced-with-prose",
            ),
            _case(
                (
                    "set",
                    (
                        "recursive_rotation",
                        "recursive_window_rotation_requirement",
                        "one_time_summary_or_non_propagating_simplification_prohibited",
                    ),
                    False,
                ),
                "r2-recursive-one-time-summary-allowed",
            ),
        )
    )
    closed_objects = {
        "root": (),
        "authority": ("authority",),
        "first-release": ("first_release",),
        "signal-policy": ("signal_speed_policy",),
        "signal-classes": ("signal_speed_policy", "classes"),
        "signal-fast": ("signal_speed_policy", "classes", "FAST"),
        "signal-standard": ("signal_speed_policy", "classes", "STANDARD"),
        "strategy": ("strategy_lifecycle",),
        "strategy-disable-policy": ("strategy_lifecycle", "disable_policy"),
        "data-product": ("data_product_lifecycle",),
        "learning-loop": ("learning_loop",),
        "milestones": ("capability_milestones",),
        "releases": ("releases",),
        "release-r0": ("releases", "R0"),
        "release-r1": ("releases", "R1"),
        "governance": ("governance_levels",),
        "development-route": ("development_route",),
        "finalization": ("review_finalization_policy",),
        "rotation": ("recursive_rotation",),
        "recursive-requirement": (
            "recursive_rotation",
            "recursive_window_rotation_requirement",
        ),
    }
    for name, object_path in closed_objects.items():
        cases.append(
            _case(
                ("add_property", object_path, ("unexpected_authority", True)),
                f"closed-object-{name}-rejects-unexpected-property",
            )
        )
    return cases


def _descend(document: Any, path: tuple[str | int, ...]) -> Any:
    current = document
    for part in path:
        current = current[part]
    return current


def _apply_mutation(document: dict[str, Any], mutation: Mutation) -> None:
    operation, path, value = mutation
    if operation == "set":
        parent = _descend(document, path[:-1])
        parent[path[-1]] = value
    elif operation == "remove_key":
        parent = _descend(document, path[:-1])
        del parent[path[-1]]
    elif operation == "remove_value":
        target = _descend(document, path)
        target.remove(value)
    elif operation == "replace_value":
        target = _descend(document, path)
        old, new = value
        target[target.index(old)] = new
    elif operation == "append":
        target = _descend(document, path)
        target.append(value)
    elif operation == "swap":
        target = _descend(document, path)
        left, right = value
        target[left], target[right] = target[right], target[left]
    elif operation == "add_property":
        target = _descend(document, path)
        key, added = value
        target[key] = added
    else:  # pragma: no cover - mutation table is static
        raise AssertionError(f"unknown mutation operation: {operation}")


def _expected_validation_path(mutation: Mutation) -> tuple[str | int, ...]:
    operation, path, _ = mutation
    if operation == "remove_key":
        return path[:-1]
    return path


@pytest.mark.parametrize("mutation", _program_mutation_cases())
def test_schema_rejects_hostile_program_mutation(mutation: Mutation) -> None:
    schema = _load_json(SCHEMA_PATH)
    hostile = copy.deepcopy(_load_json(PROGRAM_PATH))
    _apply_mutation(hostile, mutation)

    with pytest.raises(jsonschema.ValidationError) as exc_info:
        Draft202012Validator(schema).validate(hostile)

    expected_path = _expected_validation_path(mutation)
    actual_path = tuple(exc_info.value.absolute_path)
    assert actual_path[: len(expected_path)] == expected_path


@pytest.mark.parametrize(
    ("object_path", "case_id"),
    (
        ((), "root"),
        (("active_write_lease",), "active-write-lease"),
    ),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_project_state_schema_rejects_unexpected_properties(
    object_path: tuple[str, ...],
    case_id: str,
) -> None:
    del case_id
    schema = _load_json(SCHEMA_PATH)["$defs"]["ProjectState"]
    hostile = copy.deepcopy(_load_json(STATE_PATH))
    target = _descend(hostile, object_path)
    target["unexpected_authority"] = True

    with pytest.raises(jsonschema.ValidationError):
        Draft202012Validator(schema).validate(hostile)


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
