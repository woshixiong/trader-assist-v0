"""Finite synthetic engineering tests, never natural-signal/forward evidence."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from trader_assist_v0.nautilus_e4.dev_legacy_sandbox import (
    LABEL,
    VERSION,
    admission_reasons,
    create_dev_fixture,
)


def test_dev_fixture_requires_explicit_new_isolated_ledger(tmp_path: Path) -> None:
    for path, opt_in in [
        (tmp_path / "forward.sqlite", True),
        (tmp_path / "x.dev-only.sqlite", False),
    ]:
        with pytest.raises(ValueError, match="DEV_ONLY"):
            create_dev_fixture(path, dev_only=opt_in)
    path = tmp_path / "occupied.dev-only.sqlite"
    path.write_text("retained prior evidence")
    with pytest.raises(ValueError, match="DEV_ONLY"):
        create_dev_fixture(path, dev_only=True)
    assert path.read_text() == "retained prior evidence"


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"event_ns": 0}, "NONCAUSAL_OR_UNKNOWN_CLOCK"),
        ({"init_ns": 11_000_000_000}, "NONCAUSAL_OR_UNKNOWN_CLOCK"),
        ({"event_ns": 9_000_000_000, "init_ns": 8_000_000_000}, "NONCAUSAL_OR_UNKNOWN_CLOCK"),
        ({"init_ns": 6_000_000_000}, "STALE"),
        ({"coverage_ok": False}, "GAP"),
        ({"duplicate": True}, "DUPLICATE"),
    ],
)
def test_dev_admission_is_causal_and_fail_closed(change: dict[str, Any], reason: str) -> None:
    inputs = dict(
        now_ns=10_000_000_000,
        event_ns=5_000_000_000,
        init_ns=9_000_000_000,
        coverage_ok=True,
        duplicate=False,
    )
    assert admission_reasons(**inputs) == []
    assert reason in admission_reasons(**{**inputs, **change})


@pytest.mark.skipif(
    importlib.util.find_spec("nautilus_trader") is None, reason="official Linux rc7 CI"
)
@pytest.mark.parametrize(
    "scenario", ["filled_exit", "partial_cancel_exit", "unfilled_cancel", "deny"]
)
def test_dev_native_sandbox_causal_lifecycle(tmp_path: Path, scenario: str) -> None:
    asyncio.run(_native_scenario(tmp_path, scenario))


async def _native_scenario(root: Path, scenario: str) -> None:
    from nautilus_trader.adapters.sandbox import (
        SandboxExecutionClientConfig,
        SandboxExecutionClientFactory,
    )
    from nautilus_trader.common import Environment
    from nautilus_trader.execution import MakerTakerFeeModel
    from nautilus_trader.live import (
        DataClientConfig,
        LiveExecutionEngineConfig,
        LiveNodeBuilder,
        LiveNodeConfig,
        LiveRiskEngineConfig,
    )
    from nautilus_trader.live.clients import DataClient, DataClientFactory
    from nautilus_trader.model import (
        AccountType,
        Bar,
        BarType,
        BookType,
        Money,
        OmsType,
        Price,
        Quantity,
        QuoteTick,
        TraderId,
        Venue,
    )
    from test_nautilus_vnext_g4_runner import native_hyperliquid_instrument

    from trader_assist_v0.nautilus_e4.native_catalog import read_staged_run, streaming_config

    instrument = native_hyperliquid_instrument()
    holder: list[Any] = []
    subscribed = asyncio.Event()

    class FiniteFixtureInput(DataClient):
        """Test-only finite typed injection using the official adapter test seam.

        No sockets, requests, polling, reconnection, clock rewriting or collector.
        """

        async def _connect(self) -> None:
            self._handle_instrument(instrument)

        async def _disconnect(self) -> None:
            pass

        async def _subscribe_quotes(self, command: Any) -> None:
            pass

        async def _subscribe_bars(self, command: Any) -> None:
            subscribed.set()

    class FiniteFixtureFactory(DataClientFactory):
        @staticmethod
        def create(**kwargs: Any) -> Any:
            client = FiniteFixtureInput(**kwargs, venue=Venue("HYPERLIQUID"))
            holder.append(client)
            return client

    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId("DEV-001"),
        streaming=streaming_config(root, continuous=True),
        shutdown_on_error=True,
        risk_engine=LiveRiskEngineConfig(bypass=False),
        exec_engine=LiveExecutionEngineConfig(reconciliation=False),
    )
    builder = LiveNodeBuilder.from_config("DEV_ONLY", config)
    builder.add_data_client("DEV-FIXTURE", FiniteFixtureFactory(), DataClientConfig())
    builder.add_simulated_exec_client(
        "HYPERLIQUID",
        SandboxExecutionClientFactory(),
        SandboxExecutionClientConfig(
            venue=Venue("HYPERLIQUID"),
            starting_balances=[
                Money.from_str("0.01 USDC" if scenario == "deny" else "100000 USDC"),
                Money.from_str("100000 USD"),
            ],
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            default_leverage=Decimal("1"),
            book_type=BookType.L1_MBP,
            fee_model=MakerTakerFeeModel(Decimal("0.000432"), Decimal("0.000432")),
            liquidity_consumption=True,
            use_reduce_only=True,
        ),
    )
    builder.with_delay_post_stop_secs(0).with_delay_shutdown_secs(0)
    node = builder.build()
    fixture = create_dev_fixture(
        root / "fixture.dev-only.sqlite", dev_only=True, passive=scenario == "unfilled_cancel"
    )
    fixture.observations = asyncio.Queue()
    node.add_strategy(fixture)
    handle, instance_id, cache = node.handle(), str(node.instance_id), node.cache
    pending: dict[str, list[Any]] = {}

    async def observed(kind: str | tuple[str, ...]) -> Any:
        kinds = (kind,) if isinstance(kind, str) else kind
        for name in kinds:
            if pending.get(name):
                return pending[name].pop(0)
        while True:
            found, value = await asyncio.wait_for(fixture.observations.get(), timeout=8)
            if found in kinds:
                return value
            pending.setdefault(found, []).append(value)

    def quote(bid: str = "1999.0", ask: str = "2000.0", size: str = "1.000") -> Any:
        now = fixture.clock.timestamp_ns()
        return QuoteTick(
            instrument.id,
            Price.from_str(bid),
            Price.from_str(ask),
            Quantity.from_str(size),
            Quantity.from_str(size),
            now,
            now,
        )

    def bar(minutes: int = 5, future: bool = False) -> Any:
        now = fixture.clock.timestamp_ns()
        duration = minutes * 60_000_000_000
        start = now // duration * duration - (0 if future else duration)
        return Bar(
            BarType.from_str(f"{instrument.id}-{minutes}-MINUTE-LAST-EXTERNAL"),
            Price.from_str("1998.0"),
            Price.from_str("2002.0"),
            Price.from_str("1997.0"),
            Price.from_str("2000.0"),
            Quantity.from_str("1.000"),
            start,
            now,
        )

    run = asyncio.create_task(node.run_async())
    try:
        await asyncio.wait_for(subscribed.wait(), timeout=8)
        client = holder[0]
        # Direct native-typed callback negatives cannot enter the native matcher.
        fixture.on_bar(bar(1))
        assert "WRONG_5M_SOURCE" in await observed("REJECT")
        fixture.on_bar(bar(future=True))
        assert "BAR_NOT_CLOSED" in await observed("REJECT")
        source = bar()
        client._handle_data(source)
        await observed("SIGNAL")
        fixture.on_bar(source)
        assert "DUPLICATE" in await observed("REJECT")
        fixture.coverage_ok = False
        client._handle_data(quote())
        assert "GAP" in await observed("REJECT")
        assert fixture.entry is None
        fixture.coverage_ok = True
        tick = quote(size="0.020" if scenario == "partial_cancel_exit" else "1.000")
        client._handle_data(tick)
        if scenario == "deny":
            # Native margin insufficiency is a harness fault, not strategy economics.
            await observed(("OrderDenied", "OrderRejected"))
            assert fixture.failed and not cache.positions_open()
        else:
            await observed("OrderAccepted")
            if scenario == "unfilled_cancel":
                entry_state = cache.order(fixture.entry.client_order_id)
                assert Decimal(str(entry_state.filled_qty)) == 0
                fixture.cancel_order(entry_state)
                await observed("OrderCanceled")
                assert not cache.positions_open()
            else:
                await observed("OrderFilled")
                entry_state = cache.order(fixture.entry.client_order_id)
                if scenario == "partial_cancel_exit":
                    assert Decimal("0") < Decimal(str(entry_state.filled_qty)) < Decimal("0.050")
                    fixture.cancel_order(entry_state)
                    await observed("OrderCanceled")
                else:
                    assert Decimal(str(entry_state.filled_qty)) == Decimal("0.050")
                # Native quote occurs strictly after entry; never fill at a past bar price.
                client._handle_data(quote("1989.0", "1990.0"))
                await observed("PositionClosed")
                assert not cache.positions_open()
        state = fixture.snapshot()
        rows = list(fixture.ledger.db.execute("SELECT kind,payload FROM events"))
        assert all(json.loads(raw)["strategy_id"] == VERSION for _, raw in rows)
        assert any(kind == "DEV_PROFILE" and LABEL in raw for kind, raw in rows)
        for kind, raw in rows:
            if kind == "DEV_ORDER_EVENT_LINK":
                assert (
                    json.loads(raw)["payload"]["link"]["source_hash"]
                    == fixture.source["source_hash"]
                )
        fills = [json.loads(raw)["payload"] for kind, raw in rows if kind == "OrderFilled"]
        if scenario in {"filled_exit", "partial_cancel_exit"}:
            assert len(fills) >= 2 and all(fill["commission"] for fill in fills)
            assert state["realized_pnl"] and state["positions"]
            native_fills = [
                event
                for order in cache.orders()
                for event in order.events()
                if type(event).__name__ == "OrderFilled"
            ]
            assert all(fill.commission.as_decimal() > 0 for fill in native_fills)
            assert cache.positions()[0].realized_pnl.as_decimal() < 0
        else:
            assert not fills
        assert fixture.ledger.verify() == len(rows)
    finally:
        handle.stop()
        await asyncio.wait_for(run, timeout=8)
        node.dispose()
        del node  # Release native thread ownership even when pytest retains a failed frame.
        fixture.ledger.close()
    proof = read_staged_run(root, instance_id, require_closed=True)
    assert proof["types"]["QuoteTick"]["count"] >= 2
    assert proof["types"]["Bar"]["count"] == 1
