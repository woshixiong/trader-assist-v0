# mypy: disable-error-code="import-not-found"
"""Thin exact-version public-data LiveNode composition for E4 Capture.

Nautilus owns transport, subscriptions, parsing and reconnect. Trade OS
receives normalized public objects only to add causal and Strategy evidence
semantics through its existing EvidenceStore. No execution client or order API
is present.
"""

from __future__ import annotations

import os
import resource
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Self, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .capture import CaptureSession, SubscriptionPolicy, recover_capture_session
from .contracts import (
    NAUTILUS_VERSION,
    AdmittedEvent,
    DataKind,
    EvidenceState,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    SourceEvent,
)
from .markettruth import (
    MARKETTRUTH_TOPIC,
    Depth10PublicationGate,
    MarketTruthFanout,
    MarketTruthFanoutHealth,
    MarketTruthRef,
    MarketTruthSubscriber,
)
from .safety import assert_public_only
from .storage import EvidenceStore

if TYPE_CHECKING:
    from nautilus_trader.model import Bar, BookType, OrderBookDepth10, QuoteTick, TradeTick

    class StrategyConfig:
        def __new__(cls, *args: object, **kwargs: object) -> Self: ...

        def __init__(self, *args: object, **kwargs: object) -> None: ...

    class _InstrumentCache(Protocol):
        def instrument(self, instrument_id: object) -> object | None: ...

    class Strategy:
        clock: Any
        cache: _InstrumentCache

        def __init__(self, config: StrategyConfig | None = None) -> None: ...

        def subscribe_bars(self, bar_type: object) -> None: ...

        def subscribe_quotes(self, instrument_id: object) -> None: ...

        def subscribe_trades(self, instrument_id: object) -> None: ...

        def subscribe_book_depth10(
            self, instrument_id: object, book_type: object
        ) -> None: ...

        def subscribe_socket_state(
            self,
            client_id: object | None = None,
            endpoint: str | None = None,
            priority: int | None = None,
        ) -> None: ...

        def publish_message(self, topic: str, message: object) -> None: ...

        def subscribe_topic(
            self, topic: str, handler: Callable[[object], None], priority: int = 0
        ) -> None: ...

else:
    from nautilus_trader.model import Bar, BookType, OrderBookDepth10, QuoteTick, TradeTick
    from nautilus_trader.trading import Strategy, StrategyConfig


class SocketStateChangedLike(Protocol):
    client_id: object
    venue: object
    endpoint: object
    state: object


class AdmittedEventObserver(Protocol):
    def __call__(
        self, event: AdmittedEvent, provider_instrument: object | None = None
    ) -> None: ...


class LiveNodeHandleLike(Protocol):
    def stop(self) -> None: ...


class LiveNodeLike(Protocol):
    def add_strategy(self, strategy: object) -> None: ...

    def run(self) -> None: ...

    def handle(self) -> LiveNodeHandleLike: ...

    def dispose(self) -> None: ...


def assert_exact_nautilus_version() -> str:
    """Fail closed unless the installed runtime is the selected exact baseline."""
    actual = version("nautilus-trader")
    if actual != NAUTILUS_VERSION:
        raise RuntimeError(f"exact Nautilus {NAUTILUS_VERSION} required; found {actual}")
    return actual


class NautilusE4CaptureStrategyConfig(StrategyConfig):
    """Serializable public-only subscription and evidence identity."""

    _CUSTOM_FIELDS = (
        "manifest_json",
        "snapshot_json",
        "expressions_json",
        "discovery_market_ids",
        "watch_market_ids",
        "actionable_market_ids",
        "bar_types",
        "evidence_root",
    )

    manifest_json: str
    snapshot_json: str
    expressions_json: str
    discovery_market_ids: tuple[str, ...]
    watch_market_ids: tuple[str, ...]
    actionable_market_ids: tuple[str, ...]
    bar_types: tuple[str, ...]
    evidence_root: str

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        for key in cls._CUSTOM_FIELDS:
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        manifest_json: str,
        snapshot_json: str,
        expressions_json: str,
        discovery_market_ids: tuple[str, ...],
        watch_market_ids: tuple[str, ...],
        actionable_market_ids: tuple[str, ...],
        bar_types: tuple[str, ...],
        evidence_root: str,
        **_kwargs: object,
    ) -> None:
        super().__init__()
        self.manifest_json = manifest_json
        self.snapshot_json = snapshot_json
        self.expressions_json = expressions_json
        self.discovery_market_ids = discovery_market_ids
        self.watch_market_ids = watch_market_ids
        self.actionable_market_ids = actionable_market_ids
        self.bar_types = bar_types
        self.evidence_root = evidence_root


