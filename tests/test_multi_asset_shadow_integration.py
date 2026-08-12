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
    build_envelope,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    OneMinuteBar,
    OutcomeEngine,
)
from trader_assist_v0.multi_asset_shadow.planning import (
    CostModel,
    PlanRejection,
    PublicBbo,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.shadow_records import (
    EvidenceStore,
    HumanReviewAction,
    ShadowOrder,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    BreakoutLinkage,
    DecisionKind,
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

    def subscribe_1m(self, *, market_id: str) -> None:
        self.subscribed.append(market_id)

    def unsubscribe_1m(self, *, market_id: str) -> None:
        self.unsubscribed.append(market_id)

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        del market_id, start_ms, end_ms
        return ()


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
    coordinator: MultiAssetShadowCoordinator

    @property
    def latest(self) -> ClosedBar:
        return self.closed_store.bars(self.market.identity.market_id)[-1]


def _market(
    *, tier: RegistryTier, lifecycle: MarketLifecycle = MarketLifecycle.ACTIVE
) -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=tier,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=lifecycle,
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(b"BTC-metadata"),
    )


def _payload(index: int, *, final: bool) -> dict[str, object]:
    start = index * 300_000
    baseline_close = "102" if (index // 3) % 2 else "100"
    return {
        "i": "5m",
        "s": "BTC",
        "t": start,
        "T": start + 299_999,
        "o": "101" if final else "100",
        "h": "102" if final else "103",
        "l": "99.8" if final else "98",
        "c": "101.5" if final else baseline_close,
        "v": "10",
    }


def _route(
    tmp_path: Path,
    *,
    tier: RegistryTier = RegistryTier.P0,
    count: int = 60,
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
    decision: StrategyDecision,
    *,
    candidate_id: str | None = None,
) -> FormalizationArtifacts | PlanRejection:
    start_ms = route.latest.close_time_ms + 1
    return route.coordinator.process_formal_decision(
        decision=decision,
        confirmed_bar=route.latest,
        now_ms=start_ms + 5_000,
        candidate_id=candidate_id,
        correlation_market_metrics=CorrelationMarketMetrics(
            Decimal("100"), Decimal("2"), Decimal("1000000"), Decimal("500000")
        ),
    )


def test_finalized_5m_to_direct_formal_shadow_evidence_outbox_and_outcome(tmp_path: Path) -> None:
    route = _route(tmp_path, tier=RegistryTier.P2)
    result = route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
        zone_book=_zones(route.market.identity.market_id),
    )
    decision = next(
        item for item in result.decisions if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert decision.setup_family is SetupFamily.RANGE_EDGE_REJECTION
    assert len(result.htf_context.__dict__) == 4
    artifacts = _formalize(route, decision)
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
    assert route.coordinator.human_review_status(artifacts.shadow_order.record_id) == "UNLABELED"
    research_receipt = route.coordinator.publish_research(
        ResearchNotificationView(
            kind=NotificationKind.RESEARCH_FAILED_BREAKOUT,
            market_display=route.market.display,
            tier=route.market.tier,
            evidence_time=NOW + timedelta(hours=6),
            side="LONG",
            research_id="failed-breakout-1",
            source_shadow_order_id=artifacts.shadow_order.record_id,
            evidence_summary="accepted re-entry evidence",
            outcome_summary="research-only path",
            strategy_version="FL-MA-PRICE-ACTION-v0.1",
            parameter_version="2026-08-03-r1",
        )
    )
    assert "NOT A FORMAL SIGNAL" in research_receipt.envelope.content
    assert "Planned entry:" not in research_receipt.envelope.content
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


@pytest.mark.parametrize(
    ("tier", "family", "mode", "retest"),
    (
        (RegistryTier.P0, SetupFamily.SWEEP_RECLAIM, None, None),
        (RegistryTier.P1, SetupFamily.BREAKOUT_RETEST, SetupMode.MICRO_FAST, None),
        (RegistryTier.P2, SetupFamily.BREAKOUT_RETEST, SetupMode.STANDARD, RetestType.DEEP),
        (RegistryTier.P0, SetupFamily.BREAKOUT_RETEST, SetupMode.STANDARD, RetestType.SHALLOW),
        (RegistryTier.P1, SetupFamily.RANGE_EDGE_REJECTION, None, None),
    ),
)
def test_all_tiers_three_setups_and_breakout_modes_cross_shared_adapters(
    tmp_path: Path,
    tier: RegistryTier,
    family: SetupFamily,
    mode: SetupMode | None,
    retest: RetestType | None,
) -> None:
    route = _route(tmp_path, tier=tier)
    artifacts = _formalize(
        route,
        _direct_decision(
            route.market.identity.market_id,
            family=family,
            mode=mode,
            retest=retest,
        ),
    )
    assert isinstance(artifacts, FormalizationArtifacts)
    assert artifacts.signal.payload["tier"] == tier.value
    assert artifacts.signal.payload["setup_family"] == family.value
    assert artifacts.signal.payload["setup_mode"] == (None if mode is None else mode.value)
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
    result = _formalize(route, _direct_decision(route.market.identity.market_id))
    assert result is expected
    assert route.evidence.count() == 0
    assert not route.outcome.attached_shadow_ids


def test_scanner_watch_and_directionless_new_market_never_create_shadow_or_1m(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path, count=64)
    observations = route.coordinator.scan_finalized(
        {
            route.market.identity.market_id: ScannerPublicSnapshot(
                current_spread_price=Decimal("0.1"), liquidity_healthy=True
            )
        }
    )
    candidate = observations[0].candidate
    assert candidate is not None and candidate.state is ScannerState.WATCH_NEW_MARKET
    assert candidate.side is None
    candidate_record = route.coordinator.persist_scanner_candidate(
        candidate, observed_at=NOW + timedelta(hours=6)
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
    directional = replace(
        directionless,
        kind=NotificationKind.WATCH,
        side="LONG",
        watch_id="directional-watch",
    )
    receipt = route.coordinator.publish_watch(directional)
    assert "WATCH — NOT ACTIONABLE" in receipt.envelope.content
    assert "NOT_YET_SETUP_CONFIRMED" in receipt.envelope.content
    assert route.evidence.get(candidate_record.record_id) == candidate_record
    assert not route.outcome.attached_shadow_ids
    assert not route.outcome.subscription_requirements
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM shadow_orders").fetchone()[0] == 0
    )


def test_optional_candidate_link_validates_and_bad_or_missing_link_fails_closed(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path, count=64)
    observation = route.coordinator.scan_finalized(
        {
            route.market.identity.market_id: ScannerPublicSnapshot(
                current_spread_price=Decimal("0.1"), liquidity_healthy=True
            )
        }
    )[0]
    assert observation.candidate is not None
    candidate = observation.candidate
    retained = route.coordinator.persist_scanner_candidate(
        candidate, observed_at=NOW + timedelta(hours=6)
    )
    linked = _direct_decision(route.market.identity.market_id, scanner_linkage=candidate.linkage)
    artifacts = _formalize(route, linked, candidate_id=retained.record_id)
    assert isinstance(artifacts, FormalizationArtifacts)
    assert artifacts.signal.payload["candidate_id"] == retained.record_id

    other_route = _route(tmp_path / "bad", count=64)
    missing = _direct_decision(
        other_route.market.identity.market_id, scanner_linkage=candidate.linkage
    )
    with pytest.raises(IntegrationError, match="not retained"):
        _formalize(other_route, missing, candidate_id="e" * 64)
    with pytest.raises(IntegrationError, match="requires retained Candidate"):
        _formalize(other_route, missing)
    assert other_route.evidence.count() == 0


def test_draining_blocks_new_activity_but_existing_outcome_completes_and_detaches(
    tmp_path: Path,
) -> None:
    route = _route(tmp_path)
    artifacts = _formalize(route, _direct_decision(route.market.identity.market_id))
    assert isinstance(artifacts, FormalizationArtifacts)
    successor = route.registry.lifecycle_update(
        "registry-draining",
        route.market.identity.market_id,
        MarketLifecycle.DRAINING,
        now=NOW + timedelta(hours=6),
    )
    route.registry.request_apply(successor.version)
    next_index = 60
    route.data.admit_rest_history(
        market=successor.markets[0],
        snapshot=[_payload(next_index, final=False)],
        received_at=datetime.fromtimestamp(((next_index + 1) * 300_000 + 1_000) / 1000, UTC),
    )
    with pytest.raises(IntegrationError, match="lifecycle"):
        route.coordinator.evaluate_finalized_market(
            market_id=route.market.identity.market_id,
            zone_book=_zones(route.market.identity.market_id),
        )
    start = int(artifacts.shadow_order.payload["outcome_start_ms"])
    for index in range(120):
        route.outcome.admit_bar(
            OneMinuteBar.create(
                market_id=route.market.identity.market_id,
                open_time_ms=start + index * 60_000,
                open=Decimal("100.1"),
                high=Decimal("100.2"),
                low=Decimal("100.0"),
                close=Decimal("100.1"),
            )
        )
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
        evidence_summary="accepted re-entry",
        outcome_summary="research only",
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
    artifacts = _formalize(route, _direct_decision(route.market.identity.market_id))
    assert isinstance(artifacts, FormalizationArtifacts)
    assert isinstance(route.evidence.get(artifacts.shadow_order.record_id), ShadowOrder)
    research = CorrelationResearchAdapter(route.evidence)
    assert research.completed_signals() == ()
    assert research.build_report({}).raw_market_level.raw_shadow_order_count == 0
    assert len(SetupFamily) == 3
