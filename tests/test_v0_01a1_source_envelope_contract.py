from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from trader_assist_v0.contracts import EnvironmentV0, RawCaptureModeV0, RawEventV0
from trader_assist_v0.contracts.source_catalog import (
    CANDLE_WS_ACCEPTED_ENVELOPE_SHAPES,
    validate_candle_websocket_envelope_shape,
)

NOW = datetime(2026, 7, 9, 1, 0, tzinfo=UTC)


def _payload_ref(payload: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(payload).hexdigest()
    return digest, f"payloads/sha256/{digest[:2]}/{digest}.payload"


def _raw_candle_event(payload: bytes, *, sequence: int = 1) -> RawEventV0:
    digest, ref = _payload_ref(payload)
    return RawEventV0.bind_observation(
        endpoint_id="hl-ws-mainnet-public",
        operation_type="candle",
        coin="ETH",
        candle_interval="1m",
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id="conn-a1-contract",
        subscription_id="sub-a1-candle",
        receive_sequence=sequence,
        source_native_id=None,
        source_native_cursor=None,
        collector_version="collector.0.1",
        environment=EnvironmentV0.READ_ONLY,
        content_type="application/json",
        payload_sha256=digest,
        payload_size_bytes=len(payload),
        payload_encoding="utf-8",
        payload_ref=ref,
        source_event_time=None,
        source_publish_time=None,
        first_observed_time=NOW,
        collector_receive_time=NOW,
        collector_monotonic_ns=123,
        revision_time=None,
    )


def test_candle_websocket_envelope_policy_accepts_only_frozen_shapes() -> None:
    assert CANDLE_WS_ACCEPTED_ENVELOPE_SHAPES == ("data:Candle", "data:Candle[]")
    assert validate_candle_websocket_envelope_shape("data:Candle") == "data:Candle"
    assert validate_candle_websocket_envelope_shape("data:Candle[]") == "data:Candle[]"

    for unsupported in ("data:Trade[]", "data:WsBook", "payload:Candle", "data:{}"):
        with pytest.raises(ValueError):
            validate_candle_websocket_envelope_shape(unsupported)


def test_raw_event_remains_exact_payload_evidence_not_parsed_signal() -> None:
    compact = (
        b'{"channel":"candle","data":{"t":1783386000000,"T":1783386059999,'
        b'"s":"ETH","i":"1m","o":"3000","c":"3001","h":"3002",'
        b'"l":"2999","v":"10","n":42}}'
    )
    spaced = b'{ "channel": "candle", "data": { "s": "ETH", "i": "1m" } }'

    first = _raw_candle_event(compact, sequence=1)
    second = _raw_candle_event(spaced, sequence=2)

    assert first.payload_sha256 == hashlib.sha256(compact).hexdigest()
    assert second.payload_sha256 == hashlib.sha256(spaced).hexdigest()
    assert first.payload_sha256 != second.payload_sha256
    assert first.source_event_id != second.source_event_id
    assert first.source_event_time is None
    assert first.source_publish_time is None
    assert first.revision_time is None
    assert not hasattr(first, "open_price")
    assert not hasattr(first, "direction")
    assert not hasattr(first, "risk_size")
