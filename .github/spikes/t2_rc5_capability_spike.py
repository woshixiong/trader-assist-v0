#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Exact Nautilus 2.0.0rc5 two-phase capability spike.

Phase A is a completely offline provider-owned backtest. Phase B is reachable
only after Phase A passes, proves that no Hyperliquid signer is configured,
performs one public instrument-definition request, and then runs the identical
offline backtest path. This is capability evidence only and grants no T2 or
trading credit.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

NAUTILUS_VERSION = "2.0.0rc5"
PUBLIC_INSTRUMENT_ID = "BTC-USD-PERP.HYPERLIQUID"
ORDER_QUANTITY = 0.01
STRATEGY_MODULE = "t2_rc5_capability_spike"
SCHEMA_VERSION = "T2_RC5_CAPABILITY_SPIKE_V2"
CREDENTIAL_NAMES = (
    "HYPERLIQUID_PK",
    "HYPERLIQUID_VAULT",
    "HYPERLIQUID_TESTNET_PK",
    "HYPERLIQUID_TESTNET_VAULT",
)
SYNTHETIC_CREDENTIAL_SENTINEL = "SYNTHETIC_NON_SECRET_SENTINEL_DO_NOT_USE"
TASK_PACKET_IDENTITY: dict[str, object] = {
    "repository": "woshixiong/trader-assist-v0",
    "controlling_issue": 163,
    "clean_replacement_pre_writer_review_comment": 5739827496,
    "replan_authority_comment": 5739769270,
    "canonical_resource_amendment_comment": 5739874592,
    "rejected_predecessor_pr": 197,
    "frozen_base_main": "303cfad95876ee48417697ddd858f1f298358995",
    "frozen_base_tree": "12a1251bb35e7a4191d1137eff2f3058a4c38e5e",
    "required_changed_paths": [
        ".github/spikes/t2_rc5_capability_spike.py",
        ".github/workflows/nautilus-vnext-g4-ci.yml",
    ],
    "tightenings": [
        "PHASE_SCOPED_PROVIDER_ORDER_FILLED_CARDINALITY",
        "FOUR_VARIABLE_CREDENTIAL_GUARD_AND_RUNTIME_NO_SIGNER",
    ],
}


if TYPE_CHECKING:

    class StrategyConfig:
        def __new__(cls, *args: object, **kwargs: object) -> Self: ...

        def __init__(self, *args: object, **kwargs: object) -> None: ...

    class Strategy:
        order_factory: Any

        def __init__(self, config: StrategyConfig | None = None) -> None: ...

        def subscribe_quotes(self, instrument_id: object) -> None: ...

        def subscribe_trades(self, instrument_id: object) -> None: ...

        def subscribe_bars(self, bar_type: object) -> None: ...

        def submit_order(self, order: object) -> None: ...

    class OrderFilled: ...

else:
    from nautilus_trader.model import OrderFilled
    from nautilus_trader.trading import Strategy, StrategyConfig


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


TASK_PACKET_SHA256 = _sha256(TASK_PACKET_IDENTITY)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(_canonical_bytes(dict(payload)) + b"\n")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object at {path}")
    return value


def _git_identity() -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(head) != 40 or len(tree) != 40:
        raise RuntimeError("git exact-head identity is not canonical")
    return head, tree


class CredentialGuardError(RuntimeError):
    """Credential material was present before public-client construction."""


def _credential_guard(env: Mapping[str, str]) -> None:
    present = tuple(name for name in CREDENTIAL_NAMES if name in env)
    if present:
        raise CredentialGuardError(
            "Hyperliquid credential environment is prohibited: " + ",".join(present)
        )


def _construct_public_client(
    *,
    env: Mapping[str, str],
    counters: dict[str, int],
) -> object:
    """Guard credentials before importing or constructing the exact rc5 client."""
    _credential_guard(env)
    from nautilus_trader.adapters.hyperliquid import (
        HyperliquidEnvironment,
        HyperliquidHttpClient,
    )

    counters["provider_client_construction_count"] += 1
    return HyperliquidHttpClient(environment=HyperliquidEnvironment.MAINNET)


