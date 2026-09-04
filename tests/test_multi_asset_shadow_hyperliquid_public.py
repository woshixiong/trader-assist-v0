from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    INFO_URL,
    HyperliquidPublicClient,
    HyperliquidPublicPlanningAdapter,
    HyperliquidRestOneMinuteProvider,
    PublicDataError,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.planning import Side
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager


def test_only_public_info_market_data_request_shapes_are_issued() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def post(url: str, body: bytes, timeout: float) -> bytes:
        seen.append((url, json.loads(body)))
        return b"[]"

    client = HyperliquidPublicClient(post=post)
    client.perp_dexes()
    client.metadata("")
    client.metadata_and_context("xyz")
    client.closed_candles(coin="xyz:XYZ100", interval="5m", start_ms=0, end_ms=300_000)
    client.l2_book(coin="BTC")
    assert {url for url, _ in seen} == {INFO_URL}
    assert [body["type"] for _, body in seen] == [
        "perpDexs",
        "meta",
        "metaAndAssetCtxs",
        "candleSnapshot",
        "l2Book",
    ]
    assert "dex" not in seen[1][1]
    assert seen[3][1] == {
        "type": "candleSnapshot",
        "req": {
            "coin": "xyz:XYZ100",
            "interval": "5m",
            "startTime": 0,
            "endTime": 299_999,
        },
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "clearinghouseState", "user": "0xabc"},
        {"type": "openOrders", "user": "0xabc"},
        {"type": "userRateLimit", "user": "0xabc"},
        {"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "15m"}},
    ],
)
def test_account_and_unsupported_public_surfaces_fail_before_transport(
    payload: dict[str, object],
) -> None:
    client = HyperliquidPublicClient(post=lambda *_: pytest.fail("transport must not run"))
    with pytest.raises(PublicDataError, match="approved"):
        client.request(payload)


def _registry(tmp_path: Path) -> tuple[MarketRegistryManager, RegistryMarket]:
    market = RegistryMarket(
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
        metadata_observed_at=datetime(2026, 8, 14, tzinfo=UTC),
        metadata_hash=sha256_hex(b"btc"),
    )
    registry = MarketRegistryManager(tmp_path, metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="registry-1",
        created_at=datetime(2026, 8, 14, tzinfo=UTC),
        markets=(market,),
    )
    registry.stage(version)
    registry.request_apply(version.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    authority.admit_rest_history(
        market=market,
        snapshot=[
            {
                "i": "5m",
                "s": "BTC",
                "t": 0,
                "T": 299_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ],
        received_at=datetime.fromtimestamp(301, UTC),
    )
    return registry, market


def test_public_planning_adapter_binds_bbo_and_l2_to_one_response(tmp_path: Path) -> None:
    calls = 0

    def post(_url: str, body: bytes, _timeout: float) -> bytes:
        nonlocal calls
        calls += 1
        assert json.loads(body)["type"] == "l2Book"
        return json.dumps(
            {
                "coin": "BTC",
                "time": 1_000,
                "levels": [
                    [{"px": "100", "sz": "20"}],
                    [{"px": "100.1", "sz": "20"}],
                ],
            }
        ).encode()

    _, market = _registry(tmp_path / "registry")
    adapter = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=post), wall_clock_ms=lambda: 1_001
    )
    bbo = adapter.fetch_bbo(market=market, now_ms=1_001)
    l2 = adapter.fetch_l2(market=market, side=Side.LONG, bbo=bbo)
    assert calls == 1
    assert l2.levels == ((Decimal("100.1"), Decimal("20")),)
    with pytest.raises(PublicDataError, match="one retained"):
        adapter.fetch_l2(market=market, side=Side.LONG, bbo=bbo)


