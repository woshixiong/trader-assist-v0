"""Deterministic A1 runtime acceptance matrix; no provider transport is used."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import (
    MultiAssetPublicRuntime,
    ReconnectRequired,
)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


class Clock:
    def __init__(self, seconds: int = 303) -> None:
        self.seconds = seconds
        self.monotonic_seconds = 0.0

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.seconds += int(seconds)
        self.monotonic_seconds += seconds
        await asyncio.sleep(0)


def candle(coin: str, open_ms: int, *, close: str = "100") -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": close,
        "v": "10",
    }


def market(
    coin: str = "BTC", lifecycle: MarketLifecycle = MarketLifecycle.WARMING
) -> RegistryMarket:
    return RegistryMarket(
        display=coin,
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin=coin),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=lifecycle,
        metadata_observed_at=datetime(2026, 8, 12, tzinfo=UTC),
        metadata_hash=sha256_hex(coin.encode()),
    )


class Client:
    def __init__(self, values: list[object]) -> None:
        self.values = values
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def setup(
    tmp_path: Path,
    *,
    clock: Clock | None = None,
    lifecycle: MarketLifecycle = MarketLifecycle.WARMING,
    client_values: list[object] | None = None,
) -> tuple[MultiAssetPublicRuntime, MultiAssetDataAuthority, RegistryMarket, Clock, Client]:
    clock = clock or Clock()
    item = market(lifecycle=lifecycle)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version="seed", created_at=clock.now(), markets=(item,))
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
    )
    client = Client(client_values or [[candle("BTC", 0)]])
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    return runtime, authority, item, clock, client


@async_test
async def test_bootstrap_pending_seed_warms_then_admitted_boundary_activates_without_formalization(
    tmp_path: Path,
) -> None:
    runtime, authority, item, clock, _ = setup(tmp_path)
    assert runtime.registry.active() is None
    assert runtime.selected_markets() == (item,)
    runtime.warmup(item, start_ms=0, end_ms=300_000)
    assert runtime.registry.active() is not None
    active = runtime.registry.active()
    assert active is not None and active.version == "seed"
    assert not authority.can_formalize(active.markets[0])
    row = authority.store.connection.execute(
        "SELECT registry_version, registry_content_hash FROM closed_bars WHERE interval='5m'"
    ).fetchone()
    assert row == ("seed", active.content_hash)
    assert clock.now().tzinfo is UTC


@async_test
async def test_candidate_is_scheduled_nonblocking_and_admits_without_second_ws_message(
    tmp_path: Path,
) -> None:
    runtime, authority, item, _, client = setup(tmp_path, client_values=[[candle("BTC", 0)]])
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    assert client.calls == []
    task = runtime._finality.task_for(item.identity.market_id)
    assert task is not None
    await task
    assert len(client.calls) == 2
    assert authority.store.last_open(item.identity.market_id) == 0


@async_test
async def test_finality_gap_change_and_supersession_fail_closed_or_cancel_stale(
    tmp_path: Path,
) -> None:
    runtime, authority, item, clock, _ = setup(
        tmp_path,
        client_values=[[candle("BTC", 0)], [candle("BTC", 0, close="101")]],
    )
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    task = runtime._finality.task_for(item.identity.market_id)
    assert task is not None
    await task
    assert authority.store.bars(item.identity.market_id) == ()
    # A later market generation replaces the only pending task rather than
    # accumulating unbounded candidates for the same market.
    clock.seconds = 603
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 300_000)}))
    first = runtime._finality.task_for(item.identity.market_id)
    assert first is not None
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 600_000)}))
    assert runtime._finality.task_for(item.identity.market_id) is first
    assert len(runtime._finality.tasks) == 1


class Socket:
    def __init__(self, frames: list[object], *, shutdown: asyncio.Event | None = None) -> None:
        self.frames = frames
        self.sent: list[str] = []
        self.shutdown = shutdown
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(raw)

    async def recv(self) -> str:
        if self.frames:
            value = self.frames.pop(0)
            if isinstance(value, BaseException):
                raise value
            if self.shutdown is not None:
                self.shutdown.set()
            return str(value)
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


def ack(coin: str = "BTC") -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": coin, "interval": "5m"},
            },
        }
    )


@async_test
async def test_startup_warmup_ack_policy_and_shutdown_are_runtime_owned(tmp_path: Path) -> None:
    clock = Clock(seconds=600)
    runtime, authority, item, _, client = setup(
        tmp_path, clock=clock, client_values=[[candle("BTC", 300_000)]]
    )
    shutdown = asyncio.Event()
    socket = Socket([ack()], shutdown=shutdown)

    async def factory(_: str) -> Socket:
        return socket

    runtime.websocket_factory = factory
    await runtime.run(shutdown)
    assert client.calls  # run(), not an external caller, warmed history.
    assert authority.store.last_open(item.identity.market_id) == 300_000
    assert runtime.health.acknowledgements == {"BTC"}
    assert socket.closed


@async_test
async def test_ack_unknown_duplicate_timeout_and_reconnect_close_paths(tmp_path: Path) -> None:
    runtime, _, _, _, _ = setup(tmp_path)
    runtime._expected_acks = {"BTC"}
    await runtime.handle_message(ack())
    await runtime.handle_message(ack())
    assert runtime.health.acknowledgements == {"BTC"}
    with pytest.raises(ReconnectRequired, match="unknown"):
        await runtime.handle_message(ack("ETH"))

    class Never(Socket):
        async def recv(self) -> str:
            await asyncio.Future()
            raise AssertionError("unreachable")

    runtime.acknowledgement_timeout_seconds = 0.001
    runtime.health.acknowledgements.clear()
    with pytest.raises(ReconnectRequired, match="timeout"):
        await runtime._await_acknowledgements(Never([]), asyncio.Event())

    clock = Clock(seconds=600)
    recovery, _, _, _, _ = setup(
        tmp_path / "reconnect", clock=clock, client_values=[[candle("BTC", 300_000)]]
    )
    shutdown = asyncio.Event()
    sockets = [Socket([ack(), ConnectionClosedOK(None, None)]), Socket([ack()], shutdown=shutdown)]

    async def factory(_: str) -> Socket:
        return sockets.pop(0)

    recovery.websocket_factory = factory
    await recovery.run(shutdown)
    assert recovery.health.reconnects == 1
    assert recovery.health.subscriptions == 1


@async_test
async def test_error_close_reconnects_and_exhaustion_stops(tmp_path: Path) -> None:
    clock = Clock(seconds=600)
    runtime, _, _, _, _ = setup(tmp_path, clock=clock, client_values=[[candle("BTC", 300_000)]])
    sockets = [Socket([ack(), ConnectionClosedError(None, None)]) for _ in range(4)]

    async def factory(_: str) -> Socket:
        return sockets.pop(0)

    runtime.websocket_factory = factory
    await runtime.run(asyncio.Event())
    assert runtime.health.reconnects == 3
    assert runtime.health.connection_count == 0


@async_test
async def test_lifecycle_advances_one_safe_boundary_at_a_time(tmp_path: Path) -> None:
    clock = Clock(seconds=600)
    runtime, authority, item, _, _ = setup(tmp_path, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 300_000)], received_at=clock.now()
    )
    assert runtime.registry.active() is not None
    for open_ms, expected in (
        (600_000, MarketLifecycle.HISTORY_READY),
        (900_000, MarketLifecycle.SNAPSHOT_READY),
        (1_200_000, MarketLifecycle.ACTIVE),
    ):
        await runtime._maybe_stage_lifecycle(snapshot_ready=True)
        pending = runtime.registry.pending_version()
        assert pending is not None
        candidate = pending.markets[0]
        assert candidate.lifecycle is expected
        clock.seconds = (open_ms + 303_000) // 1000
        authority.admit_rest_history(
            market=candidate,
            snapshot=[candle("BTC", open_ms)],
            received_at=clock.now(),
        )
    active = runtime.registry.active()
    assert active is not None and active.markets[0].lifecycle is MarketLifecycle.ACTIVE
    assert authority.can_formalize(active.markets[0])


def test_runtime_readiness_snapshot_binds_transport_failure_registry_and_currentness(
    tmp_path: Path,
) -> None:
    runtime, authority, item, clock, _ = setup(tmp_path, lifecycle=MarketLifecycle.ACTIVE)
    authority.admit_rest_history(market=item, snapshot=[candle("BTC", 0)], received_at=clock.now())
    runtime.health.data_ready = True
    ready = runtime.readiness_snapshot()
    active = runtime.registry.active()
    assert active is not None
    assert ready.registry_version == active.version
    assert ready.registry_content_hash == active.content_hash
    assert ready.latest_closed_5m_open_time_ms == 0
    assert ready.ready_market_ids == (item.identity.market_id,)

    runtime.health.failed_markets.add(item.identity.market_id)
    failed = runtime.readiness_snapshot()
    assert failed.ready_market_ids == ()
    assert failed.failed_market_ids == (item.identity.market_id,)

    runtime.health.failed_markets.clear()
    runtime.health.data_ready = False
    disconnected = runtime.readiness_snapshot()
    assert disconnected.ready_market_ids == ()
    assert disconnected.data_ready is False
