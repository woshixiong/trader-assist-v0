"""Pure Ordinary VNext G4 policy evaluation over causal admitted feature state."""

from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.nautilus_e4.contracts import GuardInputs
from trader_assist_v0.nautilus_e4.guard import evaluate_entry_guard

from .contracts import (
    AttemptPolicy,
    EntryActivation,
    ExitPolicy,
    ParticipationState,
    ReentryPolicy,
    VNextCandidateConfig,
    VNextEvaluationRecord,
    VNextFeatureSnapshot,
    WinnerConfirmation,
)


def _flow_accepts(snapshot: VNextFeatureSnapshot) -> bool | None:
    if snapshot.flow_imbalance_side_adjusted is None or snapshot.flow_price_response_bps is None:
        return None
    return (
        Decimal(snapshot.flow_imbalance_side_adjusted) > 0
        and Decimal(snapshot.flow_price_response_bps) > 0
    )


def _activation(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
) -> tuple[bool, tuple[str, ...], bool]:
    """Return activation, reasons, not-evaluable."""
    if candidate.entry_activation is EntryActivation.EA0_FORMAL_TIME_CONTROL:
        return snapshot.structural_setup_confirmed, ("EA0_FORMAL_TIME_CONTROL",), False
    if candidate.entry_activation is EntryActivation.EA1_DIRECT_REACCEL_PRICE:
        return snapshot.ea1_direct_reaccel, ("EA1_DIRECT_REACCEL_PRICE",), False
    if candidate.entry_activation is EntryActivation.EA2_RETEST_REACCEL_PRICE:
        return snapshot.ea2_retest_reaccel, ("EA2_RETEST_REACCEL_PRICE",), False
    if not snapshot.predecision_window_complete:
        return False, ("EA3_PREDECISION_60S_INCOMPLETE",), True
    flow = _flow_accepts(snapshot)
    if flow is None:
        return False, ("EA3_FLOW_INPUT_MISSING",), True
    base_activation = snapshot.ea1_direct_reaccel or snapshot.ea2_retest_reaccel
    return base_activation and flow, ("EA3_SIMPLE_FLOW_PRICE_RESPONSE",), False


def _participation(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
    *,
    activation: bool,
) -> tuple[ParticipationState, tuple[str, ...]]:
    if not snapshot.thesis_valid:
        return ParticipationState.BLOCKED, ("THESIS_INVALID",)
    if not snapshot.data_evaluable:
        return ParticipationState.BLOCKED, ("DATA_NOT_EVALUABLE",)
    if not snapshot.bbo_state_valid:
        return ParticipationState.BLOCKED, ("BBO_STATE_INVALID",)
    if not activation:
        return ParticipationState.WAIT, ("WAIT_FOR_CAUSAL_ACTIVATION",)

    guard = evaluate_entry_guard(
        GuardInputs(
            spread_bps=Decimal("0"),
            all_in_friction_bps=snapshot.all_in_friction_bps,
            remaining_room_bps=snapshot.remaining_room_bps,
            minimum_room_to_cost=Decimal(candidate.room_to_cost_hurdle),
            bbo_state_valid=snapshot.bbo_state_valid,
            data_evaluable=snapshot.data_evaluable,
            intended_notional=snapshot.intended_notional,
            top_level_notional=snapshot.top_level_notional,
            guard_config_version=f"vnext-g4-k{candidate.room_to_cost_hurdle}",
        )
    )
    if guard.decision.value == "PASS":
        return ParticipationState.TAKE, ("ENTRY_GUARD_PASS",)

    hard = tuple(
        reason
        for reason in guard.reason_codes
        if reason
        in {
            "DATA_NOT_EVALUABLE",
            "BBO_STATE_INVALID",
            "UNSUPPORTED_L1_DEPTH",
        }
    )
    if hard:
        return ParticipationState.BLOCKED, hard
    if "ROOM_TO_COST_BELOW_POLICY" in guard.reason_codes:
        return ParticipationState.PASS, ("ROOM_TO_COST_BELOW_POLICY",)
    return ParticipationState.BLOCKED, tuple(guard.reason_codes)


