from __future__ import annotations

from trader_assist_v0.nautilus_e4.markettruth import (
    BoundedMarketTruthHandoff,
    MarketTruthRef,
)


def _truth(index: int) -> MarketTruthRef:
    return MarketTruthRef.create(
        market_id="a" * 64,
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        source_event_id=f"native-depth10-{index}",
        ts_event=index,
        ts_init=index + 1,
        continuity_epoch="continuity-1",
        bid_price="1999.0",
        bid_size="2.0",
        ask_price="2001.0",
        ask_size="3.0",
    )


def test_markettruth_ref_is_immutable_and_hash_bound() -> None:
    first = _truth(1)
    assert first.ref_hash == _truth(1).ref_hash
    assert first.bid_price == "1999.0"


def test_bounded_handoff_drops_oldest_without_blocking_capture() -> None:
    handoff = BoundedMarketTruthHandoff(capacity=2)
    handoff.offer(_truth(1))
    handoff.offer(_truth(2))
    handoff.offer(_truth(3))
    assert [item.source_event_id for item in handoff.drain()] == [
        "native-depth10-2",
        "native-depth10-3",
    ]
    assert handoff.health.dropped == 1
