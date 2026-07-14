from __future__ import annotations

# The frozen mathematical expressions and canonical plan construction are kept
# on single lines to make directional rounding relationships directly auditable.
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, Decimal
from enum import StrEnum
from statistics import median
from typing import Literal, Protocol

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import Candle, DataQualityState

STRATEGY_VERSION: Literal["ETH-LDAR-v0.1"] = "ETH-LDAR-v0.1"
CONFIGURATION_VERSION: Literal["1"] = "1"
TRADE_PLAN_VERSION: Literal["1"] = "1"
TRADE_PLAN_HASH_DOMAIN = "trader-assist-v0/first-launch/trade-plan/v1"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class SignalState(StrEnum):
    WAIT = "WAIT"
    WATCH = "WATCH"
    PREPARE = "PREPARE"
    TRIGGERED_FAST = "TRIGGERED_FAST"
    TRIGGERED_STANDARD = "TRIGGERED_STANDARD"
    EXPIRED = "EXPIRED"
    INVALIDATED = "INVALIDATED"
    TAKEN = "TAKEN"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"


class PlanError(ValueError):
    pass


@dataclass(frozen=True)
class Signal:
    state: SignalState
    side: Side | None
    speed: Literal["FAST", "STANDARD"] | None
    setup_id: str | None
    reason: str