def _stop_trigger(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
) -> tuple[bool, tuple[str, ...], bool]:
    policy = candidate.attempt_policy
    if policy is AttemptPolicy.AP0_STRUCTURAL_REFERENCE:
        return snapshot.structural_stop_reached, ("AP0_STRUCTURAL_REFERENCE",), False
    if policy is AttemptPolicy.AP1_FIXED_BPS:
        assert candidate.fixed_stop_bps is not None
        return (
            Decimal(snapshot.adverse_progress_bps) >= Decimal(candidate.fixed_stop_bps),
            ("AP1_FIXED_BPS",),
            False,
        )
    if policy is AttemptPolicy.AP2_VOL_NORMALIZED:
        if snapshot.micro_rv_60s_bps is None:
            return False, ("AP2_MICRO_RV_MISSING",), True
        assert candidate.rv_multiplier is not None
        raw = Decimal(candidate.rv_multiplier) * Decimal(snapshot.micro_rv_60s_bps)
        threshold = min(Decimal("20"), max(Decimal("4"), raw))
        return (
            Decimal(snapshot.adverse_progress_bps) >= threshold,
            ("AP2_VOL_NORMALIZED", f"AP2_THRESHOLD_BPS={threshold}"),
            False,
        )
    if policy is AttemptPolicy.AP3_TIME_NO_FOLLOWTHROUGH:
        if snapshot.no_followthrough_state is None:
            return False, ("AP3_NO_FOLLOWTHROUGH_STATE_MISSING",), True
        assert candidate.no_followthrough_seconds is not None
        return (
            snapshot.elapsed_attempt_seconds >= candidate.no_followthrough_seconds
            and snapshot.no_followthrough_state,
            ("AP3_TIME_NO_FOLLOWTHROUGH",),
            False,
        )
    return False, ("AP4_COMBINATION_SEMANTIC_NOT_FROZEN",), True


def _winner_confirmed(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
) -> tuple[bool, tuple[str, ...], bool]:
    progress = Decimal(snapshot.favorable_progress_bps) >= Decimal(
        candidate.winner_progress_bps
    )
    policy = candidate.winner_confirmation
    if policy is WinnerConfirmation.WC0_PROGRESS:
        return progress, ("WC0_PROGRESS",), False
    if policy is WinnerConfirmation.WC1_PROGRESS_PERSISTENCE:
        assert candidate.winner_persistence_seconds is not None
        return (
            progress
            and snapshot.favorable_persistence_seconds
            >= candidate.winner_persistence_seconds,
            ("WC1_PROGRESS_PERSISTENCE",),
            False,
        )
    if policy is WinnerConfirmation.WC2_PROGRESS_FRESH_STRUCTURE:
        return (
            progress and snapshot.fresh_favorable_structure,
            ("WC2_PROGRESS_FRESH_STRUCTURE",),
            False,
        )
    flow = _flow_accepts(snapshot)
    if flow is None:
        return False, ("WC3_FLOW_INPUT_MISSING",), True
    return progress and flow, ("WC3_PROGRESS_FLOW_RESPONSE",), False


def _giveback_exit(candidate: VNextCandidateConfig, snapshot: VNextFeatureSnapshot) -> bool:
    assert candidate.giveback_numerator is not None
    assert candidate.giveback_denominator is not None
    mfe = Decimal(snapshot.net_mfe_bps)
    if mfe <= 0:
        return False
    current = Decimal(snapshot.current_net_progress_bps)
    giveback = mfe - current
    ratio = giveback / mfe
    threshold = Decimal(candidate.giveback_numerator) / Decimal(candidate.giveback_denominator)
    return ratio >= threshold


def _exit_trigger(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
    *,
    winner_confirmed: bool,
) -> tuple[bool, tuple[str, ...], bool]:
    if not snapshot.thesis_valid:
        return True, ("THESIS_INVALIDATION_EXIT",), False
    policy = candidate.exit_policy
    if policy is ExitPolicy.X0_FIXED_R_CONTROL:
        if snapshot.fixed_r_exit_reached is None:
            return False, ("X0_FIXED_R_REFERENCE_MISSING",), True
        return snapshot.fixed_r_exit_reached, ("X0_FIXED_R_CONTROL",), False
    if policy is ExitPolicy.X1_STRUCTURAL_FULL_EXIT:
        return (
            winner_confirmed and snapshot.structural_exit_reached,
            ("X1_STRUCTURAL_FULL_EXIT",),
            False,
        )
    if policy is ExitPolicy.X2_MFE_GIVEBACK:
        return (
            winner_confirmed and _giveback_exit(candidate, snapshot),
            ("X2_MFE_GIVEBACK",),
            False,
        )
    return (
        winner_confirmed
        and (snapshot.structural_exit_reached or _giveback_exit(candidate, snapshot)),
        ("X3_STRUCTURAL_RATCHET_GIVEBACK",),
        False,
    )


