from __future__ import annotations

import ast
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.contracts.events import RawCaptureModeV0
from trader_assist_v0.contracts.source_catalog import RATE_LIMIT_STATUS
from trader_assist_v0.data.bronze import BronzeStore
from trader_assist_v0.data.ingress import (
    A2_CONTRACT_ID,
    assert_live_transport_blocked_by_rate_limit_gate,
    bind_public_observation_bytes,
    ingest_public_observation_bytes,
)

NOW = datetime(2026, 7, 10, 0, 0, tzinfo=UTC)


def _bind(payload: bytes, *, sequence: int = 1):
    return bind_public_observation_bytes(
        payload=payload,
        endpoint_id="hl-ws-mainnet-public",
        operation_type="candle",
        coin="ETH",
        candle_interval="1m",
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id="conn-a2-contract",
        subscription_id="sub-a2-candle",
        receive_sequence=sequence,
        first_observed_time=NOW,
        collector_receive_time=NOW,
        collector_monotonic_ns=1_000_000 + sequence,
    )


def test_a2_contract_keeps_live_transport_blocked_by_unresolved_rate_limit() -> None:
    assert A2_CONTRACT_ID == "V0-01A2-NO-NETWORK-PUBLIC-OBSERVATION-INGRESS-CONTRACT"
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert_live_transport_blocked_by_rate_limit_gate()


def test_bind_public_observation_uses_exact_caller_supplied_bytes() -> None:
    compact = b'{"channel":"candle","data":{"s":"ETH","i":"1m"}}'
    spaced = b'{ "channel": "candle", "data": { "s": "ETH", "i": "1m" } }'

    first = _bind(compact, sequence=1)
    second = _bind(spaced, sequence=2)

    assert first.payload_sha256 == hashlib.sha256(compact).hexdigest()
    assert second.payload_sha256 == hashlib.sha256(spaced).hexdigest()
    assert first.payload_sha256 != second.payload_sha256
    assert first.payload_ref == (
        f"payloads/sha256/{first.payload_sha256[:2]}/{first.payload_sha256}.payload"
    )
    assert first.source_event_id != second.source_event_id
    assert first.source_event_time is None
    assert first.source_publish_time is None
    assert first.revision_time is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation_type": "/exchange"},
        {"operation_type": "order"},
        {"operation_type": "nonce"},
        {"endpoint_id": "hl-private-mainnet"},
        {"endpoint_id": "hl-account-mainnet"},
        {"capture_mode": RawCaptureModeV0.HTTP_RESPONSE_BODY},
        {"coin": "SOL"},
        {"candle_interval": "30m"},
    ],
)
def test_bind_public_observation_rejects_private_or_write_classes(
    kwargs: dict[str, object],
) -> None:
    request: dict[str, object] = {
        "payload": b'{"channel":"candle","data":{"s":"ETH","i":"1m"}}',
        "endpoint_id": "hl-ws-mainnet-public",
        "operation_type": "candle",
        "coin": "ETH",
        "candle_interval": "1m",
        "capture_mode": RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        "connection_id": "conn-a2-contract",
        "subscription_id": "sub-a2-candle",
        "receive_sequence": 1,
        "first_observed_time": NOW,
        "collector_receive_time": NOW,
        "collector_monotonic_ns": 1_000_001,
    }
    request.update(kwargs)

    with pytest.raises(ValueError):
        bind_public_observation_bytes(**request)


def test_bind_public_observation_rejects_mutable_or_text_payloads() -> None:
    with pytest.raises(TypeError, match="exact bytes"):
        _bind(bytearray(b'{"channel":"candle"}'))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact bytes"):
        _bind('{"channel":"candle"}')  # type: ignore[arg-type]


def test_ingress_can_persist_payload_without_manifest_writer(tmp_path: Path) -> None:
    root = tmp_path / "bronze"
    root.mkdir()
    store = BronzeStore(root)
    payload = b'{"channel":"allMids","data":{"ETH":"3000"}}'

    result = ingest_public_observation_bytes(
        payload=payload,
        endpoint_id="hl-ws-mainnet-public",
        operation_type="allMids",
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id="conn-a2-contract",
        subscription_id="sub-a2-allmids",
        receive_sequence=7,
        first_observed_time=NOW,
        collector_receive_time=NOW,
        collector_monotonic_ns=1_000_007,
        store=store,
    )

    assert result.payload_write is not None
    assert result.payload_write.payload_sha256 == hashlib.sha256(payload).hexdigest()
    assert result.manifest_append is None
    assert store.read_bytes(result.raw_event.payload_ref) == payload


def test_a2_implementation_has_no_network_imports_or_async_runtime() -> None:
    source_path = (
        Path(__file__).resolve().parents[1] / "src" / "trader_assist_v0" / "data" / "ingress.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    banned_modules = {
        "socket",
        "ssl",
        "asyncio",
        "http.client",
        "urllib",
        "urllib.request",
        "urllib3",
        "requests",
        "websockets",
        "websocket",
        "aiohttp",
        "httpx",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported = {alias.name for alias in node.names}
            assert imported.isdisjoint(banned_modules)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            assert node.module not in banned_modules
        if isinstance(
            node,
            ast.AsyncFunctionDef | ast.Await | ast.AsyncFor | ast.AsyncWith,
        ):
            raise AssertionError("A2 ingress must not introduce async runtime syntax")
