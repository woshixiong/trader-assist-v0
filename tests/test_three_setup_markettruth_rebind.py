"""Deterministic E4/Three Setup authority-seam tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.e4_markettruth import (
    E4MarketTruthProjection,
    E4PlanningData,
    E4ProjectionError,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.planning import Side, assess_l2
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager, RegistryError
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore as DomainStore
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    SourceEvent,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4Store

T = 1_800_000


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def _market(coin: str) -> RegistryMarket:
    raw = f"meta-{coin}".encode()
    return RegistryMarket(
        display=coin,
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin=coin),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=datetime(2026, 9, 27, tzinfo=UTC),
        metadata_hash=sha256_hex(raw),
    )


def _identity():
    markets = (_market("BTC"), _market("ETH"))
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=T * 1_000_000,
        expressions=tuple(
            MarketExpression(
                market_id=market.identity.market_id,
                dex="MAIN",
                provider_coin=market.identity.coin,
                instrument_id=f"{market.identity.coin}-PERP.HYPERLIQUID",
                expression_id=f"expr-{market.identity.coin}",
                instrument_metadata_version="v1",
                instrument_metadata_hash=market.metadata_hash,
            )
            for market in markets
        ),
    )
    manifest = RunManifest.create(
        run_id="ts4-e4-test",
        git_sha="a" * 40,
        git_tree="b" * 40,
        snapshot=snapshot,
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        capture_configuration={"bar_types": ["1-MINUTE", "5-MINUTE"]},
        subscription_policy={
            "discovery": [m.identity.market_id for m in markets],
            "watch": [m.identity.market_id for m in markets],
            "actionable": [m.identity.market_id for m in markets],
        },
        trial_ledger_id="ts4-test",
    )
    return markets, snapshot, manifest


def _setup(tmp_path: Path):
    markets, snapshot, manifest = _identity()
    e4 = E4Store(tmp_path / "e4")
    e4.initialize(manifest, snapshot)
    domain = DomainStore(tmp_path / "domain.sqlite")
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="ts4-initial",
        created_at=datetime(2026, 9, 27, tzinfo=UTC),
        markets=markets,
    )
    registry.stage(version)
    registry.request_apply(version.version)
    health = {
        "stream_health": "HEALTHY",
        "continuity_requirements_remaining": 0,
        "storage_failures": 0,
        "admitted_observer_failures": (),
    }
    projection = E4MarketTruthProjection(
        e4_store=e4,
        domain_evidence=domain,
        registry=registry,
        manifest=manifest,
        snapshot=snapshot,
        warmup_health=lambda: {"readiness": "READY"},
        capture_health=lambda: health,
        clock_ms=lambda: T + 301_000,
    )
    registry.bind_e4_evidence_authority(projection)
    return markets, e4, domain, registry, projection


def _event(
    market: RegistryMarket,
    *,
    ordinal: int,
    interval: str = "5m",
    open_ms: int = T,
    payload: dict | None = None,
    continuity: EvidenceState = EvidenceState.COMPLETE,
    continuity_epoch: str = "continuity-1",
    out_of_order: bool = False,
) -> AdmittedEvent:
    step = 300_000 if interval == "5m" else 60_000
    body = payload or {
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100",
        "volume": "10",
        "finalized": True,
    }
    source = SourceEvent.create(
        market_id=market.identity.market_id,
        expression_id=f"expr-{market.identity.coin}",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=f"{market.identity.coin}-PERP.HYPERLIQUID",
        data_kind=DataKind.BAR,
        source_event_id=f"bar:{interval}:{open_ms}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=(
            f"{market.identity.coin}-PERP.HYPERLIQUID-{step // 60_000}-MINUTE-LAST-EXTERNAL"
        ),
        ts_event=open_ms * 1_000_000,
        ts_init=(open_ms + step) * 1_000_000 + 1,
        true_network_receive_ts=None,
        payload=body,
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch=continuity_epoch,
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=source.ts_init,
        source_identity=source.replay_identity,
        out_of_order=out_of_order,
        continuity_state=continuity,
        source=source,
    )


def _depth_event(
    market: RegistryMarket,
    *,
    ordinal: int,
    now_ms: int = T + 300_500,
    bids: list[list[str]] | None = None,
    asks: list[list[str]] | None = None,
    bid_price: str | None = None,
    ask_price: str | None = None,
    continuity: EvidenceState = EvidenceState.COMPLETE,
    out_of_order: bool = False,
) -> AdmittedEvent:
    bids = bids or [["100", "10"], ["99.9", "10"]]
    asks = asks or [["100.1", "10"], ["100.2", "10"]]
    payload = {
        "bid_price": bid_price or bids[0][0],
        "bid_size": bids[0][1],
        "ask_price": ask_price or asks[0][0],
        "ask_size": asks[0][1],
        "native_depth": 10,
        "bids": bids,
        "asks": asks,
    }
    source = SourceEvent.create(
        market_id=market.identity.market_id,
        expression_id=f"expr-{market.identity.coin}",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id=f"{market.identity.coin}-PERP.HYPERLIQUID",
        data_kind=DataKind.DEPTH10,
        source_event_id=f"depth10:{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=f"native-depth10:{now_ms}",
        ts_event=now_ms * 1_000_000,
        ts_init=now_ms * 1_000_000 + 1,
        true_network_receive_ts=None,
        payload=payload,
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=source.ts_init,
        source_identity=source.replay_identity,
        out_of_order=out_of_order,
        continuity_state=continuity,
        source=source,
    )


def test_exact_t_initial_bootstrap_requires_full_durable_e4_cohort(tmp_path: Path) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    first = _event(markets[0], ordinal=1)
    e4.append_admission_batch((first,))
    assert projection.accept(first) == "5m"
    witness = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    with pytest.raises(RegistryError, match="incomplete"):
        registry.apply_initial_e4_witness(witness, evidence_authority=projection)
    assert registry.active() is None
    second = _event(markets[1], ordinal=2)
    e4.append_admission_batch((second,))
    assert projection.accept(second) == "5m"
    witness = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    assert (
        registry.apply_initial_e4_witness(witness, evidence_authority=projection).version
        == "ts4-initial"
    )
    with pytest.raises(RegistryError, match="already consumed"):
        registry.apply_initial_e4_witness(witness, evidence_authority=projection)
    assert projection.accept(second) is None
    domain.close()
    projection.close()


def test_depth10_1000_gate_equivalence_and_bad_books(tmp_path: Path) -> None:
    from dataclasses import replace

    from trader_assist_v0.multi_asset_shadow.planning import CostModel, PlanInputs, make_plan

    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _depth_event(markets[0], ordinal=1)
    e4.append_admission_batch((event,))
    projection.accept(event)
    planning = E4PlanningData(projection)
    bbo = planning.fetch_bbo(market=markets[0], now_ms=T + 301_000)
    l2 = planning.fetch_l2(market=markets[0], side=Side.LONG, bbo=bbo)
    expected = assess_l2(
        market_id=markets[0].identity.market_id,
        coin="BTC",
        side=Side.LONG,
        observed_at_ms=event.source.ts_event // 1_000_000,
        best_bid=Decimal("100"),
        best_ask=Decimal("100.1"),
        levels=((Decimal("100.1"), Decimal("10")), (Decimal("100.2"), Decimal("10"))),
        provenance_hash=event.admission_hash,
    )
    assert l2.levels == ((Decimal("100.1"), Decimal("10")), (Decimal("100.2"), Decimal("10")))
    assert expected.sufficient_depth
    observed = assess_l2(
        market_id=l2.market_id,
        coin=l2.coin,
        side=Side.LONG,
        observed_at_ms=l2.observed_at_ms,
        best_bid=l2.best_bid,
        best_ask=l2.best_ask,
        levels=l2.levels,
        provenance_hash=l2.provenance_hash,
    )
    assert observed == expected
    inputs = PlanInputs(
        market_id=markets[0].identity.market_id,
        side=Side.LONG,
        ideal_entry_low=Decimal("100"),
        ideal_entry_high=Decimal("101"),
        chase_limit=Decimal("102"),
        structural_stop=Decimal("99"),
        structural_target=Decimal("105"),
        liquidity=observed,
        cost_model=CostModel("fixed", Decimal("1"), Decimal("1"), Decimal("2")),
        now_ms=T + 301_000,
    )
    assert make_plan(inputs, bbo) == make_plan(replace(inputs, liquidity=expected), bbo)
    with pytest.raises(Exception, match="stale"):
        projection.current_depth(markets[0].identity.market_id, T + 320_000)
    crossed = _depth_event(markets[1], ordinal=2, asks=[["99", "10"]])
    with pytest.raises(E4ProjectionError, match="crossed"):
        projection.accept(crossed)
    domain.close()
    projection.close()


def test_outcome_ref_restarts_without_ohlc_duplicate(tmp_path: Path) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _event(markets[0], ordinal=1, interval="1m", open_ms=T)
    e4.append_admission_batch((event,))
    projection.accept(event)
    bar = projection.one_minute_window(markets[0].identity.market_id, T, T + 60_000)[0]
    ref = projection.outcome_reference(bar)
    domain._write_controlled((ref,))
    assert set(ref.payload).isdisjoint({"open", "high", "low", "close", "volume"})
    before = e4.admission_columns_path.read_bytes()
    projection.close()
    restarted = E4MarketTruthProjection(
        e4_store=e4,
        domain_evidence=domain,
        registry=registry,
        manifest=e4.load_manifest(),
        snapshot=e4.load_snapshot(),
        warmup_health=lambda: {"readiness": "READY"},
        capture_health=lambda: {
            "stream_health": "HEALTHY",
            "continuity_requirements_remaining": 0,
            "storage_failures": 0,
        },
        clock_ms=lambda: T + 301_000,
    )
    assert restarted.resolve_outcome_reference(ref) == bar
    assert e4.admission_columns_path.read_bytes() == before
    restarted.close()
    domain.close()


def test_active_entrypoint_never_constructs_legacy_market_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import inspect
    import sys
    from types import ModuleType

    from trader_assist_v0.multi_asset_shadow import bootstrap as legacy_bootstrap
    from trader_assist_v0.multi_asset_shadow import data as legacy_data
    from trader_assist_v0.multi_asset_shadow import hyperliquid_public as legacy_public
    from trader_assist_v0.multi_asset_shadow import production
    from trader_assist_v0.multi_asset_shadow.planning import CostModel

    markets, e4, domain, registry, projection = _setup(tmp_path)
    del markets, registry
    projection.close()
    domain.close()
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", tmp_path / "domain.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", tmp_path / "registry")
    monkeypatch.setattr(production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed.sqlite")
    calls: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> object:
        calls.append("legacy")
        raise AssertionError("legacy public market path reached")

    monkeypatch.setattr(legacy_data, "ClosedBarStore", forbidden)
    monkeypatch.setattr(legacy_data, "MultiAssetDataAuthority", forbidden)
    monkeypatch.setattr(legacy_public, "HyperliquidPublicClient", forbidden)
    monkeypatch.setattr(legacy_public, "OfficialMetadataValidator", forbidden)
    monkeypatch.setattr(legacy_bootstrap.MultiAssetProductionBootstrap, "compose", forbidden)

    class Node:
        def add_strategy(self, strategy: object) -> None:
            self.strategy = strategy

    class Capture:
        def __init__(self) -> None:
            self.warmup_health = {"readiness": "READY"}
            self.capture_health = {
                "stream_health": "HEALTHY",
                "continuity_requirements_remaining": 0,
                "storage_failures": 0,
                "admitted_observer_failures": (),
            }

        def set_admitted_event_observer(self, observer: object) -> None:
            self.observer = observer

    node = Node()
    capture = Capture()
    fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
    fake_host.build_public_data_node = lambda: node  # type: ignore[attr-defined]
    fake_host.build_capture_strategy = lambda **_kwargs: capture  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "trader_assist_v0.nautilus_e4.host", fake_host)
    config = production.ThreeSetupProductionConfig(
        release_sha="a" * 40,
        evidence_store_path=tmp_path / "domain.sqlite",
        registry_root=tmp_path / "registry",
        closed_bar_store_path=root / "closed.sqlite",
        cost_model=CostModel("test", Decimal("1"), Decimal("1"), Decimal("1")),
        e4_evidence_root=tmp_path / "e4",
        e4_manifest_path=e4.manifest_path,
        e4_snapshot_path=e4.snapshot_path,
        e4_bar_types=(
            "BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
            "BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
            "ETH-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
            "ETH-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
        ),
    )
    signature = inspect.signature(production.compose_three_setup_application)
    assert "public_client" not in signature.parameters
    with pytest.raises(TypeError, match="public_client"):
        production.compose_three_setup_application(
            config=config,
            notification_adapter=object(),
            public_client=object(),  # type: ignore[call-arg]
        )
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=object(),
        clock=lambda: datetime.fromtimestamp((T + 301_000) / 1000, UTC),
    )
    assert isinstance(application, production.E4ThreeSetupProductionApplication)
    assert node.strategy is capture and capture.observer is not None
    assert calls == []
    assert not config.closed_bar_store_path.exists()
    application.bootstrap.close()
    application.projection.close()


def test_restart_missing_e4_lineage_ref_fails_closed(tmp_path: Path) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _event(markets[0], ordinal=1, interval="1m")
    e4.append_admission_batch((event,))
    projection.accept(event)
    bar = projection.one_minute_window(markets[0].identity.market_id, T, T + 60_000)[0]
    ref = projection.outcome_reference(bar)
    domain._write_controlled((ref,))
    projection.close()
    e4.admission_columns_path.unlink()
    restarted = E4MarketTruthProjection(
        e4_store=e4,
        domain_evidence=domain,
        registry=registry,
        manifest=e4.load_manifest(),
        snapshot=e4.load_snapshot(),
        warmup_health=lambda: {"readiness": "READY"},
        capture_health=lambda: {
            "stream_health": "HEALTHY",
            "continuity_requirements_remaining": 0,
            "storage_failures": 0,
        },
        clock_ms=lambda: T + 301_000,
    )
    with pytest.raises(E4ProjectionError, match="missing or corrupt"):
        restarted.resolve_outcome_reference(ref)
    restarted.close()
    domain.close()


@async_test
async def test_exact_t_missing_peer_waits_then_wakes_once(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.multi_asset_shadow.runtime import E4ThreeSetupRuntime

    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        projection.accept(event)
    witness = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    registry.apply_initial_e4_witness(witness, evidence_authority=projection)
    current_ms = T + 601_000
    projection.clock_ms = lambda: current_ms
    runtime = E4ThreeSetupRuntime(
        projection=projection,
        registry=registry,
        clock=lambda: datetime.fromtimestamp(current_ms / 1000, UTC),
    )
    wakes: list[tuple[int, str]] = []

    async def on_boundary(bar: object, mode: object) -> object:
        wakes.append((bar.open_time_ms, mode.value))
        return SimpleNamespace(disposition=SimpleNamespace(value="PROCESSED"))

    runtime.on_finalized_5m = on_boundary
    first = _event(markets[0], ordinal=3, open_ms=T + 300_000)
    e4.append_admission_batch((first,))
    projection.accept(first)
    await runtime._on_5m(first)
    assert wakes == []
    second = _event(markets[1], ordinal=4, open_ms=T + 300_000)
    e4.append_admission_batch((second,))
    projection.accept(second)
    await runtime._on_5m(second)
    await runtime._on_5m(second)
    assert wakes == [(T + 300_000, "LIVE_ACTIONABLE")]
    projection.close()
    domain.close()


@async_test
async def test_late_context_cohort_never_replays_as_live_action(tmp_path: Path) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.multi_asset_shadow.runtime import E4ThreeSetupRuntime

    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        projection.accept(event)
    registry.apply_initial_e4_witness(
        registry.issue_initial_e4_witness(boundary_open_time_ms=T),
        evidence_authority=projection,
    )
    now_ms = T + 700_000
    projection.clock_ms = lambda: now_ms
    runtime = E4ThreeSetupRuntime(
        projection=projection,
        registry=registry,
        clock=lambda: datetime.fromtimestamp(now_ms / 1000, UTC),
    )
    wakes: list[tuple[int, str]] = []

    async def on_boundary(bar: object, mode: object) -> object:
        wakes.append((bar.open_time_ms, mode.value))
        return SimpleNamespace(disposition=SimpleNamespace(value="PROCESSED"))

    runtime.on_finalized_5m = on_boundary
    late = tuple(_event(m, ordinal=i + 3, open_ms=T + 300_000) for i, m in enumerate(markets))
    e4.append_admission_batch(late)
    for event in late:
        projection.accept(event)
    for event in late:
        await runtime._on_5m(event)
    assert wakes == [(T + 300_000, "RECOVERY_CONTEXT_ONLY")]
    now_ms = T + 901_000
    current = tuple(_event(m, ordinal=i + 5, open_ms=T + 600_000) for i, m in enumerate(markets))
    e4.append_admission_batch(current)
    for event in current:
        projection.accept(event)
    for event in current:
        await runtime._on_5m(event)
    assert wakes == [
        (T + 300_000, "RECOVERY_CONTEXT_ONLY"),
        (T + 600_000, "LIVE_ACTIONABLE"),
    ]
    projection.close()
    domain.close()


@async_test
async def test_gapped_strategy_cohort_runs_while_registry_evidence_stays_strict(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.multi_asset_shadow.runtime import E4ThreeSetupRuntime

    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        projection.accept(event)
    active = registry.apply_initial_e4_witness(
        registry.issue_initial_e4_witness(boundary_open_time_ms=T),
        evidence_authority=projection,
    )
    health = {
        "stream_health": "REESTABLISHING",
        "continuity_requirements_remaining": 2,
        "storage_failures": 0,
        "admitted_observer_failures": (),
        "continuity_epoch": "continuity-2",
    }
    projection._capture_health = lambda: health
    required = frozenset(m.identity.market_id for m in markets)
    assert not projection.prove_boundary_evidence(
        boundary_open_time_ms=T,
        market_ids=required,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
    )
    now_ms = T + 601_000
    projection.clock_ms = lambda: now_ms
    runtime = E4ThreeSetupRuntime(
        projection=projection,
        registry=registry,
        clock=lambda: datetime.fromtimestamp(now_ms / 1000, UTC),
    )
    wakes: list[tuple[int, str]] = []

    async def on_boundary(bar: object, mode: object) -> object:
        wakes.append((bar.open_time_ms, mode.value))
        return SimpleNamespace(disposition=SimpleNamespace(value="PROCESSED"))

    runtime.on_finalized_5m = on_boundary
    mixed = (
        _event(markets[0], ordinal=3, open_ms=T + 300_000, continuity=EvidenceState.GAPPED),
        _event(
            markets[1],
            ordinal=4,
            open_ms=T + 300_000,
            continuity=EvidenceState.GAPPED,
            continuity_epoch="continuity-2",
        ),
    )
    e4.append_admission_batch(mixed)
    for event in mixed:
        assert event.continuity_state is EvidenceState.GAPPED
        assert not event.out_of_order
        assert projection.accept(event) == "5m"
        await runtime._on_5m(event)
    assert set(projection.readiness_snapshot().ready_market_ids) == required
    assert not projection.prove_boundary_evidence(
        boundary_open_time_ms=T + 300_000,
        market_ids=required,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
    )
    assert wakes == [(T + 300_000, "LIVE_ACTIONABLE")]
    successor = registry.lifecycle_successor(
        version="same-epoch-next",
        updates={markets[0].identity.market_id: MarketLifecycle.DRAINING},
        now=datetime(2026, 9, 27, tzinfo=UTC),
    )
    registry.request_apply(successor.version)
    mixed_witness = registry._issue_cohort_witness(
        boundary_open_time_ms=T + 300_000,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=required,
    )
    with pytest.raises(RegistryError, match="evidence cohort is not proven"):
        registry.apply_witness(mixed_witness, evidence_authority=projection)
    assert registry.active() == active

    now_ms = T + 901_000
    later = tuple(
        _event(
            m,
            ordinal=i + 5,
            open_ms=T + 600_000,
            continuity_epoch="continuity-2",
        )
        for i, m in enumerate(markets)
    )
    e4.append_admission_batch(later)
    for event in later:
        projection.accept(event)
        await runtime._on_5m(event)
    assert projection.prove_boundary_evidence(
        boundary_open_time_ms=T + 600_000,
        market_ids=required,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
    )
    assert wakes == [
        (T + 300_000, "LIVE_ACTIONABLE"),
        (T + 600_000, "LIVE_ACTIONABLE"),
    ]
    assert registry.active() == successor
    await runtime._on_5m(mixed[1])
    await runtime._on_5m(mixed[1])
    assert wakes.count((T + 600_000, "LIVE_ACTIONABLE")) == 1
    assert wakes.count((T + 300_000, "LIVE_ACTIONABLE")) == 1
    projection.close()
    domain.close()


@async_test
async def test_domain_adapter_exception_is_observable_and_does_not_touch_e4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from trader_assist_v0.multi_asset_shadow.runtime import E4ThreeSetupRuntime

    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _event(markets[0], ordinal=1)
    e4.append_admission_batch((event,))
    before = e4.admission_columns_path.read_bytes()
    runtime = E4ThreeSetupRuntime(
        projection=projection,
        registry=registry,
        clock=lambda: datetime.fromtimestamp((T + 301_000) / 1000, UTC),
    )
    failures: list[tuple[str, str, str]] = []
    runtime.on_domain_error = lambda *args: failures.append(args)
    monkeypatch.setattr(
        projection,
        "accept",
        lambda _event: (_ for _ in ()).throw(ValueError("domain")),
    )
    shutdown = asyncio.Event()
    task = asyncio.create_task(runtime.run(shutdown))
    await asyncio.sleep(0)
    runtime.offer_admission(event)
    await asyncio.wait_for(runtime._queue.join(), timeout=2)
    shutdown.set()
    await task
    assert failures == [(markets[0].identity.market_id, event.admission_hash, "ValueError")]
    assert projection.market_failed(markets[0].identity.market_id)
    assert e4.admission_columns_path.read_bytes() == before
    projection.close()
    domain.close()


def test_e4_outcome_and_legacy_outcome_bar_read_together(tmp_path: Path) -> None:
    from dataclasses import asdict

    from trader_assist_v0.multi_asset_shadow.integration import EvidenceOutcomeAdapter
    from trader_assist_v0.multi_asset_shadow.outcome_engine import OneMinuteBar
    from trader_assist_v0.multi_asset_shadow.shadow_records import OutcomeBarEvidence

    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _event(markets[0], ordinal=1, interval="1m")
    e4.append_admission_batch((event,))
    projection.accept(event)
    e4_bar = projection.one_minute_window(markets[0].identity.market_id, T, T + 60_000)[0]
    domain._write_controlled((projection.outcome_reference(e4_bar),))
    legacy_bar = OneMinuteBar.create(
        market_id=markets[0].identity.market_id,
        open_time_ms=T + 60_000,
        open=Decimal("101"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101"),
    )
    legacy = OutcomeBarEvidence.create(
        identity={
            "market_id": legacy_bar.market_id,
            "open_time_ms": legacy_bar.open_time_ms,
            "canonical_hash": legacy_bar.canonical_hash,
        },
        **asdict(legacy_bar),
    )
    domain._write_controlled((legacy,))
    adapter = EvidenceOutcomeAdapter(domain, e4_projection=projection)
    assert adapter._retained_bars({markets[0].identity.market_id: ((T, T + 120_000),)}) == (
        e4_bar,
        legacy_bar,
    )
    projection.close()
    domain.close()


def test_scanner_semantics_equal_for_equivalent_e4_and_legacy_bars(tmp_path: Path) -> None:
    from dataclasses import replace

    from trader_assist_v0.multi_asset_shadow.integration import MultiAssetShadowCoordinator
    from trader_assist_v0.multi_asset_shadow.models import ClosedBar
    from trader_assist_v0.multi_asset_shadow.strategy_kernel.engine import (
        StrategyEvaluationInput,
        evaluate_strategy,
    )
    from trader_assist_v0.multi_asset_shadow.strategy_kernel.scanner import (
        ScannerMarketInput,
        scan_cross_section,
    )

    markets, e4, domain, registry, projection = _setup(tmp_path)
    market = markets[0]
    events = []
    legacy = []
    for index in range(64):
        open_ms = T + index * 300_000
        open_price = Decimal("100") + Decimal(index) / 10
        payload = {
            "open": str(open_price),
            "high": str(open_price + 1),
            "low": str(open_price - 1),
            "close": str(open_price + Decimal("0.5")),
            "volume": str(10 + index),
            "finalized": True,
        }
        events.append(_event(market, ordinal=index + 1, open_ms=open_ms, payload=payload))
        legacy.append(
            ClosedBar.create(
                market_id=market.identity.market_id,
                open_time_ms=open_ms,
                close_time_ms=open_ms + 299_999,
                open=open_price,
                high=open_price + 1,
                low=open_price - 1,
                close=open_price + Decimal("0.5"),
                volume=Decimal(10 + index),
                source_id="legacy-fixture",
                provenance_hash=sha256_hex(str(index).encode()),
                received_at=datetime.fromtimestamp((open_ms + 300_000) / 1000, UTC),
            )
        )
    e4.append_admission_batch(tuple(events))
    for event in events:
        projection.accept(event)
    projected = projection.store.tail_bars(
        market.identity.market_id, at_or_before_ms=T + 63 * 300_000, limit=64
    )
    assert len(projected) == 64
    assert tuple((b.open, b.high, b.low, b.close, b.volume) for b in projected) == tuple(
        (b.open, b.high, b.low, b.close, b.volume) for b in legacy
    )

    def scan(bars: tuple[ClosedBar, ...]):
        return scan_cross_section(
            (
                ScannerMarketInput(
                    market_id=market.identity.market_id,
                    bars_5m=tuple(MultiAssetShadowCoordinator._strategy_bar(item) for item in bars),
                    minimum_tick=Decimal("0.1"),
                    current_spread_price=Decimal("0.1"),
                    liquidity_healthy=True,
                    history_count=64,
                ),
            )
        )

    projected_scan = scan(projected)[0]
    legacy_scan = scan(tuple(legacy))[0]
    assert projected_scan.metrics == legacy_scan.metrics
    assert projected_scan.candidate is not None and legacy_scan.candidate is not None
    assert replace(projected_scan.candidate, candidate_id="LINEAGE") == replace(
        legacy_scan.candidate, candidate_id="LINEAGE"
    )

    def evaluate(bars: tuple[ClosedBar, ...]):
        normalized = tuple(
            replace(MultiAssetShadowCoordinator._strategy_bar(item), source_identity="FIXTURE")
            for item in bars
        )
        return evaluate_strategy(
            StrategyEvaluationInput(bars_5m=normalized, minimum_tick=Decimal("0.1"))
        )

    assert evaluate(projected) == evaluate(tuple(legacy))
    projection.close()
    domain.close()


def test_e4_registry_successor_witness_mismatch_foreign_and_crash_convergence(
    tmp_path: Path,
) -> None:
    from trader_assist_v0.contracts.common import canonical_json_bytes

    markets, e4, domain, registry, projection = _setup(tmp_path)
    first = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(first)
    for event in first:
        projection.accept(event)
    initial = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    active = registry.apply_initial_e4_witness(initial, evidence_authority=projection)
    successor = registry.lifecycle_successor(
        version="draining",
        updates={markets[0].identity.market_id: MarketLifecycle.DRAINING},
        now=datetime(2026, 9, 27, tzinfo=UTC),
    )
    registry.request_apply(successor.version)
    second = tuple(_event(m, ordinal=i + 3, open_ms=T + 300_000) for i, m in enumerate(markets))
    e4.append_admission_batch(second)
    for event in second:
        projection.accept(event)
    required = frozenset(m.identity.market_id for m in markets)

    def witness(manager: MarketRegistryManager):
        return manager._issue_cohort_witness(
            boundary_open_time_ms=T + 300_000,
            base_registry_version=active.version,
            base_registry_hash=active.content_hash,
            expected_successor_version=successor.version,
            expected_successor_hash=successor.content_hash,
            required_evidence_market_ids=required,
        )

    foreign = MarketRegistryManager(registry.root, metadata_validator=lambda _: True)
    with pytest.raises(RegistryError, match="not issued"):
        registry.apply_witness(witness(foreign), evidence_authority=projection)
    assert registry.active() == active
    other = RegistryVersion.create(
        version="other-pending",
        created_at=datetime(2026, 9, 27, tzinfo=UTC),
        markets=markets,
    )
    registry.stage(other)
    mismatch = witness(registry)
    registry.request_apply(other.version)
    with pytest.raises(RegistryError, match="expected successor"):
        registry.apply_witness(mismatch, evidence_authority=projection)
    assert registry.active() == active
    registry.request_apply(successor.version)
    valid = witness(registry)
    assert registry.apply_witness(valid, evidence_authority=projection) == successor
    with pytest.raises(RegistryError, match="already consumed"):
        registry.apply_witness(valid, evidence_authority=projection)
    # A crash after the pointer switch but before pending cleanup converges on readback.
    registry.pending.write_bytes(
        canonical_json_bytes({"version": successor.version, "content_hash": successor.content_hash})
    )
    assert registry.reconcile_pending() is None
    assert registry.pending_version() is None
    assert registry.active() == successor
    projection.close()
    domain.close()


def test_e4_warmup_and_continuity_incomplete_block_initial_registry(tmp_path: Path) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    events = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(events)
    for event in events:
        projection.accept(event)
    projection._warmup_health = lambda: {"readiness": "NOT_READY"}
    witness = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    with pytest.raises(RegistryError, match="incomplete"):
        registry.apply_initial_e4_witness(witness, evidence_authority=projection)
    projection._warmup_health = lambda: {"readiness": "READY"}
    projection._capture_health = lambda: {
        "stream_health": "REESTABLISHING",
        "continuity_requirements_remaining": 1,
        "storage_failures": 0,
    }
    witness = registry.issue_initial_e4_witness(boundary_open_time_ms=T)
    with pytest.raises(RegistryError, match="incomplete"):
        registry.apply_initial_e4_witness(witness, evidence_authority=projection)
    assert registry.active() is None
    projection.close()
    domain.close()


def test_e4_readiness_health_defects_then_future_cohort_recovery(tmp_path: Path) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        projection.accept(event)
    registry.apply_initial_e4_witness(
        registry.issue_initial_e4_witness(boundary_open_time_ms=T),
        evidence_authority=projection,
    )
    healthy = {
        "stream_health": "HEALTHY",
        "continuity_requirements_remaining": 0,
        "storage_failures": 0,
        "admitted_observer_failures": (),
    }
    projection._capture_health = lambda: healthy
    projection._warmup_health = lambda: {"readiness": "READY"}
    assert len(projection.readiness_snapshot().ready_market_ids) == 2
    for allowed in ({"stream_health": "REESTABLISHING", "continuity_requirements_remaining": 1},):
        projection._capture_health = lambda allowed=allowed: healthy | allowed
        assert len(projection.readiness_snapshot().ready_market_ids) == 2
    for defect in (
        {"stream_health": "DISCONNECTED"},
        {"storage_failures": 1},
        {"admitted_observer_failures": ("domain",)},
    ):
        projection._capture_health = lambda defect=defect: healthy | defect
        assert projection.readiness_snapshot().ready_market_ids == ()
    projection._warmup_health = lambda: {"readiness": "NOT_READY"}
    projection._capture_health = lambda: healthy
    assert projection.readiness_snapshot().ready_market_ids == ()
    projection._warmup_health = lambda: {"readiness": "READY"}
    future = tuple(_event(m, ordinal=i + 3, open_ms=T + 300_000) for i, m in enumerate(markets))
    e4.append_admission_batch(future)
    for event in future:
        projection.accept(event)
    projection.clock_ms = lambda: T + 601_000
    assert set(projection.readiness_snapshot().ready_market_ids) == {
        m.identity.market_id for m in markets
    }
    projection.close()
    domain.close()


def test_strategy_readiness_enforces_close_deadline_and_contiguous_5m_history(
    tmp_path: Path,
) -> None:
    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        projection.accept(event)
    registry.apply_initial_e4_witness(
        registry.issue_initial_e4_witness(boundary_open_time_ms=T),
        evidence_authority=projection,
    )
    projection.clock_ms = lambda: T + 360_000
    assert len(projection.readiness_snapshot().ready_market_ids) == 2
    projection.clock_ms = lambda: T + 360_001
    assert projection.readiness_snapshot().ready_market_ids == ()

    gapped_history = tuple(
        _event(m, ordinal=i + 3, open_ms=T + 600_000) for i, m in enumerate(markets)
    )
    e4.append_admission_batch(gapped_history)
    for event in gapped_history:
        projection.accept(event)
    projection.clock_ms = lambda: T + 901_000
    assert projection.readiness_snapshot().ready_market_ids == ()
    projection.close()
    domain.close()


@async_test
async def test_late_5m_gap_fill_stays_durable_without_strategy_projection(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.multi_asset_shadow.runtime import E4ThreeSetupRuntime

    markets, e4, domain, registry, projection = _setup(tmp_path)
    initial = tuple(_event(m, ordinal=i + 1) for i, m in enumerate(markets))
    e4.append_admission_batch(initial)
    for event in initial:
        assert projection.accept(event) == "5m"
    registry.apply_initial_e4_witness(
        registry.issue_initial_e4_witness(boundary_open_time_ms=T),
        evidence_authority=projection,
    )

    gap_market = markets[0]
    missing_open = T + 5_100_000
    pre_late_latest = missing_open + 300_000
    ordinal = 3
    history = []
    for open_ms in range(T + 300_000, pre_late_latest + 1, 300_000):
        for market in markets:
            if market == gap_market and open_ms == missing_open:
                continue
            event = _event(market, ordinal=ordinal, open_ms=open_ms)
            ordinal += 1
            history.append(event)
    e4.append_admission_batch(tuple(history))
    for event in history:
        assert projection.accept(event) == "5m"

    projection.clock_ms = lambda: pre_late_latest + 301_000
    assert not projection.store.is_contiguous_5m(gap_market.identity.market_id)
    assert projection.readiness_snapshot().ready_market_ids == ()
    derived_before = projection.store.connection.execute(
        "SELECT COUNT(*) FROM closed_bars WHERE market_id=? AND interval IN ('15m','60m')",
        (gap_market.identity.market_id,),
    ).fetchone()[0]

    late = _event(
        gap_market,
        ordinal=ordinal,
        open_ms=missing_open,
        continuity=EvidenceState.GAPPED,
        out_of_order=True,
    )
    ordinal += 1
    e4.append_admission_batch((late,))
    durable = next(
        event for event in e4.load_admissions() if event.admission_hash == late.admission_hash
    )
    assert durable.out_of_order is True
    assert durable.continuity_state is EvidenceState.GAPPED
    assert projection.accept(late) is None

    slot = (gap_market.identity.market_id, "5m", missing_open)
    assert slot not in projection._bar_events
    assert (
        projection.store.connection.execute(
            "SELECT 1 FROM closed_bars WHERE market_id=? AND interval='5m' AND open_time_ms=?",
            (gap_market.identity.market_id, missing_open),
        ).fetchone()
        is None
    )
    assert late.admission_hash.encode() not in domain.export_jsonl()
    derived_after = projection.store.connection.execute(
        "SELECT COUNT(*) FROM closed_bars WHERE market_id=? AND interval IN ('15m','60m')",
        (gap_market.identity.market_id,),
    ).fetchone()[0]
    assert derived_after == derived_before

    projected_open_times = {
        bar.open_time_ms
        for bar in projection.store.tail_bars(
            gap_market.identity.market_id, at_or_before_ms=pre_late_latest, limit=64
        )
    }
    assert missing_open not in projected_open_times
    assert pre_late_latest in projected_open_times
    assert not projection.store.is_contiguous_5m(gap_market.identity.market_id)
    readiness = projection.readiness_snapshot()
    assert readiness.data_ready is False
    assert readiness.ready_market_ids == ()

    future_open = pre_late_latest + 300_000
    future = tuple(
        _event(m, ordinal=ordinal + i, open_ms=future_open) for i, m in enumerate(markets)
    )
    e4.append_admission_batch(future)
    for event in future:
        assert projection.accept(event) == "5m"
    projection.clock_ms = lambda: future_open + 301_000
    assert not projection.store.is_contiguous_5m(gap_market.identity.market_id)
    assert projection.readiness_snapshot().ready_market_ids == ()

    runtime = E4ThreeSetupRuntime(
        projection=projection,
        registry=registry,
        clock=lambda: datetime.fromtimestamp((future_open + 301_000) / 1000, UTC),
    )
    wakes: list[tuple[int, str]] = []

    async def on_boundary(bar: object, mode: object) -> object:
        wakes.append((bar.open_time_ms, mode.value))
        return SimpleNamespace(disposition=SimpleNamespace(value="PROCESSED"))

    runtime.on_finalized_5m = on_boundary
    for event in future:
        await runtime._on_5m(event)
    assert wakes == []
    projection.close()
    domain.close()


def test_late_5m_same_slot_duplicate_and_conflict_are_decided_before_discard(
    tmp_path: Path,
) -> None:
    markets, e4, domain, _registry, projection = _setup(tmp_path)
    current = _event(markets[0], ordinal=1)
    e4.append_admission_batch((current,))
    assert projection.accept(current) == "5m"

    duplicate = _event(markets[0], ordinal=2, out_of_order=True)
    e4.append_admission_batch((duplicate,))
    assert projection.accept(duplicate) is None
    assert not projection.market_failed(markets[0].identity.market_id)

    payload = dict(current.source.payload)
    payload["close"] = "100.5"
    conflict = _event(markets[0], ordinal=3, payload=payload, out_of_order=True)
    e4.append_admission_batch((conflict,))
    with pytest.raises(E4ProjectionError, match="conflicting E4 closed-bar slot"):
        projection.accept(conflict)
    assert projection.market_failed(markets[0].identity.market_id)
    projection.close()
    domain.close()


def test_gapped_depth_is_usable_and_older_snapshot_is_ignored_without_market_poison(
    tmp_path: Path,
) -> None:
    markets, e4, domain, _registry, projection = _setup(tmp_path)
    current = _depth_event(
        markets[0],
        ordinal=1,
        continuity=EvidenceState.GAPPED,
        now_ms=T + 300_500,
    )
    e4.append_admission_batch((current,))
    projection.accept(current)
    assert projection.current_depth(markets[0].identity.market_id, T + 301_000) == current

    older = _depth_event(
        markets[0],
        ordinal=2,
        continuity=EvidenceState.GAPPED,
        out_of_order=True,
        now_ms=T + 300_000,
    )
    e4.append_admission_batch((older,))
    projection.accept(older)
    assert projection.current_depth(markets[0].identity.market_id, T + 301_000) == current
    assert not projection.market_failed(markets[0].identity.market_id)
    projection.close()
    domain.close()


def test_depth10_unordered_and_top_of_book_mismatch_fail_closed(tmp_path: Path) -> None:
    markets, e4, domain, _registry, projection = _setup(tmp_path)
    unordered = _depth_event(
        markets[0],
        ordinal=1,
        bids=[["99.9", "10"], ["100", "10"]],
    )
    e4.append_admission_batch((unordered,))
    with pytest.raises(E4ProjectionError, match="not ordered"):
        projection.accept(unordered)

    mismatch = _depth_event(markets[1], ordinal=2, bid_price="99")
    e4.append_admission_batch((mismatch,))
    with pytest.raises(E4ProjectionError, match="top-of-book"):
        projection.accept(mismatch)
    projection.close()
    domain.close()


def test_depth10_future_conflict_and_insufficient_liquidity_fail_closed(tmp_path: Path) -> None:
    from trader_assist_v0.multi_asset_shadow.hyperliquid_public import PublicDataError

    markets, e4, domain, registry, projection = _setup(tmp_path)
    event = _depth_event(markets[0], ordinal=1, asks=[["100.1", "0.001"]])
    e4.append_admission_batch((event,))
    projection.accept(event)
    with pytest.raises(PublicDataError, match="future"):
        projection.current_depth(markets[0].identity.market_id, T + 300_000)
    snapshot = E4PlanningData(projection).fetch_scanner_snapshot(
        market=markets[0],
        now_ms=T + 301_000,
        btc_returns=(None, None, None),
    )
    assert snapshot.liquidity_healthy is False
    conflict = _depth_event(markets[0], ordinal=2, asks=[["100.2", "1"]])
    e4.append_admission_batch((conflict,))
    with pytest.raises(E4ProjectionError, match="conflicting"):
        projection.accept(conflict)
    assert projection.market_failed(markets[0].identity.market_id)
    projection.close()
    domain.close()
