from __future__ import annotations

import importlib.util
import os
from types import SimpleNamespace

import pytest

from trader_assist_v0.nautilus_e4.native_catalog import NativeCatalogBatchSink
from trader_assist_v0.nautilus_e4.native_health import NativeFeedObservations

AVAILABLE = importlib.util.find_spec("nautilus_trader") is not None
NATIVE = pytest.mark.skipif(
    not AVAILABLE and os.environ.get("NAUTILUS_E4_REQUIRED") != "1",
    reason="exact rc5 absent; native Linux CI required",
)


def test_receipt_age_is_per_stream_and_socket_cannot_mint_receipt():
    now = [100]
    quote = ("ETH", "QuoteTick")
    trade = ("ETH", "TradeTick")
    bar = ("ETH", "ETH-5-MINUTE-LAST-EXTERNAL")
    health = NativeFeedObservations({quote: 10, trade: 10, bar: 30}, now_ns=lambda: now[0])
    health.socket_observed(
        client_id="HYPERLIQUID", endpoint="hyperliquid-data-streams", state="CONNECTED",
    )
    assert {row["status"] for row in health.snapshot()["streams"]} == {"UNKNOWN"}
    health.received(quote)
    now[0] = 111
    rows = {row["stream"]: row for row in health.snapshot()["streams"]}
    assert rows["QuoteTick"]["status"] == "STALE"
    assert rows["TradeTick"]["status"] == "UNKNOWN"
    health.received(trade)
    health.socket_observed(client_id="OTHER", endpoint="other", state="DISCONNECTED")
    assert next(r for r in health.snapshot()["streams"] if r["stream"] == "TradeTick")[
        "status"
    ] == "RECEIVING"
    health.socket_observed(
        client_id="HYPERLIQUID", endpoint="hyperliquid-data-streams", state="DISCONNECTED",
    )
    assert {row["status"] for row in health.snapshot()["streams"]} == {"UNKNOWN"}
    with pytest.raises(ValueError, match="unconfigured"):
        health.received(("SKHX", "QuoteTick"))


def test_queue_observation_is_bounded_and_does_not_create_receipts():
    health = NativeFeedObservations({("ETH", "QuoteTick"): 10})
    for depth in range(100):
        health.queue_observed(SimpleNamespace(
            channel="data", condition="depth", state="PRESSURED",
            queue_depth=depth, mean_dispatch_ns=100,
        ))
    snapshot = health.snapshot()
    assert snapshot["queue"]["queue_depth"] == "99"
    assert snapshot["streams"][0]["status"] == "UNKNOWN"


@pytest.mark.parametrize("failure", [OSError("disk full"), PermissionError("read only")])
def test_failed_batch_is_uncertain_and_never_retried(tmp_path, failure):
    # Test only error handling here; real catalog serialization is tested below.
    sink = NativeCatalogBatchSink.__new__(NativeCatalogBatchSink)
    sink.root = tmp_path
    sink.failed = sink.closed = False
    sink.verified = 0
    sink._pending = [SimpleNamespace(ts_init=100)]
    sink._route = lambda event: ("quote_ticks", "ETH", "identifiers", "ETH")
    calls = []

    def write(events):
        calls.append(events)
        raise failure

    sink._catalog = SimpleNamespace(write_quote_ticks=write)
    with pytest.raises(OSError):
        sink.flush()
    assert sink.observation()["unverified_events"] == 1
    assert sink.verified == 0 and sink.failed
    with pytest.raises(RuntimeError, match="must not be retried"):
        sink.flush()
    assert len(calls) == 1


@NATIVE
def test_real_native_catalog_reopen_and_bounded_idle_flush(tmp_path):
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument, quote_tick

    now = [0]
    sink = NativeCatalogBatchSink(tmp_path / "catalog", batch_size=2, now_ns=lambda: now[0])
    sink.write_instruments([native_hyperliquid_instrument()])
    ticks = [quote_tick(ts_event=i, ts_init=i) for i in (100, 200, 300)]
    sink.append(ticks[0])
    assert sink.pending_count == 1
    sink.append(ticks[1])
    assert sink.pending_count == 0 and sink.verified == 2
    sink.append(ticks[2])
    now[0] = 1_000_000_000
    sink.flush_due()
    sink.close()
    from nautilus_trader.persistence import ParquetDataCatalog

    assert list(ParquetDataCatalog(str(sink.root)).query_quote_ticks()) == ticks
    assert not sink.observation()["continuity_proven"]
    with pytest.raises(RuntimeError, match="closed"):
        sink.append(ticks[0])


@NATIVE
def test_native_public_strategy_cold_start_has_zero_history_or_execution(tmp_path, monkeypatch):
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument, quote_tick

    from trader_assist_v0.nautilus_e4.host import NativePublicCaptureStrategy

    instrument = native_hyperliquid_instrument()
    sink = NativeCatalogBatchSink(tmp_path / "native")
    stops = []
    strategy = NativePublicCaptureStrategy(
        instrument_ids=(str(instrument.id),),
        bar_types=(f"{instrument.id}-1-MINUTE-LAST-EXTERNAL",),
        sink=sink, stop=lambda: stops.append(True),
    )
    calls = []

    def forbidden(*args, **kwargs):
        pytest.fail("history or order API reached")

    # Exercise the actual foundation on_start/callback/stop methods with native events.
    seam = SimpleNamespace(
        instrument_ids=strategy.instrument_ids, bar_types=strategy.bar_types,
        sink=sink, observations=strategy.observations, failure=None,
        cache=SimpleNamespace(instrument=lambda identity: instrument),
        clock=SimpleNamespace(set_timer_ns=lambda *a: None, cancel_timer=lambda *a: None),
        _timer_started=False, _failed=forbidden,
        subscribe_socket_state=lambda: calls.append("socket"),
        subscribe_queue_state=lambda: calls.append("queue"),
        subscribe_quotes=lambda i: calls.append("quote"),
        subscribe_trades=lambda i: calls.append("trade"),
        subscribe_book_depth10=lambda *a: calls.append("depth"),
        subscribe_bars=lambda b: calls.append("bar"),
        request_bars=forbidden, submit_order=forbidden,
    )
    NativePublicCaptureStrategy.on_start(seam)
    assert calls == ["socket", "queue", "quote", "trade", "depth", "bar"]
    NativePublicCaptureStrategy._received(seam, quote_tick(), "QuoteTick")
    NativePublicCaptureStrategy.on_stop(seam)
    assert sink.verified == 1 and not stops


