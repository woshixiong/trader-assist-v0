# mypy: disable-error-code="import-not-found"
"""Causal readiness for provider-native completed historical bars."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import TYPE_CHECKING

from .contracts import WARMUP_5M_BARS, AdmittedEvent, DataKind

if TYPE_CHECKING:
    from nautilus_trader.model import Bar

FDML_REQUIRED_1M_BARS = 15
HISTORICAL_RESPONSE_TIMEOUT_NS = 300_000_000_000
MINUTE_NS = 60_000_000_000


def _valid_ohlcv(
    open_value: object,
    high_value: object,
    low_value: object,
    close_value: object,
    volume_value: object,
) -> bool:
    try:
        open_ = Decimal(str(open_value))
        high = Decimal(str(high_value))
        low = Decimal(str(low_value))
        close = Decimal(str(close_value))
        volume = Decimal(str(volume_value))
    except (InvalidOperation, ValueError):
        return False
    return (
        all(value.is_finite() for value in (open_, high, low, close, volume))
        and low <= min(open_, close)
        and high >= max(open_, close)
        and low <= high
        and volume >= 0
    )


class WarmupReadiness(StrEnum):
    NOT_READY = "NOT_READY"
    READY = "READY"


@dataclass
class WarmupStream:
    bar_type: str
    instrument_id: str
    duration_ns: int
    required: int
    cutoff_ns: int
    start_ns: int
    end_ns: int
    requested: bool = False
    request_id: str | None = None
    requested_at_ns: int | None = None
    received: int = 0
    readiness: WarmupReadiness = WarmupReadiness.NOT_READY
    reason: str = "NOT_REQUESTED"
    gap_count: int = 0

    @classmethod
    def create(
        cls, *, bar_type: str, instrument_id: str, minutes: int, cutoff_ns: int
    ) -> WarmupStream:
        if minutes not in (1, 5):
            raise ValueError("only frozen 1m and 5m history streams are supported")
        duration = minutes * MINUTE_NS
        required = FDML_REQUIRED_1M_BARS if minutes == 1 else WARMUP_5M_BARS
        end = cutoff_ns // duration * duration
        start = end - required * duration
        if start <= 0:
            raise ValueError("warm-up cutoff precedes required history window")
        return cls(bar_type, instrument_id, duration, required, cutoff_ns, start, end)

    @property
    def start(self) -> datetime:
        return datetime.fromtimestamp(self.start_ns / 1_000_000_000, UTC)

    @property
    def end(self) -> datetime:
        return datetime.fromtimestamp(self.end_ns / 1_000_000_000, UTC)

    def request_sent(self, request_id: str, now_ns: int) -> None:
        self.requested = True
        self.request_id = request_id
        self.requested_at_ns = now_ns
        self.reason = "AWAITING_NATIVE_RESPONSE"

    def fail(self, reason: str) -> None:
        self.readiness = WarmupReadiness.NOT_READY
        self.reason = reason

    def expire(self, now_ns: int) -> None:
        if (
            self.readiness is WarmupReadiness.NOT_READY
            and self.requested_at_ns is not None
            and now_ns - self.requested_at_ns >= HISTORICAL_RESPONSE_TIMEOUT_NS
            and self.reason == "AWAITING_NATIVE_RESPONSE"
        ):
            self.fail("NATIVE_RESPONSE_TIMEOUT")

    def validate(self, bars: Sequence[Bar]) -> tuple[Bar, ...]:
        """Validate the whole native response before any causal admission."""
        if not bars:
            self.fail("EMPTY_NATIVE_RESPONSE")
            return ()
        by_open: dict[int, Bar] = {}
        for bar in bars:
            if str(bar.bar_type) != self.bar_type:
                self.fail("WRONG_BAR_TYPE")
                return ()
            if str(getattr(bar.bar_type, "instrument_id", "")) != self.instrument_id:
                self.fail("WRONG_INSTRUMENT")
                return ()
            if (
                not isinstance(bar.ts_event, int)
                or not isinstance(bar.ts_init, int)
                or bar.ts_event < self.start_ns
                or bar.ts_event >= self.end_ns
                or bar.ts_event % self.duration_ns != 0
            ):
                self.fail("MALFORMED_OR_OUTSIDE_WINDOW")
                return ()
            close_boundary = bar.ts_event + self.duration_ns
            if (
                bar.ts_init < close_boundary
                or bar.ts_init > self.cutoff_ns
                or close_boundary > self.cutoff_ns
            ):
                self.fail("INCOMPLETE_OR_FUTURE_BAR")
                return ()
            if not _valid_ohlcv(bar.open, bar.high, bar.low, bar.close, bar.volume):
                self.fail("MALFORMED_BAR")
                return ()
            if bar.ts_event in by_open:
                self.fail("DUPLICATE_NATIVE_BAR")
                return ()
            by_open[bar.ts_event] = bar
        self.received = len(by_open)
        expected = set(range(self.start_ns, self.end_ns, self.duration_ns))
        self.gap_count = len(expected - by_open.keys())
        if self.gap_count:
            self.fail("GAPPED_OR_INSUFFICIENT_HISTORY")
            return ()
        return tuple(by_open[key] for key in sorted(by_open))

    def mark_durable(self) -> None:
        if self.received != self.required or self.gap_count:
            raise ValueError("warm-up cannot be ready without a complete window")
        self.readiness = WarmupReadiness.READY
        self.reason = "COMPLETE_DURABLE_HISTORY"

    def reconstruct(self, admissions: Sequence[AdmittedEvent]) -> None:
        relevant = [
            item.source
            for item in admissions
            if item.source.data_kind is DataKind.BAR
            and item.source.instrument_id == self.instrument_id
            and item.source.event_context == self.bar_type
            and self.start_ns <= item.source.ts_event < self.end_ns
        ]
        if any(
            source.payload.get("finalized") is not True
            or source.ts_event % self.duration_ns != 0
            or source.ts_init < source.ts_event + self.duration_ns
            or source.ts_init > self.cutoff_ns
            or not _valid_ohlcv(
                *(source.payload.get(key) for key in ("open", "high", "low", "close", "volume"))
            )
            for source in relevant
        ):
            self.fail("MALFORMED_DURABLE_BAR")
            return
        opens = {source.ts_event for source in relevant}
        self.received = len(opens)
        self.gap_count = len(set(range(self.start_ns, self.end_ns, self.duration_ns)) - opens)
        if not self.gap_count:
            self.mark_durable()
        else:
            self.fail("DURABLE_HISTORY_INCOMPLETE")

    def health(self) -> dict[str, object]:
        return {
            "bar_type": self.bar_type,
            "instrument_id": self.instrument_id,
            "readiness": self.readiness.value,
            "reason": self.reason,
            "requested": self.requested,
            "request_id": self.request_id,
            "received": self.received,
            "required": self.required,
            "cutoff_ns": self.cutoff_ns,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "gap_count": self.gap_count,
        }


class HistoricalWarmup:
    """One frozen cutoff and independent per-stream historical sufficiency."""

    def __init__(self, cutoff_ns: int, streams: Sequence[WarmupStream]) -> None:
        if cutoff_ns <= 0 or any(stream.cutoff_ns != cutoff_ns for stream in streams):
            raise ValueError("warm-up streams must share one positive cutoff")
        self.cutoff_ns = cutoff_ns
        self.streams = {stream.bar_type: stream for stream in streams}
        if len(self.streams) != len(streams):
            raise ValueError("duplicate warm-up bar type")

    @property
    def ready(self) -> bool:
        return bool(self.streams) and all(
            stream.readiness is WarmupReadiness.READY for stream in self.streams.values()
        )

    def health(self, now_ns: int) -> dict[str, object]:
        for stream in self.streams.values():
            stream.expire(now_ns)
        return {
            "readiness": (WarmupReadiness.READY if self.ready else WarmupReadiness.NOT_READY).value,
            "cutoff_ns": self.cutoff_ns,
            "streams": {key: stream.health() for key, stream in sorted(self.streams.items())},
        }