class SetupFamily(StrEnum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"


@dataclass(frozen=True)
class PreparedSetup:
    setup_id: str
    family: SetupFamily
    side: Side
    boundary: Decimal
    atr: Decimal
    sweep_extreme: Decimal
    created_open_time_ms: int
    expires_after_open_time_ms: int


@dataclass(frozen=True)
class StrategyOutput:
    state: SignalState
    family: SetupFamily
    side: Side
    speed: Literal["FAST", "STANDARD"]
    setup_id: str
    trigger_open_time_ms: int
    entry_low: Decimal
    entry_high: Decimal
    chase_limit: Decimal
    stop: Decimal
    expires_at: datetime
    reason: str
    do_not_chase: Literal["DO NOT CHASE"] = "DO NOT CHASE"


def lifecycle_state(
    output: StrategyOutput,
    *,
    now: datetime,
    reference: Decimal,
    quality: DataQualityState,
    terminal: SignalState | None = None,
) -> SignalState:
    if terminal in {SignalState.TAKEN, SignalState.SKIPPED, SignalState.REJECTED}:
        return terminal
    if quality is not DataQualityState.READY:
        return SignalState.INVALIDATED
    if (output.side is Side.LONG and reference <= output.stop) or (
        output.side is Side.SHORT and reference >= output.stop
    ):
        return SignalState.INVALIDATED
    if now.astimezone(UTC) >= output.expires_at:
        return SignalState.EXPIRED
    return output.state


def strategy_output(
    setup: PreparedSetup,
    *,
    speed: Literal["FAST", "STANDARD"],
    trigger: Candle,
    retest_extreme: Decimal | None = None,
) -> StrategyOutput:
    long = setup.side is Side.LONG
    boundary, atr = setup.boundary, setup.atr
    if setup.family is SetupFamily.SWEEP_RECLAIM:
        low, high = (
            (
                (boundary, boundary + Decimal("0.15") * atr)
                if speed == "FAST"
                else (boundary - Decimal("0.05") * atr, boundary + Decimal("0.10") * atr)
            )
            if long
            else (
                (boundary - Decimal("0.15") * atr, boundary)
                if speed == "FAST"
                else (boundary - Decimal("0.10") * atr, boundary + Decimal("0.05") * atr)
            )
        )
        chase = (
            boundary + (Decimal("0.25") if speed == "FAST" else Decimal("0.20")) * atr
            if long
            else boundary - (Decimal("0.25") if speed == "FAST" else Decimal("0.20")) * atr
        )
        stop = (
            setup.sweep_extreme - Decimal("0.10") * atr
            if long
            else setup.sweep_extreme + Decimal("0.10") * atr
        )
    elif speed == "FAST":
        low, high = (
            (boundary + Decimal("0.10") * atr, boundary + Decimal("0.20") * atr)
            if long
            else (boundary - Decimal("0.20") * atr, boundary - Decimal("0.10") * atr)
        )
        chase, stop = (
            (boundary + Decimal("0.30") * atr, boundary - Decimal("0.25") * atr)
            if long
            else (boundary - Decimal("0.30") * atr, boundary + Decimal("0.25") * atr)
        )
    else:
        low, high = (
            (boundary - Decimal("0.05") * atr, boundary + Decimal("0.10") * atr)
            if long
            else (boundary - Decimal("0.10") * atr, boundary + Decimal("0.05") * atr)
        )
        chase = boundary + Decimal("0.20") * atr if long else boundary - Decimal("0.20") * atr
        extreme = setup.sweep_extreme if retest_extreme is None else retest_extreme
        stop = (
            min(boundary - Decimal("0.25") * atr, extreme - Decimal("0.05") * atr)
            if long
            else max(boundary + Decimal("0.25") * atr, extreme + Decimal("0.05") * atr)
        )
    return StrategyOutput(
        SignalState.TRIGGERED_FAST if speed == "FAST" else SignalState.TRIGGERED_STANDARD,
        setup.family,
        setup.side,
        speed,
        setup.setup_id,
        trigger.open_time_ms,
        low,
        high,
        chase,
        stop,
        trigger.evidence.received_at + timedelta(seconds=180 if speed == "FAST" else 900),
        "CONFIRMED",
    )


def advance_prepare(
    setup: PreparedSetup,
    candle: Candle,
    *,
    quality: DataQualityState,
    intervening_closes: tuple[Decimal, ...] = (),
    already_decided: bool = False,
) -> Signal | StrategyOutput:
    if quality is not DataQualityState.READY:
        return Signal(
            SignalState.INVALIDATED, setup.side, "STANDARD", setup.setup_id, "DATA_NOT_READY"
        )
    if already_decided:
        return Signal(
            SignalState.REJECTED, setup.side, "STANDARD", setup.setup_id, "SETUP_ALREADY_DECIDED"
        )
    if candle.open_time_ms > setup.expires_after_open_time_ms:
        return Signal(
            SignalState.EXPIRED, setup.side, "STANDARD", setup.setup_id, "PREPARE_WINDOW_EXPIRED"
        )
    if setup.family is SetupFamily.SWEEP_RECLAIM:
        if setup.side is Side.LONG:
            valid = (
                setup.boundary - Decimal("0.15") * setup.atr
                <= candle.low
                <= setup.boundary + Decimal("0.10") * setup.atr
                and candle.close >= setup.boundary + Decimal("0.05") * setup.atr
                and candle.low > setup.sweep_extreme
            )
            extreme = candle.low
        else:
            valid = (
                setup.boundary - Decimal("0.10") * setup.atr
                <= candle.high
                <= setup.boundary + Decimal("0.15") * setup.atr
                and candle.close <= setup.boundary - Decimal("0.05") * setup.atr
                and candle.high < setup.sweep_extreme
            )
            extreme = candle.high
    elif setup.side is Side.LONG:
        valid = (
            setup.boundary - Decimal("0.15") * setup.atr
            <= candle.low
            <= setup.boundary + Decimal("0.10") * setup.atr
            and candle.close >= setup.boundary + Decimal("0.05") * setup.atr
            and not any(
                value < setup.boundary - Decimal("0.20") * setup.atr for value in intervening_closes
            )
        )
        extreme = candle.low
    else:
        valid = (
            setup.boundary - Decimal("0.10") * setup.atr
            <= candle.high
            <= setup.boundary + Decimal("0.15") * setup.atr
            and candle.close <= setup.boundary - Decimal("0.05") * setup.atr
            and not any(
                value > setup.boundary + Decimal("0.20") * setup.atr for value in intervening_closes
            )
        )
        extreme = candle.high
    return (
        strategy_output(setup, speed="STANDARD", trigger=candle, retest_extreme=extreme)
        if valid
        else Signal(SignalState.PREPARE, setup.side, "STANDARD", setup.setup_id, "AWAITING_RETEST")
    )


def _features(
    candles_5m: tuple[Candle, ...], candles_15m: tuple[Candle, ...]
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool, bool]:
    if len(candles_5m) < 27 or len(candles_15m) < 11:
        raise PlanError("INSUFFICIENT_LOOKBACK")
    trigger = candles_5m[-1]
    if trigger.high == trigger.low:
        raise PlanError("ZERO_RANGE_TRIGGER")
    trs = [
        max(
            item.high - item.low,
            abs(item.high - candles_5m[index - 1].close),
            abs(item.low - candles_5m[index - 1].close),
        )
        for index, item in enumerate(candles_5m[-14:], start=len(candles_5m) - 14)
    ]
    atr = _mean(trs)
    prior = candles_5m[-13:-1]
    prior_high, prior_low = max(item.high for item in prior), min(item.low for item in prior)
    volume = median([item.volume for item in candles_5m[-21:-1]])
    closes = [item.close for item in candles_15m]
    sma_now, sma_old = _mean(closes[-8:]), _mean(closes[-11:-3])
    return (
        atr,
        prior_high,
        prior_low,
        volume,
        (trigger.close - trigger.low) / (trigger.high - trigger.low),
        closes[-1] > sma_now > sma_old,
        closes[-1] < sma_now < sma_old,
    )


def evaluate_signal(
    candles_5m: tuple[Candle, ...],
    candles_15m: tuple[Candle, ...],
    *,
    quality: DataQualityState,
    decided_setup_ids: frozenset[str] = frozenset(),
) -> Signal | PreparedSetup:
    if quality is not DataQualityState.READY:
        return Signal(SignalState.WAIT, None, None, None, f"DATA_{quality.value}")
    try:
        atr, high, low, med_volume, location, long_bias, short_bias = _features(
            candles_5m, candles_15m
        )
    except PlanError as exc:
        return Signal(SignalState.WAIT, None, None, None, str(exc))
    trigger = candles_5m[-1]
    body = abs(trigger.close - trigger.open)
    candidates: tuple[tuple[SetupFamily, Side, Decimal, Decimal, bool, bool], ...] = (
        (
            SetupFamily.SWEEP_RECLAIM,
            Side.LONG,
            low,
            trigger.low,
            trigger.low <= low - Decimal("0.10") * atr
            and trigger.close >= low
            and location >= Decimal("0.60")
            and not short_bias,
            trigger.volume >= Decimal("1.50") * med_volume
            and trigger.close - low >= Decimal("0.10") * atr,
        ),
        (
            SetupFamily.SWEEP_RECLAIM,
            Side.SHORT,
            high,
            trigger.high,
            trigger.high >= high + Decimal("0.10") * atr
            and trigger.close <= high
            and Decimal(1) - location >= Decimal("0.60")
            and not long_bias,
            trigger.volume >= Decimal("1.50") * med_volume
            and high - trigger.close >= Decimal("0.10") * atr,
        ),
        (
            SetupFamily.BREAKOUT_RETEST,
            Side.LONG,
            high,
            trigger.low,
            trigger.close >= high + Decimal("0.10") * atr
            and body >= Decimal("0.35") * atr
            and location >= Decimal("0.70")
            and trigger.volume >= Decimal("1.20") * med_volume
            and long_bias,
            body >= Decimal("0.50") * atr and trigger.volume >= Decimal("1.50") * med_volume,
        ),
        (
            SetupFamily.BREAKOUT_RETEST,
            Side.SHORT,
            low,
            trigger.high,
            trigger.close <= low - Decimal("0.10") * atr
            and body >= Decimal("0.35") * atr
            and Decimal(1) - location >= Decimal("0.70")
            and trigger.volume >= Decimal("1.20") * med_volume
            and short_bias,
            body >= Decimal("0.50") * atr and trigger.volume >= Decimal("1.50") * med_volume,
        ),
    )
    for family, side, boundary, extreme, matched, fast in candidates:
        if not matched:
            continue
        setup_id = _hash(
            [
                STRATEGY_VERSION,
                family.value,
                side.value,
                str(boundary),
                str(trigger.open_time_ms),
                CONFIGURATION_VERSION,
            ]
        )
        if setup_id in decided_setup_ids:
            return Signal(SignalState.WAIT, None, None, setup_id, "SETUP_ALREADY_DECIDED")
        if fast:
            return Signal(SignalState.TRIGGERED_FAST, side, "FAST", setup_id, family.value)
        return PreparedSetup(
            setup_id,
            family,
            side,
            boundary,
            atr,
            extreme,
            trigger.open_time_ms,
            trigger.open_time_ms + 3 * 300_000,
        )
    watch = Decimal("0.25") * atr
    reference = trigger.close
    if abs(reference - high) <= watch or abs(reference - low) <= watch:
        return Signal(SignalState.WATCH, None, None, None, "NEAR_PRIOR_RANGE_BOUNDARY")
    return Signal(SignalState.WAIT, None, None, None, "NO_ACTIONABLE_CLOSED_CANDLE")


def evaluate_closed_candles(
    candles_5m: tuple[Candle, ...],
    candles_15m: tuple[Candle, ...],
    *,
    quality: DataQualityState,
) -> Signal:
    """Closed-candle-only ETH-LDAR trigger classifier; never sizes or executes."""
    if quality is not DataQualityState.READY:
        return Signal(SignalState.WAIT, None, None, None, f"DATA_{quality.value}")
    candles = candles_5m
    if len(candles) < 27 or len(candles_15m) < 11:
        return Signal(SignalState.WAIT, None, None, None, "INSUFFICIENT_LOOKBACK")
    c5 = candles[-1]
    prior = candles[-13:-1]
    previous_close = candles[-2].close
    tr = [
        max(item.high - item.low, abs(item.high - previous_close), abs(item.low - previous_close))
        for item in candles[-14:]
    ]
    atr = _mean(tr)
    if atr <= 0 or c5.high == c5.low:
        return Signal(SignalState.WAIT, None, None, None, "ATR_OR_TRIGGER_INVALID")
    close15 = [item.close for item in candles_15m]
    sma_now = _mean(close15[-8:])
    sma_old = _mean(close15[-11:-3])
    high, low = max(item.high for item in prior), min(item.low for item in prior)
    volume = Decimal(str(median([item.volume for item in candles[-21:-1]])))
    location = (c5.close - c5.low) / (c5.high - c5.low)
    long_bias = close15[-1] > sma_now > sma_old
    short_bias = close15[-1] < sma_now < sma_old
    if (
        c5.low <= low - Decimal("0.10") * atr
        and c5.close >= low
        and location >= Decimal("0.60")
        and not short_bias
    ):
        fast = c5.volume >= Decimal("1.50") * volume and c5.close - low >= Decimal("0.10") * atr
        speed_long: Literal["FAST", "STANDARD"] = "FAST" if fast else "STANDARD"
        setup = _hash(
            [
                STRATEGY_VERSION,
                "SWEEP",
                "LONG",
                str(low),
                str(c5.open_time_ms),
                CONFIGURATION_VERSION,
            ]
        )
        return Signal(
            SignalState.TRIGGERED_FAST if fast else SignalState.PREPARE,
            Side.LONG,
            speed_long,
            setup,
            "SWEEP_RECLAIM",
        )
    if (
        c5.high >= high + Decimal("0.10") * atr
        and c5.close <= high
        and (Decimal(1) - location) >= Decimal("0.60")
        and not long_bias
    ):
        fast = c5.volume >= Decimal("1.50") * volume and high - c5.close >= Decimal("0.10") * atr
        speed_short: Literal["FAST", "STANDARD"] = "FAST" if fast else "STANDARD"
        setup = _hash(
            [
                STRATEGY_VERSION,
                "SWEEP",
                "SHORT",
                str(high),
                str(c5.open_time_ms),
                CONFIGURATION_VERSION,
            ]
        )
        return Signal(
            SignalState.TRIGGERED_FAST if fast else SignalState.PREPARE,
            Side.SHORT,
            speed_short,
            setup,
            "SWEEP_RECLAIM",
        )
    return Signal(SignalState.WAIT, None, None, None, "NO_ACTIONABLE_CLOSED_CANDLE")


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal()) / Decimal(len(values))


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _round_price(value: Decimal, sz_decimals: int, direction: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise PlanError("PRICE_PRECISION_INPUT_INVALID")
    if type(sz_decimals) is not int or isinstance(sz_decimals, bool) or not 0 <= sz_decimals <= 6:
        raise PlanError("SZ_DECIMALS_PRECISION_INVALID")
    if direction not in {"up", "down"}:
        raise PlanError("PRICE_ROUNDING_DIRECTION_INVALID")
    places = 6 - sz_decimals
    quantum = Decimal(1).scaleb(max(value.adjusted() - 4, -places))
    rounding = ROUND_CEILING if direction == "up" else ROUND_FLOOR
    return value.quantize(quantum, rounding=rounding)


def round_quantity(raw_quantity: Decimal, sz_decimals: int) -> Decimal:
    if type(raw_quantity) is not Decimal or not raw_quantity.is_finite() or raw_quantity <= 0:
        raise PlanError("QUANTITY_PRECISION_INPUT_INVALID")
    if type(sz_decimals) is not int or isinstance(sz_decimals, bool) or not 0 <= sz_decimals <= 18:
        raise PlanError("SZ_DECIMALS_QUANTITY_INVALID")
    quantity = raw_quantity.quantize(Decimal(1).scaleb(-sz_decimals), rounding=ROUND_DOWN)
    if quantity <= 0:
        raise PlanError("ZERO_QUANTITY_AFTER_PRECISION")
    return quantity


def inward_zone(low: Decimal, high: Decimal, sz_decimals: int) -> tuple[Decimal, Decimal]:
    rounded_low, rounded_high = (
        _round_price(low, sz_decimals, "up"),
        _round_price(high, sz_decimals, "down"),
    )
    if rounded_low > rounded_high:
        raise PlanError("ROUNDED_ENTRY_ZONE_EMPTY")
    return rounded_low, rounded_high


@dataclass(frozen=True)
class RiskResult:
    quantity: Decimal
    notional: Decimal
    risk_budget: Decimal
    planned_risk: Decimal


@dataclass(frozen=True)
class RawRiskMath:
    adverse_entry: Decimal
    adverse_stop: Decimal
    price_loss_per_unit: Decimal
    entry_fee_per_unit: Decimal
    exit_fee_per_unit: Decimal
    worst_case_loss_per_unit: Decimal
    risk_budget_usd: Decimal
    max_notional_usd: Decimal
    risk_limited_quantity_raw: Decimal
    notional_limited_quantity_raw: Decimal
    quantity_raw: Decimal


def risk_math(
    *, side: Side, planned_entry: Decimal, stop: Decimal, account_equity_usd: Decimal
) -> RawRiskMath:
    values = (planned_entry, stop, account_equity_usd)
    if any(type(value) is not Decimal or not value.is_finite() for value in values):
        raise PlanError("DECIMAL_AUTHORITY_REQUIRED")
    if account_equity_usd <= 0 or planned_entry <= 0 or stop <= 0:
        raise PlanError("POSITIVE_RISK_INPUT_REQUIRED")
    if (side is Side.LONG and planned_entry <= stop) or (
        side is Side.SHORT and planned_entry >= stop
    ):
        raise PlanError("SIDE_STOP_ORDER_INVALID")
    adverse_entry = planned_entry * (Decimal("1.0005") if side is Side.LONG else Decimal("0.9995"))
    adverse_stop = stop * (Decimal("0.9995") if side is Side.LONG else Decimal("1.0005"))
    price_loss = adverse_entry - adverse_stop if side is Side.LONG else adverse_stop - adverse_entry
    entry_fee, exit_fee = adverse_entry * Decimal("0.00045"), adverse_stop * Decimal("0.00045")
    loss = price_loss + entry_fee + exit_fee
    if price_loss <= 0 or loss <= 0:
        raise PlanError("NON_POSITIVE_WORST_CASE_LOSS")
    budget, maximum = account_equity_usd * Decimal("0.0025"), account_equity_usd
    risk_quantity, notional_quantity = budget / loss, maximum / abs(adverse_entry)
    quantity = min(risk_quantity, notional_quantity)
    if quantity <= 0:
        raise PlanError("NON_POSITIVE_RAW_QUANTITY")
    return RawRiskMath(
        adverse_entry,
        adverse_stop,
        price_loss,
        entry_fee,
        exit_fee,
        loss,
        budget,
        maximum,
        risk_quantity,
        notional_quantity,
        quantity,
    )


def size_plan(
    *, side: Side, entry: Decimal, stop: Decimal, equity: Decimal, sz_decimals: int
) -> RiskResult:
    if equity <= 0:
        raise PlanError("ACCOUNT_EQUITY_REQUIRED")
    worst_entry = entry * (Decimal("1.0005") if side is Side.LONG else Decimal("0.9995"))
    worst_stop = stop * (Decimal("0.9995") if side is Side.LONG else Decimal("1.0005"))
    distance = (worst_entry - worst_stop) if side is Side.LONG else (worst_stop - worst_entry)
    per_unit = (
        distance + abs(worst_entry) * Decimal("0.00045") + abs(worst_stop) * Decimal("0.00045")
    )
    if per_unit <= 0:
        raise PlanError("RISK_DISTANCE_INVALID")
    risk_budget = equity * Decimal("0.0025")
    raw = min(risk_budget / per_unit, equity / abs(worst_entry))
    quantity = raw.quantize(Decimal(1).scaleb(-sz_decimals), rounding=ROUND_DOWN)
    if quantity <= 0:
        raise PlanError("ZERO_QUANTITY_AFTER_PRECISION")
    planned_risk = quantity * per_unit
    if planned_risk > risk_budget:
        raise PlanError("RISK_BUDGET_EXCEEDED")
    return RiskResult(quantity, quantity * abs(worst_entry), risk_budget, planned_risk)


@dataclass(frozen=True)
class TradePlan:
    plan_id: str
    setup_id: str
    supersedes_plan_id: str | None
    created_at: datetime
    expires_at: datetime
    symbol: Literal["ETH"]
    side: Side
    speed: Literal["FAST", "STANDARD"]
    entry_low: Decimal
    entry_high: Decimal
    planned_entry: Decimal
    chase_limit: Decimal
    stop: Decimal
    tp1: Decimal
    tp2: Decimal
    quantity: Decimal
    notional: Decimal
    account_equity: Decimal
    risk_budget: Decimal
    planned_risk: Decimal
    sz_decimals: int
    canonical_hash: str
    trade_plan_version: Literal["1"] = TRADE_PLAN_VERSION
    strategy_version: Literal["ETH-LDAR-v0.1"] = STRATEGY_VERSION
    configuration_version: Literal["1"] = CONFIGURATION_VERSION
    do_not_chase: Literal["DO NOT CHASE"] = "DO NOT CHASE"

    def __post_init__(self) -> None:
        if (
            self.trade_plan_version != TRADE_PLAN_VERSION
            or self.strategy_version != STRATEGY_VERSION
            or self.configuration_version != CONFIGURATION_VERSION
            or self.symbol != "ETH"
            or self.do_not_chase != "DO NOT CHASE"
        ):
            raise PlanError("TRADE_PLAN_FIXED_AUTHORITY_INVALID")
        if type(self.side) is not Side or self.speed not in {"FAST", "STANDARD"}:
            raise PlanError("TRADE_PLAN_SIDE_OR_SPEED_INVALID")
        if type(self.sz_decimals) is not int:
            raise PlanError("TRADE_PLAN_SZ_DECIMALS_INVALID")
        _round_price(Decimal(1), self.sz_decimals, "up")
        required_identifiers = (self.setup_id, self.plan_id, self.canonical_hash)
        if any(
            type(identifier) is not str or re.fullmatch(r"[0-9a-f]{64}", identifier) is None
            for identifier in required_identifiers
        ) or (
            self.supersedes_plan_id is not None
            and (
                type(self.supersedes_plan_id) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.supersedes_plan_id) is None
            )
        ):
            raise PlanError("TRADE_PLAN_IDENTIFIER_INVALID")
        if self.plan_id != self.canonical_hash:
            raise PlanError("TRADE_PLAN_IDENTITY_MISMATCH")
        for timestamp in (self.created_at, self.expires_at):
            if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
                raise PlanError("TRADE_PLAN_TIMESTAMP_NOT_UTC")
        if self.expires_at != self.created_at + timedelta(
            seconds=180 if self.speed == "FAST" else 900
        ):
            raise PlanError("TRADE_PLAN_EXPIRY_INVALID")
        financials = (
            self.entry_low,
            self.entry_high,
            self.planned_entry,
            self.chase_limit,
            self.stop,
            self.tp1,
            self.tp2,
            self.quantity,
            self.notional,
            self.account_equity,
            self.risk_budget,
            self.planned_risk,
        )
        if any(
            type(value) is not Decimal or not value.is_finite() or value <= 0
            for value in financials
        ):
            raise PlanError("TRADE_PLAN_FINANCIAL_INVALID")
        if not self.entry_low <= self.planned_entry <= self.entry_high:
            raise PlanError("TRADE_PLAN_ENTRY_ZONE_INVALID")
        if self.planned_risk > self.risk_budget:
            raise PlanError("TRADE_PLAN_RISK_BUDGET_EXCEEDED")
        if self.side is Side.LONG:
            valid_structure = (
                self.stop < self.planned_entry <= self.chase_limit
                and self.planned_entry < self.tp1 < self.tp2
            )
        else:
            valid_structure = (
                self.chase_limit <= self.planned_entry < self.stop
                and self.tp2 < self.tp1 < self.planned_entry
            )
        if not valid_structure:
            raise PlanError("TRADE_PLAN_STRUCTURE_INVALID")
        expected_risk = size_plan(
            side=self.side,
            entry=self.planned_entry,
            stop=self.stop,
            equity=self.account_equity,
            sz_decimals=self.sz_decimals,
        )
        if (
            self.quantity,
            self.notional,
            self.risk_budget,
            self.planned_risk,
        ) != (
            expected_risk.quantity,
            expected_risk.notional,
            expected_risk.risk_budget,
            expected_risk.planned_risk,
        ):
            raise PlanError("TRADE_PLAN_RISK_INCONSISTENT")
        values = {
            field: getattr(self, field)
            for field in (
                "trade_plan_version",
                "strategy_version",
                "configuration_version",
                "setup_id",
                "supersedes_plan_id",
                "created_at",
                "expires_at",
                "symbol",
                "side",
                "speed",
                "entry_low",
                "entry_high",
                "planned_entry",
                "chase_limit",
                "stop",
                "tp1",
                "tp2",
                "quantity",
                "notional",
                "account_equity",
                "risk_budget",
                "planned_risk",
                "sz_decimals",
                "do_not_chase",
            )
        }
        if self.plan_id != _trade_plan_digest(
            _trade_plan_payload(
                values,
                created_at=self.created_at,
                expires_at=self.expires_at,
                side=self.side,
            )
        ):
            raise PlanError("TRADE_PLAN_HASH_INVALID")


