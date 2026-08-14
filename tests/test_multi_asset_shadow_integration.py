from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.correlation_engine import CorrelationEngineError
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import (
    CorrelationMarketMetrics,
    CorrelationResearchAdapter,
    EvaluationReceipt,
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    FormalizationArtifacts,
    IntegrationError,
    MultiAssetShadowCoordinator,
    PublicL2Snapshot,
    ScannerPublicSnapshot,
    mature_discord_delivery_adapter,
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
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    DeliveryState,
    DeliveryTransition,
    NotificationKind,
    ResearchNotificationView,
    ScannerWatchNotificationView,
    SignalNotificationView,
    build_envelope,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    OneMinuteBar,
    OutcomeEngine,
    OutcomeTransitionView,
    TransitionKind,
)
from trader_assist_v0.multi_asset_shadow.planning import (
    CostModel,
    PlanRejection,
    PublicBbo,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import RuntimeReadinessSnapshot
from trader_assist_v0.multi_asset_shadow.shadow_records import (
    EvidenceStore,
    FormalSignal,
    HumanReviewAction,
    MarketEvent,
    NotificationOutboxReference,
    OutcomeEnvelope,
    PlanRecord,
    ProvenanceRecord,
    RecordConflictError,
    RecordError,
    ScannerEvidence,
    ShadowOrder,
    StrategyEvaluation,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfRelation,
    RetestType,
    ScannerState,
    SetupFamily,
    SetupMode,
    Side,
    StrategyDecision,
    TargetKind,
    TargetReference,
    ZoneBook,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    MarketEvent as KernelMarketEvent,
)
from trader_assist_v0.runtime.first_launch_notification import (
    HttpResponse,
    NotificationConfig,
)

NOW = datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
RELEASE_SHA = "1" * 40


class FakeOneMinuteProvider:
    def __init__(self) -> None:
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []
        self.inventory: list[OneMinuteBar] = []

    def subscribe_1m(self, *, market_id: str) -> None:
        self.subscribed.append(market_id)

    def unsubscribe_1m(self, *, market_id: str) -> None:
        self.unsubscribed.append(market_id)

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        return tuple(
            bar
            for bar in self.inventory
            if bar.market_id == market_id and start_ms <= bar.open_time_ms < end_ms
        )


class FakePlanningData:
    def __init__(
        self,
        *,
        stale_ms: int = 0,
        best_bid: Decimal = Decimal("100"),
        best_ask: Decimal = Decimal("100.1"),
        l2_offset: Decimal = Decimal(),
    ) -> None:
        self.stale_ms = stale_ms
        self.best_bid = best_bid
        self.best_ask = best_ask
        self.l2_offset = l2_offset
        self.calls: list[str] = []

    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> PublicBbo:
        self.calls.append("BBO")
        return PublicBbo(
            best_bid=self.best_bid,
            best_ask=self.best_ask,
            observed_at_ms=now_ms - self.stale_ms,
            market_id=market.identity.market_id,
            coin=market.identity.coin,
        )

    def fetch_l2(self, *, market: RegistryMarket, side: object, bbo: PublicBbo) -> PublicL2Snapshot:
        self.calls.append("L2")
        assert str(side) == "LONG"
        return PublicL2Snapshot(
            market_id=market.identity.market_id,
            coin=market.identity.coin,
            observed_at_ms=bbo.observed_at_ms,
            best_bid=bbo.best_bid,
            best_ask=bbo.best_ask,
            levels=((bbo.best_ask + self.l2_offset, Decimal("20")),),
            provenance_hash="f" * 64,
        )


class MutableReadiness:
    def __init__(
        self,
        *,
        registry: MarketRegistryManager,
        closed_store: ClosedBarStore,
        latest_open_ms: int,
    ) -> None:
        self.registry = registry
        self.closed_store = closed_store
        self.latest_open_ms = latest_open_ms
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


@dataclass
class Route:
    market: RegistryMarket
    registry: MarketRegistryManager
    data: MultiAssetDataAuthority
    closed_store: ClosedBarStore
    evidence: EvidenceStore
    outbox: EvidenceOutbox
    outcome_adapter: EvidenceOutcomeAdapter
    outcome_provider: FakeOneMinuteProvider
    outcome: OutcomeEngine
    planning: FakePlanningData
    readiness: MutableReadiness
    coordinator: MultiAssetShadowCoordinator

    @property
    def latest(self) -> ClosedBar:
        return self.closed_store.bars(self.market.identity.market_id)[-1]


def _market(
    *,
    tier: RegistryTier,
    lifecycle: MarketLifecycle = MarketLifecycle.ACTIVE,
    coin: str = "BTC",
) -> RegistryMarket:
    return RegistryMarket(
        display=coin,
        tier=tier,
        identity=MarketIdentity.create(dex="MAIN", coin=coin),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=lifecycle,
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(f"{coin}-metadata".encode()),
    )


def _payload(index: int, *, final: bool, coin: str = "BTC") -> dict[str, object]:
    start = index * 300_000
    group = index // 3
    payload: dict[str, object] = {
        "i": "5m",
        "s": coin,
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


def _route(
    tmp_path: Path,
    *,
    tier: RegistryTier = RegistryTier.P0,
    count: int = 64,
    planning: FakePlanningData | None = None,
) -> Route:
    market = _market(tier=tier)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="registry-1", created_at=NOW, markets=(market,))
    registry.stage(version)
    registry.request_apply(version.version)
    closed_store = ClosedBarStore(tmp_path / "closed.sqlite")
    data = MultiAssetDataAuthority(store=closed_store, registry=registry)
    data.admit_rest_history(
        market=market,
        snapshot=[_payload(index, final=index == count - 1) for index in range(count)],
        received_at=datetime.fromtimestamp((count * 300_000 + 1_000) / 1000, tz=UTC),
    )
    evidence = EvidenceStore(tmp_path / "evidence.sqlite")
    outbox = EvidenceOutbox(evidence)
    outcome_adapter = EvidenceOutcomeAdapter(evidence)
    outcome_provider = FakeOneMinuteProvider()
    outcome = OutcomeEngine(provider=outcome_provider, sink=outcome_adapter)
    planning_data = planning or FakePlanningData()
    readiness = MutableReadiness(
        registry=registry,
        closed_store=closed_store,
        latest_open_ms=(count - 1) * 300_000,
    )
    coordinator = MultiAssetShadowCoordinator(
        registry=registry,
        data_authority=data,
        evidence=evidence,
        outbox=outbox,
        outcome_engine=outcome,
        outcome_adapter=outcome_adapter,
        planning_data=planning_data,
        cost_model=CostModel(
            version="cost-1",
            fee_bps_per_side=Decimal(),
            slippage_bps_per_side=Decimal(),
            stress_slippage_bps_per_side=Decimal("2"),
        ),
        release_sha=RELEASE_SHA,
        runtime_readiness=readiness,
    )
    return Route(
        market,
        registry,
        data,
        closed_store,
        evidence,
        outbox,
        outcome_adapter,
        outcome_provider,
        outcome,
        planning_data,
        readiness,
        coordinator,
    )


def _zones(market_id: str) -> ZoneBook:
    support = ZoneSnapshot(
        "a" * 64,
        market_id,
        ZoneType.LOW,
        Decimal("100"),
        Decimal("99.5"),
        Decimal("100.5"),
        Decimal("0.5"),
        ZoneQuality.ZQ3,
        3,
        20,
        ("r1", "r2", "r3"),
        True,
    )
    resistance = ZoneSnapshot(
        "b" * 64,
        market_id,
        ZoneType.HIGH,
        Decimal("110"),
        Decimal("109.5"),
        Decimal("110.5"),
        Decimal("0.5"),
        ZoneQuality.ZQ3,
        3,
        20,
        ("r4", "r5", "r6"),
        True,
    )
    return ZoneBook((support, resistance), (), support, resistance)


def _direct_decision(
    market_id: str,
    *,
    family: SetupFamily = SetupFamily.RANGE_EDGE_REJECTION,
    mode: SetupMode | None = None,
    retest: RetestType | None = None,
    scanner_linkage: object | None = None,
) -> StrategyDecision:
    zone = _zones(market_id).active_support
    assert zone is not None
    return StrategyDecision(
        market_id=market_id,
        setup_family=family,
        setup_mode=mode,
        retest_type=retest,
        side=Side.LONG,
        decision=DecisionKind.FORMAL_SETUP_CONFIRMED,
        reason="INTEGRATION_FORMAL_FIXTURE",
        market_event_id=sha256_hex(f"{market_id}|{family.value}|{mode}|{retest}".encode()),
        zone_id=zone.zone_id,
        zone_snapshot=zone,
        a5_event=Decimal("1"),
        m20_event=Decimal("10"),
        htf_relation=HtfRelation.NEUTRAL,
        breakout_linkage=(
            BreakoutLinkage("c" * 64, "d" * 64) if family is SetupFamily.BREAKOUT_RETEST else None
        ),
        ideal_entry_low=Decimal("100"),
        ideal_entry_high=Decimal("100.2"),
        chase_limit=Decimal("101"),
        structural_stop=Decimal("99"),
        target_reference=TargetReference(TargetKind.RANGE_CENTER, Decimal("105")),
        transition="FORMAL_SETUP_CONFIRMED",
        scanner_linkage=scanner_linkage,  # type: ignore[arg-type]
    )


def _formalize(
    route: Route,
    receipt: EvaluationReceipt,
    *,
    candidate_id: str | None = None,
) -> FormalizationArtifacts | PlanRejection:
    start_ms = route.latest.close_time_ms + 1
    formal_ids = tuple(
        decision_id
        for decision_id, decision in zip(
            receipt.decision_ids, receipt.result.decisions, strict=True
        )
        if decision.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert formal_ids
    return route.coordinator.process_formal_decision(
        evaluation_receipt=receipt,
        decision_id=formal_ids[0],
        now_ms=start_ms + 5_000,
        candidate_id=candidate_id,
        correlation_market_metrics=CorrelationMarketMetrics(
            Decimal("100"), Decimal("2"), Decimal("1000000"), Decimal("500000")
        ),
    )


def _persist_breakout_shadow(
    store: EvidenceStore,
    *,
    market_id: str,
    start_ms: int,
    tag: str,
    family: str = "BREAKOUT_RETEST",
) -> ShadowOrder:
    setup_mode = "MICRO_FAST" if family == "BREAKOUT_RETEST" else None
    provenance = ProvenanceRecord.create(
        identity={"provenance": tag},
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        registry_version="registry-1",
        registry_hash="a" * 64,
        cost_model_version="cost-1",
        release_sha=RELEASE_SHA,
        recorded_at="2026-08-13T00:00:00Z",
    )
    event = MarketEvent.create(
        identity={"event": tag},
        market_id=market_id,
        event_kind=family,
        event_time="2026-08-13T00:00:00Z",
    )
    signal = FormalSignal.create(
        identity={"signal": tag},
        market_event_id=event.record_id,
        market_id=market_id,
        setup_family=family,
        setup_mode=setup_mode,
        side="LONG",
        approval_status="APPROVED",
        tier="P0",
        confirmed_at="2026-08-13T00:00:00Z",
        provenance_id=provenance.record_id,
    )
    plan = PlanRecord.create(
        identity={"plan": tag},
        signal_id=signal.record_id,
        planned_entry="100",
        stop="95",
        tp1="105",
        tp2="110",
        risk_reference_sizing={"reference": "only"},
        created_at="2026-08-13T00:00:00Z",
        provenance_id=provenance.record_id,
    )
    shadow = ShadowOrder.create(
        identity={"shadow": tag},
        signal_id=signal.record_id,
        plan_id=plan.record_id,
        market_event_id=event.record_id,
        market_id=market_id,
        setup_family=family,
        setup_mode=setup_mode,
        side="LONG",
        planned_entry="100",
        stop="95",
        tp1="105",
        tp2="110",
        risk_reference_sizing={"reference": "only"},
        provenance_id=provenance.record_id,
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        registry_version="registry-1",
        registry_hash="a" * 64,
        cost_model_version="cost-1",
        created_at="2026-08-13T00:00:00Z",
        confirmed_at="2026-08-13T00:00:00Z",
        submission_status="NOT_SUBMITTED",
        outcome_start_ms=start_ms,
        atr="2",
        zone_low="99",
        zone_high="101",
    )
    view = SignalNotificationView(
        kind=NotificationKind.FORMAL_SIGNAL,
        market_display="BTC",
        tier=RegistryTier.P0,
        setup_family=family,
        setup_mode=setup_mode,
        side="LONG",
        signal_time=NOW,
        planned_entry=Decimal("100"),
        stop=Decimal("95"),
        tp1=Decimal("105"),
        tp2=Decimal("110"),
        entry_quality="TEST",
        htf_relation="NEUTRAL",
        zone_context="test",
        reference_risk_sizing="REFERENCE_SIZE_ONLY",
        liquidity_attribution="test",
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        signal_id=signal.record_id,
        shadow_order_id=shadow.record_id,
    )
    envelope = build_envelope(view=view, created_at=NOW)
    reference = NotificationOutboxReference.create(
        identity={"signal_id": signal.record_id, "publication_id": envelope.idempotency_key},
        signal_id=signal.record_id,
        publication_id=envelope.idempotency_key,
        published_at="2026-08-13T00:00:00Z",
    )
    store.publish_formal_bundle(
        records=(provenance, event, signal, plan, shadow),
        notification_reference=reference,
        envelope=envelope,
    )
    return shadow


def test_finalized_5m_to_direct_formal_shadow_evidence_outbox_and_outcome(tmp_path: Path) -> None:
    route = _route(tmp_path, tier=RegistryTier.P2)
    result = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    decision = next(
        item
        for item in result.result.decisions
        if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert decision.setup_family is SetupFamily.RANGE_EDGE_REJECTION
    assert len(result.result.htf_context.__dict__) == 4
    artifacts = _formalize(route, result)
    assert isinstance(artifacts, FormalizationArtifacts)
    assert "candidate_id" not in artifacts.market_event.payload
    assert "candidate_id" not in artifacts.signal.payload
    assert artifacts.shadow_order.payload["submission_status"] == "NOT_SUBMITTED"
    assert artifacts.plan.reference_size_only == "YES"
    assert artifacts.plan.not_account_authoritative == "YES"
    assert artifacts.outcome_attached
    assert route.outcome.subscription_requirements == (route.market.identity.market_id,)
    assert (
        route.outbox.state(artifacts.outbox_receipt.envelope.idempotency_key)
        is DeliveryState.PENDING
    )
    assert route.planning.calls == ["BBO", "L2"]
    assert route.evidence.get(artifacts.shadow_order.record_id) == artifacts.shadow_order
    with pytest.raises(ValueError, match="publish_formal_bundle"):
        route.outbox.enqueue(artifacts.outbox_receipt.envelope)
    assert route.coordinator.human_review_status(artifacts.shadow_order.record_id) == "UNLABELED"
    with pytest.raises(IntegrationError, match="BREAKOUT_RETEST"):
        route.coordinator.publish_failed_breakout_research(
            shadow_order_id=artifacts.shadow_order.record_id
        )
    with pytest.raises(IntegrationError, match="caller-authored research"):
        route.coordinator.publish_research(
            ResearchNotificationView(
                kind=NotificationKind.RESEARCH_FAILED_BREAKOUT,
                market_display=route.market.display,
                tier=route.market.tier,
                evidence_time=NOW,
                side="SHORT",
                research_id="fabricated",
                source_shadow_order_id=artifacts.shadow_order.record_id,
                outcome_id="fabricated",
                failed_transition_ids=(),
                path_maturity_status="MATURE",
                required_end_ms=0,
                accepted_reentry_time_ms=None,
                reclaim_status="FAILED",
                conflict_count=0,
                has_gap=False,
                strategy_version="wrong",
                parameter_version="wrong",
            )
        )
    review = route.coordinator.record_human_review(
        shadow_order_id=artifacts.shadow_order.record_id,
        action=HumanReviewAction.SKIPPED,
        actor="operator",
        source="offline-test",
        reviewed_at=NOW + timedelta(hours=6),
        reason_code="NO_CAPACITY",
    )
    assert review.payload["action"] == "SKIPPED"
    assert route.coordinator.human_review_status(artifacts.shadow_order.record_id) == "SKIPPED"
    restarted_store = EvidenceStore(route.evidence.path)
    restarted_provider = FakeOneMinuteProvider()
    restarted = EvidenceOutcomeAdapter(restarted_store).restore_engine(
        now_ms=int(artifacts.shadow_order.payload["outcome_start_ms"]) + 60_000,
        provider=restarted_provider,
    )
    assert restarted.subscription_requirements == (route.market.identity.market_id,)
    restarted_store.close()


@pytest.mark.parametrize("tier", tuple(RegistryTier))
def test_all_tiers_cross_shared_adapters(tmp_path: Path, tier: RegistryTier) -> None:
    route = _route(tmp_path, tier=tier)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    assert artifacts.signal.payload["tier"] == tier.value
    assert artifacts.signal.payload["setup_family"] == SetupFamily.RANGE_EDGE_REJECTION.value
    rendered = artifacts.outbox_receipt.envelope.content
    assert "STANDARD_DEEP" not in rendered
    assert "STANDARD_SHALLOW" not in rendered
    assert "FAILED_ACCEPTED_BREAKOUT" not in rendered


@pytest.mark.parametrize(
    ("planning", "expected"),
    (
        (FakePlanningData(stale_ms=10_001), PlanRejection.BBO_INVALID_OR_STALE),
        (
            FakePlanningData(best_bid=Decimal("100"), best_ask=Decimal("100.5")),
            PlanRejection.LIQUIDITY_HARD_LIMIT,
        ),
        (FakePlanningData(l2_offset=Decimal("0.5")), PlanRejection.LIQUIDITY_HARD_LIMIT),
    ),
)
def test_stale_bbo_spread_and_1000_usd_slippage_fail_closed(
    tmp_path: Path, planning: FakePlanningData, expected: PlanRejection
) -> None:
    route = _route(tmp_path, planning=planning)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    result = _formalize(route, evaluation)
    assert result is expected
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM formal_signals").fetchone()[0] == 0
    )
    assert not route.outcome.attached_shadow_ids


def test_scanner_watch_and_directionless_new_market_never_create_shadow_or_1m(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path, count=64)
    scan = route.coordinator.scan_finalized(
        {
            route.market.identity.market_id: ScannerPublicSnapshot(
                current_spread_price=Decimal("0.1"), liquidity_healthy=True
            )
        },
        observed_at=NOW + timedelta(hours=6),
    )
    candidate = scan.observations[0].candidate
    assert candidate is not None and candidate.state is ScannerState.WATCH_NEW_MARKET
    assert candidate.side is None
    candidate_record = route.coordinator.persist_scanner_candidate(
        receipt=scan, candidate_id=candidate.candidate_id
    )
    directionless = ScannerWatchNotificationView(
        kind=NotificationKind.WATCH_NEW_MARKET,
        market_display=route.market.display,
        tier=route.market.tier,
        side=None,
        observation_time=NOW + timedelta(hours=6),
        return_15m=Decimal(),
        return_30m=Decimal(),
        return_60m=Decimal(),
        rank=1,
        move_atr=Decimal(),
        relative_volume=Decimal("1"),
        prior_level="retained 5m history",
        distance_to_level=Decimal(),
        liquidity_summary="public BBO/L2 healthy",
        scanner_r3_state=candidate.state.value,
        session="continuous crypto",
        scanner_parameter_version=candidate.parameter_version,
        watch_id=candidate.candidate_id,
    )
    assert not route.coordinator.publish_watch(directionless).coalesced
    with pytest.raises(IntegrationError, match="ancestry"):
        route.coordinator.publish_watch(
            replace(
                directionless,
                kind=NotificationKind.WATCH,
                side="LONG",
                watch_id="directional-watch",
            )
        )
    assert route.evidence.get(candidate_record.record_id) == candidate_record
    assert not route.outcome.attached_shadow_ids
    assert not route.outcome.subscription_requirements
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM shadow_orders").fetchone()[0] == 0
    )


def test_failed_market_isolated_disconnect_blocks_all_and_readiness_restore_resumes(
    tmp_path: Path,
) -> None:
    markets = (
        _market(tier=RegistryTier.P0, coin="BTC"),
        _market(tier=RegistryTier.P1, coin="ETH"),
    )
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="registry-2", created_at=NOW, markets=markets)
    registry.stage(version)
    registry.request_apply(version.version)
    closed_store = ClosedBarStore(tmp_path / "closed.sqlite")
    data = MultiAssetDataAuthority(store=closed_store, registry=registry)
    for market in markets:
        data.admit_rest_history(
            market=market,
            snapshot=[
                _payload(index, final=index == 63, coin=market.identity.coin) for index in range(64)
            ],
            received_at=datetime.fromtimestamp((64 * 300_000 + 1_000) / 1000, UTC),
        )
    evidence = EvidenceStore(tmp_path / "evidence.sqlite")
    outbox = EvidenceOutbox(evidence)
    adapter = EvidenceOutcomeAdapter(evidence)
    outcome = OutcomeEngine(sink=adapter)
    readiness = MutableReadiness(
        registry=registry, closed_store=closed_store, latest_open_ms=63 * 300_000
    )
    coordinator = MultiAssetShadowCoordinator(
        registry=registry,
        data_authority=data,
        evidence=evidence,
        outbox=outbox,
        outcome_engine=outcome,
        outcome_adapter=adapter,
        planning_data=FakePlanningData(),
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=RELEASE_SHA,
        runtime_readiness=readiness,
    )
    btc_id, eth_id = (market.identity.market_id for market in markets)
    readiness.failed.add(btc_id)
    scan = coordinator.scan_finalized(
        {eth_id: ScannerPublicSnapshot(Decimal("0.1"), True)},
        observed_at=NOW + timedelta(hours=6),
    )
    assert tuple(item.market_id for item in scan.observations) == (eth_id,)
    with pytest.raises(IntegrationError, match="readiness"):
        coordinator.evaluate_finalized_market(market_id=btc_id)
    healthy = coordinator.evaluate_finalized_market(market_id=eth_id)
    assert healthy.market_id == eth_id

    readiness.connected = False
    with pytest.raises(IntegrationError, match="disconnected"):
        coordinator.scan_finalized({}, observed_at=NOW + timedelta(hours=6, minutes=5))
    with pytest.raises(IntegrationError, match="disconnected"):
        coordinator.evaluate_finalized_market(market_id=eth_id)

    readiness.connected = True
    resumed = coordinator.evaluate_finalized_market(market_id=eth_id)
    assert resumed.latest_closed_5m_hash == healthy.latest_closed_5m_hash


