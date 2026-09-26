from __future__ import annotations

from dataclasses import dataclass

import pytest

from trader_assist_v0.nautilus_e4.warmup import (
    FDML_REQUIRED_1M_BARS,
    HISTORICAL_RESPONSE_TIMEOUT_NS,
    MINUTE_NS,
    HistoricalWarmup,
    WarmupReadiness,
    WarmupStream,
)

CUTOFF = 1_000_000 * MINUTE_NS


@dataclass(frozen=True)
class _BarType:
    raw: str
    instrument_id: str = "ETH-PERP.HYPERLIQUID"

    def __str__(self) -> str:
        return self.raw


@dataclass(frozen=True)
class _Bar:
    bar_type: _BarType
    ts_event: int
    ts_init: int
    open: str = "100"
    high: str = "102"
    low: str = "99"
    close: str = "101"
    volume: str = "10"


def _stream(minutes: int) -> WarmupStream:
    return WarmupStream.create(
        bar_type=f"ETH-PERP.HYPERLIQUID-{minutes}-MINUTE-LAST-EXTERNAL",
        instrument_id="ETH-PERP.HYPERLIQUID",
        minutes=minutes,
        cutoff_ns=CUTOFF,
    )


def _bars(stream: WarmupStream) -> list[_Bar]:
    kind = _BarType(stream.bar_type)
    return [
        _Bar(kind, open_ns, open_ns + stream.duration_ns)
        for open_ns in range(stream.start_ns, stream.end_ns, stream.duration_ns)
    ]


@pytest.mark.parametrize("minutes,required", [(1, FDML_REQUIRED_1M_BARS), (5, 2304)])
def test_frozen_completed_window_and_threshold(minutes: int, required: int) -> None:
    stream = _stream(minutes)
    assert stream.required == required
    assert stream.end_ns <= CUTOFF
    assert stream.start_ns == stream.end_ns - required * stream.duration_ns
    assert stream.start.utcoffset().total_seconds() == 0
    assert stream.end.utcoffset().total_seconds() == 0
    stream.request_sent("native-id", CUTOFF)
    bars = _bars(stream)
    assert stream.validate(bars[:-1]) == ()
    assert stream.reason == "GAPPED_OR_INSUFFICIENT_HISTORY"
    assert stream.received == required - 1
    assert stream.readiness is WarmupReadiness.NOT_READY
    assert stream.validate(tuple(reversed(bars))) == tuple(bars)
    stream.mark_durable()
    assert stream.readiness is WarmupReadiness.READY


@pytest.mark.parametrize(
    "change,reason",
    [
        (
            lambda bar, stream: _Bar(bar.bar_type, bar.ts_event, bar.ts_event),
            "INCOMPLETE_OR_FUTURE_BAR",
        ),
        (
            lambda bar, stream: _Bar(bar.bar_type, bar.ts_event, stream.cutoff_ns + 1),
            "INCOMPLETE_OR_FUTURE_BAR",
        ),
        (
            lambda bar, stream: _Bar(
                bar.bar_type, stream.end_ns, stream.end_ns + stream.duration_ns
            ),
            "MALFORMED_OR_OUTSIDE_WINDOW",
        ),
        (lambda bar, stream: _Bar(_BarType("OTHER"), bar.ts_event, bar.ts_init), "WRONG_BAR_TYPE"),
        (
            lambda bar, stream: _Bar(bar.bar_type, bar.ts_event, bar.ts_init, high="98"),
            "MALFORMED_BAR",
        ),
    ],
)
def test_bad_native_batch_is_rejected_before_admission(change, reason: str) -> None:
    stream = _stream(1)
    bars = _bars(stream)
    bars[-1] = change(bars[-1], stream)
    assert stream.validate(bars) == ()
    assert stream.reason == reason
    assert stream.readiness is WarmupReadiness.NOT_READY


def test_one_cutoff_per_stream_and_native_timeout_health() -> None:
    one = _stream(1)
    five = _stream(5)
    warmup = HistoricalWarmup(CUTOFF, (one, five))
    assert warmup.health(CUTOFF)["readiness"] == "NOT_READY"
    one.request_sent("native-id", CUTOFF)
    one.expire(CUTOFF + HISTORICAL_RESPONSE_TIMEOUT_NS)
    assert one.reason == "NATIVE_RESPONSE_TIMEOUT"
    assert not warmup.ready
    with pytest.raises(ValueError, match="share one positive cutoff"):
        HistoricalWarmup(CUTOFF + MINUTE_NS, (one, five))
