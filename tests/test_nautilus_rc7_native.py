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
    # A missing promoted row must never produce catalog PASS.
    for file in (tmp_path / "data").rglob("*.parquet"):
        if "quote" in str(file).lower():
            file.unlink()
    with pytest.raises(RuntimeError, match="CATALOG_INTEGRITY_FAILURE"):
        verify_promoted_run(tmp_path, runs[0], live=False)


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
