from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pytest

from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    EthMarketData,
    MarketDataError,
    RawEvidence,
    ReconnectController,
    candle_from_websocket,
    candles_from_snapshot,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


def _evidence(raw: str, operation: str = "WebSocket", sequence: int = 1) -> RawEvidence:
    return evidence_from_raw(
        raw,
        operation=operation,
        received_at=NOW,
        receive_sequence=sequence,
        connection_id="connection-1",
    )


def _candle(interval: Literal["5m", "15m"], offset: int) -> Candle:
    width = 300_000 if interval == "5m" else 900_000
    close_time = int(NOW.timestamp() * 1000) - (1_000 + offset * width)
    raw = json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": close_time - width,
                "T": close_time,
                "o": "100",
                "h": "102",
                "l": "99",
                "c": "101",
                "v": "12",
                "n": 1,
            },
        },
        separators=(",", ":"),
    )
    return candle_from_websocket(raw, _evidence(raw, sequence=offset + 1))


def _ready_data() -> EthMarketData:
    data = EthMarketData()
    data.begin_connection()
    for interval, count in (("5m", 36), ("15m", 20)):
        for offset in reversed(range(count)):
            assert data.accept_candle(_candle(interval, offset)) == "ACCEPTED"

    context_raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"101","midPx":"100.9","openInterest":"5","funding":"0.001"}}}'
    )
    data.accept_context(context_from_websocket(context_raw, _evidence(context_raw, sequence=100)))

    metadata_raw = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    data.accept_metadata(
        metadata_from_info(
            metadata_raw,
            _evidence(metadata_raw, operation="metaAndAssetCtxs", sequence=101),
        )
    )
    return data


def test_raw_evidence_constructor_and_factory_are_fail_closed() -> None:
    raw = '{"channel":"candle","data":{}}'
    digest = hashlib.sha256(raw.encode()).hexdigest()
    assert RawEvidence(raw, digest, "source", "WebSocket", NOW, 0, "connection").received_at == NOW

    for sequence in (True, 1.0, -1):
        with pytest.raises(MarketDataError):
            evidence_from_raw(
                raw,
                operation="WebSocket",
                received_at=NOW,
                receive_sequence=sequence,
                connection_id="connection",
            )

    defaults: dict[str, object] = {
        "raw_text": raw,
        "sha256": digest,
        "source_id": "source",
        "operation": "WebSocket",
        "received_at": NOW,
        "receive_sequence": 1,
        "connection_id": "connection",
        "product_version": "ETH-public-normalized-v0.1",
    }
    for field in ("source_id", "operation", "connection_id", "product_version"):
        for invalid in ("", " untrimmed", 3):
            values = {**defaults, field: invalid}
            with pytest.raises(MarketDataError):
                RawEvidence(**values)

    with pytest.raises(MarketDataError):
        RawEvidence(raw, "0" * 64, "source", "WebSocket", NOW, 1, "connection")
    for invalid_received_at in (datetime(2026, 7, 14, 12, 0), "not-a-datetime"):
        with pytest.raises(MarketDataError):
            evidence_from_raw(
                raw,
                operation="WebSocket",
                received_at=invalid_received_at,
                receive_sequence=1,
                connection_id="connection",
            )


def test_lower_parsers_bind_raw_text_hash_and_operation() -> None:
    candle = (
        '{"channel":"candle","data":{"s":"ETH","i":"5m","t":0,"T":300000,'
        '"o":"1","h":"2","l":"1","c":"2","v":"3","n":1}}'
    )
    evidence = _evidence(candle)
    assert candle_from_websocket(candle, evidence).interval == "5m"
    with pytest.raises(MarketDataError):
        candle_from_websocket(candle + " ", evidence)
    with pytest.raises(MarketDataError):
        candle_from_websocket(candle, _evidence(candle, "metaAndAssetCtxs"))

    context = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"1","openInterest":"0","funding":"0"}}}'
    )
    assert context_from_websocket(context, _evidence(context)).open_interest == Decimal("0")
    with pytest.raises(MarketDataError):
        context_from_websocket(context, _evidence(context, "metaAndAssetCtxs"))

    metadata = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    assert metadata_from_info(metadata, _evidence(metadata, "metaAndAssetCtxs")).sz_decimals == 3
    with pytest.raises(MarketDataError):
        metadata_from_info(metadata, _evidence(metadata))


