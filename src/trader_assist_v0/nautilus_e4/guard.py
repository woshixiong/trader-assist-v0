"""Pure economic EntryExecutionGuard; this module has no execution imports."""

from __future__ import annotations

from decimal import Decimal

from .contracts import GuardDecision, GuardInputs, GuardResult


def evaluate_entry_guard(inputs: GuardInputs) -> GuardResult:
    """Return PASS or terminal NO_SUBMIT without performing any side effect."""
    reasons: list[str] = []
    if not inputs.data_evaluable:
        reasons.append("DATA_NOT_EVALUABLE")
    if not inputs.bbo_state_valid:
        reasons.append("BBO_STATE_INVALID")
    if inputs.intended_notional > inputs.top_level_notional:
        reasons.append("UNSUPPORTED_L1_DEPTH")
    friction = Decimal(inputs.all_in_friction_bps)
    if friction == 0:
        room_to_cost = Decimal("Infinity")
    else:
        room_to_cost = Decimal(inputs.remaining_room_bps) / friction
    if room_to_cost < Decimal(inputs.minimum_room_to_cost):
        reasons.append("ROOM_TO_COST_BELOW_POLICY")
    return GuardResult(
        decision=GuardDecision.NO_SUBMIT if reasons else GuardDecision.PASS,
        reason_codes=tuple(reasons),
        inputs=inputs,
    )
