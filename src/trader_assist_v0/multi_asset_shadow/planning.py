"""Frozen R1/R1.1 public-only Shadow plan arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum
from itertools import pairwise

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
    # This is one machine-contract value in R1/R1.1.  Keep invalid and stale
    # detail in logs/evidence, not in a second incompatible decision value.
    BBO_INVALID_OR_STALE = "BBO_INVALID_OR_STALE"
    LIQUIDITY_HARD_LIMIT = "LIQUIDITY_HARD_LIMIT"
    CHASE_LIMIT_EXCEEDED = "CHASE_LIMIT_EXCEEDED"
    TARGET_FEASIBILITY_FAILED = "TARGET_FEASIBILITY_FAILED"


class PlanningError(ValueError):
    pass


@dataclass(frozen=True)
class PublicBbo:
    best_bid: Decimal
    best_ask: Decimal
    age_seconds: Decimal = Decimal("0")
    observed_at_ms: int = 0
    market_id: str = ""
    coin: str = ""

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

    version: str
    fee_bps_per_side: Decimal
    slippage_bps_per_side: Decimal
    stress_slippage_bps_per_side: Decimal

    def __post_init__(self) -> None:
        if not self.version or any(
            value < 0
            for value in (
                self.fee_bps_per_side,
                self.slippage_bps_per_side,
                self.stress_slippage_bps_per_side,
            )
        ):
            raise PlanningError("cost configuration is invalid")


@dataclass(frozen=True)
class LiquidityAssessment:
    """Immutable on-demand L2 evidence for the $1,000 hard gate.

    The configured 2 bps is intentionally absent: it is a planning cost
    assumption, while this is an observed book-execution result.
    """

    market_id: str
    coin: str
    side: Side
    observed_at_ms: int
    best_bid: Decimal
    best_ask: Decimal
    reference_notional_usd: Decimal
    depth_consumed: tuple[tuple[Decimal, Decimal], ...]
    executable_price: Decimal | None
    one_way_slippage_bps: Decimal | None
    sufficient_depth: bool
    provenance_hash: str

    def fresh_for(
        self, *, market_id: str, coin: str, side: Side, now_ms: int, max_age_ms: int = 10_000
    ) -> bool:
        return (
            self.market_id == market_id
            and self.coin == coin
            and self.side is side
            and self.reference_notional_usd == PRIMARY_REFERENCE_NOTIONAL_USD
            and self.sufficient_depth
            and self.executable_price is not None
            and self.one_way_slippage_bps is not None
            and 0 <= now_ms - self.observed_at_ms <= max_age_ms
        )


@dataclass(frozen=True)
class PlanInputs:
    market_id: str
    side: Side
    ideal_entry_low: Decimal
    ideal_entry_high: Decimal
    chase_limit: Decimal
    structural_stop: Decimal
    structural_target: Decimal
    liquidity: LiquidityAssessment | None
    cost_model: CostModel | None
    now_ms: int
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


def minimum_tick(price: Decimal, *, max_decimals: int, significant_figures: int = 5) -> Decimal:
    """Return the provider's smallest legal increment at this price magnitude."""
    if price <= 0 or not price.is_finite():
        raise PlanningError("price precision input is invalid")
    if max_decimals < 0 or significant_figures <= 0:
        raise PlanningError("price precision input is invalid")
    # Hyperliquid's five-significant-figure limit does not remove the legal
    # integer price exception.  At a legal integral price the next minimum
    # increment is one, including high BTC-like prices.
    if price == price.to_integral_value():
        return Decimal(1)
    decimal_quantum = Decimal(1).scaleb(-max_decimals)
    significant_quantum = Decimal(1).scaleb(price.adjusted() - significant_figures + 1)
    return max(decimal_quantum, significant_quantum)


