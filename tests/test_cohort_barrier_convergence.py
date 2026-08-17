"""Clock-driven 5m cohort barrier + dual-REST cohort finality convergence.

Mandatory attack tests (A-L) over the REAL production composition:
Runtime clock barrier -> Closed5mCohortFinality -> DataAuthority admission ->
Registry barrier activation -> Bootstrap -> Scanner -> Strategy.

The clock owns WHEN a boundary is reconciled; the finality policy owns HOW it
is proven.  Nothing here uses WebSocket candidates: the production
composition runs ``ws_candidate_finality=False`` and the clock alone wakes the
cohort.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path
from typing import Any

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.bootstrap import (
    BoundaryDisposition,
    MultiAssetProductionBootstrap,
)
from trader_assist_v0.multi_asset_shadow.cohort_finality import (
    Closed5mCohortFinality,
    CohortFinalityResult,
)
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import PublicDataError
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    MultiAssetShadowCoordinator,
    PublicL2Snapshot,
    ScannerPublicSnapshot,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    ClosedBar,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import OneMinuteBar, OutcomeEngine
from trader_assist_v0.multi_asset_shadow.planning import CostModel, PublicBbo
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import MultiAssetPublicRuntime
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

SLOT = 300_000
HOLD_MS = 3_000
BARS = 64
BOUNDARY = (BARS - 1) * SLOT
LIVE = BARS * SLOT
NOW = datetime(2026, 8, 17, 0, 0, tzinfo=UTC)
RELEASE_SHA = "1" * 40
COINS = (
    "BTC", "ETH", "HYPE", "SOL", "XRP",
    "xyz:SKHX", "xyz:MU", "xyz:SNDK", "xyz:XYZ100", "xyz:SP500",
    "xyz:CL", "xyz:DRAM", "xyz:SPCX", "xyz:SILVER", "xyz:NVDA",
    "xyz:SMSN", "xyz:EWY", "xyz:GOLD", "xyz:TESLA", "xyz:GOOGL",
)
FLAT_COINS = frozenset(COINS[5:10])
HOT_ADD_COIN = "xyz:NEWCOIN"


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def market(coin: str, lifecycle: MarketLifecycle = MarketLifecycle.ACTIVE) -> RegistryMarket:
    native = not coin.startswith("xyz:")
    return RegistryMarket(
        display=coin.removeprefix("xyz:"),
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN" if native else "xyz", coin=coin),
        asset_class=AssetClass.CRYPTO if native else AssetClass.EQUITY,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=not native,
        market_status="ACTIVE",
        lifecycle=lifecycle,
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(f"{coin}-metadata".encode()),
    )


def payload(coin: str, index: int) -> dict[str, object]:
    """Deterministic provider truth for (coin, open): every observation agrees.

    Zero-trade markets are flat ONLY at their zero-trade boundaries; history
    keeps provider variance so the frozen ATR14/zone authority stays satisfiable
    (a fully flat retained series is a legitimate kernel decline, not a bug).
    """
    start = index * SLOT
    if coin in FLAT_COINS and index >= LIVE // SLOT:
        return {
            "i": "5m", "s": coin, "t": start, "T": start + SLOT - 1,
            "o": "105", "h": "105", "l": "105", "c": "105", "v": "0",
        }
    group = index // 3
    return {
        "i": "5m", "s": coin, "t": start, "T": start + SLOT - 1,
        "o": "105",
        "h": "110" if group % 5 == 2 else "106",
        "l": "100" if group % 5 == 3 else "104",
        "c": "105", "v": "10",
    }


def poisoned(coin: str, index: int) -> dict[str, object]:
    """Schema-valid but wrong: an unsafe end-inclusive echo value."""
    start = index * SLOT
    return {
        "i": "5m", "s": coin, "t": start, "T": start + SLOT - 1,
        "o": "999", "h": "999", "l": "1", "c": "1", "v": "9999",
    }


class CohortGrid:
    """End-inclusive provider grid with per-market attack scripting."""

    def __init__(self) -> None:
        self.omit: dict[str, set[int]] = {}
        self.duplicate: set[tuple[str, int]] = set()
        self.conflict: set[tuple[str, int]] = set()
        self.echo_poison: set[tuple[str, int]] = set()
        self.transport_fail: dict[tuple[str, int], int] = {}

    def window(self, coin: str, start_ms: int, end_ms: int) -> list[dict[str, object]]:
        # Real candleSnapshot is end-inclusive: the bar whose open == end_ms
        # is echoed, including the still-forming next boundary.
        first = start_ms // SLOT
        last = end_ms // SLOT
        out: list[dict[str, object]] = []
        for index in range(first, last + 1):
            if index in self.omit.get(coin, set()):
                continue
            if (coin, index) in self.echo_poison:
                out.append(poisoned(coin, index))
                continue
            out.append(payload(coin, index))
            if (coin, index) in self.duplicate:
                out.append(payload(coin, index))
        return out


class CohortClient:
    """Synchronous public REST client over the scripted grid."""

    def __init__(self, grid: CohortGrid) -> None:
        self.grid = grid
        self.calls: list[float] = []
        self.monotonic: Any = None
        self.observation_counts: dict[tuple[str, int], int] = {}

    def bind_monotonic(self, monotonic: Any) -> None:
        self.monotonic = monotonic

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        if self.monotonic is not None:
            self.calls.append(self.monotonic())
        target = start_ms // SLOT
        remaining = self.grid.transport_fail.get((coin, target))
        if remaining:
            self.grid.transport_fail[(coin, target)] = remaining - 1
            raise PublicDataError("transient public route failure")
        count = self.observation_counts.get((coin, target), 0) + 1
        self.observation_counts[(coin, target)] = count
        window = self.grid.window(coin, start_ms, end_ms)
        if (coin, target) in self.grid.conflict and count % 2 == 0:
            flipped = dict(payload(coin, target))
            flipped["c"] = "777"
            return [flipped if item.get("t") == start_ms else item for item in window]
        return window


class VirtualClock:
    def __init__(self, now_ms: int) -> None:
        self.now_ms = now_ms
        self.monotonic_seconds = 0.0

    def clock(self) -> datetime:
        return datetime.fromtimestamp(self.now_ms / 1000, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.now_ms += int(seconds * 1000)
        self.monotonic_seconds += seconds
        await asyncio.sleep(0)


class PlanningData:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> PublicBbo:
        self.calls.append("BBO")
        return PublicBbo(
            best_bid=Decimal("100"),
            best_ask=Decimal("100.1"),
            observed_at_ms=now_ms,
            market_id=market.identity.market_id,
            coin=market.identity.coin,
        )

    def fetch_l2(
        self, *, market: RegistryMarket, side: object, bbo: PublicBbo
    ) -> PublicL2Snapshot:
        self.calls.append("L2")
        return PublicL2Snapshot(
            market_id=market.identity.market_id,
            coin=market.identity.coin,
            observed_at_ms=bbo.observed_at_ms,
            best_bid=bbo.best_bid,
            best_ask=bbo.best_ask,
            levels=((bbo.best_ask, Decimal("20")),),
            provenance_hash="f" * 64,
        )

    def fetch_scanner_snapshot(
        self,
        *,
        market: RegistryMarket,
        now_ms: int,
        btc_returns: tuple[Decimal | None, Decimal | None, Decimal | None],
    ) -> ScannerPublicSnapshot:
        del market, now_ms
        self.calls.append("SCANNER_L2")
        return ScannerPublicSnapshot(Decimal("0.1"), True, btc_returns)


class OneMinuteProvider:
    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        return ()


class BarrierHarness:
    """Real Runtime/Bootstrap/Coordinator composition, clock-driven barrier."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        coins: tuple[str, ...] = COINS,
        lifecycles: dict[str, MarketLifecycle] | None = None,
        grid: CohortGrid | None = None,
        cohort_finality: Closed5mCohortFinality | None = None,
        subdir: str = ".",
        resume: bool = False,
    ) -> None:
        root = tmp_path / subdir
        root.mkdir(parents=True, exist_ok=True)
        self.grid = grid if grid is not None else CohortGrid()
        self.client = CohortClient(self.grid)
        self.registry = MarketRegistryManager(
            root / "registry", metadata_validator=lambda _: True
        )
        if resume:
            # Restart: the durable Registry pointer is the authority; the
            # retained closed-bar rows are already durable.
            active = self.registry.active()
            assert active is not None
            self.markets = active.markets
        else:
            self.markets = tuple(
                market(
                    coin,
                    lifecycle=(
                        lifecycles[coin]
                        if lifecycles is not None
                        else MarketLifecycle.ACTIVE
                    ),
                )
                for coin in coins
            )
            version = RegistryVersion.create(
                version="registry-cohort-20260817", created_at=NOW, markets=self.markets
            )
            self.registry.stage(version)
            self.registry.request_apply(version.version)
        self.closed = ClosedBarStore(root / "closed.sqlite")
        self.data = MultiAssetDataAuthority(store=self.closed, registry=self.registry)
        if not resume:
            for item in self.markets:
                self.data.admit_rest_history(
                    market=item,
                    snapshot=[payload(item.identity.coin, index) for index in range(BARS)],
                    received_at=datetime.fromtimestamp(
                        (BOUNDARY + SLOT + 1_000) / 1000, UTC
                    ),
                )
        self.evidence = EvidenceStore(root / "evidence.sqlite")
        self.outbox = EvidenceOutbox(self.evidence)
        self.outcome_adapter = EvidenceOutcomeAdapter(self.evidence)
        self.outcome = OutcomeEngine(provider=OneMinuteProvider(), sink=self.outcome_adapter)
        self.planning = PlanningData()
        self.clock = VirtualClock(LIVE + SLOT + HOLD_MS)
        self.client.bind_monotonic(self.clock.monotonic)
        self.runtime = MultiAssetPublicRuntime(
            registry=self.registry,
            authority=self.data,
            client=self.client,  # type: ignore[arg-type]
            clock=self.clock.clock,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
            cohort_finality=cohort_finality,
            ws_candidate_finality=False,
        )
        self.runtime.health.data_ready = True
        self.coordinator = MultiAssetShadowCoordinator(
            registry=self.registry,
            data_authority=self.data,
            evidence=self.evidence,
            outbox=self.outbox,
            outcome_engine=self.outcome,
            outcome_adapter=self.outcome_adapter,
            planning_data=self.planning,  # type: ignore[arg-type]
            cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
            release_sha=RELEASE_SHA,
            runtime_readiness=self.runtime,
        )
        self.bootstrap = MultiAssetProductionBootstrap(
            registry=self.registry,
            data_authority=self.data,
            evidence=self.evidence,
            outbox=self.outbox,
            outcome_adapter=self.outcome_adapter,
            outcome_engine=self.outcome,
            planning_data=self.planning,  # type: ignore[arg-type]
            coordinator=self.coordinator,
            runtime=self.runtime,
            clock=self.clock.clock,
            sleep=lambda _: asyncio.sleep(0),
        )
        self.runtime.on_finalized_5m = self.bootstrap.on_finalized_5m

    def id_of(self, coin: str) -> str:
        return next(m.identity.market_id for m in self.markets if m.identity.coin == coin)

    async def barrier(self, boundary_open_time_ms: int) -> Any:
        self.clock.now_ms = boundary_open_time_ms + SLOT + HOLD_MS
        return await self.runtime.process_cohort_boundary(boundary_open_time_ms)

    def binding_of(self, coin: str, boundary: int) -> tuple[str, str] | None:
        row = self.closed.connection.execute(
            "SELECT registry_version, registry_content_hash FROM closed_bars "
            "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
            (self.id_of(coin), boundary),
        ).fetchone()
        return None if row is None else (row[0], row[1])

    def live_bar(self, coin: str, boundary: int) -> ClosedBar:
        return next(
            bar for bar in self.closed.bars(self.id_of(coin)) if bar.open_time_ms == boundary
        )

    def strategy_evaluations(self, boundary: int) -> int:
        # Retained authority counts across Registry epochs: a boundary
        # evaluated under a predecessor epoch is durable truth, never
        # re-created under the newer Registry (restart/replay invariant).
        return sum(
            1
            for item in self.markets
            if self.coordinator.has_retained_strategy_evaluation(
                market_id=item.identity.market_id,
                source_open_time_ms=boundary,
                any_registry_epoch=True,
            )
        )