def test_scanner_authority_slot_exact_retry_and_changed_input_conflict(tmp_path: Path) -> None:
    route = _route(tmp_path, count=64)
    market_id = route.market.identity.market_id
    snapshots = {market_id: ScannerPublicSnapshot(Decimal("0.1"), True)}
    observed_at = NOW + timedelta(hours=6)
    first = route.coordinator.scan_finalized(snapshots, observed_at=observed_at)
    retained_count = route.evidence.count()
    retry = route.coordinator.scan_finalized(snapshots, observed_at=observed_at)
    assert retry == first
    assert route.evidence.count() == retained_count
    assert isinstance(route.evidence.get(first.scanner_evidence_id), ScannerEvidence)

    with pytest.raises(RecordConflictError, match="conflicts"):
        route.coordinator.scan_finalized(
            {market_id: ScannerPublicSnapshot(Decimal("0.2"), True)},
            observed_at=observed_at,
        )
    assert route.evidence.count() == retained_count


def test_optional_candidate_link_validates_and_bad_or_missing_link_fails_closed(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path, count=64)
    scan = route.coordinator.scan_finalized(
        {
            route.market.identity.market_id: ScannerPublicSnapshot(
                current_spread_price=Decimal("0.1"), liquidity_healthy=True
            )
        },
        observed_at=NOW + timedelta(hours=6),
    )
    observation = scan.observations[0]
    assert observation.candidate is not None
    candidate = observation.candidate
    retained = route.coordinator.persist_scanner_candidate(
        receipt=scan, candidate_id=candidate.candidate_id
    )
    linked = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
        scanner_linkage=candidate.linkage,
    )
    artifacts = _formalize(route, linked, candidate_id=retained.record_id)
    assert isinstance(artifacts, FormalizationArtifacts)
    assert artifacts.signal.payload["candidate_id"] == retained.record_id

    other_route = _route(tmp_path / "bad", count=64)
    with pytest.raises(IntegrationError, match="retained Candidate"):
        other_route.coordinator.evaluate_finalized_market(
            market_id=other_route.market.identity.market_id,
            scanner_linkage=candidate.linkage,
        )
    assert (
        other_route.evidence._connection.execute("SELECT COUNT(*) FROM formal_signals").fetchone()[
            0
        ]
        == 0
    )