def test_active_context_requires_explicit_eth_and_nonnegative_open_interest() -> None:
    template = '{"channel":"activeAssetCtx","data":%s}'
    good = template % '{"coin":"ETH","ctx":{"markPx":"1","openInterest":"0","funding":"0"}}'
    assert context_from_websocket(good, _evidence(good)).open_interest == Decimal("0")

    for payload in (
        '{"ctx":{"markPx":"1","openInterest":"0","funding":"0"}}',
        '{"coin":"BTC","ctx":{"markPx":"1","openInterest":"0","funding":"0"}}',
        '{"coin":"ETH","ctx":{"markPx":"1","openInterest":"-1","funding":"0"}}',
    ):
        raw = template % payload
        with pytest.raises(MarketDataError):
            context_from_websocket(raw, _evidence(raw))


def test_raw_evidence_normalizes_timezone() -> None:
    raw = "{}"
    value = evidence_from_raw(
        raw,
        operation="WebSocket",
        received_at=NOW.astimezone(UTC),
        receive_sequence=1,
        connection_id="connection",
    )
    assert value.received_at.tzinfo is UTC


def test_warmup_ready_and_freshness() -> None:
    data = EthMarketData()
    assert data.quality(NOW).state is DataQualityState.DISCONNECTED

    data.begin_connection()
    assert data.quality(NOW).state is DataQualityState.METADATA_UNAVAILABLE

    data = _ready_data()
    assert data.quality(NOW).state is DataQualityState.READY
    assert data.active_context is not None
    assert data.active_context.reference_price == Decimal("100.9")
    stale = data.quality(NOW + timedelta(seconds=16))
    assert stale.state is DataQualityState.STALE
    assert stale.reason == "ACTIVE_ASSET_CONTEXT_STALE"


def test_gap_duplicate_and_conflict_fail_closed() -> None:
    data = _ready_data()
    existing = _candle("5m", 0)
    assert data.accept_candle(existing) == "DUPLICATE"

    conflicting_raw = existing.evidence.raw_text.replace('"c":"101"', '"c":"100"')
    conflicting = candle_from_websocket(
        conflicting_raw,
        _evidence(conflicting_raw, sequence=999),
    )
    assert data.accept_candle(conflicting) == "CONFLICT"
    assert data.quality(NOW).state is DataQualityState.CONFLICT

    gap = _ready_data()
    assert gap.accept_candle(_candle("5m", 36)) == "ACCEPTED"
    del gap.candles["5m"][sorted(gap.candles["5m"])[-2]]
    assert gap.quality(NOW).state is DataQualityState.GAP
    gap.mark_disconnected()
    assert gap.quality(NOW).state is DataQualityState.GAP


def test_snapshot_bound_and_closed_candle_gate() -> None:
    data = EthMarketData()
    data.begin_connection()

    with pytest.raises(MarketDataError, match="snapshot"):
        data.recover_snapshot("5m", [_candle("5m", 0)] * 65)

    candle = _candle("5m", 0)
    unclosed = replace(candle, close_time_ms=int(NOW.timestamp() * 1000))
    with pytest.raises(MarketDataError, match="parser-issued"):
        data.accept_candle(unclosed)


def test_direct_or_modified_normalized_objects_are_not_ingestable() -> None:
    data = EthMarketData()
    data.begin_connection()
    issued = _candle("5m", 0)
    raw = "{}"
    evidence = RawEvidence(
        raw,
        hashlib.sha256(raw.encode()).hexdigest(),
        "source",
        "WebSocket",
        NOW,
        1,
        "connection",
    )
    direct = Candle(
        issued.interval,
        issued.open_time_ms,
        issued.close_time_ms,
        issued.open,
        issued.high,
        issued.low,
        issued.close,
        issued.volume,
        evidence,
    )
    for candidate in (direct, replace(issued), object.__new__(Candle)):
        with pytest.raises(MarketDataError, match="parser-issued"):
            data.accept_candle(candidate)  # type: ignore[arg-type]

    context_raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"1","openInterest":"0","funding":"0"}}}'
    )
    issued_context = context_from_websocket(context_raw, _evidence(context_raw))
    with pytest.raises(MarketDataError, match="parser-issued"):
        data.accept_context(replace(issued_context))

    metadata_raw = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    issued_metadata = metadata_from_info(
        metadata_raw,
        _evidence(metadata_raw, "metaAndAssetCtxs"),
    )
    with pytest.raises(MarketDataError, match="parser-issued"):
        data.accept_metadata(replace(issued_metadata))


