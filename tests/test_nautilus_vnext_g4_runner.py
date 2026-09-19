from __future__ import annotations

import importlib.util
import inspect
import json
import os
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from scripts.nautilus_vnext_g4_qualification import _representative_scale_probe
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_g4.catalog_bridge import (
    NativeReplayProjection,
    NativeReplayProjectionIdentity,
    _native_content_hash,
)
from trader_assist_v0.nautilus_g4.runner import (
    BACKTEST_NODE_PUBLIC_METHODS,
    ProviderExecutionEvidence,
    ProviderExecutionRecord,
    ProviderFillEvidence,
    ProviderStateProjection,
    RepresentativeMarketEvidence,
    TriggerQuoteEvidence,
    _assert_single_provider_state,
    _ExecutionLedger,
    _mint_provider_execution_evidence,
    _persist_and_reload_projection,
    _provider_order_side,
    _validate_execution_inputs,
    assert_actual_representative_scale,
    assert_backtest_node_catalog_surface,
    assert_exact_nautilus_rc5,
    assert_representative_scale,
    build_fill_model,
    candidate_state_isolation_plan,
    causal_claim_gate_states,
    execute_provider_native_state,
    formal_g4_acceptance,
    new_isolated_backtest_engine,
    project_provider_native_state,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    HypotheticalOrderIntent,
    OrderPrimitive,
    PositionSide,
    ReentryPolicy,
    TechnicalOrderQuantity,
    WinnerConfirmation,
)

STRUCTURAL = "a" * 64
NAUTILUS_AVAILABLE = importlib.util.find_spec("nautilus_trader") is not None
NAUTILUS_REQUIRED = os.environ.get("NAUTILUS_G4_REQUIRED") == "1"
REQUIRES_NAUTILUS = pytest.mark.skipif(
    not NAUTILUS_AVAILABLE and not NAUTILUS_REQUIRED,
    reason="optional Nautilus distribution is absent",
)


def _assert_required_nautilus_available() -> None:
    if not NAUTILUS_AVAILABLE:
        raise AssertionError("authoritative G4 CI requires the exact Nautilus distribution")


def candidate(candidate_id: str) -> CandidateManifest:
    config = CandidateConfig(
        entry_activation=EntryActivation.EA1,
        attempt_stop=AttemptStop.AP0,
        room_to_cost_k=Decimal("2"),
        reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
        winner_confirmation=WinnerConfirmation.WC0,
        winner_progress_bps=Decimal("3"),
        exit_policy=ExitPolicy.X1,
        comparison_role="REFERENCE" if candidate_id == "reference" else "CHALLENGER",
    )
    return CandidateManifest.create(
        candidate_id=candidate_id,
        structural_component_manifest_hash=STRUCTURAL,
        config=config,
    )


def execution_model() -> ExecutionModelConfig:
    return ExecutionModelConfig(
        book_type="L1_MBP",
        order_primitive=OrderPrimitive.MARKETABLE,
        prob_fill_on_limit=Decimal("0"),
        prob_slippage=Decimal("0"),
        trade_execution=True,
        queue_position=False,
        liquidity_consumption=True,
        fill_limit_at_price=False,
        fill_stop_at_price=False,
        random_seed=7,
        execution_model_limited=True,
    )


def canonical_intent(side: PositionSide = PositionSide.LONG) -> HypotheticalOrderIntent:
    from trader_assist_v0.vnext_g4.contracts import _ORDER_INTENT_DOMAIN

    quantity = TechnicalOrderQuantity(
        quantity=Decimal("0.010"),
        displayed_opposite_l1_size=Decimal("1.000"),
        size_decimals=3,
        instrument_metadata_version="metadata-v1",
        instrument_metadata_hash="b" * 64,
        bbo_admission_hash="c" * 64,
    )
    payload: dict[str, object] = {
        "strategy_decision_id": "decision-1",
        "candidate_hash": "d" * 64,
        "side": side,
        "technical_quantity": quantity.model_dump(mode="python"),
        "executable_price": Decimal("2000.0"),
        "technical_notional": Decimal("20.0000"),
        "activation_sequence_id": "activation-1",
        "activation_reference_hash": "e" * 64,
        "validation_reference_id": "validation-v1",
        "validation_reference_hash": "f" * 64,
        "causal_lineage_hash": "1" * 64,
        "not_submitted": True,
        "venue_submitted": False,
    }
    return HypotheticalOrderIntent.model_validate(
        {
            **payload,
            "order_intent_hash": sha256_hex(
                _ORDER_INTENT_DOMAIN + canonical_json_bytes(payload)
            ),
        }
    )