def _credential_negative_proof() -> dict[str, object]:
    cases: list[dict[str, object]] = []
    for selected in CREDENTIAL_NAMES:
        synthetic_env = {selected: SYNTHETIC_CREDENTIAL_SENTINEL}
        counters = {
            "provider_client_construction_count": 0,
            "network_call_count": 0,
            "private_api_call_count": 0,
            "signing_count": 0,
            "exchange_write_count": 0,
        }
        blocked = False
        error = ""
        try:
            _construct_public_client(env=synthetic_env, counters=counters)
            raise AssertionError("credential guard allowed provider-client construction")
        except CredentialGuardError as exc:
            blocked = True
            error = str(exc)
        if not blocked or selected not in error or any(counters.values()):
            raise AssertionError(f"credential negative proof failed for {selected}")
        cases.append(
            {
                "credential_variable": selected,
                "synthetic_non_secret_sentinel": True,
                "guard_failed_closed": True,
                **counters,
            }
        )
    if {case["credential_variable"] for case in cases} != set(CREDENTIAL_NAMES):
        raise AssertionError("credential negative proof did not cover all variables")
    return {
        "status": "PASS",
        "case_count": len(cases),
        "covered_variables": list(CREDENTIAL_NAMES),
        "cases": cases,
    }


class CapabilitySpikeStrategyConfig(StrategyConfig):
    """Serializable source-event trigger and phase evidence identity."""

    _CUSTOM_FIELDS = (
        "phase",
        "instrument_id",
        "bar_type",
        "trigger_ts_event",
        "trigger_ts_init",
        "trigger_bid_price",
        "trigger_ask_price",
        "trigger_bid_size",
        "trigger_ask_size",
        "quantity",
        "ledger_path",
    )

    phase: str
    instrument_id: str
    bar_type: str
    trigger_ts_event: int
    trigger_ts_init: int
    trigger_bid_price: str
    trigger_ask_price: str
    trigger_bid_size: str
    trigger_ask_size: str
    quantity: float
    ledger_path: str

    def __new__(cls, *args: object, **kwargs: object) -> Self:
        for key in cls._CUSTOM_FIELDS:
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(
        self,
        phase: str,
        instrument_id: str,
        bar_type: str,
        trigger_ts_event: int,
        trigger_ts_init: int,
        trigger_bid_price: str,
        trigger_ask_price: str,
        trigger_bid_size: str,
        trigger_ask_size: str,
        quantity: float,
        ledger_path: str,
        **_kwargs: object,
    ) -> None:
        super().__init__()
        if phase not in {"PHASE_A", "PHASE_B"}:
            raise ValueError("unknown capability-spike phase")
        if type(quantity) is not float or quantity != ORDER_QUANTITY:
            raise ValueError("order quantity must be the Python float 0.01")
        self.phase = phase
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.trigger_ts_event = trigger_ts_event
        self.trigger_ts_init = trigger_ts_init
        self.trigger_bid_price = trigger_bid_price
        self.trigger_ask_price = trigger_ask_price
        self.trigger_bid_size = trigger_bid_size
        self.trigger_ask_size = trigger_ask_size
        self.quantity = quantity
        self.ledger_path = ledger_path


