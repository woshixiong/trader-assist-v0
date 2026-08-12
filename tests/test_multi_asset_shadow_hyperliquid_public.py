from __future__ import annotations

import json

import pytest

from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    INFO_URL,
    HyperliquidPublicClient,
    PublicDataError,
)


def test_only_public_info_market_data_request_shapes_are_issued() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def post(url: str, body: bytes, timeout: float) -> bytes:
        seen.append((url, json.loads(body)))
        return b"[]"

    client = HyperliquidPublicClient(post=post)
    client.perp_dexes()
    client.metadata("MAIN")
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