def native_projection(
    events: tuple[object, ...],
    *,
    source_hashes: tuple[str, ...] | None = None,
) -> NativeReplayProjection:
    from nautilus_trader.model import Bar, QuoteTick, TradeTick

    event_hashes = tuple(sha256_hex(f"native-{index}".encode()) for index in range(len(events)))
    sources = source_hashes or tuple(
        sha256_hex(f"source-{index}".encode()) for index in range(len(events))
    )
    identity = NativeReplayProjectionIdentity.create(
        schema_version="NATIVE_REPLAY_PROJECTION_V1",
        transform_version="E4_ADMITTED_TO_NAUTILUS_RC5_NATIVE_REPLAY_V1",
        market_id="a" * 64,
        expression_id="expr-ETH",
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        ordered_source_admission_hashes=sources,
        ordered_native_event_hashes=event_hashes,
        native_content_hash=_native_content_hash(event_hashes),
        event_count=len(events),
        quote_tick_count=sum(isinstance(event, QuoteTick) for event in events),
        trade_tick_count=sum(isinstance(event, TradeTick) for event in events),
        bar_count=sum(isinstance(event, Bar) for event in events),
    )
    return NativeReplayProjection(identity=identity, events=events)


def quote_tick(
    *,
    instrument_id: str = "ETH-USD-PERP.HYPERLIQUID",
    ts_event: int = 100,
    ts_init: int = 101,
    bid_price: str = "1999.0",
) -> object:
    from nautilus_trader.model import InstrumentId, Price, Quantity, QuoteTick

    return QuoteTick(
        instrument_id=InstrumentId.from_str(instrument_id),
        bid_price=Price.from_str(bid_price),
        ask_price=Price.from_str("2001.0"),
        bid_size=Quantity.from_str("1.000"),
        ask_size=Quantity.from_str("1.000"),
        ts_event=ts_event,
        ts_init=ts_init,
    )


def native_hyperliquid_instrument() -> object:
    """Construct one offline real rc5 CryptoPerpetual with provider identity."""
    from nautilus_trader.model import (
        CryptoPerpetual,
        Currency,
        InstrumentId,
        Price,
        Quantity,
        Symbol,
    )

    return CryptoPerpetual(
        instrument_id=InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID"),
        raw_symbol=Symbol("ETH"),
        base_currency=Currency.from_str("ETH"),
        quote_currency=Currency.from_str("USDC"),
        settlement_currency=Currency.from_str("USDC"),
        is_inverse=False,
        price_precision=1,
        size_precision=3,
        price_increment=Price.from_str("0.1"),
        size_increment=Quantity.from_str("0.001"),
        ts_event=0,
        ts_init=0,
        margin_init=Decimal("0.05"),
        margin_maint=Decimal("0.025"),
        maker_fee=Decimal("0.0002"),
        taker_fee=Decimal("0.0005"),
    )


def install_post_run_node_double(
    monkeypatch: pytest.MonkeyPatch,
    *,
    emit_fill: bool,
    extra_position: bool,
) -> None:
    """Replace only the run boundary after real input/catalog construction."""
    import nautilus_trader.backtest as backtest

    import trader_assist_v0.nautilus_g4.runner as runner_module

    class Value:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class Cache:
        def orders(self) -> tuple[object, ...]:
            return (
                Value(
                    client_order_id="order-1",
                    status="FILLED",
                    filled_qty="0.010",
                    avg_px="2001.0",
                ),
            )

        def positions(self) -> tuple[object, ...]:
            position = Value(
                id="position-1",
                instrument_id="ETH-USD-PERP.HYPERLIQUID",
                side="LONG",
                quantity="0.010",
            )
            if extra_position:
                return (position, Value(**position.__dict__))
            return (position,)

        def account_for_venue(self, _venue: object) -> object:
            return Value(id="account-1", account_type="MARGIN", base_currency="USDC")

    class Portfolio:
        pass

    Cache.__module__ = "nautilus_trader.cache.cache"
    Portfolio.__module__ = "nautilus_trader.portfolio.portfolio"

    class NodeDouble:
        def __init__(self, *, configs: list[object]) -> None:
            assert len(configs) == 1
            self.cache = Cache()
            self.portfolio = Portfolio()

        def build(self) -> None:
            pass

        def add_strategy_from_config(self, _run_id: object, _config: object) -> None:
            pass

        def run(self) -> list[object]:
            (ledger,) = runner_module._EXECUTION_LEDGERS.values()
            ledger.trigger_match_count = 1
            ledger.submission_count = 1
            ledger.submitted_client_order_id = "order-1"
            ledger.submitted_quantity = "0.010"
            if emit_fill:
                ledger.fills.append(
                    ProviderFillEvidence(
                        client_order_id="order-1",
                        venue_order_id="venue-1",
                        trade_id="trade-1",
                        event_id="event-1",
                        last_qty="0.010",
                        last_px="2001.0",
                        ts_event=1_700_000_000_000_000_002,
                        ts_init=1_700_000_000_000_000_003,
                        provider_event_type=(
                            "nautilus_trader.model.events.OrderFilled"
                        ),
                    )
                )
            return []

        def get_engine_cache(self, _run_id: object) -> object:
            return self.cache

        def get_engine_portfolio(self, _run_id: object) -> object:
            return self.portfolio

        def dispose(self) -> None:
            pass

    NodeDouble.__module__ = "nautilus_trader.backtest.node"
    monkeypatch.setattr(backtest, "BacktestNode", NodeDouble)


