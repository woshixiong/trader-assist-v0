"""Deterministic Hyperliquid connection-session contract acceptance."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any

import pytest
from websockets.exceptions import ConnectionClosedOK

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
    DataRouteError,
    MultiAssetDataAuthority,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import (
    MarketRegistryManager,
    RegistryError,
)
from trader_assist_v0.multi_asset_shadow.runtime import (
    MultiAssetPublicRuntime,
    ReconnectRequired,
)


class Clock:
    def __init__(self) -> None:
        self.seconds = 303
        self.monotonic_seconds = 0.0
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.seconds += int(seconds)
        self.monotonic_seconds += seconds
        await asyncio.sleep(0)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


class PublicClient:
    def closed_candles(self, **_: object) -> object:
        raise AssertionError("session tests bypass history acquisition only")


class SessionSocket:
    def __init__(self, *, fail_ping: bool = False) -> None:
        self.frames: asyncio.Queue[object] = asyncio.Queue()
        self.sent: list[str] = []
        self.closed = False
        self.fail_ping = fail_ping
        self.recv_calls = 0
        self.active_recv = 0
        self.max_active_recv = 0
        self.recv_owners: set[asyncio.Task[Any]] = set()

    async def send(self, raw: str) -> None:
        self.sent.append(raw)
        if self.fail_ping and raw == '{"method":"ping"}':
            raise OSError("injected heartbeat send failure")

    async def recv(self) -> str:
        owner = asyncio.current_task()
        assert owner is not None
        self.recv_owners.add(owner)
        self.recv_calls += 1
        self.active_recv += 1
        self.max_active_recv = max(self.max_active_recv, self.active_recv)
        try:
            frame = await self.frames.get()
        finally:
            self.active_recv -= 1
        if isinstance(frame, BaseException):
            raise frame
        return str(frame)

    async def close(self) -> None:
        self.closed = True

    def feed(self, frame: object) -> None:
        self.frames.put_nowait(frame)


def candle(coin: str = "BTC") -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": 0,
        "T": 299_999,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "10",
    }


def acknowledgement(coin: str = "BTC") -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": coin, "interval": "5m"},
            },
        }
    )


def compose(tmp_path: Path) -> tuple[MultiAssetPublicRuntime, Clock]:
    clock = Clock()
    item = RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=clock.now(),
        metadata_hash=sha256_hex(b"BTC"),
    )
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="seed", created_at=clock.now(), markets=(item,))
    registry.stage(version)
    registry.request_apply(version.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    authority.admit_rest_history(market=item, snapshot=[candle()], received_at=clock.now())
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=PublicClient(),  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        heartbeat_interval_seconds=0.01,
    )

    async def startup(_: asyncio.Event) -> bool:
        return True

    async def ticker(shutdown: asyncio.Event) -> None:
        await shutdown.wait()

    runtime._startup_warmup_barrier = startup  # type: ignore[method-assign]
    runtime._barrier_ticker = ticker  # type: ignore[method-assign]
    return runtime, clock


async def wait_until(predicate: Callable[[], bool], *, timeout: float = 1.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.001)


async def start(
    runtime: MultiAssetPublicRuntime, socket: SessionSocket, shutdown: asyncio.Event
) -> asyncio.Task[None]:
    async def factory(_: str) -> SessionSocket:
        return socket

    runtime.websocket_factory = factory
    task = asyncio.create_task(runtime.run(shutdown))
    await wait_until(lambda: len(socket.sent) >= 1)
    return task


@async_test
async def test_provider_control_contract_and_single_session_owners(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    socket.feed("Websocket connection established.")
    socket.feed(acknowledgement())
    await wait_until(lambda: runtime.health.data_ready)
    receiver_tasks = [
        item for item in asyncio.all_tasks() if item.get_name() == "hyperliquid-ws-receiver"
    ]
    heartbeat_tasks = [
        item for item in asyncio.all_tasks() if item.get_name() == "hyperliquid-ws-heartbeat"
    ]
    assert len(receiver_tasks) == 1
    assert len(heartbeat_tasks) == 1
    await wait_until(lambda: socket.sent.count('{"method":"ping"}') >= 2)
    socket.feed(json.dumps({"channel": "pong"}))
    await wait_until(lambda: runtime.health.heartbeat_pongs == 1)
    assert socket.sent[0] == (
        '{"method":"subscribe","subscription":{"type":"candle","coin":"BTC","interval":"5m"}}'
    )
    assert socket.max_active_recv == 1
    assert len(socket.recv_owners) == 1
    assert runtime.health.greeting_count == 1
    assert runtime.health.heartbeat_sent >= 2
    shutdown.set()
    await task
    assert socket.closed
    assert runtime.health.data_ready is False
    assert runtime.health.connection_count == 0
    assert runtime.health.acknowledgements == set()
    assert not {
        item.get_name() for item in asyncio.all_tasks() if item is not asyncio.current_task()
    } & {"hyperliquid-ws-receiver", "hyperliquid-ws-heartbeat"}


@async_test
async def test_control_parser_is_exact_and_unknown_frames_fail_closed(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    runtime._expected_acks = {"BTC"}
    await runtime.handle_message("Websocket connection established.")
    await runtime.handle_message(json.dumps({"channel": "pong"}))
    await runtime.handle_message(acknowledgement())
    assert runtime.health.acknowledgements == {"BTC"}
    with pytest.raises(ReconnectRequired, match="unknown"):
        await runtime.handle_message(json.dumps({"channel": "pong", "data": {}}))
    with pytest.raises(ReconnectRequired, match="unknown"):
        await runtime.handle_message(json.dumps({"channel": "mystery"}))
    with pytest.raises(DataRouteError, match="websocket message is invalid"):
        await runtime.handle_message("not-json")


@async_test
async def test_shutdown_during_ack_never_enters_ready_and_joins_tasks(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    shutdown.set()
    await task
    assert runtime.health.data_ready is False
    assert runtime.health.ready_transitions == 0
    assert socket.closed and socket.active_recv == 0


@async_test
async def test_ack_timeout_exhaustion_uses_unified_teardown(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    runtime.acknowledgement_timeout_seconds = 0.01
    socket = SessionSocket()
    calls = 0

    async def factory(_: str) -> SessionSocket:
        nonlocal calls
        calls += 1
        return socket

    runtime.websocket_factory = factory
    with pytest.raises(ReconnectRequired, match="reconnect attempts exhausted"):
        await runtime.run(asyncio.Event())
    assert calls == 4
    assert runtime.health.connections == runtime.health.disconnects == 4
    assert runtime.health.connection_count == 0
    assert runtime.health.data_ready is False
    assert runtime.health.acknowledgements == set()
    assert socket.closed and socket.active_recv == 0


@async_test
async def test_heartbeat_failure_withdraws_ready_and_reconnects(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket(fail_ping=True)
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    socket.feed(acknowledgement())
    await wait_until(lambda: runtime.health.data_ready)
    await wait_until(lambda: runtime.health.heartbeat_failures == 1)
    await wait_until(lambda: runtime.health.reconnects == 1)
    shutdown.set()
    await task
    assert runtime.health.data_ready is False
    assert runtime.health.connection_count == 0
    assert socket.closed and socket.active_recv == 0


@async_test
async def test_malformed_frame_enters_unified_reconnect_and_teardown(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    socket.feed(acknowledgement())
    await wait_until(lambda: runtime.health.data_ready)
    socket.feed("not-json")
    await wait_until(lambda: runtime.health.reconnects == 1)
    shutdown.set()
    await task
    assert runtime.health.data_ready is False
    assert runtime.health.last_disconnect_error == "DataRouteError"
    assert socket.closed and socket.active_recv == 0


@pytest.mark.parametrize("after_ready", [False, True])
@async_test
async def test_provider_close_before_ack_or_after_ready_reconnects(
    tmp_path: Path, after_ready: bool
) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    if after_ready:
        socket.feed(acknowledgement())
        await wait_until(lambda: runtime.health.data_ready)
    socket.feed(ConnectionClosedOK(None, None))
    await wait_until(lambda: runtime.health.reconnects == 1)
    shutdown.set()
    await task
    assert runtime.health.data_ready is False
    assert runtime.health.disconnects >= 1
    assert socket.max_active_recv == 1


@async_test
async def test_transient_connect_error_retries_but_fatal_connect_error_surfaces(
    tmp_path: Path,
) -> None:
    runtime, clock = compose(tmp_path / "transient")
    socket = SessionSocket()
    shutdown = asyncio.Event()
    calls = 0

    async def transient_factory(_: str) -> SessionSocket:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("transient")
        return socket

    runtime.websocket_factory = transient_factory
    task = asyncio.create_task(runtime.run(shutdown))
    await wait_until(lambda: calls == 2)
    shutdown.set()
    await task
    assert runtime.health.reconnects == 1
    assert runtime.connection_attempt_spacing_seconds in clock.sleeps

    fatal, _ = compose(tmp_path / "fatal")

    async def fatal_factory(_: str) -> SessionSocket:
        raise ValueError("fatal connect configuration")

    fatal.websocket_factory = fatal_factory
    with pytest.raises(ValueError, match="fatal connect configuration"):
        await fatal.run(asyncio.Event())
    assert fatal.health.reconnects == 0


@async_test
async def test_subscription_identity_drift_uses_heartbeat_reconnect_path(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    shutdown = asyncio.Event()
    task = await start(runtime, socket, shutdown)
    socket.feed(acknowledgement())
    await wait_until(lambda: runtime.health.data_ready)
    original = runtime._current_subscription_identity
    identity = original()
    events: list[tuple[str, dict[str, object]]] = []
    runtime.on_session_event = lambda event, fields: events.append((event, fields))
    runtime._current_subscription_identity = lambda: (  # type: ignore[method-assign]
        *identity,
        ("candle", "ETH", "5m"),
    )
    await wait_until(lambda: runtime.health.reconnects == 1)
    shutdown.set()
    await task
    assert runtime.health.data_ready is False
    assert runtime.health.last_disconnect_error == "ReconnectRequired"
    assert runtime.health.heartbeat_failures == 0
    assert any(
        event == "SESSION_REFRESH"
        and fields["reason"] == "PROVIDER_SUBSCRIPTION_PROJECTION_CHANGED"
        for event, fields in events
    )


@async_test
async def test_projection_registry_error_is_fatal_not_heartbeat(tmp_path: Path) -> None:
    runtime, _ = compose(tmp_path)
    socket = SessionSocket()
    task = await start(runtime, socket, asyncio.Event())
    socket.feed(acknowledgement())
    await wait_until(lambda: runtime.health.data_ready)
    injected = RegistryError("injected projection authority failure")

    def fail_projection() -> tuple[tuple[str, str, str], ...]:
        raise injected

    runtime._current_subscription_identity = fail_projection  # type: ignore[method-assign]
    with pytest.raises(RegistryError, match="injected projection") as exc_info:
        await task
    assert exc_info.value is injected
    assert runtime.health.heartbeat_failures == 0
    assert runtime.health.reconnects == 0
    assert runtime.health.last_disconnect_error == "RegistryError"
