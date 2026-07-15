from __future__ import annotations

import hashlib
import re
import weakref
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, Decimal, InvalidOperation
from enum import StrEnum
from statistics import median
from typing import Literal

from trader_assist_v0.contracts.common import canonical_json_bytes, decimal_to_canonical_string
from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    StrategySnapshot,
    _validated_strategy_snapshot,
)

STRATEGY_VERSION: Literal["ETH-LDAR-v0.1"] = "ETH-LDAR-v0.1"
CONFIGURATION_VERSION: Literal["1"] = "1"
TRADE_PLAN_VERSION: Literal["2"] = "2"
TRADE_PLAN_HASH_DOMAIN = "trader-assist-v0/first-launch/trade-plan/v2"


class PlanError(ValueError):
    pass


# Issuance is process-local and deliberately excluded from every strategy and
# TradePlan canonical payload.  It is a consumption guard, not decision data.
_ISSUED: dict[int, tuple[weakref.ReferenceType[object], str]] = {}


def _issue(value: object, fingerprint: str) -> object:
    key = id(value)

    def _release(reference: weakref.ReferenceType[object]) -> None:
        current = _ISSUED.get(key)
        if current is not None and current[0] is reference:
            del _ISSUED[key]

    _ISSUED[key] = (weakref.ref(value, _release), fingerprint)
    return value