class CapabilitySpikeStrategy(Strategy):
    """One source-bound simulated order with actual provider fill callbacks."""

    def __init__(self, config: CapabilitySpikeStrategyConfig) -> None:
        super().__init__(config)
        from nautilus_trader.model import BarType, InstrumentId

        self._phase = config.phase
        self._instrument_id = InstrumentId.from_str(config.instrument_id)
        self._bar_type = BarType.from_str(config.bar_type)
        self._quantity = config.quantity
        self._ledger_path = Path(config.ledger_path)
        self._trigger_identity = {
            "instrument_id": config.instrument_id,
            "ts_event": config.trigger_ts_event,
            "ts_init": config.trigger_ts_init,
            "bid_price": config.trigger_bid_price,
            "ask_price": config.trigger_ask_price,
            "bid_size": config.trigger_bid_size,
            "ask_size": config.trigger_ask_size,
        }

    def _mutate_ledger(self, **updates: object) -> dict[str, Any]:
        ledger = _read_json(self._ledger_path)
        if ledger.get("phase") != self._phase:
            raise RuntimeError("strategy ledger phase identity mismatch")
        ledger.update(updates)
        _write_json(self._ledger_path, ledger)
        return ledger

    def on_start(self) -> None:
        self.subscribe_quotes(self._instrument_id)
        self.subscribe_trades(self._instrument_id)
        self.subscribe_bars(self._bar_type)
        self._mutate_ledger(subscriptions={"quotes": True, "trades": True, "bars": True})

    def on_quote(self, tick: Any) -> None:
        from nautilus_trader.model import OrderSide, Quantity

        ledger = _read_json(self._ledger_path)
        quote_count = int(ledger["quote_observation_count"]) + 1
        actual = {
            "instrument_id": str(tick.instrument_id),
            "ts_event": int(tick.ts_event),
            "ts_init": int(tick.ts_init),
            "bid_price": str(tick.bid_price),
            "ask_price": str(tick.ask_price),
            "bid_size": str(tick.bid_size),
            "ask_size": str(tick.ask_size),
        }
        if actual != self._trigger_identity:
            self._mutate_ledger(quote_observation_count=quote_count)
            return
        trigger_match_count = int(ledger["trigger_match_count"]) + 1
        if trigger_match_count != 1 or int(ledger["submit_order_count"]) != 0:
            self._mutate_ledger(
                quote_observation_count=quote_count,
                trigger_match_count=trigger_match_count,
                duplicate_trigger_failed_closed=True,
            )
            raise RuntimeError("second matching source quote failed closed")
        order = self.order_factory.market(
            instrument_id=self._instrument_id,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_float(self._quantity),
        )
        client_order_id = str(order.client_order_id)
        self._mutate_ledger(
            quote_observation_count=quote_count,
            trigger_match_count=trigger_match_count,
            submit_order_count=1,
            submitted_client_order_id=client_order_id,
            submitted_quantity=self._quantity,
            submitted_quantity_python_type=type(self._quantity).__name__,
            matched_source_quote=actual,
        )
        self.submit_order(order)

    def on_trade(self, _tick: object) -> None:
        ledger = _read_json(self._ledger_path)
        self._mutate_ledger(
            trade_observation_count=int(ledger["trade_observation_count"]) + 1
        )

    def on_bar(self, _bar: object) -> None:
        ledger = _read_json(self._ledger_path)
        self._mutate_ledger(bar_observation_count=int(ledger["bar_observation_count"]) + 1)

    def on_order_filled(self, event: OrderFilled) -> None:
        if not isinstance(event, OrderFilled):
            raise TypeError("fill callback did not receive provider-native OrderFilled")
        ledger = _read_json(self._ledger_path)
        fill_count = int(ledger["fill_event_count"]) + 1
        fill = {
            "phase": self._phase,
            "client_order_id": str(event.client_order_id),
            "venue_order_id": str(event.venue_order_id),
            "trade_id": str(event.trade_id),
            "event_id": str(event.event_id),
            "last_qty": str(event.last_qty),
            "last_px": str(event.last_px),
            "ts_event": int(event.ts_event),
            "ts_init": int(event.ts_init),
            "event_type": f"{type(event).__module__}.{type(event).__qualname__}",
            "provider_native_order_filled": True,
        }
        if fill_count != 1:
            self._mutate_ledger(
                fill_event_count=fill_count,
                fill_events=[*ledger["fill_events"], fill],
                duplicate_fill_failed_closed=True,
            )
            raise RuntimeError("second provider-native OrderFilled event failed closed")
        submitted = ledger.get("submitted_client_order_id")
        if not submitted or fill["client_order_id"] != submitted:
            self._mutate_ledger(
                fill_event_count=fill_count,
                fill_events=[fill],
                fill_order_binding=False,
            )
            raise RuntimeError("fill client_order_id does not bind submitted order")
        self._mutate_ledger(
            fill_event_count=fill_count,
            fill_events=[fill],
            sole_fill_event=fill,
            fill_order_binding=True,
        )


