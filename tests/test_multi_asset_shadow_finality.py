"""Adversarial generation/finality tests for the A1 public-data runtime.

Single-owner architecture (attack AV): per-market websocket traffic may only
offer and supersede candidates, while targeted exact-T confirmation REST,
durable admission, and the global LIVE_ACTIONABLE wake happen exclusively
inside the cohort barrier.  The legacy per-market ``runtime._finality`` engine
tests were replaced by these composition equivalents; the generation
coordinator unit tests and the frozen constants below are unchanged.
"""

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
    DataRouteError,
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
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime

T = 300_000


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
    sleep: Callable[[float], object] | None = None,
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
        sleep=sleep or clock.sleep,
        confirmation_concurrency=confirmation_concurrency,
    )
    return runtime, authority, selected, clock


async def wait_for_thread_event(event: threading.Event) -> None:
    assert await asyncio.wait_for(asyncio.to_thread(event.wait, 2), timeout=3)


def active_market(coin: str = "BTC") -> RegistryMarket:
    return market(coin).model_copy(update={"lifecycle": MarketLifecycle.ACTIVE})


def seed_boundary_zero(
    authority: MultiAssetDataAuthority, selected: tuple[RegistryMarket, ...]
) -> None:
    for item in selected:
        authority.admit_rest_history(
            market=item,
            snapshot=[candle(item.identity.coin, 0)],
            received_at=datetime.fromtimestamp(301_000 / 1000, UTC),
        )


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
async def test_ws_candidate_supersession_is_observation_only_then_barrier_proves(
    tmp_path: Path,
) -> None:
    item = active_market()
    a = candle("BTC", T)
    b = candle("BTC", T, close="101")
    client = SequenceClient([[a], [a]])
    runtime, authority, (selected,), clock = setup_runtime(
        tmp_path, client=client, markets=(item,)
    )
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime.on_finalized_5m = on_finalized
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (selected,))

    first = authority.offer_ws_candidate(market=item, payload=a, received_at=clock.now())
    second = authority.offer_ws_candidate(market=item, payload=b, received_at=clock.now())
    assert first != second
    assert (
        authority.offer_ws_candidate(market=item, payload=b, received_at=clock.now()) == second
    )
    await runtime.handle_message(ws(a))
    await runtime.handle_message(ws(b))
    # Superseding candidates are pure observation: no REST, no durable evidence.
    assert client.calls == []
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [0]

    await runtime.process_cohort_boundary(T)
    assert client.calls == [("BTC", T, T + 300_000)] * 2
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [0, T]
    assert wakes == [(T, BoundaryMode.LIVE_ACTIONABLE)]


@async_test
async def test_stable_confirmation_pair_finalizes_and_unstable_pair_fails_closed(
    tmp_path: Path,
) -> None:
    stable = candle("BTC", T)
    changed = candle("BTC", T, close="101")
    good = SequenceClient([[stable], [stable]])
    runtime, authority, (item,), _ = setup_runtime(
        tmp_path / "stable", client=good, markets=(active_market(),)
    )
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime.on_finalized_5m = on_finalized
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (item,))
    await runtime.process_cohort_boundary(T)
    assert len(good.calls) == TARGET_CONFIRMATIONS
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [0, T]
    assert wakes == [(T, BoundaryMode.LIVE_ACTIONABLE)]

    bad = SequenceClient([[stable], [changed]])
    rejected, rejected_authority, (rejected_item,), _ = setup_runtime(
        tmp_path / "unstable", client=bad, markets=(active_market(),)
    )
    rejected_wakes: list[tuple[int, BoundaryMode]] = []

    async def on_rejected(bar: object, mode: BoundaryMode) -> None:
        rejected_wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    rejected.on_finalized_5m = on_rejected
    rejected.health.data_ready = True
    seed_boundary_zero(rejected_authority, (rejected_item,))
    await rejected.process_cohort_boundary(T)
    assert [
        bar.open_time_ms for bar in rejected_authority.store.bars(rejected_item.identity.market_id)
    ] == [0]
    assert rejected_item.identity.market_id in rejected.health.failed_markets
    assert rejected_wakes == []


@async_test
async def test_frozen_monotonic_confirmation_gap_is_requested_between_confirmations(
    tmp_path: Path,
) -> None:
    value = candle("BTC", T)
    clock = Clock()
    requested: list[float] = []

    async def sleep(seconds: float) -> None:
        requested.append(seconds)
        await clock.sleep(seconds)

    client = SequenceClient([[value], [value]])
    runtime, authority, (item,), _ = setup_runtime(
        tmp_path, client=client, markets=(active_market(),), clock=clock, sleep=sleep
    )
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (item,))
    await runtime.process_cohort_boundary(T)
    # Post-close hold first, then exactly one frozen-gap sleep between the two
    # targeted confirmations.
    assert requested == [300.0, MIN_MONOTONIC_CONFIRMATION_GAP_MS / 1_000]
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [0, T]


