from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from typing import Final

from .contracts import (
    BBO,
    STATE_SCHEMA_VERSION,
    AggressorSide,
    CompletedBar,
    FreshnessResult,
    L2Level,
    L2Snapshot,
    MarketIdentity,
    PublicTrade,
)

WINDOW_SECONDS: Final = (5, 15, 60)
RETURN_MINUTES: Final = (5, 15, 30, 60, 120)
ACTIVITY_BASELINE_SECONDS: Final = 300
ACTIVITY_RATIO_CAP: Final = 10.0


@dataclass(frozen=True, slots=True)
class DepthLevelFeature:
    price: float
    size: float
    notional: float
    distance_from_mid_bps: float
    cumulative_notional: float


@dataclass(frozen=True, slots=True)
class DepthFeatures:
    bids: tuple[DepthLevelFeature, ...]
    asks: tuple[DepthLevelFeature, ...]
    top1_imbalance: float
    top5_imbalance: float
    cumulative_bid_notional: float
    cumulative_ask_notional: float


@dataclass(frozen=True, slots=True)
class TradeFlowWindow:
    seconds: int
    aggressive_buy_notional: float
    aggressive_sell_notional: float
    normalized_imbalance: float
    trade_count: int
    total_notional: float
    executable_bid_response_bps: float
    executable_ask_response_bps: float


@dataclass(frozen=True, slots=True)
class StateSchemaV0:
    market: MarketIdentity
    data_cutoff_ns: int
    bbo: BBO
    l2: L2Snapshot
    depth: DepthFeatures
    trade_flow: tuple[TradeFlowWindow, ...]
    one_minute_bars: tuple[CompletedBar, ...]
    five_minute_bars: tuple[CompletedBar, ...]
    returns: tuple[tuple[str, float], ...]
    structure_distances_bps: tuple[tuple[str, float], ...]
    reference_distances_bps: tuple[tuple[str, float], ...]
    atr_1m_bps: float
    atr_5m_bps: float
    realized_volatility_bps: float
    activity_ratio: float
    freshness: FreshnessResult
    snapshot_hash: str
    snapshot_id: str

    def compact_payload(self) -> dict[str, object]:
        payload = _payload_without_hash(self)
        payload["snapshot_hash"] = self.snapshot_hash
        payload["snapshot_id"] = self.snapshot_id
        return payload


def _level_features(levels: tuple[L2Level, ...], mid: float) -> tuple[DepthLevelFeature, ...]:
    cumulative = 0.0
    output: list[DepthLevelFeature] = []
    for level in levels:
        notional = level.price * level.size
        cumulative += notional
        output.append(
            DepthLevelFeature(
                price=level.price,
                size=level.size,
                notional=notional,
                distance_from_mid_bps=(level.price - mid) / mid * 10_000.0,
                cumulative_notional=cumulative,
            )
        )
    return tuple(output)


def depth_features(snapshot: L2Snapshot, bbo: BBO) -> DepthFeatures:
    if snapshot.bids[0].price != bbo.bid_price or snapshot.asks[0].price != bbo.ask_price:
        raise ValueError("L2 top-of-book must match the normalized BBO")
    bids = _level_features(snapshot.bids, bbo.mid)
    asks = _level_features(snapshot.asks, bbo.mid)
    bid1 = bids[0].notional
    ask1 = asks[0].notional
    bid5 = bids[-1].cumulative_notional
    ask5 = asks[-1].cumulative_notional
    return DepthFeatures(
        bids=bids,
        asks=asks,
        top1_imbalance=_imbalance(bid1, ask1),
        top5_imbalance=_imbalance(bid5, ask5),
        cumulative_bid_notional=bid5,
        cumulative_ask_notional=ask5,
    )


def _imbalance(left: float, right: float) -> float:
    total = left + right
    return 0.0 if total == 0 else (left - right) / total


