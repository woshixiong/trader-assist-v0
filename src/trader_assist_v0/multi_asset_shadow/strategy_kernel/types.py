"""Immutable contracts for the pure multi-asset strategy kernel.

These types deliberately do not import the A1 runtime or persistence layers.  An
integration lane can adapt provider-finalized ``ClosedBar`` objects to ``Bar``
without giving the strategy kernel network, database, account, or order authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any

STRATEGY_VERSION = "FL-MA-PRICE-ACTION-v0.1"
PARAMETER_VERSION = "2026-08-03-r1"
SCANNER_VERSION = "SESSION-MOMENTUM-R3"
SCHEMA_VERSION = "1"


class KernelInputError(ValueError):
    """Raised when an immutable strategy input is incomplete or contradictory."""


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def opposite(self) -> Side:
        return Side.SHORT if self is Side.LONG else Side.LONG


class SetupFamily(StrEnum):
    """The complete and intentionally closed formal Setup set."""

    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    RANGE_EDGE_REJECTION = "RANGE_EDGE_REJECTION"


class SetupMode(StrEnum):
    """External confirmation modes for Breakout Retest only."""

    MICRO_FAST = "MICRO_FAST"
    STANDARD = "STANDARD"


class RetestType(StrEnum):
    """Internal STANDARD retest classification exposed separately from mode."""

    DEEP = "DEEP"
    SHALLOW = "SHALLOW"


class DecisionKind(StrEnum):
    WAIT = "WAIT"
    FORMAL_SETUP_CONFIRMED = "FORMAL_SETUP_CONFIRMED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    DATA_INVALID = "DATA_INVALID"


class EventStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"
    DATA_INVALID = "DATA_INVALID"
    UNRESOLVED_AT_SHUTDOWN = "UNRESOLVED_AT_SHUTDOWN"

    @property
    def terminal(self) -> bool:
        return self is not EventStatus.ACTIVE


class ZoneType(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class ZoneQuality(StrEnum):
    ZQ1 = "ZQ1"
    ZQ2 = "ZQ2"
    ZQ3 = "ZQ3"

    @property
    def rank(self) -> int:
        return {ZoneQuality.ZQ1: 1, ZoneQuality.ZQ2: 2, ZoneQuality.ZQ3: 3}[self]


class HtfMomentum(StrEnum):
    UP = "HTF_MOMENTUM_UP"
    DOWN = "HTF_MOMENTUM_DOWN"
    NEUTRAL = "HTF_MOMENTUM_NEUTRAL"
    UNAVAILABLE = "HTF_MOMENTUM_UNAVAILABLE"


class HtfStructure(StrEnum):
    UP = "HTF_STRUCTURE_UP"
    DOWN = "HTF_STRUCTURE_DOWN"
    RANGE = "HTF_STRUCTURE_RANGE"
    TRANSITION = "HTF_STRUCTURE_TRANSITION"
    INSUFFICIENT = "HTF_STRUCTURE_INSUFFICIENT"
    UNAVAILABLE = "HTF_STRUCTURE_UNAVAILABLE"


class HtfRelation(StrEnum):
    ALIGNED_STRONG = "ALIGNED_STRONG"
    ALIGNED_PARTIAL = "ALIGNED_PARTIAL"
    COUNTERTREND_STRONG = "COUNTERTREND_STRONG"
    COUNTERTREND_PARTIAL = "COUNTERTREND_PARTIAL"
    CONFLICTED = "CONFLICTED"
    NEUTRAL = "NEUTRAL"
    CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"


class ScannerState(StrEnum):
    WATCH_MOMENTUM = "WATCH_MOMENTUM"
    WATCH_NEAR_LEVEL = "WATCH_NEAR_LEVEL"
    WATCH_NEW_MARKET = "WATCH_NEW_MARKET"
    BREAKOUT_DETECTED = "BREAKOUT_DETECTED"
    RETEST_PENDING = "RETEST_PENDING"
    BREAKOUT_RETEST_READY = "BREAKOUT_RETEST_READY"
    FAILED_BREAKOUT_SWEEP_WATCH = "FAILED_BREAKOUT_SWEEP_WATCH"
    FAILED_INVALIDATED_INSIDE_RANGE = "FAILED_INVALIDATED_INSIDE_RANGE"
    LATE_WATCH = "LATE_WATCH"
    REJECTED_CHASE_FOR_ACTION = "REJECTED_CHASE_FOR_ACTION"
    EXPIRED_NO_RETEST = "EXPIRED_NO_RETEST"


class ScannerChase(StrEnum):
    EARLY = "EARLY_ACCEPTABLE_FOR_REVIEW"
    LATE = "LATE_WATCH_DO_NOT_CHASE"
    REJECTED = "REJECTED_CHASE_FOR_ACTION_KEEP_FOR_RESEARCH"


class TargetKind(StrEnum):
    ZONE = "ZONE"
    RANGE_CENTER = "RANGE_CENTER"
    SOURCE_ZONE_CENTER = "SOURCE_ZONE_CENTER"
    DIRECTIONAL_ZONE_SET_FROZEN = "DIRECTIONAL_ZONE_SET_FROZEN"
    OPEN_SPACE_REFERENCE = "OPEN_SPACE_REFERENCE"


def _finite_positive(value: Decimal) -> bool:
    return value.is_finite() and value > 0


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Bar:
    """Narrow immutable view of a received, closed candle."""

    market_id: str
    interval: str
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source_identity: str = "STRATEGY_INPUT_VIEW"

    def __post_init__(self) -> None:
        if not self.market_id or self.interval not in {"5m", "15m", "1h"}:
            raise KernelInputError("bar identity or interval is invalid")
        if self.open_time_ms < 0 or self.close_time_ms <= self.open_time_ms:
            raise KernelInputError("bar time geometry is invalid")
        if not all(_finite_positive(item) for item in (self.open, self.high, self.low, self.close)):
            raise KernelInputError("OHLC values must be positive and finite")
        if not self.volume.is_finite() or self.volume < 0:
            raise KernelInputError("volume must be nonnegative and finite")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise KernelInputError("bar OHLC range is invalid")

    @property
    def candle_id(self) -> str:
        return _hash_text(
            "|".join(
                (
                    self.market_id,
                    self.interval,
                    str(self.open_time_ms),
                    str(self.close_time_ms),
                    str(self.open),
                    str(self.high),
                    str(self.low),
                    str(self.close),
                    str(self.volume),
                    self.source_identity,
                )
            )
        )


@dataclass(frozen=True)
class Reaction:
    reaction_id: str
    market_id: str
    zone_type: ZoneType
    pivot_bar_index: int
    confirmed_bar_index: int
    price: Decimal
    a15_reaction: Decimal


@dataclass(frozen=True)
class ZoneSnapshot:
    zone_id: str
    market_id: str
    zone_type: ZoneType
    center: Decimal
    low: Decimal
    high: Decimal
    half_width: Decimal
    quality: ZoneQuality
    reaction_count: int
    latest_reaction_bar_index: int
    member_reaction_ids: tuple[str, ...]
    active_for_new_event: bool
    suppressed: bool = False

    def __post_init__(self) -> None:
        if not self.zone_id or self.low > self.center or self.center > self.high:
            raise KernelInputError("zone geometry is invalid")
        if self.half_width <= 0 or self.reaction_count != len(self.member_reaction_ids):
            raise KernelInputError("zone membership is invalid")

    @property
    def width(self) -> Decimal:
        return self.high - self.low

    def contains(self, value: Decimal) -> bool:
        return self.low <= value <= self.high


@dataclass(frozen=True)
class HtfContext:
    momentum: HtfMomentum
    structure: HtfStructure
    er8_1h: Decimal | None
    d8_1h: Decimal | None


@dataclass(frozen=True)
class ScannerLinkage:
    candidate_id: str
    state: ScannerState
    scanner_version: str = SCANNER_VERSION


@dataclass(frozen=True)
class TargetReference:
    kind: TargetKind
    price: Decimal | None
    zone_id: str | None = None
    frozen_directional_zones: tuple[ZoneSnapshot, ...] = ()


@dataclass(frozen=True)
class BreakoutLinkage:
    underlying_breakout_event_id: str
    initial_breakout_candle_id: str
    accepted_reentry_source_event_id: str | None = None


@dataclass(frozen=True)
class StrategyDecision:
    market_id: str
    setup_family: SetupFamily
    setup_mode: SetupMode | None
    retest_type: RetestType | None
    side: Side
    decision: DecisionKind
    reason: str
    market_event_id: str
    zone_id: str
    zone_snapshot: ZoneSnapshot
    a5_event: Decimal
    m20_event: Decimal
    htf_relation: HtfRelation
    breakout_linkage: BreakoutLinkage | None
    ideal_entry_low: Decimal | None
    ideal_entry_high: Decimal | None
    chase_limit: Decimal | None
    structural_stop: Decimal | None
    target_reference: TargetReference | None
    transition: str
    scanner_linkage: ScannerLinkage | None
    strategy_version: str = STRATEGY_VERSION
    parameter_version: str = PARAMETER_VERSION
    scanner_version: str = SCANNER_VERSION
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
            if self.setup_mode is not None or self.retest_type is not None:
                raise KernelInputError("non-formal decisions cannot expose confirmation mode")
            return
        if self.setup_family is not SetupFamily.BREAKOUT_RETEST:
            if self.setup_mode is not None or self.retest_type is not None:
                raise KernelInputError("non-breakout decisions cannot expose breakout mode")
            return
        if self.setup_mode is SetupMode.MICRO_FAST:
            if self.retest_type is not None:
                raise KernelInputError("MICRO_FAST cannot expose a STANDARD retest type")
            return
        if self.setup_mode is SetupMode.STANDARD and isinstance(self.retest_type, RetestType):
            return
        raise KernelInputError("formal Breakout Retest requires MICRO_FAST or typed STANDARD")


@dataclass(frozen=True)
class MarketEvent:
    market_event_id: str
    market_id: str
    setup_family: SetupFamily
    side: Side
    status: EventStatus
    transition: str
    zone: ZoneSnapshot
    created_bar: Bar
    latest_bar: Bar
    a5_event: Decimal
    m20_event: Decimal
    htf_relation: HtfRelation
    scanner_linkage: ScannerLinkage | None = None
    breakout_linkage: BreakoutLinkage | None = None
    reclaim_candle_high: Decimal | None = None
    reclaim_candle_low: Decimal | None = None
    sweep_extreme: Decimal | None = None
    initial_breakout_open: Decimal | None = None
    initial_breakout_high: Decimal | None = None
    initial_breakout_low: Decimal | None = None
    initial_breakout_close: Decimal | None = None
    previous_close: Decimal | None = None
    previous_high: Decimal | None = None
    previous_low: Decimal | None = None
    pullback_started: bool = False
    impulse_extreme: Decimal | None = None
    pullback_extreme: Decimal | None = None
    retest_type: RetestType | None = None
    retest_seen_bar_time_ms: int | None = None
    formal_mode: SetupMode | None = None
    ideal_entry_low: Decimal | None = None
    ideal_entry_high: Decimal | None = None
    chase_limit: Decimal | None = None
    structural_stop: Decimal | None = None
    target_reference: TargetReference | None = None

    def evolve(self, **changes: Any) -> MarketEvent:
        return replace(self, **changes)


@dataclass(frozen=True)
class EventLedger:
    events: tuple[MarketEvent, ...] = ()

    def active(self, *, market_id: str, family: SetupFamily, side: Side) -> MarketEvent | None:
        matches = (
            event
            for event in reversed(self.events)
            if event.market_id == market_id
            and event.setup_family is family
            and event.side is side
            and event.status is EventStatus.ACTIVE
        )
        return next(matches, None)

    def replace_event(self, value: MarketEvent) -> EventLedger:
        replaced = False
        updated: list[MarketEvent] = []
        for event in self.events:
            if event is value:
                updated.append(event)
            elif (
                not replaced
                and event.market_event_id == value.market_event_id
                and event.setup_family is value.setup_family
                and event.side is value.side
                and event.created_bar.candle_id == value.created_bar.candle_id
            ):
                updated.append(value)
                replaced = True
            else:
                updated.append(event)
        if not replaced:
            raise KernelInputError("event to replace is not present")
        return EventLedger(tuple(updated))

    def append(self, value: MarketEvent) -> EventLedger:
        return EventLedger((*self.events, value))


@dataclass(frozen=True)
class KernelResult:
    ledger: EventLedger
    decisions: tuple[StrategyDecision, ...]
    zones: tuple[ZoneSnapshot, ...]
    active_support: ZoneSnapshot | None
    active_resistance: ZoneSnapshot | None
    htf_context: HtfContext
