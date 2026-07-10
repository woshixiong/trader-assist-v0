from __future__ import annotations

import ast
import inspect
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.candles import (
    A5_CONTRACT_ID,
    CANDLE_EXTRACTION_HASH_VERSION,
    CANDLE_EXTRACTION_SCHEMA_VERSION,
    CANDLE_LOGICAL_KEY_VERSION,
    CandleEnvelopeShapeV0,
    CandlePayloadExtractionV0,
    compute_candle_extraction_hash,
)
from trader_assist_v0.contracts.events import RawCaptureModeV0, RawEventV0
from trader_assist_v0.contracts.source_catalog import (
    RATE_LIMIT_STATUS,
    SOURCE_CATALOG_HASH,
)
from trader_assist_v0.data import candle_extractor
from trader_assist_v0.data.candle_extractor import (
    CandlePayloadExtractionError,
    extract_candle_payload,
)
from trader_assist_v0.data.ingress import bind_public_observation_bytes

_NOW = datetime(2026, 7, 10, 0, 0, tzinfo=UTC)


def _candle(
    *,
    open_time: int = 1_720_000_000_000,
    close_time: int = 1_720_000_059_999,
    coin: str = "ETH",
    interval: str = "1m",
    open_price: int | float = 3000,
    close_price: int | float = 3001,
    high_price: int | float = 3002,
    low_price: int | float = 2999,
    volume: int | float = 12.5,
    trades: int = 7,
) -> dict[str, Any]:
    return {
        "t": open_time,
        "T": close_time,
        "s": coin,
        "i": interval,
        "o": open_price,
        "c": close_price,
        "h": high_price,
        "l": low_price,
        "v": volume,
        "n": trades,
    }


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _raw(
    payload: bytes,
    *,
    endpoint_id: str = "hl-ws-mainnet-public",
    operation_type: str = "candle",
    capture_mode: RawCaptureModeV0 = (
        RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
    ),
    coin: str | None = "ETH",
    interval: str | None = "1m",
    content_type: str = "application/json",
    payload_encoding: str = "utf-8",
) -> RawEventV0:
    return bind_public_observation_bytes(
        payload=payload,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        capture_mode=capture_mode,
        connection_id="test-connection",
        subscription_id="test-subscription",
        receive_sequence=1,
        first_observed_time=_NOW,
        collector_receive_time=_NOW,
        collector_monotonic_ns=1,
        coin=cast(Any, coin),
        candle_interval=cast(Any, interval),
        content_type=content_type,
        payload_encoding=payload_encoding,
    )


def _extract(
    payload: bytes,
    **raw_overrides: Any,
) -> CandlePayloadExtractionV0:
    return extract_candle_payload(
        raw_event=_raw(payload, **raw_overrides),
        payload=payload,
    )


def test_a5_frozen_authorities_and_existing_gates_remain_fail_closed() -> None:
    assert (
        A5_CONTRACT_ID
        == "V0-01A5-OFFLINE-CANDLE-PAYLOAD-EXTRACTION-CONTRACT"
    )
    assert CANDLE_EXTRACTION_SCHEMA_VERSION == "0.1.0"
    assert (
        CANDLE_EXTRACTION_HASH_VERSION
        == "trader-assist-v0/candle-payload-extraction/v1"
    )
    assert (
        CANDLE_LOGICAL_KEY_VERSION
        == "trader-assist-v0/candle-logical-key/v1"
    )
    assert (
        SOURCE_CATALOG_HASH
        == "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
    )
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"


def test_extracts_valid_ws_singular_candle_deterministically() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    first = _extract(payload)
    second = _extract(payload)

    assert first == second
    assert first.envelope_shape is CandleEnvelopeShapeV0.WS_DATA_CANDLE
    assert len(first.candles) == 1
    candle = first.candles[0]
    assert candle.open_price == Decimal("3000")
    assert candle.close_price == Decimal("3001")
    assert candle.volume_base == Decimal("12.5")
    assert first.extraction_hash == compute_candle_extraction_hash(first)
    dumped = first.model_dump(mode="json")
    assert dumped["candles"][0]["volume_base"] == "12.5"


