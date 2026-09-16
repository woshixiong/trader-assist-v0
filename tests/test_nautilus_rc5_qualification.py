from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import distribution, version
from pathlib import Path

from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID_CLIENT_ID,
    HyperliquidDataClientConfig,
    HyperliquidDataClientFactory,
    HyperliquidEnvironment,
)
from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode, LiveNodeBuilder, LiveNodeHandle
from nautilus_trader.model import (
    AggregationSource,
    AggressorSide,
    Bar,
    BarAggregation,
    BarSpecification,
    BarType,
    InstrumentId,
    Price,
    PriceType,
    Quantity,
    QuoteTick,
    TradeId,
    TraderId,
    TradeTick,
)
from nautilus_trader.trading import Strategy, StrategyConfig

from scripts.nautilus_rc5_public_data_probe import (
    RC5_VERSION,
    bar_source_event,
    build_public_data_node,
    expression_for,
    external_minute_bar_type,
    quote_source_event,
    trade_source_event,
)
from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.nautilus_e4.causal import CausalAdmissionLedger
from trader_assist_v0.nautilus_e4.contracts import DataKind
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.nautilus_pilot.contracts import StrategyInputEvent
from trader_assist_v0.nautilus_pilot.host import (
    NautilusPilotStrategy,
    NautilusPilotStrategyConfig,
    build_custom_data,
)
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)

BASE_SHA = "b0b13cb179c4f9d54ce568443fe404c2cd2ae2de"
INSTRUMENT_ID = "ETH-USD-PERP.HYPERLIQUID"
MARKET = "2" * 64
FIVE_MINUTES_MS = 300_000


def _installed_strategy_stub_methods() -> tuple[
    Path,
    dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
]:
    dist = distribution("nautilus-trader")
    assert dist.version == RC5_VERSION
    stub_entries = sorted(
        (entry for entry in (dist.files or ()) if entry.suffix == ".pyi"), key=str
    )
    assert stub_entries, "installed Nautilus distribution has no public .pyi files"
    matches: list[
        tuple[Path, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]]
    ] = []
    required = {"__init__", "subscribe_socket_state", "on_socket_state"}
    for entry in stub_entries:
        path = Path(dist.locate_file(entry))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise AssertionError(f"cannot inspect installed public stub {path}") from exc
        for declaration in tree.body:
            if not isinstance(declaration, ast.ClassDef) or declaration.name != "Strategy":
                continue
            methods = {
                node.name: node
                for node in declaration.body
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            }
            if required <= methods.keys():
                matches.append((path, methods))
    assert len(matches) == 1, [str(path) for path, _ in matches]
    return matches[0]