def _validate_causal_trades(trades: tuple[PublicTrade, ...], cutoff_ns: int) -> None:
    previous = -1
    for trade in trades:
        if trade.ts_ns > cutoff_ns:
            raise ValueError("future trade cannot enter a causal state snapshot")
        if trade.ts_ns < previous:
            raise ValueError("trades must be ordered by non-decreasing timestamp")
        previous = trade.ts_ns


def trade_flow_windows(
    trades: tuple[PublicTrade, ...], cutoff_ns: int, bbo: BBO
) -> tuple[TradeFlowWindow, ...]:
    _validate_causal_trades(trades, cutoff_ns)
    output: list[TradeFlowWindow] = []
    for seconds in WINDOW_SECONDS:
        start_ns = cutoff_ns - seconds * 1_000_000_000
        window = tuple(trade for trade in trades if start_ns <= trade.ts_ns <= cutoff_ns)
        buys = sum(trade.notional for trade in window if trade.aggressor_side is AggressorSide.BUY)
        sells = sum(
            trade.notional for trade in window if trade.aggressor_side is AggressorSide.SELL
        )
        bid_response = 0.0
        ask_response = 0.0
        if window:
            first_price = window[0].price
            bid_response = (bbo.bid_price - first_price) / first_price * 10_000.0
            ask_response = (bbo.ask_price - first_price) / first_price * 10_000.0
        output.append(
            TradeFlowWindow(
                seconds=seconds,
                aggressive_buy_notional=buys,
                aggressive_sell_notional=sells,
                normalized_imbalance=_imbalance(buys, sells),
                trade_count=len(window),
                total_notional=buys + sells,
                executable_bid_response_bps=bid_response,
                executable_ask_response_bps=ask_response,
            )
        )
    return tuple(output)


def _validate_bars(bars: tuple[CompletedBar, ...], interval: int, cutoff_ns: int) -> None:
    previous = -1
    for bar in bars:
        if bar.interval_seconds != interval:
            raise ValueError(f"expected only {interval}-second bars")
        if bar.close_ts_ns > cutoff_ns:
            raise ValueError("future bar cannot enter a causal state snapshot")
        if bar.close_ts_ns <= previous:
            raise ValueError("completed bars must be strictly ordered by close timestamp")
        previous = bar.close_ts_ns


def _return_for_minutes(five_minute_bars: tuple[CompletedBar, ...], minutes: int) -> float:
    periods = minutes // 5
    if len(five_minute_bars) <= periods:
        raise ValueError(
            f"at least {periods + 1} completed 5m bars are required for {minutes}m return"
        )
    current = five_minute_bars[-1].close
    reference = five_minute_bars[-(periods + 1)].close
    return current / reference - 1.0


def _atr_bps(bars: tuple[CompletedBar, ...], periods: int = 14) -> float:
    if len(bars) < periods + 1:
        raise ValueError(f"at least {periods + 1} bars are required for ATR{periods}")
    selected = bars[-periods:]
    previous_close = bars[-(periods + 1)].close
    true_ranges: list[float] = []
    for bar in selected:
        true_ranges.append(
            max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))
        )
        previous_close = bar.close
    return statistics.fmean(true_ranges) / bars[-1].close * 10_000.0


def _realized_volatility_bps(bars: tuple[CompletedBar, ...], periods: int = 10) -> float:
    if len(bars) < periods + 1:
        raise ValueError(f"at least {periods + 1} bars are required for realized volatility")
    closes = [bar.close for bar in bars[-(periods + 1) :]]
    returns = [math.log(closes[index] / closes[index - 1]) for index in range(1, len(closes))]
    return statistics.pstdev(returns) * 10_000.0


