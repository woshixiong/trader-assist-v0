# mypy: disable-error-code="import-not-found"
"""Pinned provider-native data-only composition. Building never starts connectivity."""

from collections.abc import Callable
from importlib.metadata import version
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .admission import ExternalReferenceLedger
from .contracts import (
    BarPayload,
    BboPayload,
    BoundRecord,
    ContextPayload,
    ControlReplan,
    ExternalReferenceEvent,
    OpenInterestPayload,
    ProviderCapability,
    SourceMode,
    TimestampProvenance,
    TradePayload,
)

if TYPE_CHECKING:
    # Static shape only, following the existing E4 optional-runtime boundary.
    # Exact installed native inheritance and methods are qualified in Linux CI.
    class Strategy:
        def subscribe_bars(self, bar_type: object, *, client_id: object) -> None: ...

        def request_data(self, data_type: object, client_id: object) -> object: ...


RC5_VERSION = "2.0.0rc5"
RC5_SOURCE = "1b0a49d2792a9432a3aca3fcb617ce7a630d905e"


class ExternalReferenceNodeSpec(BoundRecord):
    provider: Literal["BINANCE", "OKX"]
    product: Literal["SPOT", "USD_M", "COIN_M", "SWAP"]
    instruments: tuple[str, ...] = Field(min_length=1, max_length=100)
    capabilities: tuple[ProviderCapability, ...]
    source_mode: Literal[SourceMode.LIVE] = SourceMode.LIVE
    depth_enabled: Literal[False] = False
    credentials: Literal[None] = None

    @model_validator(mode="after")
    def validate_matrix(self) -> Self:
        if len(set(self.instruments)) != len(self.instruments):
            raise ValueError("duplicate native instrument")
        if self.provider == "BINANCE" and self.product == "SWAP":
            raise ValueError("wrong Binance product")
        if self.provider == "OKX" and self.product not in {"SPOT", "SWAP"}:
            raise ValueError("wrong OKX product")
        keys = [c.datatype for c in self.capabilities]
        if len(keys) != len(set(keys)) or not {"BAR_1M", "BAR_5M", "TRADE", "BBO"} <= set(keys):
            raise ValueError("complete unique core matrix required")
        if not {"MARK", "INDEX", "FUNDING", "OI"} <= set(keys):
            raise ValueError("context exposure dispositions required")
        for c in self.capabilities:
            if (c.provider, c.venue, c.product, c.source_mode) != (
                self.provider,
                self.provider,
                self.product,
                self.source_mode,
            ):
                raise ValueError("provider/product/mode substitution")
            c.require_core_proof()
            if c.datatype in {"DEPTH10", "L2"} and c.enabled:
                raise ValueError("external depth is disabled in this bounded composition")
            expected_owner = (
                "OKX_PUBLIC_STDLIB"
                if self.provider == "OKX" and c.datatype == "OI" and c.source_exposes
                else "NAUTILUS_RC5"
            )
            if c.adapter_owner != expected_owner:
                raise ValueError("capability owner substitution")
        return self


class NativeSemanticProfile(BoundRecord):
    """Explicit semantics proven for the selected callback, not inferred from a declaration."""

    datatype: str
    capability_hash: str
    proof_locator: str = Field(min_length=1)
    bar_timestamp_meaning: Literal["OPEN", "CLOSE", "NOT_APPLICABLE"]
    bar_finality_proven: bool
    trade_semantics: Literal["TRADE", "AGGREGATED_TRADE", "NOT_APPLICABLE"]
    unit: str = Field(min_length=1)
    period: str = Field(min_length=1)