def assert_processed(report: Any, *, scanner_runs: int, evaluated: int) -> None:
    assert report.action is not None
    assert report.action.disposition is BoundaryDisposition.PROCESSED
    assert report.action.scanner_run_count == scanner_runs
    assert len(report.action.evaluated_market_ids) == evaluated


def assert_deferred(report: Any) -> None:
    assert report.action is not None
    assert report.action.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.action.scanner_run_count == 0
    assert report.action.evaluated_market_ids == ()


# --------------------------------------------------------------------------
# A. ZERO WS -- EXACT 20
# --------------------------------------------------------------------------


@async_test
async def test_a_zero_ws_clock_alone_confirms_exact_20(tmp_path: Path) -> None:
    cohort = BarrierHarness(tmp_path)
    # ZERO websocket events: no candidate was ever offered to the finality
    # authority; the clock barrier alone reconciles the boundary.
    assert cohort.runtime._finality.tasks == {}

    report = await cohort.barrier(LIVE)

    assert len(report.finalized_market_ids) == 20
    assert len(set(report.finalized_market_ids)) == 20
    assert report.failed_market_ids == ()
    # 20/20 same-T durable rows carrying exactly the provider payload: no
    # synthetic candle; zero-trade markets keep the provider's own flat bar.
    for coin in COINS:
        bars = [b for b in cohort.closed.bars(cohort.id_of(coin)) if b.open_time_ms == LIVE]
        assert len(bars) == 1
        truth = payload(coin, LIVE // SLOT)
        assert bars[0].volume == Decimal(str(truth["v"]))
        assert str(bars[0].open) == truth["o"] and str(bars[0].close) == truth["c"]
    flat = cohort.live_bar("xyz:SKHX", LIVE)
    assert str(flat.volume) == "0" and str(flat.high) == str(flat.low)
    # 20/20 current and fresh (close lag 3s <= 30s target).
    readiness = cohort.runtime.readiness_snapshot()
    assert readiness.latest_closed_5m_open_time_ms == LIVE
    assert len(readiness.ready_market_ids) == 20
    assert cohort.runtime.freshness_within_target(readiness)
    # Scanner exactly once; Strategy exactly 20.
    assert_processed(report, scanner_runs=1, evaluated=20)
    assert cohort.planning.calls.count("SCANNER_L2") == 20
    assert cohort.strategy_evaluations(LIVE) == 20
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is not None


# --------------------------------------------------------------------------
# B. END-INCLUSIVE REST
# --------------------------------------------------------------------------


@async_test
async def test_b_end_inclusive_echo_ignored_and_poisoned_echo_rejected(
    tmp_path: Path,
) -> None:
    cohort = BarrierHarness(tmp_path)
    # Every targeted window is answered end-inclusively: exact T plus the
    # T+5m still-forming echo; for BTC the echo itself is poisoned.
    cohort.grid.echo_poison.add(("BTC", LIVE // SLOT + 1))

    report = await cohort.barrier(LIVE)

    assert len(report.finalized_market_ids) == 20
    assert report.failed_market_ids == ()
    btc = cohort.live_bar("BTC", LIVE)
    truth = payload("BTC", LIVE // SLOT)
    assert str(btc.open) == truth["o"] and str(btc.close) == truth["c"]
    assert str(btc.high) == truth["h"] and str(btc.low) == truth["l"]
    # Only exact T became evidence: no T+5m row exists for any market.
    for coin in COINS:
        assert cohort.closed.last_open(cohort.id_of(coin)) == LIVE


# --------------------------------------------------------------------------
# C. PROVIDER FAILURE
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode",
    ["missing", "duplicate", "conflict"],
)
@async_test
async def test_c_provider_failure_never_fabricates_or_partially_acts(
    tmp_path: Path, mode: str
) -> None:
    cohort = BarrierHarness(tmp_path)
    sp500 = cohort.id_of("xyz:SP500")
    if mode == "missing":
        cohort.grid.omit.setdefault("xyz:SP500", set()).add(LIVE // SLOT)
    elif mode == "duplicate":
        cohort.grid.duplicate.add(("xyz:SP500", LIVE // SLOT))
    else:
        cohort.grid.conflict.add(("xyz:SP500", LIVE // SLOT))

    report = await cohort.barrier(LIVE)

    assert sp500 in report.failed_market_ids
    assert sp500 not in report.finalized_market_ids
    assert len(report.finalized_market_ids) == 19
    # No fabricated row: SP500's durable series still ends at the prior
    # boundary; no synthetic candle, no locally generated flat filler.
    assert cohort.closed.last_open(sp500) == BOUNDARY
    # No partial Scanner/Strategy: the failed required peer defers the whole
    # cohort without poisoning healthy peers' callbacks.
    assert_deferred(report)
    assert report.action.formal_shadow_order_ids == ()
    assert cohort.planning.calls == []
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is None
    assert cohort.strategy_evaluations(LIVE) == 0
    assert cohort.id_of("BTC") not in cohort.runtime.health.failed_markets
    for record in cohort.runtime.health.failure_records.values():
        assert record.stage != "application_callback"
    assert cohort.runtime.health.failure_records[sp500].stage == "cohort_finality"


# --------------------------------------------------------------------------
# D. REGISTRY COHORT TRANSITION
# --------------------------------------------------------------------------


@async_test
async def test_d_registry_switches_only_at_cohort_barrier(tmp_path: Path) -> None:
    cohort = BarrierHarness(tmp_path)
    r1 = cohort.registry.active()
    assert r1 is not None
    r2 = RegistryVersion.create(
        version="r2-successor-20260817",
        created_at=NOW,
        markets=(*cohort.markets, market(HOT_ADD_COIN, MarketLifecycle.WARMING)),
    )
    cohort.registry.stage(r2)
    cohort.registry.request_apply(r2.version)

    # An individual market's T row must NOT activate the pending successor.
    cohort.data.admit_rest_history(
        market=cohort.markets[0],
        snapshot=[payload("BTC", LIVE // SLOT)],
        received_at=cohort.clock.clock(),
    )
    assert cohort.registry.active() is not None
    assert cohort.registry.active().version == r1.version
    assert cohort.registry.pending_version() is not None

    report = await cohort.barrier(LIVE)

    # All actionable T rows bind R1; T's action completed under R1.
    for coin in COINS:
        assert cohort.binding_of(coin, LIVE) == (r1.version, r1.content_hash)
    assert report.registry_version == r1.version
    assert_processed(report, scanner_runs=1, evaluated=20)
    # R2 applies only after the T barrier; T+1 binds and acts under R2.
    assert report.successor_applied
    assert cohort.registry.active() is not None
    assert cohort.registry.active().version == r2.version
    next_report = await cohort.barrier(LIVE + SLOT)
    assert next_report.registry_version == r2.version
    assert_processed(next_report, scanner_runs=1, evaluated=20)
    for coin in COINS:
        assert cohort.binding_of(coin, LIVE + SLOT) == (r2.version, r2.content_hash)
        # No mixed actionable epoch: T stays durably bound to R1 history.
        assert cohort.binding_of(coin, LIVE) == (r1.version, r1.content_hash)


# --------------------------------------------------------------------------
# E. INITIAL LAUNCH
# --------------------------------------------------------------------------


@async_test
async def test_e_initial_launch_transitions_at_barrier_only(tmp_path: Path) -> None:
    lifecycles = {coin: MarketLifecycle.WARMING for coin in COINS}
    cohort = BarrierHarness(tmp_path, lifecycles=lifecycles)
    n = len(COINS)
    observed_active: list[int] = []

    # WARMING -> HISTORY_READY -> SNAPSHOT_READY -> ACTIVE: exactly one
    # Registry pointer transition per barrier, never partial, and no
    # transition boundary is itself a live Scanner boundary.
    for boundary in (LIVE, LIVE + SLOT, LIVE + 2 * SLOT):
        report = await cohort.barrier(boundary)
        active = cohort.registry.active()
        assert active is not None
        counts = sum(1 for m in active.markets if m.lifecycle is MarketLifecycle.ACTIVE)
        observed_active.append(counts)
        assert counts in (0, n)
        assert report.successor_applied
        assert_deferred(report)

    assert observed_active == [0, 0, n]
    active = cohort.registry.active()
    assert active is not None
    assert all(m.lifecycle is MarketLifecycle.ACTIVE for m in active.markets)

    # The next complete boundary is the first actionable ACTIVE boundary.
    first_live = await cohort.barrier(LIVE + 3 * SLOT)
    assert first_live.registry_version == active.version
    assert_processed(first_live, scanner_runs=1, evaluated=n)
    readiness = cohort.runtime.readiness_snapshot()
    assert len(readiness.ready_market_ids) == n


# --------------------------------------------------------------------------
# F. HOT-ADD
# --------------------------------------------------------------------------


@async_test
async def test_f_failed_hot_add_never_pauses_active_cohort(tmp_path: Path) -> None:
    cohort = BarrierHarness(tmp_path)
    r1 = cohort.registry.active()
    assert r1 is not None
    hot_add = market(HOT_ADD_COIN, MarketLifecycle.WARMING)
    r2 = RegistryVersion.create(
        version="r2-hotadd-20260817", created_at=NOW, markets=(*cohort.markets, hot_add)
    )
    cohort.registry.stage(r2)
    cohort.registry.request_apply(r2.version)
    # The hot-add's WARMING finality transport fails at T: the existing
    # ACTIVE cohort must keep processing T regardless.
    cohort.grid.transport_fail[(HOT_ADD_COIN, LIVE // SLOT)] = 1

    report = await cohort.barrier(LIVE)

    assert report.registry_version == r1.version
    assert_processed(report, scanner_runs=1, evaluated=20)
    assert cohort.strategy_evaluations(LIVE) == 20
    assert report.successor_applied
    assert cohort.registry.active() is not None
    assert cohort.registry.active().version == r2.version
    # The failed hot-add is diagnostic state only: it is recorded, and the
    # ACTION gate intersects failures with the ACTIVE required set, so the
    # 20-market ready set and processing authority are unaffected.
    assert hot_add.identity.market_id in cohort.runtime.health.failure_records
    readiness = cohort.runtime.readiness_snapshot()
    assert hot_add.identity.market_id not in readiness.ready_market_ids
    assert len(readiness.ready_market_ids) == 20

    # T+1 uses the successor epoch; the live cohort continues unpaused.
    next_report = await cohort.barrier(LIVE + SLOT)
    assert next_report.registry_version == r2.version
    assert_processed(next_report, scanner_runs=1, evaluated=20)


# --------------------------------------------------------------------------
# G. RESTART / REPLAY
# --------------------------------------------------------------------------


@async_test
async def test_g_restart_replay_no_second_authority_no_retrospective_action(
    tmp_path: Path,
) -> None:
    first = BarrierHarness(tmp_path, subdir="run")
    r1 = first.registry.active()
    assert r1 is not None
    r2 = RegistryVersion.create(
        version="r2-successor-20260817",
        created_at=NOW,
        markets=(*first.markets, market(HOT_ADD_COIN, MarketLifecycle.WARMING)),
    )
    first.registry.stage(r2)
    first.registry.request_apply(r2.version)
    transition = await first.barrier(LIVE)
    assert transition.successor_applied
    after_transition = await first.barrier(LIVE + SLOT)
    assert_processed(after_transition, scanner_runs=1, evaluated=20)
    assert first.planning.calls.count("SCANNER_L2") == 40

    # Restart: fresh process objects over the SAME durable authorities.
    second = BarrierHarness(tmp_path, subdir="run", resume=True)
    assert second.registry.active() is not None
    # Hot-add lifecycle progressed independently after the transition, so the
    # active pointer is r2's lineage successor, never a different authority.
    assert second.registry.active().version.startswith(r2.version)
    # Retained Scanner/Strategy authority for old T dominates replay: the
    # restarted coordinator sees the retained run without re-creating it.
    assert second.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is not None
    assert second.strategy_evaluations(LIVE) == 20

    # A stale old T must not gain retrospective action after restart, and
    # historical rows bound to the older epoch are not treated as corruption.
    second.clock.now_ms = LIVE + SLOT + 70_000
    stale = await second.runtime.process_cohort_boundary(LIVE)
    assert stale.action is None
    assert second.planning.calls == []

    # Replaying the already-durable T+1 wake stays idempotent.
    replay = await second.barrier(LIVE + SLOT)
    assert replay.action is None
    assert second.planning.calls == []

    # T+2 resumes normally under the active R2 lineage epoch (captured before
    # the barrier; the hot-add may progress independently afterwards).
    epoch_before = second.registry.active().version
    resumed = await second.barrier(LIVE + 2 * SLOT)
    assert resumed.registry_version == epoch_before
    assert_processed(resumed, scanner_runs=1, evaluated=20)
    assert second.planning.calls.count("SCANNER_L2") == 20


# --------------------------------------------------------------------------
# H. DEFERRED MAINTENANCE
# --------------------------------------------------------------------------


@async_test
async def test_h_deferred_boundary_stops_new_action_not_maintenance(
    tmp_path: Path,
) -> None:
    cohort = BarrierHarness(tmp_path)
    outcome_ticks: list[int] = []
    original_tick = cohort.outcome.tick

    def spying_tick(*args: Any, **kwargs: Any) -> Any:
        outcome_ticks.append(cohort.clock.now_ms)
        return original_tick(*args, **kwargs)

    cohort.outcome.tick = spying_tick  # type: ignore[method-assign]
    expiry_calls: list[int] = []
    original_expire = cohort.bootstrap._expire_prior_pending

    def spying_expire(current: int) -> None:
        expiry_calls.append(current)
        original_expire(current)

    cohort.bootstrap._expire_prior_pending = spying_expire  # type: ignore[method-assign]
    # One required market is non-actionable at T.
    cohort.grid.omit.setdefault("xyz:SP500", set()).add(LIVE // SLOT)

    report = await cohort.barrier(LIVE)

    # ACTION LANE: no new live authority at all.
    assert_deferred(report)
    assert report.action.formal_shadow_order_ids == ()
    assert cohort.planning.calls == []
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is None
    assert cohort.strategy_evaluations(LIVE) == 0
    # MAINTENANCE LANE: Outcome cadence ticked and retained-Formal
    # reconciliation ran during the defer (after the finality confirmation
    # gap consumed its share of virtual time, still within the boundary).
    assert len(outcome_ticks) == 1
    assert LIVE + SLOT + HOLD_MS <= outcome_ticks[0] < LIVE + 2 * SLOT
    assert expiry_calls == [LIVE]


# --------------------------------------------------------------------------
# I. STARTUP COOLDOWN
# --------------------------------------------------------------------------


@async_test
async def test_i_startup_cooldown_blocks_first_live_burst(tmp_path: Path) -> None:
    cohort = BarrierHarness(tmp_path)
    # Warmup completed 10s before the first completed boundary's wake: the
    # barrier must hold the full 60s cooldown before any live cohort REST
    # burst.  Skipping the earliest possible burst is acceptable pacing.
    cohort.clock.now_ms = LIVE + SLOT + HOLD_MS - 10_000
    cohort.runtime._warmup_completed_monotonic = cohort.clock.monotonic()

    shutdown = asyncio.Event()
    task = asyncio.create_task(cohort.runtime._cohort_barrier_loop(shutdown))
    for _ in range(200_000):
        if cohort.client.calls:
            break
        await asyncio.sleep(0)
    assert cohort.client.calls
    first_call_monotonic = cohort.client.calls[0]
    shutdown.set()
    await asyncio.wait_for(task, timeout=30)

    assert first_call_monotonic >= 60.0
    # Cooldown is operational pacing only: no durable state was added.
    tables = {
        row[0]
        for row in cohort.closed.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "cooldown" not in tables and "barrier_state" not in tables


# --------------------------------------------------------------------------
# J. HARD 60S CEILING
# --------------------------------------------------------------------------


@async_test
async def test_j_stale_boundary_keeps_evidence_but_no_live_action(
    tmp_path: Path,
) -> None:
    cohort = BarrierHarness(tmp_path)
    # Finality completes 70s after close: past the hard action ceiling.
    cohort.clock.now_ms = LIVE + SLOT + 70_000

    report = await cohort.runtime.process_cohort_boundary(LIVE)

    # Provider bars may remain durable as history...
    assert len(report.finalized_market_ids) == 20
    for coin in COINS:
        assert cohort.closed.last_open(cohort.id_of(coin)) == LIVE
    # ...but no newly generated live Scanner/Strategy for stale T.
    assert report.action is None
    assert cohort.planning.calls == []
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is None
    assert cohort.strategy_evaluations(LIVE) == 0
    readiness = cohort.runtime.readiness_snapshot()
    assert readiness.ready_market_ids == ()


# --------------------------------------------------------------------------
# K. DUPLICATE CLOCK WAKE
# --------------------------------------------------------------------------


@async_test
async def test_k_duplicate_clock_wake_never_duplicates_authority(
    tmp_path: Path,
) -> None:
    cohort = BarrierHarness(tmp_path)
    first = await cohort.barrier(LIVE)
    assert_processed(first, scanner_runs=1, evaluated=20)
    pending_after_first = cohort.coordinator.pending_formal_decisions()

    second = await cohort.barrier(LIVE)

    assert second.finalized_market_ids == ()
    assert second.action is None
    assert cohort.planning.calls.count("SCANNER_L2") == 20
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=LIVE) is not None
    assert cohort.strategy_evaluations(LIVE) == 20
    assert cohort.coordinator.pending_formal_decisions() == pending_after_first


# --------------------------------------------------------------------------
# L. FINALITY REPLACEMENT SEAM
# --------------------------------------------------------------------------


class NodeBackedFakeFinality:
    """Deterministic replacement policy: no REST transport at all."""

    def __init__(self) -> None:
        self.authority: MultiAssetDataAuthority | None = None
        self.clock: VirtualClock | None = None
        self.calls: list[tuple[tuple[str, ...], int, int]] = []

    def bind(self, authority: MultiAssetDataAuthority, clock: VirtualClock) -> None:
        self.authority = authority
        self.clock = clock

    async def confirm_cohort_boundary(
        self,
        *,
        markets: Sequence[RegistryMarket],
        boundary_open_time_ms: int,
        deadline_ms: int,
    ) -> CohortFinalityResult:
        self.calls.append(
            (tuple(m.identity.coin for m in markets), boundary_open_time_ms, deadline_ms)
        )
        assert self.authority is not None and self.clock is not None
        finalized: list[ClosedBar] = []
        for item in markets:
            finalized.extend(
                self.authority.admit_rest_history(
                    market=item,
                    snapshot=[payload(item.identity.coin, boundary_open_time_ms // SLOT)],
                    received_at=self.clock.clock(),
                )
            )
        return CohortFinalityResult(
            boundary_open_time_ms=boundary_open_time_ms,
            finalized=tuple(finalized),
            failures=(),
        )


@async_test
async def test_l_finality_policy_replaceable_without_architecture_rewrite(
    tmp_path: Path,
) -> None:
    fake = NodeBackedFakeFinality()
    harness = BarrierHarness(tmp_path, cohort_finality=fake)
    fake.bind(harness.data, harness.clock)

    report = await harness.barrier(LIVE)

    # Clock Barrier -> Data admission -> Registry barrier -> Bootstrap ->
    # Scanner/Strategy ran end to end with ZERO REST transport: Bootstrap,
    # Registry, Scanner, and Strategy never learned the finality source.
    assert harness.client.calls == []
    assert fake.calls
    markets_arg, boundary_arg, deadline_arg = fake.calls[0]
    assert len(markets_arg) == 20
    assert boundary_arg == LIVE
    assert deadline_arg == LIVE + SLOT + 60_000
    assert len(report.finalized_market_ids) == 20
    assert_processed(report, scanner_runs=1, evaluated=20)
    assert harness.strategy_evaluations(LIVE) == 20
    assert harness.planning.calls.count("SCANNER_L2") == 20


@async_test
async def test_barrier_does_not_hardcode_market_count(tmp_path: Path) -> None:
    three = ("BTC", "ETH", "xyz:SKHX")
    cohort = BarrierHarness(tmp_path, coins=three)
    report = await cohort.barrier(LIVE)
    assert len(report.finalized_market_ids) == 3
    assert report.failed_market_ids == ()
    assert_processed(report, scanner_runs=1, evaluated=3)
    assert cohort.planning.calls.count("SCANNER_L2") == 3