def _activity_ratio(trades: tuple[PublicTrade, ...], cutoff_ns: int) -> float:
    recent_start = cutoff_ns - 60 * 1_000_000_000
    baseline_start = cutoff_ns - ACTIVITY_BASELINE_SECONDS * 1_000_000_000
    recent = sum(t.notional for t in trades if recent_start <= t.ts_ns <= cutoff_ns)
    baseline = sum(t.notional for t in trades if baseline_start <= t.ts_ns < recent_start)
    baseline_per_minute = baseline / ((ACTIVITY_BASELINE_SECONDS - 60) / 60)
    if baseline_per_minute == 0:
        return ACTIVITY_RATIO_CAP if recent > 0 else 0.0
    return min(ACTIVITY_RATIO_CAP, recent / baseline_per_minute)


def _distance_bps(reference: float, mid: float) -> float:
    return (reference - mid) / mid * 10_000.0


def _structure(
    one_minute: tuple[CompletedBar, ...], five_minute: tuple[CompletedBar, ...], mid: float
) -> tuple[tuple[str, float], ...]:
    recent_1m = one_minute[-10:]
    recent_5m = five_minute[-12:]
    return (
        ("one_minute_recent_high", _distance_bps(max(bar.high for bar in recent_1m), mid)),
        ("one_minute_recent_low", _distance_bps(min(bar.low for bar in recent_1m), mid)),
        ("five_minute_recent_high", _distance_bps(max(bar.high for bar in recent_5m), mid)),
        ("five_minute_recent_low", _distance_bps(min(bar.low for bar in recent_5m), mid)),
    )


def _references(five_minute: tuple[CompletedBar, ...], mid: float) -> tuple[tuple[str, float], ...]:
    prior = five_minute[-2]
    return (
        ("prior_5m_high", _distance_bps(prior.high, mid)),
        ("prior_5m_low", _distance_bps(prior.low, mid)),
        ("prior_5m_close", _distance_bps(prior.close, mid)),
    )


def canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def canonical_sha256(payload: dict[str, object]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _bar_payload(bar: CompletedBar) -> dict[str, object]:
    return {
        "interval_seconds": bar.interval_seconds,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "close_ts_ns": bar.close_ts_ns,
    }


def _payload_without_hash(state: StateSchemaV0) -> dict[str, object]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "market": asdict(state.market),
        "data_cutoff_ns": state.data_cutoff_ns,
        "bbo": {
            "bid_price": state.bbo.bid_price,
            "bid_size": state.bbo.bid_size,
            "ask_price": state.bbo.ask_price,
            "ask_size": state.bbo.ask_size,
            "mid": state.bbo.mid,
            "spread_bps": state.bbo.spread_bps,
            "source_ts_ns": state.bbo.source_ts_ns,
            "admitted_ts_ns": state.bbo.admitted_ts_ns,
            "continuity_valid": state.bbo.continuity_valid,
        },
        "l2": {
            "source_ts_ns": state.l2.source_ts_ns,
            "admitted_ts_ns": state.l2.admitted_ts_ns,
            "provenance": state.l2.provenance,
            "bids": [asdict(level) for level in state.depth.bids],
            "asks": [asdict(level) for level in state.depth.asks],
            "top1_imbalance": state.depth.top1_imbalance,
            "top5_imbalance": state.depth.top5_imbalance,
            "cumulative_bid_notional": state.depth.cumulative_bid_notional,
            "cumulative_ask_notional": state.depth.cumulative_ask_notional,
        },
        "trade_flow": [asdict(window) for window in state.trade_flow],
        "one_minute_bars": [_bar_payload(bar) for bar in state.one_minute_bars],
        "five_minute_bars": [_bar_payload(bar) for bar in state.five_minute_bars],
        "returns": dict(state.returns),
        "structure_distances_bps": dict(state.structure_distances_bps),
        "reference_distances_bps": dict(state.reference_distances_bps),
        "atr_1m_bps": state.atr_1m_bps,
        "atr_5m_bps": state.atr_5m_bps,
        "realized_volatility_bps": state.realized_volatility_bps,
        "activity_ratio": state.activity_ratio,
        "freshness": {
            "valid": state.freshness.valid,
            "reasons": [reason.value for reason in state.freshness.reasons],
            "l2_age_seconds": state.freshness.l2_age_seconds,
            "one_minute_age_seconds": state.freshness.one_minute_age_seconds,
            "five_minute_age_seconds": state.freshness.five_minute_age_seconds,
            "active_context_age_seconds": state.freshness.active_context_age_seconds,
            "metadata_age_seconds": state.freshness.metadata_age_seconds,
            "bbo_value_age_seconds": state.freshness.bbo_value_age_seconds,
            "latest_trade_age_seconds": state.freshness.latest_trade_age_seconds,
        },
    }


