"""PHASE 1 frozen contract: Strategy ledger restore across Registry epochs.

Packet section 12 and attacks X, Y, Z, AQ.  A retained StrategyEvaluation for
boundary T dominates across Registry epochs: after R1->R2 and an immediate
process restart with zero R2 evaluations, evaluating T+1 under R2 must restore
the exact output ledger of T and behave like an uninterrupted run.  Unknown,
wrong-hash, or duplicated retained authority fails closed; a boundary already
authoritative under a predecessor epoch is never re-evaluated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
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
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.registry import (
    CohortWitness,
    MarketRegistryManager,
)
from trader_assist_v0.multi_asset_shadow.runtime import (
    BoundaryMode,
    RuntimeReadinessSnapshot,
)
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

NOW = datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
RELEASE_SHA = "1" * 40
COUNT = 64
T = (COUNT - 1) * 300_000
T_NEXT = COUNT * 300_000


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
        self.failed: set[str] = set()

    def readiness_snapshot(self) -> RuntimeReadinessSnapshot:
        active = self.registry.active()
        assert active is not None
        ready = tuple(
            market.identity.market_id
            for market in active.markets
            if self.connected
            and market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id not in self.failed
            and self.closed_store.last_open(market.identity.market_id) == self.latest_open_ms
        )
        return RuntimeReadinessSnapshot.create(
            registry_version=active.version,
            registry_content_hash=active.content_hash,
            data_ready=self.connected,
            ready_market_ids=ready,
            failed_market_ids=tuple(self.failed),
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
    start = index * 300_000
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


class World:
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
            received_at=datetime.fromtimestamp((COUNT * 300_000 + 1_000) / 1000, UTC),
        )
        self.evidence = EvidenceStore(root / "evidence.sqlite")
        self.outbox = EvidenceOutbox(self.evidence)
        self.outcome_adapter = EvidenceOutcomeAdapter(self.evidence)
        self.outcome = OutcomeEngine(provider=FakeOneMinuteProvider(), sink=self.outcome_adapter)
        self.readiness = MutableReadiness(
            registry=self.registry, closed_store=self.closed_store
        )
        self.coordinator = self._coordinator()

    def _coordinator(self) -> MultiAssetShadowCoordinator:
        return MultiAssetShadowCoordinator(
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

    def admit(self, index: int, *, final: bool = False) -> None:
        self.data.admit_rest_history(
            market=self.market,
            snapshot=[_payload(index, final=final)],
            received_at=datetime.fromtimestamp(((index + 1) * 300_000 + 1_000) / 1000, UTC),
        )
        self.readiness.latest_open_ms = index * 300_000

    def switch_registry(self, version: str) -> None:
        active = self.registry.active()
        assert active is not None
        successor = self.registry.successor(
            version=version, now=NOW, update_market=self.market.model_copy(
                update={"metadata_hash": sha256_hex(version.encode())}
            )
        )
        self.registry.request_apply(successor.version)
        witness = CohortWitness.create(
            boundary_open_time_ms=T,
            base_registry_version=active.version,
            base_registry_hash=active.content_hash,
            expected_successor_version=successor.version,
            expected_successor_hash=successor.content_hash,
            required_evidence_market_ids=frozenset({self.market.identity.market_id}),
            issuer="SINGLE_OWNER_5M_COHORT_BARRIER",
        )
        assert self.registry.apply_witness(
            witness, evidence_authority=self.data
        )


def test_r1_t_r2_crash_restart_t1_equals_uninterrupted_run(tmp_path: Path) -> None:
    control = World(tmp_path / "control")
    control_t = control.coordinator.evaluate_finalized_market(
        market_id=control.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    control.admit(COUNT, final=True)
    control_t1 = control.coordinator.evaluate_finalized_market(
        market_id=control.market.identity.market_id,
        source_open_time_ms=T_NEXT,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )

    crashed = World(tmp_path / "crashed")
    crashed_t = crashed.coordinator.evaluate_finalized_market(
        market_id=crashed.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    assert crashed_t.output_ledger_hash == control_t.output_ledger_hash
    crashed.switch_registry("registry-2")
    # PROCESS CRASH: zero StrategyEvaluations exist under registry-2.
    crashed.coordinator = crashed._coordinator()
    crashed.admit(COUNT, final=True)
    crashed_t1 = crashed.coordinator.evaluate_finalized_market(
        market_id=crashed.market.identity.market_id,
        source_open_time_ms=T_NEXT,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    assert crashed_t1.input_ledger_hash == control_t1.input_ledger_hash
    assert crashed_t1.output_ledger_hash == control_t1.output_ledger_hash
    assert crashed_t1.result.ledger == control_t1.result.ledger
    assert crashed.coordinator._ledgers == control.coordinator._ledgers


def test_predecessor_evaluation_is_recognized_and_not_reevaluated(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    world.switch_registry("registry-2")
    world.coordinator = world._coordinator()
    assert world.coordinator.has_retained_strategy_evaluation(
        market_id=world.market.identity.market_id, source_open_time_ms=T
    )
    world.admit(COUNT, final=True)
    missing = world.coordinator.strategy_recovery_boundaries(
        market_id=world.market.identity.market_id, current_source_open_time_ms=T_NEXT
    )
    assert missing == (T_NEXT,)
    with pytest.raises(IntegrationError):
        world.coordinator.evaluate_finalized_market(
            market_id=world.market.identity.market_id,
            source_open_time_ms=T,
            evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
        )


def test_unknown_referenced_registry_version_fails_closed(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    world.switch_registry("registry-2")
    # The predecessor version file disappears: the retained evaluation now
    # references an unknown Registry epoch and must fail closed on restore.
    (tmp_path / "registry" / "versions" / "registry-1.json").unlink()
    with pytest.raises(IntegrationError):
        world._coordinator()


def test_wrong_predecessor_hash_fails_closed(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.coordinator.evaluate_finalized_market(
        market_id=world.market.identity.market_id,
        source_open_time_ms=T,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    world.switch_registry("registry-2")
    path = tmp_path / "registry" / "versions" / "registry-1.json"
    import json

    from trader_assist_v0.contracts.common import canonical_json_bytes

    parsed = json.loads(path.read_text(encoding="utf-8"))
    parsed["created_at"] = "1999-01-01T00:00:00Z"
    path.write_bytes(canonical_json_bytes(parsed))
    with pytest.raises(IntegrationError):
        world._coordinator()
