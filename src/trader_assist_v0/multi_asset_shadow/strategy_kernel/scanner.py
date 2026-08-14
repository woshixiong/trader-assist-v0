"""Pure Scanner R3 cross-sectional discovery and candidate state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from itertools import pairwise
from math import ceil
from statistics import median

from .indicators import median_previous_20_volume, wilder_atr14
from .types import (
    PARAMETER_VERSION,
    SCANNER_VERSION,
    Bar,
    KernelInputError,
    ScannerChase,
    ScannerLinkage,
    ScannerState,
    Side,
)


@dataclass(frozen=True)
class ScannerMarketInput:
    market_id: str
    bars_5m: tuple[Bar, ...]
    minimum_tick: Decimal
    current_spread_price: Decimal
    liquidity_healthy: bool
    btc_returns: tuple[Decimal | None, Decimal | None, Decimal | None] = (
        None,
        None,
        None,
    )


@dataclass(frozen=True)
class ScannerMetrics:
    return_15m: Decimal
    return_30m: Decimal
    return_60m: Decimal
    relative_universe_15m: Decimal
    relative_universe_30m: Decimal
    relative_universe_60m: Decimal
    relative_btc_15m: Decimal | None
    relative_btc_30m: Decimal | None
    relative_btc_60m: Decimal | None
    move_atr_15m: Decimal
    move_atr_30m: Decimal
    move_atr_60m: Decimal
    relative_volume_5m: Decimal
    er_15m: Decimal
    er_30m: Decimal
    er_60m: Decimal
    prior_high_12: Decimal
    prior_low_12: Decimal
    prior_high_36: Decimal
    prior_low_36: Decimal


@dataclass(frozen=True)
class ScannerCandidate:
    candidate_id: str
    market_id: str
    side: Side | None
    state: ScannerState
    created_bar_open_time_ms: int
    breakout_bar_open_time_ms: int | None
    breakout_level: Decimal | None
    breakout_buffer: Decimal | None
    secondary_level_broken: bool
    retest_touch_bar_open_time_ms: int | None
    chase: ScannerChase | None
    chase_distance_atr: Decimal | None
    reason: str
    transitions: tuple[str, ...]
    scanner_version: str = SCANNER_VERSION
    parameter_version: str = PARAMETER_VERSION

    @property
    def linkage(self) -> ScannerLinkage:
        return ScannerLinkage(self.candidate_id, self.state)


@dataclass(frozen=True)
class ScannerObservation:
    market_id: str
    metrics: ScannerMetrics | None
    candidate: ScannerCandidate | None


def _returns(bars: tuple[Bar, ...]) -> tuple[Decimal, Decimal, Decimal]:
    if len(bars) < 13:
        raise KernelInputError("scanner returns require 13 closed 5m bars")
    current = bars[-1].close
    return tuple(current / bars[-1 - offset].close - 1 for offset in (3, 6, 12))  # type: ignore[return-value]


def _metrics(
    item: ScannerMarketInput,
    universe_medians: tuple[Decimal, Decimal, Decimal],
) -> ScannerMetrics:
    bars = item.bars_5m
    if len(bars) < 37:
        raise KernelInputError("scanner structure metrics require 37 closed bars")
    atr = wilder_atr14(bars)
    returns = _returns(bars)
    moves = tuple(
        abs(bars[-1].close - bars[-1 - offset].close) / atr for offset in (3, 6, 12)
    )
    m20 = median_previous_20_volume(bars)
    relative_volume = Decimal() if m20 == 0 else bars[-1].volume / m20
    previous_12 = bars[-13:-1]
    previous_36 = bars[-37:-1]
    relative_btc = tuple(
        None if btc is None else value - btc
        for value, btc in zip(returns, item.btc_returns, strict=True)
    )
    def efficiency(offset: int) -> Decimal:
        selected = bars[-1 - offset :]
        denominator = sum(
            (
                abs(right.close - left.close)
                for left, right in pairwise(selected)
            ),
            Decimal(),
        )
        if denominator == 0:
            return Decimal()
        return abs(selected[-1].close - selected[0].close) / denominator

    return ScannerMetrics(
        return_15m=returns[0],
        return_30m=returns[1],
        return_60m=returns[2],
        relative_universe_15m=returns[0] - universe_medians[0],
        relative_universe_30m=returns[1] - universe_medians[1],
        relative_universe_60m=returns[2] - universe_medians[2],
        relative_btc_15m=relative_btc[0],
        relative_btc_30m=relative_btc[1],
        relative_btc_60m=relative_btc[2],
        move_atr_15m=moves[0],
        move_atr_30m=moves[1],
        move_atr_60m=moves[2],
        relative_volume_5m=relative_volume,
        er_15m=efficiency(3),
        er_30m=efficiency(6),
        er_60m=efficiency(12),
        prior_high_12=max(value.high for value in previous_12),
        prior_low_12=min(value.low for value in previous_12),
        prior_high_36=max(value.high for value in previous_36),
        prior_low_36=min(value.low for value in previous_36),
    )


def _tail_members(
    values: dict[str, Decimal], fraction: Decimal
) -> tuple[set[str], set[str]]:
    count = max(1, ceil(len(values) * float(fraction)))
    ordered = sorted(values, key=lambda market_id: (values[market_id], market_id))
    return set(ordered[:count]), set(ordered[-count:])


def _candidate_id(
    *,
    market_id: str,
    side: Side | None,
    state: ScannerState,
    bar: Bar,
    level: Decimal | None,
) -> str:
    return sha256(
        (
            market_id
            + ("NO_DIRECTION" if side is None else side.value)
            + state.value
            + bar.candle_id
            + str(level)
            + SCANNER_VERSION
            + PARAMETER_VERSION
        ).encode("utf-8")
    ).hexdigest()


def _chase(distance: Decimal) -> ScannerChase:
    if distance <= Decimal("0.75"):
        return ScannerChase.EARLY
    if distance <= Decimal("1.50"):
        return ScannerChase.LATE
    return ScannerChase.REJECTED


def _breakout(
    item: ScannerMarketInput, metrics: ScannerMetrics, side: Side
) -> ScannerCandidate | None:
    current = item.bars_5m[-1]
    atr = wilder_atr14(item.bars_5m)
    buffer = max(
        Decimal("0.10") * atr,
        2 * item.current_spread_price,
        2 * item.minimum_tick,
    )
    level = metrics.prior_high_12 if side is Side.LONG else metrics.prior_low_12
    detected = (
        current.close > level + buffer
        if side is Side.LONG
        else current.close < level - buffer
    )
    if not detected:
        return None
    secondary = (
        current.close > metrics.prior_high_36 + buffer
        if side is Side.LONG
        else current.close < metrics.prior_low_36 - buffer
    )
    distance = abs(current.close - level) / atr
    chase = _chase(distance)
    state = (
        ScannerState.REJECTED_CHASE_FOR_ACTION
        if chase is ScannerChase.REJECTED
        else ScannerState.LATE_WATCH
        if chase is ScannerChase.LATE
        else ScannerState.BREAKOUT_DETECTED
    )
    return ScannerCandidate(
        candidate_id=_candidate_id(
            market_id=item.market_id,
            side=side,
            state=ScannerState.BREAKOUT_DETECTED,
            bar=current,
            level=level,
        ),
        market_id=item.market_id,
        side=side,
        state=state,
        created_bar_open_time_ms=current.open_time_ms,
        breakout_bar_open_time_ms=current.open_time_ms,
        breakout_level=level,
        breakout_buffer=buffer,
        secondary_level_broken=secondary,
        retest_touch_bar_open_time_ms=None,
        chase=chase,
        chase_distance_atr=distance,
        reason="BREAKOUT_DETECTED",
        transitions=(f"NEW->{state.value}",),
    )


def scan_cross_section(inputs: tuple[ScannerMarketInput, ...]) -> tuple[ScannerObservation, ...]:
    """Evaluate one closed-5m cadence without using any future universe data."""
    usable = [item for item in inputs if len(item.bars_5m) >= 64 and item.liquidity_healthy]
    return_maps: tuple[dict[str, Decimal], ...] = tuple(
        {
            item.market_id: _returns(item.bars_5m)[horizon]
            for item in usable
            if len(item.bars_5m) >= 13
        }
        for horizon in range(3)
    )
    medians = tuple(
        median(values.values()) if values else Decimal() for values in return_maps
    )
    tails_15 = tuple(_tail_members(values, Decimal("0.15")) for values in return_maps)
    tails_20 = tuple(_tail_members(values, Decimal("0.20")) for values in return_maps)
    observations: list[ScannerObservation] = []
    for item in sorted(inputs, key=lambda value: value.market_id):
        candidate: ScannerCandidate | None = None
        if len(item.bars_5m) < 64 or not item.liquidity_healthy:
            observations.append(ScannerObservation(item.market_id, None, None))
            continue
        if len(item.bars_5m) < 288:
            current = item.bars_5m[-1]
            state = ScannerState.WATCH_NEW_MARKET
            candidate = ScannerCandidate(
                candidate_id=_candidate_id(
                    market_id=item.market_id,
                    side=None,
                    state=state,
                    bar=current,
                    level=None,
                ),
                market_id=item.market_id,
                side=None,
                state=state,
                created_bar_open_time_ms=current.open_time_ms,
                breakout_bar_open_time_ms=None,
                breakout_level=None,
                breakout_buffer=None,
                secondary_level_broken=False,
                retest_touch_bar_open_time_ms=None,
                chase=None,
                chase_distance_atr=None,
                reason="HISTORY_64_TO_287",
                transitions=("NEW->WATCH_NEW_MARKET",),
            )
            observations.append(ScannerObservation(item.market_id, None, candidate))
            continue
        metrics = _metrics(item, medians)  # type: ignore[arg-type]
        long_rank = any(item.market_id in upper for _, upper in tails_15)
        short_rank = any(item.market_id in lower for lower, _ in tails_15)
        move_ready = (
            metrics.move_atr_15m >= Decimal("0.60")
            or metrics.move_atr_30m >= Decimal("0.90")
            or metrics.move_atr_60m >= Decimal("1.20")
        )
        if long_rank and move_ready:
            candidate = _breakout(item, metrics, Side.LONG)
        if candidate is None and short_rank and move_ready:
            candidate = _breakout(item, metrics, Side.SHORT)
        if candidate is None and (long_rank or short_rank) and move_ready:
            side = Side.LONG if long_rank else Side.SHORT
            current = item.bars_5m[-1]
            state = ScannerState.WATCH_MOMENTUM
            candidate = ScannerCandidate(
                candidate_id=_candidate_id(
                    market_id=item.market_id,
                    side=side,
                    state=state,
                    bar=current,
                    level=None,
                ),
                market_id=item.market_id,
                side=side,
                state=state,
                created_bar_open_time_ms=current.open_time_ms,
                breakout_bar_open_time_ms=None,
                breakout_level=None,
                breakout_buffer=None,
                secondary_level_broken=False,
                retest_touch_bar_open_time_ms=None,
                chase=None,
                chase_distance_atr=None,
                reason="TOP_OR_BOTTOM_15_PERCENT_AND_MOVE_ATR",
                transitions=("NEW->WATCH_MOMENTUM",),
            )
        if candidate is None:
            current = item.bars_5m[-1]
            atr = wilder_atr14(item.bars_5m)
            long_near = min(
                abs(current.close - metrics.prior_high_12),
                abs(current.close - metrics.prior_high_36),
            ) <= Decimal("0.35") * atr and any(
                item.market_id in upper for _, upper in tails_20
            )
            short_near = min(
                abs(current.close - metrics.prior_low_12),
                abs(current.close - metrics.prior_low_36),
            ) <= Decimal("0.35") * atr and any(
                item.market_id in lower for lower, _ in tails_20
            )
            if long_near or short_near:
                side = Side.LONG if long_near else Side.SHORT
                state = ScannerState.WATCH_NEAR_LEVEL
                level = metrics.prior_high_12 if long_near else metrics.prior_low_12
                candidate = ScannerCandidate(
                    candidate_id=_candidate_id(
                        market_id=item.market_id,
                        side=side,
                        state=state,
                        bar=current,
                        level=level,
                    ),
                    market_id=item.market_id,
                    side=side,
                    state=state,
                    created_bar_open_time_ms=current.open_time_ms,
                    breakout_bar_open_time_ms=None,
                    breakout_level=level,
                    breakout_buffer=None,
                    secondary_level_broken=False,
                    retest_touch_bar_open_time_ms=None,
                    chase=None,
                    chase_distance_atr=None,
                    reason="TOP_OR_BOTTOM_20_PERCENT_NEAR_LEVEL",
                    transitions=("NEW->WATCH_NEAR_LEVEL",),
                )
        observations.append(ScannerObservation(item.market_id, metrics, candidate))
    return tuple(observations)


def advance_scanner_candidate(
    candidate: ScannerCandidate,
    *,
    bars_5m: tuple[Bar, ...],
    current_spread_price: Decimal,
    liquidity_healthy: bool,
) -> ScannerCandidate:
    """Advance only the Scanner path; Formal events are intentionally untouched."""
    if candidate.breakout_bar_open_time_ms is None or candidate.breakout_level is None:
        return candidate
    if candidate.state in {
        ScannerState.BREAKOUT_RETEST_READY,
        ScannerState.FAILED_BREAKOUT_SWEEP_WATCH,
        ScannerState.FAILED_INVALIDATED_INSIDE_RANGE,
        ScannerState.EXPIRED_NO_RETEST,
    }:
        return candidate
    positions = {
        item.open_time_ms: index for index, item in enumerate(bars_5m)
    }
    if candidate.breakout_bar_open_time_ms not in positions:
        raise KernelInputError("scanner breakout bar is absent from history")
    breakout_index = positions[candidate.breakout_bar_open_time_ms]
    elapsed = len(bars_5m) - 1 - breakout_index
    if elapsed <= 0:
        return candidate
    current = bars_5m[-1]
    atr = wilder_atr14(bars_5m)
    level = candidate.breakout_level
    if candidate.side is None:
        raise KernelInputError("directionless WATCH cannot enter the breakout state machine")
    failed = (
        current.close <= level - Decimal("0.10") * atr
        if candidate.side is Side.LONG
        else current.close >= level + Decimal("0.10") * atr
    )
    if elapsed <= 6 and failed and liquidity_healthy:
        state = ScannerState.FAILED_BREAKOUT_SWEEP_WATCH
        return replace(
            candidate,
            state=state,
            reason="RETURNED_INSIDE_RANGE_AT_LEAST_0.10_ATR_WITHIN_1_TO_6",
            transitions=(*candidate.transitions, f"{candidate.state.value}->{state.value}"),
        )
    invalidated = (
        current.close <= level - Decimal("0.25") * atr
        if candidate.side is Side.LONG
        else current.close >= level + Decimal("0.25") * atr
    )
    if invalidated:
        state = ScannerState.FAILED_INVALIDATED_INSIDE_RANGE
        return replace(
            candidate,
            state=state,
            reason="INVALIDATION_INSIDE_RANGE_0.25_ATR",
            transitions=(*candidate.transitions, f"{candidate.state.value}->{state.value}"),
        )
    if elapsed > 12:
        state = ScannerState.EXPIRED_NO_RETEST
        return replace(
            candidate,
            state=state,
            reason="SCANNER_RETEST_WINDOW_ENDED",
            transitions=(*candidate.transitions, f"{candidate.state.value}->{state.value}"),
        )
    half_width = max(Decimal("0.25") * atr, 2 * current_spread_price)
    touched = current.low <= level + half_width and current.high >= level - half_width
    touch_time = candidate.retest_touch_bar_open_time_ms
    if touch_time is None and touched:
        touch_time = current.open_time_ms
    distance = abs(current.close - level) / atr
    chase = _chase(distance)
    after_touch = touch_time is not None and current.open_time_ms > touch_time
    direction_confirmed = (
        current.close > level if candidate.side is Side.LONG else current.close < level
    )
    if (
        after_touch
        and direction_confirmed
        and chase is not ScannerChase.REJECTED
        and liquidity_healthy
    ):
        state = ScannerState.BREAKOUT_RETEST_READY
        reason = (
            "RETEST_CONFIRMED"
            if chase is ScannerChase.EARLY
            else "RETEST_CONFIRMED_DO_NOT_CHASE"
        )
    elif chase is ScannerChase.REJECTED:
        state = ScannerState.REJECTED_CHASE_FOR_ACTION
        reason = "CHASE_DISTANCE_ABOVE_1.50_ATR"
    elif chase is ScannerChase.LATE:
        state = ScannerState.LATE_WATCH
        reason = "CHASE_DISTANCE_ABOVE_0.75_ATR_DO_NOT_CHASE"
    else:
        state = ScannerState.RETEST_PENDING
        reason = (
            "RETEST_TOUCH_PENDING_CONFIRMATION"
            if touch_time is not None
            else "RETEST_NOT_TOUCHED"
        )
    transition = f"{candidate.state.value}->{state.value}"
    return replace(
        candidate,
        state=state,
        retest_touch_bar_open_time_ms=touch_time,
        chase=chase,
        chase_distance_atr=distance,
        reason=reason,
        transitions=(
            candidate.transitions
            if state is candidate.state
            else (*candidate.transitions, transition)
        ),
    )