def fake_provider(monkeypatch: pytest.MonkeyPatch, *, quantity: str = "0.010") -> object:
    import nautilus_trader.model as model
    from nautilus_trader.model import InstrumentId, Quantity

    class ProviderInstrument:
        __module__ = "nautilus_trader.model.instruments.crypto_perpetual"

        id = InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID")
        quote_currency = "USDC"

        def __init__(self) -> None:
            self.make_qty_inputs: list[object] = []

        def make_qty(self, value: object) -> object:
            self.make_qty_inputs.append(value)
            return Quantity.from_str(quantity)

    monkeypatch.setattr(model, "CryptoPerpetual", ProviderInstrument)
    return ProviderInstrument()


@REQUIRES_NAUTILUS
def test_installed_rc5_and_provider_owned_fill_model_are_consumed() -> None:
    _assert_required_nautilus_available()
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    model = build_fill_model(execution_model())
    assert isinstance(model, ProbabilisticFillModel)


@REQUIRES_NAUTILUS
def test_exact_rc5_exposes_high_level_backtest_node_catalog_surface() -> None:
    _assert_required_nautilus_available()
    assert_backtest_node_catalog_surface()


@REQUIRES_NAUTILUS
def test_execute_provider_native_state_runs_real_rc5_hyperliquid_product_seam(
    tmp_path: Path,
) -> None:
    _assert_required_nautilus_available()
    assert_exact_nautilus_rc5()
    instrument = native_hyperliquid_instrument()
    trigger_quote = quote_tick(
        ts_event=1_700_000_000_000_000_000,
        ts_init=1_700_000_000_000_000_001,
    )
    projection = native_projection((trigger_quote,))
    trigger_hash = projection.identity.ordered_source_admission_hashes[0]

    evidence = execute_provider_native_state(
        projection=projection,
        intent=canonical_intent(),
        trigger_admission_hash=trigger_hash,
        provider_instrument=instrument,
        catalog_path=tmp_path / "real-product-seam",
    )

    assert isinstance(evidence, ProviderExecutionEvidence)
    assert evidence.authoritative_provider_runtime is True
    assert evidence.record.authoritative_provider_runtime is False
    assert evidence.provider_instrument_id == "ETH-USD-PERP.HYPERLIQUID"
    assert evidence.submitted_order_count == 1
    assert evidence.fill_count == 1
    assert evidence.position_count == 1
    assert evidence.account_count == 1
    assert evidence.simulation_only is True
    assert evidence.real_t2_credit is False
    assert evidence.g4_promotion is False


@pytest.mark.parametrize(
    ("emit_fill", "extra_position", "message"),
    (
        (False, False, "exactly one OrderFilled"),
        (True, True, "unexpected extra or missing"),
    ),
)
@REQUIRES_NAUTILUS
def test_execute_provider_native_state_fails_closed_on_post_run_attacks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    emit_fill: bool,
    extra_position: bool,
    message: str,
) -> None:
    _assert_required_nautilus_available()
    instrument = native_hyperliquid_instrument()
    trigger_quote = quote_tick(
        ts_event=1_700_000_000_000_000_000,
        ts_init=1_700_000_000_000_000_001,
    )
    projection = native_projection((trigger_quote,))
    install_post_run_node_double(
        monkeypatch,
        emit_fill=emit_fill,
        extra_position=extra_position,
    )

    with pytest.raises(RuntimeError, match=message):
        execute_provider_native_state(
            projection=projection,
            intent=canonical_intent(),
            trigger_admission_hash=(
                projection.identity.ordered_source_admission_hashes[0]
            ),
            provider_instrument=instrument,
            catalog_path=tmp_path / f"attack-{emit_fill}-{extra_position}",
        )


def test_candidate_execution_contexts_are_identity_isolated() -> None:
    reference = candidate("reference")
    challenger = candidate("challenger")
    assert candidate_state_isolation_plan((reference, challenger)) == (
        reference.candidate_hash,
        challenger.candidate_hash,
    )
    with pytest.raises(ValueError, match="duplicate candidate"):
        candidate_state_isolation_plan((reference, reference))


