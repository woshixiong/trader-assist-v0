"""Causal aggregation and frozen indicator semantics."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from itertools import pairwise
from statistics import median

from .types import (
    Bar,
    HtfContext,
    HtfMomentum,
    HtfRelation,
    HtfStructure,
    KernelInputError,
    Side,
)

FIVE_MINUTES_MS = 300_000


def validate_series(bars: Sequence[Bar], *, interval: str | None = None) -> None:
    if not bars:
        raise KernelInputError("bar history is empty")
    market_id = bars[0].market_id
    expected_interval = interval or bars[0].interval
    interval_ms = {"5m": FIVE_MINUTES_MS, "15m": 900_000, "1h": 3_600_000}[
        expected_interval
    ]
    previous_open: int | None = None
    for item in bars:
        if item.market_id != market_id or item.interval != expected_interval:
            raise KernelInputError("bar history identity is inconsistent")
        if item.open_time_ms % interval_ms != 0:
            raise KernelInputError("bar history is not UTC-aligned")
        if previous_open is not None and item.open_time_ms != previous_open + interval_ms:
            raise KernelInputError("bar history has a gap or overlap")
        previous_open = item.open_time_ms


def aggregate_closed_5m_causally(bars: Sequence[Bar], *, minutes: int) -> tuple[Bar, ...]:
    """Aggregate only complete UTC-aligned buckets from a closed 5m sequence."""
    if minutes not in {15, 60}:
        raise KernelInputError("only local 15m and 1h aggregation is frozen")
    validate_series(bars, interval="5m")
    for left, right in pairwise(bars):
        if right.open_time_ms != left.open_time_ms + FIVE_MINUTES_MS:
            raise KernelInputError("5m history has a gap")

    bucket_ms = minutes * 60_000
    required = minutes // 5
    grouped: dict[int, list[Bar]] = {}
    for item in bars:
        bucket = item.open_time_ms - item.open_time_ms % bucket_ms
        grouped.setdefault(bucket, []).append(item)

    output: list[Bar] = []
    interval = "15m" if minutes == 15 else "1h"
    for bucket, members in sorted(grouped.items()):
        expected_opens = [bucket + index * FIVE_MINUTES_MS for index in range(required)]
        if [item.open_time_ms for item in members] != expected_opens:
            # Prefix/suffix partial buckets are not visible yet.  An internal
            # partial bucket would imply a gap, already rejected above.
            continue
        output.append(
            Bar(
                market_id=members[0].market_id,
                interval=interval,
                open_time_ms=bucket,
                close_time_ms=members[-1].close_time_ms,
                open=members[0].open,
                high=max(item.high for item in members),
                low=min(item.low for item in members),
                close=members[-1].close,
                volume=sum((item.volume for item in members), Decimal()),
                source_identity="CAUSAL_LOCAL_FROM_CLOSED_5M",
            )
        )
    return tuple(output)


def true_range(current: Bar, previous_close: Decimal) -> Decimal:
    return max(
        current.high - current.low,
        abs(current.high - previous_close),
        abs(current.low - previous_close),
    )


def wilder_atr14_series(bars: Sequence[Bar]) -> tuple[Decimal | None, ...]:
    """Return ATR aligned to each bar; the first available value is index 14."""
    validate_series(bars)
    values: list[Decimal | None] = [None] * len(bars)
    if len(bars) < 15:
        return tuple(values)
    ranges = [true_range(bars[index], bars[index - 1].close) for index in range(1, len(bars))]
    seed = sum(ranges[:14], Decimal()) / Decimal(14)
    if not seed.is_finite() or seed <= 0:
        return tuple(values)
    values[14] = seed
    current = seed
    for bar_index in range(15, len(bars)):
        current = (Decimal(13) * current + ranges[bar_index - 1]) / Decimal(14)
        values[bar_index] = current if current.is_finite() and current > 0 else None
    return tuple(values)


def wilder_atr14(bars: Sequence[Bar]) -> Decimal:
    value = wilder_atr14_series(bars)[-1]
    if value is None:
        raise KernelInputError("ATR14 requires at least 15 valid closed bars")
    return value


def median_previous_20_volume(bars: Sequence[Bar]) -> Decimal:
    """M20 excludes the current evaluation/trigger bar."""
    validate_series(bars)
    if len(bars) < 21:
        raise KernelInputError("M20 requires 20 bars before the current bar")
    value = median(item.volume for item in bars[-21:-1])
    if not value.is_finite() or value < 0:
        raise KernelInputError("M20 is invalid")
    return value


def clv_long(bar: Bar) -> Decimal:
    span = bar.high - bar.low
    if span <= 0:
        raise KernelInputError("CLV requires a positive candle range")
    return (bar.close - bar.low) / span


def clv_short(bar: Bar) -> Decimal:
    span = bar.high - bar.low
    if span <= 0:
        raise KernelInputError("CLV requires a positive candle range")
    return (bar.high - bar.close) / span


def directional_efficiency_8(bars: Sequence[Bar]) -> Decimal:
    validate_series(bars)
    if len(bars) < 9:
        raise KernelInputError("ER8 requires 9 closed bars")
    selected = bars[-9:]
    denominator = sum(
        (abs(right.close - left.close) for left, right in pairwise(selected)), Decimal()
    )
    if denominator == 0:
        return Decimal()
    return abs(selected[-1].close - selected[0].close) / denominator


def directional_move_8(bars: Sequence[Bar], atr: Decimal) -> Decimal:
    validate_series(bars)
    if len(bars) < 9 or not atr.is_finite() or atr <= 0:
        raise KernelInputError("D8 requires 9 bars and positive ATR")
    return (bars[-1].close - bars[-9].close) / atr


def causal_pivot_high_indices(bars: Sequence[Bar]) -> tuple[int, ...]:
    validate_series(bars)
    return tuple(
        index
        for index in range(1, len(bars) - 1)
        if bars[index].high > bars[index - 1].high
        and bars[index].high >= bars[index + 1].high
    )


def causal_pivot_low_indices(bars: Sequence[Bar]) -> tuple[int, ...]:
    validate_series(bars)
    return tuple(
        index
        for index in range(1, len(bars) - 1)
        if bars[index].low < bars[index - 1].low and bars[index].low <= bars[index + 1].low
    )


def htf_context(bars_1h: Sequence[Bar]) -> HtfContext:
    if not bars_1h:
        return HtfContext(
            HtfMomentum.UNAVAILABLE, HtfStructure.UNAVAILABLE, None, None
        )
    validate_series(bars_1h, interval="1h")
    atr_values = wilder_atr14_series(bars_1h)
    a1h = atr_values[-1]
    if a1h is None or len(bars_1h) < 9:
        return HtfContext(
            HtfMomentum.UNAVAILABLE, HtfStructure.UNAVAILABLE, None, None
        )
    er8 = directional_efficiency_8(bars_1h)
    d8 = directional_move_8(bars_1h, a1h)
    if er8 >= Decimal("0.35") and d8 >= Decimal("0.75"):
        momentum = HtfMomentum.UP
    elif er8 >= Decimal("0.35") and d8 <= Decimal("-0.75"):
        momentum = HtfMomentum.DOWN
    else:
        momentum = HtfMomentum.NEUTRAL

    highs = causal_pivot_high_indices(bars_1h)
    lows = causal_pivot_low_indices(bars_1h)
    if len(highs) < 2 or len(lows) < 2:
        structure = HtfStructure.INSUFFICIENT
    else:
        epsilon = Decimal("0.10") * a1h
        first_high, second_high = (bars_1h[index].high for index in highs[-2:])
        first_low, second_low = (bars_1h[index].low for index in lows[-2:])
        high_state = (
            "HH"
            if second_high > first_high + epsilon
            else "LH"
            if second_high < first_high - epsilon
            else "EH"
        )
        low_state = (
            "HL"
            if second_low > first_low + epsilon
            else "LL"
            if second_low < first_low - epsilon
            else "EL"
        )
        if high_state == "HH" and low_state == "HL":
            structure = HtfStructure.UP
        elif high_state == "LH" and low_state == "LL":
            structure = HtfStructure.DOWN
        elif high_state in {"LH", "EH"} and low_state in {"HL", "EL"}:
            structure = HtfStructure.RANGE
        else:
            structure = HtfStructure.TRANSITION
    return HtfContext(momentum, structure, er8, d8)


def htf_relation(context: HtfContext, side: Side) -> HtfRelation:
    if context.momentum is HtfMomentum.UNAVAILABLE or context.structure is HtfStructure.UNAVAILABLE:
        return HtfRelation.CONTEXT_INCOMPLETE
    momentum_direction = {
        HtfMomentum.UP: 1,
        HtfMomentum.DOWN: -1,
        HtfMomentum.NEUTRAL: 0,
        HtfMomentum.UNAVAILABLE: 0,
    }[context.momentum]
    structure_direction = {
        HtfStructure.UP: 1,
        HtfStructure.DOWN: -1,
        HtfStructure.RANGE: 0,
        HtfStructure.TRANSITION: 0,
        HtfStructure.INSUFFICIENT: 0,
        HtfStructure.UNAVAILABLE: 0,
    }[context.structure]
    signal_direction = 1 if side is Side.LONG else -1
    pair = (momentum_direction, structure_direction)
    if pair == (signal_direction, signal_direction):
        return HtfRelation.ALIGNED_STRONG
    if signal_direction in pair and 0 in pair:
        return HtfRelation.ALIGNED_PARTIAL
    if pair == (-signal_direction, -signal_direction):
        return HtfRelation.COUNTERTREND_STRONG
    if -signal_direction in pair and 0 in pair:
        return HtfRelation.COUNTERTREND_PARTIAL
    if signal_direction in pair and -signal_direction in pair:
        return HtfRelation.CONFLICTED
    return HtfRelation.NEUTRAL
