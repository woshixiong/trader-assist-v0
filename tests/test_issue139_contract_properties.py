"""Property/stateful foundation for admitted-input and causal topology invariants."""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from tests.property_strategies import (
    FIVE_MINUTES_MS,
    MARKET_ID,
    causal_five_minute_series,
    valid_strategy_bars,
)
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import _bar_from_payload
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    KernelInputError,
    aggregate_closed_5m_causally,
    clv_long,
    clv_short,
    directional_efficiency_8,
    median_previous_20_volume,
)


@settings(max_examples=60, deadline=None)
@given(valid_strategy_bars())
def test_admitted_ohlc_domain_is_deterministic_and_serialization_total(bar: Bar) -> None:
    assert bar.high >= max(bar.open, bar.close)
    assert bar.low <= min(bar.open, bar.close)
    assert bar.volume >= 0
    payload = json.loads(canonical_json_bytes(asdict(bar)))
    assert _bar_from_payload(payload) == bar
    assert len(bar.candle_id) == 64
    if bar.high == bar.low:
        with pytest.raises(KernelInputError, match="positive candle range"):
            clv_long(bar)
        with pytest.raises(KernelInputError, match="positive candle range"):
            clv_short(bar)
    else:
        assert Decimal() <= clv_long(bar) <= Decimal(1)
        assert Decimal() <= clv_short(bar) <= Decimal(1)


@settings(max_examples=50, deadline=None)
@given(causal_five_minute_series())
def test_causal_aggregation_contains_only_complete_utc_buckets(bars: tuple[Bar, ...]) -> None:
    for minutes in (15, 60):
        aggregated = aggregate_closed_5m_causally(bars, minutes=minutes)
        bucket_ms = minutes * 60_000
        required = minutes // 5
        for item in aggregated:
            assert item.open_time_ms % bucket_ms == 0
            members = tuple(
                bar
                for bar in bars
                if item.open_time_ms <= bar.open_time_ms < item.open_time_ms + bucket_ms
            )
            assert len(members) == required
            assert item.open == members[0].open
            assert item.close == members[-1].close
            assert item.high == max(member.high for member in members)
            assert item.low == min(member.low for member in members)
            assert item.volume == sum((member.volume for member in members), Decimal())
            assert item.close_time_ms <= bars[-1].close_time_ms


def test_flat_zero_volume_and_decimal_extremes_have_explicit_contract_outcomes() -> None:
    flat = tuple(
        Bar(
            MARKET_ID,
            "5m",
            index * FIVE_MINUTES_MS,
            (index + 1) * FIVE_MINUTES_MS,
            Decimal("1E-100"),
            Decimal("1E-100"),
            Decimal("1E-100"),
            Decimal("1E-100"),
            Decimal(),
        )
        for index in range(21)
    )
    assert directional_efficiency_8(flat) == 0
    assert median_previous_20_volume(flat) == 0
    extreme = Bar(
        MARKET_ID,
        "5m",
        0,
        FIVE_MINUTES_MS,
        Decimal("1E+100"),
        Decimal("1E+100"),
        Decimal("1E+100"),
        Decimal("1E+100"),
        Decimal(),
    )
    assert extreme.high == extreme.low
    near_zero = Bar(
        MARKET_ID,
        "5m",
        0,
        FIVE_MINUTES_MS,
        Decimal("1E-100"),
        Decimal("2E-100"),
        Decimal("1E-100"),
        Decimal("1.5E-100"),
        Decimal(),
    )
    assert clv_long(near_zero) == Decimal("0.5")
    assert clv_short(near_zero) == Decimal("0.5")


def _market(lifecycle: MarketLifecycle = MarketLifecycle.WARMING) -> RegistryMarket:
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
        lifecycle=lifecycle,
        metadata_observed_at=datetime(2026, 8, 31, tzinfo=UTC),
        metadata_hash=sha256_hex(b"issue139-property-market"),
    )