@dataclass(frozen=True)
class Fixture:
    instrument: object
    quotes: tuple[object, ...]
    trades: tuple[object, ...]
    bars: tuple[object, ...]
    trigger_identity: dict[str, object]
    bar_type: object


def _build_fixture() -> Fixture:
    from nautilus_trader.model import (
        AggregationSource,
        AggressorSide,
        Bar,
        BarAggregation,
        BarSpecification,
        BarType,
        Price,
        PriceType,
        Quantity,
        QuoteTick,
        TradeId,
        TradeTick,
    )
    from nautilus_trader.testkit.providers import TestInstrumentProvider

    instrument = TestInstrumentProvider.btcusdt_perp_binance()
    start = 1_700_000_000_000_000_000
    quotes = (
        QuoteTick(
            instrument_id=instrument.id,
            bid_price=Price.from_str("30000.0"),
            ask_price=Price.from_str("30000.1"),
            bid_size=Quantity.from_str("1.000"),
            ask_size=Quantity.from_str("1.000"),
            ts_event=start,
            ts_init=start + 1,
        ),
        QuoteTick(
            instrument_id=instrument.id,
            bid_price=Price.from_str("30001.0"),
            ask_price=Price.from_str("30001.1"),
            bid_size=Quantity.from_str("2.000"),
            ask_size=Quantity.from_str("3.000"),
            ts_event=start + 2_000,
            ts_init=start + 2_001,
        ),
        QuoteTick(
            instrument_id=instrument.id,
            bid_price=Price.from_str("30002.0"),
            ask_price=Price.from_str("30002.1"),
            bid_size=Quantity.from_str("1.500"),
            ask_size=Quantity.from_str("1.500"),
            ts_event=start + 5_000,
            ts_init=start + 5_001,
        ),
    )
    trades = (
        TradeTick(
            instrument_id=instrument.id,
            price=Price.from_str("30000.5"),
            size=Quantity.from_str("0.100"),
            aggressor_side=AggressorSide.BUY,
            trade_id=TradeId("capability-spike-trade"),
            ts_event=start + 1_000,
            ts_init=start + 1_001,
        ),
    )
    bar_type = BarType(
        instrument.id,
        BarSpecification(1, BarAggregation.MINUTE, PriceType.LAST),
        AggregationSource.EXTERNAL,
    )
    bars = (
        Bar(
            bar_type=bar_type,
            open=Price.from_str("30000.0"),
            high=Price.from_str("30003.0"),
            low=Price.from_str("29999.0"),
            close=Price.from_str("30002.0"),
            volume=Quantity.from_str("10.000"),
            ts_event=start + 4_000,
            ts_init=start + 4_001,
        ),
    )
    trigger = quotes[1]
    trigger_identity = {
        "instrument_id": str(trigger.instrument_id),
        "ts_event": trigger.ts_event,
        "ts_init": trigger.ts_init,
        "bid_price": str(trigger.bid_price),
        "ask_price": str(trigger.ask_price),
        "bid_size": str(trigger.bid_size),
        "ask_size": str(trigger.ask_size),
    }
    return Fixture(instrument, quotes, trades, bars, trigger_identity, bar_type)


def _initial_ledger(phase: str, trigger_identity: Mapping[str, object]) -> dict[str, object]:
    return {
        "phase": phase,
        "trigger_identity": dict(trigger_identity),
        "trigger_identity_fields": [
            "instrument_id",
            "ts_event",
            "ts_init",
            "bid_price",
            "ask_price",
            "bid_size",
            "ask_size",
        ],
        "timestamp_only_trigger": False,
        "trigger_match_count": 0,
        "duplicate_trigger_failed_closed": False,
        "submit_order_count": 0,
        "submitted_client_order_id": None,
        "fill_event_count": 0,
        "fill_events": [],
        "fill_order_binding": False,
        "duplicate_fill_failed_closed": False,
        "quote_observation_count": 0,
        "trade_observation_count": 0,
        "bar_observation_count": 0,
        "subscriptions": {"quotes": False, "trades": False, "bars": False},
    }


