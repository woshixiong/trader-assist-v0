"""Synthetic native integration evidence, never evidence that a public symbol is listed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

if importlib.util.find_spec("nautilus_trader") is None:
    pytest.skip("official rc7 native evidence requires Linux CPython3.13", allow_module_level=True)

from decimal import Decimal

from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common import Cache, Clock
from nautilus_trader.execution import MakerTakerFeeModel
from nautilus_trader.model import (
    AccountType,
    AggressorSide,
    Bar,
    BarType,
    CryptoPerpetual,
    Currency,
    CurrencyPair,
    InstrumentId,
    Money,
    OmsType,
    Price,
    Quantity,
    QuoteTick,
    Symbol,
    TradeId,
    TradeTick,
)
from nautilus_trader.persistence import StreamingFeatherWriter

from trader_assist_v0.nautilus_e4.native_capture import native_event_hash
from trader_assist_v0.nautilus_e4.native_reference import (
    CANDIDATES,
    ReferenceReader,
    reference_actor,
    reference_bar_end,
    reference_proof,
)
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def instrument(
    venue: str,
    *,
    multiplier: str = "0.010",
    tick: str = "0.1",
    raw_symbol: str | None = None,
) -> object:
    swap = venue == "OKX"
    symbol = raw_symbol or ("ETH-USDT-SWAP" if swap else "ETHUSDT")
    kwargs = dict(
        instrument_id=InstrumentId.from_str(f"{symbol}.{venue}"),
        raw_symbol=Symbol(symbol),
        base_currency=Currency.from_str("ETH"),
        quote_currency=Currency.from_str("USDT"),
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str(tick),
        size_increment=Quantity.from_str("0.001"),
        ts_event=0,
        ts_init=0,
    )
    if swap:
        return CryptoPerpetual(
            **kwargs,
            settlement_currency=Currency.from_str("USDT"),
            is_inverse=False,
            multiplier=Quantity.from_str(multiplier),
        )
    return CurrencyPair(**kwargs)


def events(native: object) -> list[object]:
    now = 120_000_000_000
    identity = native.id
    return [
        QuoteTick(
            identity,
            Price.from_str("2000.0"),
            Price.from_str("2000.1"),
            Quantity.from_str("1.000"),
            Quantity.from_str("2.000"),
            now - 1,
            now,
        ),
        TradeTick(
            identity,
            Price.from_str("2000.0"),
            Quantity.from_str("1.000"),
            AggressorSide.BUY,
            TradeId("causal-native-fixture"),
            now - 1,
            now,
        ),
        Bar(
            BarType.from_str(f"{identity}-1-MINUTE-LAST-EXTERNAL"),
            Price.from_str("2000.0"),
            Price.from_str("2001.0"),
            Price.from_str("1999.0"),
            Price.from_str("2000.5"),
            Quantity.from_str("3.000"),
            now - 1_000_000 if str(identity.venue) == "BINANCE" else now - 60_000_000_000,
            now,
        ),
    ]


def test_native_public_factories_and_no_sandbox_reference_path(tmp_path: Path) -> None:
    node = build_native_node(tmp_path, venues=("BINANCE", "OKX"))
    try:
        assert not node.is_running
        assert node.cache is not None
    finally:
        node.dispose()
    with pytest.raises(ValueError, match="public-only"):
        build_native_node(tmp_path, venues=("BINANCE",), sandbox=True)
    with pytest.raises(ValueError, match="unsupported"):
        build_native_node(tmp_path, venues=("FAKE",))


def test_native_reference_actor_writer_catalog_consumer(tmp_path: Path) -> None:
    natives = [instrument("BINANCE"), instrument("OKX")]
    inputs = [event for native in natives for event in events(native)]
    reader = ReferenceReader()
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
    for native in natives:
        engine.add_venue(
            native.id.venue,
            OmsType.NETTING,
            AccountType.MARGIN,
            [Money.from_str("100000 USDT")],
            fee_model=MakerTakerFeeModel(Decimal("0"), Decimal("0")),
        )
        engine.add_instrument(native)
    engine.add_actor(reference_actor(reader))
    engine.add_data(inputs)
    try:
        engine.run()
        assert len(reader.hashes) == 6
        assert set(reader.hashes.values()) == {native_event_hash(e) for e in inputs}
    finally:
        engine.dispose()
    run_id = "f516ef25-6500-4ee8-994d-cbd64feb3ccd"
    stage = tmp_path / "live" / run_id
    writer = StreamingFeatherWriter(str(stage), Cache(), Clock.new_test())
    try:
        for native in natives:
            writer.write(native)
        for event in sorted(inputs, key=lambda e: e.ts_init):
            writer.write(event)
        writer.flush()
        with pytest.raises(ValueError, match="SEALED"):
            reference_proof(tmp_path, run_id, reader)
    finally:
        writer.close()
    proof = reference_proof(tmp_path, run_id, reader)
    assert proof["status"] == "AVAILABLE_NATIVE_SUBSET_PROVEN"
    assert proof["qualified"] == {"BINANCE": ["ETHUSDT"], "OKX": ["ETH-USDT-SWAP"]}
    assert proof["readback_count"] == 6
    assert list(stage.rglob("*.feather")) and list((tmp_path / "data").rglob("*.parquet"))
    assert len(proof["venues"]["BINANCE"]) == 12 and len(proof["venues"]["OKX"]) == 8
    missing = ReferenceReader()
    missing.admit(natives[0])
    assert reference_proof(tmp_path, run_id, missing)["status"] == "INCOMPLETE"
    changed = ReferenceReader()
    changed.admit(natives[0])
    changed.admit(instrument("OKX", multiplier="0.020"))
    with pytest.raises(ValueError, match="STORED_CONTRACT_MISMATCH"):
        reference_proof(tmp_path, run_id, changed)


def test_reference_research_rejects_identity_stale_duplicate_gap_and_units() -> None:
    reader = ReferenceReader()
    native = instrument("OKX")
    assert not reader.admit(instrument("BINANCE", raw_symbol="FAKEUSDT"))
    quote, trade, bar = events(native)
    assert not reader.consume(quote, now_ns=quote.ts_init)
    assert reader.rejects["UNRESOLVED_IDENTITY"] == 1
    assert reader.admit(native)
    assert not reader.admit(native)
    with pytest.raises(ValueError, match="CONTRACT_CHANGED"):
        reader.admit(instrument("OKX", multiplier="0.020"))
    assert not reader.consume(quote, now_ns=quote.ts_init - 1)
    assert not reader.consume(quote, now_ns=quote.ts_init + 31_000_000_000)
    assert reader.consume(quote, now_ns=quote.ts_init)
    assert reader.health.connected
    assert not reader.consume(quote, now_ns=quote.ts_init)
    off_tick = QuoteTick(
        native.id,
        Price.from_str("2000.01"),
        Price.from_str("2000.11"),
        Quantity.from_str("1.000"),
        Quantity.from_str("2.000"),
        quote.ts_event,
        quote.ts_init,
    )
    assert not reader.consume(off_tick, now_ns=quote.ts_init)
    off_size = TradeTick(
        native.id,
        trade.price,
        Quantity.from_str("0.0001"),
        trade.aggressor_side,
        trade.trade_id,
        trade.ts_event,
        trade.ts_init,
    )
    assert not reader.consume(off_size, now_ns=trade.ts_init)
    assert reader.rejects["NATIVE_PRICE_SIZE_CONTRACT_MISMATCH"] == 2
    assert reader.consume(bar, now_ns=bar.ts_init)
    assert reference_bar_end(bar) == bar.ts_init
    after_gap = Bar(
        bar.bar_type,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.ts_event + 120_000_000_000,
        bar.ts_init + 120_000_000_000,
    )
    assert not reader.consume(after_gap, now_ns=after_gap.ts_init)
    assert reader.rejects["GAP"] == 1
    assert reader.health.gaps[-1]["prior_ts_init"] == bar.ts_init
    assert reader.health.gaps[-1]["next_ts_init"] == after_gap.ts_init
    assert reader.health.gaps[-1]["lost_events"] == "UNKNOWN"
    open_bar = Bar(
        bar.bar_type,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.ts_event,
        bar.ts_event + 1,
    )
    assert not reader.consume(open_bar, now_ns=open_bar.ts_init)
    assert reader.rejects["REFERENCE_BAR_NOT_CLOSED"] == 1
    assert reader.coverage()["venues"]["BINANCE"][0]["missing_families"]
    assert tuple(CANDIDATES) == ("BINANCE", "OKX")


def test_reference_restart_boundary_requires_fresh_native_event_and_keeps_gap() -> None:
    native = instrument("OKX")
    quote = events(native)[0]
    reader = ReferenceReader()
    reader.admit(native)
    key = f"{native.id}:quote"
    reader.health.restore_boundaries(
        {key: {"ts_event": quote.ts_event - 1_000_000, "ts_init": quote.ts_init - 1_000_000}},
        now=quote.ts_init,
    )
    assert not reader.health.connected
    assert key in reader.coverage()["pending_gap_streams"]
    assert not reader.consume(quote, now_ns=quote.ts_init)
    assert reader.rejects["GAP"] == 1
    assert reader.health.connected
    assert reader.health.gaps[0]["reason"] == "PROCESS_RESTART"
    assert reader.health.gaps[0]["next_ts_init"] == quote.ts_init
    assert reader.health.gaps[0]["lost_events"] == "UNKNOWN"