@async_test
async def test_duplicate_boundary_is_idempotent_and_changed_identity_conflicts(
    tmp_path: Path,
) -> None:
    a = candle("BTC", T)
    client = SequenceClient([[a], [a]])
    runtime, authority, (item,), _ = setup_runtime(
        tmp_path, client=client, markets=(active_market(),)
    )
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (item,))
    await runtime.process_cohort_boundary(T)
    calls_after_first = len(client.calls)
    bars_after_first = authority.store.bars(item.identity.market_id)
    await runtime.process_cohort_boundary(T)
    assert len(client.calls) == calls_after_first
    assert authority.store.bars(item.identity.market_id) == bars_after_first
    # A changed payload for an already-durable boundary can never rewrite it.
    with pytest.raises(DataRouteError):
        authority.admit_rest_history(
            market=item,
            snapshot=[candle("BTC", T, close="999")],
            received_at=datetime.fromtimestamp((T + 301_000) / 1000, UTC),
        )
    assert authority.store.bars(item.identity.market_id) == bars_after_first


class BoundedClient:
    def __init__(self) -> None:
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(
        self, *, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> object:
        assert interval == "5m" and end_ms == start_ms + 300_000
        with self._lock:
            self.calls.append((coin, start_ms, end_ms))
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
async def test_40_market_confirmation_concurrency_is_bounded_without_pending_state(
    tmp_path: Path,
) -> None:
    selected = tuple(active_market(f"M{index:02d}") for index in range(40))
    client = BoundedClient()

    async def instant_sleep(_seconds: float) -> None:
        await asyncio.sleep(0)

    runtime, authority, _, _ = setup_runtime(
        tmp_path,
        client=client,  # type: ignore[arg-type]
        markets=selected,
        confirmation_concurrency=4,
        clock=Clock(seconds=605, advance_monotonic=False),
        sleep=instant_sleep,
    )
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime.on_finalized_5m = on_finalized
    runtime.health.data_ready = True
    seed_boundary_zero(authority, selected)
    task = asyncio.create_task(runtime.process_cohort_boundary(T))
    for _ in range(2_000):
        if client.max_active == 4:
            break
        await asyncio.sleep(0.001)
    assert client.max_active == 4
    client.release.set()
    await task
    assert len(client.calls) == 2 * len(selected)
    for item in selected:
        assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [
            0,
            T,
        ]
    assert wakes == [(T, BoundaryMode.LIVE_ACTIONABLE)]


@async_test
async def test_reconnect_recovery_persists_evidence_but_only_barrier_acts(
    tmp_path: Path,
) -> None:
    boundary = 600_000
    clock = Clock(seconds=905)
    client = SequenceClient([[candle("BTC", 300_000), candle("BTC", boundary)]])
    runtime, authority, (item,), _ = setup_runtime(
        tmp_path, client=client, markets=(active_market(),), clock=clock
    )
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime.on_finalized_5m = on_finalized
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (item,))
    await runtime.handle_message(ws(candle("BTC", boundary)))
    assert client.calls == []
    # Reconnect drops readiness and re-hydrates history as context only.
    runtime.health.data_ready = False
    await runtime._warmup_all(recovery=True)
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [
        0,
        300_000,
        boundary,
    ]
    assert wakes == []
    # Global LIVE_ACTIONABLE authority still belongs to the barrier alone.
    runtime.health.data_ready = True
    await runtime.process_cohort_boundary(boundary)
    assert wakes == [(boundary, BoundaryMode.LIVE_ACTIONABLE)]


@async_test
async def test_cancelled_barrier_leaves_no_durable_authority(tmp_path: Path) -> None:
    value = candle("BTC", T)
    client = SequenceClient([[value]], blocked_calls={0})
    runtime, authority, (item,), _ = setup_runtime(
        tmp_path, client=client, markets=(active_market(),)
    )
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime.on_finalized_5m = on_finalized
    runtime.health.data_ready = True
    seed_boundary_zero(authority, (item,))
    task = asyncio.create_task(runtime.process_cohort_boundary(T))
    await wait_for_thread_event(client.entered[0])
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # The orphaned worker thread may return late; it must not admit anything.
    client.release[0].set()
    await asyncio.sleep(0.05)
    assert [bar.open_time_ms for bar in authority.store.bars(item.identity.market_id)] == [0]
    assert item.identity.market_id not in runtime.health.nonrecoverable_markets
    assert item.identity.market_id not in runtime.health.failed_markets
    assert wakes == []


def test_frozen_finality_constants() -> None:
    assert POST_CLOSE_HOLD_MS == 3_000
    assert TARGET_CONFIRMATIONS == 2
    assert MIN_MONOTONIC_CONFIRMATION_GAP_MS == 1_000