class RegistryLifecycleMachine(RuleBasedStateMachine):
    """Real Registry/DataAuthority state machine across restart/idempotency paths."""

    def __init__(self) -> None:
        super().__init__()
        self.temporary = tempfile.TemporaryDirectory(prefix="trade-os-issue139-")
        self.root = Path(self.temporary.name)
        self.registry_root = self.root / "registry"
        self.store_path = self.root / "closed.sqlite"
        self.registry = MarketRegistryManager(
            self.registry_root, metadata_validator=lambda _: True
        )
        initial = RegistryVersion.create(
            version="stateful-initial",
            created_at=datetime(2026, 8, 31, tzinfo=UTC),
            markets=(_market(),),
        )
        self.registry.stage(initial)
        self.registry.request_apply(initial.version)
        self.store = ClosedBarStore(self.store_path)
        self.authority = MultiAssetDataAuthority(store=self.store, registry=self.registry)
        self.boundary = 0
        self.last_payload = self._payload(self.boundary)
        self.authority.admit_rest_history(
            market=initial.markets[0],
            snapshot=[self.last_payload],
            received_at=self._received_at(self.boundary),
        )
        self.expected = MarketLifecycle.WARMING

    @staticmethod
    def _payload(open_ms: int) -> dict[str, object]:
        return {
            "i": "5m",
            "s": "BTC",
            "t": open_ms,
            "T": open_ms + FIVE_MINUTES_MS - 1,
            "o": "100",
            "h": "101",
            "l": "99",
            "c": "100",
            "v": "0",
        }

    @staticmethod
    def _received_at(open_ms: int) -> datetime:
        return datetime.fromtimestamp((open_ms + FIVE_MINUTES_MS + 3_000) / 1_000, UTC)

    @precondition(lambda self: self.expected is not MarketLifecycle.ACTIVE)
    @rule()
    def owner_bounded_lifecycle_progress(self) -> None:
        next_state = {
            MarketLifecycle.WARMING: MarketLifecycle.HISTORY_READY,
            MarketLifecycle.HISTORY_READY: MarketLifecycle.SNAPSHOT_READY,
            MarketLifecycle.SNAPSHOT_READY: MarketLifecycle.ACTIVE,
        }[self.expected]
        active = self.registry.active()
        assert active is not None
        candidate = self.registry.lifecycle_update(
            f"stateful-{self.boundary}-{next_state.value}",
            active.markets[0].identity.market_id,
            next_state,
            now=self._received_at(self.boundary),
        )
        self.registry.request_apply(candidate.version)
        self.boundary += FIVE_MINUTES_MS
        self.last_payload = self._payload(self.boundary)
        self.authority.admit_rest_history(
            market=active.markets[0],
            snapshot=[self.last_payload],
            received_at=self._received_at(self.boundary),
        )
        witness = self.registry._issue_cohort_witness(
            boundary_open_time_ms=self.boundary,
            base_registry_version=active.version,
            base_registry_hash=active.content_hash,
            expected_successor_version=candidate.version,
            expected_successor_hash=candidate.content_hash,
            required_evidence_market_ids=frozenset({active.markets[0].identity.market_id}),
        )
        self.registry.apply_witness(witness, evidence_authority=self.authority)
        self.expected = next_state

    @rule()
    def duplicate_boundary_is_idempotent(self) -> None:
        active = self.registry.active()
        assert active is not None
        before = self.store.connection.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0]
        self.authority.admit_rest_history(
            market=active.markets[0],
            snapshot=[self.last_payload],
            received_at=self._received_at(self.boundary),
        )
        after = self.store.connection.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0]
        assert after == before

    @rule()
    def provider_delay_or_reconnect_does_not_advance_authority(self) -> None:
        before = self.registry.active()
        assert before is not None
        assert self.registry.reconcile_pending() is None
        assert self.registry.active() == before

    @rule()
    def restart_reopen_preserves_epoch_and_state(self) -> None:
        before = self.registry.active()
        assert before is not None
        self.store.close()
        self.registry = MarketRegistryManager(
            self.registry_root, metadata_validator=lambda _: True
        )
        self.store = ClosedBarStore(self.store_path)
        self.authority = MultiAssetDataAuthority(store=self.store, registry=self.registry)
        assert self.registry.active() == before

    @invariant()
    def active_epoch_matches_reference_model(self) -> None:
        active = self.registry.active()
        assert active is not None
        assert active.markets[0].lifecycle is self.expected
        assert self.registry.pending_version() is None

    def teardown(self) -> None:
        self.store.close()
        self.temporary.cleanup()


RegistryLifecycleTest = RegistryLifecycleMachine.TestCase
RegistryLifecycleTest.settings = settings(max_examples=20, stateful_step_count=15, deadline=None)
