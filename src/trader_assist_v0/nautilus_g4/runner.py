# mypy: disable-error-code="import-not-found"
"""Thin Nautilus rc5 execution seam for Ordinary VNext G4 development replay."""

from __future__ import annotations

import hmac
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_g4.catalog_bridge import NativeReplayProjection
from trader_assist_v0.vnext_g4.contracts import (
    NAUTILUS_VERSION,
    REPRESENTATIVE_MARKET_FLOOR,
    CandidateManifest,
    ExecutionModelConfig,
    HypotheticalOrderIntent,
    PositionSide,
)

if TYPE_CHECKING:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.backtest import BacktestNode as _NautilusBacktestNode
    from nautilus_trader.execution import ProbabilisticFillModel

    class _QuantityInstrument(Protocol):
        def make_qty(self, value: float) -> object: ...

    class _MechanicalCache(Protocol):
        def instrument(self, instrument_id: object) -> _QuantityInstrument | None: ...

    class _MechanicalOrder(Protocol):
        client_order_id: object

    class _MechanicalOrderFactory(Protocol):
        def market(
            self,
            *,
            instrument_id: object,
            order_side: object,
            quantity: object,
        ) -> _MechanicalOrder: ...

    class _NautilusStrategyConfig:
        def __new__(cls, *args: object, **kwargs: object) -> Self: ...

        def __init__(self, **kwargs: object) -> None: ...

    class _NautilusStrategy:
        cache: _MechanicalCache
        order_factory: _MechanicalOrderFactory

        def __init__(self, config: object | None = None) -> None: ...

        def subscribe_quotes(self, instrument_id: object) -> None: ...

        def submit_order(self, order: object) -> None: ...

    class _NautilusOrderFilled: ...


class RepresentativeMarketEvidence(BaseModel):
    """One actual accepted source market; generated labels cannot enter G4E8."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: Sha256Hex
    instrument_id: str = Field(min_length=3, max_length=160)
    source_kind: Literal["ACCEPTED_E4_CAUSAL"] = "ACCEPTED_E4_CAUSAL"
    source_e4_manifest_hash: Sha256Hex
    source_event_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    event_count: int = Field(gt=0)


class ProviderStateProjection(BaseModel):
    """Deterministic observation of provider-owned Cache/Portfolio state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_api: Literal["NAUTILUS_CACHE_PORTFOLIO"] = "NAUTILUS_CACHE_PORTFOLIO"
    cache_type: str
    portfolio_type: str
    order_count: int = Field(ge=0)
    filled_order_count: int = Field(ge=0)
    position_count: int = Field(ge=0)
    account_count: int = Field(ge=0)
    state_hash: Sha256Hex


BACKTEST_NODE_PUBLIC_METHODS = (
    "build",
    "run",
    "dispose",
    "get_engine_cache",
    "get_engine_portfolio",
)

_PROVIDER_EXECUTION_DOMAIN = b"trader-assist-v0/nautilus-g4/provider-execution/v1\0"
_TRIGGER_FIELDS = (
    "instrument_id",
    "ts_event",
    "ts_init",
    "bid_price",
    "ask_price",
    "bid_size",
    "ask_size",
)


class TriggerQuoteEvidence(BaseModel):
    """Exact source-bound QuoteTick selected by its R1 admission identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    native_event_hash: Sha256Hex
    instrument_id: str
    ts_event: int = Field(ge=0)
    ts_init: int = Field(ge=0)
    bid_price: str
    ask_price: str
    bid_size: str
    ask_size: str


class ProviderFillEvidence(BaseModel):
    """The sole provider-native OrderFilled callback bound to the submitted order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    client_order_id: str = Field(min_length=1)
    venue_order_id: str = Field(min_length=1)
    trade_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    last_qty: str = Field(min_length=1)
    last_px: str = Field(min_length=1)
    ts_event: int = Field(ge=0)
    ts_init: int = Field(ge=0)
    provider_event_type: str = Field(min_length=1)