def test_stale_changed_and_foreign_evaluation_receipts_fail_closed(tmp_path: Path) -> None:
    route = _route(tmp_path)
    receipt = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    changed = replace(
        receipt,
        result=replace(
            receipt.result,
            decisions=(replace(receipt.result.decisions[0], reason="CHANGED"),),
        ),
    )
    with pytest.raises(IntegrationError, match="content was changed"):
        _formalize(route, changed)
    with pytest.raises(IntegrationError, match="contradicts"):
        _formalize(route, replace(receipt, registry_hash="f" * 64))

    other = _route(tmp_path / "other")
    with pytest.raises(IntegrationError, match="not retained"):
        _formalize(other, receipt)

    next_index = route.latest.open_time_ms // 300_000 + 1
    route.data.admit_rest_history(
        market=route.market,
        snapshot=[_payload(next_index, final=False)],
        received_at=datetime.fromtimestamp(((next_index + 1) * 300_000 + 1_000) / 1000, UTC),
    )
    route.readiness.latest_open_ms = next_index * 300_000
    with pytest.raises(IntegrationError, match="stale"):
        _formalize(route, receipt)


def test_event_ledger_continuation_survives_evidence_reopen(tmp_path: Path) -> None:
    uninterrupted = _route(tmp_path / "live")
    restarted = _route(tmp_path / "restart")
    for route in (uninterrupted, restarted):
        zone = _zones(route.market.identity.market_id).active_support
        assert zone is not None
        latest = route.coordinator._strategy_bar(route.latest)
        active = KernelMarketEvent(
            market_event_id="active-sweep",
            market_id=route.market.identity.market_id,
            setup_family=SetupFamily.SWEEP_RECLAIM,
            side=Side.LONG,
            status=EventStatus.ACTIVE,
            transition="SWEEP_CANDIDATE_CREATED",
            zone=zone,
            created_bar=latest,
            latest_bar=latest,
            a5_event=Decimal("1"),
            m20_event=Decimal("10"),
            htf_relation=HtfRelation.NEUTRAL,
            reclaim_candle_high=Decimal("200"),
            reclaim_candle_low=Decimal("99"),
            sweep_extreme=Decimal("99"),
            ideal_entry_low=Decimal("99.55"),
            ideal_entry_high=Decimal("99.75"),
            chase_limit=Decimal("99.85"),
            structural_stop=Decimal("98.9"),
            target_reference=TargetReference(TargetKind.SOURCE_ZONE_CENTER, zone.center),
        )
        route.coordinator._ledgers[route.market.identity.market_id] = EventLedger((active,))
        checkpoint = route.coordinator.evaluate_finalized_market(
            market_id=route.market.identity.market_id,
        )
        assert any(event.status is EventStatus.ACTIVE for event in checkpoint.result.ledger.events)

    restarted.evidence.close()
    reopened = EvidenceStore(restarted.evidence.path)
    adapter = EvidenceOutcomeAdapter(reopened)
    outcome = OutcomeEngine(sink=adapter)
    restarted.coordinator = MultiAssetShadowCoordinator(
        registry=restarted.registry,
        data_authority=restarted.data,
        evidence=reopened,
        outbox=EvidenceOutbox(reopened),
        outcome_engine=outcome,
        outcome_adapter=adapter,
        planning_data=restarted.planning,
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=RELEASE_SHA,
        runtime_readiness=restarted.readiness,
    )
    restarted.evidence = reopened
    for route in (uninterrupted, restarted):
        next_index = route.latest.open_time_ms // 300_000 + 1
        route.data.admit_rest_history(
            market=route.market,
            snapshot=[_payload(next_index, final=False)],
            received_at=datetime.fromtimestamp(((next_index + 1) * 300_000 + 1_000) / 1000, UTC),
        )
        route.readiness.latest_open_ms = next_index * 300_000
    live_result = uninterrupted.coordinator.evaluate_finalized_market(
        market_id=uninterrupted.market.identity.market_id,
    ).result
    restart_result = restarted.coordinator.evaluate_finalized_market(
        market_id=restarted.market.identity.market_id,
    ).result
    assert restart_result == live_result