class NautilusE4CaptureStrategy(Strategy):
    """Callbacks consume only normalized public QuoteTick/TradeTick/finalized Bar."""

    def __init__(self, config: NautilusE4CaptureStrategyConfig) -> None:
        super().__init__(config)
        actual_nautilus_version = assert_exact_nautilus_version()
        assert_public_only(env=os.environ)
        from pydantic import TypeAdapter

        self._manifest = RunManifest.model_validate_json(config.manifest_json)
        if self._manifest.nautilus_version != actual_nautilus_version:
            raise RuntimeError(
                "active Capture manifest/runtime Nautilus version mismatch: "
                f"manifest={self._manifest.nautilus_version} "
                f"runtime={actual_nautilus_version}"
            )
        self._snapshot = PitUniverseSnapshot.model_validate_json(config.snapshot_json)
        if self._manifest.pit_snapshot_hash != self._snapshot.snapshot_hash:
            raise ValueError("run manifest and PIT snapshot conflict")
        self._expressions = {
            item.instrument_id: item
            for item in TypeAdapter(tuple[MarketExpression, ...]).validate_json(
                config.expressions_json
            )
        }
        self._policy = SubscriptionPolicy(
            discovery=frozenset(config.discovery_market_ids),
            watch=frozenset(config.watch_market_ids),
            actionable=frozenset(config.actionable_market_ids),
        )
        self._bar_types = config.bar_types
        self._registered_bar_streams: set[tuple[str, DataKind]] = set()
        self._registered_depth10_streams: set[tuple[str, DataKind]] = set()
        self._markettruth_fanout = MarketTruthFanout()
        self._depth10_gate = Depth10PublicationGate()
        self._markettruth_subscribers: list[MarketTruthSubscriber] = []
        self._store = EvidenceStore(Path(config.evidence_root))
        if not self._store.manifest_path.exists():
            self._store.initialize(self._manifest, self._snapshot)
        else:
            self._store.verify_manifest_hash(self._manifest.manifest_hash)
            if self._store.load_snapshot() != self._snapshot:
                raise ValueError("existing PIT snapshot contradicts Capture config")
        self._session = recover_capture_session(
            manifest=self._manifest,
            policy=self._policy,
            raw_sink=None,
            evidence_store=self._store,
        )
        self._continuity_streams: set[tuple[str, DataKind]] = {
            (market_id, data_kind)
            for market_id in self._policy.watch | self._policy.actionable
            for data_kind in (DataKind.BBO, DataKind.TRADE, DataKind.DEPTH10)
        }
        self._session.await_continuity(required_streams=self._continuity_streams)
        self._admitted_event_observer: AdmittedEventObserver | None = None

    def set_admitted_event_observer(
        self, observer: AdmittedEventObserver | None
    ) -> None:
        """Attach one synchronous composition observer; E4 remains admission owner."""
        self._admitted_event_observer = observer

    @property
    def capture_session(self) -> CaptureSession:
        """Read-only composition access to the existing E4 semantic owner."""
        return self._session

    @property
    def markettruth_fanout_health(self) -> MarketTruthFanoutHealth:
        """Truthful health for the synchronous native component topic."""
        return self._markettruth_fanout.health

    def subscribe_markettruth(
        self, handler: Callable[[MarketTruthRef], None], *, priority: int = 0
    ) -> None:
        """Register a bounded project handler with observable typed failure."""
        subscriber = MarketTruthSubscriber(handler, self._markettruth_fanout)
        self._markettruth_subscribers.append(subscriber)
        self.subscribe_topic(MARKETTRUTH_TOPIC, subscriber, priority=priority)

    def open_structural_package(
        self,
        *,
        package_id: str,
        opportunity_id: str,
        thesis_id: str,
        market_id: str,
        expression_id: str,
        created_ts: int,
        active_valid_ts: int,
    ) -> EvidenceState:
        return self._session.open_structural_package(
            package_id=package_id,
            opportunity_id=opportunity_id,
            thesis_id=thesis_id,
            market_id=market_id,
            expression_id=expression_id,
            created_ts=created_ts,
            active_valid_ts=active_valid_ts,
        )

    def _observe_admission(self, outcome: object) -> None:
        observer = self._admitted_event_observer
        event = getattr(outcome, "event", None)
        if observer is None or event is None:
            return
        from nautilus_trader.model import InstrumentId

        provider_instrument = self.cache.instrument(
            InstrumentId.from_str(event.source.instrument_id)
        )
        observer(event, provider_instrument)

    @property
    def capture_health(self) -> dict[str, object]:
        health = self._session.health_summary()
        usage = resource.getrusage(resource.RUSAGE_SELF)
        return {
            **health,
            "markettruth_fanout": self._markettruth_fanout.health.__dict__,
            "resource_max_rss_native_units": usage.ru_maxrss,
            "resource_user_cpu_seconds": usage.ru_utime,
            "resource_system_cpu_seconds": usage.ru_stime,
        }

    @property
    def public_provider_observation(self) -> dict[str, object]:
        expected = self._continuity_streams
        observed = self._session.observed_streams
        missing = expected - observed
        rich_markets = self._policy.watch | self._policy.actionable
        expected_quotes = {(market_id, DataKind.BBO) for market_id in rich_markets}
        expected_trades = {(market_id, DataKind.TRADE) for market_id in rich_markets}
        expected_depth10 = {(market_id, DataKind.DEPTH10) for market_id in rich_markets}
        persisted_finalized_bars = {
            (item.source.market_id, item.source.data_kind)
            for item in self._store.load_admissions()
            if item.source.data_kind is DataKind.BAR
            and item.source.payload.get("finalized") is True
        }
        quote_observed = bool(expected_quotes) and expected_quotes <= observed
        trade_observed = bool(expected_trades) and expected_trades <= observed
        depth10_observed = bool(expected_depth10) and expected_depth10 <= observed
        bar_subscription_registered = bool(self._registered_bar_streams)
        finalized_bar_callback_observed = (
            bar_subscription_registered and self._registered_bar_streams <= observed
        )
        finalized_bar_evidence_persisted = (
            bar_subscription_registered
            and self._registered_bar_streams <= persisted_finalized_bars
        )
        provider_observation_pass = all(
            (
                quote_observed,
                trade_observed,
                depth10_observed,
                bar_subscription_registered,
                finalized_bar_callback_observed,
                finalized_bar_evidence_persisted,
            )
        )
        return {
            "expected_streams": [
                f"{market_id}:{data_kind.value}"
                for market_id, data_kind in sorted(
                    expected, key=lambda item: (item[0], item[1].value)
                )
            ],
            "observed_streams": [
                f"{market_id}:{data_kind.value}"
                for market_id, data_kind in sorted(
                    observed & expected, key=lambda item: (item[0], item[1].value)
                )
            ],
            "missing_streams": [
                f"{market_id}:{data_kind.value}"
                for market_id, data_kind in sorted(
                    missing, key=lambda item: (item[0], item[1].value)
                )
            ],
            "quote_observed": quote_observed,
            "trade_observed": trade_observed,
            "depth10_observed": depth10_observed,
            "bar_subscription_registered": bar_subscription_registered,
            "finalized_bar_callback_observed": finalized_bar_callback_observed,
            "finalized_bar_evidence_persisted": finalized_bar_evidence_persisted,
            "provider_observation_pass": provider_observation_pass,
        }

    def on_start(self) -> None:
        from nautilus_trader.model import BarType, InstrumentId

        by_market = {item.market_id: item for item in self._expressions.values()}
        self.subscribe_socket_state()
        for raw in self._bar_types:
            bar_type = BarType.from_str(raw)
            expression = self._expressions.get(str(bar_type.instrument_id))
            if expression is None:
                raise ValueError("bar subscription is outside the PIT snapshot")
            stream = (expression.market_id, DataKind.BAR)
            self.subscribe_bars(bar_type)
            self._registered_bar_streams.add(stream)
            self._continuity_streams.add(stream)
        rich_markets = self._policy.watch | self._policy.actionable
        for market_id in sorted(rich_markets):
            instrument_id = InstrumentId.from_str(by_market[market_id].instrument_id)
            self.subscribe_quotes(instrument_id)
            self.subscribe_trades(instrument_id)
            self.subscribe_book_depth10(instrument_id, BookType.L2_MBP)
            self._registered_depth10_streams.add((market_id, DataKind.DEPTH10))
        self._session.await_continuity(required_streams=self._continuity_streams)

    def on_quote(self, tick: QuoteTick) -> None:
        expression = self._expression_for(tick)
        payload = {
            "bid_price": str(tick.bid_price),
            "bid_size": str(tick.bid_size),
            "ask_price": str(tick.ask_price),
            "ask_size": str(tick.ask_size),
        }
        source = SourceEvent.create(
            market_id=expression.market_id,
            expression_id=expression.expression_id,
            provider_id="NAUTILUS_HYPERLIQUID",
            instrument_id=expression.instrument_id,
            data_kind=DataKind.BBO,
            source_event_id="bbo:" + sha256_hex(canonical_json_bytes(payload)),
            native_trade_id=None,
            provider_aggressor_side=None,
            event_context=f"block-time:{tick.ts_event}",
            ts_event=tick.ts_event,
            ts_init=tick.ts_init,
            true_network_receive_ts=None,
            payload=payload,
        )
        outcome = self._session.ingest(
            source, admission_ts=max(tick.ts_init, self.clock.timestamp_ns())
        )
        self._observe_admission(outcome)

    def on_trade(self, tick: TradeTick) -> None:
        expression = self._expression_for(tick)
        source = SourceEvent.create(
            market_id=expression.market_id,
            expression_id=expression.expression_id,
            provider_id="NAUTILUS_HYPERLIQUID",
            instrument_id=expression.instrument_id,
            data_kind=DataKind.TRADE,
            source_event_id=f"trade:{tick.trade_id}",
            native_trade_id=str(tick.trade_id),
            provider_aggressor_side=str(tick.aggressor_side),
            event_context=f"block-time:{tick.ts_event}",
            ts_event=tick.ts_event,
            ts_init=tick.ts_init,
            true_network_receive_ts=None,
            payload={"price": str(tick.price), "size": str(tick.size)},
        )
        outcome = self._session.ingest(
            source, admission_ts=max(tick.ts_init, self.clock.timestamp_ns())
        )
        self._observe_admission(outcome)

    def on_book_depth(self, depth: OrderBookDepth10) -> None:
        """Admit native rc5 Depth10 and fan out only immutable top-of-book facts."""
        expression = self._expression_for(depth)
        if not depth.bids or not depth.asks:
            self._markettruth_fanout.record_subscriber_failure(
                ValueError("INCOMPLETE_DEPTH10")
            )
            return
        bid, ask = depth.bids[0], depth.asks[0]
        payload = {
            "bid_price": str(bid.price), "bid_size": str(bid.size),
            "ask_price": str(ask.price), "ask_size": str(ask.size),
            "native_depth": 10,
        }
        source = SourceEvent.create(
            market_id=expression.market_id,
            expression_id=expression.expression_id,
            provider_id="NAUTILUS_HYPERLIQUID",
            instrument_id=expression.instrument_id,
            data_kind=DataKind.DEPTH10,
            source_event_id="depth10:" + sha256_hex(canonical_json_bytes(payload)),
            native_trade_id=None,
            provider_aggressor_side=None,
            event_context=f"native-depth10:{depth.ts_event}",
            ts_event=depth.ts_event, ts_init=depth.ts_init,
            true_network_receive_ts=None, payload=payload,
        )
        outcome = self._session.ingest(
            source, admission_ts=max(depth.ts_init, self.clock.timestamp_ns())
        )
        event = outcome.event
        if event is not None:
            rejection = self._depth10_gate.admit(
                market_id=event.source.market_id,
                ts_event=event.source.ts_event,
                ts_init=event.source.ts_init,
                admission_ts=event.admission_ts,
                continuity_complete=event.continuity_state is EvidenceState.COMPLETE,
            )
        else:
            rejection = "DEPTH10_DUPLICATE"
        if event is not None and rejection is None:
            markettruth = MarketTruthRef.create(
                market_id=event.source.market_id,
                instrument_id=event.source.instrument_id,
                source_event_id=event.source.source_event_id,
                ts_event=event.source.ts_event, ts_init=event.source.ts_init,
                continuity_epoch=event.continuity_epoch,
                bid_price=payload["bid_price"], bid_size=payload["bid_size"],
                ask_price=payload["ask_price"], ask_size=payload["ask_size"],
            )
            self._markettruth_fanout.publish(self.publish_message, markettruth)
        else:
            self._markettruth_fanout.record_subscriber_failure(
                ValueError(rejection or "DEPTH10_REJECTED")
            )
        self._observe_admission(outcome)

    def on_bar(self, bar: Bar) -> None:
        expression = self._expression_for(bar)
        source = SourceEvent.create(
            market_id=expression.market_id,
            expression_id=expression.expression_id,
            provider_id="NAUTILUS_HYPERLIQUID",
            instrument_id=expression.instrument_id,
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
        outcome = self._session.ingest(
            source, admission_ts=max(bar.ts_init, self.clock.timestamp_ns())
        )
        self._observe_admission(outcome)
        self._session.persist_durable_evidence(reason="FINALIZED_BAR_CALLBACK_ADMITTED")

    def on_socket_state(self, event: SocketStateChangedLike) -> None:
        from nautilus_trader.adapters.hyperliquid import HYPERLIQUID_CLIENT_ID

        self._session.handle_socket_state_event(
            event,
            expected_client_id=HYPERLIQUID_CLIENT_ID,
            required_streams=self._continuity_streams,
        )

    def on_stop(self) -> None:
        self._session.interrupt(reason="APPLICATION_STOP")
        self._session.persist_runtime_checkpoint(reason="GRACEFUL_STOP")
        self._session.write_operational_artifacts(health_overrides=self.capture_health)

    def _expression_for(
        self, event: QuoteTick | TradeTick | Bar | OrderBookDepth10
    ) -> MarketExpression:
        if isinstance(event, QuoteTick):
            instrument_id = str(event.instrument_id)
        elif isinstance(event, TradeTick):
            instrument_id = str(event.instrument_id)
        elif isinstance(event, Bar):
            instrument_id = str(event.bar_type.instrument_id)
        elif isinstance(event, OrderBookDepth10):
            instrument_id = str(event.instrument_id)
        else:
            raise TypeError(f"unsupported provider event type: {type(event).__name__}")
        try:
            return self._expressions[instrument_id]
        except KeyError as exc:
            raise ValueError("provider event instrument is outside the PIT snapshot") from exc


def build_public_data_node() -> LiveNodeLike:
    """Build, but do not run, the current exact public-data-only LiveNode."""
    assert_public_only(env=os.environ)
    assert_exact_nautilus_version()
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidDataClientConfig,
        HyperliquidDataClientFactory,
        HyperliquidEnvironment,
    )
    from nautilus_trader.common import Environment
    from nautilus_trader.live import LiveNode
    from nautilus_trader.model import TraderId

    builder = LiveNode.builder(
        "TRADEOS-E4-CAPTURE",
        TraderId("TRADEOS-E4-CAPTURE"),
        Environment.LIVE,
    )
    builder.add_data_client(
        None,
        HyperliquidDataClientFactory(),
        HyperliquidDataClientConfig(environment=HyperliquidEnvironment.MAINNET),
    )
    return cast(LiveNodeLike, builder.build())


def build_capture_strategy(
    *,
    manifest: RunManifest,
    snapshot: PitUniverseSnapshot,
    policy: SubscriptionPolicy,
    bar_types: tuple[str, ...],
    evidence_root: Path,
) -> NautilusE4CaptureStrategy:
    """Build the project semantic observer for attachment to a public-only node."""
    if manifest.pit_snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("manifest and PIT snapshot conflict")
    config = NautilusE4CaptureStrategyConfig(
        manifest_json=manifest.model_dump_json(),
        snapshot_json=snapshot.model_dump_json(),
        expressions_json="["
        + ",".join(item.model_dump_json() for item in snapshot.expressions)
        + "]",
        discovery_market_ids=tuple(sorted(policy.discovery)),
        watch_market_ids=tuple(sorted(policy.watch)),
        actionable_market_ids=tuple(sorted(policy.actionable)),
        bar_types=bar_types,
        evidence_root=str(evidence_root),
    )
    return NautilusE4CaptureStrategy(config)
