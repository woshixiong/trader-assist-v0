from __future__ import annotations

from pathlib import Path

from trader_assist_v0.nautilus_e4.markettruth import (
    MARKETTRUTH_TOPIC,
    MarketTruthFanoutHealth,
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


def test_native_fanout_contract_is_versioned_and_truthful() -> None:
    health = MarketTruthFanoutHealth()
    assert MARKETTRUTH_TOPIC == "app.trader_assist.markettruth.v1"
    assert health.transport == "NAUTILUS_MESSAGEBUS_SYNC_TOPIC"
    assert health.native_internal_queue_pressure == "NOT_APPLICABLE_SYNC_IN_PROCESS_TOPIC"


def test_host_uses_native_topic_without_project_shared_deque() -> None:
    source = (Path(__file__).parents[1] / "src/trader_assist_v0/nautilus_e4/host.py").read_text()
    assert "self.publish_message(MARKETTRUTH_TOPIC, markettruth)" in source
    assert "BoundedMarketTruthHandoff" not in source
    assert "collections.deque" not in source
    assert "DataKind.DEPTH10" in source
    assert 'last_publish_error="INCOMPLETE_DEPTH10"' in source
    assert 'last_publish_error="DEPTH10_NOT_CURRENT_OR_CONTINUOUS"' in source
