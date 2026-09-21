from __future__ import annotations

from dataclasses import replace

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import (
    AggressorSide,
    BBO,
    BlockReason,
    CompletedBar,
    FreshnessInputs,
    L2Level,
    L2Snapshot,
    MarketIdentity,
    PublicTrade,
    evaluate_freshness,
)
from trader_assist_v0.fast_decision_model_lab.state import build_state_schema_v0

NANO = 1_000_000_000


def _bar(interval: int, index: int, cutoff_ns: int) -> CompletedBar:
    close_ts = cutoff_ns - (30 - index) * interval * NANO
    base = 100.0 + index * 0.1
    return CompletedBar(interval, base, base + 1.0, base - 1.0, base + 0.2, 10.0 + index, close_ts)


def _inputs() -> dict[str, object]:
    cutoff = 10_000 * NANO
    bbo = BBO(102.0, 5.0, 102.1, 6.0, cutoff - NANO, cutoff - NANO // 2, True)
    bids = tuple(L2Level(102.0 - index * 0.1, 5.0 + index) for index in range(5))
    asks = tuple(L2Level(102.1 + index * 0.1, 6.0 + index) for index in range(5))
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
    return {
        "market": MarketIdentity("ABC", "provider", "ABC-PERP"),
        "cutoff_ns": cutoff,
        "bbo": bbo,
        "l2": L2Snapshot(bids, asks, cutoff - NANO, cutoff - NANO // 2, "public-l2"),
        "trades": trades,
        "one_minute_bars": one,
        "five_minute_bars": five,
        "freshness": evaluate_freshness(
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
        ),
    }


def test_state_hash_is_deterministic_causal_and_market_configurable() -> None:
    inputs = _inputs()
    first = build_state_schema_v0(**inputs)
    second = build_state_schema_v0(**inputs)
    assert first.snapshot_hash == second.snapshot_hash
    assert first.snapshot_id == f"sha256:{first.snapshot_hash}"
    assert first.market.market == "ABC"
    future = PublicTrade(inputs["cutoff_ns"] + 1, 102.0, 1.0, AggressorSide.BUY)
    changed = dict(inputs)
    changed["trades"] = inputs["trades"] + (future,)
    with pytest.raises(ValueError, match="future trade"):
        build_state_schema_v0(**changed)


def test_freshness_boundary_and_health_fail_closed() -> None:
    now = 100 * NANO
    base = FreshnessInputs(
        l2_source_ts_ns=now - 2 * NANO,
        latest_1m_close_ts_ns=now - 60 * NANO,
        latest_5m_close_ts_ns=now - 300 * NANO,
        optional_active_context_ts_ns=now - NANO,
        metadata_ts_ns=now - NANO,
    )
    assert BlockReason.L2_STALE not in evaluate_freshness(now, base).reasons
    assert BlockReason.L2_STALE in evaluate_freshness(
        now, replace(base, l2_source_ts_ns=base.l2_source_ts_ns - 1)
    ).reasons
    disconnected = evaluate_freshness(now, replace(base, connected=False))
    assert not disconnected.valid
    assert BlockReason.DISCONNECTED in disconnected.reasons