def test_scanner_receipt_rejects_fabrication_and_linkage_state_version_market(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path, count=64)
    scan = route.coordinator.scan_finalized(
        {route.market.identity.market_id: ScannerPublicSnapshot(Decimal("0.1"), True)},
        observed_at=NOW + timedelta(hours=6),
    )
    candidate = scan.observations[0].candidate
    assert candidate is not None
    retained = route.coordinator.persist_scanner_candidate(
        receipt=scan, candidate_id=candidate.candidate_id
    )
    with pytest.raises(IntegrationError, match="not produced"):
        route.coordinator.persist_scanner_candidate(receipt=scan, candidate_id="fabricated")

    for linkage in (
        replace(candidate.linkage, state=ScannerState.BREAKOUT_RETEST_READY),
        replace(candidate.linkage, scanner_version="wrong"),
    ):
        with pytest.raises(IntegrationError, match="contradicts"):
            route.coordinator._candidate_link(
                _direct_decision(route.market.identity.market_id, scanner_linkage=linkage),
                retained.record_id,
            )

    with pytest.raises(IntegrationError, match="contradicts"):
        route.coordinator._candidate_link(
            _direct_decision("different-market", scanner_linkage=candidate.linkage),
            retained.record_id,
        )

    other = _route(tmp_path / "market", count=64)
    with pytest.raises(IntegrationError, match="retained Candidate"):
        other.coordinator._candidate_link(
            _direct_decision(other.market.identity.market_id, scanner_linkage=candidate.linkage),
            retained.record_id,
        )


