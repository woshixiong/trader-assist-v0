from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
    DataRouteError,
    MultiAssetDataAuthority,
    aggregate_closed_5m,
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
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager

MARKET_ID = MarketIdentity.create(dex="MAIN", coin="BTC").market_id
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def bar(index: int, *, close: str = "101") -> ClosedBar:
    start = index * 300_000
    return ClosedBar.create(
        market_id=MARKET_ID,
        open_time_ms=start,
        close_time_ms=start + 300_000,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        volume=Decimal("10"),
        source_id="hyperliquid-public-mainnet",
        provenance_hash=sha256_hex(f"source-{index}".encode()),
        received_at=NOW,
    )


def test_closed_bar_store_is_idempotent_but_rejects_conflicts(tmp_path: Path) -> None:
    store = ClosedBarStore(tmp_path / "evidence.db")
    value = bar(0)
    assert store.put(value)
    assert not store.put(value)
    with pytest.raises(DataRouteError, match="conflicting"):
        store.put(bar(0, close="100"))
    store.close()


def test_15m_and_1h_are_complete_aligned_causal_5m_aggregates() -> None:
    fifteen = aggregate_closed_5m([bar(0), bar(1), bar(2)], minutes=15)
    assert fifteen.interval == "15m"
    assert fifteen.open_time_ms == 0
    assert fifteen.volume == Decimal("30")
    hour = aggregate_closed_5m([bar(index) for index in range(12)], minutes=60)
    assert hour.interval == "1h"
    assert hour.close_time_ms == 3_600_000


def test_gap_or_misaligned_aggregate_fails_closed() -> None:
    with pytest.raises(DataRouteError, match="gap"):
        aggregate_closed_5m([bar(0), bar(1), bar(3)], minutes=15)
    with pytest.raises(DataRouteError, match="aligned"):
        aggregate_closed_5m([bar(1), bar(2), bar(3)], minutes=15)


def _market() -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=NOW,
        metadata_hash="a" * 64,
    )


def _payload(open_ms: int, *, close: str = "100") -> dict[str, object]:
    return {
        "i": "5m",
        "s": "BTC",
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": close,
        "v": "10",
    }


def _authority(tmp_path: Path) -> tuple[MultiAssetDataAuthority, RegistryMarket]:
    market = _market()
    manager = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="one", created_at=NOW, markets=(market,))
    manager.stage(version)
    manager.request_apply("one")
    return MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "authority.db"), registry=manager
    ), market


def test_ws_candidate_requires_final_stable_rest_and_real_end_minus_one_geometry(
    tmp_path: Path,
) -> None:
    authority, market = _authority(tmp_path)
    payload = _payload(0)
    fingerprint = authority.offer_ws_candidate(market=market, payload=payload, received_at=NOW)
    assert authority.store.bars(market.identity.market_id) == ()
    assert (
        authority.confirm_ws_candidate(
            market=market,
            open_time_ms=0,
            candidate_fingerprint=fingerprint,
            snapshot=[payload],
            stable_snapshot=[payload],
            received_at=datetime.fromtimestamp(300.5, UTC),
        )
        is None
    )
    admitted = authority.confirm_ws_candidate(
        market=market,
        open_time_ms=0,
        candidate_fingerprint=fingerprint,
        snapshot=[payload],
        stable_snapshot=[payload],
        received_at=datetime.fromtimestamp(301, UTC),
    )
    assert admitted is not None and admitted.close_time_ms == 299_999
    assert authority.registry.active() is not None and authority.registry.active().version == "one"


def test_conflict_and_gap_are_isolated_and_backfill_recovers(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    received = datetime.fromtimestamp(1_000, UTC)
    authority.admit_rest_history(market=market, snapshot=[_payload(0)], received_at=received)
    with pytest.raises(DataRouteError, match="gap"):
        authority.admit_rest_history(
            market=market, snapshot=[_payload(600_000)], received_at=received
        )
    assert authority.market_failed(market.identity.market_id)
    authority.admit_rest_history(
        market=market, snapshot=[_payload(300_000), _payload(600_000)], received_at=received
    )
    assert not authority.market_failed(market.identity.market_id)
    with pytest.raises(DataRouteError, match="conflicting"):
        authority.admit_rest_history(
            market=market, snapshot=[_payload(600_000, close="101")], received_at=received
        )


def test_restart_recovers_last_authoritative_identity(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    authority.admit_rest_history(
        market=market,
        snapshot=[_payload(0), _payload(300_000)],
        received_at=datetime.fromtimestamp(1_000, UTC),
    )
    restored = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "authority.db"), registry=authority.registry
    )
    assert restored.store.last_open(market.identity.market_id) == 300_000