@NATIVE
def test_missing_instrument_stops_before_subscriptions(tmp_path):
    from trader_assist_v0.nautilus_e4.host import NativePublicCaptureStrategy

    errors = []
    seam = SimpleNamespace(
        instrument_ids=("missing",), cache=SimpleNamespace(instrument=lambda i: None),
        _failed=lambda exc: errors.append(str(exc)),
    )
    NativePublicCaptureStrategy.on_start(seam)
    assert errors == ["native instrument missing from cache"]


@NATIVE
def test_native_typed_quote_trade_depth_bar_roundtrip(tmp_path):
    from nautilus_trader.model import (
        AggressorSide,
        Bar,
        BarType,
        BookOrder,
        OrderBookDepth10,
        OrderSide,
        Price,
        Quantity,
        TradeId,
        TradeTick,
    )
    from nautilus_trader.persistence import ParquetDataCatalog
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument, quote_tick

    instrument = native_hyperliquid_instrument()
    sink = NativeCatalogBatchSink(tmp_path / "mixed", batch_size=4)
    sink.write_instruments([instrument])
    quote = quote_tick()
    trade = TradeTick(
        instrument_id=instrument.id, price=Price.from_str("2000.0"),
        size=Quantity.from_str("0.010"), aggressor_side=AggressorSide.BUY,
        trade_id=TradeId("offline-native-fixture"), ts_event=102, ts_init=103,
    )
    bids = [BookOrder(
        side=OrderSide.BUY, price=Price.from_str(f"{1999 - i}.0"),
        size=Quantity.from_str("1.000"), order_id=i,
    ) for i in range(10)]
    asks = [BookOrder(
        side=OrderSide.SELL, price=Price.from_str(f"{2001 + i}.0"),
        size=Quantity.from_str("1.000"), order_id=10 + i,
    ) for i in range(10)]
    depth = OrderBookDepth10(
        instrument_id=instrument.id, bids=bids, asks=asks,
        bid_counts=[1] * 10, ask_counts=[1] * 10,
        flags=0, sequence=1, ts_event=104, ts_init=105,
    )
    bar = Bar(
        bar_type=BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-EXTERNAL"),
        open=Price.from_str("2000.0"), high=Price.from_str("2001.0"),
        low=Price.from_str("1999.0"), close=Price.from_str("2000.0"),
        volume=Quantity.from_str("1.000"), ts_event=106, ts_init=107,
    )
    for event in (quote, trade, depth, bar):
        sink.append(event)
    sink.close()
    fresh = ParquetDataCatalog(str(sink.root))
    assert list(fresh.query_quote_ticks()) == [quote]
    assert list(fresh.query_trade_ticks()) == [trade]
    assert list(fresh.query_order_book_depths()) == [depth]
    assert list(fresh.query_bars()) == [bar]
    assert sink.verified == 4


def test_readback_mismatch_keeps_batch_uncertain(tmp_path):
    sink = NativeCatalogBatchSink.__new__(NativeCatalogBatchSink)
    sink.root = tmp_path
    sink.failed = sink.closed = False
    sink.verified = 0
    sink._pending = [SimpleNamespace(ts_init=100)]
    sink._route = lambda event: ("quote_ticks", "ETH", "identifiers", "ETH")
    sink._catalog = SimpleNamespace(write_quote_ticks=lambda events: None)
    sink._factory = lambda path: SimpleNamespace(query_quote_ticks=lambda **kwargs: [])
    with pytest.raises(RuntimeError, match="readback mismatch"):
        sink.flush()
    assert sink.failed and sink.pending_count == 1 and sink.verified == 0


def test_instrument_freshness_and_clock_regression_remain_distinct():
    now = [20]
    eth, hip3 = ("ETH", "QuoteTick"), ("xyz:SKHX", "QuoteTick")
    health = NativeFeedObservations({eth: 10, hip3: 10}, now_ns=lambda: now[0])
    health.received(eth)
    now[0] = 30
    rows = {row["instrument_id"]: row for row in health.snapshot()["streams"]}
    assert rows["ETH"]["status"] == "RECEIVING"
    assert rows["xyz:SKHX"]["status"] == "UNKNOWN"
    now[0] = 19
    assert health.snapshot()["streams"][0]["status"] == "UNKNOWN"


@NATIVE
def test_out_of_order_native_batch_stops_without_reordering(tmp_path):
    from test_nautilus_vnext_g4_runner import quote_tick

    sink = NativeCatalogBatchSink(tmp_path / "out-of-order", batch_size=2)
    sink.append(quote_tick(ts_init=200))
    with pytest.raises(ValueError, match="nondecreasing"):
        sink.append(quote_tick(ts_init=100))
    assert sink.failed and sink.pending_count == 2 and sink.verified == 0
