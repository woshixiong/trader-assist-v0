from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    Ea3Base,
    EntryActivation,
    ExitPolicy,
    ParticipationDecision,
    ReentryPolicy,
    WinnerConfirmation,
)
from trader_assist_v0.vnext_g4.evaluator import (
    EvaluationInputs,
    evaluate_participation,
    exit_triggered,
    reentry_allowed,
    winner_confirmed,
)


def candidate(**updates: object) -> CandidateConfig:
    values: dict[str, object] = {
        "entry_activation": EntryActivation.EA1,
        "attempt_stop": AttemptStop.AP0,
        "room_to_cost_k": Decimal("2"),
        "reentry_policy": ReentryPolicy.ONE_FRESH_CAUSAL_ACTIVATION_REENTRY,
        "winner_confirmation": WinnerConfirmation.WC0,
        "winner_progress_bps": Decimal("3"),
        "exit_policy": ExitPolicy.X1,
        "comparison_role": "CHALLENGER",
    }
    values.update(updates)
    return CandidateConfig.model_validate(values)


def inputs(**updates: object) -> EvaluationInputs:
    values: dict[str, object] = {
        "formal_setup_confirmed": True,
        "thesis_valid": True,
        "bbo_state_valid": True,
        "data_evaluable": True,
        "restart_reference_crossed": True,
        "retest_seen": False,
        "microstructure_warmup_seconds": 60,
        "side_adjusted_aggressor_imbalance_15s": Decimal("0.2"),
        "flow_price_response_15s_bps": Decimal("1"),
        "remaining_structural_room_bps": Decimal("10"),
        "all_in_friction_bps": Decimal("2"),
        "economics_can_improve": True,
    }
    values.update(updates)
    return EvaluationInputs.model_validate(values)


def test_ea3_requires_full_microstructure_warmup_without_fallback() -> None:
    config = candidate(entry_activation=EntryActivation.EA3, ea3_base=Ea3Base.EA1)
    result = evaluate_participation(config, inputs(microstructure_warmup_seconds=59))
    assert result.decision is ParticipationDecision.NOT_EVALUABLE
    assert result.activated is False
    assert "EA3_MICROSTRUCTURE_WARMUP_INCOMPLETE" in result.reason_codes


def test_ea3_sign_and_price_response_acceptance_can_take() -> None:
    config = candidate(entry_activation=EntryActivation.EA3, ea3_base=Ea3Base.EA1)
    result = evaluate_participation(config, inputs())
    assert result.decision is ParticipationDecision.TAKE
    assert result.activated is True
    weak = evaluate_participation(
        config,
        inputs(flow_price_response_15s_bps=Decimal("0")),
    )
    assert weak.decision is ParticipationDecision.WAIT
    assert "EA3_WEAK_RESPONSE_ABSORPTION_CANDIDATE" in weak.reason_codes


def test_room_to_cost_distinguishes_wait_from_pass_without_direction_change() -> None:
    config = candidate(room_to_cost_k=Decimal("4"))
    wait = evaluate_participation(
        config,
        inputs(remaining_structural_room_bps=Decimal("6"), economics_can_improve=True),
    )
    passed = evaluate_participation(
        config,
        inputs(remaining_structural_room_bps=Decimal("6"), economics_can_improve=False),
    )
    assert wait.decision is ParticipationDecision.WAIT
    assert passed.decision is ParticipationDecision.PASS


def test_one_fresh_reentry_only_and_attempt_three_plus_is_prohibited() -> None:
    policy = ReentryPolicy.ONE_FRESH_CAUSAL_ACTIVATION_REENTRY
    assert reentry_allowed(
        policy=policy,
        completed_attempts=1,
        thesis_valid=True,
        fresh_activation_after_failure=True,
    )
    assert not reentry_allowed(
        policy=policy,
        completed_attempts=1,
        thesis_valid=True,
        fresh_activation_after_failure=False,
    )
    assert not reentry_allowed(
        policy=policy,
        completed_attempts=2,
        thesis_valid=True,
        fresh_activation_after_failure=True,
    )


def test_winner_and_exit_families_remain_bounded() -> None:
    wc1 = candidate(
        winner_confirmation=WinnerConfirmation.WC1,
        winner_progress_bps=Decimal("5"),
        persistence_seconds=30,
    )
    assert winner_confirmed(
        candidate=wc1,
        favorable_progress_bps=Decimal("5"),
        persistence_seconds=30,
        fresh_favorable_structure=False,
        favorable_flow_price_response=False,
    )
    x3 = candidate(exit_policy=ExitPolicy.X3, giveback_ratio=Decimal("0.5"))
    assert exit_triggered(
        candidate=x3,
        fixed_r_reference_hit=False,
        structural_deterioration=False,
        giveback_ratio=Decimal("0.5"),
        protective_stop_hit=False,
        thesis_invalid=False,
    )
    assert exit_triggered(
        candidate=x3,
        fixed_r_reference_hit=False,
        structural_deterioration=False,
        giveback_ratio=Decimal("0"),
        protective_stop_hit=True,
        thesis_invalid=False,
    )