def test_primary_ingest_and_reconnect_paths_retain_evidence_validation() -> None:
    raw = (
        '{"channel":"candle","data":{"s":"ETH","i":"5m","t":0,'
        '"T":300000,"o":"1","h":"2","l":"1","c":"2","v":"3","n":1}}'
    )
    data = EthMarketData()
    data.begin_connection()
    assert (
        data.ingest_websocket(
            raw,
            received_at=NOW,
            receive_sequence=1,
            connection_id="connection-1",
        )
        == "ACCEPTED"
    )
    with pytest.raises(MarketDataError):
        data.ingest_websocket(
            raw,
            received_at=NOW,
            receive_sequence=True,
            connection_id="connection-1",
        )

    controller = ReconnectController()
    assert controller.next_delay_seconds() == 1
    with pytest.raises(MarketDataError, match="overlapping"):
        controller.next_delay_seconds()
    controller.connection_opened(NOW)
    controller.on_disconnect()
    assert controller.next_delay_seconds() == 2
    controller.connection_opened(NOW)
    controller.observe_health(NOW + timedelta(minutes=5))
    controller.on_disconnect()
    assert controller.next_delay_seconds() == 1


def test_live_and_replay_normalization_are_identical() -> None:
    raw = (
        '{"channel":"candle","data":{"s":"ETH","i":"5m","t":1000,'
        '"T":301000,"o":"1","h":"2","l":"1","c":"2","v":"3","n":1}}'
    )
    live_data = EthMarketData()
    replay_data = EthMarketData()
    live_data.begin_connection()
    replay_data.begin_connection()

    assert (
        live_data.ingest_websocket(
            raw,
            received_at=NOW,
            receive_sequence=1,
            connection_id="connection-1",
        )
        == "ACCEPTED"
    )
    assert (
        replay_data.ingest_websocket(
            raw,
            received_at=NOW,
            receive_sequence=1,
            connection_id="connection-1",
        )
        == "ACCEPTED"
    )

    live = next(iter(live_data.candles["5m"].values()))
    replay = next(iter(replay_data.candles["5m"].values()))
    assert live.identity == replay.identity
    assert live.canonical_hash == replay.canonical_hash
    assert (
        live.interval,
        live.open_time_ms,
        live.close_time_ms,
        live.open,
        live.high,
        live.low,
        live.close,
        live.volume,
    ) == (
        replay.interval,
        replay.open_time_ms,
        replay.close_time_ms,
        replay.open,
        replay.high,
        replay.low,
        replay.close,
        replay.volume,
    )


def test_public_candle_snapshot_is_strict_closed_parser_issued_authority() -> None:
    close = int(NOW.timestamp() * 1000) - 1
    raw = json.dumps(
        [
            {
                "t": close - 300_000,
                "T": close,
                "s": "ETH",
                "i": "5m",
                "o": "100",
                "c": "101",
                "h": "102",
                "l": "99",
                "v": "0",
                "n": 3,
            }
        ],
        separators=(",", ":"),
    )
    evidence = _evidence(raw, operation="candleSnapshot")
    candles = candles_from_snapshot(raw, evidence, requested_interval="5m")
    assert len(candles) == 1
    assert candles[0].canonical_hash
    assert evidence.sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_snapshot_rejects_wrong_interval_duplicate_keys_and_open_candles() -> None:
    close = int(NOW.timestamp() * 1000)
    open_raw = json.dumps(
        [
            {
                "t": close - 300_000,
                "T": close,
                "s": "ETH",
                "i": "5m",
                "o": "1",
                "c": "1",
                "h": "1",
                "l": "1",
                "v": "0",
                "n": 0,
            }
        ],
        separators=(",", ":"),
    )
    evidence = _evidence(open_raw, operation="candleSnapshot")
    assert candles_from_snapshot(open_raw, evidence, requested_interval="5m") == ()
    data = EthMarketData()
    data.begin_connection()
    assert (
        data.ingest_candle_snapshot(
            open_raw,
            interval="5m",
            received_at=NOW,
            receive_sequence=2,
            connection_id="snapshot",
        )
        == ()
    )
    assert data.invalid_reason is None
    wrong = open_raw.replace('"i":"5m"', '"i":"15m"')
    with pytest.raises(MarketDataError):
        candles_from_snapshot(wrong, _evidence(wrong, "candleSnapshot"), requested_interval="5m")
    duplicate = '[{"t":1,"t":1}]'
    with pytest.raises(MarketDataError):
        candles_from_snapshot(
            duplicate, _evidence(duplicate, "candleSnapshot"), requested_interval="5m"
        )