def test_candidate_side_and_parameter_must_match_formal_decision(tmp_path: Path) -> None:
    route = _route(tmp_path, count=288)
    scan = route.coordinator.scan_finalized(
        {route.market.identity.market_id: ScannerPublicSnapshot(Decimal("0.1"), True)},
        observed_at=NOW + timedelta(hours=30),
    )
    candidate = scan.observations[0].candidate
    assert candidate is not None and candidate.side is Side.LONG
    retained = route.coordinator.persist_scanner_candidate(
        receipt=scan, candidate_id=candidate.candidate_id
    )
    decision = _direct_decision(
        route.market.identity.market_id, scanner_linkage=candidate.linkage
    )
    assert route.coordinator._candidate_link(decision, retained.record_id) == retained.record_id
    with pytest.raises(IntegrationError, match="Formal strategy evidence"):
        route.coordinator._candidate_link(
            replace(decision, side=Side.SHORT), retained.record_id
        )
    with pytest.raises(IntegrationError, match="Formal strategy evidence"):
        route.coordinator._candidate_link(
            replace(decision, parameter_version="wrong"), retained.record_id
        )


def test_formal_bundle_exact_retry_and_changed_semantic_content_conflict(tmp_path: Path) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    first = _formalize(route, evaluation)
    assert isinstance(first, FormalizationArtifacts)
    retained_count = route.evidence.count()
    outbox_count = route.evidence._connection.execute(
        "SELECT COUNT(*) FROM notification_outbox"
    ).fetchone()[0]
    retry = _formalize(route, evaluation)
    assert isinstance(retry, FormalizationArtifacts)
    assert retry.outbox_receipt.coalesced
    assert retry.shadow_order == first.shadow_order
    assert retry.shadow_order.payload["submission_status"] == "NOT_SUBMITTED"
    assert route.evidence.count() == retained_count
    assert (
        route.evidence._connection.execute(
            "SELECT COUNT(*) FROM notification_outbox"
        ).fetchone()[0]
        == outbox_count
    )

    route.planning.best_ask = Decimal("100.2")
    with pytest.raises(RecordConflictError, match="conflicts"):
        _formalize(route, evaluation)
    assert route.evidence.count() == retained_count