class ProviderExecutionRecord(BaseModel):
    """Serializable run record; alone it is not provider-runtime evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["PROVIDER_EXECUTION_STATE_V1"] = (
        "PROVIDER_EXECUTION_STATE_V1"
    )
    projection_hash: Sha256Hex
    ordered_source_admission_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    order_intent_hash: Sha256Hex
    trigger_admission_hash: Sha256Hex
    trigger: TriggerQuoteEvidence
    provider_instrument_id: str
    provider_instrument_type: str
    submitted_client_order_id: str = Field(min_length=1)
    submitted_side: Literal["BUY", "SELL"]
    submitted_technical_quantity: str = Field(min_length=1)
    fill: ProviderFillEvidence
    provider_state: ProviderStateProjection
    event_count: int = Field(ge=1)
    quote_tick_count: int = Field(ge=1)
    trade_tick_count: int = Field(ge=0)
    bar_count: int = Field(ge=0)
    submitted_order_count: Literal[1] = 1
    fill_count: Literal[1] = 1
    position_count: Literal[1] = 1
    account_count: Literal[1] = 1
    simulation_only: Literal[True] = True
    private_api: Literal[False] = False
    signing: Literal[False] = False
    exchange_write: Literal[False] = False
    live_venue_submitted: Literal[False] = False
    real_t2_credit: Literal[False] = False
    g4_promotion: Literal[False] = False
    authoritative_provider_runtime: Literal[False] = False
    evidence_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        expected = sha256_hex(
            _PROVIDER_EXECUTION_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.evidence_hash, expected):
            raise ValueError("evidence_hash does not bind provider execution evidence")
        if self.fill.client_order_id != self.submitted_client_order_id:
            raise ValueError("provider fill does not bind the submitted client_order_id")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        digest = sha256_hex(_PROVIDER_EXECUTION_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "evidence_hash": digest})


class ProviderExecutionEvidence:
    """Capability minted only from a completed, genuine rc5 BacktestNode run."""

    __slots__ = ("_node", "_record")
    _node: object
    _record: ProviderExecutionRecord

    def __new__(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError(
            "ProviderExecutionEvidence is minted only from a completed BacktestNode run"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise TypeError("ProviderExecutionEvidence is immutable")

    @property
    def record(self) -> ProviderExecutionRecord:
        return self._record

    @property
    def authoritative_provider_runtime(self) -> Literal[True]:
        return True

    def __getattr__(self, name: str) -> object:
        return getattr(self._record, name)


def _quote_identity(tick: object) -> dict[str, object]:
    values = {name: getattr(tick, name) for name in _TRIGGER_FIELDS}
    return {
        "instrument_id": str(values["instrument_id"]),
        "ts_event": int(values["ts_event"]),
        "ts_init": int(values["ts_init"]),
        "bid_price": str(values["bid_price"]),
        "ask_price": str(values["ask_price"]),
        "bid_size": str(values["bid_size"]),
        "ask_size": str(values["ask_size"]),
    }


def _optional_attr(value: object, name: str) -> object | None:
    return getattr(value, name, None)


def _required_attr(value: object, name: str) -> object:
    result = getattr(value, name, None)
    if result is None:
        raise ValueError(f"provider-native value lacks required public field {name}")
    return result


def _decimal_quantity(value: object, *, label: str) -> Decimal:
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError(f"{label} is not a decimal quantity") from exc
    if not quantity.is_finite() or quantity <= 0:
        raise RuntimeError(f"{label} must be a positive finite quantity")
    return quantity


@dataclass(slots=True)
class _ExecutionLedger:
    trigger_identity: dict[str, object]
    trigger_match_count: int = 0
    submission_count: int = 0
    submitted_client_order_id: str | None = None
    submitted_quantity: str | None = None
    fills: list[ProviderFillEvidence] = field(default_factory=list)

    def observe_quote(self, actual: dict[str, object]) -> bool:
        if actual != self.trigger_identity:
            return False
        self.trigger_match_count += 1
        if self.trigger_match_count != 1 or self.submission_count != 0:
            raise RuntimeError("second matching source-bound trigger failed closed")
        return True

    def record_submission(self, *, client_order_id: object, quantity: object) -> None:
        self.submission_count += 1
        if self.submission_count != 1 or self.submitted_client_order_id is not None:
            raise RuntimeError("second provider order submission failed closed")
        self.submitted_client_order_id = str(client_order_id)
        self.submitted_quantity = str(quantity)

    def record_fill(self, event: object, *, provider_fill_type: type[object]) -> None:
        if not isinstance(event, provider_fill_type):
            raise TypeError("fill callback did not receive provider-native OrderFilled")
        if self.submitted_client_order_id is None:
            raise RuntimeError("provider fill arrived before the sole order submission")
        values = {
            "client_order_id": getattr(event, "client_order_id", None),
            "venue_order_id": getattr(event, "venue_order_id", None),
            "trade_id": getattr(event, "trade_id", None),
            "event_id": getattr(event, "event_id", None),
            "last_qty": getattr(event, "last_qty", None),
            "last_px": getattr(event, "last_px", None),
            "ts_event": getattr(event, "ts_event", None),
            "ts_init": getattr(event, "ts_init", None),
        }
        if any(value is None for value in values.values()):
            raise RuntimeError("provider OrderFilled is missing required public fields")
        fill = ProviderFillEvidence(
            client_order_id=str(values["client_order_id"]),
            venue_order_id=str(values["venue_order_id"]),
            trade_id=str(values["trade_id"]),
            event_id=str(values["event_id"]),
            last_qty=str(values["last_qty"]),
            last_px=str(values["last_px"]),
            ts_event=int(str(values["ts_event"])),
            ts_init=int(str(values["ts_init"])),
            provider_event_type=f"{type(event).__module__}.{type(event).__qualname__}",
        )
        self.fills.append(fill)
        if len(self.fills) != 1:
            raise RuntimeError("second provider-native OrderFilled failed closed")
        if fill.client_order_id != self.submitted_client_order_id:
            raise RuntimeError("provider fill does not bind the submitted client_order_id")


_EXECUTION_LEDGERS: dict[str, _ExecutionLedger] = {}


if not TYPE_CHECKING:
    try:
        from nautilus_trader.backtest import BacktestNode as _NautilusBacktestNode
        from nautilus_trader.model import OrderFilled as _NautilusOrderFilled
        from nautilus_trader.trading import Strategy as _NautilusStrategy
        from nautilus_trader.trading import StrategyConfig as _NautilusStrategyConfig
    except ModuleNotFoundError:
        # Keep non-Nautilus contract tests importable; execution still fails at the rc5 gate.
        class _NautilusBacktestNode:
            pass

        class _NautilusStrategyConfig:
            def __init__(self, **_kwargs: object) -> None:
                pass

        class _NautilusStrategy:
            def __init__(self, _config: object | None = None) -> None:
                pass

        class _NautilusOrderFilled:
            pass


class ProviderExecutionStrategyConfig(_NautilusStrategyConfig):
    """Serializable identities for the mechanical provider submission hook."""

    _CUSTOM_FIELDS = (
        "ledger_key",
        "instrument_id",
        "order_side",
        "technical_quantity",
        *(f"trigger_{name}" for name in _TRIGGER_FIELDS[1:]),
    )

    ledger_key: str
    instrument_id: str
    order_side: str
    technical_quantity: str
    trigger_ts_event: int
    trigger_ts_init: int
    trigger_bid_price: str
    trigger_ask_price: str
    trigger_bid_size: str
    trigger_ask_size: str

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        for key in cls._CUSTOM_FIELDS:
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        ledger_key: str,
        instrument_id: str,
        order_side: str,
        technical_quantity: str,
        trigger_ts_event: int,
        trigger_ts_init: int,
        trigger_bid_price: str,
        trigger_ask_price: str,
        trigger_bid_size: str,
        trigger_ask_size: str,
        **_kwargs: object,
    ) -> None:
        super().__init__()
        if order_side not in {"BUY", "SELL"}:
            raise ValueError("unsupported provider order side")
        _decimal_quantity(technical_quantity, label="technical quantity")
        self.ledger_key = ledger_key
        self.instrument_id = instrument_id
        self.order_side = order_side
        self.technical_quantity = technical_quantity
        self.trigger_ts_event = trigger_ts_event
        self.trigger_ts_init = trigger_ts_init
        self.trigger_bid_price = trigger_bid_price
        self.trigger_ask_price = trigger_ask_price
        self.trigger_bid_size = trigger_bid_size
        self.trigger_ask_size = trigger_ask_size


class ProviderExecutionStrategy(_NautilusStrategy):
    """Mechanical exact-QuoteTick hook with no strategy-economic authority."""

    def __init__(self, config: ProviderExecutionStrategyConfig) -> None:
        super().__init__(config)
        from nautilus_trader.model import InstrumentId

        self._ledger_key = config.ledger_key
        self._instrument_id = InstrumentId.from_str(config.instrument_id)
        self._order_side = config.order_side
        self._technical_quantity = _decimal_quantity(
            config.technical_quantity,
            label="technical quantity",
        )
        expected_trigger = {
            "instrument_id": config.instrument_id,
            "ts_event": config.trigger_ts_event,
            "ts_init": config.trigger_ts_init,
            "bid_price": config.trigger_bid_price,
            "ask_price": config.trigger_ask_price,
            "bid_size": config.trigger_bid_size,
            "ask_size": config.trigger_ask_size,
        }
        ledger = _EXECUTION_LEDGERS.get(self._ledger_key)
        if ledger is None or ledger.trigger_identity != expected_trigger:
            raise RuntimeError("Strategy trigger identity conflicts with execution ledger")

    def on_start(self) -> None:
        self.subscribe_quotes(self._instrument_id)

    def on_quote(self, tick: object) -> None:
        from nautilus_trader.model import OrderSide

        ledger = _EXECUTION_LEDGERS[self._ledger_key]
        if not ledger.observe_quote(_quote_identity(tick)):
            return
        instrument = self.cache.instrument(self._instrument_id)
        if instrument is None:
            raise RuntimeError("provider instrument is absent from Strategy cache")
        quantity = instrument.make_qty(float(self._technical_quantity))
        if _decimal_quantity(quantity, label="provider quantity") != self._technical_quantity:
            raise RuntimeError("provider make_qty changed technical quantity semantics")
        side = OrderSide.BUY if self._order_side == "BUY" else OrderSide.SELL
        order = self.order_factory.market(
            instrument_id=self._instrument_id,
            order_side=side,
            quantity=quantity,
        )
        ledger.record_submission(
            client_order_id=order.client_order_id,
            quantity=quantity,
        )
        self.submit_order(order)

    def on_order_filled(self, event: object) -> None:
        _EXECUTION_LEDGERS[self._ledger_key].record_fill(
            event,
            provider_fill_type=_NautilusOrderFilled,
        )


def _provider_order_side(side: PositionSide) -> Literal["BUY", "SELL"]:
    if side is PositionSide.LONG:
        return "BUY"
    if side is PositionSide.SHORT:
        return "SELL"
    raise ValueError("unsupported canonical intent side")


def _validate_execution_inputs(
    *,
    projection: NativeReplayProjection,
    intent: HypotheticalOrderIntent,
    trigger_admission_hash: str,
    provider_instrument: object,
) -> tuple[object, TriggerQuoteEvidence, Literal["BUY", "SELL"], str]:
    from nautilus_trader.model import Bar, CryptoPerpetual, QuoteTick, TradeTick

    if type(projection) is not NativeReplayProjection:
        raise TypeError("exact NativeReplayProjection is required")
    if type(intent) is not HypotheticalOrderIntent:
        raise TypeError("exact HypotheticalOrderIntent is required")
    revalidated = HypotheticalOrderIntent.model_validate(intent.model_dump(mode="python"))
    if revalidated != intent or not intent.not_submitted or intent.venue_submitted:
        raise ValueError("canonical hypothetical intent identity is invalid")
    identity = projection.identity
    source_hashes = identity.ordered_source_admission_hashes
    if source_hashes.count(trigger_admission_hash) != 1:
        raise ValueError("trigger_admission_hash must occur exactly once in R1 identity")
    trigger_index = source_hashes.index(trigger_admission_hash)
    trigger = projection.events[trigger_index]
    if not isinstance(trigger, QuoteTick):
        raise ValueError("source-bound trigger does not map to QuoteTick")
    if not isinstance(provider_instrument, CryptoPerpetual):
        raise TypeError("provider instrument must be provider-native CryptoPerpetual")
    provider_type = (
        f"{type(provider_instrument).__module__}."
        f"{type(provider_instrument).__qualname__}"
    )
    if not provider_type.startswith("nautilus_trader."):
        raise TypeError("provider instrument type is not owned by Nautilus")
    provider_id = str(getattr(provider_instrument, "id", ""))
    if provider_id != identity.instrument_id or not provider_id.endswith(".HYPERLIQUID"):
        raise ValueError("provider Instrument identity conflicts with R1 projection")

    typed_counts = {QuoteTick: 0, TradeTick: 0, Bar: 0}
    for event in projection.events:
        matched_type = next(
            (native_type for native_type in typed_counts if isinstance(event, native_type)),
            None,
        )
        if matched_type is None:
            raise TypeError("R1 projection contains unsupported native event type")
        typed_counts[matched_type] += 1
        event_instrument = (
            event.bar_type.instrument_id
            if isinstance(event, Bar)
            else _optional_attr(event, "instrument_id")
        )
        if str(event_instrument) != identity.instrument_id:
            raise ValueError("R1 projection contains mixed instrument identity")
    if (
        typed_counts[QuoteTick],
        typed_counts[TradeTick],
        typed_counts[Bar],
    ) != (
        identity.quote_tick_count,
        identity.trade_tick_count,
        identity.bar_count,
    ):
        raise ValueError("R1 projection native type counts conflict with its identity")

    trigger_identity = _quote_identity(trigger)
    matching_quotes = tuple(
        event
        for event in projection.events
        if isinstance(event, QuoteTick) and _quote_identity(event) == trigger_identity
    )
    if len(matching_quotes) != 1:
        raise ValueError("source replay contains a second matching trigger QuoteTick")

    requested_quantity = intent.technical_quantity.quantity
    native_quantity = provider_instrument.make_qty(float(requested_quantity))
    if _decimal_quantity(native_quantity, label="provider quantity") != requested_quantity:
        raise ValueError("technical quantity does not round-trip through provider make_qty")
    quantity_text = str(native_quantity)
    trigger_evidence = TriggerQuoteEvidence.model_validate(
        {
            "native_event_hash": identity.ordered_native_event_hashes[trigger_index],
            **trigger_identity,
        }
    )
    return trigger, trigger_evidence, _provider_order_side(intent.side), quantity_text


def _persist_and_reload_projection(
    *,
    catalog_path: Path,
    provider_instrument: object,
    projection: NativeReplayProjection,
) -> None:
    from nautilus_trader.model import Bar, QuoteTick, TradeTick
    from nautilus_trader.persistence import ParquetDataCatalog

    if catalog_path.exists():
        if not catalog_path.is_dir() or any(catalog_path.iterdir()):
            raise ValueError("provider execution catalog path must be absent or empty")
    else:
        catalog_path.mkdir(parents=True)
    catalog = ParquetDataCatalog(str(catalog_path))
    catalog.write_instruments([provider_instrument])
    quote_ticks: tuple[QuoteTick, ...] = tuple(
        event for event in projection.events if isinstance(event, QuoteTick)
    )
    trade_ticks: tuple[TradeTick, ...] = tuple(
        event for event in projection.events if isinstance(event, TradeTick)
    )
    bars: tuple[Bar, ...] = tuple(
        event for event in projection.events if isinstance(event, Bar)
    )
    if quote_ticks:
        catalog.write_quote_ticks(quote_ticks)
    if trade_ticks:
        catalog.write_trade_ticks(trade_ticks)
    if bars:
        catalog.write_bars(bars)

    instrument_id = projection.identity.instrument_id
    reloaded_quotes = tuple(catalog.query_quote_ticks(identifiers=[instrument_id]))
    reloaded_trades = tuple(catalog.query_trade_ticks(identifiers=[instrument_id]))
    bar_ids = tuple(dict.fromkeys(str(event.bar_type) for event in bars))
    reloaded_bars = (
        tuple(catalog.query_bars(identifiers=list(bar_ids))) if bar_ids else ()
    )
    if reloaded_quotes != quote_ticks:
        raise RuntimeError("typed catalog QuoteTick read changed content or order")
    if reloaded_trades != trade_ticks:
        raise RuntimeError("typed catalog TradeTick read changed content or order")
    if reloaded_bars != bars:
        raise RuntimeError("typed catalog Bar read changed content or order")
    if len(quote_ticks) + len(trade_ticks) + len(bars) != projection.identity.event_count:
        raise RuntimeError("typed catalog routing silently dropped a replay event")


def _assert_single_provider_state(
    *,
    cache: object,
    portfolio: object,
    venue: object,
    instrument_id: str,
    client_order_id: str,
    technical_quantity: Decimal,
) -> ProviderStateProjection:
    state = project_provider_native_state(cache, portfolio, venue=venue)
    if (
        state.order_count,
        state.filled_order_count,
        state.position_count,
        state.account_count,
    ) != (1, 1, 1, 1):
        raise RuntimeError("unexpected extra or missing provider order/fill/position/account state")
    if not state.cache_type.startswith("nautilus_trader.") or not state.portfolio_type.startswith(
        "nautilus_trader."
    ):
        raise RuntimeError("provider state is not owned by Nautilus Cache/Portfolio")
    orders_method = getattr(cache, "orders", None)
    positions_method = getattr(cache, "positions", None)
    if not callable(orders_method) or not callable(positions_method):
        raise RuntimeError("provider Cache public state is unavailable")
    orders = tuple(_as_collection(orders_method(), name="orders"))
    positions = tuple(_as_collection(positions_method(), name="positions"))
    if str(getattr(orders[0], "client_order_id", "")) != client_order_id:
        raise RuntimeError("provider Cache order does not bind the submitted client_order_id")
    if str(_optional_attr(orders[0], "status") or "") != "FILLED":
        raise RuntimeError("sole provider order is not in FILLED state")
    if _decimal_quantity(
        _optional_attr(orders[0], "filled_qty"),
        label="provider filled quantity",
    ) != technical_quantity:
        raise RuntimeError("provider filled quantity changed canonical technical quantity")
    if str(getattr(positions[0], "instrument_id", "")) != instrument_id:
        raise RuntimeError("provider position does not bind the selected instrument")
    if _decimal_quantity(
        _optional_attr(positions[0], "quantity"),
        label="provider position quantity",
    ) != technical_quantity:
        raise RuntimeError("provider position quantity changed canonical technical quantity")
    return state


def _mint_provider_execution_evidence(
    *,
    node: object,
    run_config_id: str,
    venue: object,
    projection: NativeReplayProjection,
    intent: HypotheticalOrderIntent,
    trigger_admission_hash: str,
    trigger: TriggerQuoteEvidence,
    provider_instrument: object,
    submitted_client_order_id: str,
    submitted_side: Literal["BUY", "SELL"],
    submitted_quantity: str,
    fill: ProviderFillEvidence,
) -> ProviderExecutionEvidence:
    """Validate the completed native run and mint its non-serializable capability."""
    if not isinstance(node, _NautilusBacktestNode):
        raise TypeError("provider-runtime provenance requires an actual BacktestNode")
    cache = node.get_engine_cache(run_config_id)
    portfolio = node.get_engine_portfolio(run_config_id)
    if cache is None or portfolio is None:
        raise RuntimeError("BacktestNode did not retain public Cache/Portfolio state")
    identity = projection.identity
    provider_state = _assert_single_provider_state(
        cache=cache,
        portfolio=portfolio,
        venue=venue,
        instrument_id=identity.instrument_id,
        client_order_id=submitted_client_order_id,
        technical_quantity=intent.technical_quantity.quantity,
    )
    record = ProviderExecutionRecord.create(
        schema_version="PROVIDER_EXECUTION_STATE_V1",
        projection_hash=identity.projection_hash,
        ordered_source_admission_hashes=identity.ordered_source_admission_hashes,
        order_intent_hash=intent.order_intent_hash,
        trigger_admission_hash=trigger_admission_hash,
        trigger=trigger.model_dump(mode="json"),
        provider_instrument_id=identity.instrument_id,
        provider_instrument_type=(
            f"{type(provider_instrument).__module__}."
            f"{type(provider_instrument).__qualname__}"
        ),
        submitted_client_order_id=submitted_client_order_id,
        submitted_side=submitted_side,
        submitted_technical_quantity=submitted_quantity,
        fill=fill.model_dump(mode="json"),
        provider_state=provider_state.model_dump(mode="json"),
        event_count=identity.event_count,
        quote_tick_count=identity.quote_tick_count,
        trade_tick_count=identity.trade_tick_count,
        bar_count=identity.bar_count,
        submitted_order_count=1,
        fill_count=1,
        position_count=provider_state.position_count,
        account_count=provider_state.account_count,
        simulation_only=True,
        private_api=False,
        signing=False,
        exchange_write=False,
        live_venue_submitted=False,
        real_t2_credit=False,
        g4_promotion=False,
        authoritative_provider_runtime=False,
    )
    evidence = object.__new__(ProviderExecutionEvidence)
    object.__setattr__(evidence, "_record", record)
    object.__setattr__(evidence, "_node", node)
    return evidence


def execute_provider_native_state(
    *,
    projection: NativeReplayProjection,
    intent: HypotheticalOrderIntent,
    trigger_admission_hash: str,
    provider_instrument: object,
    catalog_path: str | Path,
) -> ProviderExecutionEvidence:
    """Run one simulation-only source-bound order through rc5 BacktestNode."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.model import (
        AccountType,
        BookType,
        CryptoPerpetual,
        Currency,
        OmsType,
        TraderId,
    )
    from nautilus_trader.trading import ImportableStrategyConfig

    assert_backtest_node_catalog_surface()
    _, trigger_evidence, order_side, quantity_text = _validate_execution_inputs(
        projection=projection,
        intent=intent,
        trigger_admission_hash=trigger_admission_hash,
        provider_instrument=provider_instrument,
    )
    catalog_root = Path(catalog_path)
    _persist_and_reload_projection(
        catalog_path=catalog_root,
        provider_instrument=provider_instrument,
        projection=projection,
    )

    identity = projection.identity
    if not isinstance(provider_instrument, CryptoPerpetual):
        raise TypeError("provider instrument must be provider-native CryptoPerpetual")
    provider_instrument_id = provider_instrument.id
    timestamps = tuple(
        int(str(_required_attr(event, "ts_init"))) for event in projection.events
    )
    catalog_path_text = str(catalog_root)
    start_time = min(timestamps)
    end_time = max(timestamps) + 1
    data: list[BacktestDataConfig] = []
    if identity.quote_tick_count:
        data.append(
            BacktestDataConfig(
                data_type="QuoteTick",
                catalog_path=catalog_path_text,
                instrument_id=provider_instrument_id,
                start_time=start_time,
                end_time=end_time,
            )
        )
    if identity.trade_tick_count:
        data.append(
            BacktestDataConfig(
                data_type="TradeTick",
                catalog_path=catalog_path_text,
                instrument_id=provider_instrument_id,
                start_time=start_time,
                end_time=end_time,
            )
        )
    if identity.bar_count:
        data.append(
            BacktestDataConfig(
                data_type="Bar",
                catalog_path=catalog_path_text,
                instrument_id=provider_instrument_id,
                start_time=start_time,
                end_time=end_time,
            )
        )
    quote_currency = _optional_attr(provider_instrument, "quote_currency")
    if quote_currency is None:
        raise ValueError("provider CryptoPerpetual lacks public quote_currency")
    venue = _optional_attr(provider_instrument_id, "venue")
    if venue is None:
        raise ValueError("provider InstrumentId lacks public venue")
    venue_config = BacktestVenueConfig(
        name=str(venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        base_currency=Currency.from_str(str(quote_currency)),
        starting_balances=[f"1_000_000 {quote_currency}"],
    )
    config = BacktestRunConfig(
        venues=[venue_config],
        data=data,
        engine=BacktestEngineConfig(
            trader_id=TraderId(f"R2-{identity.projection_hash[:16]}"),
            bypass_logging=True,
            run_analysis=False,
        ),
        dispose_on_completion=False,
    )
    ledger_key = sha256_hex(
        canonical_json_bytes(
            {
                "projection_hash": identity.projection_hash,
                "order_intent_hash": intent.order_intent_hash,
                "trigger_admission_hash": trigger_admission_hash,
            }
        )
    )
    if ledger_key in _EXECUTION_LEDGERS:
        raise RuntimeError("provider execution identity is already active")
    trigger_config = trigger_evidence.model_dump(
        mode="python",
        exclude={"native_event_hash", "instrument_id"},
    )
    strategy_config = ImportableStrategyConfig(
        strategy_path=(
            "trader_assist_v0.nautilus_g4.runner:ProviderExecutionStrategy"
        ),
        config_path=(
            "trader_assist_v0.nautilus_g4.runner:ProviderExecutionStrategyConfig"
        ),
        config={
            "ledger_key": ledger_key,
            "instrument_id": identity.instrument_id,
            "order_side": order_side,
            "technical_quantity": quantity_text,
            **{f"trigger_{name}": value for name, value in trigger_config.items()},
        },
    )
    ledger = _ExecutionLedger(trigger_identity=_quote_identity(projection.events[
        identity.ordered_source_admission_hashes.index(trigger_admission_hash)
    ]))
    _EXECUTION_LEDGERS[ledger_key] = ledger
    node = BacktestNode(configs=[config])
    try:
        node.build()
        node.add_strategy_from_config(config.id, strategy_config)
        node.run()
        cache = node.get_engine_cache(config.id)
        portfolio = node.get_engine_portfolio(config.id)
        if cache is None or portfolio is None:
            raise RuntimeError("BacktestNode did not retain public Cache/Portfolio state")
        if ledger.trigger_match_count != 1 or ledger.submission_count != 1:
            raise RuntimeError("exact source-bound trigger did not submit exactly one order")
        if ledger.submitted_client_order_id is None or ledger.submitted_quantity is None:
            raise RuntimeError("provider submission identity is unavailable")
        if _decimal_quantity(
            ledger.submitted_quantity,
            label="submitted quantity",
        ) != intent.technical_quantity.quantity:
            raise RuntimeError("submitted quantity changed canonical technical quantity")
        if len(ledger.fills) != 1:
            raise RuntimeError("provider execution did not produce exactly one OrderFilled")
        fill = ledger.fills[0]
        if _decimal_quantity(
            fill.last_qty,
            label="provider fill last_qty",
        ) != intent.technical_quantity.quantity:
            raise RuntimeError("provider fill quantity changed canonical technical quantity")
        _assert_single_provider_state(
            cache=cache,
            portfolio=portfolio,
            venue=venue,
            instrument_id=identity.instrument_id,
            client_order_id=ledger.submitted_client_order_id,
            technical_quantity=intent.technical_quantity.quantity,
        )
        submitted_client_order_id = ledger.submitted_client_order_id
        submitted_quantity = ledger.submitted_quantity
        evidence = _mint_provider_execution_evidence(
            node=node,
            run_config_id=config.id,
            venue=venue,
            projection=projection,
            intent=intent,
            trigger_admission_hash=trigger_admission_hash,
            trigger=trigger_evidence,
            provider_instrument=provider_instrument,
            submitted_client_order_id=submitted_client_order_id,
            submitted_side=order_side,
            submitted_quantity=submitted_quantity,
            fill=fill,
        )
    finally:
        node.dispose()
        _EXECUTION_LEDGERS.pop(ledger_key, None)
    return evidence


def causal_claim_gate_states(
    *,
    evidence_tier: Literal[
        "T0_SYNTHETIC_CONTROL",
        "T1_SAME_JOB_90S_PUBLIC_E4_PROBE",
        "T2_REAL_CAUSAL_G4_ARTIFACT",
    ],
    synthetic: bool,
    manual_substitution: bool,
    deterministic_replay_proven: bool,
    semantic_derivation_proven: bool,
    validation_materialized: bool,
    canonical_order_intent_proven: bool,
    provider_outcome_cost_provenance_complete: bool,
    restart_equivalence_proven: bool,
) -> dict[str, str]:
    """Map evidence topology to causal gates without promoting controls."""
    if (
        evidence_tier != "T2_REAL_CAUSAL_G4_ARTIFACT"
        or synthetic
        or manual_substitution
    ):
        return {name: "NOT_PROVEN" for name in ("G4E1", "G4E2", "G4E5", "G4E7")}
    g4e1 = "PASS" if deterministic_replay_proven else "NOT_PROVEN"
    g4e2 = (
        "PASS"
        if deterministic_replay_proven
        and semantic_derivation_proven
        and validation_materialized
        and canonical_order_intent_proven
        else "NOT_PROVEN"
    )
    g4e5 = (
        "PASS"
        if g4e2 == "PASS" and provider_outcome_cost_provenance_complete
        else "NOT_PROVEN"
    )
    g4e7 = "PASS" if restart_equivalence_proven else "NOT_PROVEN"
    return {"G4E1": g4e1, "G4E2": g4e2, "G4E5": g4e5, "G4E7": g4e7}


def formal_g4_acceptance(gates: Mapping[str, str]) -> bool:
    """Formal acceptance is total over exactly G4E0..G4E8; no vacuous PASS."""
    required = tuple(f"G4E{index}" for index in range(9))
    return set(gates) == set(required) and all(gates[name] == "PASS" for name in required)


def assert_exact_nautilus_rc5() -> None:
    from importlib.metadata import version

    installed = version("nautilus-trader")
    if installed != NAUTILUS_VERSION:
        raise RuntimeError(f"expected Nautilus {NAUTILUS_VERSION}, installed {installed}")


def build_fill_model(config: ExecutionModelConfig) -> ProbabilisticFillModel:
    """Map explicit project assumptions onto Nautilus' provider-owned fill model."""
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    return ProbabilisticFillModel(
        prob_fill_on_limit=float(config.prob_fill_on_limit),
        prob_slippage=float(config.prob_slippage),
        random_seed=config.random_seed,
    )


def new_isolated_backtest_engine(candidate: CandidateManifest) -> BacktestEngine:
    """Create one fresh Nautilus engine per candidate; simulated state is never shared."""
    from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.model import TraderId

    assert_exact_nautilus_rc5()
    config = BacktestEngineConfig(
        trader_id=TraderId(f"VNEXT-G4-{candidate.candidate_hash[:16]}"),
        bypass_logging=True,
    )
    return BacktestEngine(config)


def assert_backtest_node_catalog_surface() -> None:
    """Fail closed unless the exact rc5 high-level catalog replay surface is available."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.persistence import ParquetDataCatalog

    assert_exact_nautilus_rc5()
    public_types = (
        BacktestNode,
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
        ParquetDataCatalog,
    )
    if not all(callable(item) for item in public_types):
        raise RuntimeError("exact rc5 high-level catalog replay surface is incomplete")
    missing = tuple(
        name
        for name in BACKTEST_NODE_PUBLIC_METHODS
        if not callable(getattr(BacktestNode, name, None))
    )
    if missing:
        raise RuntimeError(f"exact rc5 BacktestNode is missing public methods: {missing}")


def _as_collection(value: object, *, name: str) -> Collection[object]:
    if isinstance(value, dict):
        return tuple(value.values())
    if isinstance(value, Collection) and not isinstance(value, str | bytes):
        return value
    raise RuntimeError(f"Nautilus Cache {name} did not return a public collection")


def _identity_rows(values: Collection[object], fields: tuple[str, ...]) -> list[dict[str, str]]:
    rows = [
        {field: str(getattr(value, field, None)) for field in fields}
        for value in values
    ]
    return sorted(rows, key=lambda row: tuple(row.values()))


def _provider_account(
    cache: object,
    portfolio: object,
    *,
    venue: object | None,
    account_id: object | None,
) -> object:
    """Resolve one known run account through rc5 public lookup methods only."""
    lookup_available = False
    account = None
    if account_id is not None:
        lookup = getattr(cache, "account", None)
        if callable(lookup):
            lookup_available = True
            account = lookup(account_id)
    if account is None and venue is not None:
        for owner, name in (
            (cache, "account_for_venue"),
            (portfolio, "account"),
        ):
            lookup = getattr(owner, name, None)
            if callable(lookup):
                lookup_available = True
                account = lookup(venue)
                if account is not None:
                    break
    if not lookup_available:
        raise RuntimeError("Nautilus Cache/Portfolio lacks a public account lookup method")
    if account is None:
        raise RuntimeError("known run account was not found in provider-owned state")
    return account


def project_provider_native_state(
    cache: object,
    portfolio: object,
    *,
    venue: object | None = None,
    account_id: object | None = None,
) -> ProviderStateProjection:
    """Project public Cache/Portfolio state without raw-engine or report access."""
    if venue is None and account_id is None:
        raise ValueError("known run venue or account identity is required")
    orders_method = getattr(cache, "orders", None)
    positions_method = getattr(cache, "positions", None)
    methods = {"orders": orders_method, "positions": positions_method}
    missing = tuple(name for name, method in methods.items() if not callable(method))
    if missing:
        raise RuntimeError(f"Nautilus Cache is missing public state methods: {missing}")
    assert callable(orders_method)
    assert callable(positions_method)
    orders = _as_collection(orders_method(), name="orders")
    positions = _as_collection(positions_method(), name="positions")
    account = _provider_account(
        cache,
        portfolio,
        venue=venue,
        account_id=account_id,
    )
    accounts = (account,)
    cache_type = f"{type(cache).__module__}.{type(cache).__qualname__}"
    portfolio_type = f"{type(portfolio).__module__}.{type(portfolio).__qualname__}"
    filled_orders = tuple(
        item for item in orders if str(getattr(item, "filled_qty", "0")) not in {"0", "0.0"}
    )
    payload = {
        "source_api": "NAUTILUS_CACHE_PORTFOLIO",
        "cache_type": cache_type,
        "portfolio_type": portfolio_type,
        "orders": _identity_rows(
            orders,
            ("client_order_id", "status", "filled_qty", "avg_px"),
        ),
        "positions": _identity_rows(
            positions,
            ("id", "instrument_id", "side", "quantity"),
        ),
        "accounts": _identity_rows(
            accounts,
            ("id", "account_type", "base_currency"),
        ),
    }
    return ProviderStateProjection(
        cache_type=cache_type,
        portfolio_type=portfolio_type,
        order_count=len(orders),
        filled_order_count=len(filled_orders),
        position_count=len(positions),
        account_count=len(accounts),
        state_hash=sha256_hex(canonical_json_bytes(payload)),
    )


def assert_representative_scale(market_ids: tuple[str, ...]) -> None:
    unique = set(market_ids)
    if len(unique) != len(market_ids):
        raise ValueError("representative-scale market identities must be unique")
    if len(unique) < REPRESENTATIVE_MARKET_FLOOR:
        raise ValueError(
            f"formal G4 scale requires at least {REPRESENTATIVE_MARKET_FLOOR} markets"
        )


def assert_actual_representative_scale(
    evidence: tuple[RepresentativeMarketEvidence, ...],
) -> tuple[str, ...]:
    """Accept G4E8 only for source-bound markets with actual retained events."""
    if not evidence:
        raise ValueError("actual representative scale requires retained market evidence")
    markets = tuple(sorted(item.market_id for item in evidence))
    if len(markets) != len(set(markets)):
        raise ValueError("representative-scale market identities must be unique")
    if len({item.source_e4_manifest_hash for item in evidence}) != 1:
        raise ValueError("representative markets must bind one accepted E4 source manifest")
    all_event_hashes = tuple(
        event_hash for item in evidence for event_hash in item.source_event_hashes
    )
    if len(all_event_hashes) != len(set(all_event_hashes)):
        raise ValueError("representative causal event identities must be unique")
    assert_representative_scale(markets)
    return markets


def candidate_state_isolation_plan(
    candidates: tuple[CandidateManifest, ...],
) -> tuple[str, ...]:
    """Return exact candidate hashes requiring independent engine/context state."""
    hashes = tuple(candidate.candidate_hash for candidate in candidates)
    if len(hashes) != len(set(hashes)):
        raise ValueError("duplicate candidate identity would violate comparison isolation")
    return hashes
