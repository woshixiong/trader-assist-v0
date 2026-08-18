"""PHASE 1 frozen contract: maintenance continues while action is deferred.

Packet section 20 and attack AH.  ACTION DEFERRED never defers MAINTENANCE:
when the whole cohort cannot act at T, the Barrier still runs the Bootstrap
maintenance lane, which expires prior-boundary pending Formal decisions,
reconciles retained strictly-prior Strategy checkpoints as context, and
advances Outcome cadence -- while NEW Scanner / Strategy / Formal authority
for the deferred boundary itself remains exactly zero.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.bootstrap import MultiAssetProductionBootstrap
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    IntegrationError,
    MultiAssetShadowCoordinator,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import OutcomeEngine
from trader_assist_v0.multi_asset_shadow.planning import CostModel, PlanningError
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

NOW = datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
RELEASE_SHA = "1" * 40
COUNT = 64
FIVE_MINUTES_MS = 300_000
T = (COUNT - 1) * FIVE_MINUTES_MS
T_NEXT = T + FIVE_MINUTES_MS


class FakeOneMinuteProvider:
    def subscribe_1m(self, *, market_id: str) -> None:
        return None

    def unsubscribe_1m(self, *, market_id: str) -> None:
        return None

    def backfill_1m(self, *, market_id: str, start_ms: int, end_ms: int) -> tuple[()]:
        return ()


class FakePlanningData:
    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> None:
        return None

    def fetch_l2(self, *, market: RegistryMarket, side: object, bbo: object) -> None:
        return None

    def fetch_scanner_snapshot(
        self, *, market: RegistryMarket, now_ms: int, btc_returns: object
    ) -> None:
        return None


class MutableReadiness:
    def __init__(self, *, registry: MarketRegistryManager, closed_store: ClosedBarStore) -> None:
        self.registry = registry
        self.closed_store = closed_store
        self.latest_open_ms = T
        self.connected = True

    def readiness_snapshot(self):  # type: ignore[no-untyped-def]
        from trader_assist_v0.multi_asset_shadow.runtime import RuntimeReadinessSnapshot

        active = self.registry.active()
        assert active is not None
        ready = tuple(
            market.identity.market_id
            for market in active.markets
            if self.connected
            and market.lifecycle is MarketLifecycle.ACTIVE
            and self.closed_store.last_open(market.identity.market_id) == self.latest_open_ms
        )
        return RuntimeReadinessSnapshot.create(
            registry_version=active.version,
            registry_content_hash=active.content_hash,
            data_ready=self.connected,
            ready_market_ids=ready,
            failed_market_ids=(),
            latest_closed_5m_open_time_ms=self.latest_open_ms,
            observed_at_ms=self.latest_open_ms + 300_001,
        )


def _market() -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(b"BTC-metadata"),
    )


def _payload(index: int, *, final: bool) -> dict[str, object]:
    start = index * FIVE_MINUTES_MS
    group = index // 3
    payload: dict[str, object] = {
        "i": "5m",
        "s": "BTC",
        "t": start,
        "T": start + 299_999,
        "o": "105",
        "h": "110" if group in {15, 17, 19} else "106",
        "l": "100" if group in {14, 16, 18} else "104",
        "c": "105",
        "v": "10",
    }
    if final:
        payload.update({"o": "102.5", "h": "106", "l": "99.8", "c": "105.5"})
    return payload


class MaintenanceWorld:
    """One ACTIVE market, retained evidence, and the Bootstrap application."""

    def __init__(self, root: Path) -> None:
        self.market = _market()
        self.registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
        version = RegistryVersion.create(
            version="registry-1", created_at=NOW, markets=(self.market,)
        )
        self.registry.stage(version)
        self.registry.request_apply(version.version)
        self.closed_store = ClosedBarStore(root / "closed.sqlite")
        self.data = MultiAssetDataAuthority(store=self.closed_store, registry=self.registry)
        self.data.admit_rest_history(
            market=self.market,
            snapshot=[_payload(index, final=index == COUNT - 1) for index in range(COUNT)],
            received_at=datetime.fromtimestamp((COUNT * FIVE_MINUTES_MS + 1_000) / 1000, UTC),
        )
        self.evidence = EvidenceStore(root / "evidence.sqlite")
        self.outbox = EvidenceOutbox(self.evidence)
        self.outcome_adapter = EvidenceOutcomeAdapter(self.evidence)
        self.outcome = OutcomeEngine(provider=FakeOneMinuteProvider(), sink=self.outcome_adapter)
        self.readiness = MutableReadiness(
            registry=self.registry, closed_store=self.closed_store
        )
        self.coordinator = MultiAssetShadowCoordinator(
            registry=self.registry,
            data_authority=self.data,
            evidence=self.evidence,
            outbox=self.outbox,
            outcome_engine=self.outcome,
            outcome_adapter=self.outcome_adapter,
            planning_data=FakePlanningData(),  # type: ignore[arg-type]
            cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
            release_sha=RELEASE_SHA,
            runtime_readiness=self.readiness,
        )
        self.outcome_ticks = 0
        self.scanner_calls = 0
        original_tick = self.outcome.tick

        def counted_tick(*, now_ms: int):  # type: ignore[no-untyped-def]
            self.outcome_ticks += 1
            return original_tick(now_ms=now_ms)

        self.outcome.tick = counted_tick  # type: ignore[method-assign]

        def guarded_scan(*args, **kwargs):  # type: ignore[no-untyped-def]
            self.scanner_calls += 1
            raise AssertionError("maintenance lane must not create Scanner authority")

        self.coordinator.scan_finalized = guarded_scan  # type: ignore[method-assign]

        def guarded_retained(*args, **kwargs):  # type: ignore[no-untyped-def]
            self.scanner_calls += 1
            raise AssertionError("maintenance lane must not create Scanner authority")

        self.coordinator.retained_scanner_run = guarded_retained  # type: ignore[method-assign]
        self.application = MultiAssetProductionBootstrap(
            registry=self.registry,
            data_authority=self.data,
            evidence=self.evidence,
            outbox=self.outbox,
            outcome_adapter=self.outcome_adapter,
            outcome_engine=self.outcome,
            planning_data=FakePlanningData(),  # type: ignore[arg-type]
            coordinator=self.coordinator,
            runtime=None,  # type: ignore[arg-type]
            clock=lambda: datetime.fromtimestamp(
                (self.readiness.latest_open_ms + 305_000) / 1000, UTC
            ),
            sleep=asyncio.sleep,
        )

    def admit(self, index: int, *, final: bool = False) -> None:
        self.data.admit_rest_history(
            market=self.market,
            snapshot=[_payload(index, final=final)],
            received_at=datetime.fromtimestamp(((index + 1) * FIVE_MINUTES_MS + 1_000) / 1000, UTC),
        )
        self.readiness.latest_open_ms = index * FIVE_MINUTES_MS

    def strategy_evaluation_count(self) -> int:
        return int(
            self.evidence._connection.execute(
                "SELECT COUNT(*) FROM immutable_records WHERE record_type='strategy_evaluation'"
            ).fetchone()[0]
        )

    def strategy_evaluation_boundaries(self) -> tuple[int, ...]:
        rows = self.evidence._connection.execute(
            "SELECT record_id FROM immutable_records WHERE record_type='strategy_evaluation'"
        ).fetchall()
        boundaries = []
        for row in rows:
            record = self.evidence.get(str(row[0]))
            boundaries.append(int(record.payload["source_open_time_ms"]))
        return tuple(sorted(boundaries))


def test_deferred_boundary_expires_pending_formal_and_advances_outcomes(
    tmp_path: Path,
) -> None:
    world = MaintenanceWorld(tmp_path)
    receipt = world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    assert receipt.evaluation_id
    pending = world.coordinator.pending_formal_decisions()
    assert len(pending) == 1
    assert pending[0].source_open_time_ms == T
    world.admit(COUNT, final=True)
    ticks_before = world.outcome_ticks

    # Whole-cohort action at T_NEXT is deferred: the Barrier runs only the
    # maintenance lane.
    asyncio.run(world.application.on_maintenance_5m(T_NEXT))

    assert world.coordinator.pending_formal_decisions() == ()
    assert world.outcome_ticks > ticks_before
    assert world.scanner_calls == 0
    assert world.strategy_evaluation_count() == 1
    assert world.strategy_evaluation_boundaries() == (T,)


def test_deferred_boundary_never_reconciles_itself_only_strictly_prior(
    tmp_path: Path,
) -> None:
    world = MaintenanceWorld(tmp_path)
    world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        source_open_time_ms=T - FIVE_MINUTES_MS,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    assert world.strategy_evaluation_count() == 1

    # T is the deferred boundary itself: maintenance must not evaluate it.
    asyncio.run(world.application.on_maintenance_5m(T))
    assert world.strategy_evaluation_count() == 1
    assert world.strategy_evaluation_boundaries() == (T - FIVE_MINUTES_MS,)

    # At the next boundary T is strictly prior: it reconciles as context only.
    asyncio.run(world.application.on_maintenance_5m(T_NEXT))
    assert world.strategy_evaluation_count() == 2
    boundaries = world.strategy_evaluation_boundaries()
    assert boundaries == (T - FIVE_MINUTES_MS, T)
    rows = world.evidence._connection.execute(
        "SELECT record_id FROM immutable_records WHERE record_type='strategy_evaluation'"
    ).fetchall()
    for row in rows:
        record = world.evidence.get(str(row[0]))
        if record.payload["source_open_time_ms"] == T:
            assert record.payload["evaluation_mode"] == BoundaryMode.RECOVERY_CONTEXT_ONLY.value


def _maintenance_runtime(world: MaintenanceWorld) -> MultiAssetPublicRuntime:
    runtime = MultiAssetPublicRuntime(
        registry=world.registry,
        authority=world.data,
        client=object(),  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp((T + FIVE_MINUTES_MS + 5_000) / 1000, UTC),
    )
    runtime.on_maintenance_5m = world.application.on_maintenance_5m
    return runtime


def test_maintenance_unknown_retained_registry_epoch_fails_closed(
    tmp_path: Path,
) -> None:
    world = MaintenanceWorld(tmp_path)
    world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    active = world.registry.active()
    assert active is not None
    registry_two = world.registry.successor(
        version="registry-2",
        now=NOW,
        update_market=world.market.model_copy(update={"metadata_hash": sha256_hex(b"r2")}),
    )
    world.registry.request_apply(registry_two.version)
    witness = world.registry._issue_cohort_witness(
        boundary_open_time_ms=T,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
        expected_successor_version=registry_two.version,
        expected_successor_hash=registry_two.content_hash,
        required_evidence_market_ids=frozenset({world.market.identity.market_id}),
    )
    world.registry.apply_witness(witness, evidence_authority=world.data)
    active = world.registry.active()
    assert active is not None
    world.data.admit_rest_history(
        market=active.markets[0],
        snapshot=[_payload(COUNT, final=True)],
        received_at=datetime.fromtimestamp((T_NEXT + FIVE_MINUTES_MS + 1_000) / 1000, UTC),
    )
    registry_three = world.registry.successor(
        version="registry-3",
        now=NOW,
        update_market=active.markets[0].model_copy(update={"metadata_hash": sha256_hex(b"r3")}),
    )
    world.registry.request_apply(registry_three.version)
    (tmp_path / "registry" / "versions" / "registry-1.json").unlink()

    runtime = MultiAssetPublicRuntime(
        registry=world.registry,
        authority=world.data,
        client=object(),  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp((T_NEXT + FIVE_MINUTES_MS + 5_000) / 1000, UTC),
    )
    runtime.on_maintenance_5m = world.application.on_maintenance_5m
    with pytest.raises(IntegrationError, match="unknown Registry epoch"):
        asyncio.run(runtime.process_cohort_boundary(T_NEXT))

    assert runtime._integrity_failed is True
    assert world.registry.active() is not None
    assert world.registry.active().version == "registry-2"
    runtime.on_maintenance_5m = lambda _: None
    runtime.health.data_ready = True
    asyncio.run(runtime.process_cohort_boundary(T_NEXT))
    assert world.registry.active() is not None
    assert world.registry.active().version == "registry-2"


@pytest.mark.parametrize(
    "reason",
    (
        "unknown retained Registry epoch",
        "duplicate retained Strategy boundary authority",
    ),
)
def test_maintenance_authority_error_fails_closed_before_successor(
    tmp_path: Path, reason: str
) -> None:
    world = MaintenanceWorld(tmp_path)
    runtime = _maintenance_runtime(world)
    successor = world.registry.successor(
        version="registry-2",
        now=NOW,
        update_market=world.market.model_copy(update={"metadata_hash": sha256_hex(b"r2")}),
    )
    world.registry.request_apply(successor.version)

    world.coordinator.strategy_recovery_boundaries = (  # type: ignore[method-assign]
        lambda **_: (T - FIVE_MINUTES_MS,)
    )

    def authority_conflict(**_: object) -> None:
        raise IntegrationError(reason)

    world.coordinator.evaluate_finalized_market = authority_conflict  # type: ignore[method-assign]

    with pytest.raises(IntegrationError, match=reason):
        asyncio.run(runtime.process_cohort_boundary(T))

    assert runtime._integrity_failed is True
    assert len(runtime.health.callback_failures) == 1
    assert world.registry.active() is not None
    assert world.registry.active().version == "registry-1"

    # A later apparent maintenance success cannot clear the process-local
    # integrity state or activate the pending Registry successor.
    runtime.on_maintenance_5m = lambda _: None
    runtime.health.data_ready = True
    asyncio.run(runtime.process_cohort_boundary(T))
    assert world.registry.active() is not None
    assert world.registry.active().version == "registry-1"


def test_maintenance_operational_planning_error_stays_market_local(tmp_path: Path) -> None:
    world = MaintenanceWorld(tmp_path)
    ticks_before = world.outcome_ticks
    world.coordinator.strategy_recovery_boundaries = (  # type: ignore[method-assign]
        lambda **_: (T - FIVE_MINUTES_MS,)
    )

    def operational_failure(**_: object) -> None:
        raise PlanningError("temporary public planning failure")

    world.coordinator.evaluate_finalized_market = operational_failure  # type: ignore[method-assign]
    asyncio.run(world.application.on_maintenance_5m(T))

    assert world.outcome_ticks > ticks_before


def test_maintenance_cancellation_propagates_without_integrity_failure(tmp_path: Path) -> None:
    world = MaintenanceWorld(tmp_path)
    runtime = _maintenance_runtime(world)

    async def cancelled(_: int) -> None:
        raise asyncio.CancelledError()

    runtime.on_maintenance_5m = cancelled
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(runtime._run_maintenance(T))
    assert runtime._integrity_failed is False
    assert runtime.health.callback_failures == []


def test_compose_wires_single_maintenance_lane(tmp_path: Path) -> None:
    market = _market()
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="registry-1", created_at=NOW, markets=(market,))
    registry.stage(version)
    registry.request_apply(version.version)
    data = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )

    class ExternalClient:
        pass

    application = MultiAssetProductionBootstrap.compose(
        registry=registry,
        data_authority=data,
        public_client=ExternalClient(),  # type: ignore[arg-type]
        evidence_db_path=tmp_path / "evidence.sqlite",
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=RELEASE_SHA,
    )
    # The Barrier owns both wakes: one live application wake plus exactly one
    # maintenance lane, both bound to this application and nothing else.
    assert application.runtime.on_finalized_5m == application.on_finalized_5m
    assert application.runtime.on_maintenance_5m == application.on_maintenance_5m
    application.evidence.close()
