"""Whole-cohort application gate proof over the real production composition.

Runtime -> Bootstrap -> Coordinator -> Scanner -> Strategy, exercised through
``MultiAssetProductionBootstrap.process_boundary`` exactly as the production
callback drives it.  CASE A proves a 19/20 cohort can never produce partial
Scanner or Strategy authority; CASE B proves the exact 20-market cohort is
processed as one whole with no duplicate authority.  The LAYER 2 precedence
matrix proves FINAL INVARIANT B: an observable integrity contradiction always
raises BootstrapIntegrityError, dominating every operational DEFER condition.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.bootstrap import (
    BootstrapIntegrityError,
    BoundaryDisposition,
    MultiAssetProductionBootstrap,
)
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    MultiAssetShadowCoordinator,
    PublicL2Snapshot,
    ScannerPublicSnapshot,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import OneMinuteBar, OutcomeEngine
from trader_assist_v0.multi_asset_shadow.planning import CostModel, PublicBbo
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import (
    BoundaryMode,
    MultiAssetPublicRuntime,
    RuntimeReadinessSnapshot,
)
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

NOW = datetime(2026, 8, 17, 0, 0, tzinfo=UTC)
RELEASE_SHA = "1" * 40
BARS = 64
SLOT = 300_000
COINS = (
    "BTC", "ETH", "HYPE", "SOL", "XRP",
    "xyz:SKHX", "xyz:MU", "xyz:SNDK", "xyz:XYZ100", "xyz:SP500",
    "xyz:CL", "xyz:DRAM", "xyz:SPCX", "xyz:SILVER", "xyz:NVDA",
    "xyz:SMSN", "xyz:EWY", "xyz:GOLD", "xyz:TSLA", "xyz:GOOGL",
)
BOUNDARY = (BARS - 1) * SLOT


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
    start = index * SLOT
    group = index // 3
    return {
        "i": "5m",
        "s": coin,
        "t": start,
        "T": start + SLOT - 1,
        "o": "105",
        "h": "110" if group in {15, 17, 19} else "106",
        "l": "100" if group in {14, 16, 18} else "104",
        "c": "105",
        "v": "10",
    }


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


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
        assert str(side) == "LONG"
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


class Cohort:
    def __init__(
        self,
        tmp_path: Path,
        *,
        omit_boundary_for: str | None = None,
        lifecycles: dict[str, MarketLifecycle] | None = None,
    ) -> None:
        self.registry = MarketRegistryManager(
            tmp_path / "registry", metadata_validator=lambda _: True
        )
        self.markets = tuple(
            market(
                coin,
                lifecycle=lifecycles[coin] if lifecycles is not None else MarketLifecycle.ACTIVE,
            )
            for coin in COINS
        )
        version = RegistryVersion.create(
            version="registry-cohort-20260817", created_at=NOW, markets=self.markets
        )
        self.registry.stage(version)
        self.registry.request_apply(version.version)
        self.closed = ClosedBarStore(tmp_path / "closed.sqlite")
        self.data = MultiAssetDataAuthority(store=self.closed, registry=self.registry)
        for item in self.markets:
            count = BARS - 1 if item.identity.coin == omit_boundary_for else BARS
            self.data.admit_rest_history(
                market=item,
                snapshot=[payload(item.identity.coin, index) for index in range(count)],
                received_at=datetime.fromtimestamp((BOUNDARY + SLOT + 1_000) / 1000, UTC),
            )
        self.evidence = EvidenceStore(tmp_path / "evidence.sqlite")
        self.outbox = EvidenceOutbox(self.evidence)
        self.outcome_adapter = EvidenceOutcomeAdapter(self.evidence)
        self.outcome = OutcomeEngine(provider=OneMinuteProvider(), sink=self.outcome_adapter)
        self.planning = PlanningData()

        self.now_ms = BOUNDARY + SLOT + 1_000

        def clock() -> datetime:
            return datetime.fromtimestamp(self.now_ms / 1000, UTC)

        self.runtime = MultiAssetPublicRuntime(
            registry=self.registry,
            authority=self.data,
            client=object(),  # type: ignore[arg-type]
            clock=clock,
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
            clock=clock,
            sleep=lambda _: asyncio.sleep(0),
        )

    def id_of(self, coin: str) -> str:
        return next(m.identity.market_id for m in self.markets if m.identity.coin == coin)


async def drive(cohort: Cohort) -> object:
    return await cohort.bootstrap.process_boundary(BOUNDARY, BoundaryMode.LIVE_ACTIONABLE)


@async_test
async def test_case_a_missing_market_boundary_defers_whole_cohort(tmp_path: Path) -> None:
    cohort = Cohort(tmp_path, omit_boundary_for="xyz:SP500")
    report = await drive(cohort)
    assert report.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.scanner_run_count == 0
    assert report.evaluated_market_ids == ()
    assert report.formal_shadow_order_ids == ()
    assert cohort.planning.calls == []
    readiness = cohort.runtime.readiness_snapshot()
    assert len(readiness.ready_market_ids) == 19
    assert cohort.id_of("xyz:SP500") not in readiness.ready_market_ids


@async_test
async def test_failed_peer_defers_whole_cohort_no_callback_cascade(
    tmp_path: Path,
) -> None:
    """CASE A (failed peer): expected cohort non-readiness defers through the
    real Runtime -> Bootstrap callback path without cascading an application
    failure onto the healthy triggering market."""
    cohort = Cohort(tmp_path)
    sp500_id = cohort.id_of("xyz:SP500")
    btc_id = cohort.id_of("BTC")
    cohort.runtime.health.failed_markets.add(sp500_id)

    # Real production wiring: Runtime dispatches the finalized healthy bar to
    # the Bootstrap application callback exactly as
    # ThreeSetupProductionApplication wires on_finalized_5m.
    cohort.runtime.on_finalized_5m = cohort.bootstrap.on_finalized_5m
    bar = next(
        closed for closed in cohort.data.store.bars(btc_id)
        if closed.open_time_ms == BOUNDARY
    )
    report = await cohort.runtime._notify_finalized(bar, BoundaryMode.LIVE_ACTIONABLE)

    assert report.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.scanner_run_count == 0
    assert report.evaluated_market_ids == ()
    assert report.formal_shadow_order_ids == ()
    assert cohort.planning.calls == []
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=BOUNDARY) is None
    # No cascade: the healthy triggering market stays healthy and unrecorded.
    assert btc_id not in cohort.runtime.health.failed_markets
    assert btc_id not in cohort.runtime.health.failure_records
    assert sp500_id in cohort.runtime.health.failed_markets

    # True integrity failures still raise: a boundary that contradicts the
    # runtime's authoritative latest closed boundary.
    with pytest.raises(BootstrapIntegrityError):
        await cohort.bootstrap.process_boundary(BOUNDARY - SLOT, BoundaryMode.LIVE_ACTIONABLE)


@async_test
async def test_case_b_exact_cohort_scans_once_strategies_all_no_duplicates(
    tmp_path: Path,
) -> None:
    cohort = Cohort(tmp_path)
    report = await drive(cohort)
    assert report.disposition is BoundaryDisposition.PROCESSED
    assert report.scanner_run_count == 1
    assert len(report.evaluated_market_ids) == 20
    assert len(set(report.evaluated_market_ids)) == 20
    # First Scanner processing consumed the full cohort before anything else.
    assert cohort.planning.calls[:20] == ["SCANNER_L2"] * 20

    # A replayed boundary reuses the retained Scanner run and retained
    # Strategy evaluations: no second scan, no duplicate authority.
    replay = await drive(cohort)
    assert replay.disposition is BoundaryDisposition.PROCESSED
    assert replay.scanner_run_count == 0
    assert len(set(replay.evaluated_market_ids)) == 20
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=BOUNDARY) is not None
    for item in cohort.markets:
        assert cohort.coordinator.has_retained_strategy_evaluation(
            market_id=item.identity.market_id, source_open_time_ms=BOUNDARY
        )
    assert cohort.planning.calls.count("SCANNER_L2") == 20


# --------------------------------------------------------------------------
# LAYER 2 -- Bootstrap gate precedence matrix (FINAL INVARIANT B).
#
# INTEGRITY ERROR > OPERATIONAL DEFER > ACTION: an observable authority
# contradiction must always raise, even when an operational condition (failed
# peer, zero-ACTIVE launch, incomplete readiness) would otherwise defer.
# --------------------------------------------------------------------------

WARMING_LAUNCH: dict[str, MarketLifecycle] = {
    coin: MarketLifecycle.WARMING for coin in COINS
}


def tamper_boundary_binding(cohort: Cohort, coin: str) -> None:
    cohort.data.store.connection.execute(
        "UPDATE closed_bars SET registry_version = 'tampered-boundary-authority' "
        "WHERE market_id = ? AND interval = '5m' AND open_time_ms = ?",
        (cohort.id_of(coin), BOUNDARY),
    )
    cohort.data.store.connection.commit()


@async_test
async def test_precedence_failed_peer_with_present_wrong_bound_row_raises(
    tmp_path: Path,
) -> None:
    """Failed peer + PRESENT retained row bound to the wrong Registry authority
    raises BootstrapIntegrityError: integrity dominates the failed-peer defer."""
    cohort = Cohort(tmp_path)
    cohort.runtime.health.failed_markets.add(cohort.id_of("xyz:SP500"))
    tamper_boundary_binding(cohort, "BTC")
    with pytest.raises(BootstrapIntegrityError):
        await drive(cohort)
    assert cohort.planning.calls == []
    assert cohort.coordinator.retained_scanner_run(boundary_open_time_ms=BOUNDARY) is None

    # Control pair: the identical failed peer with coherent retained authority
    # defers operationally instead of raising.
    control_path = tmp_path / "control"
    control_path.mkdir()
    control = Cohort(control_path)
    control.runtime.health.failed_markets.add(control.id_of("xyz:SP500"))
    report = await drive(control)
    assert report.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.scanner_run_count == 0


@async_test
async def test_precedence_zero_active_initial_launch_defers(tmp_path: Path) -> None:
    """A coherent zero-ACTIVE Initial-Launch cohort (all PRE_ACTIVE) defers."""
    cohort = Cohort(tmp_path, lifecycles=WARMING_LAUNCH)
    report = await drive(cohort)
    assert report.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.scanner_run_count == 0
    assert report.evaluated_market_ids == ()
    assert cohort.planning.calls == []


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("registry_version", "stale-registry-version-20260816"),
        ("registry_content_hash", "e" * 64),
    ],
)
@async_test
async def test_precedence_zero_active_registry_readiness_mismatch_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, wrong_value: str
) -> None:
    """Zero ACTIVE + readiness Registry identity mismatch raises even though a
    coherent zero-ACTIVE launch would defer."""
    cohort = Cohort(tmp_path, lifecycles=WARMING_LAUNCH)
    snapshot = cohort.runtime.readiness_snapshot()
    fields = {
        "registry_version": snapshot.registry_version,
        "registry_content_hash": snapshot.registry_content_hash,
    }
    fields[field] = wrong_value
    tampered = RuntimeReadinessSnapshot.create(
        registry_version=fields["registry_version"],
        registry_content_hash=fields["registry_content_hash"],
        data_ready=snapshot.data_ready,
        ready_market_ids=snapshot.ready_market_ids,
        failed_market_ids=snapshot.failed_market_ids,
        latest_closed_5m_open_time_ms=snapshot.latest_closed_5m_open_time_ms,
        observed_at_ms=snapshot.observed_at_ms,
    )
    monkeypatch.setattr(cohort.runtime, "readiness_snapshot", lambda: tampered)
    with pytest.raises(BootstrapIntegrityError):
        await drive(cohort)
    assert cohort.planning.calls == []


@async_test
async def test_precedence_zero_active_boundary_contradiction_raises(
    tmp_path: Path,
) -> None:
    """Zero ACTIVE + requested boundary contradicting the runtime's
    authoritative latest closed boundary raises."""
    cohort = Cohort(tmp_path, lifecycles=WARMING_LAUNCH)
    with pytest.raises(BootstrapIntegrityError):
        await cohort.bootstrap.process_boundary(BOUNDARY - SLOT, BoundaryMode.LIVE_ACTIONABLE)
    assert cohort.planning.calls == []


@async_test
async def test_precedence_incomplete_ready_set_with_present_rows_defers(
    tmp_path: Path,
) -> None:
    """All required boundary rows PRESENT and bound correctly, but the observed
    boundary is older than the hard action ceiling: readiness exposes an empty
    ready set and the boundary defers operationally."""
    cohort = Cohort(tmp_path)
    cohort.now_ms = BOUNDARY + SLOT + 61_000
    snapshot = cohort.runtime.readiness_snapshot()
    assert snapshot.latest_closed_5m_open_time_ms == BOUNDARY
    assert snapshot.ready_market_ids == ()
    report = await drive(cohort)
    assert report.disposition is BoundaryDisposition.DEFERRED_WAITING_FOR_PEERS
    assert report.scanner_run_count == 0
    assert cohort.planning.calls == []
