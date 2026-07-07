from __future__ import annotations

import json
from pathlib import Path

import pytest

from trader_assist_v0.data.source_catalog import (
    ALLOWED_COINS,
    ENTRIES,
    RATE_LIMIT_STATUS,
    RUNTIME_CANDLE_INTERVALS,
    SOURCE_CATALOG_HASH,
    endpoint_kind,
    get_entry,
    source_catalog_document,
    source_catalog_hash,
    validate_public_selection,
)


def test_catalog_is_deterministic_unique_and_json_serializable() -> None:
    assert SOURCE_CATALOG_HASH == source_catalog_hash()
    document = json.loads(json.dumps(source_catalog_document(), sort_keys=True))
    assert document["allowed_coins"] == ["BTC", "ETH"]
    keys = [(entry.endpoint_id, entry.operation_type) for entry in ENTRIES]
    assert len(keys) == len(set(keys))


def test_catalog_boundaries_and_uncertainty() -> None:
    assert ALLOWED_COINS == ("BTC", "ETH")
    assert RUNTIME_CANDLE_INTERVALS == ("1m", "3m", "5m", "15m", "1h")
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    candle = get_entry("hl-ws-mainnet-public", "candle")
    assert candle.documentation_status == "AMBIGUOUS_DOCUMENTATION"
    assert "Candle or Candle[]" in candle.response_envelope
    book = get_entry("hl-ws-mainnet-public", "l2Book")
    assert book.semantics == "FULL_SNAPSHOT_NOT_DELTA"


@pytest.mark.parametrize("coin", ["ETH", "BTC"])
def test_coin_allowlist(coin: str) -> None:
    validate_public_selection("hl-ws-mainnet-public", "trades", coin=coin)


@pytest.mark.parametrize("coin", ["SOL", "eth", "", "TEST"])
def test_unsupported_coin_rejected(coin: str) -> None:
    with pytest.raises(ValueError):
        validate_public_selection("hl-ws-mainnet-public", "trades", coin=coin)


def test_interval_and_endpoint_strictness() -> None:
    for interval in RUNTIME_CANDLE_INTERVALS:
        validate_public_selection(
            "hl-ws-mainnet-public", "candle", coin="ETH", interval=interval
        )
    with pytest.raises(ValueError):
        validate_public_selection(
            "hl-ws-mainnet-public", "candle", coin="ETH", interval="30m"
        )
    with pytest.raises(ValueError):
        validate_public_selection(
            "hl-ws-mainnet-public", "trades", coin="ETH", interval="1m"
        )
    with pytest.raises(ValueError):
        validate_public_selection("hl-ws-mainnet-public", "trades")
    with pytest.raises(ValueError):
        validate_public_selection("hl-info-mainnet-public", "meta", coin="ETH")
    with pytest.raises(ValueError):
        get_entry("hl-info-mainnet-public", "exchange")
    assert endpoint_kind("hl-ws-mainnet-public") == "WEBSOCKET"
    assert endpoint_kind("hl-info-mainnet-public") == "INFO"
    with pytest.raises(ValueError):
        endpoint_kind("testnet")


def test_catalog_contains_no_testnet_or_exchange_endpoint() -> None:
    encoded = json.dumps(source_catalog_document(), sort_keys=True).lower()
    assert "testnet" not in encoded
    assert '"exchange"' not in encoded


def test_synthetic_fixture_set_is_complete_and_safe() -> None:
    fixture_dir = Path(__file__).parent / "fixtures/hyperliquid/v0_01a0"
    assert {path.name for path in fixture_dir.iterdir()} == {"public_messages.json"}
    messages = json.loads((fixture_dir / "public_messages.json").read_text())
    assert set(messages) == {
        "activeAssetCtx",
        "allMids",
        "bboBothSides",
        "bboNullSide",
        "candle",
        "l2BookSnapshot",
        "malformedJSON",
        "pong",
        "subscriptionResponse",
        "tradesBatch",
        "unknownChannel",
    }
    for name, payload in messages.items():
        if name == "malformedJSON":
            with pytest.raises(json.JSONDecodeError):
                json.loads(payload)
        else:
            assert isinstance(json.loads(payload), dict)
    assert json.loads(messages["l2BookSnapshot"])["channel"] == "l2Book"
    combined = (fixture_dir / "public_messages.json").read_bytes().lower()
    forbidden = (
        b"private key",
        b"api wallet",
        b"0x0000000000000000000000000000000000000000",
    )
    for marker in forbidden:
        assert marker not in combined