def evaluate_vnext(
    candidate: VNextCandidateConfig,
    snapshot: VNextFeatureSnapshot,
) -> VNextEvaluationRecord:
    """Evaluate one immutable candidate without transport, account, or order side effects."""
    if snapshot.candidate_hash != candidate.candidate_hash:
        raise ValueError("feature snapshot candidate identity mismatch")

    activation, activation_reasons, activation_ne = _activation(candidate, snapshot)
    if activation_ne:
        return VNextEvaluationRecord.create(
            package_id=snapshot.package_id,
            candidate_hash=candidate.candidate_hash,
            feature_hash=snapshot.feature_hash,
            participation=ParticipationState.NOT_EVALUABLE,
            activation=False,
            stop_triggered=False,
            winner_confirmed=False,
            exit_triggered=False,
            can_reenter=False,
            order_intent="NONE",
            reason_codes=activation_reasons,
        )

    participation, participation_reasons = _participation(
        candidate,
        snapshot,
        activation=activation,
    )
    if participation is not ParticipationState.TAKE:
        return VNextEvaluationRecord.create(
            package_id=snapshot.package_id,
            candidate_hash=candidate.candidate_hash,
            feature_hash=snapshot.feature_hash,
            participation=participation,
            activation=activation,
            stop_triggered=False,
            winner_confirmed=False,
            exit_triggered=not snapshot.thesis_valid,
            can_reenter=False,
            order_intent="NONE",
            reason_codes=(*activation_reasons, *participation_reasons),
        )

    stop, stop_reasons, stop_ne = _stop_trigger(candidate, snapshot)
    winner, winner_reasons, winner_ne = _winner_confirmed(candidate, snapshot)
    if stop_ne or winner_ne:
        reasons = (
            *activation_reasons,
            *participation_reasons,
            *stop_reasons,
            *winner_reasons,
        )
        return VNextEvaluationRecord.create(
            package_id=snapshot.package_id,
            candidate_hash=candidate.candidate_hash,
            feature_hash=snapshot.feature_hash,
            participation=ParticipationState.NOT_EVALUABLE,
            activation=activation,
            stop_triggered=False,
            winner_confirmed=False,
            exit_triggered=False,
            can_reenter=False,
            order_intent="NONE",
            reason_codes=reasons,
        )

    exit_triggered, exit_reasons, exit_ne = _exit_trigger(
        candidate,
        snapshot,
        winner_confirmed=winner,
    )
    if exit_ne:
        return VNextEvaluationRecord.create(
            package_id=snapshot.package_id,
            candidate_hash=candidate.candidate_hash,
            feature_hash=snapshot.feature_hash,
            participation=ParticipationState.NOT_EVALUABLE,
            activation=activation,
            stop_triggered=stop,
            winner_confirmed=winner,
            exit_triggered=False,
            can_reenter=False,
            order_intent="NONE",
            reason_codes=(
                *activation_reasons,
                *participation_reasons,
                *stop_reasons,
                *winner_reasons,
                *exit_reasons,
            ),
        )

    can_reenter = (
        stop
        and snapshot.attempt_number == 1
        and snapshot.thesis_valid
        and candidate.reentry_policy is ReentryPolicy.R1_ONE_FRESH_CAUSAL_ACTIVATION
        and snapshot.fresh_reentry_activation
    )
    if candidate.reentry_policy is ReentryPolicy.BLIND_IMMEDIATE_NEGATIVE_CONTROL:
        can_reenter = stop and snapshot.attempt_number == 1 and snapshot.thesis_valid

    return VNextEvaluationRecord.create(
        package_id=snapshot.package_id,
        candidate_hash=candidate.candidate_hash,
        feature_hash=snapshot.feature_hash,
        participation=ParticipationState.TAKE,
        activation=activation,
        stop_triggered=stop,
        winner_confirmed=winner,
        exit_triggered=exit_triggered or stop,
        can_reenter=can_reenter,
        order_intent="MARKETABLE_ENTRY",
        reason_codes=(
            *activation_reasons,
            *participation_reasons,
            *stop_reasons,
            *winner_reasons,
            *exit_reasons,
        ),
    )