def assess_l2(
    *,
    market_id: str,
    coin: str,
    side: Side,
    observed_at_ms: int,
    best_bid: Decimal,
    best_ask: Decimal,
    levels: tuple[tuple[Decimal, Decimal], ...],
    provenance_hash: str,
) -> LiquidityAssessment:
    """Consume provider levels to exactly the frozen $1,000 quote reference."""
    if best_bid <= 0 or best_ask <= best_bid or observed_at_ms < 0:
        raise PlanningError("invalid BBO")
    if not market_id or not coin or not provenance_hash:
        raise PlanningError("L2 identity is invalid")
    if any(
        not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0
        for price, size in levels
    ):
        raise PlanningError("L2 levels are invalid")
    if side is Side.LONG and (
        any(price < best_ask for price, _ in levels)
        or any(right[0] < left[0] for left, right in pairwise(levels))
    ):
        raise PlanningError("L2 ask levels are not ordered outward")
    if side is Side.SHORT and (
        any(price > best_bid for price, _ in levels)
        or any(right[0] > left[0] for left, right in pairwise(levels))
    ):
        raise PlanningError("L2 bid levels are not ordered outward")
    usable = levels
    remaining = PRIMARY_REFERENCE_NOTIONAL_USD
    quote = Decimal()
    base = Decimal()
    consumed: list[tuple[Decimal, Decimal]] = []
    for price, size in usable:
        available = price * size
        take = min(available, remaining)
        if take <= 0:
            continue
        quantity = take / price
        quote += take
        base += quantity
        consumed.append((price, quantity))
        remaining -= take
        if remaining == 0:
            break
    if remaining > 0 or base == 0:
        return LiquidityAssessment(
            market_id,
            coin,
            side,
            observed_at_ms,
            best_bid,
            best_ask,
            PRIMARY_REFERENCE_NOTIONAL_USD,
            tuple(consumed),
            None,
            None,
            False,
            provenance_hash,
        )
    vwap = quote / base
    touch = best_ask if side is Side.LONG else best_bid
    directional = (vwap - touch) if side is Side.LONG else (touch - vwap)
    if directional < 0:
        raise PlanningError("L2 VWAP direction is impossible")
    slippage = directional / touch * Decimal("10000")
    return LiquidityAssessment(
        market_id,
        coin,
        side,
        observed_at_ms,
        best_bid,
        best_ask,
        PRIMARY_REFERENCE_NOTIONAL_USD,
        tuple(consumed),
        vwap,
        slippage,
        True,
        provenance_hash,
    )


def make_plan(inputs: PlanInputs, bbo: PublicBbo) -> PlanDraft | PlanRejection:
    if inputs.liquidity is None:
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    if bbo.market_id != inputs.market_id or bbo.coin != inputs.liquidity.coin:
        return PlanRejection.BBO_INVALID_OR_STALE
    if not (0 <= inputs.now_ms - bbo.observed_at_ms <= 10_000):
        return PlanRejection.BBO_INVALID_OR_STALE
    try:
        spread_bps = bbo.spread_bps
    except PlanningError:
        return PlanRejection.BBO_INVALID_OR_STALE
    if inputs.cost_model is None:
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    if not inputs.liquidity.fresh_for(
        market_id=inputs.market_id,
        coin=bbo.coin,
        side=inputs.side,
        now_ms=inputs.now_ms,
    ):
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    if (
        inputs.liquidity.best_bid != bbo.best_bid
        or inputs.liquidity.best_ask != bbo.best_ask
        or inputs.liquidity.observed_at_ms != bbo.observed_at_ms
    ):
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    if (
        spread_bps > HARD_MAX_SPREAD_BPS
        or inputs.liquidity.one_way_slippage_bps is None
        or inputs.liquidity.one_way_slippage_bps > HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS
    ):
        return PlanRejection.LIQUIDITY_HARD_LIMIT
    touch = bbo.best_ask if inputs.side is Side.LONG else bbo.best_bid
    entry = round_provider_perp_price(
        touch,
        max_decimals=inputs.price_max_decimals,
        significant_figures=inputs.price_max_significant_figures,
    )
    # ROUND_DOWN would improve a long price.  Do not invent a better fill;
    # display the observed legal provider touch when that happens.
    if inputs.side is Side.LONG and entry < touch:
        entry = touch
    if inputs.side is Side.SHORT and entry > touch:
        entry = touch
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
