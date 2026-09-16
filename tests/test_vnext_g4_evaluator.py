from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.vnext_g4.contracts import (
    AttemptPolicy,
    EntryActivation,
    ExitPolicy,
    ParticipationState,
    ReentryPolicy,
    VNextCandidateConfig,
    VNextFeatureSnapshot,
    WinnerConfirmation,
)
from trader_assist_v0.vnext_g4.evaluator import evaluate_vnext


SOURCE = "a" * 64


def candidate(**updates: object) -> VNextCandidateConfig:
    values: dict[str, object] = {
        "candidate_id": "candidate-g4-eval",
        "entry_activation": EntryActivation.EA1_DIRECT_REACCEL_PRICE,
        "attempt_policy": AttemptPolicy.AP1_FIXED_BPS,
        "reentry_policy": ReentryPolicy.R1_ONE_FRESH_CAUSAL_ACTIVATION,
        "winner_confirmation": WinnerConfirmation.WC0_PROGRESS,
        "exit_policy": ExitPolicy.X1_STRUCTURAL_FULL_EXIT,
        "room_to_cost_hurdle": 3,
        "fixed_stop_bps": 8,
        "rv_multiplier": None,
        "no_followthrough_seconds": None,
        "winner_progress_bps": 5,
        "winner_persistence_seconds": None,
        "giveback_numerator": None,
        "giveback_denominator": None,
    }
    values.update(updates)
    return VNextCandidateConfig.create(**values)


def feature(c: VNextCandidateConfig, **updates: object) -> VNextFeatureSnapshot:
    values: dict[str, object] = {
        "market_id": sha256_hex(b"market"),
        "expression_id": "expr-001",
        "package_id": "pkg-001",
        "candidate_hash": c.candidate_hash,
        "source_e4_manifest_hash": SOURCE,
        "admission_ordinal": 10,
        "decision_ts": 1000,
        "side": "LONG",
        "structural_setup_confirmed": True,
        "thesis_valid": True,
        "data_evaluable": True,
        "bbo_state_valid": True,
        "predecision_window_complete": True,
        "ea1_direct_reaccel": True,
        "ea2_retest_reaccel": False,
        "flow_imbalance_side_adjusted": Decimal("0.2"),
        "flow_price_response_bps": Decimal("1"),
        "remaining_room_bps": Decimal("10"),
        "all_in_friction_bps": Decimal("2"),
        "intended_notional": Decimal("100"),
        "top_level_notional": Decimal("1000"),
        "attempt_number": 1,
        "adverse_progress_bps": Decimal("1"),
        "micro_rv_60s_bps": Decimal("8"),
        "elapsed_attempt_seconds": 10,
        "no_followthrough_state": False,
        "fresh_reentry_activation": False,
        "favorable_progress_bps": Decimal("5"),
        "favorable_persistence_seconds": 60,
        "fresh_favorable_structure": True,
        "structural_stop_reached": False,
        "structural_exit_reached": False,
        "fixed_r_exit_reached": False,
        "current_net_progress_bps": Decimal("5"),
        "net_mfe_bps": Decimal("5"),
    }
    values.update(updates)
    return VNextFeatureSnapshot.create(**values)


def test_ea3_requires_complete_microstructure_predecision_evidence() -> None:
    c = candidate(entry_activation=EntryActivation.EA3_SIMPLE_FLOW_PRICE_RESPONSE)
    result = evaluate_vnext(c, feature(c, predecision_window_complete=False))
    assert result.participation is ParticipationState.NOT_EVALUABLE
    assert "EA3_PREDECISION_60S_INCOMPLETE" in result.reason_codes
    assert result.order_intent == "NONE"


def test_soft_room_to_cost_failure_is_pass_not_hard_block() -> None:
    c = candidate(room_to_cost_hurdle=4)
    result = evaluate_vnext(c, feature(c, remaining_room_bps=Decimal("6")))
    assert result.participation is ParticipationState.PASS
    assert "ROOM_TO_COST_BELOW_POLICY" in result.reason_codes


def test_l1_capacity_failure_is_blocked_and_never_emits_order_intent() -> None:
    c = candidate()
    result = evaluate_vnext(
        c,
        feature(c, intended_notional=Decimal("2000"), top_level_notional=Decimal("1000")),
    )
    assert result.participation is ParticipationState.BLOCKED
    assert "UNSUPPORTED_L1_DEPTH" in result.reason_codes
    assert result.order_intent == "NONE"


def test_ap1_stop_and_fresh_reentry_are_thesis_scoped_and_attempt_bounded() -> None:
    c = candidate()
    first = evaluate_vnext(
        c,
        feature(
            c,
            adverse_progress_bps=Decimal("9"),
            fresh_reentry_activation=True,
            favorable_progress_bps=Decimal("0"),
        ),
    )
    assert first.stop_triggered is True
    assert first.can_reenter is True
    second = evaluate_vnext(
        c,
        feature(
            c,
            attempt_number=2,
            adverse_progress_bps=Decimal("9"),
            fresh_reentry_activation=True,
            favorable_progress_bps=Decimal("0"),
        ),
    )
    assert second.stop_triggered is True
    assert second.can_reenter is False


def test_ap4_fails_closed_instead_of_writer_inventing_combination_semantics() -> None:
    c = candidate(
        attempt_policy=AttemptPolicy.AP4_SIMPLE_PRICE_PLUS_TIME,
        fixed_stop_bps=8,
        no_followthrough_seconds=60,
    )
    result = evaluate_vnext(c, feature(c))
    assert result.participation is ParticipationState.NOT_EVALUABLE
    assert "AP4_COMBINATION_SEMANTIC_NOT_FROZEN" in result.reason_codes


def test_wc3_uses_exact_positive_flow_and_price_response_sign_rule() -> None:
    c = candidate(winner_confirmation=WinnerConfirmation.WC3_PROGRESS_FLOW_RESPONSE)
    accepted = evaluate_vnext(c, feature(c))
    assert accepted.winner_confirmed is True
    rejected = evaluate_vnext(c, feature(c, flow_price_response_bps=Decimal("0")))
    assert rejected.winner_confirmed is False


def test_x2_giveback_uses_only_frozen_fraction_grid() -> None:
    c = candidate(
        exit_policy=ExitPolicy.X2_MFE_GIVEBACK,
        giveback_numerator=1,
        giveback_denominator=2,
    )
    result = evaluate_vnext(
        c,
        feature(
            c,
            net_mfe_bps=Decimal("10"),
            current_net_progress_bps=Decimal("4"),
        ),
    )
    assert result.winner_confirmed is True
    assert result.exit_triggered is True