@pytest.mark.parametrize("failure_index", range(1, 7))
def test_atomic_formal_publication_rolls_back_on_record_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_index: int
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    original = route.evidence._write_one
    calls = 0

    def fail_on_signal(record: object) -> bool:
        nonlocal calls
        calls += 1
        if calls == failure_index:
            raise RuntimeError("injected formal boundary")
        return original(record)  # type: ignore[arg-type]

    monkeypatch.setattr(route.evidence, "_write_one", fail_on_signal)
    with pytest.raises(RuntimeError, match="injected"):
        _formalize(route, evaluation)
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM formal_signals").fetchone()[0] == 0
    )
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[0]
        == 0
    )


def test_atomic_formal_publication_rolls_back_if_outbox_insert_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )

    def fail_outbox(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("injected outbox boundary")

    monkeypatch.setattr(route.evidence, "_insert_outbox", fail_outbox)
    with pytest.raises(RuntimeError, match="outbox"):
        _formalize(route, evaluation)
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM formal_signals").fetchone()[0] == 0
    )
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[0]
        == 0
    )


def test_draining_blocks_new_activity_but_existing_outcome_completes_and_detaches(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    successor = route.registry.lifecycle_update(
        "registry-draining",
        route.market.identity.market_id,
        MarketLifecycle.DRAINING,
        now=NOW + timedelta(hours=6),
    )
    route.registry.request_apply(successor.version)
    next_index = route.latest.open_time_ms // 300_000 + 1
    route.data.admit_rest_history(
        market=successor.markets[0],
        snapshot=[_payload(next_index, final=False)],
        received_at=datetime.fromtimestamp(((next_index + 1) * 300_000 + 1_000) / 1000, UTC),
    )
    with pytest.raises(IntegrationError, match="lifecycle"):
        route.coordinator.evaluate_finalized_market(
            market_id=route.market.identity.market_id,
        )
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    route.outcome_provider.inventory.extend(
        OneMinuteBar.create(
            market_id=route.market.identity.market_id,
            open_time_ms=start + index * 60_000,
            open=Decimal("100.1"),
            high=Decimal("100.2"),
            low=Decimal("100.0"),
            close=Decimal("100.1"),
        )
        for index in range(120)
    )
    route.coordinator.recover_outcome_bars(now_ms=start + 120 * 60_000)
    completed = route.outcome.tick(now_ms=start + 120 * 60_000)[0]
    assert not completed.unresolved
    assert route.outcome.subscription_requirements == ()
    assert route.outcome_provider.unsubscribed == [route.market.identity.market_id]
    assert route.outcome_adapter.persisted_outcomes(artifacts.shadow_order.record_id)

    route.evidence.close()
    reopened = EvidenceStore(tmp_path / "evidence.sqlite")
    reopened_adapter = EvidenceOutcomeAdapter(reopened)
    assert reopened_adapter.persisted_outcomes(artifacts.shadow_order.record_id)
    restarted_provider = FakeOneMinuteProvider()
    restarted = reopened_adapter.restore_engine(
        now_ms=start + 120 * 60_000, provider=restarted_provider
    )
    assert artifacts.shadow_order.record_id in restarted.attached_shadow_ids
    assert restarted.subscription_requirements == ()
    research = CorrelationResearchAdapter(reopened)
    assert len(research.completed_signals()) == 1
    assert (
        research.build_report(
            {route.market.identity.market_id: ()}
        ).raw_market_level.raw_shadow_order_count
        == 1
    )
    with pytest.raises(CorrelationEngineError, match="every signal market"):
        research.build_report({})
    assert isinstance(reopened.get(artifacts.shadow_order.record_id), ShadowOrder)


def test_strategy_authority_retry_context_bar_conflict_and_canonical_zone(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    market_id = route.market.identity.market_id
    with pytest.raises(IntegrationError, match="canonical ZoneBook"):
        route.coordinator.evaluate_finalized_market(
            market_id=market_id, zone_book=_zones(market_id)
        )
    first = route.coordinator.evaluate_finalized_market(market_id=market_id)
    retained_count = route.evidence.count()
    retry = route.coordinator.evaluate_finalized_market(market_id=market_id)
    assert retry == first
    assert route.evidence.count() == retained_count == 1
    assert isinstance(route.evidence.get(first.evaluation_record_id), StrategyEvaluation)

    route.coordinator._release_sha = "2" * 40
    with pytest.raises(IntegrationError, match="conflicts with current context"):
        route.coordinator.evaluate_finalized_market(market_id=market_id)
    route.coordinator._release_sha = RELEASE_SHA

    prior = route.latest
    changed = ClosedBar.create(
        market_id=prior.market_id,
        interval=prior.interval,
        open_time_ms=prior.open_time_ms,
        close_time_ms=prior.close_time_ms,
        open=prior.open,
        high=prior.high,
        low=prior.low,
        close=prior.close + Decimal("0.1"),
        volume=prior.volume,
        source_id=prior.source_id,
        provenance_hash="9" * 64,
        received_at=prior.received_at,
    )
    route.closed_store.connection.execute(
        "UPDATE closed_bars SET canonical_hash = ?, payload_json = ? "
        "WHERE market_id = ? AND interval = '5m' AND open_time_ms = ?",
        (changed.canonical_hash, changed.model_dump_json(), market_id, changed.open_time_ms),
    )
    route.closed_store.connection.commit()
    with pytest.raises(IntegrationError, match="conflicts with current context"):
        route.coordinator.evaluate_finalized_market(market_id=market_id)
    assert route.evidence.count() == retained_count


def test_strategy_restart_uses_semantic_chronology_not_record_id_order(tmp_path: Path) -> None:
    route = _route(tmp_path)
    receipts = [
        route.coordinator.evaluate_finalized_market(market_id=route.market.identity.market_id)
    ]
    for _ in range(3):
        next_index = route.latest.open_time_ms // 300_000 + 1
        route.data.admit_rest_history(
            market=route.market,
            snapshot=[_payload(next_index, final=False)],
            received_at=datetime.fromtimestamp(
                ((next_index + 1) * 300_000 + 1_000) / 1000, UTC
            ),
        )
        route.readiness.latest_open_ms = next_index * 300_000
        receipts.append(
            route.coordinator.evaluate_finalized_market(
                market_id=route.market.identity.market_id
            )
        )
    latest = receipts[-1]
    assert latest.evaluation_record_id < receipts[-2].evaluation_record_id

    database = route.evidence.path
    route.evidence.close()
    reopened = EvidenceStore(database)
    adapter = EvidenceOutcomeAdapter(reopened)
    outcome = OutcomeEngine(sink=adapter)
    restarted = MultiAssetShadowCoordinator(
        registry=route.registry,
        data_authority=route.data,
        evidence=reopened,
        outbox=EvidenceOutbox(reopened),
        outcome_engine=outcome,
        outcome_adapter=adapter,
        planning_data=route.planning,
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=RELEASE_SHA,
        runtime_readiness=route.readiness,
    )
    retry = restarted.evaluate_finalized_market(market_id=route.market.identity.market_id)
    assert retry == latest
    assert reopened._connection.execute("SELECT COUNT(*) FROM strategy_evaluations").fetchone()[
        0
    ] == len(receipts)


@pytest.mark.parametrize(
    "kind", (TransitionKind.ACCEPTED_REENTRY, TransitionKind.FAILED_BREAKOUT)
)
def test_literal_transition_has_no_production_ingress(
    tmp_path: Path, kind: TransitionKind
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    transition = OutcomeTransitionView(
        transition_id=f"literal-{kind.value.lower()}",
        shadow_order_id=artifacts.shadow_order.record_id,
        market_id=route.market.identity.market_id,
        kind=kind,
        occurred_at_ms=start,
        reference_price=Decimal("100"),
    )

    with pytest.raises(IntegrationError, match="literal Outcome transitions"):
        route.coordinator.admit_outcome_transition(
            transition, now_ms=start, recover=False
        )
    assert not hasattr(route.coordinator, "admit_accepted_reentry")
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_transitions").fetchone()[0]
        == 0
    )


def test_direct_engine_arbitrary_bar_cannot_persist_canonical_outcome(tmp_path: Path) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    bar = OneMinuteBar.create(
        market_id=route.market.identity.market_id,
        open_time_ms=start,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
    )

    with pytest.raises(IntegrationError, match="caller-authored 1m"):
        route.coordinator.admit_outcome_bar(bar)
    route.outcome.admit_bar(bar)
    with pytest.raises(RecordError, match="retained transition or 1m authority"):
        route.outcome.tick(now_ms=start + 60_000)
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_envelopes").fetchone()[0]
        == 0
    )


def test_normal_formal_outcome_uses_provider_bars_with_zero_transitions_and_restarts(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    bars = tuple(
        OneMinuteBar.create(
            market_id=route.market.identity.market_id,
            open_time_ms=start + minute * 60_000,
            open=Decimal("100.1"),
            high=Decimal("100.2"),
            low=Decimal("100"),
            close=Decimal("100.1"),
        )
        for minute in range(120)
    )
    route.outcome_provider.inventory.extend((*bars, bars[10]))
    now_ms = start + 120 * 60_000
    route.coordinator.recover_outcome_bars(now_ms=now_ms)
    before = route.outcome.tick(now_ms=now_ms)
    outcome = next(
        item
        for item in before
        if item.shadow_order_id == artifacts.shadow_order.record_id
    )
    assert outcome.path_maturity_status.value == "MATURE"
    assert not outcome.unresolved
    assert {item.horizon_minutes for item in outcome.horizons} == {30, 60, 120}
    assert outcome.required_end_ms == start + 120 * 60_000
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_transitions").fetchone()[0]
        == 0
    )
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_bars").fetchone()[0]
        == 120
    )
    assert artifacts.shadow_order.payload["submission_status"] == "NOT_SUBMITTED"

    route.evidence.close()
    reopened = EvidenceStore(tmp_path / "evidence.sqlite")
    provider = FakeOneMinuteProvider()
    adapter = EvidenceOutcomeAdapter(reopened)
    restored = adapter.restore_engine(now_ms=now_ms, provider=provider)
    after = tuple(
        restored.evaluate(identity, as_of_ms=now_ms)
        for identity in restored.attached_shadow_ids
    )
    assert after == before


