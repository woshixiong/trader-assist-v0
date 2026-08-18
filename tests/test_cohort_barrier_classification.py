"""PHASE 1 frozen contract: barrier retained-boundary classification.

Packet: COHORT_BARRIER_CLEAN_REPLACEMENT_V1_R2_NEW_GLM_20260818 sections 6A,
11, and rulings 2 (predecessor context is not recovery).  The five retained
exact-T state classes are distinct semantics owned by the Cohort Barrier and
must be decided BEFORE any provider request for T.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    ClosedBar,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import (
    CohortWitness,
    MarketRegistryManager,
    RegistryError,
)
from trader_assist_v0.multi_asset_shadow.runtime import (
    RetainedBoundaryClass,
    classify_retained_boundary,
)

FIVE_MINUTES_MS = 300_000
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
T = 100 * FIVE_MINUTES_MS


def market(
    coin: str = "BTC", lifecycle: MarketLifecycle = MarketLifecycle.WARMING
) -> RegistryMarket:
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


def active_registry(
    tmp_path: Path,
) -> tuple[MarketRegistryManager, MultiAssetDataAuthority, ClosedBarStore, RegistryMarket]:
    """Seed pending Registry activated through the first provider admission."""
    item = market()
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version="seed", created_at=NOW, markets=(item,))
    registry.stage(seed)
    registry.request_apply(seed.version)
    store = ClosedBarStore(tmp_path / "closed.sqlite")
    authority = MultiAssetDataAuthority(store=store, registry=registry)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=received_at(0)
    )
    assert registry.active() is not None
    return registry, authority, store, item


def contiguous_through(boundary: int) -> list[dict[str, object]]:
    """Candles 5m..boundary inclusive; contiguous with the seeded bar 0."""
    return [
        candle("BTC", open_ms)
        for open_ms in range(FIVE_MINUTES_MS, boundary + FIVE_MINUTES_MS, FIVE_MINUTES_MS)
    ]


def test_exact_t_row_bound_to_captured_epoch_is_current_epoch_finalized(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item, snapshot=contiguous_through(T), received_at=received_at(T)
    )
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.CURRENT_EPOCH_FINALIZED
    )


def test_exact_t_row_bound_to_known_predecessor_is_context_only(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    predecessor = registry.active()
    assert predecessor is not None
    authority.admit_rest_history(
        market=item, snapshot=contiguous_through(T), received_at=received_at(T)
    )
    successor = registry.successor(
        version="manual-r2",
        now=NOW,
        update_market=item.model_copy(update={"growth_mode": "HOT_ADD"}),
    )
    registry.request_apply(successor.version)
    # Once an active Registry exists the successor activates only through the
    # exact successor-bound cohort witness, never through a ClosedBar.
    authority.admit_rest_history(
        market=item,
        snapshot=[candle("BTC", T + FIVE_MINUTES_MS)],
        received_at=received_at(T + FIVE_MINUTES_MS),
    )
    witness = CohortWitness.create(
        boundary_open_time_ms=T + FIVE_MINUTES_MS,
        base_registry_version=predecessor.version,
        base_registry_hash=predecessor.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset({item.identity.market_id}),
        issuer="SINGLE_OWNER_5M_COHORT_BARRIER",
    )
    registry.apply_witness(witness, evidence_authority=authority)
    active = registry.active()
    assert active is not None and active.version == successor.version
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.PREDECESSOR_CONTEXT_ONLY
    )


def test_unknown_or_wrong_epoch_binding_is_integrity_failure(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None

    bar = ClosedBar.create(
        market_id=item.identity.market_id,
        open_time_ms=T,
        close_time_ms=T + FIVE_MINUTES_MS - 1,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        source_id="test",
        provenance_hash="0" * 64,
        received_at=received_at(T),
    )
    store.put(bar, registry_version="ghost-version", registry_content_hash="1" * 64)
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.INVALID_BINDING
    )
    with pytest.raises(RegistryError):
        registry.load_version("ghost-version")


def test_known_version_with_wrong_hash_is_invalid_binding(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None

    bar = ClosedBar.create(
        market_id=item.identity.market_id,
        open_time_ms=T,
        close_time_ms=T + FIVE_MINUTES_MS - 1,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        source_id="test",
        provenance_hash="0" * 64,
        received_at=received_at(T),
    )
    # Row claims a version name that exists but with a mismatched hash.
    store.put(bar, registry_version=active.version, registry_content_hash="2" * 64)
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.INVALID_BINDING
    )


def test_missing_row_coherent_through_t_minus_one_is_live_eligible(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item,
        snapshot=[candle("BTC", index * FIVE_MINUTES_MS) for index in range(1, 100)],
        received_at=received_at(99 * FIVE_MINUTES_MS),
    )
    assert store.last_open(item.identity.market_id) == T - FIVE_MINUTES_MS
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.MISSING_LIVE_ELIGIBLE
    )


def test_missing_row_behind_t_minus_one_needs_recovery(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item,
        snapshot=[candle("BTC", index * FIVE_MINUTES_MS) for index in range(1, 50)],
        received_at=received_at(49 * FIVE_MINUTES_MS),
    )
    assert store.last_open(item.identity.market_id) < T - FIVE_MINUTES_MS
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.MISSING_NEEDS_RECOVERY
    )


def test_current_epoch_t_row_with_later_row_remains_valid(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item,
        snapshot=contiguous_through(T + FIVE_MINUTES_MS),
        received_at=received_at(T + FIVE_MINUTES_MS),
    )
    # A valid current-R exact-T row does NOT become invalid merely because a
    # later T+1 durable row also exists (gate correction 3).  Backward/stale T
    # handling is Barrier freshness logic, never classification invalidation.
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.CURRENT_EPOCH_FINALIZED
    )


def test_predecessor_t_row_with_later_row_remains_context_only(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    predecessor = registry.active()
    assert predecessor is not None
    authority.admit_rest_history(
        market=item, snapshot=contiguous_through(T), received_at=received_at(T)
    )
    successor = registry.successor(
        version="manual-r2",
        now=NOW,
        update_market=item.model_copy(update={"growth_mode": "HOT_ADD"}),
    )
    registry.request_apply(successor.version)
    authority.admit_rest_history(
        market=item,
        snapshot=[candle("BTC", T + FIVE_MINUTES_MS)],
        received_at=received_at(T + FIVE_MINUTES_MS),
    )
    witness = CohortWitness.create(
        boundary_open_time_ms=T + FIVE_MINUTES_MS,
        base_registry_version=predecessor.version,
        base_registry_hash=predecessor.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset({item.identity.market_id}),
        issuer="SINGLE_OWNER_5M_COHORT_BARRIER",
    )
    registry.apply_witness(witness, evidence_authority=authority)
    active = registry.active()
    assert active is not None and active.version == successor.version
    # Predecessor-bound T stays context-only even though T+1 is durable.
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.PREDECESSOR_CONTEXT_ONLY
    )


def test_staged_never_active_binding_is_invalid(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item, snapshot=contiguous_through(T), received_at=received_at(T)
    )
    # A merely staged/validated candidate that was never the live authority is
    # NOT a predecessor epoch (gate correction 9).
    staged = registry.successor(
        version="staged-never-active",
        now=NOW,
        update_market=item.model_copy(update={"growth_mode": "HOT_ADD"}),
    )
    assert (tmp_path / "registry" / "versions" / f"{staged.version}.json").exists()
    assert registry.prior_active(staged.version) is None
    bar = ClosedBar.create(
        market_id=item.identity.market_id,
        open_time_ms=T,
        close_time_ms=T + FIVE_MINUTES_MS - 1,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        source_id="test",
        provenance_hash="0" * 64,
        received_at=received_at(T),
    )
    # Overwrite the T row with a binding to the staged-never-active candidate.
    store.connection.execute(
        "DELETE FROM closed_bars WHERE market_id=? AND interval='5m' AND open_time_ms=?",
        (item.identity.market_id, T),
    )
    store.connection.commit()
    store.put(
        bar,
        registry_version=staged.version,
        registry_content_hash=staged.content_hash,
    )
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.INVALID_BINDING
    )


def test_gap_beyond_t_without_t_row_is_integrity_failure(tmp_path: Path) -> None:
    registry, authority, store, item = active_registry(tmp_path)
    active = registry.active()
    assert active is not None
    authority.admit_rest_history(
        market=item,
        snapshot=[
            candle("BTC", open_ms)
            for open_ms in range(FIVE_MINUTES_MS, T, FIVE_MINUTES_MS)
        ],
        received_at=received_at(T - FIVE_MINUTES_MS),
    )
    # Durable row beyond T while the exact-T row is missing: a continuity hole
    # that cannot exist under the legal single-owner ordering.
    bar = ClosedBar.create(
        market_id=item.identity.market_id,
        open_time_ms=T + FIVE_MINUTES_MS,
        close_time_ms=T + 2 * FIVE_MINUTES_MS - 1,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("10"),
        source_id="test",
        provenance_hash="0" * 64,
        received_at=received_at(T + FIVE_MINUTES_MS),
    )
    store.put(
        bar,
        registry_version=active.version,
        registry_content_hash=active.content_hash,
    )
    assert (
        classify_retained_boundary(
            store=store,
            registry=registry,
            market_id=item.identity.market_id,
            boundary_open_ms=T,
            captured_version=active.version,
            captured_hash=active.content_hash,
        )
        is RetainedBoundaryClass.INVALID_BINDING
    )


def test_class_names_are_the_frozen_five_semantic_states() -> None:
    assert {member.value for member in RetainedBoundaryClass} == {
        "CURRENT_EPOCH_FINALIZED",
        "PREDECESSOR_CONTEXT_ONLY",
        "MISSING_LIVE_ELIGIBLE",
        "MISSING_NEEDS_RECOVERY",
        "INVALID_BINDING",
    }