def test_extracts_valid_ws_array_in_payload_order() -> None:
    first_candle = _candle(open_time=1000, close_time=1999)
    second_candle = _candle(
        open_time=2000,
        close_time=2999,
        close_price=3002,
        high_price=3003,
    )
    payload = _json_bytes(
        {"channel": "candle", "data": [first_candle, second_candle]}
    )

    result = _extract(payload)

    assert result.envelope_shape is CandleEnvelopeShapeV0.WS_DATA_CANDLE_ARRAY
    assert [item.open_time_ms for item in result.candles] == [1000, 2000]


def test_extracts_valid_info_array_and_empty_arrays_without_sentinel_events() -> None:
    payload = _json_bytes([_candle()])
    result = _extract(
        payload,
        endpoint_id="hl-info-mainnet-public",
        operation_type="candleSnapshot",
        capture_mode=RawCaptureModeV0.HTTP_RESPONSE_BODY,
    )
    assert result.envelope_shape is CandleEnvelopeShapeV0.INFO_CANDLE_ARRAY
    assert len(result.candles) == 1

    empty_payload = b"[]"
    empty_result = _extract(
        empty_payload,
        endpoint_id="hl-info-mainnet-public",
        operation_type="candleSnapshot",
        capture_mode=RawCaptureModeV0.HTTP_RESPONSE_BODY,
    )
    assert empty_result.candles == ()


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        b"\xef\xbb\xbf{}",
        b"{",
        b'{"channel":"candle","data":{"t":NaN}}',
        b'{"channel":"candle","channel":"candle","data":[]}',
    ],
)
def test_rejects_invalid_utf8_bom_malformed_nonfinite_and_duplicate_keys(
    payload: bytes,
) -> None:
    with pytest.raises(CandlePayloadExtractionError):
        _extract(payload)


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"channel": "trades", "data": _candle()},
        {"channel": "candle"},
        {"channel": "candle", "data": _candle(), "extra": True},
        {"channel": "candle", "data": "not-a-candle"},
    ],
)
def test_rejects_invalid_ws_envelopes(value: Any) -> None:
    payload = _json_bytes(value)
    with pytest.raises(CandlePayloadExtractionError):
        _extract(payload)


def test_rejects_invalid_info_envelope() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    with pytest.raises(CandlePayloadExtractionError):
        _extract(
            payload,
            endpoint_id="hl-info-mainnet-public",
            operation_type="candleSnapshot",
            capture_mode=RawCaptureModeV0.HTTP_RESPONSE_BODY,
        )


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("missing", None),
        ("extra", 1),
        ("o", "3000"),
        ("t", True),
        ("t", -1),
        ("T", 999),
        ("o", 0),
        ("o", -1),
        ("v", -1),
        ("n", -1),
        ("h", 2998),
        ("l", 3002),
        ("s", "BTC"),
        ("i", "5m"),
    ],
)
def test_rejects_invalid_candle_fields(
    mutation: str,
    value: Any,
) -> None:
    candle = _candle(open_time=1000, close_time=1999)
    if mutation == "missing":
        candle.pop("o")
    elif mutation == "extra":
        candle["extra"] = value
    else:
        candle[mutation] = value
    payload = _json_bytes({"channel": "candle", "data": candle})

    with pytest.raises((CandlePayloadExtractionError, ValidationError, ValueError)):
        _extract(payload)


def test_rejects_duplicate_logical_candle_key() -> None:
    candle = _candle()
    payload = _json_bytes(
        {"channel": "candle", "data": [candle, candle]}
    )
    with pytest.raises(
        CandlePayloadExtractionError,
        match="duplicate candle logical key",
    ):
        _extract(payload)


