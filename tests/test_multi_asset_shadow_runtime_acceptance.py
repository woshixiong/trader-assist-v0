"""Deterministic A1 runtime acceptance matrix; no provider transport is used."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosedOK

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import PublicDataError
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
    WARMUP_ADMISSION_CHUNK_BARS,
    WARMUP_CATCHUP_ROUNDS_MAX,
    BoundaryMode,
    MultiAssetPublicRuntime,
    ReconnectRequired,
    RuntimeReadinessSnapshot,
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
        self.sleep_seconds: list[float] = []

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.sleep_seconds.append(seconds)
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
async def test_ws_candidate_is_observation_only_without_rest_or_wake(
    tmp_path: Path,
) -> None:
    # Single-owner architecture: a WS candle message may persist a candidate
    # observation, but never performs provider REST, never admits evidence,
    # and never wakes global application authority (packet attack AR/AV).
    runtime, authority, item, _, client = setup(tmp_path, client_values=[[candle("BTC", 0)]])
    wakes: list[BoundaryMode] = []
    runtime.on_finalized_5m = lambda _bar, mode: wakes.append(mode)
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    await asyncio.sleep(0)
    assert client.calls == []
    assert authority.store.last_open(item.identity.market_id) is None
    assert wakes == []


@async_test
async def test_candidate_supersession_stays_observation_only(tmp_path: Path) -> None:
    # A later observation of the same unfinalized boundary replaces the prior
    # candidate without accumulating per-market finality tasks, without REST,
    # and without any durable ClosedBar (gap/change/supersession authority
    # now lives in the data authority and the cohort barrier).
    runtime, authority, item, clock, client = setup(tmp_path)
    wakes: list[BoundaryMode] = []
    runtime.on_finalized_5m = lambda _bar, mode: wakes.append(mode)
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    clock.seconds = 603
    await runtime.handle_message(
        json.dumps({"channel": "candle", "data": candle("BTC", 0, close="101")})
    )
    assert client.calls == []
    assert authority.store.bars(item.identity.market_id) == ()
    assert wakes == []


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
    callbacks: list[tuple[int, BoundaryMode]] = []
    runtime.on_finalized_5m = lambda bar, mode: callbacks.append((bar.open_time_ms, mode))
    await runtime.run(shutdown)
    assert client.calls  # run(), not an external caller, warmed history.
    assert authority.store.last_open(item.identity.market_id) == 300_000
    assert runtime.health.acknowledgements == {"BTC"}
    assert socket.closed
    # Startup warmup owns no application wake: only the cohort barrier may
    # wake global LIVE_ACTIONABLE authority.
    assert callbacks == []


@async_test
async def test_ws_boundary_evidence_never_wakes_application_directly(tmp_path: Path) -> None:
    # Packet attack AV replacement: per-market WS evidence may persist, but
    # global action occurs only when the cohort barrier processes the boundary.
    runtime, _, item, _, _ = setup(tmp_path, client_values=[[candle("BTC", 0)]])
    callbacks: list[tuple[str, int, BoundaryMode]] = []
    runtime.on_finalized_5m = lambda bar, mode: callbacks.append(
        (bar.market_id, bar.open_time_ms, mode)
    )
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    await asyncio.sleep(0)
    assert callbacks == []
    assert item.identity.market_id not in runtime.health.nonrecoverable_markets


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
async def test_repeated_completed_reconnects_replenish_budget(tmp_path: Path) -> None:
    clock = Clock(seconds=600)
    runtime, _, _, _, _ = setup(
        tmp_path, clock=clock, client_values=[[candle("BTC", 300_000)]]
    )
    shutdown = asyncio.Event()
    sockets = [Socket([ack(), ConnectionClosedOK(None, None)]) for _ in range(5)]
    sockets.append(Socket([ack()], shutdown=shutdown))
    created: list[Socket] = []
    wakes: list[BoundaryMode] = []

    async def factory(_: str) -> Socket:
        socket = sockets.pop(0)
        created.append(socket)
        return socket

    runtime.websocket_factory = factory
    runtime.on_finalized_5m = lambda _bar, mode: wakes.append(mode)
    await runtime.run(shutdown)

    # Four completed reconnects (more than the nominal maximum of three) each
    # re-established provider history. Reconnect recovery owns no application
    # wake in the single-owner architecture: only the barrier wakes action.
    assert len(created) == 6
    assert wakes == []
    assert runtime.health.reconnects == 5
    assert runtime.health.data_ready is True
    assert all(socket.closed for socket in created)


@async_test
async def test_consecutive_incomplete_recoveries_exhaust_budget_fail_closed(
    tmp_path: Path,
) -> None:
    clock = Clock(seconds=600)
    runtime, _, _, _, _ = setup(
        tmp_path, clock=clock, client_values=[[candle("BTC", 300_000)]]
    )
    sockets = [Socket([ack("ETH")]) for _ in range(4)]
    created: list[Socket] = []

    async def factory(_: str) -> Socket:
        socket = sockets.pop(0)
        created.append(socket)
        return socket

    runtime.websocket_factory = factory
    await runtime.run(asyncio.Event())

    # The initial startup failure is free. Three later incomplete recoveries
    # consume the bounded budget without any READY/application-wake reset.  The
    # reconnect backoff sequence is isolated from the barrier ticker's pacing
    # sleeps (5s each) observed on the same injected clock.
    assert len(created) == 4
    assert runtime.health.reconnects == 3
    assert runtime.health.connection_count == 0
    assert runtime.health.data_ready is False
    backoffs = [value for value in clock.sleep_seconds if value in (1.0, 2.0, 4.0)]
    assert backoffs == [1.0, 2.0, 4.0]
    assert all(socket.closed for socket in created)


@async_test
async def test_lifecycle_advances_one_safe_boundary_at_a_time(tmp_path: Path) -> None:
    # Lifecycle staging is owned solely by the cohort barrier: each boundary
    # advances exactly one legal stage for the minimum PRE_ACTIVE cohort.
    clock = Clock(seconds=600)
    runtime, authority, item, _, _ = setup(tmp_path, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 300_000)], received_at=clock.now()
    )
    runtime.health.data_ready = True
    runtime.health.acknowledgements = {item.identity.coin}
    assert runtime.registry.active() is not None
    active = runtime.registry.active()
    assert active is not None
    for open_ms, expected in (
        (600_000, MarketLifecycle.HISTORY_READY),
        (900_000, MarketLifecycle.SNAPSHOT_READY),
        (1_200_000, MarketLifecycle.ACTIVE),
    ):
        clock.seconds = (open_ms + 303_000) // 1000
        authority.admit_rest_history(
            market=active.markets[0],
            snapshot=[candle("BTC", open_ms)],
            received_at=clock.now(),
        )
        await runtime.process_cohort_boundary(open_ms)
        active = runtime.registry.active()
        assert active is not None
        assert active.markets[0].lifecycle is expected
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


# ---------------------------------------------------------------------------
# Cold-start cohort warmup acceptance (captured T0, bounded catch-up, barrier,
# chunked admission, shutdown responsiveness, trading freshness).
# ---------------------------------------------------------------------------


class WindowClient:
    """Deterministic public client serving exactly the closed bars in [start, end)."""

    def __init__(self, coins: tuple[str, ...], clock: Clock) -> None:
        self.coins = coins
        self.clock = clock
        self.calls: list[tuple[str, int, int]] = []
        self.on_call: Callable[[], None] | None = None
        self.fail_coins: frozenset[str] = frozenset()

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        if self.on_call is not None:
            self.on_call()
        if coin in self.fail_coins:
            raise PublicDataError("provider route failed")
        return [candle(coin, open_ms) for open_ms in range(max(0, start_ms), end_ms, 300_000)]


class RecordingAuthority(MultiAssetDataAuthority):
    """Spy over the unchanged public Data seam admitting in bounded chunks."""

    def __init__(self, *, store: ClosedBarStore, registry: MarketRegistryManager) -> None:
        super().__init__(store=store, registry=registry)
        self.admission_sizes: list[int] = []
        self.on_admission: Callable[[], None] | None = None

    def admit_rest_history(  # type: ignore[override]
        self, *, market: RegistryMarket, snapshot: object, received_at: datetime
    ) -> object:
        assert isinstance(snapshot, list)
        self.admission_sizes.append(len(snapshot))
        if self.on_admission is not None:
            self.on_admission()
        return super().admit_rest_history(
            market=market, snapshot=snapshot, received_at=received_at
        )


class CohortSocket:
    """Socket acknowledging every subscribed coin, then setting shutdown."""

    def __init__(self, coins: tuple[str, ...], shutdown: asyncio.Event) -> None:
        self.frames = [ack(coin) for coin in coins]
        self.shutdown = shutdown
        self.sent: list[str] = []
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(raw)

    async def recv(self) -> str:
        if self.frames:
            return self.frames.pop(0)
        self.shutdown.set()
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


def cohort_setup(
    tmp_path: Path,
    coins: tuple[str, ...],
    clock: Clock,
    *,
    client: object | None = None,
    spy: bool = False,
) -> tuple[
    MultiAssetPublicRuntime,
    MultiAssetDataAuthority,
    tuple[RegistryMarket, ...],
    Clock,
    WindowClient | Client,
]:
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    markets = tuple(market(coin) for coin in coins)
    seed = RegistryVersion.create(version="seed", created_at=clock.now(), markets=markets)
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority: MultiAssetDataAuthority
    if spy:
        authority = RecordingAuthority(
            store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
        )
    else:
        authority = MultiAssetDataAuthority(
            store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
        )
    selected_client: WindowClient | Client
    if client is not None:
        assert isinstance(client, WindowClient | Client)
        selected_client = client
    else:
        selected_client = WindowClient(coins, clock)
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=selected_client,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    return runtime, authority, markets, clock, selected_client


@async_test
async def test_captured_cohort_target_judges_markets_against_one_t0(
    tmp_path: Path,
) -> None:
    # A. One captured T0: the clock crosses a closed-5m boundary mid-round yet
    # markets that reached the original target are not falsely marked stale.
    clock = Clock(seconds=599)
    coins = ("BTC", "ETH", "SOL")
    runtime, authority, markets, _, client = cohort_setup(tmp_path, coins, clock)
    assert runtime._capture_cohort().target_open_ms == 0

    def advance_past_boundary() -> None:
        if len(client.calls) == 1:
            clock.seconds = 700

    client.on_call = advance_past_boundary
    assert await runtime._startup_warmup_barrier(asyncio.Event()) is True

    # Every market was judged against the single captured T0=0 even though the
    # wall clock had already advanced past the next boundary during the round.
    assert [end for _, _, end in client.calls[:3]] == [300_000, 300_000, 300_000]
    assert runtime.health.failed_markets == set()
    for item in markets:
        assert not authority.market_failed(item.identity.market_id)
        assert runtime._history_current(item) is True
        assert authority.store.last_open(item.identity.market_id) == 300_000


@async_test
async def test_target_aware_currentness_does_not_chase_wall_clock(tmp_path: Path) -> None:
    # Repair 2 semantics: currentness at a captured target is exact equality,
    # independent of the later wall clock the old check recomputed.
    clock = Clock(seconds=599)
    runtime, authority, markets, _, _ = cohort_setup(tmp_path, ("BTC",), clock)
    item = markets[0]
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    clock.seconds = 700
    assert runtime._history_current_at(item, 0) is True
    assert runtime._history_current_at(item, 300_000) is False
    assert runtime._history_current(item) is False  # wall clock now points to 300_000


@async_test
async def test_bounded_cohort_catchup_moves_whole_cohort_to_t1(tmp_path: Path) -> None:
    # B. After all markets reach T0, the clock reports T1 and the runtime runs
    # exactly one whole-cohort catch-up round ending at T1 for every market.
    clock = Clock(seconds=599)
    coins = ("BTC", "ETH", "SOL")
    runtime, authority, markets, _, client = cohort_setup(tmp_path, coins, clock)

    def advance_past_boundary() -> None:
        if len(client.calls) == 1:
            clock.seconds = 700

    client.on_call = advance_past_boundary
    assert await runtime._startup_warmup_barrier(asyncio.Event()) is True
    assert len(client.calls) == len(coins) * 2  # initial round plus one catch-up round
    assert [end for _, _, end in client.calls[3:]] == [600_000, 600_000, 600_000]
    assert runtime.health.failed_markets == set()
    for item in markets:
        assert authority.store.last_open(item.identity.market_id) == 300_000
        assert runtime._history_current_at(item, 300_000) is True


@async_test
async def test_outrun_catchup_bound_fails_closed_without_websocket(tmp_path: Path) -> None:
    # B (fail-closed). A target that keeps advancing faster than the bounded
    # catch-up must fail closed instead of opening a mixed-time cohort.
    clock = Clock(seconds=600)
    coins = ("BTC", "ETH")
    runtime, _, _, _, client = cohort_setup(tmp_path, coins, clock)

    def advance_every_fetch() -> None:
        clock.seconds += 300

    client.on_call = advance_every_fetch
    factory_calls: list[str] = []

    async def factory(url: str) -> object:
        factory_calls.append(url)
        raise AssertionError("websocket must not open on a mixed-time cohort")

    runtime.websocket_factory = factory
    await runtime.run(asyncio.Event())
    assert len(client.calls) == len(coins) * (1 + WARMUP_CATCHUP_ROUNDS_MAX)
    assert factory_calls == []
    assert runtime.health.subscriptions == 0
    assert runtime.health.failed_markets == set()
    # The fail-closed return released the process-local barrier lock: no
    # global authority remains in flight after the failed startup.
    assert runtime._barrier_lock.locked() is False


@async_test
async def test_all_market_barrier_holds_websocket_until_full_cohort(
    tmp_path: Path,
) -> None:
    # C. 40 unique markets: no WebSocket factory call and no subscription until
    # every selected market reaches the exact common current boundary.
    coins = tuple(f"C{index}" for index in range(40))
    clock = Clock(seconds=600)
    runtime, authority, markets, _, _ = cohort_setup(tmp_path, coins, clock)
    assert runtime.registry.active() is None
    shutdown = asyncio.Event()
    socket = CohortSocket(coins, shutdown)
    factory_states: list[tuple[tuple[int, ...], tuple[str, ...]]] = []

    async def factory(_: str) -> CohortSocket:
        factory_states.append(
            (
                tuple(
                    authority.store.last_open(item.identity.market_id) for item in markets
                ),
                tuple(sorted(runtime.health.failed_markets)),
            )
        )
        return socket

    runtime.websocket_factory = factory
    await runtime.run(shutdown)

    assert len(factory_states) == 1
    boundaries, failed = factory_states[0]
    assert boundaries == (300_000,) * len(coins)
    assert failed == ()
    assert runtime.health.subscriptions == len(coins)
    assert len(socket.sent) == len(coins)
    assert runtime.health.acknowledgements == set(coins)
    assert socket.closed is True
    active = runtime.registry.active()
    assert active is not None and active.version == "seed"


@async_test
async def test_single_provider_failure_keeps_partial_cohort_fail_closed(
    tmp_path: Path,
) -> None:
    # D. One genuine market/provider failure prevents the partial cohort from
    # becoming live-ready; startup does not silently continue to WebSocket.
    clock = Clock(seconds=600)
    coins = ("BTC", "ETH", "SOL")
    runtime, authority, markets, _, client = cohort_setup(tmp_path, coins, clock)
    client.fail_coins = frozenset({"SOL"})
    factory_calls: list[str] = []

    async def factory(url: str) -> object:
        factory_calls.append(url)
        raise AssertionError("websocket must not open after a genuine market failure")

    runtime.websocket_factory = factory
    await runtime.run(asyncio.Event())

    assert factory_calls == []
    assert runtime.health.subscriptions == 0
    assert runtime.health.data_ready is False
    assert runtime.health.failed_markets == {markets[2].identity.market_id}
    assert authority.store.bars(markets[2].identity.market_id) == ()
    for item in markets[:2]:
        assert authority.store.last_open(item.identity.market_id) == 300_000
    # The fail-closed return released the process-local barrier lock: no
    # global authority remains in flight after the failed startup.
    assert runtime._barrier_lock.locked() is False


def large_history_fixture(bars: int) -> list[object]:
    return [candle("BTC", index * 300_000) for index in range(bars)]


@async_test
async def test_large_history_admission_is_chunked_with_cooperative_yields(
    tmp_path: Path,
) -> None:
    # E + F. A full ~2304-candle cold history is admitted in bounded chunks,
    # and the injected sleep seam proves deterministic zero-delay cooperative
    # yields between chunks (no wall-clock microbenchmark).
    bars = 2_304
    clock = Clock(seconds=(bars * 300_000) // 1000 + 3)
    target_open_ms = (bars - 1) * 300_000
    client = Client([large_history_fixture(bars)])
    runtime, authority, markets, _, _ = cohort_setup(
        tmp_path, ("BTC",), clock, client=client, spy=True
    )
    assert isinstance(authority, RecordingAuthority)
    expected_chunks = -(-bars // WARMUP_ADMISSION_CHUNK_BARS)

    count = await runtime._warmup_market(
        markets[0], recovery=False, target_open_ms=target_open_ms
    )

    assert count == bars
    assert authority.admission_sizes == [WARMUP_ADMISSION_CHUNK_BARS] * expected_chunks
    assert max(authority.admission_sizes) == WARMUP_ADMISSION_CHUNK_BARS
    assert len(authority.store.bars(markets[0].identity.market_id)) == bars
    assert authority.store.last_open(markets[0].identity.market_id) == target_open_ms
    assert clock.sleep_seconds.count(0) == expected_chunks
    assert runtime._history_current_at(markets[0], target_open_ms) is True


@async_test
async def test_shutdown_during_large_admission_stops_at_bounded_chunk_boundary(
    tmp_path: Path,
) -> None:
    # G. Shutdown set during cold-history admission finishes the current chunk,
    # skips the remaining bars, never opens WebSocket, and run() returns
    # normally through the finality-closing cleanup path without TimeoutError.
    bars = 2_304
    clock = Clock(seconds=(bars * 300_000) // 1000 + 3)
    target_open_ms = (bars - 1) * 300_000
    client = Client([large_history_fixture(bars)])
    runtime, authority, markets, _, _ = cohort_setup(
        tmp_path, ("BTC",), clock, client=client, spy=True
    )
    assert isinstance(authority, RecordingAuthority)
    shutdown = asyncio.Event()
    authority.on_admission = lambda: shutdown.set() if len(authority.admission_sizes) == 2 else None
    factory_calls: list[str] = []

    async def factory(url: str) -> object:
        factory_calls.append(url)
        raise AssertionError("websocket must not open after shutdown during warmup")

    runtime.websocket_factory = factory
    await runtime.run(shutdown)

    admitted = 2 * WARMUP_ADMISSION_CHUNK_BARS
    assert authority.admission_sizes == [
        WARMUP_ADMISSION_CHUNK_BARS,
        WARMUP_ADMISSION_CHUNK_BARS,
    ]
    assert len(authority.store.bars(markets[0].identity.market_id)) == admitted
    assert authority.store.last_open(markets[0].identity.market_id) == (
        admitted - 1
    ) * 300_000
    assert authority.store.last_open(markets[0].identity.market_id) != target_open_ms
    assert factory_calls == []
    assert runtime.health.subscriptions == 0
    assert runtime.health.data_ready is False
    assert runtime.health.failed_markets == set()  # clean shutdown is not a market failure
    # The fail-closed return released the process-local barrier lock: no
    # global authority remains in flight after the failed startup.
    assert runtime._barrier_lock.locked() is False


@async_test
async def test_shutdown_during_warmup_skips_remaining_markets(tmp_path: Path) -> None:
    # G (cohort view). Shutdown during the first market's admission stops the
    # round before any further market fetch or WebSocket activity.
    clock = Clock(seconds=600)
    coins = ("BTC", "ETH", "SOL")
    runtime, authority, _, _, client = cohort_setup(tmp_path, coins, clock, spy=True)
    assert isinstance(authority, RecordingAuthority)
    shutdown = asyncio.Event()
    authority.on_admission = shutdown.set
    factory_calls: list[str] = []

    async def factory(url: str) -> object:
        factory_calls.append(url)
        raise AssertionError("websocket must not open after shutdown during warmup")

    runtime.websocket_factory = factory
    await runtime.run(shutdown)

    assert [coin for coin, _, _ in client.calls] == ["BTC"]
    assert factory_calls == []
    assert runtime.health.subscriptions == 0
    assert runtime.health.failed_markets == set()
    # The fail-closed return released the process-local barrier lock: no
    # global authority remains in flight after the failed startup.
    assert runtime._barrier_lock.locked() is False


@async_test
async def test_trading_freshness_target_metric_and_hard_action_ceiling(
    tmp_path: Path,
) -> None:
    # H. Boundary age <=30s is inside the operational target, 30s..60s stays
    # potentially actionable but outside target, and >60s must not expose any
    # market as ready for NEW actionable activity. observed_at_ms keeps
    # affecting RuntimeReadinessSnapshot.snapshot_hash exactly as before.
    runtime, authority, item, clock, _ = setup(tmp_path, lifecycle=MarketLifecycle.ACTIVE)
    runtime.health.data_ready = True
    authority.admit_rest_history(market=item, snapshot=[candle("BTC", 0)], received_at=clock.now())

    clock.seconds = 310
    fresh = runtime.readiness_snapshot()
    assert runtime.freshness_lag_seconds(fresh) == 10.0
    assert runtime.freshness_within_target(fresh) is True
    assert runtime.actionable_ready_market_ids() == (item.identity.market_id,)
    assert fresh.ready_market_ids == (item.identity.market_id,)

    clock.seconds = 345
    slow = runtime.readiness_snapshot()
    assert runtime.freshness_lag_seconds(slow) == 45.0
    assert runtime.freshness_within_target(slow) is False
    assert runtime.actionable_ready_market_ids() == (item.identity.market_id,)
    assert slow.ready_market_ids == (item.identity.market_id,)

    clock.seconds = 361
    stale = runtime.readiness_snapshot()
    assert runtime.freshness_lag_seconds(stale) == 61.0
    assert runtime.freshness_within_target(stale) is False
    assert runtime.actionable_ready_market_ids() == ()
    # The hard freshness gate is on the production path itself: the
    # RuntimeReadinessSnapshot seen by production gates must exclude a market
    # whose latest authoritative boundary is older than the action ceiling.
    assert stale.ready_market_ids == ()
    assert stale.observed_at_ms == 361_000

    assert fresh.snapshot_hash != slow.snapshot_hash != stale.snapshot_hash
    rebuilt = RuntimeReadinessSnapshot.create(
        registry_version=stale.registry_version,
        registry_content_hash=stale.registry_content_hash,
        data_ready=stale.data_ready,
        ready_market_ids=stale.ready_market_ids,
        failed_market_ids=stale.failed_market_ids,
        latest_closed_5m_open_time_ms=stale.latest_closed_5m_open_time_ms,
        observed_at_ms=stale.observed_at_ms,
    )
    assert rebuilt.snapshot_hash == stale.snapshot_hash


@async_test
async def test_startup_barrier_activates_pending_registry_through_admission_only(
    tmp_path: Path,
) -> None:
    # I. Initial pending Registry startup stays deterministic: active=None and
    # a validated pending version warm through the provider admission seam.
    clock = Clock(seconds=600)
    coins = ("BTC", "ETH", "SOL")
    runtime, _, markets, _, _ = cohort_setup(tmp_path, coins, clock)
    assert runtime.registry.active() is None
    assert runtime.registry.pending_version() is not None
    shutdown = asyncio.Event()
    socket = CohortSocket(coins, shutdown)

    async def factory(_: str) -> CohortSocket:
        return socket

    runtime.websocket_factory = factory
    await runtime.run(shutdown)

    active = runtime.registry.active()
    assert active is not None and active.version == "seed"
    active_ids = {entry.identity.market_id for entry in active.markets}
    assert all(item.identity.market_id in active_ids for item in markets)
    assert all(runtime._history_current(item) for item in markets)
    assert runtime.health.failed_markets == set()


@async_test
async def test_run_regression_startup_warmup_and_shutdown_paths_stay_green(
    tmp_path: Path,
) -> None:
    # J. The repaired startup path still produces the original deterministic
    # cold-start behavior: runtime-owned warmup and acknowledgement.  In the
    # single-owner architecture startup owns no application wake; only the
    # cohort barrier wakes global action.
    clock = Clock(seconds=600)
    client = Client([[candle("BTC", 300_000)]])
    runtime, _, _, _, _ = cohort_setup(tmp_path, ("BTC",), clock, client=client)
    shutdown = asyncio.Event()
    socket = Socket([ack()], shutdown=shutdown)
    callbacks: list[tuple[int, BoundaryMode]] = []

    async def factory(_: str) -> Socket:
        return socket

    runtime.websocket_factory = factory
    runtime.on_finalized_5m = lambda bar, mode: callbacks.append((bar.open_time_ms, mode))
    await runtime.run(shutdown)
    assert runtime.health.acknowledgements == {"BTC"}
    assert socket.closed
    assert callbacks == []


# ---------------------------------------------------------------------------
# Integrated acceptance: one cohort target per round, canonical equivalence,
# global ordering, and observed_at hash strictness.
# ---------------------------------------------------------------------------


class BoundaryAdvancingClock(Clock):
    """Adversarial clock: crosses a 5m boundary on the second now() call."""

    def __init__(self, *, start: int = 599, advance_to: int = 700) -> None:
        super().__init__(seconds=start)
        self._advance_to = advance_to
        self._now_calls = 0

    def now(self) -> datetime:
        self._now_calls += 1
        if self._now_calls == 2:
            self.seconds = self._advance_to
        return datetime.fromtimestamp(self.seconds, UTC)


def _assert_persisted_bars_equal(
    ref_bars: tuple[object, ...], rt_bars: tuple[object, ...], interval: str
) -> None:
    assert len(ref_bars) == len(rt_bars), f"{interval}: {len(ref_bars)} != {len(rt_bars)}"
    for ref_bar, rt_bar in zip(ref_bars, rt_bars, strict=True):
        assert ref_bar.canonical_hash == rt_bar.canonical_hash, interval
        assert ref_bar.provenance_hash == rt_bar.provenance_hash, interval
        assert ref_bar.received_at == rt_bar.received_at, interval
        assert ref_bar.open == rt_bar.open, interval
        assert ref_bar.high == rt_bar.high, interval
        assert ref_bar.low == rt_bar.low, interval
        assert ref_bar.close == rt_bar.close, interval
        assert ref_bar.volume == rt_bar.volume, interval
        assert ref_bar.open_time_ms == rt_bar.open_time_ms, interval
        assert ref_bar.close_time_ms == rt_bar.close_time_ms, interval


@async_test
async def test_one_cohort_target_per_round_adversarial_clock(tmp_path: Path) -> None:
    # A. A 5m boundary can advance between internal calls without allowing
    # _warmup_all to replace the round target.  One round must use exactly
    # the _WarmupCohort supplied by the barrier.
    clock = BoundaryAdvancingClock(start=599, advance_to=700)
    coins = ("BTC", "ETH", "SOL")
    runtime, authority, markets, _, _ = cohort_setup(tmp_path, coins, clock)
    # cohort_setup consumed one now() call (RegistryVersion.create), so reset
    # the adversarial counter.  Within the barrier, call #1 is _capture_cohort
    # (target=0 at 599s); call #2 is _warmup_market, which must still see the
    # captured target 0 even though the clock has advanced to 700s.
    clock._now_calls = 0

    warmup_targets: list[int] = []
    original_warmup_market = runtime._warmup_market

    async def spy_warmup_market(
        market: RegistryMarket,
        *,
        recovery: bool,
        target_open_ms: int,
        shutdown: asyncio.Event | None = None,
    ) -> int:
        warmup_targets.append(target_open_ms)
        return await original_warmup_market(
            market,
            recovery=recovery,
            target_open_ms=target_open_ms,
            shutdown=shutdown,
        )

    runtime._warmup_market = spy_warmup_market  # type: ignore[assignment]

    assert await runtime._startup_warmup_barrier(asyncio.Event()) is True

    # Round 1 used the barrier's captured target (0), not a re-captured target
    # (300_000) that a wall-clock advance between captures would produce.
    assert warmup_targets[: len(coins)] == [0] * len(coins)
    for item in markets:
        assert authority.store.last_open(item.identity.market_id) == 300_000
    assert runtime.health.failed_markets == set()


@async_test
async def test_chunked_admission_canonical_equivalence(tmp_path: Path) -> None:
    # B. Every source 5m bar from the Runtime chunked path has the same
    # received_at, canonical_hash, provenance_hash, and OHLCV as the one-shot
    # reference.  Every persisted 15m/1h aggregate is also identical.
    bars = 200
    received_at = datetime.fromtimestamp(10_000_000, UTC)
    snapshot: list[object] = [candle("BTC", index * 300_000) for index in range(bars)]

    _, ref_authority, ref_item, _, _ = setup(tmp_path / "ref")
    ref_authority.admit_rest_history(
        market=ref_item, snapshot=snapshot, received_at=received_at
    )

    clock = Clock(seconds=10_000)
    rt_runtime, rt_authority, rt_item, _, _ = setup(tmp_path / "rt", clock=clock)
    count = await rt_runtime._admit_history_chunked(
        rt_item, snapshot, received_at=received_at, shutdown=None
    )
    assert count == bars

    for interval in ("5m", "15m", "1h"):
        _assert_persisted_bars_equal(
            ref_authority.store.bars(ref_item.identity.market_id, interval=interval),
            rt_authority.store.bars(rt_item.identity.market_id, interval=interval),
            interval,
        )


@async_test
async def test_global_out_of_order_snapshot_chunked_equivalence(tmp_path: Path) -> None:
    # C. A provider snapshot deliberately reversed across chunk boundaries
    # produces identical 5m/15m/1h durable evidence via the Runtime chunked
    # path and the one-shot Data reference.  No gap false-positive results
    # merely from provider list ordering.
    bars = 200
    received_at = datetime.fromtimestamp(10_000_000, UTC)
    ordered: list[object] = [candle("BTC", index * 300_000) for index in range(bars)]
    reversed_snapshot: list[object] = list(reversed(ordered))

    _, ref_authority, ref_item, _, _ = setup(tmp_path / "ref")
    ref_authority.admit_rest_history(
        market=ref_item, snapshot=reversed_snapshot, received_at=received_at
    )

    clock = Clock(seconds=10_000)
    rt_runtime, rt_authority, rt_item, _, _ = setup(tmp_path / "rt", clock=clock)
    count = await rt_runtime._admit_history_chunked(
        rt_item, reversed_snapshot, received_at=received_at, shutdown=None
    )
    assert count == bars

    for interval in ("5m", "15m", "1h"):
        _assert_persisted_bars_equal(
            ref_authority.store.bars(ref_item.identity.market_id, interval=interval),
            rt_authority.store.bars(rt_item.identity.market_id, interval=interval),
            interval,
        )


def test_observed_at_ms_strictly_affects_snapshot_hash(tmp_path: Path) -> None:
    # E. Otherwise identical readiness observations with different observed_at_ms
    # must produce different snapshot_hash.  observed_at_ms remains in snapshot
    # hash identity; runtime_readiness_hash authority is not weakened.
    runtime, authority, item, clock, _ = setup(tmp_path, lifecycle=MarketLifecycle.ACTIVE)
    runtime.health.data_ready = True
    authority.admit_rest_history(market=item, snapshot=[candle("BTC", 0)], received_at=clock.now())

    clock.seconds = 310
    a = runtime.readiness_snapshot()
    clock.seconds = 311
    b = runtime.readiness_snapshot()

    assert a.observed_at_ms == 310_000
    assert b.observed_at_ms == 311_000
    assert a.registry_version == b.registry_version
    assert a.ready_market_ids == b.ready_market_ids
    assert a.failed_market_ids == b.failed_market_ids
    assert a.latest_closed_5m_open_time_ms == b.latest_closed_5m_open_time_ms
    # Only observed_at_ms differs, yet snapshot_hash must differ.
    assert a.snapshot_hash != b.snapshot_hash