def test_provider_conflict_and_gap_reconstruct_deterministically(tmp_path: Path) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    bars = [
        OneMinuteBar.create(
            market_id=route.market.identity.market_id,
            open_time_ms=start + minute * 60_000,
            open=Decimal("100.1"),
            high=Decimal("100.2"),
            low=Decimal("100"),
            close=Decimal("100.1"),
        )
        for minute in range(120)
        if minute != 10
    ]
    bars.append(
        OneMinuteBar.create(
            market_id=route.market.identity.market_id,
            open_time_ms=start + 11 * 60_000,
            open=Decimal("100.1"),
            high=Decimal("100.3"),
            low=Decimal("100"),
            close=Decimal("100.2"),
            source_id="PUBLIC_1M_CONFLICT",
        )
    )
    route.outcome_provider.inventory.extend(bars)
    now_ms = start + 120 * 60_000
    route.coordinator.recover_outcome_bars(now_ms=now_ms)
    before = route.outcome.tick(now_ms=now_ms)
    outcome = next(
        item
        for item in before
        if item.shadow_order_id == artifacts.shadow_order.record_id
    )
    assert outcome.conflicts
    assert outcome.path_maturity_status.value == "CONFLICTED"
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_bars").fetchone()[0]
        == 120
    )

    route.evidence.close()
    reopened = EvidenceStore(tmp_path / "evidence.sqlite")
    restored = EvidenceOutcomeAdapter(reopened).restore_engine(now_ms=now_ms)
    after = tuple(
        restored.evaluate(identity, as_of_ms=now_ms)
        for identity in restored.attached_shadow_ids
    )
    assert after == before