def test_rejects_payload_hash_and_size_mismatch() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    raw = _raw(payload)
    with pytest.raises(CandlePayloadExtractionError, match="hash"):
        extract_candle_payload(raw_event=raw, payload=payload + b" ")

    material = raw.model_dump(mode="python", round_trip=True)
    material["payload_size_bytes"] += 1
    wrong_size = RawEventV0.model_validate(material)
    with pytest.raises(CandlePayloadExtractionError, match="size"):
        extract_candle_payload(raw_event=wrong_size, payload=payload)


@pytest.mark.parametrize(
    ("content_type", "payload_encoding"),
    [("text/plain", "utf-8"), ("application/json", "UTF-8")],
)
def test_rejects_wrong_content_type_or_encoding(
    content_type: str,
    payload_encoding: str,
) -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    raw = _raw(
        payload,
        content_type=content_type,
        payload_encoding=payload_encoding,
    )
    with pytest.raises(CandlePayloadExtractionError):
        extract_candle_payload(raw_event=raw, payload=payload)


def test_rejects_wrong_source_selection_and_capture_mode() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    trades_raw = _raw(
        payload,
        operation_type="trades",
        coin="ETH",
        interval=None,
    )
    with pytest.raises(CandlePayloadExtractionError):
        extract_candle_payload(raw_event=trades_raw, payload=payload)

    with pytest.raises(ValueError):
        _raw(
            payload,
            capture_mode=RawCaptureModeV0.HTTP_RESPONSE_BODY,
        )


@pytest.mark.parametrize(
    ("coin", "interval"),
    [("SOL", "1m"), ("ETH", "30m")],
)
def test_unsupported_coin_and_interval_fail_at_raw_authority(
    coin: str,
    interval: str,
) -> None:
    payload = _json_bytes(
        {
            "channel": "candle",
            "data": _candle(coin=coin, interval=interval),
        }
    )
    with pytest.raises((ValueError, ValidationError)):
        _raw(payload, coin=coin, interval=interval)


def test_requires_exact_raw_event_and_exact_payload_bytes() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    with pytest.raises(TypeError):
        extract_candle_payload(raw_event=cast(Any, {}), payload=payload)
    with pytest.raises(TypeError):
        extract_candle_payload(
            raw_event=_raw(payload),
            payload=cast(Any, bytearray(payload)),
        )

    class RawEventSubclass(RawEventV0):
        pass

    fabricated = object.__new__(RawEventSubclass)
    with pytest.raises(TypeError):
        extract_candle_payload(raw_event=fabricated, payload=payload)


def test_a5_models_reject_mutation_and_hash_forgery() -> None:
    payload = _json_bytes({"channel": "candle", "data": _candle()})
    result = _extract(payload)
    with pytest.raises(TypeError):
        result.model_copy(update={"coin": "BTC"})
    forged = result.model_dump(mode="python", round_trip=True)
    forged["extraction_hash"] = "0" * 64
    with pytest.raises(ValidationError):
        CandlePayloadExtractionV0.model_validate(forged)


def test_extractor_has_no_network_async_or_filesystem_capability() -> None:
    tree = ast.parse(inspect.getsource(candle_extractor))
    forbidden_import_roots = {
        "aiohttp",
        "asyncio",
        "http",
        "httpx",
        "pathlib",
        "requests",
        "socket",
        "ssl",
        "urllib",
        "urllib3",
        "websocket",
        "websockets",
    }
    forbidden_async_nodes = (
        ast.AsyncFunctionDef,
        ast.Await,
        ast.AsyncFor,
        ast.AsyncWith,
    )
    for node in ast.walk(tree):
        assert not isinstance(node, forbidden_async_nodes)
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
            assert roots.isdisjoint(forbidden_import_roots)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module.split(".")[0] not in forbidden_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "exec", "eval"}
