from __future__ import annotations

import ast
import importlib.util
import inspect
import os
from importlib.metadata import distribution, version
from pathlib import Path

import pytest

if importlib.util.find_spec("nautilus_trader") is None:
    if os.environ.get("NAUTILUS_E4_REQUIRED") == "1":
        raise AssertionError("authoritative E4 CI requires the exact Nautilus distribution")
    pytest.skip("optional Nautilus distribution is absent", allow_module_level=True)

from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID_CLIENT_ID,
    HyperliquidDataClientConfig,
    HyperliquidDataClientFactory,
    HyperliquidEnvironment,
)
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode, LiveNodeBuilder, LiveNodeHandle
from nautilus_trader.model import (
    AggregationSource,
    AggressorSide,
    Bar,
    BarAggregation,
    BarSpecification,
    BarType,
    BookOrder,
    InstrumentId,
    OrderBookDepth10,
    OrderSide,
    Price,
    PriceType,
    Quantity,
    QuoteTick,
    TradeId,
    TraderId,
    TradeTick,
)
from nautilus_trader.trading import Strategy, StrategyConfig

from scripts.e4_nautilus_public_data_probe import _external_minute_bar_type
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
from trader_assist_v0.nautilus_e4.contracts import (
    LEGACY_NAUTILUS_VERSION,
    NAUTILUS_VERSION,
    DataKind,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.host import (
    NautilusE4CaptureStrategy,
    build_capture_strategy,
    build_public_data_node,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore

INSTRUMENT_ID = "ETH-USD-PERP.HYPERLIQUID"
MARKET_ID = sha256_hex(b"HYPERLIQUID|MAIN|ETH")
SECOND_INSTRUMENT_ID = "BTC-USD-PERP.HYPERLIQUID"
SECOND_MARKET_ID = sha256_hex(b"HYPERLIQUID|MAIN|BTC")
_MANIFEST_DOMAIN = b"trader-assist-v0/e4/run-manifest/v1\0"


def _installed_strategy_stub_methods() -> tuple[
    Path,
    dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
]:
    dist = distribution("nautilus-trader")
    assert dist.version == NAUTILUS_VERSION
    stub_entries = sorted(
        (entry for entry in (dist.files or ()) if entry.suffix == ".pyi"),
        key=str,
    )
    assert stub_entries, "installed Nautilus distribution has no public .pyi files"
    matches: list[
        tuple[Path, dict[str, ast.FunctionDef | ast.AsyncFunctionDef]]
    ] = []
    required = {"__init__", "subscribe_socket_state", "on_socket_state"}
    for entry in stub_entries:
        path = Path(dist.locate_file(entry))
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise AssertionError(
                f"cannot read/parse installed public stub {path}"
            ) from exc
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
    assert len(matches) == 1, (
        "expected one installed public Strategy stub, found "
        f"{[str(path) for path, _ in matches]}"
    )
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


def _annotation_parts(annotation: ast.expr) -> tuple[str, ...]:
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        try:
            annotation = ast.parse(annotation.value, mode="eval").body
        except SyntaxError as exc:
            raise AssertionError(
                f"unparseable installed stub annotation: {annotation.value!r}"
            ) from exc
    if isinstance(annotation, ast.Name):
        return (annotation.id,)
    if isinstance(annotation, ast.Attribute):
        return (*_annotation_parts(annotation.value), annotation.attr)
    raise AssertionError(
        "installed on_socket_state event annotation is not a qualified public name: "
        f"{ast.dump(annotation)}"
    )


def _capture_identity() -> tuple[MarketExpression, PitUniverseSnapshot, RunManifest]:
    expression = MarketExpression(
        market_id=MARKET_ID,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id=INSTRUMENT_ID,
        expression_id="exact-current-real-bar",
        instrument_metadata_version="EXACT_CURRENT_CONSTRUCTIVE_TEST_V1",
        instrument_metadata_hash=sha256_hex(b"EXACT_CURRENT_CONSTRUCTIVE_TEST_V1"),
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=1, expressions=(expression,))
    manifest = RunManifest.create(
        run_id="exact-current-real-bar",
        git_sha="2" * 40,
        git_tree="3" * 40,
        snapshot=snapshot,
        process_epoch="process-real-bar",
        continuity_epoch="continuity-real-bar",
        admission_epoch="admission-real-bar",
        capture_configuration={"expressions": [expression.model_dump(mode="json")]},
        subscription_policy={
            "discovery": [MARKET_ID],
            "watch": [MARKET_ID],
            "actionable": [],
        },
        trial_ledger_id="exact-current-real-bar-v1",
    )
    return expression, snapshot, manifest


def _legacy_rc4_manifest(manifest: RunManifest) -> RunManifest:
    raw = manifest.model_dump(mode="json")
    raw["nautilus_version"] = LEGACY_NAUTILUS_VERSION
    identity = {key: value for key, value in raw.items() if key != "manifest_hash"}
    raw["manifest_hash"] = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(identity))
    return RunManifest.model_validate(raw)


def _capture_strategy(root: Path) -> NautilusE4CaptureStrategy:
    _expression, snapshot, manifest = _capture_identity()
    return build_capture_strategy(
        manifest=manifest,
        snapshot=snapshot,
        policy=SubscriptionPolicy(
            discovery=frozenset({MARKET_ID}),
            watch=frozenset({MARKET_ID}),
            actionable=frozenset(),
        ),
        bar_types=(_external_minute_bar_type(INSTRUMENT_ID),),
        evidence_root=root,
    )


def _two_market_capture_strategy(root: Path) -> NautilusE4CaptureStrategy:
    expression, _snapshot, manifest = _capture_identity()
    second = MarketExpression(
        market_id=SECOND_MARKET_ID,
        dex="MAIN",
        provider_coin="BTC",
        instrument_id=SECOND_INSTRUMENT_ID,
        expression_id="exact-current-btc",
        instrument_metadata_version="EXACT_CURRENT_CONSTRUCTIVE_TEST_V1",
        instrument_metadata_hash=sha256_hex(b"EXACT_CURRENT_BTC"),
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=1, expressions=(expression, second))
    rebound_manifest = RunManifest.create(
        run_id="exact-current-two-market",
        git_sha=manifest.git_sha,
        git_tree=manifest.git_tree,
        snapshot=snapshot,
        process_epoch="process-real-two-market",
        continuity_epoch="continuity-real-two-market",
        admission_epoch="admission-real-two-market",
        capture_configuration={"expressions": [
            expression.model_dump(mode="json"), second.model_dump(mode="json")
        ]},
        subscription_policy={
            "discovery": [MARKET_ID, SECOND_MARKET_ID],
            "watch": [MARKET_ID, SECOND_MARKET_ID],
            "actionable": [],
        },
        trial_ledger_id="exact-current-two-market-v1",
    )
    return build_capture_strategy(
        manifest=rebound_manifest,
        snapshot=snapshot,
        policy=SubscriptionPolicy(
            discovery=frozenset({MARKET_ID, SECOND_MARKET_ID}),
            watch=frozenset({MARKET_ID, SECOND_MARKET_ID}),
            actionable=frozenset(),
        ),
        bar_types=(_external_minute_bar_type(INSTRUMENT_ID),),
        evidence_root=root,
    )


def _real_nautilus_events() -> tuple[QuoteTick, TradeTick, Bar]:
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
        trade_id=TradeId("exact-current-trade"),
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


def _depth10(*, instrument_id: str, ts_event: int, ts_init: int) -> OrderBookDepth10:
    native_instrument = InstrumentId.from_str(instrument_id)
    return OrderBookDepth10(
        instrument_id=native_instrument,
        bids=[
            BookOrder(
                side=OrderSide.BUY,
                price=Price.from_str(f"{1999 - index}.00"),
                size=Quantity.from_str(f"{2 + index}.0"),
                order_id=index + 1,
            )
            for index in range(10)
        ],
        asks=[
            BookOrder(
                side=OrderSide.SELL,
                price=Price.from_str(f"{2001 + index}.00"),
                size=Quantity.from_str(f"{3 + index}.0"),
                order_id=index + 11,
            )
            for index in range(10)
        ],
        bid_counts=[1] * 10,
        ask_counts=[1] * 10,
        flags=0,
        sequence=ts_event,
        ts_event=ts_event,
        ts_init=ts_init,
    )


def test_exact_current_public_data_live_node_surfaces() -> None:
    assert version("nautilus-trader") == NAUTILUS_VERSION
    assert inspect.isclass(HyperliquidDataClientConfig)
    assert inspect.isclass(HyperliquidDataClientFactory)
    assert inspect.isclass(StrategyConfig)
    assert callable(StrategyConfig.__new__)
    assert callable(StrategyConfig.__init__)
    assert inspect.isclass(LiveNode)
    assert inspect.isclass(LiveNodeBuilder)
    assert inspect.isclass(LiveNodeHandle)
    assert HyperliquidEnvironment.MAINNET is not None
    assert Environment.LIVE is not None
    assert HYPERLIQUID_CLIENT_ID is not None
    assert callable(TraderId)
    assert callable(LiveNode.builder)
    builder = LiveNode.builder(
        "TRADEOS-E4-CURRENT-TEST",
        TraderId("TRADEOS-E4-CURRENT-TEST"),
        Environment.LIVE,
    )
    assert isinstance(builder, LiveNodeBuilder)
    assert callable(builder.add_data_client)
    assert callable(builder.build)
    node = build_public_data_node()
    try:
        assert isinstance(node, LiveNode)
        assert callable(node.add_strategy)
        handle = node.handle()
        assert isinstance(handle, LiveNodeHandle)
        assert callable(handle.stop)
    finally:
        node.dispose()


def test_exact_host_composes_public_data_factory_only() -> None:
    from trader_assist_v0.nautilus_e4 import host

    source = Path(inspect.getfile(host)).read_text(encoding="utf-8")
    assert "LiveNode.builder(" in source
    assert "builder.add_data_client(" in source
    assert "HyperliquidDataClientFactory()" in source
    assert "HyperliquidEnvironment.MAINNET" in source
    assert "Environment.LIVE" in source
    assert "StreamingConfig" not in source
    assert "TradingNode" not in source
    assert "ExecClient" not in source
    assert all(name not in source for name in ("submit_order(", "cancel_order(", "modify_order("))


def test_e4_provider_boundary_uses_only_supported_root_model_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    provider_files = (
        root / "src/trader_assist_v0/nautilus_e4/host.py",
        root / "scripts/e4_nautilus_public_data_probe.py",
        Path(__file__),
    )
    model_root = "nautilus_trader.model"
    forbidden = {
        f"{model_root}.{leaf}"
        for leaf in ("data", "enums", "identifiers", "objects")
    }
    offenders: list[str] = []
    for path in provider_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: tuple[str, ...] = ()
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                modules = (node.module,)
            elif isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            for module in modules:
                if any(module == item or module.startswith(item + ".") for item in forbidden):
                    offenders.append(f"{path.relative_to(root)}:{node.lineno}:{module}")
    assert not offenders, "legacy Nautilus model imports: " + ", ".join(offenders)


def test_exact_current_strategy_market_data_and_socket_state_contract() -> None:
    assert callable(Strategy.subscribe_quotes)
    assert callable(Strategy.subscribe_trades)
    assert callable(Strategy.subscribe_bars)
    assert callable(Strategy.on_quote)
    assert callable(Strategy.on_trade)
    assert callable(Strategy.on_bar)
    assert callable(Strategy.subscribe_socket_state)
    assert callable(Strategy.on_socket_state)
    strategy_stub_path, strategy_stub = _installed_strategy_stub_methods()
    assert strategy_stub_path.is_file()
    init_positional = tuple(
        argument.arg
        for argument in (
            *strategy_stub["__init__"].args.posonlyargs,
            *strategy_stub["__init__"].args.args,
        )
    )
    assert init_positional[:2] == ("self", "config")
    subscribe = strategy_stub["subscribe_socket_state"]
    subscribe_names = _parameter_names(subscribe)
    callback_names = _parameter_names(strategy_stub["on_socket_state"])
    assert {"client_id", "endpoint", "priority"} <= set(subscribe_names)
    positional = (*subscribe.args.posonlyargs, *subscribe.args.args)
    optional_positional = max(0, len(positional) - 1)
    assert len(subscribe.args.defaults) >= optional_positional
    assert "event" in callback_names
    event_argument = next(
        argument
        for argument in (
            *strategy_stub["on_socket_state"].args.posonlyargs,
            *strategy_stub["on_socket_state"].args.args,
            *strategy_stub["on_socket_state"].args.kwonlyargs,
        )
        if argument.arg == "event"
    )
    assert event_argument.annotation is not None
    assert _annotation_parts(event_argument.annotation) in {
        ("SocketStateChanged",),
        ("common", "SocketStateChanged"),
    }

    from trader_assist_v0.nautilus_e4 import host

    source = Path(inspect.getfile(host)).read_text(encoding="utf-8")
    assert "self.subscribe_socket_state()" in source
    assert "self.subscribe_quotes(instrument_id)" in source
    assert "self.subscribe_trades(instrument_id)" in source
    assert "def on_quote(" in source
    assert "def on_trade(" in source
    assert "tick: QuoteTick" in source
    assert "tick: TradeTick" in source
    assert "bar: Bar" in source
    assert "def on_socket_state(" in source
    for obsolete in (
        "subscribe_quote_ticks",
        "subscribe_trade_ticks",
        "def on_quote_tick(",
        "def on_trade_tick(",
    ):
        assert obsolete not in source


def test_constructive_exact_current_objects_drive_typed_identity_and_real_bar_callback(
    tmp_path: Path,
) -> None:
    quote, trade, bar = _real_nautilus_events()
    strategy = _capture_strategy(tmp_path)
    node = build_public_data_node()
    try:
        node.add_strategy(strategy)
        assert quote.instrument_id == trade.instrument_id == bar.bar_type.instrument_id
        assert not hasattr(bar, "instrument_id")
        assert strategy._expression_for(quote).market_id == MARKET_ID
        assert strategy._expression_for(trade).market_id == MARKET_ID
        assert strategy._expression_for(bar).market_id == MARKET_ID
        with pytest.raises(TypeError, match="unsupported provider event type"):
            strategy._expression_for(object())  # type: ignore[arg-type]

        strategy.on_quote(quote)
        strategy.on_trade(trade)
        strategy.on_bar(bar)
    finally:
        node.dispose()

    stored = EvidenceStore(tmp_path).load_admissions()
    assert len(stored) == 1
    finalized = stored[0].source
    assert finalized.market_id == MARKET_ID
    assert finalized.instrument_id == INSTRUMENT_ID
    assert finalized.data_kind is DataKind.BAR
    assert finalized.ts_event == bar.ts_event
    assert finalized.ts_init == bar.ts_init
    assert finalized.payload["finalized"] is True


def test_exact_rc5_markettruth_recovery_and_subscriber_failure_composition(
    tmp_path: Path,
) -> None:
    """Exercise native rc5 component topic delivery through the real E4 callback."""
    strategy = _capture_strategy(tmp_path)
    node = build_public_data_node()
    received = []
    try:
        node.add_strategy(strategy)
        strategy.subscribe_markettruth(received.append)
        base_ns = strategy.clock.timestamp_ns()

        strategy.on_book_depth(_depth10(
            instrument_id=INSTRUMENT_ID, ts_event=base_ns + 1, ts_init=base_ns + 1
        ))
        assert len(received) == 1
        assert received[0].instrument_id == INSTRUMENT_ID

        strategy.capture_session.disconnect(reason="TEST_GAP")
        strategy.capture_session.reconnect(required_streams=strategy._continuity_streams)
        quote, trade, _bar = _real_nautilus_events()
        strategy.on_quote(quote)
        strategy.on_trade(trade)
        strategy.on_book_depth(_depth10(
            instrument_id=INSTRUMENT_ID, ts_event=base_ns + 2, ts_init=base_ns + 2
        ))
        assert len(received) == 1  # reconnect-completing event was GAPPED

        strategy.on_book_depth(_depth10(
            instrument_id=INSTRUMENT_ID, ts_event=base_ns + 3, ts_init=base_ns + 3
        ))
        assert len(received) == 2

        def fail(_message: object) -> None:
            raise RuntimeError("subscriber failure")

        strategy.subscribe_markettruth(fail)
        strategy.on_book_depth(_depth10(
            instrument_id=INSTRUMENT_ID, ts_event=base_ns + 4, ts_init=base_ns + 4
        ))
        assert len(received) == 3
        assert strategy.markettruth_fanout_health.state == "DEGRADED"
        assert strategy.markettruth_fanout_health.last_publish_error == "SUBSCRIBER_RuntimeError"
    finally:
        node.dispose()


def test_exact_rc5_markettruth_depth10_currentness_is_cross_market_isolated(
    tmp_path: Path,
) -> None:
    strategy = _two_market_capture_strategy(tmp_path)
    node = build_public_data_node()
    received = []
    try:
        node.add_strategy(strategy)
        strategy.subscribe_markettruth(received.append)
        now = strategy.clock.timestamp_ns()
        strategy.on_quote(
            QuoteTick(
                instrument_id=InstrumentId.from_str(INSTRUMENT_ID),
                bid_price=Price.from_str("1999.00"),
                ask_price=Price.from_str("2001.00"),
                bid_size=Quantity.from_str("2.0"),
                ask_size=Quantity.from_str("3.0"),
                ts_event=now + 100,
                ts_init=now + 100,
            )
        )
        strategy.on_book_depth(_depth10(
            instrument_id=SECOND_INSTRUMENT_ID, ts_event=now, ts_init=now
        ))
        assert [item.instrument_id for item in received] == [SECOND_INSTRUMENT_ID]
    finally:
        node.dispose()


def test_legacy_rc4_manifest_is_readable_but_active_rc5_runtime_fails_closed(
    tmp_path: Path,
) -> None:
    _expression, snapshot, current_manifest = _capture_identity()
    legacy_manifest = _legacy_rc4_manifest(current_manifest)
    assert legacy_manifest.nautilus_version == LEGACY_NAUTILUS_VERSION
    assert RunManifest.model_validate_json(legacy_manifest.model_dump_json()) == legacy_manifest
    with pytest.raises(RuntimeError, match="manifest/runtime Nautilus version mismatch"):
        build_capture_strategy(
            manifest=legacy_manifest,
            snapshot=snapshot,
            policy=SubscriptionPolicy(
                discovery=frozenset({MARKET_ID}),
                watch=frozenset({MARKET_ID}),
                actionable=frozenset(),
            ),
            bar_types=(_external_minute_bar_type(INSTRUMENT_ID),),
            evidence_root=tmp_path / "legacy-runtime-mismatch",
        )


def test_exact_current_external_minute_bar_type_round_trips_through_public_parser() -> None:
    raw = _external_minute_bar_type(INSTRUMENT_ID)
    parsed = BarType.from_str(raw)
    assert str(parsed.instrument_id) == INSTRUMENT_ID
    assert parsed.spec.step == 1
    assert parsed.spec.aggregation is BarAggregation.MINUTE
    assert parsed.spec.price_type is PriceType.LAST
    assert parsed.aggregation_source is AggregationSource.EXTERNAL


def test_probe_uses_live_node_strategy_and_handle_surfaces() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/e4_nautilus_public_data_probe.py").read_text(
        encoding="utf-8"
    )
    assert "node.add_strategy(strategy)" in source
    assert "handle = node.handle()" in source
    assert "threading.Timer(args.run_seconds, handle.stop)" in source
    assert "node.trader" not in source
    assert "node.stop" not in source


def test_depth10_uses_the_exact_rc5_public_strategy_binding() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/trader_assist_v0/nautilus_e4/host.py").read_text(
        encoding="utf-8"
    )
    assert "from nautilus_trader.model import Bar, BookType, OrderBookDepth10" in source
    assert "subscribe_book_depth10(instrument_id, BookType.L2_MBP)" in source
    assert "def on_book_depth(self, depth: OrderBookDepth10)" in source
    assert "on_book_depth10" not in source
