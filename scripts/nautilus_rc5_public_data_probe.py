"""Qualification-only Nautilus 2.0.0rc5 public Hyperliquid data probe.

This module is diagnostic evidence for Issue #162. It is not an adopted runtime,
does not alter the accepted rc4 host, and never configures execution, credentials,
signing, or exchange writes.
"""

from __future__ import annotations

import argparse
import os
import threading
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from nautilus_trader.adapters.hyperliquid import (
    HyperliquidDataClientConfig,
    HyperliquidDataClientFactory,
    HyperliquidEnvironment,
)
from nautilus_trader.common import Environment
from nautilus_trader.live import LiveNode
from nautilus_trader.model import (
    AggregationSource,
    Bar,
    BarAggregation,
    BarSpecification,
    BarType,
    InstrumentId,
    PriceType,
    QuoteTick,
    TradeTick,
    TraderId,
)
from nautilus_trader.trading import Strategy, StrategyConfig

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_e4.safety import assert_public_only
from trader_assist_v0.nautilus_e4.storage import EvidenceStore

RC5_VERSION = "2.0.0rc5"
PASS = 0
PROVIDER_DATA_INCOMPLETE = 2
APPLICATION_FAILURE = 3


def _external_minute_bar_type(instrument_id: str) -> BarType:
    return BarType(
        InstrumentId.from_str(instrument_id),
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json_bytes(payload) + b"\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    print(encoded.decode().strip())


class Rc5QualificationStrategy(Strategy):
    """Minimal public-data observer using current Trade OS evidence semantics only."""

    def __init__(self, *, evidence_root: Path, instrument_id: str) -> None:
        super().__init__(StrategyConfig())
        if version("nautilus-trader") != RC5_VERSION:
            raise RuntimeError("rc5 qualification requires exact nautilus-trader==2.0.0rc5")
        self._instrument_id = InstrumentId.from_str(instrument_id)
        self._bar_type = _external_minute_bar_type(instrument_id)
        self._market_id = sha256_hex(f"HYPERLIQUID|MAIN|{instrument_id}".encode())
        self._expression_id = "rc5-qualification-public-data"
        self._store = EvidenceStore(evidence_root)
        self._observed: set[DataKind] = set()
        self._ordinal = 0

    @property
    def result(self) -> dict[str, Any]:
        admissions = self._store.load_admissions()
        persisted_kinds = {item.source.data_kind for item in admissions}
        required = {DataKind.BBO, DataKind.TRADE, DataKind.BAR}
        return {
            "quote_observed": DataKind.BBO in self._observed,
            "trade_observed": DataKind.TRADE in self._observed,
            "finalized_bar_callback_observed": DataKind.BAR in self._observed,
            "finalized_bar_evidence_persisted": DataKind.BAR in persisted_kinds,
            "persisted_kinds": sorted(item.value for item in persisted_kinds),
            "admission_count": len(admissions),
            "provider_observation_pass": required <= self._observed
            and required <= persisted_kinds,
        }

    def on_start(self) -> None:
        self.subscribe_quotes(self._instrument_id)
        self.subscribe_trades(self._instrument_id)
        self.subscribe_bars(self._bar_type)

    def _persist(self, source: SourceEvent) -> None:
        self._ordinal += 1
        admitted = AdmittedEvent.create(
            schema_version="E4_CAPTURE_V1",
            process_epoch="rc5-qualification-process",
            continuity_epoch="rc5-qualification-continuity",
            admission_epoch="rc5-qualification-admission",
            admission_ordinal=self._ordinal,
            admission_ts=max(source.ts_init, time.time_ns()),
            source_identity=source.replay_identity,
            out_of_order=False,
            continuity_state=EvidenceState.COMPLETE,
            source=source,
        )
        self._store.append_admission_batch((admitted,))
        self._observed.add(source.data_kind)

    def on_quote(self, tick: QuoteTick) -> None:
        payload = {
            "bid_price": str(tick.bid_price),
            "bid_size": str(tick.bid_size),
            "ask_price": str(tick.ask_price),
            "ask_size": str(tick.ask_size),
        }
        self._persist(
            SourceEvent.create(
                market_id=self._market_id,
                expression_id=self._expression_id,
                provider_id="NAUTILUS_HYPERLIQUID",
                instrument_id=str(tick.instrument_id),
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
        )

    def on_trade(self, tick: TradeTick) -> None:
        self._persist(
            SourceEvent.create(
                market_id=self._market_id,
                expression_id=self._expression_id,
                provider_id="NAUTILUS_HYPERLIQUID",
                instrument_id=str(tick.instrument_id),
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
        )

    def on_bar(self, bar: Bar) -> None:
        self._persist(
            SourceEvent.create(
                market_id=self._market_id,
                expression_id=self._expression_id,
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
        )


def _build_public_data_node() -> LiveNode:
    assert_public_only(env=os.environ)
    if version("nautilus-trader") != RC5_VERSION:
        raise RuntimeError("rc5 qualification requires exact nautilus-trader==2.0.0rc5")
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
    return builder.build()


def _run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    proof = assert_public_only(env=os.environ)
    node = _build_public_data_node()
    strategy = Rc5QualificationStrategy(
        evidence_root=args.evidence_path,
        instrument_id=args.instrument_id,
    )
    node.add_strategy(strategy)
    handle = node.handle()
    timer = threading.Timer(args.run_seconds, handle.stop)
    try:
        timer.start()
        node.run()
    finally:
        timer.cancel()
        node.dispose()
    observation = strategy.result
    passed = bool(observation["provider_observation_pass"])
    return (
        PASS if passed else PROVIDER_DATA_INCOMPLETE,
        {
            "schema_version": "RC5_QUALIFICATION_PUBLIC_PROVIDER_RESULT_V1",
            "status": "PASS" if passed else "PROVIDER_DATA_INCOMPLETE",
            "failure_class": None if passed else "PROVIDER_OR_DATA_INCOMPLETENESS",
            "qualification_only": True,
            "nautilus_version": RC5_VERSION,
            "exact_head": args.exact_head,
            "exact_tree": args.exact_tree,
            "bounded_run_seconds": args.run_seconds,
            "public_data_only": True,
            "zero_credentials": True,
            "zero_execution_client": True,
            "zero_signing": True,
            "zero_exchange_write": True,
            "zero_write_proof": proof.model_dump(mode="json"),
            "observation": observation,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-path", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--instrument-id", default="ETH-USD-PERP.HYPERLIQUID")
    parser.add_argument("--run-seconds", type=int, default=90)
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--exact-tree", required=True)
    args = parser.parse_args()
    if args.run_seconds <= 0 or args.run_seconds > 180:
        raise SystemExit("--run-seconds must be between 1 and 180")
    try:
        exit_code, result = _run(args)
    except Exception as exc:
        result = {
            "schema_version": "RC5_QUALIFICATION_PUBLIC_PROVIDER_RESULT_V1",
            "status": "APPLICATION_FAILURE",
            "failure_class": "APPLICATION_OR_PROVIDER_RUNTIME_FAILURE",
            "qualification_only": True,
            "nautilus_version": RC5_VERSION,
            "exact_head": args.exact_head,
            "exact_tree": args.exact_tree,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "public_data_only": True,
            "zero_credentials": True,
            "zero_execution_client": True,
            "zero_signing": True,
            "zero_exchange_write": True,
        }
        _write_result(args.result_path, result)
        return APPLICATION_FAILURE
    _write_result(args.result_path, result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
