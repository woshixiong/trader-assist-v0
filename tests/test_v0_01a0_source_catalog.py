from __future__ import annotations

import json

import pytest

from trader_assist_v0.contracts.source_catalog import (
    ALLOWED_COINS,
    ENTRIES,
    RATE_LIMIT_STATUS,
    RUNTIME_CANDLE_INTERVALS,
    SOURCE_CATALOG_HASH,
    catalog_entry_hash,
    endpoint_kind,
    get_entry,
    source_catalog_document,
    source_catalog_hash,
    validate_public_selection,
)


def test_catalog_is_deterministic_unique_and_public_only() -> None:
    assert SOURCE_CATALOG_HASH == source_catalog_hash()
    assert SOURCE_CATALOG_HASH == (
        "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    )
    keys = [(entry.endpoint_id, entry.operation_type) for entry in ENTRIES]
    assert len(keys) == len(set(keys))
    encoded = json.dumps(source_catalog_document(), sort_keys=True).lower()
    assert "testnet" not in encoded
    assert '"exchange"' not in encoded
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert ALLOWED_COINS == ("BTC", "ETH")
    assert RUNTIME_CANDLE_INTERVALS == ("1m", "3m", "5m", "15m", "1h")


def test_entry_hash_is_deterministic_and_selection_is_strict() -> None:
    entry = get_entry("hl-ws-mainnet-public", "trades")
    assert catalog_entry_hash(entry) == catalog_entry_hash(entry)
    assert endpoint_kind(entry.endpoint_id) == "WEBSOCKET"
    validate_public_selection(entry.endpoint_id, entry.operation_type, coin="ETH")
    validate_public_selection("hl-info-mainnet-public", "meta")

    invalid_selections = [
        ("unknown", "trades", "ETH", None),
        ("hl-info-mainnet-public", "/exchange", None, None),
        ("hl-ws-testnet-public", "trades", "ETH", None),
        ("hl-ws-mainnet-public", "unknown", "ETH", None),
        ("hl-ws-mainnet-public", "trades", None, None),
        ("hl-info-mainnet-public", "meta", "ETH", None),
        ("hl-ws-mainnet-public", "trades", "SOL", None),
        ("hl-ws-mainnet-public", "candle", "ETH", "30m"),
    ]
    for endpoint_id, operation_type, coin, interval in invalid_selections:
        with pytest.raises(ValueError):
            validate_public_selection(
                endpoint_id,
                operation_type,
                coin=coin,
                interval=interval,
            )
