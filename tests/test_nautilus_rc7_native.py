"""Required Linux-native rc7 evidence, with no exchange credentials/order writes."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

if importlib.util.find_spec("nautilus_trader") is None:
    pytest.skip("rc7 native evidence runs in isolated Linux CI", allow_module_level=True)

from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from nautilus_trader.model import (
    AccountType,
    BookType,
    InstrumentId,
    Money,
    OmsType,
    Price,
    Quantity,
    QuoteTick,
    Venue,
)
from nautilus_trader.persistence import ParquetDataCatalog

from trader_assist_v0.nautilus_e4.native_catalog import (
    recover_and_promote,
    replay_catalog_quotes,
    replay_data_config,
    streaming_config,
    verify_promoted_run,
)
from trader_assist_v0.nautilus_e4.native_execution import native_execution_contract
from trader_assist_v0.nautilus_e4.native_runtime import build_native_node


def test_native_public_sandbox_and_inert_execution_construction(tmp_path: Path) -> None:
    for sandbox in (False, True):
        from nautilus_trader.execution import MakerTakerFeeModel

        node = build_native_node(
            tmp_path / str(sandbox),
            sandbox=sandbox,
            sandbox_fee_model=MakerTakerFeeModel(Decimal("0"), Decimal("0")),
        )
        try:
            assert node.cache is not None
            assert node.portfolio is not None
            assert not node.is_running
        finally:
            node.dispose()
            del node
    config, factory, risk, execution = native_execution_contract(env={})
    assert not risk.bypass
    assert execution.reconciliation
    assert config.account_address is None
    assert factory.name()


def test_native_stream_promotes_equal_timestamp_rows_and_roundtrips(tmp_path: Path) -> None:
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    instrument = native_hyperliquid_instrument()
    engine = BacktestEngine(
        BacktestEngineConfig(
            streaming=streaming_config(tmp_path),
            bypass_logging=True,
            run_analysis=False,
        )
    )
    from nautilus_trader.execution import MakerTakerFeeModel

    engine.add_venue(
        Venue("HYPERLIQUID"),
        OmsType.NETTING,
        AccountType.MARGIN,
        [Money.from_str("100000 USDC")],
        book_type=BookType.L1_MBP,
        fee_model=MakerTakerFeeModel(Decimal("0"), Decimal("0")),
    )
    engine.add_instrument(instrument)
    ticks = [
        QuoteTick(
            InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID"),
            Price.from_str(str(2000 + i) + ".0"),
            Price.from_str(str(2001 + i) + ".0"),
            Quantity.from_str("1.000"),
            Quantity.from_str("1.000"),
            1_000_000_000,
            1_000_000_000,
        )
        for i in (0, 1, 2)
    ]
    engine.add_data(ticks)
    try:
        engine.run()
    finally:
        engine.dispose()
    catalog = ParquetDataCatalog(str(tmp_path))
    runs = catalog.list_backtest_runs()
    assert len(runs) == 1
    proof = verify_promoted_run(tmp_path, runs[0], live=False)
    assert proof["types"]["QuoteTick"]["count"] == 3
    restored = catalog.query_quote_ticks(identifiers=[str(instrument.id)])
    assert [q.to_dict() for q in restored] == [q.to_dict() for q in ticks]
    assert recover_and_promote(tmp_path, runs[0], live=False) == proof
    replay = replay_catalog_quotes(tmp_path, runs[0], live=False)
    assert replay["native_engine_runs"] == 2
    assert replay["quote_count"] == 3
    # A missing promoted row must never produce catalog PASS.
    for file in (tmp_path / "data").rglob("*.parquet"):
        if "quote" in str(file).lower():
            file.unlink()
    with pytest.raises(RuntimeError, match="CATALOG_INTEGRITY_FAILURE"):
        verify_promoted_run(tmp_path, runs[0], live=False)


def test_native_crash_recovers_flushed_partial_and_promotes_idempotently(tmp_path: Path) -> None:
    import os
    import subprocess
    import sys

    run_id = "8b067de2-e76c-49c3-851d-9ce6d03cf180"
    stage = tmp_path / "live" / run_id
    code = """
