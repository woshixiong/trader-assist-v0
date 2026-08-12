"""Frozen R1/R1.1 plan arithmetic for NOT_SUBMITTED Shadow Orders.

This module is pure domain logic.  It cannot request a BBO, submit an order,
or access an account.  A runtime must separately supply a fresh public BBO and
then persist the returned plan as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

STRATEGY_VERSION = "FL-MA-PRICE-ACTION-v0.1"
PARAMETER_VERSION = "2026-08-03-r1"
HARD_MAX_SPREAD_BPS = Decimal("40")
HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS = Decimal("35")
PRIMARY_REFERENCE_NOTIONAL_USD = Decimal("1000")


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class SetupFamily(StrEnum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    RANGE_EDGE_REJECTION = "RANGE_EDGE_REJECTION"


class EntryQuality(StrEnum):
    IDEAL = "IDEAL"
    LATE_BUT_WITHIN_CHASE = "LATE_BUT_WITHIN_CHASE"


class PlanRejection(StrEnum):
    BBO_STALE = "BBO_STALE"
    LIQUIDITY_HARD_LIMIT = "LIQUIDITY_HARD_LIMIT"
    CHASE_LIMIT_EXCEEDED = "CHASE_LIMIT_EXCEEDED"
    TARGET_FEASIBILITY_FAILED = "TARGET_FEASIBILITY_FAILED"


class PlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PublicBbo:
    best_bid: Decimal
    best_ask: Decimal
    age_seconds: Decimal

    @property
    def spread_bps(self) -> Decimal:
        if self.best_bid <= 0 or self.best_ask <= self.best_bid:
            raise PlanningError("invalid BBO")
        return (
            (self.best_ask - self.best_bid)
            / ((self.best_ask + self.best_bid) / 2)
            * Decimal("10000")
        )


@dataclass(frozen=True)
class PlanInputs:
    side: Side
    ideal_entry_low: Decimal
    ideal_entry_high: Decimal
    chase_limit: Decimal
    structural_stop: Decimal
    structural_target: Decimal
    fee_bps_per_side: Decimal = Decimal("4.5")
    slippage_bps_per_side: Decimal = Decimal("2.0")
    size_decimals: int = 5
    max_leverage: int | None = None


@dataclass(frozen=True)
class PlanDraft:
    side: Side
    planned_entry: Decimal
    stop: Decimal
    tp1: Decimal
    tp2: Decimal | None
    risk_distance: Decimal
    net_r_to_target: Decimal
    entry_quality: EntryQuality
    reference_qty_1pct: Decimal
    reference_qty_2pct: Decimal
    reference_size_unavailable: bool
    submission_status: str = "NOT_SUBMITTED"


def _round_down(value: Decimal, decimals: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_DOWN)


def make_plan(inputs: PlanInputs, bbo: PublicBbo) -> PlanDraft | PlanRejection:
    if bbo.age_seconds > Decimal("10"):
        return PlanRejection.BBO_STALE
    if bbo.spread_bps > HARD_MAX_SPREAD_BPS:
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    if inputs.slippage_bps_per_side > HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS:
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    entry = bbo.best_ask if inputs.side is Side.LONG else bbo.best_bid
    if inputs.side is Side.LONG:
        within_chase = entry <= inputs.chase_limit
        stop_valid = inputs.structural_stop < entry
        tp1 = entry + (entry - inputs.structural_stop)
        tp2: Decimal | None = min(
            inputs.structural_target, entry + 2 * (entry - inputs.structural_stop)
        )
    else:
        within_chase = entry >= inputs.chase_limit
        stop_valid = inputs.structural_stop > entry
        tp1 = entry - (inputs.structural_stop - entry)
        tp2 = max(inputs.structural_target, entry - 2 * (inputs.structural_stop - entry))
    if not within_chase:
        return PlanRejection.CHASE_LIMIT_EXCEEDED
    risk = abs(entry - inputs.structural_stop)
    if not stop_valid or risk <= 0:
        raise PlanningError("structural stop is invalid")
    cost = (
        (entry + inputs.structural_target)
        * (inputs.fee_bps_per_side + inputs.slippage_bps_per_side)
        / Decimal("10000")
    )
    net_r = (abs(inputs.structural_target - entry) - cost) / risk
    if net_r < 1:
        return PlanRejection.TARGET_FEASIBILITY_FAILED
    quality = (
        EntryQuality.IDEAL
        if inputs.ideal_entry_low <= entry <= inputs.ideal_entry_high
        else EntryQuality.LATE_BUT_WITHIN_CHASE
    )
    gross_target_r = abs(inputs.structural_target - entry) / risk
    if gross_target_r < Decimal("1.25"):
        tp2 = None
    per_unit_loss = risk + entry * (
        inputs.fee_bps_per_side + inputs.slippage_bps_per_side
    ) / Decimal("10000")
    per_unit_loss += (
        inputs.structural_stop
        * (inputs.fee_bps_per_side + inputs.slippage_bps_per_side)
        / Decimal("10000")
    )
    leverage_cap = (
        PRIMARY_REFERENCE_NOTIONAL_USD
        if inputs.max_leverage is None
        else min(PRIMARY_REFERENCE_NOTIONAL_USD, Decimal("200") * inputs.max_leverage)
    )

    def size(risk_budget: Decimal) -> Decimal:
        return _round_down(
            min(risk_budget / per_unit_loss, leverage_cap / entry), inputs.size_decimals
        )

    one, two = size(Decimal("2")), size(Decimal("4"))
    return PlanDraft(
        side=inputs.side,
        planned_entry=entry,
        stop=inputs.structural_stop,
        tp1=tp1,
        tp2=tp2,
        risk_distance=risk,
        net_r_to_target=net_r,
        entry_quality=quality,
        reference_qty_1pct=one,
        reference_qty_2pct=two,
        reference_size_unavailable=one == 0,
    )
