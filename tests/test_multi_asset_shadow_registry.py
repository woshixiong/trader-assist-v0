from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    ClosedBar,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager, RegistryError

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def market(
    display: str = "BTC", *, lifecycle: MarketLifecycle = MarketLifecycle.WARMING
) -> RegistryMarket:
    return RegistryMarket(
        display=display,
        aliases=("Bitcoin",) if display == "BTC" else (),
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin=display),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=lifecycle,
        metadata_observed_at=NOW,
        metadata_hash=sha256_hex(display.encode()),
    )


def registry(version: str, *markets: RegistryMarket) -> RegistryVersion:
    return RegistryVersion.create(version=version, created_at=NOW, markets=tuple(markets))


def manager(path: Path, valid: bool = True) -> MarketRegistryManager:
    return MarketRegistryManager(path, metadata_validator=lambda _: valid)


def boundary(value: RegistryMarket) -> ClosedBar:
    return ClosedBar.create(
        market_id=value.identity.market_id,
        open_time_ms=0,
        close_time_ms=300_000,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=Decimal("1"),
        source_id="test",
        provenance_hash=sha256_hex(b"boundary"),
        received_at=NOW,
    )


def test_validate_request_and_data_boundary_apply_are_atomic(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    one = registry("one", market())
    two = registry("two", market("ETH"))
    subject.stage(one)
    subject.stage(two)
    subject.request_apply("one")
    assert subject.apply_pending_at_closed_5m(boundary=boundary(one.markets[0])).version == "one"
    with pytest.raises(RegistryError, match="closed 5m boundary"):
        subject.apply_at_closed_5m(
            "two",
            boundary=boundary(two.markets[0]).model_copy(update={"interval": "15m"}),
        )
    assert subject.active() is not None and subject.active().version == "one"
    subject.request_apply("two")
    assert subject.apply_pending_at_closed_5m(boundary=boundary(two.markets[0])).version == "two"
    subject.rollback_request("one")
    assert subject.apply_pending_at_closed_5m(boundary=boundary(one.markets[0])).version == "one"
    assert subject.active() is not None and subject.active().version == "one"


def test_invalid_candidate_keeps_previous_active_version(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    initial = registry("one", market())
    subject.stage(initial)
    subject.request_apply("one")
    subject.apply_pending_at_closed_5m(boundary=boundary(initial.markets[0]))
    invalid_path = tmp_path / "versions" / "two.json"
    invalid_path.parent.mkdir(exist_ok=True)
    invalid_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RegistryError):
        subject.request_apply("two")
    assert subject.active() is not None and subject.active().version == "one"


def test_identity_duplicate_and_metadata_validation_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="duplicate canonical"):
        registry("duplicate", market(), market("BTC"))
    subject = manager(tmp_path, valid=False)
    with pytest.raises(RegistryError, match="REGISTRY_IDENTITY_UNRESOLVED"):
        subject.stage(registry("one", market()))


def test_lifecycle_update_is_immutable_and_does_not_change_event_expiry(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    initial = registry("one", market(lifecycle=MarketLifecycle.ACTIVE))
    subject.stage(initial)
    subject.request_apply("one")
    subject.apply_pending_at_closed_5m(boundary=boundary(initial.markets[0]))
    successor = subject.lifecycle_update(
        "two", initial.markets[0].identity.market_id, MarketLifecycle.DRAINING, now=NOW
    )
    assert successor.markets[0].lifecycle is MarketLifecycle.DRAINING
    assert subject.active() is not None and subject.active().version == "one"