import os, sys
from nautilus_trader.common import Cache, Clock
from nautilus_trader.model import Price, Quantity, QuoteTick
from nautilus_trader.persistence import StreamingFeatherWriter
from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument
instrument = native_hyperliquid_instrument()
writer = StreamingFeatherWriter(sys.argv[1], Cache(), Clock.new_test())
writer.write(instrument)
for i in range(3):
    writer.write(QuoteTick(instrument.id, Price.from_str('2000.0'), Price.from_str('2001.0'),
                          Quantity.from_str('1.000'), Quantity.from_str('1.000'),
                          1000000000+i, 1000000000+i))
writer.flush()
os._exit(0)
"""
    env = dict(os.environ, PYTHONPATH="src:.:tests")
    subprocess.run([sys.executable, "-c", code, str(stage)], env=env, check=True, timeout=30)
    partials = list(stage.rglob("*.feather.partial"))
    assert partials, "fixture must terminate before native close/seal"
    # Simulate a cut-short last append, after actual native flushed batches.
    for path in partials:
        with path.open("ab") as file:
            file.write(b"truncated-final-append")
    proof = recover_and_promote(tmp_path, run_id)
    assert proof["types"]["QuoteTick"]["count"] == 3
    assert not list(stage.rglob("*.feather.partial"))
    assert recover_and_promote(tmp_path, run_id) == proof
    assert replay_catalog_quotes(tmp_path, run_id)["quote_count"] == 3


def test_official_sandbox_protocol_fixture_attaches_without_live_execution(tmp_path: Path) -> None:
    from nautilus_trader.execution import MakerTakerFeeModel

    from trader_assist_v0.nautilus_e4.native_sandbox import attach_sandbox_probe

    node = build_native_node(
        tmp_path,
        sandbox=True,
        sandbox_fee_model=MakerTakerFeeModel(Decimal("0.00015"), Decimal("0.00045")),
    )
    try:
        attach_sandbox_probe(node)
        assert not node.is_running
    finally:
        node.dispose()


def test_explicit_book_batching_native_contract(tmp_path: Path) -> None:
    from nautilus_trader.model import NautilusDataType

    config = replay_data_config(
        tmp_path,
        NautilusDataType.OrderBookDelta,
        InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID"),
        start=1,
        end=10,
    )
    assert config.batch_deltas is True


def test_continuous_native_interval_reads_sealed_prefix_and_retains_equal_time_tail(
    tmp_path: Path,
) -> None:
    from nautilus_trader.common import Cache, Clock
    from nautilus_trader.model import BookAction, BookOrder, OrderBookDelta, OrderSide
    from nautilus_trader.persistence import RotationConfig, StreamingFeatherWriter
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.nautilus_e4.native_catalog import (
        STAGE_ROTATION_NS,
        ArchiveIntegrityError,
        read_staged_run,
    )

    config = streaming_config(tmp_path, continuous=True)
    assert config.promotion_interval_ms is None and not config.promote_on_close
    assert not config.delete_feather_after_promotion
    assert config.rotation_config.interval_ns == STAGE_ROTATION_NS
    run_id = "042e5764-dc54-4d2f-adf8-92c4396084dc"
    stage = tmp_path / "live" / run_id
    clock = Clock.new_test()
    clock.set_time(1_000_000_000)
    instrument = native_hyperliquid_instrument()
    writer = StreamingFeatherWriter(
        str(stage), Cache(), clock, rotation_config=RotationConfig.interval(STAGE_ROTATION_NS)
    )
    rows = [
        QuoteTick(
            instrument.id,
            Price.from_str(f"{2000 + i}.0"),
            Price.from_str(f"{2001 + i}.0"),
            Quantity.from_str("1.000"),
            Quantity.from_str("1.000"),
            1_000_000_000,
            1_000_000_000,
        )
        for i in range(3)
    ]
    books = [
        OrderBookDelta.clear(instrument.id, 1, 1_000_000_000, 1_000_000_000),
        OrderBookDelta(
            instrument.id,
            BookAction.ADD,
            BookOrder(OrderSide.BUY, Price.from_str("2000.0"), Quantity.from_str("1.000"), 1),
            0,
            2,
            1_000_000_000,
            1_000_000_000,
        ),
        OrderBookDelta.clear(instrument.id, 3, 1_000_000_000, 1_000_000_000),
        OrderBookDelta(
            instrument.id,
            BookAction.ADD,
            BookOrder(OrderSide.SELL, Price.from_str("2001.0"), Quantity.from_str("2.000"), 2),
            0,
            4,
            1_000_000_000,
            1_000_000_000,
        ),
    ]
    catalog = ParquetDataCatalog(str(tmp_path))

    def quotes():
        return [row for row in catalog.read_live_run(run_id) if isinstance(row, QuoteTick)]

    def book_rows():
        return [row for row in catalog.read_live_run(run_id) if isinstance(row, OrderBookDelta)]

    try:
        writer.write(instrument)
        writer.write(rows[0])
        writer.write(books[0])
        writer.write(books[1])
        writer.flush()
        assert catalog.read_live_run(run_id) == []  # Never touch the locked tail.
        clock.set_time(1_000_000_000 + STAGE_ROTATION_NS)
        writer.write(rows[1])  # The write seals, without closing/restarting the writer.
        writer.write(books[2])
        clock.set_time(2_000_000_000 + STAGE_ROTATION_NS)
        writer.write(rows[2])
        writer.write(books[3])
        writer.flush()
        assert [row.to_dict() for row in quotes()] == [row.to_dict() for row in rows[:2]]
        assert read_staged_run(tmp_path, run_id)["open_partials"]
        with pytest.raises(ArchiveIntegrityError, match="INCOMPLETE"):
            read_staged_run(tmp_path, run_id, require_closed=True)
        # Passing wall time and flushing do NOT rotate a quiet data family.
        clock.set_time(10 * STAGE_ROTATION_NS)
        writer.flush()
        assert len(quotes()) == 2
        assert [row.to_dict() for row in book_rows()] == [row.to_dict() for row in books[:3]]
        assert not writer.is_closed
        assert catalog.query_quote_ticks(identifiers=[str(instrument.id)]) == []
    finally:
        writer.close()
    assert [row.to_dict() for row in quotes()] == [row.to_dict() for row in rows]
    assert (
        read_staged_run(tmp_path, run_id, require_closed=True)["types"]["QuoteTick"]["count"] == 3
    )
    sources = list(stage.rglob("*.feather"))
    with pytest.raises(Exception, match="(?i)overlap|non.disjoint|intersect"):
        recover_and_promote(tmp_path, run_id)
    assert all(path.exists() for path in sources)
    assert len(quotes()) == 3
    assert [row.to_dict() for row in book_rows()] == [row.to_dict() for row in books]
    broken = next(path for path in sources if "quote" in str(path).lower())
    broken.write_bytes(b"corrupt-sealed-native-source")
    with pytest.raises(ArchiveIntegrityError, match="NATIVE_STAGE_READ_FAILURE"):
        read_staged_run(tmp_path, run_id, require_closed=True)


def test_native_clear_book_equal_timestamp_promotion_preserves_order(tmp_path: Path) -> None:
    from nautilus_trader.common import Cache, Clock
    from nautilus_trader.model import BookAction, BookOrder, OrderBookDelta, OrderSide
    from nautilus_trader.persistence import StreamingFeatherWriter
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.nautilus_e4.native_catalog import event_multiset

    run_id = "eb943584-b1a4-4edc-bb71-b4c00d860afd"
    instrument = native_hyperliquid_instrument()
    stage = tmp_path / "live" / run_id
    writer = StreamingFeatherWriter(str(stage), Cache(), Clock.new_test())
    writer.write(instrument)
    stamp = 1_000_000_000
    rows = [
        OrderBookDelta.clear(instrument.id, 1, stamp, stamp),
        OrderBookDelta(
            instrument.id,
            BookAction.ADD,
            BookOrder(OrderSide.BUY, Price.from_str("2000.0"), Quantity.from_str("1.000"), 1),
            0,
            2,
            stamp,
            stamp,
        ),
        OrderBookDelta.clear(instrument.id, 3, stamp, stamp),
        OrderBookDelta(
            instrument.id,
            BookAction.ADD,
            BookOrder(OrderSide.SELL, Price.from_str("2001.0"), Quantity.from_str("2.000"), 2),
            0,
            4,
            stamp,
            stamp,
        ),
        OrderBookDelta.clear(instrument.id, 5, stamp, stamp),
    ]
    try:
        for row in rows:
            writer.write(row)
            writer.flush()  # Multiple batches, same ts_init, one unrotated source.
        with pytest.raises(RuntimeError, match="ACTIVE_OR_UNRECOVERED|NO_TYPED"):
            verify_promoted_run(tmp_path, run_id)
    finally:
        writer.close()
    proof = recover_and_promote(tmp_path, run_id)
    assert proof["types"]["OrderBookDelta"]["count"] == 5
    catalog = ParquetDataCatalog(str(tmp_path))
    restored = catalog.query_order_book_deltas(identifiers=[str(instrument.id)])
    assert [row.sequence for row in restored] == [1, 2, 3, 4, 5]
    assert event_multiset(restored) == event_multiset(rows)
    assert recover_and_promote(tmp_path, run_id) == proof


def test_native_rotation_equal_timestamp_overlap_fails_with_source_retained(tmp_path: Path) -> None:
    from nautilus_trader.common import Cache, Clock
    from nautilus_trader.persistence import RotationConfig, StreamingFeatherWriter
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    run_id = "5b6435a2-0a79-4d43-b1ae-d48ce62c8cac"
    instrument = native_hyperliquid_instrument()
    stage = tmp_path / "live" / run_id
    writer = StreamingFeatherWriter(
        str(stage), Cache(), Clock.new_test(), rotation_config=RotationConfig.size(1)
    )
    writer.write(instrument)
    try:
        for i in range(3):
            writer.write(
                QuoteTick(
                    instrument.id,
                    Price.from_str(f"{2000 + i}.0"),
                    Price.from_str(f"{2001 + i}.0"),
                    Quantity.from_str("1.000"),
                    Quantity.from_str("1.000"),
                    1_000_000_000,
                    1_000_000_000,
                )
            )
            writer.flush()
    finally:
        writer.close()
    sources = list(stage.rglob("*.feather"))
    assert len(sources) >= 3, "fixture must really rotate equal-ts_init source rows"
    with pytest.raises(Exception, match="(?i)overlap|non.disjoint|intersect"):
        recover_and_promote(tmp_path, run_id)
    assert all(path.exists() for path in sources)
    with pytest.raises(RuntimeError, match="CATALOG_INTEGRITY_FAILURE"):
        verify_promoted_run(tmp_path, run_id)


def test_frozen_replay_fee_adapter_keeps_real_native_engine_and_instrument() -> None:
    import nautilus_trader.backtest as backtest
    import nautilus_trader.model as model
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.research_replay.native_fee_compat import (
        native_fee_compatibility,
        native_modules,
    )

    instrument = native_hyperliquid_instrument()
    original_engine, original_instrument = backtest.BacktestEngine, model.CryptoPerpetual
    run = SimpleNamespace(cost=SimpleNamespace(maker_bps=Decimal("1.5"), taker_bps=Decimal("4.5")))

    @native_fee_compatibility
    def replay(run: object, instrument: object) -> None:
        native = native_modules.import_module("nautilus_trader.model")
        assert isinstance(instrument, native.CryptoPerpetual)
        assert instrument.maker_fee == Decimal("0.00015")
        assert instrument.taker_fee == Decimal("0.00045")
        engine = native_modules.import_module("nautilus_trader.backtest").BacktestEngine(
            BacktestEngineConfig(bypass_logging=True, run_analysis=False)
        )
        try:
            assert isinstance(engine._engine, original_engine)
            with pytest.raises(ValueError, match="override"):
                engine.add_venue(fee_model=None)
            engine.add_venue(
                venue=Venue("HYPERLIQUID"),
                oms_type=OmsType.NETTING,
                account_type=AccountType.MARGIN,
                starting_balances=[Money.from_str("100000 USDC")],
                book_type=BookType.L1_MBP,
            )
            with pytest.raises(TypeError, match="bound instrument"):
                engine.add_instrument(instrument.native)
            engine.add_instrument(instrument)
            cached = engine.cache.instrument(instrument.id)
            assert isinstance(cached, original_instrument)
            assert cached.id == instrument.native.id
        finally:
            engine.dispose()

    replay(run, instrument)
    assert backtest.BacktestEngine is original_engine
    assert model.CryptoPerpetual is original_instrument
    assert native_modules.import_module("nautilus_trader.backtest") is backtest
    with pytest.raises(TypeError, match="CryptoPerpetual"):
        replay(run, object())


def test_frozen_replay_fee_adapter_nested_failure_restores_context() -> None:
    import nautilus_trader.model as model
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.research_replay.native_fee_compat import (
        native_fee_compatibility,
        native_modules,
    )

    instrument = native_hyperliquid_instrument()
    run = SimpleNamespace(cost=SimpleNamespace(maker_bps=Decimal(1), taker_bps=Decimal(4)))

    @native_fee_compatibility
    def inner(run: object, instrument: object) -> None:
        raise RuntimeError("nested replay failed")

    @native_fee_compatibility
    def outer(run: object, instrument: object) -> None:
        outer_view = native_modules.import_module("nautilus_trader.model")
        with pytest.raises(RuntimeError, match="nested replay failed"):
            inner(run, instrument.native)
        assert isinstance(
            instrument, native_modules.import_module("nautilus_trader.model").CryptoPerpetual
        )
        assert (
            outer_view.CryptoPerpetual
            == native_modules.import_module("nautilus_trader.model").CryptoPerpetual
        )
        raise RuntimeError("outer replay failed")

    with pytest.raises(RuntimeError, match="outer replay failed"):
        outer(run, instrument)
    assert native_modules.import_module("nautilus_trader.model") is model


def test_native_contexts_seal_readback_and_causal_research_consumer(tmp_path: Path) -> None:
    from nautilus_trader.adapters.hyperliquid import HyperliquidOpenInterest
    from nautilus_trader.common import Cache, Clock
    from nautilus_trader.model import (
        CustomData,
        DataType,
        FundingRateUpdate,
        IndexPriceUpdate,
        MarkPriceUpdate,
        NautilusDataType,
        custom_data_backend_kind,
    )
    from nautilus_trader.persistence import StreamingFeatherWriter
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.nautilus_e4.native_context import (
        ContextResearchReader,
        context_identity,
        context_proof,
        register_native_context_types,
    )

    register_native_context_types()

    instrument = native_hyperliquid_instrument()
    run_id = "60fe38f4-5cce-4403-a38f-e1b3a003a198"
    stage = tmp_path / "live" / run_id
    reader = ContextResearchReader({str(instrument.id)})
    now = 60_000_000_000
    events = [
        MarkPriceUpdate(instrument.id, Price.from_str("2000.0"), now - 1, now),
        IndexPriceUpdate(instrument.id, Price.from_str("2001.0"), now - 1, now),
        FundingRateUpdate(instrument.id, Decimal("0.00001"), now - 1, now),
        HyperliquidOpenInterest(instrument.id, Decimal("100.50"), now - 1, now),
    ]
    writer = StreamingFeatherWriter(str(stage), Cache(), Clock.new_test())
    try:
        writer.write(instrument)
        for event in events:
            assert reader.consume(event, now_ns=now)
            stored = (
                CustomData(
                    DataType("HyperliquidOpenInterest", {"instrument_id": str(instrument.id)}),
                    event,
                )
                if isinstance(event, HyperliquidOpenInterest)
                else event
            )
            if isinstance(event, HyperliquidOpenInterest):
                assert custom_data_backend_kind(stored) == "native"
                assert stored.data.to_json() == event.to_json()
            writer.write(stored)
        writer.flush()
        with pytest.raises(ValueError, match="SEALED"):
            context_proof(tmp_path, run_id, reader.instrument_ids, reader.hashes)
        assert not reader.consume(events[0], now_ns=now)
        assert not reader.consume(events[0], now_ns=now + 61_000_000_000)
        unresolved = ContextResearchReader(set())
        assert not unresolved.consume(events[0], now_ns=now)
        assert reader.rejects == {"DUPLICATE": 1, "STALE": 1}
        assert unresolved.rejects == {"UNRESOLVED_IDENTITY": 1}
    finally:
        writer.close()
    proof = context_proof(tmp_path, run_id, reader.instrument_ids, reader.hashes)
    assert proof["status"] == "USABLE_BOUNDED_SEALED_NATIVE_CONTEXT"
    assert len(proof["streams"]) == 4
    restored_oi = next(
        getattr(item, "data", item)
        for item in ParquetDataCatalog(str(tmp_path)).query_custom_data(
            NautilusDataType.Custom("HyperliquidOpenInterest")
        )
    )
    assert restored_oi.open_interest == events[-1].open_interest
    assert (restored_oi.instrument_id, restored_oi.ts_event, restored_oi.ts_init) == (
        instrument.id,
        now - 1,
        now,
    )
    assert context_identity(restored_oi)[2] == context_identity(events[-1])[2]
    for changed in (
        HyperliquidOpenInterest(instrument.id, Decimal("100.5000000000000001"), now - 1, now),
        HyperliquidOpenInterest(instrument.id, Decimal("100.50"), now, now),
    ):
        assert context_identity(changed)[2] != context_identity(events[-1])[2]
    assert list(stage.rglob("*.feather"))
    with pytest.raises(ValueError, match="CONTEXT_NOT_USABLE"):
        context_proof(
            tmp_path, run_id, reader.instrument_ids, {**reader.hashes, "unknown": "missing"}
        )


def test_native_saved_closed_5m_indicator_registration(tmp_path: Path) -> None:
    """Synthetic foundation seam only: no range classifier, strategy or order."""
    from nautilus_trader.common import Cache, Clock, DataActor, Environment
    from nautilus_trader.indicators import AverageTrueRange, DonchianChannel, EfficiencyRatio
    from nautilus_trader.model import Bar, BarType, NautilusDataType
    from nautilus_trader.persistence import StreamingFeatherWriter
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.nautilus_e4.native_capture import closed_bar_window, native_event_hash

    instrument = native_hyperliquid_instrument()
    bar_type = BarType.from_str(f"{instrument.id}-5-MINUTE-LAST-EXTERNAL")
    duration = 300_000_000_000
    bars = [
        Bar(
            bar_type,
            Price.from_str(f"{2000 + i}.0"),
            Price.from_str(f"{2002 + i}.0"),
            Price.from_str(f"{1999 + i}.0"),
            Price.from_str(f"{2001 + i}.0"),
            Quantity.from_str("1.000"),
            (i + 1) * duration,
            (i + 2) * duration,
        )
        for i in range(24)
    ]
    run_id = "5438042c-d124-4854-8bbf-ef99f3f8d09c"
    stage = tmp_path / "live" / run_id
    writer = StreamingFeatherWriter(str(stage), Cache(), Clock.new_test())
    try:
        writer.write(instrument)
        for bar in bars:
            writer.write(bar)
    finally:
        writer.close()
    catalog = ParquetDataCatalog(str(tmp_path))
    catalog.convert_stream_to_data(run_id, NautilusDataType.Bar, environment=Environment.LIVE)
    restored = catalog.query_bars(identifiers=[str(bar_type)])
    assert [native_event_hash(b) for b in restored] == [native_event_hash(b) for b in bars]
    assert not list(stage.rglob("*.feather.partial"))
    with pytest.raises(ValueError, match="NOT_CLOSED_OR_FUTURE"):
        closed_bar_window(restored[0], now_ns=restored[0].ts_init - 1)
    with pytest.raises(ValueError, match="INVALID_NATIVE_BAR_PERIOD"):
        closed_bar_window(
            SimpleNamespace(bar_type=SimpleNamespace(spec=SimpleNamespace(step=2)), ts_event=1),
            now_ns=duration,
        )

    class IndicatorProbe(DataActor):
        def __init__(self) -> None:
            super().__init__()
            self.dc = DonchianChannel(20)
            self.er = EfficiencyRatio(14)
            self.atr = AverageTrueRange(14)
            self.seen: list[str] = []

        def on_start(self) -> None:
            for indicator in (self.dc, self.er, self.atr):
                self.register_indicator_for_bars(bar_type, indicator)
            self.subscribe_bars(bar_type)

        def on_bar(self, bar: Bar) -> None:
            closed_bar_window(bar, now_ns=self.clock.timestamp_ns())
            self.seen.append(native_event_hash(bar))
            assert self.dc.has_inputs and self.er.has_inputs and self.atr.has_inputs

    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
    probe = IndicatorProbe()
    from nautilus_trader.execution import MakerTakerFeeModel

    engine.add_venue(
        Venue("HYPERLIQUID"),
        OmsType.NETTING,
        AccountType.MARGIN,
        [Money.from_str("100000 USDC")],
        fee_model=MakerTakerFeeModel(Decimal("0"), Decimal("0")),
    )
    engine.add_instrument(instrument)
    engine.add_actor(probe)
    engine.add_data(restored)
    try:
        engine.run()
        assert probe.seen == [native_event_hash(b) for b in bars]
        assert probe.dc.initialized and probe.er.initialized and probe.atr.initialized
        assert probe.dc.upper == 2025.0 and probe.dc.lower == 2003.0
        assert probe.er.value == pytest.approx(1.0)
        assert probe.atr.value > 0
    finally:
        engine.dispose()