def _provider_state(cache: object, portfolio: object, venue: object) -> dict[str, object]:
    orders_method = getattr(cache, "orders", None)
    positions_method = getattr(cache, "positions", None)
    account_method = getattr(cache, "account_for_venue", None)
    if not all(callable(method) for method in (orders_method, positions_method, account_method)):
        raise RuntimeError("provider Cache lacks required public state methods")
    orders = tuple(orders_method())
    positions = tuple(positions_method())
    account = account_method(venue)
    if account is None:
        portfolio_account = getattr(portfolio, "account", None)
        account = portfolio_account(venue) if callable(portfolio_account) else None
    if account is None:
        raise RuntimeError("provider Cache/Portfolio account state is absent")
    filled_orders = tuple(
        order for order in orders if str(getattr(order, "filled_qty", "0")) not in {"0", "0.0"}
    )
    state = {
        "source_api": "NAUTILUS_CACHE_PORTFOLIO",
        "cache_type": f"{type(cache).__module__}.{type(cache).__qualname__}",
        "portfolio_type": f"{type(portfolio).__module__}.{type(portfolio).__qualname__}",
        "order_count": len(orders),
        "filled_order_count": len(filled_orders),
        "position_count": len(positions),
        "account_count": 1,
    }
    if (
        state["order_count"],
        state["position_count"],
        state["account_count"],
    ) != (1, 1, 1):
        raise AssertionError(f"unexpected provider-owned state cardinality: {state}")
    if not str(state["cache_type"]).startswith("nautilus_trader.") or not str(
        state["portfolio_type"]
    ).startswith("nautilus_trader."):
        raise AssertionError("Cache/Portfolio are not provider-owned Nautilus types")
    return state


