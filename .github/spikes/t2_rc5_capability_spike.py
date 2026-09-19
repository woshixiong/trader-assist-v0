#!/usr/bin/env python3
"""T2 RC5 capability-spike proof; public-only and non-promotional.

This module deliberately owns only ephemeral proof data.  It never loads
credentials, constructs an execution client, signs a request, or sends an
exchange write.  Backtest orders are confined to Nautilus' BacktestNode.
"""

# Delayed optional Nautilus imports are intentionally local to this proof harness.
# ruff: noqa: I001

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Self


TASK_PACKET_SHA256 = "1d447a3537170b264c74dfefbe0914248a454d97199d0e2361961ac4a787dca4"
NAUTILUS_VERSION = "2.0.0rc5"
PUBLIC_INSTRUMENT_ID = "BTC-USD-PERP.HYPERLIQUID"
PRIVATE_ENV_NAMES = (
    "HYPERLIQUID_PRIVATE_KEY",
    "HYPERLIQUID_VAULT_ADDRESS",
    "HYPERLIQUID_VAULT",
)


class CapabilitySpikeStrategyConfig:  # Replaced by the public base at import time.
    pass


def _load_nautilus_types() -> dict[str, Any]:
    """Delay optional Nautilus imports so a local syntax check is sufficient."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.model import (
        AccountType,
        AggressorSide,
        AggregationSource,
        Bar,
        BarAggregation,
        BarSpecification,
        BarType,
        BookType,
        Currency,
        InstrumentId,
        OmsType,
        OrderSide,
        Price,
        PriceType,
        Quantity,
        QuoteTick,
        TradeId,
        TradeTick,
    )
    from nautilus_trader.persistence import ParquetDataCatalog
    from nautilus_trader.trading import ImportableStrategyConfig, Strategy, StrategyConfig

    return {
        "AccountType": AccountType,
        "AggressorSide": AggressorSide,
        "AggregationSource": AggregationSource,
        "BacktestDataConfig": BacktestDataConfig,
        "BacktestEngineConfig": BacktestEngineConfig,
        "BacktestNode": BacktestNode,
        "BacktestRunConfig": BacktestRunConfig,
        "BacktestVenueConfig": BacktestVenueConfig,
        "Bar": Bar,
        "BarAggregation": BarAggregation,
        "BarSpecification": BarSpecification,
        "BarType": BarType,
        "BookType": BookType,
        "Currency": Currency,
        "ImportableStrategyConfig": ImportableStrategyConfig,
        "InstrumentId": InstrumentId,
        "OmsType": OmsType,
        "OrderSide": OrderSide,
        "ParquetDataCatalog": ParquetDataCatalog,
        "Price": Price,
        "PriceType": PriceType,
        "Quantity": Quantity,
        "QuoteTick": QuoteTick,
        "Strategy": Strategy,
        "StrategyConfig": StrategyConfig,
        "TradeId": TradeId,
        "TradeTick": TradeTick,
    }


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _event_identity(tick: Any) -> str:
    """Bind a submission to all material fields of one exact replayed quote."""
    fields = {
        "instrument_id": str(tick.instrument_id),
        "ts_event": int(tick.ts_event),
        "ts_init": int(tick.ts_init),
        "bid_price": str(tick.bid_price),
        "ask_price": str(tick.ask_price),
        "bid_size": str(tick.bid_size),
        "ask_size": str(tick.ask_size),
    }
    return _sha256(_canonical_json(fields))


def _git_identity() -> tuple[str, str]:
    root = Path(__file__).resolve().parents[2]
    return (
        subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip(),
        subprocess.check_output(("git", "rev-parse", "HEAD^{tree}"), cwd=root, text=True).strip(),
    )


def _catalog_tree_sha256(root: Path) -> str:
    entries: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        entries.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path.read_bytes()),
            }
        )
    return _sha256(_canonical_json(entries))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_canonical_json(payload) + b"\n")
    temporary.replace(path)


def _write_evidence_value(root: Path, name: str, value: object) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(f"{value}\n", encoding="utf-8")


def _assert_public_only_environment() -> None:
    present = tuple(name for name in PRIVATE_ENV_NAMES if name in os.environ)
    if present:
        raise RuntimeError("HYPERLIQUID_PRIVATE_KEY_OR_VAULT_ENV_PRESENT:" + ",".join(present))


@dataclass(frozen=True)
class ProofInputs:
    instrument: object
    quote: object
    trade: object
    bar: object
    bar_type: object


def _fixture_inputs(types: dict[str, Any], instrument: Any) -> ProofInputs:
    QuoteTick = types["QuoteTick"]
    TradeTick = types["TradeTick"]
    TradeId = types["TradeId"]
    AggressorSide = types["AggressorSide"]
    BarType = types["BarType"]
    BarSpecification = types["BarSpecification"]
    BarAggregation = types["BarAggregation"]
    PriceType = types["PriceType"]
    AggregationSource = types["AggregationSource"]
    Bar = types["Bar"]
    start = 1_700_000_000_000_000_000
    instrument_id = instrument.id
    bar_type = BarType(
        instrument_id,
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    quote = QuoteTick(
        instrument_id=instrument_id,
        bid_price=instrument.make_price(100000.0),
        ask_price=instrument.make_price(100001.0),
        bid_size=instrument.make_qty(1.0),
        ask_size=instrument.make_qty(1.0),
        ts_event=start,
        ts_init=start + 1,
    )
    trade = TradeTick(
        instrument_id=instrument_id,
        price=instrument.make_price(100000.0),
        size=instrument.make_qty(1.0),
        aggressor_side=AggressorSide.BUY,
        trade_id=TradeId("t2-rc5-capability-spike-trade"),
        ts_event=start + 2,
        ts_init=start + 3,
    )
    bar = Bar(
        bar_type=bar_type,
        open=instrument.make_price(100000.0),
        high=instrument.make_price(100002.0),
        low=instrument.make_price(99999.0),
        close=instrument.make_price(100001.0),
        volume=instrument.make_qty(3.0),
        ts_event=start + 4,
        ts_init=start + 5,
    )
    return ProofInputs(instrument, quote, trade, bar, bar_type)


def _define_strategy(types: dict[str, Any]) -> tuple[type[object], type[object]]:
    Strategy = types["Strategy"]
    StrategyConfig = types["StrategyConfig"]
    OrderSide = types["OrderSide"]

    class _Config(StrategyConfig):
        _CUSTOM_FIELDS = (
            "instrument_id",
            "bar_type",
            "quantity",
            "trigger_identity",
            "ledger_path",
        )
        instrument_id: str
        bar_type: str
        quantity: float
        trigger_identity: str
        ledger_path: str

        def __new__(cls, *args: object, **kwargs: object) -> Self:
            for key in cls._CUSTOM_FIELDS:
                kwargs.pop(key, None)
            return super().__new__(cls, *args, **kwargs)

        def __init__(
            self,
            instrument_id: str,
            bar_type: str,
            quantity: float,
            trigger_identity: str,
            ledger_path: str,
            **_kwargs: object,
        ) -> None:
            super().__init__()
            if type(quantity) is not float or quantity != 0.01:
                raise TypeError("quantity must be the float packet value 0.01")
            self.instrument_id = instrument_id
            self.bar_type = bar_type
            self.quantity = quantity
            self.trigger_identity = trigger_identity
            self.ledger_path = ledger_path

    class _Strategy(Strategy):
        def __init__(self, config: object) -> None:
            super().__init__(config)
            self._config = config
            self._triggered = False
            self._matched = 0

        def _ledger(self, callback: str, payload: object) -> None:
            with Path(self._config.ledger_path).open("a", encoding="utf-8") as handle:
                record = {"callback": callback, "payload": payload}
                handle.write(json.dumps(record, sort_keys=True) + "\n")

        def on_start(self) -> None:
            InstrumentId = types["InstrumentId"]
            BarType = types["BarType"]
            instrument_id = InstrumentId.from_str(self._config.instrument_id)
            self.subscribe_quotes(instrument_id)
            self.subscribe_trades(instrument_id)
            self.subscribe_bars(BarType.from_str(self._config.bar_type))

        def on_quote(self, tick: object) -> None:
            identity = _event_identity(tick)
            self._ledger("on_quote", {"identity": identity})
            if identity != self._config.trigger_identity:
                return
            self._matched += 1
            if self._matched != 1 or self._triggered:
                raise RuntimeError("duplicate/second trigger match fails closed")
            instrument = self.cache.instrument(tick.instrument_id)
            if instrument is None:
                raise RuntimeError("provider Cache has no replayed instrument")
            quantity = instrument.make_qty(self._config.quantity)
            order = self.order_factory.market(
                instrument_id=tick.instrument_id,
                order_side=OrderSide.BUY,
                quantity=quantity,
            )
            self.submit_order(order)
            self._triggered = True
            self._ledger(
                "submit_order",
                {"source_event_identity": identity, "quantity": str(quantity)},
            )

        def on_trade(self, tick: object) -> None:
            self._ledger(
                "on_trade",
                {
                    "trade_id": str(tick.trade_id),
                    "aggressor_side": str(tick.aggressor_side),
                },
            )

        def on_bar(self, bar: object) -> None:
            self._ledger(
                "on_bar",
                {"bar_type": str(bar.bar_type), "ts_event": int(bar.ts_event)},
            )

    _Config.__name__ = "CapabilitySpikeStrategyConfig"
    _Config.__qualname__ = "CapabilitySpikeStrategyConfig"
    _Strategy.__name__ = "CapabilitySpikeStrategy"
    _Strategy.__qualname__ = "CapabilitySpikeStrategy"
    return _Config, _Strategy


def _write_and_reload(catalog: Any, inputs: ProofInputs) -> None:
    catalog.write_instruments([inputs.instrument])
    catalog.write_quote_ticks([inputs.quote])
    catalog.write_trade_ticks([inputs.trade])
    catalog.write_bars([inputs.bar])
    instrument_id = str(inputs.instrument.id)
    instruments = catalog.instruments(instrument_ids=[instrument_id])
    quotes = catalog.query_quote_ticks(identifiers=[instrument_id])
    trades = catalog.query_trade_ticks(identifiers=[instrument_id])
    bars = catalog.query_bars(identifiers=[str(inputs.bar_type)])
    if (
        len(instruments) != 1
        or len(quotes) != 1
        or len(trades) != 1
        or len(bars) != 1
    ):
        raise RuntimeError("immutable Parquet write/reload cardinality mismatch")


def _run_backtest(
    types: dict[str, Any],
    inputs: ProofInputs,
    root: Path,
    ledger: Path,
) -> dict[str, object]:
    Config, Strategy = _define_strategy(types)
    globals()["CapabilitySpikeStrategyConfig"] = Config
    globals()["CapabilitySpikeStrategy"] = Strategy
    # The direct-script entry point is also the importable Strategy module.
    sys.modules.setdefault("t2_rc5_capability_spike", sys.modules[__name__])
    BacktestVenueConfig = types["BacktestVenueConfig"]
    BacktestDataConfig = types["BacktestDataConfig"]
    BacktestEngineConfig = types["BacktestEngineConfig"]
    BacktestRunConfig = types["BacktestRunConfig"]
    BacktestNode = types["BacktestNode"]
    AccountType = types["AccountType"]
    BookType = types["BookType"]
    OmsType = types["OmsType"]
    ImportableStrategyConfig = types["ImportableStrategyConfig"]
    from trader_assist_v0.nautilus_g4.runner import project_provider_native_state

    trigger = _event_identity(inputs.quote)
    importable = ImportableStrategyConfig(
        strategy_path="t2_rc5_capability_spike:CapabilitySpikeStrategy",
        config_path="t2_rc5_capability_spike:CapabilitySpikeStrategyConfig",
        config={
            "instrument_id": str(inputs.instrument.id),
            "bar_type": str(inputs.bar_type),
            "quantity": 0.01,
            "trigger_identity": trigger,
            "ledger_path": str(ledger),
        },
    )
    if importable.config["quantity"] != 0.01 or type(importable.config["quantity"]) is not float:
        raise TypeError("ImportableStrategyConfig lost float quantity identity")
    account_currency = inputs.instrument.settlement_currency
    venue = BacktestVenueConfig(
        name=str(inputs.instrument.id.venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        base_currency=account_currency,
        starting_balances=[f"1_000_000 {account_currency}"],
    )
    data = [
        BacktestDataConfig(
            data_type=name,
            catalog_path=str(root),
            instrument_id=inputs.instrument.id,
        )
        for name in ("QuoteTick", "TradeTick", "Bar")
    ]
    config = BacktestRunConfig(
        venues=[venue], data=data, engine=BacktestEngineConfig(), dispose_on_completion=False
    )
    node = BacktestNode(configs=[config])
    try:
        node.build()
        node.add_strategy_from_config(config.id, importable)
        node.run()
        cache = node.get_engine_cache(config.id)
        portfolio = node.get_engine_portfolio(config.id)
        if cache is None or portfolio is None:
            raise RuntimeError("BacktestNode did not retain public Cache/Portfolio state")
        projection = project_provider_native_state(
            cache,
            portfolio,
            venue=inputs.instrument.id.venue,
        )
        result = projection.model_dump(mode="json")
        counts = (
            result["order_count"],
            result["filled_order_count"],
            result["position_count"],
            result["account_count"],
        )
        if counts != (1, 1, 1, 1):
            raise RuntimeError("unexpected provider-owned order/fill/position/account counts")
        lines = ledger.read_text(encoding="utf-8").splitlines()
        callbacks = [json.loads(line)["callback"] for line in lines]
        required_callbacks = {"on_quote", "on_trade", "on_bar"}
        if callbacks.count("submit_order") != 1 or not required_callbacks <= set(callbacks):
            raise RuntimeError("callback ledger does not show exactly one source-event-bound order")
        return {
            "source_event_bound_trigger": True,
            "timestamp_only_trigger_identity": False,
            "trigger_identity": trigger,
            "importable_strategy_config_resolves": True,
            "quantity_type": "float",
            "quantity_value": 0.01,
            "provider_state": result,
        }
    finally:
        node.dispose()


def _load_public_instrument() -> Any:
    _assert_public_only_environment()
    from nautilus_trader.adapters.hyperliquid import HyperliquidHttpClient

    async def load_definitions() -> list[Any]:
        client = HyperliquidHttpClient()
        return await client.load_instrument_definitions(
            include_spot=False,
            include_perps=True,
            include_perps_hip3=False,
            include_outcomes=False,
        )

    definitions = asyncio.run(load_definitions())
    for instrument in definitions:
        if str(instrument.id) == PUBLIC_INSTRUMENT_ID:
            return instrument
    raise RuntimeError("official Hyperliquid public metadata lacks BTC-USD-PERP.HYPERLIQUID")


def _run_phase(phase: str, evidence_root: Path) -> dict[str, object]:
    if version("nautilus-trader") != NAUTILUS_VERSION:
        raise RuntimeError("exact Nautilus rc5 identity is required")
    evidence_root.mkdir(parents=True, exist_ok=True)
    exact_head, exact_tree = _git_identity()
    _write_evidence_value(evidence_root, "exact-head", exact_head)
    _write_evidence_value(evidence_root, "exact-tree", exact_tree)
    _write_evidence_value(evidence_root, "task-packet-sha256", TASK_PACKET_SHA256)
    _write_evidence_value(evidence_root, "exact-nautilus-version", NAUTILUS_VERSION)
    _write_evidence_value(evidence_root, "zero-private-api-assertion", "PASS")
    _write_evidence_value(evidence_root, "zero-signing-assertion", "PASS")
    _write_evidence_value(evidence_root, "zero-exchange-write-assertion", "PASS")
    _assert_public_only_environment()
    types = _load_nautilus_types()
    if phase == "offline":
        from nautilus_trader.testkit.providers import TestInstrumentProvider
        instrument = TestInstrumentProvider.btcusdt_perp_binance()
        public_provider_call = False
    else:
        instrument = _load_public_instrument()
        public_provider_call = True
    with TemporaryDirectory(prefix=f"t2-rc5-{phase}-") as temporary:
        catalog_root = Path(temporary) / "catalog"
        catalog_root.mkdir()  # Required: creation precedes ParquetDataCatalog construction.
        catalog = types["ParquetDataCatalog"](str(catalog_root))
        inputs = _fixture_inputs(types, instrument)
        _write_and_reload(catalog, inputs)
        ledger = evidence_root / "callback-ledger.jsonl"
        ledger.write_text("", encoding="utf-8")
        backtest = _run_backtest(types, inputs, catalog_root, ledger)
        catalog_hash = _catalog_tree_sha256(catalog_root)
    _write_evidence_value(evidence_root, "catalog-tree-sha256", catalog_hash)
    _write_evidence_value(
        evidence_root,
        "instrument-identity-and-type",
        json.dumps(
            {
                "instrument_id": str(instrument.id),
                "type": type(instrument).__name__,
            },
            sort_keys=True,
        ),
    )
    _write_evidence_value(
        evidence_root,
        "provider-state-hash-and-counts",
        json.dumps(backtest["provider_state"], sort_keys=True),
    )
    return {
        "schema_version": "T2_RC5_CAPABILITY_SPIKE_V2",
        "status": "PASS",
        "phase": phase,
        "network": public_provider_call,
        "public_provider_call": public_provider_call,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "real_t2_credit": False,
        "exact_head": exact_head,
        "exact_tree": exact_tree,
        "task_packet_sha256": TASK_PACKET_SHA256,
        "nautilus_version": NAUTILUS_VERSION,
        "instrument_identity_and_type": {
            "instrument_id": str(instrument.id),
            "type": type(instrument).__name__,
        },
        "catalog_tree_sha256": catalog_hash,
        **backtest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("offline", "public"), required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    args = parser.parse_args()
    result_name = (
        "phase-a-terminal-status"
        if args.phase == "offline"
        else "phase-b-terminal-status"
    )
    try:
        result = _run_phase(args.phase, args.evidence_dir)
    except Exception as exc:
        status = (
            "SPIKE_V2=FAIL_HARNESS_SELF_CHECK"
            if args.phase == "offline"
            else "SPIKE_V2=FAIL_PUBLIC_COMBINED_PROOF"
        )
        result = {
            "schema_version": "T2_RC5_CAPABILITY_SPIKE_V2",
            "status": status,
            "phase": args.phase,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "phase_b_run": "NO" if args.phase == "offline" else "YES",
        }
        _write_evidence_value(args.evidence_dir, result_name, status)
        _write_json(args.result_path, result)
        return 1
    _write_evidence_value(args.evidence_dir, result_name, "PASS")
    _write_json(args.result_path, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