def test_backtest_node_contract_requires_only_public_cache_portfolio_route() -> None:
    assert BACKTEST_NODE_PUBLIC_METHODS == (
        "build",
        "run",
        "dispose",
        "get_engine_cache",
        "get_engine_portfolio",
    )
    assert "get_engine" not in BACKTEST_NODE_PUBLIC_METHODS


def test_provider_execution_api_has_no_strategy_economic_or_pass_inputs() -> None:
    assert tuple(inspect.signature(execute_provider_native_state).parameters) == (
        "projection",
        "intent",
        "trigger_admission_hash",
        "provider_instrument",
        "catalog_path",
    )
    source = inspect.getsource(execute_provider_native_state)
    assert "executable_price" not in source
    assert "economics" not in source
    assert "caller_pass" not in source


def test_canonical_direction_maps_mechanically_without_second_decision() -> None:
    assert _provider_order_side(PositionSide.LONG) == "BUY"
    assert _provider_order_side(PositionSide.SHORT) == "SELL"


def test_trigger_ledger_requires_full_identity_and_fails_on_second_match() -> None:
    trigger = {
        "instrument_id": "ETH-USD-PERP.HYPERLIQUID",
        "ts_event": 100,
        "ts_init": 101,
        "bid_price": "1999.0",
        "ask_price": "2001.0",
        "bid_size": "1.000",
        "ask_size": "1.000",
    }
    ledger = _ExecutionLedger(trigger_identity=trigger)
    near_collision = {**trigger, "bid_price": "1998.9"}
    assert ledger.observe_quote(near_collision) is False
    assert ledger.trigger_match_count == 0
    assert ledger.observe_quote(trigger) is True
    ledger.record_submission(client_order_id="order-1", quantity="0.010")
    with pytest.raises(RuntimeError, match="second matching"):
        ledger.observe_quote(trigger)
    with pytest.raises(RuntimeError, match="second provider order"):
        ledger.record_submission(client_order_id="order-2", quantity="0.010")


def test_fill_ledger_rejects_zero_duplicate_mismatch_and_non_provider_type() -> None:
    class NativeFill:
        def __init__(self, client_order_id: str) -> None:
            self.client_order_id = client_order_id
            self.venue_order_id = "venue-1"
            self.trade_id = "trade-1"
            self.event_id = "event-1"
            self.last_qty = "0.010"
            self.last_px = "2001.0"
            self.ts_event = 102
            self.ts_init = 103

    empty = _ExecutionLedger(trigger_identity={})
    assert empty.fills == []
    with pytest.raises(TypeError, match="provider-native"):
        empty.record_fill(object(), provider_fill_type=NativeFill)

    mismatched = _ExecutionLedger(trigger_identity={})
    mismatched.record_submission(client_order_id="order-1", quantity="0.010")
    with pytest.raises(RuntimeError, match="does not bind"):
        mismatched.record_fill(NativeFill("order-2"), provider_fill_type=NativeFill)

    duplicate = _ExecutionLedger(trigger_identity={})
    duplicate.record_submission(client_order_id="order-1", quantity="0.010")
    duplicate.record_fill(NativeFill("order-1"), provider_fill_type=NativeFill)
    with pytest.raises(RuntimeError, match="second provider-native"):
        duplicate.record_fill(NativeFill("order-1"), provider_fill_type=NativeFill)


@REQUIRES_NAUTILUS
def test_execution_inputs_bind_source_hash_full_quote_and_quantity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_required_nautilus_available()
    first = quote_tick()
    near_collision = quote_tick(bid_price="1998.9")
    projection = native_projection((first, near_collision))
    instrument = fake_provider(monkeypatch)
    selected = projection.identity.ordered_source_admission_hashes[0]
    _, trigger, side, quantity = _validate_execution_inputs(
        projection=projection,
        intent=canonical_intent(),
        trigger_admission_hash=selected,
        provider_instrument=instrument,
    )
    assert trigger.ts_event == 100
    assert trigger.bid_price == "1999.0"
    assert side == "BUY"
    assert Decimal(quantity) == Decimal("0.010")
    make_qty_inputs = instrument.make_qty_inputs
    assert make_qty_inputs == [0.01]
    assert type(make_qty_inputs[0]) is float