def _run_backtest_phase(
    *,
    phase: str,
    phase_root: Path,
    exact_head: str,
    exact_tree: str,
    network: bool,
    public_provider_call: bool,
) -> dict[str, object]:
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.model import AccountType, BookType, Currency, OmsType
    from nautilus_trader.persistence import ParquetDataCatalog
    from nautilus_trader.trading import ImportableStrategyConfig

    fixture = _build_fixture()
    catalog_root = phase_root / "catalog"
    catalog_root.mkdir(parents=True, exist_ok=False)
    catalog = ParquetDataCatalog(str(catalog_root))
    catalog.write_instruments([fixture.instrument])
    catalog.write_quote_ticks(list(fixture.quotes))
    catalog.write_trade_ticks(list(fixture.trades))
    catalog.write_bars(list(fixture.bars))
    reloaded_quotes = tuple(catalog.query_quote_ticks(identifiers=[str(fixture.instrument.id)]))
    reloaded_trades = tuple(catalog.query_trade_ticks(identifiers=[str(fixture.instrument.id)]))
    reloaded_bars = tuple(catalog.query_bars(identifiers=[str(fixture.bar_type)]))
    if reloaded_quotes != fixture.quotes:
        raise AssertionError("typed quote reload changed the fixture")
    if reloaded_trades != fixture.trades:
        raise AssertionError("typed trade reload changed the fixture")
    if reloaded_bars != fixture.bars:
        raise AssertionError("typed bar reload changed the fixture")

    ledger_path = phase_root / "strategy-ledger.json"
    _write_json(ledger_path, _initial_ledger(phase, fixture.trigger_identity))
    venue = BacktestVenueConfig(
        name=str(fixture.instrument.id.venue),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        base_currency=Currency.from_str("USDT"),
        starting_balances=["1_000_000 USDT"],
    )
    common_data = {
        "catalog_path": str(catalog_root),
        "instrument_id": fixture.instrument.id,
        "start_time": fixture.quotes[0].ts_init,
        "end_time": fixture.quotes[-1].ts_init + 1,
    }
    data = [
        BacktestDataConfig(data_type="QuoteTick", **common_data),
        BacktestDataConfig(data_type="TradeTick", **common_data),
        BacktestDataConfig(data_type="Bar", **common_data),
    ]
    config = BacktestRunConfig(
        venues=[venue],
        data=data,
        engine=BacktestEngineConfig(bypass_logging=True, run_analysis=False),
        dispose_on_completion=False,
    )
    trigger = fixture.trigger_identity
    strategy_config = ImportableStrategyConfig(
        strategy_path=f"{STRATEGY_MODULE}:CapabilitySpikeStrategy",
        config_path=f"{STRATEGY_MODULE}:CapabilitySpikeStrategyConfig",
        config={
            "phase": phase,
            "instrument_id": str(fixture.instrument.id),
            "bar_type": str(fixture.bar_type),
            "trigger_ts_event": trigger["ts_event"],
            "trigger_ts_init": trigger["ts_init"],
            "trigger_bid_price": trigger["bid_price"],
            "trigger_ask_price": trigger["ask_price"],
            "trigger_bid_size": trigger["bid_size"],
            "trigger_ask_size": trigger["ask_size"],
            "quantity": ORDER_QUANTITY,
            "ledger_path": str(ledger_path),
        },
    )
    node = BacktestNode(configs=[config])
    try:
        node.build()
        node.add_strategy_from_config(config.id, strategy_config)
        results = node.run()
        cache = node.get_engine_cache(config.id)
        portfolio = node.get_engine_portfolio(config.id)
        if cache is None or portfolio is None:
            raise AssertionError("BacktestNode did not retain Cache/Portfolio")
        provider_state = _provider_state(cache, portfolio, fixture.instrument.id.venue)
        ledger = _read_json(ledger_path)
    finally:
        node.dispose()

    if ledger["trigger_match_count"] != 1 or ledger["submit_order_count"] != 1:
        raise AssertionError(f"{phase} did not submit exactly one source-bound order")
    if ledger["fill_event_count"] != 1 or len(ledger["fill_events"]) != 1:
        raise AssertionError(f"{phase} did not observe exactly one OrderFilled callback")
    if ledger["fill_order_binding"] is not True:
        raise AssertionError(f"{phase} fill does not bind the submitted client_order_id")
    if ledger["submitted_quantity"] != ORDER_QUANTITY:
        raise AssertionError("submitted quantity changed")
    if ledger["submitted_quantity_python_type"] != "float":
        raise AssertionError("submitted quantity was not a real Python float")
    if not all(int(ledger[name]) > 0 for name in (
        "quote_observation_count",
        "trade_observation_count",
        "bar_observation_count",
    )):
        raise AssertionError(f"{phase} did not observe quotes, trades, and bars")
    result: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "status": "PASS",
        "exact_git_head": exact_head,
        "exact_git_tree": exact_tree,
        "task_packet_sha256": TASK_PACKET_SHA256,
        "nautilus_version": NAUTILUS_VERSION,
        "network": network,
        "public_provider_call": public_provider_call,
        "same_strategy_path": f"{STRATEGY_MODULE}:CapabilitySpikeStrategy",
        "same_config_path": f"{STRATEGY_MODULE}:CapabilitySpikeStrategyConfig",
        "same_backtest_implementation_path": (
            "t2_rc5_capability_spike:_run_backtest_phase/BacktestNode/ParquetDataCatalog"
        ),
        "same_fixture_sha256": _sha256(
            {
                "quotes": [str(item) for item in fixture.quotes],
                "trades": [str(item) for item in fixture.trades],
                "bars": [str(item) for item in fixture.bars],
            }
        ),
        "catalog_typed_reads": {
            "query_quote_ticks": len(reloaded_quotes),
            "query_trade_ticks": len(reloaded_trades),
            "query_bars": len(reloaded_bars),
        },
        "backtest_node_result_count": len(results),
        "source_event_bound_trigger": True,
        "timestamp_only_trigger": False,
        "trigger_identity": ledger["trigger_identity"],
        "trigger_identity_fields": ledger["trigger_identity_fields"],
        "trigger_match_count": ledger["trigger_match_count"],
        "submit_order_count": ledger["submit_order_count"],
        "submitted_client_order_id": ledger["submitted_client_order_id"],
        "quantity": ledger["submitted_quantity"],
        "quantity_python_type": ledger["submitted_quantity_python_type"],
        "fill_event_count": ledger["fill_event_count"],
        "sole_fill_event": ledger["sole_fill_event"],
        "fill_client_order_id_equals_submitted": ledger["fill_order_binding"],
        "subscriptions": ledger["subscriptions"],
        "observations": {
            "quotes": ledger["quote_observation_count"],
            "trades": ledger["trade_observation_count"],
            "bars": ledger["bar_observation_count"],
        },
        "provider_state": provider_state,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "venue_submitted": False,
        "real_t2_credit": False,
    }
    _write_json(phase_root / "result.json", result)
    return result


