"""PHASE 1 frozen contract: exact successor-bound Registry cohort witness.

Packet sections 13, 16, 17, 18 and attacks R, S, T, AD, AE, AF, AW.  Once an
active Registry exists, a successor activates only through a one-use witness
that re-reads live active/pending state and requires exact equality with the
witness binding plus a non-empty, proven required evidence cohort.  Registry
persistence naming/layout/schema must remain byte-compatible.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
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


class Composition:
    """One active Registry plus its data authority and evidence rows at T."""

    def __init__(self, root: Path) -> None:
        self.item = market()
        self.registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
        seed = RegistryVersion.create(version="seed", created_at=NOW, markets=(self.item,))
        self.registry.stage(seed)
        self.registry.request_apply(seed.version)
        self.authority = MultiAssetDataAuthority(
            store=ClosedBarStore(root / "closed.sqlite"), registry=self.registry
        )
        self.authority.admit_rest_history(
            market=self.item, snapshot=[candle("BTC", 0)], received_at=received_at(0)
        )
        self.active = self.registry.active()
        assert self.active is not None

    def evidence_at(self, boundary: int) -> None:
        self.authority.admit_rest_history(
            market=self.item,
            snapshot=[
                candle("BTC", open_ms)
                for open_ms in range(FIVE_MINUTES_MS, boundary + FIVE_MINUTES_MS, FIVE_MINUTES_MS)
            ],
            received_at=received_at(boundary),
        )

    def pending_successor(self, version: str) -> RegistryVersion:
        return self.registry.successor(
            version=version,
            now=NOW,
            update_market=self.item.model_copy(update={"growth_mode": "HOT_ADD"}),
        )

    def witness_for(self, successor: RegistryVersion, *, boundary: int = T) -> CohortWitness:
        return self.registry._issue_cohort_witness(
            boundary_open_time_ms=boundary,
            base_registry_version=self.active.version,  # type: ignore[union-attr]
            base_registry_hash=self.active.content_hash,  # type: ignore[union-attr]
            expected_successor_version=successor.version,
            expected_successor_hash=successor.content_hash,
            required_evidence_market_ids=frozenset({self.item.identity.market_id}),
        )


def test_witness_applies_successor_and_preserves_persistence_format(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    witness = world.witness_for(successor)
    applied = world.registry.apply_witness(
        witness, evidence_authority=world.authority
    )
    assert applied is not None and applied.version == successor.version
    active = world.registry.active()
    assert active is not None and active.version == successor.version
    # Existing-format artifacts only: canonical pointer, history record named
    # {stamp}-{prior}.json, and no pending left behind.
    pointer = json.loads((tmp_path / "registry" / "current.json").read_text(encoding="utf-8"))
    assert pointer == {"version": successor.version, "content_hash": successor.content_hash}
    assert world.registry.pending_version() is None
    history = list((tmp_path / "registry" / "history").glob("*.json"))
    assert len(history) == 1
    assert history[0].name.endswith(f"-{world.active.version}.json")  # type: ignore[union-attr]
    prior_pointer = json.loads(history[0].read_text(encoding="utf-8"))
    assert prior_pointer == {
        "version": world.active.version,  # type: ignore[union-attr]
        "content_hash": world.active.content_hash,  # type: ignore[union-attr]
    }


def test_empty_required_evidence_is_rejected(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    witness = world.registry._issue_cohort_witness(
        boundary_open_time_ms=T,
        base_registry_version=world.active.version,  # type: ignore[union-attr]
        base_registry_hash=world.active.content_hash,  # type: ignore[union-attr]
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset(),
    )
    with pytest.raises(RegistryError):
        world.registry.apply_witness(
            witness, evidence_authority=world.authority
        )
    assert world.registry.active().version == world.active.version  # type: ignore[union-attr]


def test_unproven_evidence_is_rejected_without_apply(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    # No T row retained at all: prove_boundary_evidence must return False.
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    witness = world.witness_for(successor)
    with pytest.raises(RegistryError):
        world.registry.apply_witness(
            witness, evidence_authority=world.authority
        )
    assert world.registry.active().version == world.active.version  # type: ignore[union-attr]
    assert world.registry.pending_version() is not None


def test_candidate_swap_rejects_and_never_applies_b(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor_a = world.pending_successor("candidate-a")
    world.registry.request_apply(successor_a.version)
    witness = world.witness_for(successor_a)
    # Pending is replaced by candidate B after witness creation.
    successor_b = world.pending_successor("candidate-b")
    world.registry.request_apply(successor_b.version)
    with pytest.raises(RegistryError):
        world.registry.apply_witness(
            witness, evidence_authority=world.authority
        )
    active = world.registry.active()
    assert active is not None
    assert active.version == world.active.version  # type: ignore[union-attr]
    pending = world.registry.pending_version()
    assert pending is not None and pending.version == successor_b.version


def test_base_epoch_swap_rejects_witness_captured_under_old_epoch(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    first = world.pending_successor("first-switch")
    world.registry.request_apply(first.version)
    witness_first = world.witness_for(first)
    assert world.registry.apply_witness(
        witness_first, evidence_authority=world.authority
    )
    world.evidence_at(T + FIVE_MINUTES_MS)
    second = world.pending_successor("second-switch")
    world.registry.request_apply(second.version)
    stale = world.registry._issue_cohort_witness(
        boundary_open_time_ms=T + FIVE_MINUTES_MS,
        base_registry_version=world.active.version,  # type: ignore[union-attr]  # stale R1 binding
        base_registry_hash="9" * 64,
        expected_successor_version=second.version,
        expected_successor_hash=second.content_hash,
        required_evidence_market_ids=frozenset({world.item.identity.market_id}),
    )
    with pytest.raises(RegistryError):
        world.registry.apply_witness(stale, evidence_authority=world.authority)
    assert world.registry.active().version == first.version


def test_witness_is_one_use(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    witness = world.witness_for(successor)
    assert world.registry.apply_witness(
        witness, evidence_authority=world.authority
    )
    world.evidence_at(T + FIVE_MINUTES_MS)
    with pytest.raises(RegistryError):
        world.registry.apply_witness(
            witness, evidence_authority=world.authority
        )


def test_missing_pending_rejects_witness(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    witness = world.witness_for(successor)
    # No request_apply: pending is absent, so there is nothing to activate.
    with pytest.raises(RegistryError):
        world.registry.apply_witness(
            witness, evidence_authority=world.authority
        )
    assert world.registry.active().version == world.active.version  # type: ignore[union-attr]


def test_crash_after_pointer_before_cleanup_converges_on_reopen(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    # Simulate AF: pointer switched, history written, crash before unlink.
    current_pointer = tmp_path / "registry" / "current.json"
    stamp = received_at(T).strftime("%Y%m%dT%H%M%SZ")
    _atomic_copy(
        tmp_path / "registry" / "history" / f"{stamp}-{world.active.version}.json",
        current_pointer,
    )  # type: ignore[union-attr]
    _atomic_write(
        tmp_path / "registry" / "current.json",
        json.dumps(
            {"version": successor.version, "content_hash": successor.content_hash},
            sort_keys=True,
            separators=(",", ":"),
        ).encode(),
    )
    reopened = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    # The read accessor must NOT mutate Registry state: the stale
    # same-as-active pending pointer stays readable after reopen.
    stale_pending = reopened.pending_version()
    assert stale_pending is not None and stale_pending.version == successor.version
    # Explicit single-owner reconciliation recognizes already-applied state,
    # cleans the stale pointer idempotently, and causes no second transition.
    assert reopened.reconcile_pending() is None
    assert reopened.pending_version() is None
    active = reopened.active()
    assert active is not None and active.version == successor.version
    assert len(list((tmp_path / "registry" / "history").glob("*.json"))) == 1
    witness_again = reopened._issue_cohort_witness(
        boundary_open_time_ms=T,
        base_registry_version=successor.version,
        base_registry_hash=successor.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset({world.item.identity.market_id}),
    )
    with pytest.raises(RegistryError):
        reopened.apply_witness(
            witness_again, evidence_authority=world.authority
        )


def test_crash_after_history_before_pointer_keeps_old_r_retryable(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    witness = world.witness_for(successor)
    stamp = received_at(T).strftime("%Y%m%dT%H%M%SZ")
    _atomic_copy(
        tmp_path / "registry" / "history" / f"{stamp}-{world.active.version}.json",  # type: ignore[union-attr]
        tmp_path / "registry" / "current.json",
    )
    reopened = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    active = reopened.active()
    assert active is not None and active.version == world.active.version  # type: ignore[union-attr]
    pending = reopened.pending_version()
    assert pending is not None and pending.version == successor.version
    # Process-local authority does not survive reconstruction: AE re-derives
    # the same durable state and issues a new witness for the current manager.
    with pytest.raises(RegistryError, match="this Registry process"):
        reopened.apply_witness(witness, evidence_authority=world.authority)
    reopened_authority = MultiAssetDataAuthority(
        store=world.authority.store, registry=reopened
    )
    retry = reopened._issue_cohort_witness(
        boundary_open_time_ms=T,
        base_registry_version=active.version,
        base_registry_hash=active.content_hash,
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset({world.item.identity.market_id}),
    )
    applied = reopened.apply_witness(retry, evidence_authority=reopened_authority)
    assert applied is not None and applied.version == successor.version
    assert reopened.active().version == successor.version
    # Exactly one history record for the prior version despite the retry.
    assert len(list((tmp_path / "registry" / "history").glob("*.json"))) == 1


def test_public_string_cannot_mint_or_cross_registry_capability(tmp_path: Path) -> None:
    world = Composition(tmp_path)
    world.evidence_at(T)
    successor = world.pending_successor("manual-r2")
    world.registry.request_apply(successor.version)
    assert not hasattr(CohortWitness, "create")
    assert "issuer" not in CohortWitness.__dataclass_fields__
    # A matching diagnostic string has no place in the capability shape; an
    # arbitrary object identity cannot substitute for this manager's issuer.
    forged = CohortWitness(
        boundary_open_time_ms=T,
        base_registry_version=world.active.version,  # type: ignore[union-attr]
        base_registry_hash=world.active.content_hash,  # type: ignore[union-attr]
        expected_successor_version=successor.version,
        expected_successor_hash=successor.content_hash,
        required_evidence_market_ids=frozenset({world.item.identity.market_id}),
        _issuer=object(),
    )
    with pytest.raises(RegistryError, match="this Registry process"):
        world.registry.apply_witness(forged, evidence_authority=world.authority)
    legitimate = world.witness_for(successor)
    foreign_registry = MarketRegistryManager(
        tmp_path / "registry", metadata_validator=lambda _: True
    )
    with pytest.raises(RegistryError, match="this Registry process"):
        foreign_registry.apply_witness(legitimate, evidence_authority=world.authority)
    assert world.registry.apply_witness(legitimate, evidence_authority=world.authority)


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _atomic_copy(path: Path, source: Path) -> None:
    _atomic_write(path, source.read_bytes())