@REQUIRES_NAUTILUS
def test_execution_inputs_reject_missing_duplicate_non_quote_and_duplicate_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_required_nautilus_available()
    from nautilus_trader.model import (
        AggressorSide,
        InstrumentId,
        Price,
        Quantity,
        TradeId,
        TradeTick,
    )

    instrument = fake_provider(monkeypatch)
    intent = canonical_intent()
    quote = quote_tick()
    one = native_projection((quote,))
    with pytest.raises(ValueError, match="exactly once"):
        _validate_execution_inputs(
            projection=one,
            intent=intent,
            trigger_admission_hash="9" * 64,
            provider_instrument=instrument,
        )

    duplicate_hash = "8" * 64
    duplicate = native_projection(
        (quote, quote_tick(ts_event=102, ts_init=103)),
        source_hashes=(duplicate_hash, duplicate_hash),
    )
    with pytest.raises(ValueError, match="exactly once"):
        _validate_execution_inputs(
            projection=duplicate,
            intent=intent,
            trigger_admission_hash=duplicate_hash,
            provider_instrument=instrument,
        )

    trade = TradeTick(
        instrument_id=InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID"),
        price=Price.from_str("2000.0"),
        size=Quantity.from_str("0.010"),
        aggressor_side=AggressorSide.BUY,
        trade_id=TradeId("trade-1"),
        ts_event=100,
        ts_init=101,
    )
    non_quote = native_projection((trade,))
    with pytest.raises(ValueError, match="does not map to QuoteTick"):
        _validate_execution_inputs(
            projection=non_quote,
            intent=intent,
            trigger_admission_hash=non_quote.identity.ordered_source_admission_hashes[0],
            provider_instrument=instrument,
        )

    duplicate_content = native_projection((quote, quote))
    with pytest.raises(ValueError, match="second matching trigger"):
        _validate_execution_inputs(
            projection=duplicate_content,
            intent=intent,
            trigger_admission_hash=(
                duplicate_content.identity.ordered_source_admission_hashes[0]
            ),
            provider_instrument=instrument,
        )


@REQUIRES_NAUTILUS
def test_execution_inputs_reject_provider_type_identity_precision_and_invalid_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_required_nautilus_available()
    projection = native_projection((quote_tick(),))
    trigger = projection.identity.ordered_source_admission_hashes[0]
    intent = canonical_intent()
    with pytest.raises(TypeError, match="CryptoPerpetual"):
        _validate_execution_inputs(
            projection=projection,
            intent=intent,
            trigger_admission_hash=trigger,
            provider_instrument=object(),
        )

    drifted = fake_provider(monkeypatch, quantity="0.011")
    with pytest.raises(ValueError, match="round-trip"):
        _validate_execution_inputs(
            projection=projection,
            intent=intent,
            trigger_admission_hash=trigger,
            provider_instrument=drifted,
        )

    mismatched = fake_provider(monkeypatch)
    mismatched.id = type(mismatched.id).from_str("BTC-USD-PERP.HYPERLIQUID")
    with pytest.raises(ValueError, match="identity conflicts"):
        _validate_execution_inputs(
            projection=projection,
            intent=intent,
            trigger_admission_hash=trigger,
            provider_instrument=mismatched,
        )

    invalid_intent = HypotheticalOrderIntent.model_construct(
        **{**intent.model_dump(mode="python"), "order_intent_hash": "0" * 64}
    )
    with pytest.raises(ValidationError, match="order_intent_hash"):
        _validate_execution_inputs(
            projection=projection,
            intent=invalid_intent,
            trigger_admission_hash=trigger,
            provider_instrument=fake_provider(monkeypatch),
        )