async def _public_instrument_and_no_signer_proof() -> tuple[object, dict[str, object]]:
    from nautilus_trader.model import CryptoPerpetual

    counters = {
        "provider_client_construction_count": 0,
        "network_call_count": 0,
        "private_api_call_count": 0,
        "signing_count": 0,
        "exchange_write_count": 0,
    }
    _credential_guard(os.environ)
    sequence = ["credential_guard_passed"]
    client = _construct_public_client(env=os.environ, counters=counters)
    sequence.append("provider_client_constructed")
    try:
        client.get_user_address()
    except ValueError as error:
        if type(error) is not ValueError or str(error) != "auth error: No signer configured":
            raise AssertionError("unauthenticated Hyperliquid client raised an unexpected auth error") from error
        get_user_address_error_type = type(error).__name__
        get_user_address_error = str(error)
    else:
        raise AssertionError("unauthenticated Hyperliquid client did not raise the no-signer error")
    sequence.append("get_user_address_raised_value_error_no_signer")
    no_signer_sequence_index = len(sequence) - 1
    counters["network_call_count"] += 1
    sequence.append("load_instrument_definitions_called")
    definitions = await client.load_instrument_definitions()
    values: Sequence[object]
    if isinstance(definitions, Mapping):
        values = tuple(definitions.values())
    elif isinstance(definitions, Sequence):
        values = definitions
    else:
        values = tuple(definitions)
    matches = tuple(item for item in values if str(getattr(item, "id", "")) == PUBLIC_INSTRUMENT_ID)
    if len(matches) != 1:
        raise AssertionError(
            f"public provider returned {len(matches)} definitions for {PUBLIC_INSTRUMENT_ID}"
        )
    instrument = matches[0]
    if not isinstance(instrument, CryptoPerpetual):
        raise AssertionError("public BTC instrument is not provider-native CryptoPerpetual")
    first_network_call_sequence_index = sequence.index("load_instrument_definitions_called")
    if no_signer_sequence_index >= first_network_call_sequence_index:
        raise AssertionError("runtime no-signer proof did not precede the first network call")
    proof: dict[str, object] = {
        "status": "PASS",
        "credential_guard_passed": True,
        "no_signer_proven": True,
        "get_user_address_behavior": "RAISED_VALUE_ERROR_NO_SIGNER",
        "get_user_address_error_type": get_user_address_error_type,
        "get_user_address_error": get_user_address_error,
        "no_signer_sequence_index": no_signer_sequence_index,
        "first_network_call_sequence_index": first_network_call_sequence_index,
        "event_sequence": sequence,
        "public_call": "HyperliquidHttpClient.load_instrument_definitions",
        "public_instrument_id": str(instrument.id),
        "public_instrument_type": f"{type(instrument).__module__}.{type(instrument).__qualname__}",
        "is_crypto_perpetual": True,
        **counters,
    }
    return instrument, proof


def _assert_exact_version() -> None:
    actual = version("nautilus-trader")
    if actual != NAUTILUS_VERSION:
        raise RuntimeError(f"exact Nautilus {NAUTILUS_VERSION} required; found {actual}")


