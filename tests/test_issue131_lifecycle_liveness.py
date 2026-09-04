"""Issue #131 bounded lifecycle-key and runtime-liveness acceptance."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
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
from trader_assist_v0.multi_asset_shadow.production import (
    ThreeSetupProductionApplication,
)
from trader_assist_v0.multi_asset_shadow.registry import (
    MarketRegistryManager,
    RegistryError,
)
from trader_assist_v0.multi_asset_shadow.resolution import (
    INITIAL_40,
    resolve_first_launch_20,
)
from trader_assist_v0.multi_asset_shadow.runtime import (
    BoundaryMode,
    MultiAssetPublicRuntime,
)

FIVE_MINUTES_MS = 300_000
T0 = 100 * FIVE_MINUTES_MS
NOW = datetime(2026, 8, 29, 9, 0, tzinfo=UTC)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def market(
    coin: str = "BTC", *, lifecycle: MarketLifecycle = MarketLifecycle.WARMING
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
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(coin.encode()),
    )


def candle(coin: str, open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + FIVE_MINUTES_MS - 1,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "1",
    }


def active_one(
    tmp_path: Path,
    *,
    version: str,
    lifecycle: MarketLifecycle = MarketLifecycle.WARMING,
) -> tuple[MarketRegistryManager, MultiAssetDataAuthority, RegistryVersion]:
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    initial = RegistryVersion.create(
        version=version, created_at=NOW, markets=(market(lifecycle=lifecycle),)
    )
    registry.stage(initial)
    registry.request_apply(initial.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    authority.admit_rest_history(
        market=initial.markets[0],
        snapshot=[candle("BTC", 0)],
        received_at=datetime.fromtimestamp(303, UTC),
    )
    active = registry.active()
    assert active is not None
    return registry, authority, active


def test_bounded_automatic_key_breaks_recursive_parent_growth(tmp_path: Path) -> None:
    realistic_parent = "g12-" + "x" * 39
    max_parent = "m" * 80
    assert len(realistic_parent) == 43 and len(max_parent) == 80
    first_old = f"{realistic_parent}-lifecycle-history_ready"
    assert len(f"{first_old}-lifecycle-snapshot_ready") > 80
    assert len(f"{max_parent}-lifecycle-history_ready") > 80

    for index, parent in enumerate((realistic_parent, max_parent)):
        registry, authority, active = active_one(tmp_path / str(index), version=parent)
        candidate = registry.ensure_lifecycle_successor(
            updates={active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY},
            now=NOW,
        )
        assert len(candidate.version) == 74
        assert re.fullmatch(r"lifecycle-[0-9a-f]{64}", candidate.version)
        authority.store.close()


def test_automatic_candidate_reuse_after_restart_preserves_identity(
    tmp_path: Path,
) -> None:
    registry, authority, active = active_one(tmp_path, version="base")
    updates = {active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY}
    first = registry.ensure_lifecycle_successor(updates=updates, now=NOW)
    registry._validation_path(first.version).unlink()

    def unavailable_metadata(_: RegistryMarket) -> bool:
        raise ConnectionError("metadata provider unavailable")

    restarted = MarketRegistryManager(
        registry.root, metadata_validator=unavailable_metadata
    )
    reused = restarted.ensure_lifecycle_successor(
        updates=updates, now=NOW + timedelta(days=1)
    )
    assert reused.version == first.version
    assert reused.created_at == first.created_at
    assert reused.content_hash == first.content_hash
    restarted._assert_prior_validation(reused)
    authority.store.close()


def test_automatic_lifecycle_successor_uses_validated_active_parent_offline(
    tmp_path: Path,
) -> None:
    provider_available = True
    provider_calls = 0

    def metadata_validator(_: RegistryMarket) -> bool:
        nonlocal provider_calls
        provider_calls += 1
        if not provider_available:
            raise ConnectionError("metadata provider unavailable")
        return True

    registry = MarketRegistryManager(
        tmp_path / "registry", metadata_validator=metadata_validator
    )
    initial = RegistryVersion.create(
        version="base", created_at=NOW, markets=(market(),)
    )
    registry.stage(initial)
    registry.request_apply(initial.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    authority.admit_rest_history(
        market=initial.markets[0],
        snapshot=[candle("BTC", 0)],
        received_at=datetime.fromtimestamp(303, UTC),
    )
    active = registry.active()
    assert active is not None
    initial_provider_calls = provider_calls
    provider_available = False

    successor = registry.ensure_lifecycle_successor(
        updates={
            active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY
        },
        now=NOW,
    )

    assert successor.markets[0].lifecycle is MarketLifecycle.HISTORY_READY
    assert provider_calls == initial_provider_calls
    assert json.loads(
        registry._validation_path(successor.version).read_text(encoding="utf-8")
    ) == {"version": successor.version, "content_hash": successor.content_hash}
    authority.store.close()


def test_automatic_lifecycle_successor_rejects_illegal_or_unknown_offline(
    tmp_path: Path,
) -> None:
    registry, authority, active = active_one(tmp_path, version="base")

    def unavailable_metadata(_: RegistryMarket) -> bool:
        raise ConnectionError("metadata provider unavailable")

    offline = MarketRegistryManager(
        registry.root, metadata_validator=unavailable_metadata
    )
    with pytest.raises(RegistryError, match="illegal market lifecycle transition"):
        offline.ensure_lifecycle_successor(
            updates={active.markets[0].identity.market_id: MarketLifecycle.ACTIVE},
            now=NOW,
        )
    with pytest.raises(RegistryError, match="market is not in active registry"):
        offline.ensure_lifecycle_successor(
            updates={"0" * 64: MarketLifecycle.HISTORY_READY},
            now=NOW,
        )
    assert {path.stem for path in offline.versions.glob("*.json")} == {"base"}
    assert not offline.pending.exists()
    authority.store.close()


@pytest.mark.parametrize("attack", ["malformed", "conflicting"])
def test_same_key_malformed_or_conflicting_candidate_fails_closed(
    tmp_path: Path, attack: str
) -> None:
    registry, authority, active = active_one(tmp_path, version="base")
    updates = {active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY}
    expected = registry.ensure_lifecycle_successor(updates=updates, now=NOW)
    target = registry.versions / f"{expected.version}.json"
    if attack == "malformed":
        target.write_bytes(b"not-json")
    else:
        conflicting = RegistryVersion.create(
            version=expected.version,
            created_at=NOW,
            markets=active.markets,
        )
        target.write_bytes(canonical_json_bytes(conflicting.model_dump(mode="json")))
    with pytest.raises(RegistryError):
        registry.ensure_lifecycle_successor(updates=updates, now=NOW + timedelta(days=1))
    authority.store.close()


def test_same_key_non_lifecycle_tampering_fails_closed_offline(tmp_path: Path) -> None:
    registry, authority, active = active_one(tmp_path, version="base")
    updates = {active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY}
    target_markets = registry._lifecycle_target_markets(active, updates)
    deterministic_version = registry._automatic_lifecycle_version(
        active=active, target_markets=target_markets
    )
    tampered_market = target_markets[0].model_copy(
        update={"metadata_hash": "0" * 64}
    )
    tampered = RegistryVersion.create(
        version=deterministic_version,
        created_at=NOW,
        markets=(tampered_market,),
    )
    target = registry.versions / f"{deterministic_version}.json"
    target.write_bytes(canonical_json_bytes(tampered.model_dump(mode="json")))

    def unavailable_metadata(_: RegistryMarket) -> bool:
        raise ConnectionError("metadata provider unavailable")

    restarted = MarketRegistryManager(
        registry.root, metadata_validator=unavailable_metadata
    )
    with pytest.raises(RegistryError, match="non-lifecycle metadata"):
        restarted.ensure_lifecycle_successor(
            updates=updates, now=NOW + timedelta(days=1)
        )
    assert not restarted._validation_path(deterministic_version).exists()
    assert not restarted.pending.exists()
    assert restarted.active() == active
    authority.store.close()


def test_same_key_alternate_internal_version_fails_closed_without_side_effects(
    tmp_path: Path,
) -> None:
    registry, authority, active = active_one(tmp_path, version="base")
    updates = {active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY}
    target_markets = registry._lifecycle_target_markets(active, updates)
    deterministic_version = registry._automatic_lifecycle_version(
        active=active, target_markets=target_markets
    )
    alternate = RegistryVersion.create(
        version="alternate-legal-version",
        created_at=NOW + timedelta(hours=1),
        markets=target_markets,
    )
    target = registry.versions / f"{deterministic_version}.json"
    target.write_bytes(canonical_json_bytes(alternate.model_dump(mode="json")))
    current_before = registry.pointer.read_bytes()

    with pytest.raises(RegistryError, match="does not match deterministic key"):
        registry.ensure_lifecycle_successor(updates=updates, now=NOW + timedelta(days=1))

    assert not (registry.versions / f"{alternate.version}.json").exists()
    assert not registry._validation_path(alternate.version).exists()
    assert not registry.pending.exists()
    assert registry.pointer.read_bytes() == current_before
    assert registry.active() == active
    authority.store.close()


@async_test
async def test_old_explicit_pending_successor_remains_usable_without_migration(
    tmp_path: Path,
) -> None:
    registry, authority, active = active_one(tmp_path, version="old-active")
    market_id = active.markets[0].identity.market_id
    old = registry.lifecycle_successor(
        version="old-active-lifecycle-history_ready",
        updates={market_id: MarketLifecycle.HISTORY_READY},
        now=NOW,
    )
    registry.request_apply(old.version)
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=SimpleNamespace(),  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp(303, UTC),
        monotonic=lambda: 0.0,
        sleep=asyncio.sleep,
    )
    await runtime.process_cohort_boundary(0)
    applied = registry.active()
    assert applied is not None and applied.version == old.version
    assert applied.markets[0].lifecycle is MarketLifecycle.HISTORY_READY
    assert (registry.versions / "old-active.json").exists()
    authority.store.close()


def test_manager_normalizes_candidate_schema_failure(tmp_path: Path) -> None:
    registry, authority, active = active_one(tmp_path, version="base")
    with pytest.raises(RegistryError, match="candidate schema"):
        registry.lifecycle_successor(
            version="x" * 81,
            updates={
                active.markets[0].identity.market_id: MarketLifecycle.HISTORY_READY
            },
            now=NOW,
        )
    authority.store.close()


def _apply_pending(
    registry: MarketRegistryManager,
    authority: MultiAssetDataAuthority,
    *,
    base: RegistryVersion,
    successor: RegistryVersion,
    boundary: int,
) -> None:
    witness = registry._issue_cohort_witness(
        boundary_open_time_ms=boundary,
        base_registry_version=base.version,
        base_registry_hash=base.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset(
            item.identity.market_id for item in base.markets
        ),
    )
    registry.apply_witness(witness, evidence_authority=authority)


def test_ws_identity_is_only_sorted_exact_provider_projection(tmp_path: Path) -> None:
    items = (
        market("ETH", lifecycle=MarketLifecycle.ACTIVE),
        market("BTC", lifecycle=MarketLifecycle.ACTIVE),
    )
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    base = RegistryVersion.create(version="base", created_at=NOW, markets=items)
    registry.stage(base)
    registry.request_apply(base.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    for item in items:
        authority.admit_rest_history(
            market=item,
            snapshot=[candle(item.identity.coin, 0)],
            received_at=datetime.fromtimestamp(303, UTC),
        )
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=SimpleNamespace(),  # type: ignore[arg-type]
    )
    expected = (("candle", "BTC", "5m"), ("candle", "ETH", "5m"))
    assert runtime._current_subscription_identity() == expected

    lifecycle = registry.lifecycle_successor(
        version="lifecycle-only",
        updates={item.identity.market_id: MarketLifecycle.DRAINING for item in items},
        now=NOW,
    )
    registry.request_apply(lifecycle.version)
    _apply_pending(registry, authority, base=base, successor=lifecycle, boundary=0)
    assert runtime._current_subscription_identity() == expected

    for item in lifecycle.markets:
        authority.admit_rest_history(
            market=item,
            snapshot=[candle(item.identity.coin, FIVE_MINUTES_MS)],
            received_at=datetime.fromtimestamp(603, UTC),
        )
    reordered = RegistryVersion.create(
        version="order-only", created_at=NOW, markets=tuple(reversed(lifecycle.markets))
    )
    registry.stage(reordered)
    registry.request_apply(reordered.version)
    _apply_pending(
        registry,
        authority,
        base=lifecycle,
        successor=reordered,
        boundary=FIVE_MINUTES_MS,
    )
    assert runtime._current_subscription_identity() == expected

    for item in reordered.markets:
        authority.admit_rest_history(
            market=item,
            snapshot=[candle(item.identity.coin, 2 * FIVE_MINUTES_MS)],
            received_at=datetime.fromtimestamp(903, UTC),
        )
    removed = registry.successor(
        version="remove-eth",
        now=NOW,
        remove_market_id=items[0].identity.market_id,
    )
    registry.request_apply(removed.version)
    _apply_pending(
        registry,
        authority,
        base=reordered,
        successor=removed,
        boundary=2 * FIVE_MINUTES_MS,
    )
    assert runtime._current_subscription_identity() == (("candle", "BTC", "5m"),)
    authority.store.close()


def _first_launch_markets() -> tuple[RegistryMarket, ...]:
    native: list[object] = []
    hip3: list[object] = []
    for request in INITIAL_40:
        raw = {"name": request.coin, "szDecimals": 2, "maxLeverage": 10}
        (native if request.dex == "MAIN" else hip3).append(raw)
    resolved = resolve_first_launch_20(
        perp_dexes=[{"name": "main"}, {"name": "xyz"}],
        all_perp_metas=[{"universe": native}, {"universe": hip3}],
        observed_at=NOW,
    )
    assert all(item.status == "RESOLVED" and item.market is not None for item in resolved)
    return tuple(
        item.market.model_copy(update={"lifecycle": MarketLifecycle.WARMING})
        for item in resolved
        if item.market is not None
    )


class ColdClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(
        self, *, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        if end_ms - start_ms == FIVE_MINUTES_MS:
            return [candle(coin, start_ms)]
        return [candle(coin, end_ms - FIVE_MINUTES_MS)]


class ControlledClock:
    def __init__(self) -> None:
        self.value_ms = T0 + FIVE_MINUTES_MS + 5_000
        self.monotonic_value = 0.0
        self.tick_waits = 0
        self.ticks: asyncio.Queue[tuple[int, float]] = asyncio.Queue()

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.value_ms / 1000, UTC)

    def monotonic(self) -> float:
        return self.monotonic_value

    async def sleep(self, seconds: float) -> None:
        if seconds == 0:
            await asyncio.sleep(0)
            return
        if seconds == 5.0:
            self.tick_waits += 1
            self.value_ms, self.monotonic_value = await self.ticks.get()
            return
        self.monotonic_value += seconds
        await asyncio.sleep(0)

    def release(self, boundary: int, monotonic_value: float) -> None:
        self.ticks.put_nowait(
            (boundary + FIVE_MINUTES_MS + 5_000, monotonic_value)
        )


class AckFromOutboundSocket:
    def __init__(self) -> None:
        self.frames: asyncio.Queue[str] = asyncio.Queue()
        self.sent: list[str] = []
        self.acknowledged_outbound: list[str] = []
        self.closed = False
        self.recv_owners: set[asyncio.Task[Any]] = set()

    async def send(self, raw: str) -> None:
        self.sent.append(raw)
        decoded = json.loads(raw)
        if decoded.get("method") == "subscribe":
            self.acknowledged_outbound.append(raw)
            self.frames.put_nowait(
                json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": decoded,
                    }
                )
            )

    async def recv(self) -> str:
        owner = asyncio.current_task()
        assert owner is not None
        self.recv_owners.add(owner)
        return await self.frames.get()

    async def close(self) -> None:
        self.closed = True


async def wait_until(predicate: Any, *, timeout: float = 10.0) -> None:
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.001)


@async_test
async def test_real_cold_first_launch_20_run_reaches_active_then_one_live_callback(
    tmp_path: Path,
) -> None:
    markets = _first_launch_markets()
    assert len(markets) == 20
    assert all(item.lifecycle is MarketLifecycle.WARMING for item in markets)
    metadata_available = True
    metadata_calls = 0

    def metadata_validator(_: RegistryMarket) -> bool:
        nonlocal metadata_calls
        metadata_calls += 1
        if not metadata_available:
            raise ConnectionError("metadata provider unavailable")
        return True

    registry = MarketRegistryManager(
        tmp_path / "registry", metadata_validator=metadata_validator
    )
    seed = RegistryVersion.create(
        version="first-launch-20-cold", created_at=NOW, markets=markets
    )
    registry.stage(seed)
    registry.request_apply(seed.version)
    initial_metadata_calls = metadata_calls
    metadata_available = False
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    client = ColdClient()
    clock = ControlledClock()
    socket = AckFromOutboundSocket()
    callbacks: list[tuple[int, BoundaryMode]] = []

    async def factory(_: str) -> AckFromOutboundSocket:
        return socket

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        callbacks.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        websocket_factory=factory,
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        on_finalized_5m=on_finalized,
        heartbeat_interval_seconds=3_600,
    )
    shutdown = asyncio.Event()
    task = asyncio.create_task(runtime.run(shutdown))
    await wait_until(lambda: runtime.health.data_ready and len(socket.sent) == 20)
    active = registry.active()
    assert active is not None
    assert all(item.lifecycle is MarketLifecycle.WARMING for item in active.markets)
    assert socket.acknowledged_outbound == socket.sent
    assert len(socket.recv_owners) == 1

    expected_states = (
        MarketLifecycle.HISTORY_READY,
        MarketLifecycle.SNAPSHOT_READY,
        MarketLifecycle.ACTIVE,
    )
    automatic_versions: list[str] = []

    async def wait_lifecycle(expected: MarketLifecycle) -> None:
        async with asyncio.timeout(10):
            while True:
                if task.done():
                    await task
                    raise AssertionError("runtime returned before lifecycle convergence")
                current = registry.active()
                if current is not None and all(
                    item.lifecycle is expected for item in current.markets
                ):
                    return
                await asyncio.sleep(0.001)

    for index, expected in enumerate(expected_states):
        await wait_until(lambda expected_wait=index + 1: clock.tick_waits >= expected_wait)
        boundary = T0 + index * FIVE_MINUTES_MS
        clock.release(boundary, 60.0 + index * 100.0)
        await wait_lifecycle(expected)
        current = registry.active()
        assert current is not None
        automatic_versions.append(current.version)
        assert callbacks == []

    await wait_until(lambda: clock.tick_waits >= 4)
    live_boundary = T0 + 3 * FIVE_MINUTES_MS
    clock.release(live_boundary, 360.0)
    await wait_until(lambda: len(callbacks) == 1)
    assert callbacks == [(live_boundary, BoundaryMode.LIVE_ACTIONABLE)]
    assert all(
        len(version) == 74 and re.fullmatch(r"lifecycle-[0-9a-f]{64}", version)
        for version in automatic_versions
    )
    assert metadata_calls == initial_metadata_calls
    shutdown.set()
    await task
    assert socket.closed
    assert runtime.health.data_ready is False
    authority.store.close()


class BlockingSocket:
    def __init__(self) -> None:
        self.closed = False

    async def send(self, _: str) -> None:
        return None

    async def recv(self) -> str:
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


class RecordingDispatcher:
    def __init__(self) -> None:
        self.closed = False

    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        return ()

    def close(self) -> None:
        self.closed = True


@async_test
async def test_barrier_registry_error_reaches_production_and_stops_dispatcher(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    registry, authority, _ = active_one(tmp_path, version="active")
    monotonic_calls = 0

    def monotonic() -> float:
        nonlocal monotonic_calls
        monotonic_calls += 1
        return 0.0 if monotonic_calls == 1 else 1_000.0

    socket = BlockingSocket()
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=SimpleNamespace(),  # type: ignore[arg-type]
        websocket_factory=lambda _: asyncio.sleep(0, result=socket),
        clock=lambda: datetime.fromtimestamp(303, UTC),
        monotonic=monotonic,
        sleep=lambda _: asyncio.sleep(0),
    )

    async def startup(_: asyncio.Event) -> bool:
        return True

    injected = RegistryError("injected barrier Registry failure")

    def fail_request(_: str) -> RegistryVersion:
        raise injected

    runtime._startup_warmup_barrier = startup  # type: ignore[method-assign]
    registry.request_apply = fail_request  # type: ignore[method-assign]
    dispatcher = RecordingDispatcher()
    bootstrap = SimpleNamespace(
        runtime=runtime,
        registry=registry,
        coordinator=SimpleNamespace(_release_sha="1" * 40),
        data_authority=authority,
        close=lambda: None,
    )
    application = ThreeSetupProductionApplication(
        bootstrap=bootstrap,  # type: ignore[arg-type]
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp(303, UTC),
        notification_poll_seconds=60,
    )
    shutdown = asyncio.Event()
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(RegistryError, match="injected barrier") as exc_info:
            await application.run(shutdown)
    assert exc_info.value is injected
    assert shutdown.is_set()
    assert dispatcher.closed and socket.closed
    assert runtime._integrity_failed is True
    assert runtime.health.nonrecoverable_markets == {
        (registry.active() or pytest.fail("active Registry missing")).markets[
            0
        ].identity.market_id
    }
    assert runtime.health.callback_failures[-1].error_type == "RegistryError"
    events = [json.loads(record.message) for record in caplog.records]
    assert any(
        event["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
        and event["component"] == "runtime"
        and event["error_type"] == "RegistryError"
        for event in events
    )
    live_names = {
        task.get_name()
        for task in asyncio.all_tasks()
        if task is not asyncio.current_task()
    }
    assert "closed-5m-cohort-barrier-ticker" not in live_names
    assert "hyperliquid-ws-session-loop" not in live_names


@pytest.mark.parametrize("child", ["ticker", "session"])
@async_test
async def test_runtime_rejects_unexpected_critical_child_normal_return(
    tmp_path: Path, child: str
) -> None:
    registry, authority, _ = active_one(tmp_path, version="active")
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=SimpleNamespace(),  # type: ignore[arg-type]
    )

    async def startup(_: asyncio.Event) -> bool:
        return True

    async def returns(_: asyncio.Event) -> None:
        return None

    async def waits(shutdown: asyncio.Event) -> None:
        await shutdown.wait()

    runtime._startup_warmup_barrier = startup  # type: ignore[method-assign]
    runtime._barrier_ticker = returns if child == "ticker" else waits  # type: ignore[method-assign]
    runtime._connection_session_loop = (  # type: ignore[method-assign]
        returns if child == "session" else waits
    )
    with pytest.raises(RuntimeError, match="RUNTIME_CRITICAL_CHILD_EXIT_UNEXPECTED"):
        await runtime.run(asyncio.Event())
    authority.store.close()
