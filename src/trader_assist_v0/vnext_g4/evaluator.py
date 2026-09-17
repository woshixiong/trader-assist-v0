"""Pure Ordinary VNext G4 policy semantics over already-admitted causal evidence."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import (
    CandidateConfig,
    Ea3Base,
    EntryActivation,
    ExitPolicy,
    ParticipationDecision,
    ReentryPolicy,
    WinnerConfirmation,
)


class EvaluationInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    formal_setup_confirmed: bool
    thesis_valid: bool
    bbo_state_valid: bool
    data_evaluable: bool
    restart_reference_crossed: bool
    retest_seen: bool
    microstructure_warmup_seconds: int = Field(ge=0)
    side_adjusted_aggressor_imbalance_15s: Decimal
    flow_price_response_15s_bps: Decimal
    remaining_structural_room_bps: Decimal = Field(gt=0)
    all_in_friction_bps: Decimal = Field(gt=0)
    economics_can_improve: bool


class DecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: ParticipationDecision
    activated: bool
    reason_codes: tuple[str, ...]
    room_to_cost_ratio: Decimal
    venue_submitted: Literal[False] = False


def _activation_state(
    candidate: CandidateConfig,
    inputs: EvaluationInputs,
) -> tuple[bool, str | None]:
    if not inputs.formal_setup_confirmed:
        return False, "FORMAL_SETUP_NOT_CONFIRMED"
    if candidate.entry_activation is EntryActivation.EA0:
        return True, None
    if candidate.entry_activation is EntryActivation.EA1:
        return inputs.restart_reference_crossed, "EA1_RESTART_REFERENCE_NOT_CROSSED"
    if candidate.entry_activation is EntryActivation.EA2:
        return (
            inputs.retest_seen and inputs.restart_reference_crossed,
            "EA2_RETEST_REACCEL_NOT_COMPLETE",
        )

    if inputs.microstructure_warmup_seconds < 60:
        return False, "EA3_MICROSTRUCTURE_WARMUP_INCOMPLETE"
    base_ready = inputs.restart_reference_crossed
    if candidate.ea3_base is Ea3Base.EA2:
        base_ready = base_ready and inputs.retest_seen
    if not base_ready:
        return False, "EA3_BASE_ACTIVATION_NOT_COMPLETE"
    if inputs.side_adjusted_aggressor_imbalance_15s <= 0:
        return False, "EA3_AGGRESSOR_FLOW_NOT_FAVORABLE"
    if inputs.flow_price_response_15s_bps <= 0:
        return False, "EA3_WEAK_RESPONSE_ABSORPTION_CANDIDATE"
    return True, None


def evaluate_participation(candidate: CandidateConfig, inputs: EvaluationInputs) -> DecisionResult:
    """Evaluate TAKE/WAIT/PASS without inventing a new directional Setup."""
    ratio = inputs.remaining_structural_room_bps / inputs.all_in_friction_bps
    if not inputs.thesis_valid:
        return DecisionResult(
            decision=ParticipationDecision.BLOCKED,
            activated=False,
            reason_codes=("THESIS_INVALID",),
            room_to_cost_ratio=ratio,
        )
    if not inputs.data_evaluable or not inputs.bbo_state_valid:
        return DecisionResult(
            decision=ParticipationDecision.BLOCKED,
            activated=False,
            reason_codes=("DATA_OR_BBO_NOT_EVALUABLE",),
            room_to_cost_ratio=ratio,
        )

    activated, reason = _activation_state(candidate, inputs)
    if not activated:
        if reason == "EA3_MICROSTRUCTURE_WARMUP_INCOMPLETE":
            return DecisionResult(
                decision=ParticipationDecision.NOT_EVALUABLE,
                activated=False,
                reason_codes=(reason,),
                room_to_cost_ratio=ratio,
            )
        return DecisionResult(
            decision=ParticipationDecision.WAIT,
            activated=False,
            reason_codes=((reason or "ACTIVATION_PENDING"),),
            room_to_cost_ratio=ratio,
        )

    if ratio < candidate.room_to_cost_k:
        decision = (
            ParticipationDecision.WAIT
            if inputs.economics_can_improve
            else ParticipationDecision.PASS
        )
        return DecisionResult(
            decision=decision,
            activated=True,
            reason_codes=("ROOM_TO_COST_BELOW_CANDIDATE_HURDLE",),
            room_to_cost_ratio=ratio,
        )
    return DecisionResult(
        decision=ParticipationDecision.TAKE,
        activated=True,
        reason_codes=("ACTIVATION_AND_ECONOMICS_PASS",),
        room_to_cost_ratio=ratio,
    )


def reentry_allowed(
    *,
    policy: ReentryPolicy,
    completed_attempts: int,
    thesis_valid: bool,
    fresh_activation_after_failure: bool,
) -> bool:
    if completed_attempts < 0:
        raise ValueError("completed_attempts cannot be negative")
    if not thesis_valid or completed_attempts >= 2:
        return False
    if policy is ReentryPolicy.NO_REENTRY_REFERENCE:
        return False
    if policy is ReentryPolicy.BLIND_IMMEDIATE_REENTRY_NEGATIVE_CONTROL:
        return completed_attempts == 1
    return completed_attempts == 1 and fresh_activation_after_failure


def winner_confirmed(
    *,
    candidate: CandidateConfig,
    favorable_progress_bps: Decimal,
    persistence_seconds: int,
    fresh_favorable_structure: bool,
    favorable_flow_price_response: bool,
) -> bool:
    if favorable_progress_bps < candidate.winner_progress_bps:
        return False
    mode = candidate.winner_confirmation
    if mode is WinnerConfirmation.WC0:
        return True
    if mode is WinnerConfirmation.WC1:
        assert candidate.persistence_seconds is not None
        return persistence_seconds >= candidate.persistence_seconds
    if mode is WinnerConfirmation.WC2:
        return fresh_favorable_structure
    return favorable_flow_price_response


def exit_triggered(
    *,
    candidate: CandidateConfig,
    fixed_r_reference_hit: bool,
    structural_deterioration: bool,
    giveback_ratio: Decimal,
    protective_stop_hit: bool,
    thesis_invalid: bool,
) -> bool:
    if giveback_ratio < 0:
        raise ValueError("giveback_ratio cannot be negative")
    if protective_stop_hit or thesis_invalid:
        return True
    mode = candidate.exit_policy
    if mode is ExitPolicy.X0:
        return fixed_r_reference_hit
    if mode is ExitPolicy.X1:
        return structural_deterioration
    assert candidate.giveback_ratio is not None
    giveback_hit = giveback_ratio >= candidate.giveback_ratio
    if mode is ExitPolicy.X2:
        return giveback_hit
    return structural_deterioration or giveback_hit
