"""PHASE 1 frozen contract: the single-owner 5m cohort barrier in the runtime.

Packet sections 4, 6, 8, 10-23 and attacks D, H, J, M, N, O, P, Q, U, Y, AI,
AJ, AK, AM, AN, AS, AT, AU.  ``process_cohort_boundary`` is the only global
authority: it captures R, classifies retained T before any provider request,
routes recovery/context separately from live finality, performs at most one
witness-authorized Registry switch, and issues at most one application wake.
Small synthetic cohorts prove the barrier does not encode N=20.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

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
    STARTUP_REST_COOLDOWN_SECONDS,
    BoundaryMode,
    MultiAssetPublicRuntime,
)

FIVE_MINUTES_MS = 300_000
T = 100 * FIVE_MINUTES_MS
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def market(coin: str, lifecycle: MarketLifecycle) -> RegistryMarket:
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
        metadata_hash="0" * 64,
    )


def candle(coin: str, open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + FIVE_MINUTES_MS - 1,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": "100",
        "v": "10",
    }


def received_at(open_ms: int) -> datetime:
    return datetime.fromtimestamp((open_ms + FIVE_MINUTES_MS + 4_000) / 1000, UTC)


class ScriptedClient:
    """Deterministic provider: exact-T windows vs wide history windows."""

    def __init__(self, *, errors: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, int, int]] = []
        self.errors = errors or {}

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        if coin in self.errors:
            raise self.errors[coin]
        if end_ms - start_ms == FIVE_MINUTES_MS:
            return [candle(coin, start_ms)]
        return [
            candle(coin, open_ms)
            for open_ms in range(start_ms, end_ms, FIVE_MINUTES_MS)
        ]


class Composition:
    def __init__(
        self,
        root: Path,
        *,
        coins: tuple[str, ...] = ("BTC", "ETH", "SOL"),
        lifecycle: MarketLifecycle = MarketLifecycle.SNAPSHOT_READY,
        client: ScriptedClient | None = None,
    ) -> None:
        self.items = tuple(market(coin, lifecycle) for coin in coins)
        self.registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
        seed = RegistryVersion.create(version="seed", created_at=NOW, markets=self.items)
        self.registry.stage(seed)
        self.registry.request_apply(seed.version)
        self.authority = MultiAssetDataAuthority(
            store=ClosedBarStore(root / "closed.sqlite"), registry=self.registry
        )
        self.client = client or ScriptedClient()
        self.wakes: list[tuple[int, BoundaryMode]] = []
        self.maintenance: list[int] = []
        self.mono = time.monotonic()
        self.wall = T + FIVE_MINUTES_MS + 5_000  # five seconds after T close

        async def on_finalized(bar: object, mode: BoundaryMode) -> None:
            self.wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

        async def on_maintenance(boundary: int) -> None:
            self.maintenance.append(boundary)

        self.runtime = MultiAssetPublicRuntime(
            registry=self.registry,
            authority=self.authority,
            client=self.client,  # type: ignore[arg-type]
            clock=lambda: datetime.fromtimestamp(self.wall / 1000, UTC),
            monotonic=lambda: self.mono,
            sleep=self._sleep,
            on_finalized_5m=on_finalized,
        )
        self.runtime.on_maintenance_5m = on_maintenance
        self.runtime.health.data_ready = True

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(0)

    def seed_history(self, through_ms: int, *, coins: tuple[str, ...] | None = None) -> None:
        selected = self.items if coins is None else tuple(
            item for item in self.items if item.identity.coin in coins
        )
        for item in selected:
            self.authority.admit_rest_history(
                market=item,
                snapshot=[
                    candle(item.identity.coin, open_ms)
                    for open_ms in range(0, through_ms + FIVE_MINUTES_MS, FIVE_MINUTES_MS)
                ],
                received_at=received_at(through_ms),
            )

    def barrier(self, boundary: int) -> object:
        # Production runs the barrier for B shortly after B closes: advance the
        # injected wall clock monotonically (never backwards past an explicit
        # stale-clock override set by a test).
        self.wall = max(self.wall, boundary + FIVE_MINUTES_MS + 5_000)
        return self.runtime.process_cohort_boundary(boundary)

    def rows_at(self, boundary: int) -> dict[str, tuple[str, str]]:
        active = self.registry.active()
        assert active is not None
        rows: dict[str, tuple[str, str]] = {}
        for item in self.items:
            row = self.authority.store.connection.execute(
                "SELECT registry_version, registry_content_hash FROM closed_bars "
                "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
                (item.identity.market_id, boundary),
            ).fetchone()
            rows[item.identity.coin] = (str(row[0]), str(row[1])) if row else ()
        return rows


@async_test
async def test_initial_launch_healthy_transitions_without_action_then_t1_acts(
    tmp_path: Path,
) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    active = world.registry.active()
    assert active is not None
    assert all(item.lifecycle is MarketLifecycle.ACTIVE for item in active.markets)
    # The transition boundary itself holds no live action (packet section 19).
    assert world.wakes == []
    # T rows were proven through exactly two targeted calls per market.
    assert len(world.client.calls) == 2 * len(world.items)
    assert all(world.rows_at(T).values())
    await world.barrier(T + FIVE_MINUTES_MS)
    assert world.wakes == [(T + FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)]


@async_test
async def test_initial_launch_failure_holds_lifecycle_and_wakes_nothing(tmp_path: Path) -> None:
    world = Composition(
        tmp_path,
        client=ScriptedClient(errors={"SOL": RuntimeError("defective provider path")}),
    )
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    active = world.registry.active()
    assert active is not None
    assert all(item.lifecycle is MarketLifecycle.SNAPSHOT_READY for item in active.markets)
    assert world.runtime.health.nonrecoverable_markets == {
        item.identity.market_id for item in world.items if item.identity.coin == "SOL"
    }
    assert world.wakes == []
    assert not any(world.rows_at(T)[coin] for coin in ("SOL",))


@async_test
async def test_same_process_provider_success_does_not_clear_nonrecoverable(tmp_path: Path) -> None:
    world = Composition(
        tmp_path,
        client=ScriptedClient(errors={"SOL": RuntimeError("defective provider path")}),
    )
    world.seed_history(T - FIVE_MINUTES_MS)
    await world.barrier(T)
    assert world.runtime.health.nonrecoverable_markets
    # Provider recovers in the same process: the failure authority is sticky.
    world.client.errors.clear()
    world.seed_history(T, coins=("BTC", "ETH"))
    await world.barrier(T + FIVE_MINUTES_MS)
    assert world.wakes == []
    assert world.runtime.health.nonrecoverable_markets


@async_test
async def test_duplicate_boundary_wake_uses_zero_finality_rest(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    calls_after_first = len(world.client.calls)
    await world.barrier(T)
    assert len(world.client.calls) == calls_after_first
    # The first boundary transitioned the Registry: no action at T either time.
    assert world.wakes == []


@async_test
async def test_concurrent_duplicate_boundary_is_serialized(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await asyncio.gather(world.barrier(T), world.barrier(T))
    # Exactly one finality proof round for the whole cohort, never two.
    assert len(world.client.calls) == 2 * len(world.items)


@async_test
async def test_t_and_t_plus_one_concurrency_produces_no_mixed_epochs(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await asyncio.gather(
        world.barrier(T), world.barrier(T + FIVE_MINUTES_MS)
    )
    for boundary in (T, T + FIVE_MINUTES_MS):
        bindings = {binding for binding in world.rows_at(boundary).values() if binding}
        assert len(bindings) == 1


@async_test
async def test_hot_add_failure_does_not_pause_active_cohort(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    # Initial launch completed: the cohort is ACTIVE, T is the switch boundary.
    active = world.registry.active()
    assert active is not None
    assert all(item.lifecycle is MarketLifecycle.ACTIVE for item in active.markets)
    # Stage a manual hot-add successor as a PRE-EXISTING pending proposal; the
    # barrier at T+1 is the only authority that may apply it (attack V/U).
    hot_add = market("DOGE", MarketLifecycle.WARMING)
    successor = world.registry.successor(
        version="hot-add-1", now=NOW, update_market=hot_add
    )
    world.registry.request_apply(successor.version)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items} | {"DOGE"}
    world.client.errors["DOGE"] = RuntimeError("hot-add defect")
    await world.barrier(T + FIVE_MINUTES_MS)
    # The original ACTIVE cohort still acted despite the failed WARMING add.
    assert world.wakes == [(T + FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)]
    active_now = world.registry.active()
    assert active_now is not None
    doge = next(
        item for item in active_now.markets if item.identity.coin == "DOGE"
    )
    assert doge.lifecycle is MarketLifecycle.WARMING


@async_test
async def test_stale_lifecycle_pending_not_reproduced_by_planner_is_not_applied(
    tmp_path: Path,
) -> None:
    # Attack W: a staged lifecycle candidate that the current planner would not
    # reproduce is a stale/conflicting control-plane proposal.  The barrier
    # applies nothing, mints no second successor, and still runs live action
    # for the healthy ACTIVE cohort.
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    hot_add = market("DOGE", MarketLifecycle.WARMING)
    successor = world.registry.successor(
        version="hot-add-1", now=NOW, update_market=hot_add
    )
    world.registry.request_apply(successor.version)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items} | {"DOGE"}
    await world.barrier(T + FIVE_MINUTES_MS)
    active_after_add = world.registry.active()
    assert active_after_add is not None
    assert active_after_add.version == successor.version
    doge_id = hot_add.identity.market_id
    stale = world.registry.lifecycle_successor(
        version="stale-doge-advance",
        updates={doge_id: MarketLifecycle.HISTORY_READY},
        now=NOW,
    )
    world.registry.request_apply(stale.version)
    # DOGE is behind and its recovery fails: the planner will not reproduce the
    # staged advance at the next boundary.
    world.client.errors["DOGE"] = RuntimeError("stale proposal peer defect")
    await world.barrier(T + 2 * FIVE_MINUTES_MS)
    assert world.wakes[-1] == (T + 2 * FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)
    active_now = world.registry.active()
    assert active_now is not None
    assert active_now.version == successor.version
    doge = next(item for item in active_now.markets if item.identity.market_id == doge_id)
    assert doge.lifecycle is MarketLifecycle.WARMING
    pending = world.registry.pending_version()
    assert pending is not None
    assert pending.version == stale.version


@async_test
async def test_lagging_market_routes_to_context_recovery_without_live_action(
    tmp_path: Path,
) -> None:
    world = Composition(tmp_path)
    # Two markets coherent through T-1, one stuck far behind.
    world.seed_history(T - FIVE_MINUTES_MS, coins=("BTC", "ETH"))
    world.seed_history(T - 10 * FIVE_MINUTES_MS, coins=("SOL",))
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    assert world.wakes == []
    assert T in world.maintenance
    # The lagging market recovered context history; live peers were proven.
    sol_calls = [call for call in world.client.calls if call[0] == "SOL"]
    assert any(call[2] - call[1] > FIVE_MINUTES_MS for call in sol_calls)


@async_test
async def test_predecessor_rows_are_context_not_refinalized(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    # Initial launch completed at T: the cohort is ACTIVE under the lifecycle
    # successor.  Prove T+1 rows under that epoch, then switch to a manual
    # successor R2 exactly like production: one witness at T+1 after the rows
    # are durable and bound to the live base epoch.
    await world.barrier(T + FIVE_MINUTES_MS)
    assert world.wakes == [(T + FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)]
    base = world.registry.active()
    assert base is not None
    successor = world.registry.successor(
        version="manual-r2",
            now=NOW,
            update_market=world.items[0].model_copy(update={"growth_mode": "HOT_ADD"}),
    )
    world.registry.request_apply(successor.version)
    witness = world.registry._issue_cohort_witness(
        boundary_open_time_ms=T + FIVE_MINUTES_MS,
        base_registry_version=base.version,
        base_registry_hash=base.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset(
            item.identity.market_id for item in world.items
        ),
    )
    world.registry.apply_witness(
        witness, evidence_authority=world.authority
    )
    calls_before = len(world.client.calls)
    # Restart-equivalent: a fresh runtime over the same durable state.
    world2 = Composition.__new__(Composition)
    world2.items = world.items
    world2.registry = MarketRegistryManager(
        tmp_path / "registry", metadata_validator=lambda _: True
    )
    world2.authority = MultiAssetDataAuthority(
        store=world.authority.store, registry=world2.registry
    )
    world2.client = world.client
    world2.wakes = []
    world2.maintenance = []
    world2.mono = world.mono
    world2.wall = T + 2 * FIVE_MINUTES_MS + 5_000

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        world2.wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    async def on_maintenance(boundary: int) -> None:
        world2.maintenance.append(boundary)

    world2.runtime = MultiAssetPublicRuntime(
        registry=world2.registry,
        authority=world2.authority,
        client=world2.client,  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp(world2.wall / 1000, UTC),
        monotonic=lambda: world2.mono,
        sleep=world._sleep,
        on_finalized_5m=on_finalized,
    )
    world2.runtime.on_maintenance_5m = on_maintenance
    world2.runtime.health.data_ready = True
    # The wall clock still points at the switched boundary: predecessor-bound
    # rows must not be refinalized, rewritten, or actioned.
    await world2.barrier(T + FIVE_MINUTES_MS)
    assert len(world.client.calls) == calls_before
    assert world2.wakes == []
    assert world2.maintenance == [T + FIVE_MINUTES_MS]
    # The next fresh boundary acts under R2 for the first time.
    await world2.barrier(T + 2 * FIVE_MINUTES_MS)
    assert world2.wakes == [(T + 2 * FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)]
    bindings = {binding for binding in world2.rows_at(T + 2 * FIVE_MINUTES_MS).values() if binding}
    assert len(bindings) == 1
    assert next(iter(bindings))[0] == successor.version


@async_test
async def test_stale_boundary_after_progress_is_ignored(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    await world.barrier(T + FIVE_MINUTES_MS)
    calls = len(world.client.calls)
    await world.barrier(T)  # wall clock turned backwards
    assert len(world.client.calls) == calls
    assert world.wakes == [(T + FIVE_MINUTES_MS, BoundaryMode.LIVE_ACTIONABLE)]


@async_test
async def test_stale_clock_forward_skips_old_boundary_live_action(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    # The action ceiling for T already passed before the barrier ran.
    world.wall = T + 3 * FIVE_MINUTES_MS + 5_000
    await world.barrier(T)
    assert world.wakes == []
    assert world.client.calls == []


@async_test
async def test_cold_start_rest_cooldown_blocks_first_full_cohort_burst(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    started = 1_000.0
    world.mono = started
    world.runtime.begin_cold_start_rest_cooldown()
    await world.barrier(T)
    assert world.client.calls == []
    assert world.wakes == []
    world.mono = started + STARTUP_REST_COOLDOWN_SECONDS + 1.0
    await world.barrier(T)
    assert len(world.client.calls) == 2 * len(world.items)


@async_test
async def test_maintenance_runs_when_one_peer_is_not_actionable(tmp_path: Path) -> None:
    world = Composition(
        tmp_path,
        client=ScriptedClient(errors={"SOL": RuntimeError("one market missing")}),
    )
    world.seed_history(T - FIVE_MINUTES_MS)
    world.runtime.health.acknowledgements = {item.identity.coin for item in world.items}
    await world.barrier(T)
    assert world.wakes == []
    assert T in world.maintenance


def test_barrier_does_not_hardcode_first_launch_twenty() -> None:
    # The frozen runtime contract must not encode N=20 anywhere in its surface.
    import inspect

    from trader_assist_v0.multi_asset_shadow import runtime as runtime_module

    source = inspect.getsource(runtime_module)
    assert "FIRST_LAUNCH_20" not in source
    assert "== 20" not in source