def _parameter_names(method: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    names = [
        argument.arg
        for argument in (
            *method.args.posonlyargs,
            *method.args.args,
            *method.args.kwonlyargs,
        )
    ]
    if method.args.vararg is not None:
        names.append(method.args.vararg.arg)
    if method.args.kwarg is not None:
        names.append(method.args.kwarg.arg)
    return tuple(names)


def _manifest() -> StrategyPackageManifest:
    return StrategyPackageManifest.create(trade_os_release_sha=BASE_SHA)


def _event(index: int) -> StrategyInputEvent:
    center = Decimal(100 + index % 9)
    close_time_ms = (index + 1) * FIVE_MINUTES_MS
    bar = ClosedBar.create(
        market_id=MARKET,
        interval="5m",
        open_time_ms=index * FIVE_MINUTES_MS,
        close_time_ms=close_time_ms,
        open=center,
        high=center + Decimal("2.000"),
        low=center - Decimal("2.00"),
        close=center + Decimal("0.5000"),
        volume=Decimal(f"{10 + index % 7}.00000"),
        source_id="RC5_E3_EQUIVALENCE_FIXTURE",
        provenance_hash=sha256_hex(f"rc5-fixture-{index}".encode()),
        received_at=datetime.fromtimestamp(close_time_ms / 1_000, tz=UTC),
    )
    return StrategyInputEvent.create(
        strategy_package_hash=_manifest().manifest_hash,
        closed_bar=bar,
    )


def _config() -> NautilusPilotStrategyConfig:
    manifest = _manifest()
    return NautilusPilotStrategyConfig(
        package_version=manifest.package_version,
        strategy_version=manifest.strategy_version,
        parameter_version=manifest.parameter_version,
        scanner_version=manifest.scanner_version,
        kernel_schema_version=manifest.kernel_schema_version,
        trade_os_release_sha=manifest.trade_os_release_sha,
        manifest_hash=manifest.manifest_hash,
        market_id=MARKET,
        minimum_tick="0.1",
    )


def _provider_objects() -> tuple[QuoteTick, TradeTick, Bar]:
    instrument_id = InstrumentId.from_str(INSTRUMENT_ID)
    quote = QuoteTick(
        instrument_id=instrument_id,
        bid_price=Price.from_str("1999.00"),
        ask_price=Price.from_str("2001.00"),
        bid_size=Quantity.from_str("2.0"),
        ask_size=Quantity.from_str("3.0"),
        ts_event=1_000_000_000,
        ts_init=1_000_000_001,
    )
    trade = TradeTick(
        instrument_id=instrument_id,
        price=Price.from_str("2000.00"),
        size=Quantity.from_str("1.0"),
        aggressor_side=AggressorSide.BUY,
        trade_id=TradeId("rc5-qualification-trade"),
        ts_event=1_000_000_002,
        ts_init=1_000_000_003,
    )
    bar = Bar(
        bar_type=BarType(
            instrument_id,
            BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        ),
        open=Price.from_str("1998.00"),
        high=Price.from_str("2002.00"),
        low=Price.from_str("1997.00"),
        close=Price.from_str("2000.00"),
        volume=Quantity.from_str("12.0"),
        ts_event=1_000_000_004,
        ts_init=1_000_000_005,
    )
    return quote, trade, bar


def test_q1_exact_rc5_distribution_identity() -> None:
    assert version("nautilus-trader") == RC5_VERSION == "2.0.0rc5"


def test_q2_rc5_public_consumed_api_and_installed_stub_contract() -> None:
    assert all(
        item is not None
        for item in (
            QuoteTick,
            TradeTick,
            Bar,
            InstrumentId,
            Price,
            Quantity,
            TradeId,
            AggressorSide,
            BarType,
            BarSpecification,
            BarAggregation,
            PriceType,
            AggregationSource,
        )
    )
    assert inspect.isclass(StrategyConfig)
    assert callable(StrategyConfig.__new__)
    assert callable(StrategyConfig.__init__)
    assert callable(Strategy.subscribe_quotes)
    assert callable(Strategy.subscribe_trades)
    assert callable(Strategy.subscribe_bars)
    assert callable(Strategy.subscribe_socket_state)
    assert callable(Strategy.on_quote)
    assert callable(Strategy.on_trade)
    assert callable(Strategy.on_bar)
    assert callable(Strategy.on_socket_state)

    stub_path, methods = _installed_strategy_stub_methods()
    assert stub_path.is_file()
    subscribe_names = _parameter_names(methods["subscribe_socket_state"])
    assert "client_id" not in subscribe_names
    assert "priority" in subscribe_names

    assert inspect.isclass(LiveNode)
    assert inspect.isclass(LiveNodeBuilder)
    assert inspect.isclass(LiveNodeHandle)
    assert callable(LiveNode.builder)
    builder = LiveNode.builder(
        "TRADEOS-RC5-PUBLIC-SURFACE",
        TraderId("TRADEOS-RC5-PUBLIC-SURFACE"),
        Environment.LIVE,
    )
    assert isinstance(builder, LiveNodeBuilder)
    assert callable(builder.add_data_client)
    assert callable(builder.build)
    assert inspect.isclass(HyperliquidDataClientConfig)
    assert inspect.isclass(HyperliquidDataClientFactory)
    assert HyperliquidEnvironment.MAINNET is not None
    assert HYPERLIQUID_CLIENT_ID is not None
    node = build_public_data_node()
    try:
        assert isinstance(node, LiveNode)
        assert isinstance(node.handle(), LiveNodeHandle)
    finally:
        node.dispose()


def test_q3_current_e3_host_is_semantically_equivalent_under_rc5() -> None:
    events = tuple(map(_event, range(49)))
    direct = PilotStrategyEvaluator(
        manifest=_manifest(), market_id=MARKET, minimum_tick=Decimal("0.1")
    )
    direct_outputs = tuple(output for event in events if (output := direct.evaluate(event)))

    strategy = NautilusPilotStrategy(_config())
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
    try:
        engine.add_strategy(strategy)
        engine.add_data([build_custom_data(event) for event in events], validate=True, sort=True)
        engine.run()
        engine.get_result()
    finally:
        engine.dispose()

    assert strategy.pilot_outputs
    assert strategy.pilot_outputs == direct_outputs


def test_q4_rc5_provider_objects_map_losslessly_to_current_source_event_semantics() -> None:
    expression = expression_for(INSTRUMENT_ID, "ETH")
    quote, trade, bar = _provider_objects()
    quote_source = quote_source_event(expression, quote)
    trade_source = trade_source_event(expression, trade)
    bar_source = bar_source_event(expression, bar)

    assert quote_source.data_kind is DataKind.BBO
    assert quote_source.payload == {
        "bid_price": str(quote.bid_price),
        "bid_size": str(quote.bid_size),
        "ask_price": str(quote.ask_price),
        "ask_size": str(quote.ask_size),
    }
    assert trade_source.data_kind is DataKind.TRADE
    assert trade_source.native_trade_id == str(trade.trade_id)
    assert trade_source.provider_aggressor_side == str(trade.aggressor_side)
    assert trade_source.payload == {"price": str(trade.price), "size": str(trade.size)}
    assert bar_source.data_kind is DataKind.BAR
    assert str(bar.bar_type.instrument_id) == INSTRUMENT_ID
    assert bar_source.instrument_id == INSTRUMENT_ID
    assert bar_source.payload["finalized"] is True
    assert bar_source.ts_event == bar.ts_event
    assert bar_source.ts_init == bar.ts_init


def test_q5_current_causal_admission_and_evidence_store_round_trip_rc5_objects(
    tmp_path: Path,
) -> None:
    expression = expression_for(INSTRUMENT_ID, "ETH")
    quote, trade, bar = _provider_objects()
    sources = (
        quote_source_event(expression, quote),
        trade_source_event(expression, trade),
        bar_source_event(expression, bar),
    )
    ledger = CausalAdmissionLedger(
        process_epoch="rc5-test-process",
        continuity_epoch="rc5-test-continuity",
        admission_epoch="rc5-test-admission",
    )
    store = EvidenceStore(tmp_path)
    admitted = []
    for index, source in enumerate(sources, start=1):
        outcome = ledger.admit(source, admission_ts=source.ts_init + index)
        assert not outcome.duplicate
        assert outcome.event is not None
        admitted.append(outcome.event)
    store.append_admission_batch(tuple(admitted))
    restored = store.load_admissions()
    assert restored == tuple(admitted)
    assert [item.admission_ordinal for item in restored] == [1, 2, 3]
    assert restored[-1].source.payload["finalized"] is True


def test_q4_external_bar_type_round_trip_remains_public_and_exact() -> None:
    raw = external_minute_bar_type(INSTRUMENT_ID)
    parsed = BarType.from_str(raw)
    assert str(parsed.instrument_id) == INSTRUMENT_ID
    assert parsed.spec.step == 1
    assert parsed.spec.aggregation is BarAggregation.MINUTE
    assert parsed.spec.price_type is PriceType.LAST
    assert parsed.aggregation_source is AggregationSource.EXTERNAL


def test_q7_qualification_harness_has_no_execution_or_write_surface() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/nautilus_rc5_public_data_probe.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    prohibited_calls = {
        "submit_order",
        "submit_order_list",
        "cancel_order",
        "cancel_all_orders",
        "modify_order",
        "add_exec_client",
        "add_execution_client",
    }
    referenced = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    } | {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert prohibited_calls.isdisjoint(referenced)
    assert "HyperliquidDataClientFactory" in source
    assert "add_data_client" in source
    assert "HyperliquidExecutionClient" not in source
    assert "PrivateKey" not in source
    assert "API_KEY" not in source
