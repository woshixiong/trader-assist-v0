"""Frozen R1/R1.1 public-only Shadow plan arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum

STRATEGY_VERSION = "FL-MA-PRICE-ACTION-v0.1"
PARAMETER_VERSION = "2026-08-03-r1"
HARD_MAX_SPREAD_BPS = Decimal("40")
HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS = Decimal("35")
PRIMARY_REFERENCE_NOTIONAL_USD = Decimal("1000")  # L2 hard-gate reference only.
REFERENCE_SHADOW_EQUITY_USD = Decimal("200")
REFERENCE_MAX_NOTIONAL_USD = Decimal("5000")


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
    BBO_INVALID = "BBO_INVALID"
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
class CostModel:
    """Versioned cost authority; no account-specific fee state is involved."""

    version: str = "2026-08-03-r1"
    fee_bps_per_side: Decimal = Decimal("4.5")
    slippage_bps_per_side: Decimal = Decimal("2.0")
    stress_slippage_bps_per_side: Decimal = Decimal("5.0")


@dataclass(frozen=True)
class PlanInputs:
    side: Side
    ideal_entry_low: Decimal
    ideal_entry_high: Decimal
    chase_limit: Decimal
    structural_stop: Decimal
    structural_target: Decimal
    observed_primary_one_way_slippage_bps: Decimal = Decimal("0")
    cost_model: CostModel = CostModel()
    # Perp API legal-price authority: MAX_DECIMALS(6) - szDecimals,
    # constrained further by five significant figures (integer exception).
    price_max_decimals: int = 6
    price_max_significant_figures: int = 5
    size_decimals: int = 5
    max_leverage: Decimal | None = None


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
    reference_notional_1pct: Decimal
    reference_notional_2pct: Decimal
    reference_size_unavailable: bool
    reference_size_only: str = "YES"
    not_account_authoritative: str = "YES"
    cost_model_version: str = ""
    submission_status: str = "NOT_SUBMITTED"


def _round_down(value: Decimal, decimals: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_DOWN)


def round_provider_perp_price(
    value: Decimal, *, max_decimals: int, significant_figures: int = 5
) -> Decimal:
    """Round to current provider legal precision without inventing a static tick."""
    if not value.is_finite() or value <= 0 or max_decimals < 0 or significant_figures <= 0:
        raise PlanningError("price precision input is invalid")
    decimal_quantum = Decimal(1).scaleb(-max_decimals)
    decimal_limited = value.quantize(decimal_quantum, rounding=ROUND_DOWN)
    if decimal_limited == decimal_limited.to_integral_value():
        return decimal_limited
    significant_quantum = Decimal(1).scaleb(decimal_limited.adjusted() - significant_figures + 1)
    return decimal_limited.quantize(max(decimal_quantum, significant_quantum), rounding=ROUND_DOWN)


def make_plan(inputs: PlanInputs, bbo: PublicBbo) -> PlanDraft | PlanRejection:
    if bbo.age_seconds > Decimal("10"):
        return PlanRejection.BBO_STALE
    try:
        spread_bps = bbo.spread_bps
    except PlanningError:
        return PlanRejection.BBO_INVALID
    if spread_bps > HARD_MAX_SPREAD_BPS or (
        inputs.observed_primary_one_way_slippage_bps > HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS
    ):
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    entry = round_provider_perp_price(
        bbo.best_ask if inputs.side is Side.LONG else bbo.best_bid,
        max_decimals=inputs.price_max_decimals,
        significant_figures=inputs.price_max_significant_figures,
    )
    if inputs.side is Side.LONG:
        within_chase, stop_valid = entry <= inputs.chase_limit, inputs.structural_stop < entry
        tp1 = entry + (entry - inputs.structural_stop)
        tp2: Decimal | None = min(
            inputs.structural_target, entry + 2 * (entry - inputs.structural_stop)
        )
    else:
        within_chase, stop_valid = entry >= inputs.chase_limit, inputs.structural_stop > entry
        tp1 = entry - (inputs.structural_stop - entry)
        tp2 = max(inputs.structural_target, entry - 2 * (inputs.structural_stop - entry))
    if not within_chase:
        return PlanRejection.CHASE_LIMIT_EXCEEDED
    risk = abs(entry - inputs.structural_stop)
    if not stop_valid or risk <= 0:
        raise PlanningError("structural stop is invalid")
    side_cost_bps = inputs.cost_model.fee_bps_per_side + inputs.cost_model.slippage_bps_per_side
    target_cost = (entry + inputs.structural_target) * side_cost_bps / Decimal("10000")
    net_r = (abs(inputs.structural_target - entry) - target_cost) / risk
    if net_r < 1:
        return PlanRejection.TARGET_FEASIBILITY_FAILED
    quality = (
        EntryQuality.IDEAL
        if inputs.ideal_entry_low <= entry <= inputs.ideal_entry_high
        else EntryQuality.LATE_BUT_WITHIN_CHASE
    )
    if abs(inputs.structural_target - entry) / risk < Decimal("1.25"):
        tp2 = None
    loss_per_unit = (
        risk
        + entry * side_cost_bps / Decimal("10000")
        + inputs.structural_stop * side_cost_bps / Decimal("10000")
    )
    leverage_cap = (
        REFERENCE_MAX_NOTIONAL_USD
        if inputs.max_leverage is None
        else REFERENCE_SHADOW_EQUITY_USD * inputs.max_leverage
    )
    effective_max_notional = min(REFERENCE_MAX_NOTIONAL_USD, leverage_cap)

    def size(risk_budget: Decimal) -> Decimal:
        return _round_down(
            min(risk_budget / loss_per_unit, effective_max_notional / entry),
            inputs.size_decimals,
        )

    one = size(REFERENCE_SHADOW_EQUITY_USD * Decimal("0.01"))
    two = size(REFERENCE_SHADOW_EQUITY_USD * Decimal("0.02"))
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
        reference_notional_1pct=one * entry,
        reference_notional_2pct=two * entry,
        reference_size_unavailable=one == 0,
        cost_model_version=inputs.cost_model.version,
    )