def build_state_schema_v0(
    *,
    market: MarketIdentity,
    cutoff_ns: int,
    bbo: BBO,
    l2: L2Snapshot,
    trades: tuple[PublicTrade, ...],
    one_minute_bars: tuple[CompletedBar, ...],
    five_minute_bars: tuple[CompletedBar, ...],
    freshness: FreshnessResult,
) -> StateSchemaV0:
    if cutoff_ns < 0:
        raise ValueError("cutoff_ns must be non-negative")
    if bbo.source_ts_ns > cutoff_ns or bbo.admitted_ts_ns > cutoff_ns:
        raise ValueError("future BBO cannot enter a causal state snapshot")
    if l2.source_ts_ns > cutoff_ns or l2.admitted_ts_ns > cutoff_ns:
        raise ValueError("future L2 cannot enter a causal state snapshot")
    _validate_causal_trades(trades, cutoff_ns)
    _validate_bars(one_minute_bars, 60, cutoff_ns)
    _validate_bars(five_minute_bars, 300, cutoff_ns)
    if len(one_minute_bars) < 15 or len(five_minute_bars) < 25:
        raise ValueError("STATE_SCHEMA_V0 requires >=15 completed 1m and >=25 completed 5m bars")

    depth = depth_features(l2, bbo)
    flow = trade_flow_windows(trades, cutoff_ns, bbo)
    returns = tuple(
        (f"{minutes}m", _return_for_minutes(five_minute_bars, minutes))
        for minutes in RETURN_MINUTES
    )
    partial = StateSchemaV0(
        market=market,
        data_cutoff_ns=cutoff_ns,
        bbo=bbo,
        l2=l2,
        depth=depth,
        trade_flow=flow,
        one_minute_bars=one_minute_bars[-10:],
        five_minute_bars=five_minute_bars[-12:],
        returns=returns,
        structure_distances_bps=_structure(one_minute_bars, five_minute_bars, bbo.mid),
        reference_distances_bps=_references(five_minute_bars, bbo.mid),
        atr_1m_bps=_atr_bps(one_minute_bars),
        atr_5m_bps=_atr_bps(five_minute_bars),
        realized_volatility_bps=_realized_volatility_bps(one_minute_bars),
        activity_ratio=_activity_ratio(trades, cutoff_ns),
        freshness=freshness,
        snapshot_hash="",
        snapshot_id="",
    )
    digest = canonical_sha256(_payload_without_hash(partial))
    return StateSchemaV0(
        market=partial.market,
        data_cutoff_ns=partial.data_cutoff_ns,
        bbo=partial.bbo,
        l2=partial.l2,
        depth=partial.depth,
        trade_flow=partial.trade_flow,
        one_minute_bars=partial.one_minute_bars,
        five_minute_bars=partial.five_minute_bars,
        returns=partial.returns,
        structure_distances_bps=partial.structure_distances_bps,
        reference_distances_bps=partial.reference_distances_bps,
        atr_1m_bps=partial.atr_1m_bps,
        atr_5m_bps=partial.atr_5m_bps,
        realized_volatility_bps=partial.realized_volatility_bps,
        activity_ratio=partial.activity_ratio,
        freshness=partial.freshness,
        snapshot_hash=digest,
        snapshot_id=f"sha256:{digest}",
    )