@REQUIRES_NAUTILUS
def test_catalog_routes_all_native_types_and_reloads_exact_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _assert_required_nautilus_available()
    import nautilus_trader.persistence as persistence
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
        TradeId,
        TradeTick,
    )

    instrument_id = InstrumentId.from_str("ETH-USD-PERP.HYPERLIQUID")
    quote = quote_tick()
    trade = TradeTick(
        instrument_id=instrument_id,
        price=Price.from_str("2000.0"),
        size=Quantity.from_str("0.010"),
        aggressor_side=AggressorSide.BUY,
        trade_id=TradeId("trade-1"),
        ts_event=102,
        ts_init=103,
    )
    bar_type = BarType(
        instrument_id,
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    bar = Bar(
        bar_type=bar_type,
        open=Price.from_str("1999.0"),
        high=Price.from_str("2002.0"),
        low=Price.from_str("1998.0"),
        close=Price.from_str("2001.0"),
        volume=Quantity.from_str("2.000"),
        ts_event=104,
        ts_init=105,
    )
    projection = native_projection((quote, trade, bar))

    class Catalog:
        instance: Catalog | None = None

        def __init__(self, _path: str) -> None:
            self.instruments: list[object] = []
            self.quotes: list[object] = []
            self.trades: list[object] = []
            self.bars: list[object] = []
            Catalog.instance = self

        def write_instruments(self, values: list[object]) -> None:
            self.instruments.extend(values)

        def write_quote_ticks(self, values: list[object]) -> None:
            self.quotes.extend(values)

        def write_trade_ticks(self, values: list[object]) -> None:
            self.trades.extend(values)

        def write_bars(self, values: list[object]) -> None:
            self.bars.extend(values)

        def query_quote_ticks(self, **_kwargs: object) -> list[object]:
            return self.quotes

        def query_trade_ticks(self, **_kwargs: object) -> list[object]:
            return self.trades

        def query_bars(self, **_kwargs: object) -> list[object]:
            return self.bars

    monkeypatch.setattr(persistence, "ParquetDataCatalog", Catalog)
    provider = SimpleNamespace(id=instrument_id)
    _persist_and_reload_projection(
        catalog_path=tmp_path / "catalog",
        provider_instrument=provider,
        projection=projection,
    )
    assert Catalog.instance is not None
    assert Catalog.instance.instruments == [provider]
    assert Catalog.instance.quotes == [quote]
    assert Catalog.instance.trades == [trade]
    assert Catalog.instance.bars == [bar]


@REQUIRES_NAUTILUS
def test_new_engine_is_provider_native_and_disposable() -> None:
    _assert_required_nautilus_available()
    from nautilus_trader.backtest import BacktestEngine

    engine = new_isolated_backtest_engine(candidate("reference"))
    try:
        assert isinstance(engine, BacktestEngine)
        assert callable(engine.add_venue)
        assert callable(engine.add_instrument)
        assert callable(engine.add_data)
        assert callable(engine.add_strategy)
        assert callable(engine.run)
        assert engine.cache is not None
        assert engine.portfolio is not None
    finally:
        engine.dispose()


def test_formal_representative_scale_boundary_is_twenty_unique_markets() -> None:
    assert_representative_scale(tuple(f"market-{index:02d}" for index in range(20)))
    with pytest.raises(ValueError, match="at least 20"):
        assert_representative_scale(tuple(f"market-{index:02d}" for index in range(19)))


def test_actual_representative_scale_requires_source_bound_positive_events() -> None:
    evidence = tuple(
        RepresentativeMarketEvidence(
            market_id=sha256_hex(f"actual-market-{index}".encode()),
            instrument_id=f"ACTUAL-{index}.HYPERLIQUID",
            source_e4_manifest_hash="f" * 64,
            source_event_hashes=(sha256_hex(f"actual-event-{index}".encode()),),
            event_count=index + 1,
        )
        for index in range(20)
    )
    with pytest.raises(ValueError, match="retained market evidence"):
        assert_actual_representative_scale(())
    markets = assert_actual_representative_scale(evidence)
    assert len(markets) == 20
    with pytest.raises(ValidationError):
        RepresentativeMarketEvidence(
            market_id="generated-market-01",
            instrument_id="GENERATED.HYPERLIQUID",
            source_e4_manifest_hash="f" * 64,
            source_event_hashes=("e" * 64,),
            event_count=1,
        )


def test_provider_state_projection_uses_cache_portfolio_without_report_generation() -> None:
    class Value:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class Cache:
        def __init__(self, *, reverse: bool = False) -> None:
            self.reverse = reverse

        def orders(self) -> tuple[object, ...]:
            values = (
                Value(client_order_id="order-1", status="FILLED", filled_qty="1", avg_px="100"),
                Value(client_order_id="order-2", status="ACCEPTED", filled_qty="0", avg_px=None),
            )
            return tuple(reversed(values)) if self.reverse else values

        def positions(self) -> tuple[object, ...]:
            return (
                Value(id="position-1", instrument_id="ETH", side="LONG", quantity="1"),
            )

        def accounts(self) -> tuple[object, ...]:
            raise AssertionError("unsupported Cache.accounts must not be called")

        def account_for_venue(self, venue: object) -> object:
            assert venue == "SIM"
            return Value(
                id="account-1",
                account_type="MARGIN",
                base_currency="USD",
            )

        def generate_order_fills_report(self) -> None:
            raise AssertionError("pandas report generation must not be called")

    class Portfolio:
        def account(self, venue: object) -> object:
            raise AssertionError("resolved Cache account should be used")

        def generate_order_fills_report(self) -> None:
            raise AssertionError("pandas report generation must not be called")

    first = project_provider_native_state(Cache(), Portfolio(), venue="SIM")
    second = project_provider_native_state(Cache(reverse=True), Portfolio(), venue="SIM")
    assert first == second
    assert first.source_api == "NAUTILUS_CACHE_PORTFOLIO"
    assert first.filled_order_count == 1
    assert first.account_count == 1


def test_provider_state_projection_uses_account_type_and_public_lookup_fallbacks() -> None:
    class Account:
        id = "account-1"
        account_type = "MARGIN"
        base_currency = "USD"

        @property
        def type(self) -> object:
            raise AssertionError("legacy account type field must not be read")

    class CacheById:
        def orders(self) -> tuple[object, ...]:
            return ()

        def positions(self) -> tuple[object, ...]:
            return ()

        def account(self, account_id: object) -> object:
            assert account_id == "account-1"
            return Account()

    class CacheByPortfolio:
        def orders(self) -> tuple[object, ...]:
            return ()

        def positions(self) -> tuple[object, ...]:
            return ()

        def account(self, account_id: object) -> None:
            return None

        def account_for_venue(self, venue: object) -> None:
            return None

    class Portfolio:
        def account(self, venue: object) -> object:
            assert venue == "SIM"
            return Account()

    by_id = project_provider_native_state(
        CacheById(),
        Portfolio(),
        account_id="account-1",
    )
    by_portfolio = project_provider_native_state(
        CacheByPortfolio(),
        Portfolio(),
        venue="SIM",
    )
    assert by_id.account_count == 1
    assert by_portfolio.account_count == 1


def test_provider_state_cardinality_fails_closed_for_extra_or_unavailable_state() -> None:
    class Value:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class Cache:
        def __init__(self, *, extra_order: bool = False) -> None:
            self.extra_order = extra_order

        def orders(self) -> tuple[object, ...]:
            order = Value(
                client_order_id="order-1",
                status="FILLED",
                filled_qty="0.010",
                avg_px="2001.0",
            )
            return (order, order) if self.extra_order else (order,)

        def positions(self) -> tuple[object, ...]:
            return (
                Value(
                    id="position-1",
                    instrument_id="ETH-USD-PERP.HYPERLIQUID",
                    side="LONG",
                    quantity="0.010",
                ),
            )

        def account_for_venue(self, venue: object) -> object:
            assert venue == "HYPERLIQUID"
            return Value(id="account-1", account_type="MARGIN", base_currency="USDC")

    class Portfolio:
        pass

    Cache.__module__ = "nautilus_trader.cache.cache"
    Portfolio.__module__ = "nautilus_trader.portfolio.portfolio"
    state = _assert_single_provider_state(
        cache=Cache(),
        portfolio=Portfolio(),
        venue="HYPERLIQUID",
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        client_order_id="order-1",
        technical_quantity=Decimal("0.010"),
    )
    assert state.state_hash
    with pytest.raises(RuntimeError, match="unexpected extra"):
        _assert_single_provider_state(
            cache=Cache(extra_order=True),
            portfolio=Portfolio(),
            venue="HYPERLIQUID",
            instrument_id="ETH-USD-PERP.HYPERLIQUID",
            client_order_id="order-1",
            technical_quantity=Decimal("0.010"),
        )
    with pytest.raises(RuntimeError, match="missing public state methods"):
        _assert_single_provider_state(
            cache=object(),
            portfolio=Portfolio(),
            venue="HYPERLIQUID",
            instrument_id="ETH-USD-PERP.HYPERLIQUID",
            client_order_id="order-1",
            technical_quantity=Decimal("0.010"),
        )


def test_serializable_record_is_hash_bound_but_cannot_mint_accepted_evidence() -> None:
    trigger = TriggerQuoteEvidence(
        native_event_hash="1" * 64,
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        ts_event=100,
        ts_init=101,
        bid_price="1999.0",
        ask_price="2001.0",
        bid_size="1.000",
        ask_size="1.000",
    )
    fill = ProviderFillEvidence(
        client_order_id="order-1",
        venue_order_id="venue-1",
        trade_id="trade-1",
        event_id="event-1",
        last_qty="0.010",
        last_px="2001.0",
        ts_event=102,
        ts_init=103,
        provider_event_type="nautilus_trader.model.events.OrderFilled",
    )
    state = ProviderStateProjection(
        cache_type="nautilus_trader.cache.Cache",
        portfolio_type="nautilus_trader.portfolio.Portfolio",
        order_count=1,
        filled_order_count=1,
        position_count=1,
        account_count=1,
        state_hash="2" * 64,
    )
    values: dict[str, object] = {
        "schema_version": "PROVIDER_EXECUTION_STATE_V1",
        "projection_hash": "3" * 64,
        "ordered_source_admission_hashes": ("4" * 64,),
        "order_intent_hash": "5" * 64,
        "trigger_admission_hash": "4" * 64,
        "trigger": trigger.model_dump(mode="json"),
        "provider_instrument_id": "ETH-USD-PERP.HYPERLIQUID",
        "provider_instrument_type": (
            "nautilus_trader.model.instruments.crypto_perpetual.CryptoPerpetual"
        ),
        "submitted_client_order_id": "order-1",
        "submitted_side": "BUY",
        "submitted_technical_quantity": "0.010",
        "fill": fill.model_dump(mode="json"),
        "provider_state": state.model_dump(mode="json"),
        "event_count": 1,
        "quote_tick_count": 1,
        "trade_tick_count": 0,
        "bar_count": 0,
        "submitted_order_count": 1,
        "fill_count": 1,
        "position_count": 1,
        "account_count": 1,
        "simulation_only": True,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "live_venue_submitted": False,
        "real_t2_credit": False,
        "g4_promotion": False,
        "authoritative_provider_runtime": False,
    }
    record = ProviderExecutionRecord.create(**values)
    assert record.provider_state.state_hash == "2" * 64
    assert record.authoritative_provider_runtime is False
    assert not isinstance(record, ProviderExecutionEvidence)
    assert not hasattr(ProviderExecutionEvidence, "create")
    assert not hasattr(ProviderExecutionEvidence, "model_validate")
    with pytest.raises(TypeError, match="completed BacktestNode run"):
        ProviderExecutionEvidence(record=record, provider_state=state)
    with pytest.raises(ValidationError, match="evidence_hash"):
        ProviderExecutionRecord.model_validate(
            {**record.model_dump(mode="python"), "submitted_side": "SELL"}
        )
    with pytest.raises(ValidationError):
        ProviderExecutionRecord.create(**{**values, "simulation_only": False})


@REQUIRES_NAUTILUS
def test_module_name_spoof_cannot_mint_provider_runtime_provenance() -> None:
    _assert_required_nautilus_available()

    class FakeNode:
        pass

    FakeNode.__module__ = "nautilus_trader.backtest.node"
    quote = quote_tick()
    projection = native_projection((quote,))
    trigger_hash = projection.identity.ordered_source_admission_hashes[0]
    trigger = TriggerQuoteEvidence(
        native_event_hash=projection.identity.ordered_native_event_hashes[0],
        instrument_id=str(quote.instrument_id),
        ts_event=quote.ts_event,
        ts_init=quote.ts_init,
        bid_price=str(quote.bid_price),
        ask_price=str(quote.ask_price),
        bid_size=str(quote.bid_size),
        ask_size=str(quote.ask_size),
    )
    fill = ProviderFillEvidence(
        client_order_id="order-1",
        venue_order_id="venue-1",
        trade_id="trade-1",
        event_id="event-1",
        last_qty="0.010",
        last_px="2001.0",
        ts_event=102,
        ts_init=103,
        provider_event_type="nautilus_trader.model.events.OrderFilled",
    )
    with pytest.raises(TypeError, match="actual BacktestNode"):
        _mint_provider_execution_evidence(
            node=FakeNode(),
            run_config_id="run-1",
            venue="HYPERLIQUID",
            projection=projection,
            intent=canonical_intent(),
            trigger_admission_hash=trigger_hash,
            trigger=trigger,
            provider_instrument=native_hyperliquid_instrument(),
            submitted_client_order_id="order-1",
            submitted_side="BUY",
            submitted_quantity="0.010",
            fill=fill,
        )


def test_t0_t1_or_manual_controls_cannot_pass_causal_gates() -> None:
    synthetic = causal_claim_gate_states(
        evidence_tier="T0_SYNTHETIC_CONTROL",
        synthetic=True,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    manual = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=True,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    public_probe = causal_claim_gate_states(
        evidence_tier="T1_SAME_JOB_90S_PUBLIC_E4_PROBE",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert set(synthetic.values()) == {"NOT_PROVEN"}
    assert set(public_probe.values()) == {"NOT_PROVEN"}
    assert set(manual.values()) == {"NOT_PROVEN"}

    validation_missing = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=False,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert validation_missing["G4E2"] == "NOT_PROVEN"
    assert validation_missing["G4E5"] == "NOT_PROVEN"

    no_intent = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=False,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert no_intent["G4E2"] == "NOT_PROVEN"
    assert no_intent["G4E5"] == "NOT_PROVEN"


def test_t2_absence_and_synthetic_markets_remain_truthfully_not_proven(
    tmp_path: Path,
) -> None:
    absent = _representative_scale_probe(None)
    assert absent == {
        "status": "NOT_PROVEN",
        "representative_evidence_supplied": False,
        "actual_representative_market_count": 0,
        "reason": "NO_ACCEPTED_T2_REPRESENTATIVE_EVIDENCE_SUPPLIED",
    }

    identity: dict[str, object] = {
        "evidence_tier": "T2_REAL_CAUSAL_G4_ARTIFACT",
        "synthetic": True,
        "manual_substitution": False,
        "markets": [],
    }
    artifact = {
        **identity,
        "artifact_hash": sha256_hex(canonical_json_bytes(identity)),
    }
    path = tmp_path / "synthetic-representative-evidence.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic/manual evidence cannot count"):
        _representative_scale_probe(path)


def test_formal_acceptance_requires_every_g4_gate_to_genuinely_pass() -> None:
    gates = {f"G4E{index}": "PASS" for index in range(9)}
    assert formal_g4_acceptance(gates)
    gates["G4E5"] = "NOT_PROVEN"
    assert not formal_g4_acceptance(gates)
    gates["G4E5"] = "PASS"
    del gates["G4E8"]
    assert not formal_g4_acceptance(gates)