def test_fabricated_outcome_projection_cannot_drive_research_or_correlation(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    start = route.latest.close_time_ms + 1
    shadow = _persist_breakout_shadow(
        route.evidence,
        market_id=route.market.identity.market_id,
        start_ms=start,
        tag="fabricated-projection",
    )
    fabricated = OutcomeEnvelope.create(
        identity={"shadow_order_id": shadow.record_id, "evaluated_at_ms": start},
        signal_id=shadow.payload["signal_id"],
        shadow_order_id=shadow.record_id,
        observed_at=datetime.fromtimestamp(start / 1000, UTC).isoformat().replace("+00:00", "Z"),
        evaluated_at_ms=start,
        path_maturity_status="MATURE",
        unresolved=False,
        outcome_source="FABRICATED",
        outcome_r="999",
        outcome_mfe="999",
        outcome_mae="0",
        required_start_ms=start,
        original_deadline_ms=start + 120 * 60_000,
        required_end_ms=start + 120 * 60_000,
        failed_breakout=True,
        projection={"failed_breakout": True, "research": {"failed_breakout": True}},
    )
    with pytest.raises(RecordError, match="controlled producer"):
        route.evidence.write((fabricated,))

    # Even a test-only low-level insertion cannot promote the projection to truth.
    route.evidence._write_transaction((fabricated,))
    with pytest.raises(RecordError, match="canonical reconstruction"):
        route.coordinator.publish_failed_breakout_research(shadow_order_id=shadow.record_id)
    with pytest.raises(RecordError, match="canonical reconstruction"):
        CorrelationResearchAdapter(route.evidence).completed_signals()


@pytest.mark.parametrize("family", ("SWEEP_RECLAIM", "RANGE_EDGE_REJECTION"))
def test_non_breakout_families_cannot_publish_failed_breakout_research(
    tmp_path: Path, family: str
) -> None:
    route = _route(tmp_path)
    shadow = _persist_breakout_shadow(
        route.evidence,
        market_id=route.market.identity.market_id,
        start_ms=route.latest.close_time_ms + 1,
        tag=family.lower(),
        family=family,
    )
    with pytest.raises(IntegrationError, match="requires BREAKOUT_RETEST"):
        route.coordinator.publish_failed_breakout_research(shadow_order_id=shadow.record_id)


def test_returned_inside_provider_path_without_transition_cannot_publish_research(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    market_id = route.market.identity.market_id
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    route.outcome_provider.inventory.extend(
        OneMinuteBar.create(
            market_id=market_id,
            open_time_ms=start + minute * 60_000,
            open=Decimal("100"),
            high=Decimal("100.2"),
            low=Decimal("99.8"),
            close=Decimal("100"),
        )
        for minute in range(120)
    )
    route.coordinator.recover_outcome_bars(now_ms=start + 120 * 60_000)
    outcome = next(
        item
        for item in route.outcome.tick(now_ms=start + 120 * 60_000)
        if item.shadow_order_id == artifacts.shadow_order.record_id
    )
    assert not outcome.failed_breakout and not outcome.unresolved
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM outcome_transitions").fetchone()[0]
        == 0
    )
    with pytest.raises(IntegrationError, match="BREAKOUT_RETEST"):
        route.coordinator.publish_failed_breakout_research(
            shadow_order_id=artifacts.shadow_order.record_id
        )


def test_durable_outbox_coalesces_reclaims_and_rejects_stale_completion(tmp_path: Path) -> None:
    database = tmp_path / "outbox.sqlite"
    store = EvidenceStore(database)
    outbox = EvidenceOutbox(store)
    view = ScannerWatchNotificationView(
        kind=NotificationKind.WATCH,
        market_display="BTC",
        tier=RegistryTier.P0,
        side="LONG",
        observation_time=NOW,
        return_15m=Decimal("1"),
        return_30m=Decimal("2"),
        return_60m=Decimal("3"),
        rank=1,
        move_atr=Decimal("1"),
        relative_volume=Decimal("1"),
        prior_level="range high",
        distance_to_level=Decimal("0.1"),
        liquidity_summary="healthy",
        scanner_r3_state="WATCH_MOMENTUM",
        session="continuous crypto",
        scanner_parameter_version="2026-08-03-r1",
        watch_id="watch-1",
    )
    envelope = build_envelope(view=view, created_at=NOW)
    assert not outbox.enqueue(envelope).coalesced
    assert outbox.enqueue(envelope).coalesced
    first = outbox.claim_due(now=NOW, limit=1, lease_seconds=60)[0]
    store.close()

    reopened = EvidenceStore(database)
    restarted = EvidenceOutbox(reopened)
    second = restarted.claim_due(now=NOW + timedelta(seconds=61), limit=1, lease_seconds=60)[0]
    assert second.attempt_count == 2
    assert second.claim_token != first.claim_token
    restarted.complete(
        claim_token=first.claim_token,
        transition=DeliveryTransition(
            DeliveryState.PERMANENT_FAILURE, "stale", NOW + timedelta(seconds=62)
        ),
    )
    assert restarted.state(envelope.idempotency_key) is DeliveryState.PENDING
    restarted.complete(
        claim_token=second.claim_token,
        transition=DeliveryTransition(
            DeliveryState.DELIVERED,
            "2xx",
            NOW + timedelta(seconds=62),
            response_status=204,
        ),
    )
    assert restarted.state(envelope.idempotency_key) is DeliveryState.DELIVERED


class FakeMatureTransport:
    def __init__(self) -> None:
        self.payload: bytes | None = None
        self.headers: dict[str, str] | None = None

    def post(
        self, *, url: str, payload: bytes, headers: dict[str, str], timeout: float
    ) -> HttpResponse:
        del url, timeout
        self.payload = payload
        self.headers = headers
        return HttpResponse(204, b"")


def test_mature_https_bridge_keeps_discord_payload_content_only() -> None:
    transport = FakeMatureTransport()
    adapter = mature_discord_delivery_adapter(
        config=NotificationConfig("https://discord.example.test/webhook", 5.0, None, None),
        transport=transport,
    )
    research = ResearchNotificationView(
        kind=NotificationKind.RESEARCH_FAILED_BREAKOUT,
        market_display="BTC",
        tier=RegistryTier.P0,
        evidence_time=NOW,
        side="LONG",
        research_id="research-1",
        source_shadow_order_id="shadow-1",
        outcome_id="outcome-1",
        failed_transition_ids=("transition-1",),
        path_maturity_status="MATURE",
        required_end_ms=120_000,
        accepted_reentry_time_ms=60_000,
        reclaim_status="FAILED",
        conflict_count=0,
        has_gap=False,
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
    )
    envelope = build_envelope(view=research, created_at=NOW)
    assert adapter.deliver(envelope).status_code == 204
    assert transport.payload is not None
    assert json.loads(transport.payload) == {"content": envelope.content}
    assert transport.headers == {"Content-Type": "application/json"}
    assert "Idempotency-Key" not in transport.headers


def test_correlation_unavailability_is_not_a_live_formal_gate(tmp_path: Path) -> None:
    route = _route(tmp_path)
    evaluation = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
    )
    artifacts = _formalize(route, evaluation)
    assert isinstance(artifacts, FormalizationArtifacts)
    assert isinstance(route.evidence.get(artifacts.shadow_order.record_id), ShadowOrder)
    research = CorrelationResearchAdapter(route.evidence)
    assert research.completed_signals() == ()
    assert research.build_report({}).raw_market_level.raw_shadow_order_count == 0
    assert len(SetupFamily) == 3