def _trade_plan_payload(
    values: dict[str, object], *, created_at: datetime, expires_at: datetime, side: Side
) -> dict[str, object]:
    return {
        "trade_plan_version": values["trade_plan_version"],
        "strategy_version": values["strategy_version"],
        "configuration_version": values["configuration_version"],
        "setup_id": values["setup_id"],
        "supersedes_plan_id": values["supersedes_plan_id"],
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "symbol": values["symbol"],
        "side": side.value,
        "speed": values["speed"],
        "entry_low": values["entry_low"],
        "entry_high": values["entry_high"],
        "planned_entry": values["planned_entry"],
        "chase_limit": values["chase_limit"],
        "stop": values["stop"],
        "tp1": values["tp1"],
        "tp2": values["tp2"],
        "quantity": values["quantity"],
        "notional": values["notional"],
        "account_equity": values["account_equity"],
        "risk_budget": values["risk_budget"],
        "planned_risk": values["planned_risk"],
        "sz_decimals": values["sz_decimals"],
        "do_not_chase": values["do_not_chase"],
    }


def _trade_plan_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        TRADE_PLAN_HASH_DOMAIN.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def build_plan(
    *,
    setup_id: str,
    side: Side,
    speed: Literal["FAST", "STANDARD"],
    boundary: Decimal,
    atr: Decimal,
    sweep: Decimal,
    reference: Decimal,
    equity: Decimal,
    sz_decimals: int,
    created_at: datetime,
    supersedes_plan_id: str | None = None,
) -> TradePlan:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise PlanError("CREATED_AT_TIMEZONE_REQUIRED")
    if atr <= 0:
        raise PlanError("ATR_INVALID")
    long = side is Side.LONG
    if speed == "FAST":
        low, high = (
            (boundary, boundary + Decimal("0.15") * atr)
            if long
            else (boundary - Decimal("0.15") * atr, boundary)
        )
        chase, stop = (
            (boundary + Decimal("0.25") * atr, sweep - Decimal("0.10") * atr)
            if long
            else (boundary - Decimal("0.25") * atr, sweep + Decimal("0.10") * atr)
        )
    else:
        low, high = (
            (boundary - Decimal("0.05") * atr, boundary + Decimal("0.10") * atr)
            if long
            else (boundary - Decimal("0.10") * atr, boundary + Decimal("0.05") * atr)
        )
        chase, stop = (
            (boundary + Decimal("0.20") * atr, sweep - Decimal("0.10") * atr)
            if long
            else (boundary - Decimal("0.20") * atr, sweep + Decimal("0.10") * atr)
        )
    low = _round_price(low, sz_decimals, "up")
    high = _round_price(high, sz_decimals, "down")
    if low > high:
        raise PlanError("ROUNDED_ENTRY_ZONE_EMPTY")
    if (long and reference > chase) or (not long and reference < chase):
        raise PlanError("CHASE_LIMIT_EXCEEDED")
    entry = min(max(reference, low), high)
    entry = _round_price(entry, sz_decimals, "up" if long else "down")
    stop = _round_price(stop, sz_decimals, "down" if long else "up")
    distance = abs(entry - stop)
    if distance < Decimal("0.10") * atr or distance > Decimal("1.50") * atr:
        raise PlanError("STOP_DISTANCE_OUT_OF_RANGE")
    risk = size_plan(side=side, entry=entry, stop=stop, equity=equity, sz_decimals=sz_decimals)
    r = abs(entry - stop)
    tp1 = _round_price(entry + r if long else entry - r, sz_decimals, "down" if long else "up")
    tp2 = _round_price(
        entry + 2 * r if long else entry - 2 * r, sz_decimals, "down" if long else "up"
    )
    normalized_created_at = created_at.astimezone(UTC)
    expiry = normalized_created_at + timedelta(seconds=180 if speed == "FAST" else 900)
    values: dict[str, object] = {
        "setup_id": setup_id,
        "supersedes_plan_id": supersedes_plan_id,
        "created_at": normalized_created_at,
        "expires_at": expiry,
        "symbol": "ETH",
        "side": side,
        "speed": speed,
        "entry_low": low,
        "entry_high": high,
        "planned_entry": entry,
        "chase_limit": _round_price(chase, sz_decimals, "down" if long else "up"),
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "quantity": risk.quantity,
        "notional": risk.notional,
        "account_equity": equity,
        "risk_budget": risk.risk_budget,
        "planned_risk": risk.planned_risk,
        "sz_decimals": sz_decimals,
        "trade_plan_version": TRADE_PLAN_VERSION,
        "strategy_version": STRATEGY_VERSION,
        "configuration_version": CONFIGURATION_VERSION,
        "do_not_chase": "DO NOT CHASE",
    }
    digest = _trade_plan_digest(
        _trade_plan_payload(
            values,
            created_at=normalized_created_at,
            expires_at=expiry,
            side=side,
        )
    )
    return TradePlan(plan_id=digest, canonical_hash=digest, **values)  # type: ignore[arg-type]