def _is_issued(value: object, fingerprint: str) -> bool:
    issued = _ISSUED.get(id(value))
    return issued is not None and issued[0]() is value and issued[1] == fingerprint


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class SetupFamily(StrEnum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"


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


def _hash(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _utc(value: datetime, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise PlanError(error)
    return value.astimezone(UTC)


def _exact_utc(value: datetime, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise PlanError(error)
    return value


def _guard_decimal_exponent(value: Decimal, error: str) -> None:
    try:
        decimal_to_canonical_string(value)
    except (InvalidOperation, ValueError):
        raise PlanError(error) from None


def _candle_authority(candle: Candle) -> tuple[tuple[str, str, int], int, str]:
    return candle.identity, candle.open_time_ms, candle.canonical_hash


@dataclass(frozen=True)
class StrategyProvenance:
    family: SetupFamily
    side: Side
    boundary: Decimal
    atr: Decimal
    initial_extreme: Decimal
    setup_trigger_identity: tuple[str, str, int]
    setup_trigger_open_time_ms: int
    setup_trigger_canonical_hash: str

    def __post_init__(self) -> None:
        if type(self.family) is not SetupFamily or type(self.side) is not Side:
            raise PlanError("PROVENANCE_FAMILY_OR_SIDE_INVALID")
        if any(
            type(value) is not Decimal or not value.is_finite() or value <= 0
            for value in (self.boundary, self.atr, self.initial_extreme)
        ):
            raise PlanError("PROVENANCE_DECIMAL_INVALID")
        identity = self.setup_trigger_identity
        if (
            type(identity) is not tuple
            or len(identity) != 3
            or identity[0] != "ETH"
            or identity[1] != "5m"
            or type(identity[2]) is not int
            or identity[2] < 0
            or type(self.setup_trigger_open_time_ms) is not int
            or self.setup_trigger_open_time_ms < 0
            or identity[2] != self.setup_trigger_open_time_ms
            or type(self.setup_trigger_canonical_hash) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.setup_trigger_canonical_hash) is None
        ):
            raise PlanError("PROVENANCE_TRIGGER_INVALID")

    def payload(self) -> dict[str, object]:
        return {
            "family": self.family.value,
            "side": self.side.value,
            "boundary": self.boundary,
            "atr": self.atr,
            "initial_extreme": self.initial_extreme,
            "setup_trigger_identity": self.setup_trigger_identity,
            "setup_trigger_open_time_ms": self.setup_trigger_open_time_ms,
            "setup_trigger_canonical_hash": self.setup_trigger_canonical_hash,
        }

    @property
    def setup_id(self) -> str:
        return _hash(
            {
                "strategy_version": STRATEGY_VERSION,
                "configuration_version": CONFIGURATION_VERSION,
                "provenance": self.payload(),
            }
        )


@dataclass(frozen=True)
class Signal:
    state: SignalState
    side: Side | None
    speed: Literal["FAST", "STANDARD"] | None
    setup_id: str | None
    reason: str


@dataclass(frozen=True)
class PreparedSetup:
    provenance: StrategyProvenance
    expires_after_open_time_ms: int

    def __post_init__(self) -> None:
        if type(self.expires_after_open_time_ms) is not int or (
            self.expires_after_open_time_ms != self.provenance.setup_trigger_open_time_ms + 900_000
        ):
            raise PlanError("PREPARED_SETUP_EXPIRY_INVALID")

    @property
    def setup_id(self) -> str:
        return self.provenance.setup_id


def _geometry(
    provenance: StrategyProvenance, speed: Literal["FAST", "STANDARD"], material_extreme: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if type(material_extreme) is not Decimal or not material_extreme.is_finite():
        raise PlanError("MATERIAL_EXTREME_INVALID")
    boundary, atr, long = provenance.boundary, provenance.atr, provenance.side is Side.LONG
    if provenance.family is SetupFamily.SWEEP_RECLAIM:
        low, high = (
            (
                (boundary, boundary + Decimal(".15") * atr)
                if speed == "FAST"
                else (boundary - Decimal(".05") * atr, boundary + Decimal(".10") * atr)
            )
            if long
            else (
                (boundary - Decimal(".15") * atr, boundary)
                if speed == "FAST"
                else (boundary - Decimal(".10") * atr, boundary + Decimal(".05") * atr)
            )
        )
        chase = (
            boundary + (Decimal(".25") if speed == "FAST" else Decimal(".20")) * atr
            if long
            else boundary - (Decimal(".25") if speed == "FAST" else Decimal(".20")) * atr
        )
        stop = (
            provenance.initial_extreme - Decimal(".10") * atr
            if long
            else provenance.initial_extreme + Decimal(".10") * atr
        )
    elif speed == "FAST":
        low, high = (
            (boundary + Decimal(".10") * atr, boundary + Decimal(".20") * atr)
            if long
            else (boundary - Decimal(".20") * atr, boundary - Decimal(".10") * atr)
        )
        chase, stop = (
            (boundary + Decimal(".30") * atr, boundary - Decimal(".25") * atr)
            if long
            else (boundary - Decimal(".30") * atr, boundary + Decimal(".25") * atr)
        )
    else:
        low, high = (
            (boundary - Decimal(".05") * atr, boundary + Decimal(".10") * atr)
            if long
            else (boundary - Decimal(".10") * atr, boundary + Decimal(".05") * atr)
        )
        chase = boundary + Decimal(".20") * atr if long else boundary - Decimal(".20") * atr
        stop = (
            min(boundary - Decimal(".25") * atr, material_extreme - Decimal(".05") * atr)
            if long
            else max(boundary + Decimal(".25") * atr, material_extreme + Decimal(".05") * atr)
        )
    return low, high, chase, stop


@dataclass(frozen=True)
class StrategyOutput:
    provenance: StrategyProvenance
    setup_id: str
    speed: Literal["FAST", "STANDARD"]
    decision_trigger_identity: tuple[str, str, int]
    decision_trigger_open_time_ms: int
    decision_trigger_canonical_hash: str
    decision_trigger_received_at: datetime
    material_extreme: Decimal
    raw_entry_low: Decimal
    raw_entry_high: Decimal
    raw_chase_limit: Decimal
    raw_stop: Decimal
    created_at: datetime
    expires_at: datetime
    reason: Literal["CONFIRMED"] = "CONFIRMED"
    do_not_chase: Literal["DO NOT CHASE"] = "DO NOT CHASE"

    def __post_init__(self) -> None:
        if self.setup_id != self.provenance.setup_id or self.speed not in {"FAST", "STANDARD"}:
            raise PlanError("STRATEGY_OUTPUT_AUTHORITY_INVALID")
        identity = self.decision_trigger_identity
        if (
            type(identity) is not tuple
            or len(identity) != 3
            or identity[0] != "ETH"
            or identity[1] != "5m"
            or type(identity[2]) is not int
            or identity[2] < 0
            or type(self.decision_trigger_open_time_ms) is not int
            or self.decision_trigger_open_time_ms < 0
            or identity[2] != self.decision_trigger_open_time_ms
            or type(self.decision_trigger_canonical_hash) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.decision_trigger_canonical_hash) is None
        ):
            raise PlanError("STRATEGY_OUTPUT_TRIGGER_INVALID")
        received = _exact_utc(
            self.decision_trigger_received_at,
            "STRATEGY_TRIGGER_RECEIVED_AT_INVALID",
        )
        created = _exact_utc(self.created_at, "STRATEGY_CREATED_AT_INVALID")
        expiry = _exact_utc(self.expires_at, "STRATEGY_EXPIRES_AT_INVALID")
        if (
            created != received
            or expiry != created + timedelta(seconds=180 if self.speed == "FAST" else 900)
        ):
            raise PlanError("STRATEGY_OUTPUT_EXPIRY_INVALID")
        if self.reason != "CONFIRMED" or self.do_not_chase != "DO NOT CHASE":
            raise PlanError("STRATEGY_OUTPUT_FIXED_AUTHORITY_INVALID")
        if any(
            type(value) is not Decimal or not value.is_finite() or value <= 0
            for value in (
                self.material_extreme,
                self.raw_entry_low,
                self.raw_entry_high,
                self.raw_chase_limit,
                self.raw_stop,
            )
        ):
            raise PlanError("STRATEGY_OUTPUT_FINANCIAL_INVALID")
        expected = _geometry(self.provenance, self.speed, self.material_extreme)
        if (
            self.raw_entry_low,
            self.raw_entry_high,
            self.raw_chase_limit,
            self.raw_stop,
        ) != expected:
            raise PlanError("STRATEGY_OUTPUT_GEOMETRY_INVALID")
        if self.speed == "FAST":
            if self.material_extreme != self.provenance.initial_extreme:
                raise PlanError("STRATEGY_OUTPUT_GEOMETRY_INVALID")
            if (
                self.decision_trigger_identity != self.provenance.setup_trigger_identity
                or self.decision_trigger_open_time_ms != self.provenance.setup_trigger_open_time_ms
                or self.decision_trigger_canonical_hash
                != self.provenance.setup_trigger_canonical_hash
            ):
                raise PlanError("FAST_TRIGGER_AUTHORITY_INVALID")
        elif not (
            self.provenance.setup_trigger_open_time_ms
            < self.decision_trigger_open_time_ms
            <= self.provenance.setup_trigger_open_time_ms + 900_000
        ):
            raise PlanError("STANDARD_TRIGGER_AUTHORITY_INVALID")

    @property
    def family(self) -> SetupFamily:
        return self.provenance.family

    @property
    def side(self) -> Side:
        return self.provenance.side

    @property
    def state(self) -> SignalState:
        return (
            SignalState.TRIGGERED_FAST if self.speed == "FAST" else SignalState.TRIGGERED_STANDARD
        )


def _prepared_fingerprint(value: PreparedSetup) -> str:
    return _hash(
        {
            "provenance": value.provenance.payload(),
            "expires_after_open_time_ms": value.expires_after_open_time_ms,
        }
    )


def _output_fingerprint(value: StrategyOutput) -> str:
    return _hash(
        {
            "provenance": value.provenance.payload(),
            "setup_id": value.setup_id,
            "speed": value.speed,
            "decision_trigger_identity": value.decision_trigger_identity,
            "decision_trigger_open_time_ms": value.decision_trigger_open_time_ms,
            "decision_trigger_canonical_hash": value.decision_trigger_canonical_hash,
            "decision_trigger_received_at": value.decision_trigger_received_at,
            "material_extreme": value.material_extreme,
            "raw_entry_low": value.raw_entry_low,
            "raw_entry_high": value.raw_entry_high,
            "raw_chase_limit": value.raw_chase_limit,
            "raw_stop": value.raw_stop,
            "created_at": value.created_at,
            "expires_at": value.expires_at,
            "reason": value.reason,
            "do_not_chase": value.do_not_chase,
        }
    )


def _validated_prepared_setup(value: object) -> PreparedSetup:
    if type(value) is not PreparedSetup:
        raise PlanError("PREPARED_SETUP_AUTHORITY_INVALID")
    try:
        if not _is_issued(value, _prepared_fingerprint(value)):
            raise PlanError("PREPARED_SETUP_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise PlanError("PREPARED_SETUP_AUTHORITY_INVALID") from exc
    return value


def _validated_strategy_output(value: StrategyOutput) -> StrategyOutput:
    if type(value) is not StrategyOutput:
        raise PlanError("STRATEGY_OUTPUT_AUTHORITY_INVALID")
    try:
        if not _is_issued(value, _output_fingerprint(value)):
            raise PlanError("STRATEGY_OUTPUT_AUTHORITY_INVALID")
    except (AttributeError, TypeError, ValueError) as exc:
        raise PlanError("STRATEGY_OUTPUT_AUTHORITY_INVALID") from exc
    return value


def _output(
    provenance: StrategyProvenance,
    speed: Literal["FAST", "STANDARD"],
    trigger: Candle,
    material_extreme: Decimal,
) -> StrategyOutput:
    identity, time, digest = _candle_authority(trigger)
    raw = _geometry(provenance, speed, material_extreme)
    created = trigger.evidence.received_at.astimezone(UTC)
    output = StrategyOutput(
        provenance,
        provenance.setup_id,
        speed,
        identity,
        time,
        digest,
        created,
        material_extreme,
        *raw,
        created,
        created + timedelta(seconds=180 if speed == "FAST" else 900),
    )
    return _issue(output, _output_fingerprint(output))  # type: ignore[return-value]


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
    if (output.side is Side.LONG and reference <= output.raw_stop) or (
        output.side is Side.SHORT and reference >= output.raw_stop
    ):
        return SignalState.INVALIDATED
    if _utc(now, "LIFECYCLE_TIME_INVALID") >= output.expires_at:
        return SignalState.EXPIRED
    return output.state


def advance_prepare(
    setup: PreparedSetup,
    snapshot: StrategySnapshot,
    *,
    already_decided: bool = False,
) -> Signal | StrategyOutput:
    setup = _validated_prepared_setup(setup)
    try:
        snapshot = _validated_strategy_snapshot(snapshot)
    except ValueError as exc:
        raise PlanError("STRATEGY_SNAPSHOT_AUTHORITY_INVALID") from exc
    p = setup.provenance
    if snapshot.quality.state is not DataQualityState.READY:
        return Signal(SignalState.INVALIDATED, p.side, "STANDARD", setup.setup_id, "DATA_NOT_READY")
    if already_decided:
        return Signal(
            SignalState.REJECTED, p.side, "STANDARD", setup.setup_id, "SETUP_ALREADY_DECIDED"
        )
    if not snapshot.candles_5m:
        return Signal(SignalState.INVALIDATED, p.side, "STANDARD", setup.setup_id, "DATA_NOT_READY")
    candle = snapshot.candles_5m[-1]
    if candle.open_time_ms > setup.expires_after_open_time_ms:
        return Signal(
            SignalState.EXPIRED, p.side, "STANDARD", setup.setup_id, "PREPARE_WINDOW_EXPIRED"
        )
    long = p.side is Side.LONG
    point = candle.low if long else candle.high
    within = (
        p.boundary - Decimal(".15") * p.atr <= point <= p.boundary + Decimal(".10") * p.atr
        if long
        else p.boundary - Decimal(".10") * p.atr <= point <= p.boundary + Decimal(".15") * p.atr
    )
    closes_ok = True
    if p.family is SetupFamily.BREAKOUT_RETEST:
        intervening_closes = tuple(
            item.close
            for item in snapshot.candles_5m
            if p.setup_trigger_open_time_ms < item.open_time_ms < candle.open_time_ms
        )
        closes_ok = (
            not any(value < p.boundary - Decimal(".20") * p.atr for value in intervening_closes)
            if long
            else not any(
                value > p.boundary + Decimal(".20") * p.atr
                for value in intervening_closes
            )
        )
    confirmed = (
        within
        and (
            candle.close >= p.boundary + Decimal(".05") * p.atr
            if long
            else candle.close <= p.boundary - Decimal(".05") * p.atr
        )
        and closes_ok
    )
    if p.family is SetupFamily.SWEEP_RECLAIM:
        confirmed = confirmed and (point > p.initial_extreme if long else point < p.initial_extreme)
    return (
        _output(p, "STANDARD", candle, point)
        if confirmed
        else Signal(SignalState.PREPARE, p.side, "STANDARD", setup.setup_id, "AWAITING_RETEST")
    )


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal()) / Decimal(len(values))


def _features(
    c5: tuple[Candle, ...], c15: tuple[Candle, ...]
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool, bool]:
    if len(c5) < 27 or len(c15) < 11:
        raise PlanError("INSUFFICIENT_LOOKBACK")
    trigger = c5[-1]
    if trigger.high == trigger.low:
        raise PlanError("ZERO_RANGE_TRIGGER")
    trs = [
        max(item.high - item.low, abs(item.high - c5[i - 1].close), abs(item.low - c5[i - 1].close))
        for i, item in enumerate(c5[-14:], start=len(c5) - 14)
    ]
    closes = [item.close for item in c15]
    return (
        _mean(trs),
        max(item.high for item in c5[-13:-1]),
        min(item.low for item in c5[-13:-1]),
        median([item.volume for item in c5[-21:-1]]),
        (trigger.close - trigger.low) / (trigger.high - trigger.low),
        closes[-1] > _mean(closes[-8:]) > _mean(closes[-11:-3]),
        closes[-1] < _mean(closes[-8:]) < _mean(closes[-11:-3]),
    )


def evaluate_signal(
    snapshot: StrategySnapshot,
    *,
    decided_setup_ids: frozenset[str] = frozenset(),
) -> Signal | PreparedSetup | StrategyOutput:
    try:
        snapshot = _validated_strategy_snapshot(snapshot)
    except ValueError as exc:
        raise PlanError("STRATEGY_SNAPSHOT_AUTHORITY_INVALID") from exc
    if snapshot.quality.state is not DataQualityState.READY:
        return Signal(
            SignalState.WAIT,
            None,
            None,
            None,
            f"DATA_{snapshot.quality.state.value}",
        )
    candles_5m, candles_15m = snapshot.candles_5m, snapshot.candles_15m
    try:
        atr, high, low, volume, location, long_bias, short_bias = _features(candles_5m, candles_15m)
    except PlanError as exc:
        return Signal(SignalState.WAIT, None, None, None, str(exc))
    t, body = candles_5m[-1], abs(candles_5m[-1].close - candles_5m[-1].open)
    candidates = (
        (
            SetupFamily.SWEEP_RECLAIM,
            Side.LONG,
            low,
            t.low,
            t.low <= low - Decimal(".10") * atr
            and t.close >= low
            and location >= Decimal(".60")
            and not short_bias,
            t.volume >= Decimal("1.50") * volume and t.close - low >= Decimal(".10") * atr,
        ),
        (
            SetupFamily.SWEEP_RECLAIM,
            Side.SHORT,
            high,
            t.high,
            t.high >= high + Decimal(".10") * atr
            and t.close <= high
            and Decimal(1) - location >= Decimal(".60")
            and not long_bias,
            t.volume >= Decimal("1.50") * volume and high - t.close >= Decimal(".10") * atr,
        ),
        (
            SetupFamily.BREAKOUT_RETEST,
            Side.LONG,
            high,
            t.low,
            t.close >= high + Decimal(".10") * atr
            and body >= Decimal(".35") * atr
            and location >= Decimal(".70")
            and t.volume >= Decimal("1.20") * volume
            and long_bias,
            body >= Decimal(".50") * atr and t.volume >= Decimal("1.50") * volume,
        ),
        (
            SetupFamily.BREAKOUT_RETEST,
            Side.SHORT,
            low,
            t.high,
            t.close <= low - Decimal(".10") * atr
            and body >= Decimal(".35") * atr
            and Decimal(1) - location >= Decimal(".70")
            and t.volume >= Decimal("1.20") * volume
            and short_bias,
            body >= Decimal(".50") * atr and t.volume >= Decimal("1.50") * volume,
        ),
    )
    for family, side, boundary, extreme, matched, fast in candidates:
        if not matched:
            continue
        identity, time, digest = _candle_authority(t)
        p = StrategyProvenance(family, side, boundary, atr, extreme, identity, time, digest)
        if p.setup_id in decided_setup_ids:
            return Signal(SignalState.WAIT, None, None, p.setup_id, "SETUP_ALREADY_DECIDED")
        if fast:
            return _output(p, "FAST", t, extreme)
        prepared = PreparedSetup(p, t.open_time_ms + 900_000)
        return _issue(prepared, _prepared_fingerprint(prepared))  # type: ignore[return-value]
    return Signal(
        SignalState.WATCH
        if min(abs(t.close - high), abs(t.close - low)) <= Decimal(".25") * atr
        else SignalState.WAIT,
        None,
        None,
        None,
        "NEAR_PRIOR_RANGE_BOUNDARY"
        if min(abs(t.close - high), abs(t.close - low)) <= Decimal(".25") * atr
        else "NO_ACTIONABLE_CLOSED_CANDLE",
    )


def _round_price(value: Decimal, sz_decimals: int, direction: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise PlanError("PRICE_PRECISION_INPUT_INVALID")
    if type(sz_decimals) is not int or isinstance(sz_decimals, bool) or not 0 <= sz_decimals <= 6:
        raise PlanError("SZ_DECIMALS_PRECISION_INVALID")
    if direction not in {"up", "down"}:
        raise PlanError("PRICE_ROUNDING_DIRECTION_INVALID")
    _guard_decimal_exponent(value, "PRICE_PRECISION_INPUT_INVALID")
    if value == value.to_integral_value():
        return value
    try:
        quantum = Decimal(1).scaleb(max(value.adjusted() - 4, -(6 - sz_decimals)))
    except (InvalidOperation, ValueError):
        raise PlanError("PRICE_PRECISION_INPUT_INVALID") from None
    try:
        return value.quantize(quantum, rounding=ROUND_CEILING if direction == "up" else ROUND_FLOOR)
    except InvalidOperation:
        raise PlanError("PRICE_PRECISION_INPUT_INVALID") from None


def round_quantity(raw_quantity: Decimal, sz_decimals: int) -> Decimal:
    if type(raw_quantity) is not Decimal or not raw_quantity.is_finite() or raw_quantity <= 0:
        raise PlanError("QUANTITY_PRECISION_INPUT_INVALID")
    if type(sz_decimals) is not int or isinstance(sz_decimals, bool) or not 0 <= sz_decimals <= 18:
        raise PlanError("SZ_DECIMALS_QUANTITY_INVALID")
    _guard_decimal_exponent(raw_quantity, "QUANTITY_PRECISION_INPUT_INVALID")
    try:
        result = raw_quantity.quantize(
            Decimal(1).scaleb(-sz_decimals),
            rounding=ROUND_DOWN,
        )
    except (InvalidOperation, ValueError):
        raise PlanError("QUANTITY_PRECISION_INPUT_INVALID") from None
    if result <= 0:
        raise PlanError("ZERO_QUANTITY_AFTER_PRECISION")
    return result


def inward_zone(low: Decimal, high: Decimal, sz_decimals: int) -> tuple[Decimal, Decimal]:
    result = _round_price(low, sz_decimals, "up"), _round_price(high, sz_decimals, "down")
    if result[0] > result[1]:
        raise PlanError("ROUNDED_ENTRY_ZONE_EMPTY")
    return result


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
    adverse_entry = planned_entry * (Decimal("1.0005") if side is Side.LONG else Decimal(".9995"))
    adverse_stop = stop * (Decimal(".9995") if side is Side.LONG else Decimal("1.0005"))
    price_loss = abs(adverse_entry - adverse_stop)
    entry_fee = adverse_entry * Decimal(".00045")
    exit_fee = adverse_stop * Decimal(".00045")
    worst_case = price_loss + entry_fee + exit_fee
    budget = account_equity_usd * Decimal(".0025")
    maximum = account_equity_usd
    risk_quantity = budget / worst_case
    notional_quantity = maximum / abs(adverse_entry)
    return RawRiskMath(
        adverse_entry,
        adverse_stop,
        price_loss,
        entry_fee,
        exit_fee,
        worst_case,
        budget,
        maximum,
        risk_quantity,
        notional_quantity,
        min(risk_quantity, notional_quantity),
    )


def size_plan(
    *, side: Side, entry: Decimal, stop: Decimal, equity: Decimal, sz_decimals: int
) -> RiskResult:
    result = risk_math(side=side, planned_entry=entry, stop=stop, account_equity_usd=equity)
    quantity = round_quantity(result.quantity_raw, sz_decimals)
    planned_risk = quantity * result.worst_case_loss_per_unit
    if planned_risk > result.risk_budget_usd:
        raise PlanError("RISK_BUDGET_EXCEEDED")
    return RiskResult(quantity, quantity * entry, result.risk_budget_usd, planned_risk)


@dataclass(frozen=True)
class TradePlan:
    plan_id: str
    canonical_hash: str
    strategy_output: StrategyOutput
    provenance: StrategyProvenance
    setup_id: str
    speed: Literal["FAST", "STANDARD"]
    decision_trigger_identity: tuple[str, str, int]
    decision_trigger_open_time_ms: int
    decision_trigger_canonical_hash: str
    decision_trigger_received_at: datetime
    strategy_reason: Literal["CONFIRMED"]
    strategy_do_not_chase: Literal["DO NOT CHASE"]
    material_extreme: Decimal
    raw_entry_low: Decimal
    raw_entry_high: Decimal
    raw_chase_limit: Decimal
    raw_stop: Decimal
    created_at: datetime
    expires_at: datetime
    supersedes_plan_id: str | None
    symbol: Literal["ETH"]
    reference: Decimal
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
    trade_plan_version: Literal["2"] = TRADE_PLAN_VERSION
    strategy_version: Literal["ETH-LDAR-v0.1"] = STRATEGY_VERSION
    configuration_version: Literal["1"] = CONFIGURATION_VERSION
    do_not_chase: Literal["DO NOT CHASE"] = "DO NOT CHASE"

    @property
    def side(self) -> Side:
        return self.provenance.side

    @property
    def family(self) -> SetupFamily:
        return self.provenance.family

    def raw_values(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        return self.raw_entry_low, self.raw_entry_high, self.raw_chase_limit, self.raw_stop

    def _strategy_output(self) -> StrategyOutput:
        provenance = StrategyProvenance(
            self.provenance.family,
            self.provenance.side,
            self.provenance.boundary,
            self.provenance.atr,
            self.provenance.initial_extreme,
            self.provenance.setup_trigger_identity,
            self.provenance.setup_trigger_open_time_ms,
            self.provenance.setup_trigger_canonical_hash,
        )
        return StrategyOutput(
            provenance,
            self.setup_id,
            self.speed,
            self.decision_trigger_identity,
            self.decision_trigger_open_time_ms,
            self.decision_trigger_canonical_hash,
            self.decision_trigger_received_at,
            self.material_extreme,
            self.raw_entry_low,
            self.raw_entry_high,
            self.raw_chase_limit,
            self.raw_stop,
            self.created_at,
            self.expires_at,
            self.strategy_reason,
            self.strategy_do_not_chase,
        )

    def __post_init__(self) -> None:
        if (
            self.trade_plan_version != TRADE_PLAN_VERSION
            or self.strategy_version != STRATEGY_VERSION
            or self.configuration_version != CONFIGURATION_VERSION
            or self.symbol != "ETH"
            or self.do_not_chase != "DO NOT CHASE"
        ):
            raise PlanError("TRADE_PLAN_FIXED_AUTHORITY_INVALID")
        if self.supersedes_plan_id is not None and (
            type(self.supersedes_plan_id) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.supersedes_plan_id) is None
        ):
            raise PlanError("TRADE_PLAN_SUPERSEDES_INVALID")
        if type(self.strategy_output) is not StrategyOutput:
            raise PlanError("TRADE_PLAN_STRATEGY_AUTHORITY_INVALID")
        embedded_output = _validated_strategy_output(self.strategy_output)
        output = self._strategy_output()
        if output != embedded_output:
            raise PlanError("TRADE_PLAN_STRATEGY_CORRESPONDENCE_INVALID")
        financials = (
            self.reference,
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
        low, high = inward_zone(output.raw_entry_low, output.raw_entry_high, self.sz_decimals)
        if (self.entry_low, self.entry_high) != (low, high):
            raise PlanError("TRADE_PLAN_ROUNDED_ZONE_INVALID")
        direction = "up" if output.side is Side.LONG else "down"
        expected_entry = _round_price(
            min(max(self.reference, low), high), self.sz_decimals, direction
        )
        expected_chase = _round_price(
            output.raw_chase_limit,
            self.sz_decimals,
            "down" if output.side is Side.LONG else "up",
        )
        expected_stop = _round_price(
            output.raw_stop,
            self.sz_decimals,
            "down" if output.side is Side.LONG else "up",
        )
        if (self.planned_entry, self.chase_limit, self.stop) != (
            expected_entry,
            expected_chase,
            expected_stop,
        ):
            raise PlanError("TRADE_PLAN_ROUNDED_EXECUTION_INVALID")
        if (output.side is Side.LONG and self.reference > output.raw_chase_limit) or (
            output.side is Side.SHORT and self.reference < output.raw_chase_limit
        ):
            raise PlanError("CHASE_LIMIT_EXCEEDED")
        distance = abs(self.planned_entry - self.stop)
        if (
            not Decimal(".10") * output.provenance.atr
            <= distance
            <= Decimal("1.50") * output.provenance.atr
        ):
            raise PlanError("STOP_DISTANCE_OUT_OF_RANGE")
        risk = size_plan(
            side=output.side,
            entry=self.planned_entry,
            stop=self.stop,
            equity=self.account_equity,
            sz_decimals=self.sz_decimals,
        )
        if (self.quantity, self.notional, self.risk_budget, self.planned_risk) != (
            risk.quantity,
            risk.notional,
            risk.risk_budget,
            risk.planned_risk,
        ) or self.notional < Decimal("10"):
            raise PlanError("TRADE_PLAN_RISK_INCONSISTENT")
        r_value = abs(self.planned_entry - self.stop)
        target_direction = "down" if output.side is Side.LONG else "up"
        expected_targets = (
            _round_price(
                self.planned_entry + r_value
                if output.side is Side.LONG
                else self.planned_entry - r_value,
                self.sz_decimals,
                target_direction,
            ),
            _round_price(
                self.planned_entry + 2 * r_value
                if output.side is Side.LONG
                else self.planned_entry - 2 * r_value,
                self.sz_decimals,
                target_direction,
            ),
        )
        if (self.tp1, self.tp2) != expected_targets:
            raise PlanError("TRADE_PLAN_TARGETS_INVALID")
        if (
            not all(
                type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in (self.plan_id, self.canonical_hash)
            )
            or self.plan_id != self.canonical_hash
            or self.plan_id != _trade_digest(self.payload())
        ):
            raise PlanError("TRADE_PLAN_HASH_INVALID")

    def payload(self) -> dict[str, object]:
        return _trade_plan_payload(self.__dict__)


def _trade_plan_payload(values: dict[str, object]) -> dict[str, object]:
    provenance = values["provenance"]
    if type(provenance) is not StrategyProvenance:
        raise PlanError("TRADE_PLAN_PROVENANCE_INVALID")
    created_at = values["created_at"]
    expires_at = values["expires_at"]
    received_at = values["decision_trigger_received_at"]
    if (
        type(created_at) is not datetime
        or type(expires_at) is not datetime
        or type(received_at) is not datetime
    ):
        raise PlanError("TRADE_PLAN_TIMESTAMP_INVALID")
    return {
        "trade_plan_version": values["trade_plan_version"],
        "strategy_version": values["strategy_version"],
        "configuration_version": values["configuration_version"],
        "symbol": values["symbol"],
        "setup_id": values["setup_id"],
        "provenance": provenance.payload(),
        "speed": values["speed"],
        "decision_trigger_identity": values["decision_trigger_identity"],
        "decision_trigger_open_time_ms": values["decision_trigger_open_time_ms"],
        "decision_trigger_canonical_hash": values["decision_trigger_canonical_hash"],
        "decision_trigger_received_at": received_at.isoformat(),
        "strategy_reason": values["strategy_reason"],
        "strategy_do_not_chase": values["strategy_do_not_chase"],
        "material_extreme": values["material_extreme"],
        "raw_entry_low": values["raw_entry_low"],
        "raw_entry_high": values["raw_entry_high"],
        "raw_chase_limit": values["raw_chase_limit"],
        "raw_stop": values["raw_stop"],
        "strategy_created_at": created_at.isoformat(),
        "strategy_expires_at": expires_at.isoformat(),
        "supersedes_plan_id": values["supersedes_plan_id"],
        "reference": values["reference"],
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


def _trade_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        TRADE_PLAN_HASH_DOMAIN.encode() + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def build_plan(
    *,
    strategy_output: StrategyOutput,
    reference: Decimal,
    equity: Decimal,
    sz_decimals: int,
    supersedes_plan_id: str | None = None,
) -> TradePlan:
    if type(strategy_output) is not StrategyOutput or type(reference) is not Decimal:
        raise PlanError("BUILD_PLAN_AUTHORITY_INVALID")
    if not reference.is_finite() or reference <= 0:
        raise PlanError("BUILD_PLAN_AUTHORITY_INVALID")
    output = _validated_strategy_output(strategy_output)
    low, high = inward_zone(output.raw_entry_low, output.raw_entry_high, sz_decimals)
    if (output.side is Side.LONG and reference > output.raw_chase_limit) or (
        output.side is Side.SHORT and reference < output.raw_chase_limit
    ):
        raise PlanError("CHASE_LIMIT_EXCEEDED")
    direction = "up" if output.side is Side.LONG else "down"
    entry = _round_price(min(max(reference, low), high), sz_decimals, direction)
    stop = _round_price(
        output.raw_stop,
        sz_decimals,
        "down" if output.side is Side.LONG else "up",
    )
    distance = abs(entry - stop)
    if (
        not Decimal(".10") * output.provenance.atr
        <= distance
        <= Decimal("1.50") * output.provenance.atr
    ):
        raise PlanError("STOP_DISTANCE_OUT_OF_RANGE")
    risk = size_plan(
        side=output.side, entry=entry, stop=stop, equity=equity, sz_decimals=sz_decimals
    )
    if risk.notional < Decimal("10"):
        raise PlanError("MINIMUM_NOTIONAL_NOT_MET")
    target_direction = "down" if output.side is Side.LONG else "up"
    tp1 = _round_price(
        entry + distance if output.side is Side.LONG else entry - distance,
        sz_decimals,
        target_direction,
    )
    tp2 = _round_price(
        entry + 2 * distance if output.side is Side.LONG else entry - 2 * distance,
        sz_decimals,
        target_direction,
    )
    values: dict[str, object] = {
        "strategy_output": output,
        "provenance": output.provenance,
        "setup_id": output.setup_id,
        "speed": output.speed,
        "decision_trigger_identity": output.decision_trigger_identity,
        "decision_trigger_open_time_ms": output.decision_trigger_open_time_ms,
        "decision_trigger_canonical_hash": output.decision_trigger_canonical_hash,
        "decision_trigger_received_at": output.decision_trigger_received_at,
        "strategy_reason": output.reason,
        "strategy_do_not_chase": output.do_not_chase,
        "material_extreme": output.material_extreme,
        "raw_entry_low": output.raw_entry_low,
        "raw_entry_high": output.raw_entry_high,
        "raw_chase_limit": output.raw_chase_limit,
        "raw_stop": output.raw_stop,
        "created_at": output.created_at,
        "expires_at": output.expires_at,
        "supersedes_plan_id": supersedes_plan_id,
        "symbol": "ETH",
        "reference": reference,
        "entry_low": low,
        "entry_high": high,
        "planned_entry": entry,
        "chase_limit": _round_price(
            output.raw_chase_limit, sz_decimals, "down" if output.side is Side.LONG else "up"
        ),
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
    digest = _trade_digest(_trade_plan_payload(values))
    return TradePlan(plan_id=digest, canonical_hash=digest, **values)  # type: ignore[arg-type]


@dataclass(frozen=True)
class AIExplanation:
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    missing_or_conflicting_inputs: tuple[str, ...]
    risk_and_expiry_warnings: tuple[str, ...]
    execution_checklist: tuple[str, ...]
    status: Literal["AVAILABLE", "UNAVAILABLE"]

    def __post_init__(self) -> None:
        fields = (
            self.supporting_evidence,
            self.opposing_evidence,
            self.missing_or_conflicting_inputs,
            self.risk_and_expiry_warnings,
            self.execution_checklist,
        )
        if self.status not in {"AVAILABLE", "UNAVAILABLE"} or any(
            type(field) is not tuple
            or len(field) > 8
            or any(type(item) is not str or len(item) > 240 for item in field)
            for field in fields
        ):
            raise PlanError("AI_EXPLANATION_INVALID")


def fallback_explanation(
    plan: TradePlan,
    quality: DataQualityState,
    *,
    status: Literal["AVAILABLE", "UNAVAILABLE"] = "AVAILABLE",
) -> AIExplanation:
    return AIExplanation(
        (f"Deterministic {plan.side.value} {plan.speed} plan",),
        (),
        (() if quality is DataQualityState.READY else (quality.value,)),
        ("DO NOT CHASE", f"Expires {plan.expires_at.isoformat()}"),
        ("Verify manual order details", "Record TAKEN, SKIPPED, or REJECTED"),
        status,
    )


def bounded_explanation(
    value: object | None, plan: TradePlan, quality: DataQualityState
) -> AIExplanation:
    if value is None:
        return fallback_explanation(plan, quality)
    if type(value) is not AIExplanation:
        return fallback_explanation(plan, quality, status="UNAVAILABLE")
    try:
        AIExplanation(
            value.supporting_evidence,
            value.opposing_evidence,
            value.missing_or_conflicting_inputs,
            value.risk_and_expiry_warnings,
            value.execution_checklist,
            value.status,
        )
    except (PlanError, AttributeError):
        return fallback_explanation(plan, quality, status="UNAVAILABLE")
    return value
