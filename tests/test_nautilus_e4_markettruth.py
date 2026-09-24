from __future__ import annotations

from pathlib import Path

from trader_assist_v0.nautilus_e4.markettruth import (
    MARKETTRUTH_TOPIC,
    Depth10PublicationGate,
    MarketTruthFanout,
    MarketTruthFanoutHealth,
    MarketTruthRef,
    MarketTruthSubscriber,
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


def test_depth10_gate_rejects_gapped_stale_and_reconnect_completing_event() -> None:
    gate = Depth10PublicationGate(max_admission_lag_ns=10)
    assert gate.admit(
        market_id="market-a", ts_event=10, ts_init=10, admission_ts=10,
        continuity_complete=True,
    ) is None
    assert gate.admit(
        market_id="market-a", ts_event=11, ts_init=11, admission_ts=11,
        continuity_complete=False,
    ) == "DEPTH10_CONTINUITY_NOT_COMPLETE"
    assert gate.admit(
        market_id="market-a", ts_event=12, ts_init=1, admission_ts=12,
        continuity_complete=True,
    ) == "DEPTH10_STALE"
    assert gate.admit(
        market_id="market-a", ts_event=13, ts_init=13, admission_ts=13,
        continuity_complete=True,
    ) is None


def test_depth10_currentness_is_isolated_per_market() -> None:
    gate = Depth10PublicationGate()
    assert gate.admit(
        market_id="market-a", ts_event=100, ts_init=100, admission_ts=100,
        continuity_complete=True,
    ) is None
    assert gate.admit(
        market_id="market-b", ts_event=1, ts_init=1, admission_ts=1,
        continuity_complete=True,
    ) is None
    assert gate.admit(
        market_id="market-a", ts_event=100, ts_init=100, admission_ts=100,
        continuity_complete=True,
    ) == "DEPTH10_NOT_CURRENT"


def test_project_subscriber_failure_degrades_shared_fanout_health() -> None:
    fanout = MarketTruthFanout()
    received: list[MarketTruthRef] = []
    subscriber = MarketTruthSubscriber(received.append, fanout)
    ref = _truth(1)
    subscriber(ref)
    assert received == [ref]

    def fail(_: MarketTruthRef) -> None:
        raise RuntimeError("expected")

    MarketTruthSubscriber(fail, fanout)(ref)
    assert fanout.health.state == "DEGRADED"
    assert fanout.health.last_publish_error == "SUBSCRIBER_RuntimeError"


def test_native_topic_publish_delivers_exact_immutable_ref_contract() -> None:
    fanout = MarketTruthFanout()
    delivered: list[tuple[str, object]] = []
    ref = _truth(2)
    fanout.publish(lambda topic, message: delivered.append((topic, message)), ref)

    assert delivered == [(MARKETTRUTH_TOPIC, ref)]
    assert fanout.health.published_count == 1
    assert fanout.health.state == "HEALTHY"


def test_host_uses_native_topic_without_project_shared_deque() -> None:
    source = (Path(__file__).parents[1] / "src/trader_assist_v0/nautilus_e4/host.py").read_text()
    assert "self._markettruth_fanout.publish(self.publish_message, markettruth)" in source
    assert "BoundedMarketTruthHandoff" not in source
    assert "collections.deque" not in source
    assert "self.subscribe_topic(MARKETTRUTH_TOPIC, subscriber, priority=priority)" in source
    assert "continuity_complete=event.continuity_state is EvidenceState.COMPLETE" in source
