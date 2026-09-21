from __future__ import annotations

from dataclasses import replace

import pytest

from trader_assist_v0.jev.contracts import (
    AggressorSide,
    BBO,
    CompletedBar,
    FreshnessInputs,
    L2Level,
    L2Snapshot,
    MarketIdentity,
    PublicTrade,
    evaluate_freshness,
)
from trader_assist_v0.jev.features import build_state_schema_v0, canonical_json

NANO = 1_000_000_000


def _bar(interval: int, index: int, cutoff_ns: int) -> CompletedBar:
    close_ts = cutoff_ns - (30 - index) * interval * NANO
    base = 100.0 + index * 0.1
    return CompletedBar(interval, base, base + 1.0, base - 1.0, base + 0.2, 10.0 + index, close_ts)


def _inputs() -> dict[str, object]:
    cutoff = 10_000 * NANO
    market = MarketIdentity("ABC", "provider", "ABC-PERP")
    bbo = BBO(102.0, 5.0, 102.1, 6.0, cutoff - NANO, cutoff - NANO // 2, True)
    bids = tuple(L2Level(102.0 - index * 0.1, 5.0 + index) for index in range(5))
    asks = tuple(L2Level(102.1 + index * 0.1, 6.0 + index) for index in range(5))
    l2 = L2Snapshot(bids, asks, cutoff - NANO, cutoff - NANO // 2, "public-l2")
    trades = tuple(
        PublicTrade(
            cutoff - (240 - index * 10) * NANO,
            101.0 + index * 0.05,
            1.0 + index * 0.01,
            AggressorSide.BUY if index % 2 == 0 else AggressorSide.SELL,
        )
        for index in range(25)
    )
    one = tuple(_bar(60, index, cutoff) for index in range(31))
    five = tuple(_bar(300, index, cutoff) for index in range(31))
    freshness = evaluate_freshness(
        cutoff,
        FreshnessInputs(
            l2_source_ts_ns=cutoff - NANO,
            latest_1m_close_ts_ns=one[-1].close_ts_ns,
            latest_5m_close_ts_ns=five[-1].close_ts_ns,
            optional_active_context_ts_ns=cutoff - NANO,
            metadata_ts_ns=cutoff - NANO,
            bbo_value_ts_ns=cutoff - 20 * NANO,
            latest_trade_ts_ns=trades[-1].ts_ns,
        ),
    )
    return {
        "market": market,
        "cutoff_ns": cutoff,
        "bbo": bbo,
        "l2": l2,
        "trades": trades,
        "one_minute_bars": one,
        "five_minute_bars": five,
        "freshness": freshness,
    }


def test_state_hash_and_payload_are_deterministic() -> None:
    inputs = _inputs()
    first = build_state_schema_v0(**inputs)
    second = build_state_schema_v0(**inputs)
    assert first.snapshot_hash == second.snapshot_hash
    assert first.snapshot_id == f"sha256:{first.snapshot_hash}"
    assert canonical_json(first.compact_payload()) == canonical_json(second.compact_payload())
    assert len(first.one_minute_bars) == 10
    assert len(first.five_minute_bars) == 12
    assert dict(first.returns).keys() == {"5m", "15m", "30m", "60m", "120m"}


def test_trade_windows_are_causal_and_future_trade_fails() -> None:
    inputs = _inputs()
    state = build_state_schema_v0(**inputs)
    assert tuple(window.seconds for window in state.trade_flow) == (5, 15, 60)
    future = PublicTrade(inputs["cutoff_ns"] + 1, 102.0, 1.0, AggressorSide.BUY)
    changed = dict(inputs)
    changed["trades"] = inputs["trades"] + (future,)
    with pytest.raises(ValueError, match="future trade"):
        build_state_schema_v0(**changed)


def test_incomplete_or_future_bar_is_rejected() -> None:
    inputs = _inputs()
    last = inputs["one_minute_bars"][-1]
    with pytest.raises(ValueError, match="bar must be completed"):
        replace(last, completed=False)
    changed = dict(inputs)
    changed["one_minute_bars"] = inputs["one_minute_bars"] + (
        replace(last, close_ts_ns=inputs["cutoff_ns"] + 1),
    )
    with pytest.raises(ValueError, match="future bar"):
        build_state_schema_v0(**changed)


def test_returns_atr_activity_do_not_change_from_post_cutoff_inputs() -> None:
    inputs = _inputs()
    baseline = build_state_schema_v0(**inputs)
    future = PublicTrade(inputs["cutoff_ns"] + NANO, 999.0, 99.0, AggressorSide.BUY)
    assert baseline.activity_ratio >= 0.0
    changed = dict(inputs)
    changed["trades"] = inputs["trades"] + (future,)
    with pytest.raises(ValueError):
        build_state_schema_v0(**changed)
    assert baseline.atr_1m_bps > 0
    assert baseline.atr_5m_bps > 0
    assert baseline.realized_volatility_bps >= 0