@pytest.mark.parametrize("fetch", ["bbo", "scanner"])
def test_l2_freshness_uses_post_response_wall_clock(
    tmp_path: Path, fetch: str
) -> None:
    events: list[str] = []
    calls = 0
    wall_clock_ms = 1_000

    def post(_url: str, body: bytes, _timeout: float) -> bytes:
        nonlocal calls, wall_clock_ms
        calls += 1
        assert json.loads(body) == {"type": "l2Book", "coin": "BTC"}
        wall_clock_ms = 1_100
        events.append("l2Book returned")
        return json.dumps(
            {
                "coin": "BTC",
                "time": 1_050,
                "levels": [
                    [{"px": "100", "sz": "20"}],
                    [{"px": "100.1", "sz": "20"}],
                ],
            }
        ).encode()

    def post_response_wall_clock_ms() -> int:
        assert events == ["l2Book returned"]
        events.append("wall clock sampled")
        return wall_clock_ms

    _, market = _registry(tmp_path / "registry")
    adapter = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=post), wall_clock_ms=post_response_wall_clock_ms
    )

    if fetch == "bbo":
        assert adapter.fetch_bbo(market=market, now_ms=1_000).observed_at_ms == 1_050
    else:
        snapshot = adapter.fetch_scanner_snapshot(
            market=market,
            now_ms=1_000,
            btc_returns=(None, None, None),
        )
        assert snapshot.current_spread_price == Decimal("0.1")

    assert events == ["l2Book returned", "wall clock sampled"]
    assert calls == 1


@pytest.mark.parametrize("fetch", ["bbo", "scanner"])
@pytest.mark.parametrize(
    ("provider_time_ms", "post_response_wall_ms"),
    [(99, 11_100), (1_101, 1_100)],
    ids=["stale-at-response", "future-at-response"],
)
def test_l2_freshness_fails_closed_relative_to_response_observation(
    tmp_path: Path,
    fetch: str,
    provider_time_ms: int,
    post_response_wall_ms: int,
) -> None:
    calls = 0

    def post(_url: str, body: bytes, _timeout: float) -> bytes:
        nonlocal calls
        calls += 1
        assert json.loads(body)["type"] == "l2Book"
        return json.dumps(
            {
                "coin": "BTC",
                "time": provider_time_ms,
                "levels": [
                    [{"px": "100", "sz": "20"}],
                    [{"px": "100.1", "sz": "20"}],
                ],
            }
        ).encode()

    _, market = _registry(tmp_path / "registry")
    adapter = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=post),
        wall_clock_ms=lambda: post_response_wall_ms,
    )

    with pytest.raises(PublicDataError, match="stale or future-dated"):
        if fetch == "bbo":
            adapter.fetch_bbo(market=market, now_ms=1_000)
        else:
            adapter.fetch_scanner_snapshot(
                market=market,
                now_ms=1_000,
                btc_returns=(None, None, None),
            )

    assert calls == 1


def test_public_planning_adapter_preserves_existing_default_maximum_age() -> None:
    adapter = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=lambda *_: pytest.fail("transport must not run"))
    )
    assert adapter.max_age_ms == 10_000


def test_public_one_minute_provider_accepts_only_closed_provider_bars(tmp_path: Path) -> None:
    registry, market = _registry(tmp_path / "registry")

    def post(_url: str, body: bytes, _timeout: float) -> bytes:
        request = json.loads(body)
        assert request == {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "1m",
                "startTime": 0,
                "endTime": 59_999,
            },
        }
        return json.dumps(
            [
                {
                    "i": "1m",
                    "s": "BTC",
                    "t": 0,
                    "T": 59_999,
                    "o": "100",
                    "h": "101",
                    "l": "99",
                    "c": "100.5",
                    "v": "10",
                    "n": 2,
                }
            ]
        ).encode()

    provider = HyperliquidRestOneMinuteProvider(
        HyperliquidPublicClient(post=post), registry
    )
    provider.subscribe_1m(market_id=market.identity.market_id)
    bars = provider.backfill_1m(
        market_id=market.identity.market_id, start_ms=0, end_ms=60_000
    )
    assert len(bars) == 1
    assert bars[0].source_id == "hyperliquid-public-candleSnapshot-1m"
    provider.unsubscribe_1m(market_id=market.identity.market_id)
    assert provider.subscribed_market_ids == set()
