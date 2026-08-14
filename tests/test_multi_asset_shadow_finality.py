"""Adversarial generation/finality tests for the A1 public-data runtime."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
    MultiAssetDataAuthority,
)
from trader_assist_v0.multi_asset_shadow.finality import (
    MIN_MONOTONIC_CONFIRMATION_GAP_MS,
    POST_CLOSE_HOLD_MS,
    TARGET_CONFIRMATIONS,
    ConfirmationResult,
    GenerationFinalityAuthority,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import MultiAssetPublicRuntime


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


class Clock:
    def __init__(self, seconds: float = 303.0, *, advance_monotonic: bool = True) -> None:
        self.seconds = seconds
        self.monotonic_seconds = 0.0
        self.advance_monotonic = advance_monotonic

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.seconds += seconds
        if self.advance_monotonic:
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


def market(coin: str = "BTC") -> RegistryMarket:
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
        lifecycle=MarketLifecycle.WARMING,
        metadata_observed_at=datetime(2026, 8, 12, tzinfo=UTC),
        metadata_hash=sha256_hex(coin.encode()),
    )


class SequenceClient:
    def __init__(
        self,
        values: list[object],
        *,
        blocked_calls: set[int] | None = None,
        after_call: dict[int, Callable[[], None]] | None = None,
    ) -> None:
        self.values = values
        self.blocked_calls = blocked_calls or set()
        self.after_call = after_call or {}
        self.calls: list[tuple[str, int, int]] = []
        self.entered = {index: threading.Event() for index in self.blocked_calls}
        self.release = {index: threading.Event() for index in self.blocked_calls}
        self._lock = threading.Lock()

    def closed_candles(
        self, *, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> object:
        assert interval == "5m"
        with self._lock:
            index = len(self.calls)
            self.calls.append((coin, start_ms, end_ms))
        if index in self.blocked_calls:
            self.entered[index].set()
            if not self.release[index].wait(timeout=5):
                raise TimeoutError("test client was not released")
        value = self.values[min(index, len(self.values) - 1)]
        callback = self.after_call.get(index)
        if callback is not None:
            callback()
        return value


def setup_runtime(
    tmp_path: Path,
    *,
    client: SequenceClient,
    clock: Clock | None = None,
    markets: tuple[RegistryMarket, ...] | None = None,
    confirmation_concurrency: int = 4,
) -> tuple[MultiAssetPublicRuntime, MultiAssetDataAuthority, tuple[RegistryMarket, ...], Clock]:
    clock = clock or Clock()
    selected = markets or (market(),)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version="seed", created_at=clock.now(), markets=selected)
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
    )
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        confirmation_concurrency=confirmation_concurrency,
    )
    return runtime, authority, selected, clock


async def wait_for_thread_event(event: threading.Event) -> None:
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 2), timeout=3)


async def wait_for_finality(runtime: MultiAssetPublicRuntime, market_id: str) -> None:
    task = runtime._finality.task_for(market_id)
    assert task is not None
    await asyncio.wait_for(task, timeout=3)


def ws(payload: dict[str, object]) -> str:
    return json.dumps({"channel": "candle", "data": payload})


@async_test
async def test_a_to_a_coalesces_and_a_to_b_to_c_runs_only_latest_generation() -> None:
    item = market()
    started = asyncio.Event()
    release = asyncio.Event()
    seen: list[str] = []
    discarded: list[int] = []
    failed: set[str] = set()
    coordinator: GenerationFinalityAuthority

    async def confirm(generation):  # type: ignore[no-untyped-def]
        seen.append(generation.fingerprint)
        if generation.sequence == 1:
            started.set()
            await release.wait()
        if not coordinator.is_latest(generation):
            return ConfirmationResult.STALE
        return ConfirmationResult.COMPLETE

    coordinator = GenerationFinalityAuthority(
        confirm=confirm,
        discard=lambda identity: discarded.append(identity.open_time_ms),
        mark_failed=failed.add,
        now_ms=lambda: 303_000,
        sleep=asyncio.sleep,
        confirmation_concurrency=2,
    )
    first = coordinator.offer(market=item, open_time_ms=0, fingerprint="A")
    duplicate = coordinator.offer(market=item, open_time_ms=0, fingerprint="A")
    assert duplicate is first
    await started.wait()
    second = coordinator.offer(market=item, open_time_ms=0, fingerprint="B")
    third = coordinator.offer(market=item, open_time_ms=0, fingerprint="C")
    assert (first.sequence, second.sequence, third.sequence) == (1, 2, 3)
    assert coordinator.latest(item.identity.market_id) is third
    release.set()
    task = coordinator.task_for(item.identity.market_id)
    assert task is not None
    await task
    assert seen == ["A", "C"]
    assert not coordinator.pending and not coordinator.tasks
    assert discarded == [] and failed == set()


@async_test
async def test_one_failed_market_does_not_stop_another_market() -> None:
    failed: set[str] = set()
    completed: set[str] = set()

    async def confirm(generation):  # type: ignore[no-untyped-def]
        market_id = generation.identity.market_id
        if generation.market.identity.coin == "BAD":
            return ConfirmationResult.FAILED
        completed.add(market_id)
        return ConfirmationResult.COMPLETE

    coordinator = GenerationFinalityAuthority(
        confirm=confirm,
        discard=lambda _identity: None,
        mark_failed=failed.add,
        now_ms=lambda: 303_000,
        sleep=asyncio.sleep,
        confirmation_concurrency=2,
    )
    bad = market("BAD")
    good = market("GOOD")
    coordinator.offer(market=bad, open_time_ms=0, fingerprint="bad")
    coordinator.offer(market=good, open_time_ms=0, fingerprint="good")
    tasks = tuple(coordinator.tasks.values())
    await asyncio.gather(*tasks)
    assert failed == {bad.identity.market_id}
    assert completed == {good.identity.market_id}
    assert not coordinator.pending and not coordinator.tasks


@async_test
async def test_a_rest1_running_then_b_self_finalizes_without_third_ws_event(
    tmp_path: Path,
) -> None:
    a = candle("BTC", 0)
    b = candle("BTC", 0, close="101")
    client = SequenceClient([[a], [b], [b]], blocked_calls={0})
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client)
    await runtime.handle_message(ws(a))
    original_task = runtime._finality.task_for(item.identity.market_id)
    assert original_task is not None
    await wait_for_thread_event(client.entered[0])
    await runtime.handle_message(ws(b))
    latest = runtime._finality.latest(item.identity.market_id)
    assert latest is not None and latest.sequence == 2 and latest.fingerprint != ""
    assert runtime._finality.task_for(item.identity.market_id) is original_task
    client.release[0].set()
    await original_task
    bars = authority.store.bars(item.identity.market_id)
    assert len(client.calls) == 3
    assert len(bars) == 1 and str(bars[0].close) == "101"
    assert not runtime._finality.pending and not runtime._finality.tasks


@async_test
async def test_a_two_rest_observations_then_b_supersedes_before_admission(
    tmp_path: Path,
) -> None:
    a = candle("BTC", 0)
    b = candle("BTC", 0, close="101")
    client = SequenceClient([[a], [a], [b], [b]])
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client)
    loop = asyncio.get_running_loop()
    client.after_call[1] = lambda: loop.call_soon_threadsafe(
        lambda: asyncio.create_task(runtime.handle_message(ws(b)))
    )
    await runtime.handle_message(ws(a))
    await wait_for_finality(runtime, item.identity.market_id)
    bars = authority.store.bars(item.identity.market_id)
    assert len(client.calls) == 4
    assert len(bars) == 1 and str(bars[0].close) == "101"


@async_test
async def test_different_open_supersedes_obsolete_confirmation_path(tmp_path: Path) -> None:
    a = candle("BTC", 0)
    b = candle("BTC", 300_000, close="101")
    client = SequenceClient([[a], [b], [b]], blocked_calls={0})
    runtime, authority, (item,), clock = setup_runtime(tmp_path, client=client)
    await runtime.handle_message(ws(a))
    await wait_for_thread_event(client.entered[0])
    clock.seconds = 603
    await runtime.handle_message(ws(b))
    latest = runtime._finality.latest(item.identity.market_id)
    assert latest is not None and latest.identity.open_time_ms == 300_000
    client.release[0].set()
    await wait_for_finality(runtime, item.identity.market_id)
    bars = authority.store.bars(item.identity.market_id)
    assert [bar.open_time_ms for bar in bars] == [300_000]


@async_test
async def test_stable_two_confirmation_admit_and_unstable_pair_rejects(tmp_path: Path) -> None:
    stable = candle("BTC", 0)
    changed = candle("BTC", 0, close="101")
    good = SequenceClient([[stable], [stable]])
    runtime, authority, (item,), _ = setup_runtime(tmp_path / "stable", client=good)
    await runtime.handle_message(ws(stable))
    await wait_for_finality(runtime, item.identity.market_id)
    assert len(good.calls) == TARGET_CONFIRMATIONS
    assert len(authority.store.bars(item.identity.market_id)) == 1

    bad = SequenceClient([[stable], [changed]])
    rejected, rejected_authority, (rejected_item,), _ = setup_runtime(
        tmp_path / "unstable", client=bad
    )
    await rejected.handle_message(ws(stable))
    await wait_for_finality(rejected, rejected_item.identity.market_id)
    assert rejected_authority.store.bars(rejected_item.identity.market_id) == ()
    assert rejected_item.identity.market_id in rejected.health.failed_markets


@async_test
async def test_less_than_one_second_monotonic_observation_gap_is_rejected(
    tmp_path: Path,
) -> None:
    value = candle("BTC", 0)
    client = SequenceClient([[value], [value]])
    clock = Clock(advance_monotonic=False)
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client, clock=clock)
    await runtime.handle_message(ws(value))
    await wait_for_finality(runtime, item.identity.market_id)
    assert authority.store.bars(item.identity.market_id) == ()
    assert item.identity.market_id in runtime.health.failed_markets


@async_test
async def test_duplicate_finalized_is_idempotent_and_changed_finalized_identity_conflicts(
    tmp_path: Path,
) -> None:
    a = candle("BTC", 0)
    b = candle("BTC", 0, close="101")
    client = SequenceClient([[a], [a], [a], [a], [b], [b]])
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client)
    for payload in (a, a):
        await runtime.handle_message(ws(payload))
        await wait_for_finality(runtime, item.identity.market_id)
    assert len(authority.store.bars(item.identity.market_id)) == 1
    assert item.identity.market_id not in runtime.health.failed_markets

    await runtime.handle_message(ws(b))
    await wait_for_finality(runtime, item.identity.market_id)
    bars = authority.store.bars(item.identity.market_id)
    assert len(bars) == 1 and str(bars[0].close) == "100"
    assert item.identity.market_id in runtime.health.failed_markets


class BoundedClient:
    def __init__(self) -> None:
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0

    def closed_candles(
        self, *, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> object:
        assert interval == "5m" and end_ms == start_ms + 300_000
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if not self.release.wait(timeout=5):
                raise TimeoutError("test client was not released")
            return [candle(coin, start_ms)]
        finally:
            with self._lock:
                self.active -= 1


@async_test
async def test_40_market_pending_state_and_confirmation_concurrency_are_bounded(
    tmp_path: Path,
) -> None:
    selected = tuple(market(f"M{index:02d}") for index in range(40))
    client = BoundedClient()
    runtime, authority, _, _ = setup_runtime(
        tmp_path,
        client=client,  # type: ignore[arg-type]
        markets=selected,
        confirmation_concurrency=4,
    )
    for item in selected:
        await runtime.handle_message(ws(candle(item.identity.coin, 0)))
    for _ in range(1_000):
        if client.max_active == 4:
            break
        await asyncio.sleep(0.001)
    assert len(runtime._finality.pending) == 40
    assert len(runtime._finality.tasks) == 40
    assert client.max_active == 4
    invalidation = asyncio.create_task(runtime._finality.invalidate_all())
    await asyncio.sleep(0)
    client.release.set()
    await invalidation
    assert not runtime._finality.pending and not runtime._finality.tasks
    assert all(authority.store.bars(item.identity.market_id) == () for item in selected)


@async_test
async def test_reconnect_invalidation_prevents_stale_task_admission(tmp_path: Path) -> None:
    value = candle("BTC", 0)
    client = SequenceClient([[value], [value], [value]], blocked_calls={0})
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client)
    await runtime.handle_message(ws(value))
    await wait_for_thread_event(client.entered[0])
    await runtime._finality.invalidate_all()
    client.release[0].set()
    await asyncio.sleep(0)
    assert authority.store.bars(item.identity.market_id) == ()
    assert not runtime._finality.pending and not runtime._finality.tasks

    await runtime.handle_message(ws(value))
    await wait_for_finality(runtime, item.identity.market_id)
    assert len(authority.store.bars(item.identity.market_id)) == 1


@async_test
async def test_shutdown_cancels_and_cleans_all_finality_state(tmp_path: Path) -> None:
    value = candle("BTC", 0)
    client = SequenceClient([[value]], blocked_calls={0})
    runtime, authority, (item,), _ = setup_runtime(tmp_path, client=client)
    await runtime.handle_message(ws(value))
    await wait_for_thread_event(client.entered[0])
    await runtime._finality.close()
    client.release[0].set()
    await asyncio.sleep(0)
    assert authority.store.bars(item.identity.market_id) == ()
    assert not runtime._finality.pending and not runtime._finality.tasks
    with pytest.raises(RuntimeError, match="closed"):
        runtime._finality.offer(market=item, open_time_ms=0, fingerprint="new")


def test_frozen_finality_constants() -> None:
    assert POST_CLOSE_HOLD_MS == 3_000
    assert TARGET_CONFIRMATIONS == 2
    assert MIN_MONOTONIC_CONFIRMATION_GAP_MS == 1_000
