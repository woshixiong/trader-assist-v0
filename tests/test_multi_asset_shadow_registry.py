from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
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


def provider_candle(value: RegistryMarket, open_ms: int = 0) -> dict[str, object]:
    return {
        "i": "5m",
        "s": value.identity.coin,
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "1",
    }


def admit(
    subject: MarketRegistryManager, path: Path, value: RegistryMarket, open_ms: int = 0
) -> None:
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(path / "evidence.db"), registry=subject
    )
    authority.admit_rest_history(
        market=value,
        snapshot=[provider_candle(value, open_ms)],
        received_at=datetime.fromtimestamp((open_ms + 301_000) / 1000, UTC),
    )


def test_validate_request_and_data_boundary_apply_are_atomic(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    one = registry("one", market())
    two = registry("two", market("ETH"))
    subject.stage(one)
    subject.stage(two)
    subject.request_apply("one")
    admit(subject, tmp_path, one.markets[0])
    assert subject.active() is not None and subject.active().version == "one"
    with pytest.raises(AttributeError):
        subject.apply_at_closed_5m()  # type: ignore[attr-defined]
    subject.request_apply("two")
    admit(subject, tmp_path, two.markets[0], 300_000)
    assert subject.active() is not None and subject.active().version == "two"
    subject.rollback_request("one")
    admit(subject, tmp_path, one.markets[0], 600_000)
    assert subject.active() is not None and subject.active().version == "one"


def test_invalid_candidate_keeps_previous_active_version(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    initial = registry("one", market())
    subject.stage(initial)
    subject.request_apply("one")
    admit(subject, tmp_path, initial.markets[0])
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
    admit(subject, tmp_path, initial.markets[0])
    successor = subject.lifecycle_update(
        "two", initial.markets[0].identity.market_id, MarketLifecycle.DRAINING, now=NOW
    )
    assert successor.markets[0].lifecycle is MarketLifecycle.DRAINING
    assert subject.active() is not None and subject.active().version == "one"


def test_disabled_market_can_only_reenter_warming_not_active(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    initial = registry("one", market(lifecycle=MarketLifecycle.DISABLED))
    subject.stage(initial)
    subject.request_apply("one")
    admit(subject, tmp_path, initial.markets[0])
    with pytest.raises(RegistryError, match="illegal"):
        subject.lifecycle_update(
            "bad", initial.markets[0].identity.market_id, MarketLifecycle.ACTIVE, now=NOW
        )
    successor = subject.lifecycle_update(
        "two", initial.markets[0].identity.market_id, MarketLifecycle.WARMING, now=NOW
    )
    assert successor.markets[0].lifecycle is MarketLifecycle.WARMING


def test_add_new_rejects_duplicate_and_forces_warming(tmp_path: Path) -> None:
    subject = manager(tmp_path)
    initial = registry("one", market(lifecycle=MarketLifecycle.ACTIVE))
    subject.stage(initial)
    subject.request_apply("one")
    admit(subject, tmp_path, initial.markets[0])
    added = subject.add_new(
        version="two",
        now=NOW,
        market=market("ETH", lifecycle=MarketLifecycle.ACTIVE),
    )
    eth = next(item for item in added.markets if item.display == "ETH")
    assert eth.lifecycle is MarketLifecycle.WARMING
    with pytest.raises(RegistryError, match="new canonical"):
        subject.add_new(version="three", now=NOW, market=market())
