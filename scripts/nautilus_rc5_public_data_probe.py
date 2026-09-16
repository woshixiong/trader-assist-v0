# mypy: disable-error-code="import-not-found"
"""Qualification-only Nautilus 2.0.0rc5 public-data probe.

This module is intentionally outside the accepted E4 runtime.  It proves whether
rc5 public objects and Hyperliquid public-data callbacks can feed the existing
Trade OS SourceEvent -> CausalAdmissionLedger -> EvidenceStore semantics without
editing or bypassing the accepted rc4 host/version guards.
"""

from __future__ import annotations

import argparse
import threading
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.causal import CausalAdmissionLedger
from trader_assist_v0.nautilus_e4.contracts import DataKind, MarketExpression, SourceEvent
from trader_assist_v0.nautilus_e4.storage import EvidenceStore

if TYPE_CHECKING:
    from nautilus_trader.model import Bar, QuoteTick, TradeTick

    class StrategyConfig:
        def __new__(cls, *args: object, **kwargs: object) -> Self: ...

        def __init__(self, *args: object, **kwargs: object) -> None: ...

    class Strategy:
        clock: Any

        def __init__(self, config: StrategyConfig | None = None) -> None: ...

        def subscribe_bars(self, bar_type: object) -> None: ...

        def subscribe_quotes(self, instrument_id: object) -> None: ...

        def subscribe_trades(self, instrument_id: object) -> None: ...

        def subscribe_socket_state(self, priority: int | None = None) -> None: ...

else:
    from nautilus_trader.model import Bar, QuoteTick, TradeTick
    from nautilus_trader.trading import Strategy, StrategyConfig

PASS = 0
PROVIDER_DATA_INCOMPLETE = 2
APPLICATION_FAILURE = 3
RC5_VERSION = "2.0.0rc5"


class LiveNodeHandleLike:
    def stop(self) -> None: ...


class LiveNodeLike:
    def add_strategy(self, strategy: object) -> None: ...

    def run(self) -> None: ...

    def handle(self) -> LiveNodeHandleLike: ...

    def dispose(self) -> None: ...


class Rc5QualificationStrategyConfig(StrategyConfig):
    """Qualification-only public-data subscription identity."""

    _CUSTOM_FIELDS = ("expression_json", "bar_type", "evidence_root")

    expression_json: str
    bar_type: str
    evidence_root: str

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        for key in cls._CUSTOM_FIELDS:
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        expression_json: str,
        bar_type: str,
        evidence_root: str,
        **_kwargs: object,
    ) -> None:
        super().__init__()
        self.expression_json = expression_json
        self.bar_type = bar_type
        self.evidence_root = evidence_root


