"""Pure contracts for the on-demand Formal Shadow 1m outcome path.

The contracts in this module deliberately carry no exchange, account, signing,
or order-submission surface.  Integration code can map its records into these
views without making the outcome engine depend on a parallel implementation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable

ONE_MINUTE_MS = 60_000
OUTCOME_HORIZONS_MINUTES = (30, 60, 120)


class OutcomeEngineError(ValueError):
    """An input cannot enter the deterministic outcome authority."""


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class ShadowState(StrEnum):
    FORMAL_SHADOW_PLAN = "FORMAL_SHADOW_PLAN"
    WATCH = "WATCH"


class SetupFamily(StrEnum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    RANGE_EDGE_REJECTION = "RANGE_EDGE_REJECTION"


class TransitionKind(StrEnum):
    RETURN_INSIDE_RANGE = "RETURN_INSIDE_RANGE"
    ACCEPTED_REENTRY = "ACCEPTED_REENTRY"
    FAILED_BREAKOUT = "FAILED_BREAKOUT"
    RECLAIM_ATTEMPT = "RECLAIM_ATTEMPT"
    RECLAIM_SUCCEEDED = "RECLAIM_SUCCEEDED"
    RECLAIM_FAILED = "RECLAIM_FAILED"


class AdmissionStatus(StrEnum):
    ADMITTED = "ADMITTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    OUTSIDE_REQUIRED_WINDOW = "OUTSIDE_REQUIRED_WINDOW"


class MaturityStatus(StrEnum):
    PENDING = "PENDING"
    MATURE = "MATURE"
    GAPPED = "GAPPED"
    CONFLICTED = "CONFLICTED"
    DETACHED = "DETACHED"


class PathPrimaryResult(StrEnum):
    STOP_FIRST = "STOP_FIRST"
    TP_FIRST = "TP_FIRST"
    NO_HIT = "NO_HIT"


class ReclaimStatus(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def _positive_finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise OutcomeEngineError(f"{name} must be a positive finite Decimal")


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise OutcomeEngineError(f"{name} must be a non-empty exact identifier")


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass(frozen=True)
class FormalShadowView:
    """The narrow immutable plan view required by the outcome engine."""

    shadow_order_id: str
    market_id: str
    side: Side
    setup_family: SetupFamily
    outcome_start_ms: int
    planned_entry: Decimal
    stop: Decimal
    tp1: Decimal
    atr: Decimal
    tp2: Decimal | None = None
    zone_low: Decimal | None = None
    zone_high: Decimal | None = None
    state: ShadowState = ShadowState.FORMAL_SHADOW_PLAN
    active: bool = True

    def __post_init__(self) -> None:
        _identifier(self.shadow_order_id, "shadow_order_id")
        _identifier(self.market_id, "market_id")
        if isinstance(self.outcome_start_ms, bool) or self.outcome_start_ms < 0:
            raise OutcomeEngineError("outcome_start_ms must be non-negative")
        if self.outcome_start_ms % ONE_MINUTE_MS:
            raise OutcomeEngineError("outcome_start_ms must be on a closed 1m boundary")
        for name in ("planned_entry", "stop", "tp1", "atr"):
            _positive_finite(getattr(self, name), name)
        if self.tp2 is not None:
            _positive_finite(self.tp2, "tp2")
        if (self.zone_low is None) != (self.zone_high is None):
            raise OutcomeEngineError("zone bounds must be provided together")
        if self.zone_low is not None and self.zone_high is not None:
            _positive_finite(self.zone_low, "zone_low")
            _positive_finite(self.zone_high, "zone_high")
            if self.zone_low >= self.zone_high:
                raise OutcomeEngineError("zone_low must be below zone_high")
        if self.side is Side.LONG:
            valid = self.stop < self.planned_entry < self.tp1
            valid_tp2 = self.tp2 is None or self.tp2 >= self.tp1
        else:
            valid = self.tp1 < self.planned_entry < self.stop
            valid_tp2 = self.tp2 is None or self.tp2 <= self.tp1
        if not valid or not valid_tp2:
            raise OutcomeEngineError("stop and targets are invalid for side")

    @property
    def risk_distance(self) -> Decimal:
        return abs(self.planned_entry - self.stop)

    @property
    def original_deadline_ms(self) -> int:
        return self.outcome_start_ms + 120 * ONE_MINUTE_MS

    def r_level(self, multiple: Decimal) -> Decimal:
        distance = self.risk_distance * multiple
        if self.side is Side.LONG:
            return self.planned_entry + distance
        return self.planned_entry - distance


@dataclass(frozen=True)
class OneMinuteBar:
    """One authoritative closed 1m bar with stable evidence identity."""

    market_id: str
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    canonical_hash: str
    source_id: str = "PUBLIC_1M"

    @staticmethod
    def hash_payload(
        *,
        market_id: str,
        open_time_ms: int,
        close_time_ms: int,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
    ) -> str:
        fields = "|".join(
            (
                market_id,
                str(open_time_ms),
                str(close_time_ms),
                _decimal_text(open),
                _decimal_text(high),
                _decimal_text(low),
                _decimal_text(close),
            )
        )
        return hashlib.sha256(fields.encode()).hexdigest()

    def __post_init__(self) -> None:
        _identifier(self.market_id, "market_id")
        _identifier(self.source_id, "source_id")
        if (
            isinstance(self.open_time_ms, bool)
            or self.open_time_ms < 0
            or self.open_time_ms % ONE_MINUTE_MS
            or self.close_time_ms != self.open_time_ms + ONE_MINUTE_MS
        ):
            raise OutcomeEngineError("bar must cover one exact aligned minute")
        for name in ("open", "high", "low", "close"):
            _positive_finite(getattr(self, name), name)
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise OutcomeEngineError("bar OHLC range is invalid")
        if (
            not isinstance(self.canonical_hash, str)
            or len(self.canonical_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.canonical_hash)
        ):
            raise OutcomeEngineError("canonical_hash must be lowercase sha256 hex")
        expected = self.hash_payload(
            market_id=self.market_id,
            open_time_ms=self.open_time_ms,
            close_time_ms=self.close_time_ms,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
        )
        if self.canonical_hash != expected:
            raise OutcomeEngineError("canonical_hash does not bind normalized 1m bar")

    @classmethod
    def create(
        cls,
        *,
        market_id: str,
        open_time_ms: int,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        source_id: str = "PUBLIC_1M",
    ) -> OneMinuteBar:
        close_time_ms = open_time_ms + ONE_MINUTE_MS
        return cls(
            market_id=market_id,
            open_time_ms=open_time_ms,
            close_time_ms=close_time_ms,
            open=open,
            high=high,
            low=low,
            close=close,
            canonical_hash=cls.hash_payload(
                market_id=market_id,
                open_time_ms=open_time_ms,
                close_time_ms=close_time_ms,
                open=open,
                high=high,
                low=low,
                close=close,
            ),
            source_id=source_id,
        )


@dataclass(frozen=True)
class OutcomeTransitionView:
    """An existing strategy/event transition, never a new live signal."""

    transition_id: str
    shadow_order_id: str
    market_id: str
    kind: TransitionKind
    occurred_at_ms: int
    reference_price: Decimal | None = None

    def __post_init__(self) -> None:
        _identifier(self.transition_id, "transition_id")
        _identifier(self.shadow_order_id, "shadow_order_id")
        _identifier(self.market_id, "market_id")
        if isinstance(self.occurred_at_ms, bool) or self.occurred_at_ms < 0:
            raise OutcomeEngineError("occurred_at_ms must be non-negative")
        if self.occurred_at_ms % ONE_MINUTE_MS:
            raise OutcomeEngineError("occurred_at_ms must be on a closed 1m boundary")
        if self.reference_price is not None:
            _positive_finite(self.reference_price, "reference_price")


@dataclass(frozen=True)
class BarConflict:
    market_id: str
    open_time_ms: int
    retained_hash: str
    conflicting_hash: str


@dataclass(frozen=True)
class HorizonMetrics:
    horizon_minutes: int
    maturity: MaturityStatus
    window_end_ms: int
    mfe: Decimal | None
    mae: Decimal | None
    mfe_atr: Decimal | None
    mae_atr: Decimal | None
    one_r_hit: bool
    one_and_half_r_hit: bool
    two_r_hit: bool
    stop_hit: bool


@dataclass(frozen=True)
class ReverseHorizonMetrics:
    horizon_minutes: int
    maturity: MaturityStatus
    window_end_ms: int
    mfe: Decimal | None
    mae: Decimal | None
    mfe_atr: Decimal | None
    mae_atr: Decimal | None


@dataclass(frozen=True)
class PathEvaluation:
    primary_result: PathPrimaryResult
    ambiguous_path: bool
    ambiguous_bar_open_times: tuple[int, ...]
    stop_hit: bool
    stop_hit_time_ms: int | None
    tp1_hit: bool
    tp1_hit_time_ms: int | None
    tp2_hit: bool
    tp2_hit_time_ms: int | None
    one_r_hit: bool
    one_and_half_r_hit: bool
    two_r_hit: bool
    time_to_one_r_ms: int | None
    max_mfe_before_stop: Decimal
    max_profit_giveback: Decimal
    return_to_entry_after_profit: bool


@dataclass(frozen=True)
class FailedBreakoutResearch:
    failed_breakout: bool
    first_return_inside_range_time_ms: int | None
    return_inside_range_depth_atr: Decimal | None
    accepted_reentry_time_ms: int | None
    mfe_before_first_reentry: Decimal | None
    bars_outside_zone: int
    time_outside_zone_ms: int
    reclaim_attempt_count: int
    reclaim_status: ReclaimStatus
    mae_after_reentry: Decimal | None
    original_stop: Decimal
    original_r: Decimal
    original_stop_hit: bool
    reverse_anchor_time_ms: int | None
    reverse_entry: Decimal | None
    hypothetical_reverse: tuple[ReverseHorizonMetrics, ...]


@dataclass(frozen=True)
class FormalShadowOutcome:
    shadow_order_id: str
    market_id: str
    evaluated_at_ms: int
    required_start_ms: int
    original_deadline_ms: int
    required_end_ms: int
    path_maturity_status: MaturityStatus
    unresolved: bool
    horizons: tuple[HorizonMetrics, ...]
    path: PathEvaluation
    time_to_retest_ms: int | None
    return_inside_range: bool
    failed_breakout: bool
    research: FailedBreakoutResearch | None
    conflicts: tuple[BarConflict, ...]


@runtime_checkable
class OneMinuteProvider(Protocol):
    """Public 1m transport/backfill boundary used only for attached outcomes."""

    def subscribe_1m(self, *, market_id: str) -> None: ...

    def unsubscribe_1m(self, *, market_id: str) -> None: ...

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]: ...


@runtime_checkable
class OutcomeSink(Protocol):
    """Narrow persistence/output boundary; integration maps the record later."""

    def save_outcome(self, outcome: FormalShadowOutcome) -> None: ...