def _overall_base(head: str, tree: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "exact_git_head": head,
        "exact_git_tree": tree,
        "task_packet_identity": TASK_PACKET_IDENTITY,
        "task_packet_sha256": TASK_PACKET_SHA256,
        "nautilus_version": NAUTILUS_VERSION,
        "phase_order": ["PHASE_A", "PHASE_B"],
        "phase_b_requires_phase_a_pass": True,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "venue_submitted": False,
        "real_t2_credit": False,
    }


def run(evidence_root: Path, result_path: Path) -> dict[str, object]:
    _assert_exact_version()
    exact_head, exact_tree = _git_identity()
    evidence_root.mkdir(parents=True, exist_ok=False)
    overall = _overall_base(exact_head, exact_tree)
    overall.update(
        {
            "status": "RUNNING_PHASE_A",
            "phase_a_status": "RUNNING",
            "phase_b_status": "NOT_STARTED",
        }
    )
    _write_json(result_path, overall)

    phase_a = _run_backtest_phase(
        phase="PHASE_A",
        phase_root=evidence_root / "phase-a",
        exact_head=exact_head,
        exact_tree=exact_tree,
        network=False,
        public_provider_call=False,
    )
    if phase_a["status"] != "PASS":
        raise AssertionError("Phase A did not pass; Phase B is prohibited")
    overall.update(
        {
            "status": "PHASE_A_PASS_PHASE_B_NOT_STARTED",
            "phase_a_status": "PASS",
            "phase_b_status": "NOT_STARTED",
            "phase_a": phase_a,
        }
    )
    _write_json(result_path, overall)

    credential_proof = _credential_negative_proof()
    public_instrument, no_signer_proof = asyncio.run(_public_instrument_and_no_signer_proof())
    if str(public_instrument.id) != PUBLIC_INSTRUMENT_ID:
        raise AssertionError("public provider instrument identity changed")
    phase_b = _run_backtest_phase(
        phase="PHASE_B",
        phase_root=evidence_root / "phase-b",
        exact_head=exact_head,
        exact_tree=exact_tree,
        network=True,
        public_provider_call=True,
    )
    if phase_b["status"] != "PASS":
        raise AssertionError("Phase B did not pass")
    if phase_a["same_fixture_sha256"] != phase_b["same_fixture_sha256"]:
        raise AssertionError("Phase A and Phase B did not use the same fixture")
    if phase_a["same_strategy_path"] != phase_b["same_strategy_path"]:
        raise AssertionError("Phase A and Phase B did not use the same strategy path")
    if phase_a["same_config_path"] != phase_b["same_config_path"]:
        raise AssertionError("Phase A and Phase B did not use the same config path")
    if phase_a["same_backtest_implementation_path"] != phase_b[
        "same_backtest_implementation_path"
    ]:
        raise AssertionError("Phase A and Phase B did not use the same backtest path")
    overall.update(
        {
            "status": "PASS",
            "phase_a_status": "PASS",
            "phase_b_status": "PASS",
            "phase_a": phase_a,
            "phase_b": phase_b,
            "credential_negative_proof": credential_proof,
            "runtime_no_signer_proof": no_signer_proof,
            "PHASE_A_FILL_EVENT_COUNT": phase_a["fill_event_count"],
            "PHASE_B_FILL_EVENT_COUNT": phase_b["fill_event_count"],
            "same_fixture_both_phases": True,
            "same_strategy_config_both_phases": True,
            "same_parquet_backtest_node_path_both_phases": True,
        }
    )
    _write_json(result_path, overall)
    _write_json(evidence_root / "result.json", overall)
    return overall


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--result-path", required=True, type=Path)
    args = parser.parse_args()
    stage = "INITIALIZATION"
    try:
        stage = "CAPABILITY_SPIKE"
        result = run(args.evidence_root, args.result_path)
    except Exception as exc:
        try:
            head, tree = _git_identity()
            failure = _overall_base(head, tree)
            failure.update(
                {
                    "status": "FAIL",
                    "failure_stage": stage,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            _write_json(args.result_path, failure)
        except Exception:
            pass
        raise
    print(_canonical_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