def external_minute_bar_type(instrument_id: str) -> str:
    """Return the shortest provider-supported external BarType via public APIs."""
    from nautilus_trader.model import (
        AggregationSource,
        BarAggregation,
        BarSpecification,
        BarType,
        InstrumentId,
        PriceType,
    )

    return str(
        BarType(
            InstrumentId.from_str(instrument_id),
            BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
    )


def expression_for(instrument_id: str, provider_coin: str) -> MarketExpression:
    """Build a qualification-only point-in-time venue expression."""
    market_id = sha256_hex(f"HYPERLIQUID|MAIN|{provider_coin}".encode())
    return MarketExpression(
        market_id=market_id,
        dex="MAIN",
        provider_coin=provider_coin,
        instrument_id=instrument_id,
        expression_id=f"rc5-qualification-{provider_coin.lower()}",
        instrument_metadata_version="RC5_QUALIFICATION_PUBLIC_V1",
        instrument_metadata_hash=sha256_hex(
            f"RC5_QUALIFICATION_PUBLIC_V1|{instrument_id}".encode()
        ),
    )


def quote_source_event(expression: MarketExpression, tick: QuoteTick) -> SourceEvent:
    payload = {
        "bid_price": str(tick.bid_price),
        "bid_size": str(tick.bid_size),
        "ask_price": str(tick.ask_price),
        "ask_size": str(tick.ask_size),
    }
    return SourceEvent.create(
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


def trade_source_event(expression: MarketExpression, tick: TradeTick) -> SourceEvent:
    return SourceEvent.create(
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


def bar_source_event(expression: MarketExpression, bar: Bar) -> SourceEvent:
    return SourceEvent.create(
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


class Rc5QualificationStrategy(Strategy):
    """Temporary observer proving rc5 provider objects enter current evidence semantics."""

    def __init__(self, config: Rc5QualificationStrategyConfig) -> None:
        super().__init__(config)
        if version("nautilus-trader") != RC5_VERSION:
            raise RuntimeError("rc5 qualification strategy requires exact Nautilus 2.0.0rc5")
        self._expression = MarketExpression.model_validate_json(config.expression_json)
        self._bar_type_raw = config.bar_type
        self._store = EvidenceStore(Path(config.evidence_root))
        self._ledger = CausalAdmissionLedger(
            process_epoch="rc5-qualification-process",
            continuity_epoch="rc5-qualification-continuity",
            admission_epoch="rc5-qualification-admission",
        )
        self._quote_observed = False
        self._trade_observed = False
        self._bar_observed = False

    def on_start(self) -> None:
        from nautilus_trader.model import BarType, InstrumentId

        instrument_id = InstrumentId.from_str(self._expression.instrument_id)
        self.subscribe_socket_state()
        self.subscribe_quotes(instrument_id)
        self.subscribe_trades(instrument_id)
        self.subscribe_bars(BarType.from_str(self._bar_type_raw))

    def _persist(self, source: SourceEvent, *, admission_ts: int) -> None:
        outcome = self._ledger.admit(source, admission_ts=admission_ts)
        if outcome.event is not None:
            self._store.append_admission_batch((outcome.event,))

    def on_quote(self, tick: QuoteTick) -> None:
        self._quote_observed = True
        self._persist(
            quote_source_event(self._expression, tick),
            admission_ts=max(tick.ts_init, self.clock.timestamp_ns()),
        )

    def on_trade(self, tick: TradeTick) -> None:
        self._trade_observed = True
        self._persist(
            trade_source_event(self._expression, tick),
            admission_ts=max(tick.ts_init, self.clock.timestamp_ns()),
        )

    def on_bar(self, bar: Bar) -> None:
        self._bar_observed = True
        self._persist(
            bar_source_event(self._expression, bar),
            admission_ts=max(bar.ts_init, self.clock.timestamp_ns()),
        )

    def on_socket_state(self, _event: object) -> None:
        """Socket-state subscription is observed only as a public API compatibility seam."""

    @property
    def observation(self) -> dict[str, object]:
        admissions = self._store.load_admissions()
        finalized_bars = tuple(
            item
            for item in admissions
            if item.source.data_kind is DataKind.BAR
            and item.source.payload.get("finalized") is True
        )
        return {
            "quote_observed": self._quote_observed,
            "trade_observed": self._trade_observed,
            "finalized_bar_callback_observed": self._bar_observed,
            "finalized_bar_evidence_persisted": bool(finalized_bars),
            "admission_records": len(admissions),
            "causal_ordinals": [item.admission_ordinal for item in admissions],
            "source_kinds": [item.source.data_kind.value for item in admissions],
            "provider_observation_pass": all(
                (
                    self._quote_observed,
                    self._trade_observed,
                    self._bar_observed,
                    bool(finalized_bars),
                )
            ),
        }


def build_public_data_node() -> LiveNodeLike:
    """Build a qualification-only public Hyperliquid data node; no execution client exists."""
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidDataClientConfig,
        HyperliquidDataClientFactory,
        HyperliquidEnvironment,
    )
    from nautilus_trader.common import Environment
    from nautilus_trader.live import LiveNode
    from nautilus_trader.model import TraderId

    builder = LiveNode.builder(
        "TRADEOS-RC5-QUALIFICATION",
        TraderId("TRADEOS-RC5-QUALIFICATION"),
        Environment.LIVE,
    )
    builder.add_data_client(
        None,
        HyperliquidDataClientFactory(),
        HyperliquidDataClientConfig(environment=HyperliquidEnvironment.MAINNET),
    )
    return cast(LiveNodeLike, builder.build())


def build_strategy(
    *, expression: MarketExpression, evidence_root: Path
) -> Rc5QualificationStrategy:
    return Rc5QualificationStrategy(
        Rc5QualificationStrategyConfig(
            expression_json=expression.model_dump_json(),
            bar_type=external_minute_bar_type(expression.instrument_id),
            evidence_root=str(evidence_root),
        )
    )


def _write_result(path: Path | None, payload: dict[str, object]) -> None:
    encoded = canonical_json_bytes(payload) + b"\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(path)
    print(encoded.decode().strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--instrument-id", default="ETH-USD-PERP.HYPERLIQUID")
    parser.add_argument("--provider-coin", default="ETH")
    parser.add_argument("--run-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.run_seconds <= 0 or args.run_seconds > 180:
        raise SystemExit("--run-seconds must be between 1 and 180")
    if version("nautilus-trader") != RC5_VERSION:
        raise SystemExit("exact Nautilus 2.0.0rc5 is required")

    expression = expression_for(args.instrument_id, args.provider_coin)
    strategy: Rc5QualificationStrategy | None = None
    node: LiveNodeLike | None = None
    timer: threading.Timer | None = None
    try:
        node = build_public_data_node()
        strategy = build_strategy(expression=expression, evidence_root=args.evidence_path)
        node.add_strategy(strategy)
        handle = node.handle()
        timer = threading.Timer(args.run_seconds, handle.stop)
        timer.start()
        node.run()
        observation = strategy.observation
        passed = bool(observation["provider_observation_pass"])
        payload: dict[str, object] = {
            "schema_version": "RC5_ONE_BLOCKER_QUALIFICATION_RESULT_V1",
            "status": "PASS" if passed else "PROVIDER_DATA_INCOMPLETE",
            "failure_class": None if passed else "PROVIDER_OR_DATA_INCOMPLETENESS",
            "nautilus_version": version("nautilus-trader"),
            "qualification_only": True,
            "accepted_runtime_mutated": False,
            "public_hyperliquid_data_only": True,
            "zero_credentials": True,
            "execution_client_registered": False,
            "zero_signing": True,
            "zero_exchange_write": True,
            "instrument_id": expression.instrument_id,
            "bounded_run_seconds": args.run_seconds,
            "observation": observation,
        }
        _write_result(args.result_path, payload)
        return PASS if passed else PROVIDER_DATA_INCOMPLETE
    except Exception as exc:
        _write_result(
            args.result_path,
            {
                "schema_version": "RC5_ONE_BLOCKER_QUALIFICATION_RESULT_V1",
                "status": "APPLICATION_FAILURE",
                "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
                "nautilus_version": version("nautilus-trader"),
                "qualification_only": True,
                "zero_credentials": True,
                "execution_client_registered": False,
                "zero_exchange_write": True,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return APPLICATION_FAILURE
    finally:
        if timer is not None:
            timer.cancel()
        if node is not None:
            node.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