@dataclass(frozen=True)
class AIExplanation:
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    missing_or_conflicting_inputs: tuple[str, ...]
    risk_and_expiry_warnings: tuple[str, ...]
    execution_checklist: tuple[str, ...]
    status: Literal["AVAILABLE", "UNAVAILABLE"]


class AIProvider(Protocol):
    def explain(self, summary: dict[str, str]) -> AIExplanation: ...


def fallback_explanation(plan: TradePlan, quality: DataQualityState) -> AIExplanation:
    return AIExplanation(
        (f"Deterministic {plan.side.value} {plan.speed} plan",),
        (),
        (() if quality is DataQualityState.READY else (quality.value,)),
        ("DO NOT CHASE", f"Expires {plan.expires_at.isoformat()}"),
        ("Verify manual order details", "Record TAKEN, SKIPPED, or REJECTED"),
        "AVAILABLE",
    )


def bounded_explanation(
    provider: AIProvider | None, plan: TradePlan, quality: DataQualityState
) -> AIExplanation:
    fallback = fallback_explanation(plan, quality)
    if provider is None:
        return fallback
    try:
        result = provider.explain(
            {"side": plan.side.value, "speed": plan.speed, "quality": quality.value}
        )
        fields = (
            result.supporting_evidence,
            result.opposing_evidence,
            result.missing_or_conflicting_inputs,
            result.risk_and_expiry_warnings,
            result.execution_checklist,
        )
        if result.status != "AVAILABLE" or any(
            len(values) > 8 or any(len(item) > 240 for item in values) for values in fields
        ):
            raise ValueError
        return result
    except Exception:
        return AIExplanation(
            fallback.supporting_evidence,
            fallback.opposing_evidence,
            fallback.missing_or_conflicting_inputs,
            fallback.risk_and_expiry_warnings,
            fallback.execution_checklist,
            "UNAVAILABLE",
        )
