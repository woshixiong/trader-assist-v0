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
from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig, BacktestNode
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

from scripts.nautilus_rc5_public_data_probe import _external_minute_bar_type
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
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

RC5_VERSION = "2.0.0rc5"
BASE_SHA = "b0b13cb179c4f9d54ce568443fe404c2cd2ae2de"
MARKET = "2" * 64
FIVE_MINUTES_MS = 300_000
INSTRUMENT_ID = "ETH-USD-PERP.HYPERLIQUID"


def _installed_strategy_stub() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    dist = distribution("nautilus-trader")
    assert dist.version == RC5_VERSION
    matches: list[dict[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for entry in sorted((item for item in (dist.files or ()) if item.suffix == ".pyi"), key=str):
        path = Path(dist.locate_file(entry))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for declaration in tree.body:
            if not isinstance(declaration, ast.ClassDef) or declaration.name != "Strategy":
                continue
            methods = {
                node.name: node
                for node in declaration.body
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            }
            if {"__init__", "subscribe_socket_state", "on_socket_state"} <= methods.keys():
                matches.append(methods)
    assert len(matches) == 1
    return matches[0]


def _parameter_names(method: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    names = [
        arg.arg
        for arg in (*method.args.posonlyargs, *method.args.args, *method.args.kwonlyargs)
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
        source_id="RC5_QUALIFICATION_CURRENT_FIXTURE",
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


def _rc5_objects() -> tuple[QuoteTick, TradeTick, Bar]:
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
    bar_type = BarType(
        instrument_id,
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    bar = Bar(
        bar_type=bar_type,
        open=Price.from_str("1998.00"),
        high=Price.from_str("2002.00"),
        low=Price.from_str("1997.00"),
        close=Price.from_str("2000.00"),
        volume=Quantity.from_str("12.0"),
        ts_event=1_000_000_004,
        ts_init=1_000_000_005,
    )
    return quote, trade, bar


def _source_events() -> tuple[SourceEvent, SourceEvent, SourceEvent]:
    quote, trade, bar = _rc5_objects()
    market_id = sha256_hex(b"HYPERLIQUID|MAIN|RC5-QUALIFICATION")
    expression_id = "rc5-qualification-object-semantics"
    quote_payload = {
        "bid_price": str(quote.bid_price),
        "bid_size": str(quote.bid_size),
        "ask_price": str(quote.ask_price),
        "ask_size": str(quote.ask_size),
    }
    quote_source = SourceEvent.create(
        market_id=market_id,
        expression_id=expression_id,
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=str(quote.instrument_id),
        data_kind=DataKind.BBO,
        source_event_id="bbo:" + sha256_hex(canonical_json_bytes(quote_payload)),
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=f"block-time:{quote.ts_event}",
        ts_event=quote.ts_event,
        ts_init=quote.ts_init,
        true_network_receive_ts=None,
        payload=quote_payload,
    )
    trade_source = SourceEvent.create(
        market_id=market_id,
        expression_id=expression_id,
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=str(trade.instrument_id),
        data_kind=DataKind.TRADE,
        source_event_id=f"trade:{trade.trade_id}",
        native_trade_id=str(trade.trade_id),
        provider_aggressor_side=str(trade.aggressor_side),
        event_context=f"block-time:{trade.ts_event}",
        ts_event=trade.ts_event,
        ts_init=trade.ts_init,
        true_network_receive_ts=None,
        payload={"price": str(trade.price), "size": str(trade.size)},
    )
    bar_source = SourceEvent.create(
        market_id=market_id,
        expression_id=expression_id,
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=str(bar.bar_type.instrument_id),
        data_kind=DataKind.BAR,
        source_event_id=f"bar:{bar.bar_type}:{bar.ts_event}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=str(bar.bar_type),
        ts_event=bar.ts_event,
        ts_init=bar.ts_init,
        true_network_receive_ts=None,
        payload={
            "open": str(bar.open),
            "high": str(bar.high),
            "low": str(bar.low),
            "close": str(bar.close),
            "volume": str(bar.volume),
            "finalized": True,
        },
    )
    return quote_source, trade_source, bar_source


def test_q2_rc5_public_consumed_api() -> None:
    assert version("nautilus-trader") == RC5_VERSION
    assert all(
        symbol is not None
        for symbol in (
            QuoteTick,
            TradeTick,
            Bar,
            BarType,
            InstrumentId,
            TraderId,
            Strategy,
            StrategyConfig,
            LiveNode,
            LiveNodeBuilder,
            LiveNodeHandle,
            HyperliquidDataClientConfig,
            HyperliquidDataClientFactory,
            HyperliquidEnvironment,
            HYPERLIQUID_CLIENT_ID,
        )
    )
    stub = _installed_strategy_stub()
    subscribe = stub["subscribe_socket_state"]
    names = _parameter_names(subscribe)
    assert names[:1] == ("self",)
    assert {"client_id", "endpoint", "priority"} <= set(names)
    positional = (*subscribe.args.posonlyargs, *subscribe.args.args)
    optional_positional = max(0, len(positional) - 1)
    assert len(subscribe.args.defaults) >= optional_positional
    assert callable(Strategy.subscribe_quotes)
    assert callable(Strategy.subscribe_trades)
    assert callable(Strategy.subscribe_bars)
    builder = LiveNode.builder(
        "TRADEOS-RC5-API-QUALIFICATION",
        TraderId("TRADEOS-RC5-API-QUALIFICATION"),
        Environment.LIVE,
    )
    assert isinstance(builder, LiveNodeBuilder)
    builder.add_data_client(
        None,
        HyperliquidDataClientFactory(),
        HyperliquidDataClientConfig(environment=HyperliquidEnvironment.MAINNET),
    )
    node = builder.build()
    try:
        assert isinstance(node, LiveNode)
        handle = node.handle()
        assert isinstance(handle, LiveNodeHandle)
        assert callable(handle.stop)
    finally:
        node.dispose()


def test_q3_current_e3_host_semantic_equivalence_under_rc5() -> None:
    events = tuple(map(_event, range(49)))
    direct_evaluator = PilotStrategyEvaluator(
        manifest=_manifest(),
        market_id=MARKET,
        minimum_tick=Decimal("0.1"),
    )
    direct_outputs = tuple(
        output for event in events if (output := direct_evaluator.evaluate(event))
    )
    strategy = NautilusPilotStrategy(_config())
    engine = BacktestEngine(BacktestEngineConfig(bypass_logging=True, run_analysis=False))
    try:
        engine.add_strategy(strategy)
        engine.add_data([build_custom_data(event) for event in events], validate=True, sort=True)
        engine.run()
        engine.get_result()
    finally:
        engine.dispose()
    assert callable(BacktestNode.add_strategy_from_config)
    assert strategy.pilot_outputs == direct_outputs


def test_q4_q5_rc5_provider_objects_round_trip_current_project_evidence(tmp_path: Path) -> None:
    quote, trade, bar = _rc5_objects()
    assert str(quote.instrument_id) == INSTRUMENT_ID
    assert str(trade.trade_id) == "rc5-qualification-trade"
    assert str(trade.aggressor_side)
    assert str(bar.bar_type.instrument_id) == INSTRUMENT_ID
    sources = _source_events()
    store = EvidenceStore(tmp_path / "rc5-evidence")
    admissions = tuple(
        AdmittedEvent.create(
            process_epoch="rc5-qualification-process",
            continuity_epoch="rc5-qualification-continuity",
            admission_epoch="rc5-qualification-admission",
            admission_ordinal=index,
            admission_ts=source.ts_init,
            source_identity=source.replay_identity,
            out_of_order=False,
            continuity_state=EvidenceState.COMPLETE,
            source=source,
        )
        for index, source in enumerate(sources, start=1)
    )
    store.append_admission_batch(admissions)
    loaded = store.load_admissions()
    assert loaded == admissions
    assert tuple(item.source.data_kind for item in loaded) == (
        DataKind.BBO,
        DataKind.TRADE,
        DataKind.BAR,
    )
    assert loaded[1].source.native_trade_id == "rc5-qualification-trade"
    assert loaded[1].source.provider_aggressor_side == str(trade.aggressor_side)
    assert loaded[2].source.payload["finalized"] is True


def test_q7_qualification_probe_has_no_execution_or_write_surface() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = root / "scripts/nautilus_rc5_public_data_probe.py"
    source = probe.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(probe))
    forbidden_text = (
        "submit_order(",
        "submit_order_list(",
        "cancel_order(",
        "cancel_all_orders(",
        "modify_order(",
        "ExecClient",
        "ExecutionClient",
        "wallet",
        "private_key",
        "secret_key",
    )
    assert all(item not in source for item in forbidden_text)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert all("execution" not in module for module in imports)
    assert "HyperliquidDataClientFactory" in source
    assert "assert_public_only" in source


def test_q8_rc5_qualification_is_visibly_non_adoptive() -> None:
    root = Path(__file__).resolve().parents[1]
    probe_source = (root / "scripts/nautilus_rc5_public_data_probe.py").read_text(
        encoding="utf-8"
    )
    assert "qualification-only" in probe_source.lower()
    assert "2.0.0rc5" in probe_source
    assert "assert_exact_rc4" not in probe_source