class ExternalReferenceObserver:
    def __init__(
        self,
        ledger: ExternalReferenceLedger,
        profiles: tuple[NativeSemanticProfile, ...],
        clock: Callable[[], int],
    ) -> None:
        self.ledger = ledger
        self.profiles = {
            p.datatype: NativeSemanticProfile.model_validate_json(p.model_dump_json())
            for p in profiles
        }
        if len(self.profiles) != len(profiles):
            raise ValueError("duplicate semantic profile")
        for datatype, profile in self.profiles.items():
            matches = [c for c in ledger.admission.capabilities
                       if c.record_hash == profile.capability_hash and c.datatype == datatype]
            if len(matches) != 1 or matches[0].adapter_owner != "NAUTILUS_RC5":
                raise ValueError("semantic profile/capability binding mismatch")
        self.clock = clock

    def on_native(self, datatype: str, native: Any) -> None:
        profile = self.profiles[datatype]
        observed = self.clock()
        admission = self.ledger.admission
        capability = next(
            c for c in admission.capabilities if c.record_hash == profile.capability_hash
        )
        native_id = str(
            native.instrument_id
            if datatype not in {"BAR_1M", "BAR_5M"}
            else native.bar_type.instrument_id
        )
        mapping = admission.resolver.resolve(
            capability.provider,
            native_id,
            native.ts_event,
            observed,
            production=admission.production,
        )
        payload: Any
        if datatype == "BBO":
            payload = BboPayload(
                bid=str(native.bid_price),
                ask=str(native.ask_price),
                bid_size=str(native.bid_size),
                ask_size=str(native.ask_size),
            )
        elif datatype == "TRADE":
            if profile.trade_semantics == "NOT_APPLICABLE":
                raise ControlReplan("native trade semantics unproven")
            payload = TradePayload(
                price=str(native.price),
                size=str(native.size),
                native_id=str(native.trade_id),
                aggressor=str(native.aggressor_side),
                trade_semantics=profile.trade_semantics,
            )
        elif datatype in {"BAR_1M", "BAR_5M"}:
            if not profile.bar_finality_proven or profile.bar_timestamp_meaning == "NOT_APPLICABLE":
                raise ControlReplan("native bar finality/timestamp semantics unproven")
            minutes = 1 if datatype == "BAR_1M" else 5
            duration = minutes * 60_000_000_000
            start = (
                native.ts_event
                if profile.bar_timestamp_meaning == "OPEN"
                else (native.ts_event - duration)
            )
            payload = BarPayload(
                interval_minutes=cast(Literal[1, 5], minutes),
                start_ns=start,
                end_ns=start + duration,
                timestamp_meaning=profile.bar_timestamp_meaning,
                finalized=True,
                aggregation_origin=f"{capability.provider}:NATIVE_EXTERNAL",
                open=str(native.open),
                high=str(native.high),
                low=str(native.low),
                close=str(native.close),
                volume=str(native.volume),
            )
        elif datatype in {"MARK", "INDEX", "FUNDING"}:
            payload = ContextPayload(
                field=cast(Literal["MARK", "INDEX", "FUNDING"], datatype),
                value=str(native.rate if datatype == "FUNDING" else native.value),
                unit=profile.unit,
                period=profile.period,
                settlement_ns=native.next_funding_ns if datatype == "FUNDING" else None,
            )
        elif datatype == "OI" and capability.provider == "BINANCE":
            payload = OpenInterestPayload(
                oi=str(native.open_interest),
                oi_ccy=None,
                oi_usd=None,
                oi_unit=profile.unit,
                oi_ccy_unit="NOT_EXPOSED",
            )
        else:
            raise ControlReplan("native datatype dispatch unproven")
        identity = (
            str(native.trade_id)
            if datatype == "TRADE"
            else sha256_hex(
                canonical_json_bytes(
                    {
                        "instrument": native_id,
                        "ts_event": native.ts_event,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
            )
        )
        rights = admission.dataset.rights
        assert rights is not None
        event = ExternalReferenceEvent.create(
            version="1",
            provider=capability.provider,
            venue=capability.venue,
            product=mapping.product,
            instrument_id=native_id,
            mapping_hash=admission.resolver.snapshot.record_hash,
            dataset_hash=admission.dataset.record_hash,
            capability_hash=capability.record_hash,
            rights_hash=rights.record_hash,
            source_mode=capability.source_mode,
            native_id=identity,
            sequence=None,
            timestamps=TimestampProvenance(
                source_ts=str(native.ts_event),
                source_unit="ns",
                ts_event=native.ts_event,
                ts_init=native.ts_init,
                true_network_receive_ts=None,
                receive_provenance="NOT_EXPOSED",
                observed_at_ns=observed,
            ),
            payload=payload,
        )
        self.ledger.observe(event, evaluated_at_ns=observed)


def build_external_reference_node(
    spec: ExternalReferenceNodeSpec, observer: ExternalReferenceObserver
) -> Any:
    spec = ExternalReferenceNodeSpec.model_validate_json(spec.model_dump_json())
    if version("nautilus_trader") != RC5_VERSION:
        raise RuntimeError("exact Nautilus rc5 required")
    # Import only the pinned data owners. No execution factory or arbitrary config is accepted.
    from nautilus_trader import model
    from nautilus_trader.live import LiveNode, LiveNodeConfig
    if not TYPE_CHECKING:
        from nautilus_trader.trading import Strategy

    configs: dict[str, Any] = {}
    factories: dict[str, Any] = {}
    if spec.provider == "BINANCE":
        from nautilus_trader.adapters.binance import (
            BinanceDataClientConfig,
            BinanceDataClientFactory,
            BinanceInstrumentProviderConfig,
            BinanceProductType,
            BinanceSpotMarketDataMode,
        )

        configs["BINANCE"] = BinanceDataClientConfig(
            product_type=getattr(BinanceProductType, spec.product),
            spot_market_data_mode=BinanceSpotMarketDataMode.Json,
            instrument_provider=BinanceInstrumentProviderConfig(
                load_all=False, load_ids=list(spec.instruments), query_commission_rates=False
            ),
            api_key=None,
            api_secret=None,
            proxy_url=None,
        )
        factories["BINANCE"] = BinanceDataClientFactory()
    else:
        from nautilus_trader.adapters.okx import (
            OKXDataClientConfig,
            OKXDataClientFactory,
            OKXInstrumentType,
        )

        configs["OKX"] = OKXDataClientConfig(
            instrument_types=[getattr(OKXInstrumentType, spec.product)],
            instrument_families=sorted(
                {i.rsplit(".", 1)[0].removesuffix("-SWAP") for i in spec.instruments}
            ),
            api_key=None,
            api_secret=None,
            api_passphrase=None,
            proxy_url=None,
            load_spreads=False,
        )
        factories["OKX"] = OKXDataClientFactory()

    class NativeObserver(Strategy):
        def on_start(self) -> None:
            client = model.ClientId(spec.provider)
            for text in spec.instruments:
                instrument = model.InstrumentId.from_str(text)
                for capability in spec.capabilities:
                    if not capability.enabled or capability.source_exposes is not True:
                        continue
                    datatype = capability.datatype
                    if datatype.startswith("BAR_"):
                        minutes = 1 if datatype == "BAR_1M" else 5
                        bar = model.BarType.from_str(f"{text}-{minutes}-MINUTE-LAST-EXTERNAL")
                        self.subscribe_bars(bar, client_id=client)
                    elif datatype in {"BBO", "TRADE", "MARK", "INDEX", "FUNDING"}:
                        method = {
                            "BBO": "subscribe_quotes",
                            "TRADE": "subscribe_trades",
                            "MARK": "subscribe_mark_prices",
                            "INDEX": "subscribe_index_prices",
                            "FUNDING": "subscribe_funding_rates",
                        }[datatype]
                        getattr(self, method)(instrument, client_id=client)
                    elif datatype == "OI" and spec.provider == "BINANCE":
                        self.request_data(
                            model.DataType(
                                "BinanceFuturesOpenInterest", metadata={"instrument_id": text}
                            ),
                            client,
                        )
                    # OKX OI is explicitly one-shot outside this node; never substitute rc5.

        def on_quote(self, data: Any) -> None:
            observer.on_native("BBO", data)

        def on_trade(self, data: Any) -> None:
            observer.on_native("TRADE", data)

        def on_bar(self, data: Any) -> None:
            text = str(data.bar_type)
            observer.on_native("BAR_5M" if "-5-MINUTE-" in text else "BAR_1M", data)

        def on_mark_price(self, data: Any) -> None:
            observer.on_native("MARK", data)

        def on_index_price(self, data: Any) -> None:
            observer.on_native("INDEX", data)

        def on_funding_rate(self, data: Any) -> None:
            observer.on_native("FUNDING", data)

        def on_data(self, data: Any) -> None:
            if type(data).__name__ == "BinanceFuturesOpenInterest":
                observer.on_native("OI", data)

    node = LiveNode.build(
        "ExternalReference",
        LiveNodeConfig(data_clients=configs, exec_clients={}, load_state=False, save_state=False),
        data_factories=factories,
        exec_factories={},
    )
    node.add_strategy(NativeObserver())
    return node
