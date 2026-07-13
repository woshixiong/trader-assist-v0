from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    EthMarketData,
    MarketDataError,
    ReconnectController,
    candle_from_websocket,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


def _evidence(raw: str, sequence: int = 1):
    return evidence_from_raw(
        raw,
        operation="WebSocket",
        received_at=NOW,
        receive_sequence=sequence,
        connection_id="connection-1",
    )


def _candle(interval: str, offset: int) -> Candle:
    width = 300_000 if interval == "5m" else 900_000
    close = int(NOW.timestamp() * 1000) - (1_000 + offset * width)
    raw = json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": close - width,
                "T": close,
                "o": "100",
                "h": "102",
                "l": "99",
                "c": "101",
                "v": "12",
            },
        },
        separators=(",", ":"),
    )
    return candle_from_websocket(raw, _evidence(raw, offset + 1))


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
    data.accept_context(context_from_websocket(context_raw, _evidence(context_raw, 100)))
    metadata_raw = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    data.accept_metadata(metadata_from_info(metadata_raw, _evidence(metadata_raw, 101)))
    return data


def test_warmup_ready_and_freshness() -> None:
    data = EthMarketData()
    assert data.quality(NOW).state is DataQualityState.DISCONNECTED
    data.begin_connection()
    assert data.quality(NOW).state is DataQualityState.METADATA_UNAVAILABLE
    data = _ready_data()
    assert data.quality(NOW).state is DataQualityState.READY
    assert data.active_context is not None
    assert str(data.active_context.reference_price) == "100.9"
    assert data.quality(NOW + timedelta(seconds=16)).reason == "ACTIVE_ASSET_CONTEXT_STALE"


def test_gap_duplicate_and_conflict_fail_closed() -> None:
    data = _ready_data()
    existing = _candle("5m", 0)
    assert data.accept_candle(existing) == "DUPLICATE"
    raw = existing.evidence.raw_text.replace('"c":"101"', '"c":"100"')
    conflict = candle_from_websocket(raw, _evidence(raw, 999))
    assert data.accept_candle(conflict) == "CONFLICT"
    assert data.quality(NOW).state is DataQualityState.CONFLICT

    gap = _ready_data()
    gap.accept_candle(_candle("5m", 36))
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
    unclosed = Candle(
        interval=candle.interval,
        open_time_ms=candle.open_time_ms,
        close_time_ms=int(NOW.timestamp() * 1000),
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        evidence=candle.evidence,
    )
    assert data.accept_candle(unclosed) == "CONFLICT"
    assert data.quality(NOW).state is DataQualityState.INVALID


def test_reconnect_schedule_has_no_overlap_and_resets_after_five_minutes() -> None:
    controller = ReconnectController()
    assert controller.next_delay_seconds() == 1
    with pytest.raises(MarketDataError, match="overlapping"):
        controller.next_delay_seconds()
    controller.connection_opened(NOW)
    controller.on_disconnect()
    assert [controller.next_delay_seconds()] == [2]
    controller.connection_opened(NOW)
    controller.observe_health(NOW + timedelta(minutes=5))
    controller.on_disconnect()
    assert controller.next_delay_seconds() == 1


def test_live_and_replay_normalization_are_identical() -> None:
    raw = (
        '{"channel":"candle","data":{"s":"ETH","i":"5m","t":1000,'
        '"T":301000,"o":"1","h":"2","l":"1","c":"2","v":"3"}}'
    )
    live_data = EthMarketData()
    replay_data = EthMarketData()
    live_data.begin_connection()
    replay_data.begin_connection()
    assert (
        live_data.ingest_websocket(
            raw, received_at=NOW, receive_sequence=1, connection_id="connection-1"
        )
        == "ACCEPTED"
    )
    assert (
        replay_data.ingest_websocket(
            raw, received_at=NOW, receive_sequence=1, connection_id="connection-1"
        )
        == "ACCEPTED"
    )
    live = next(iter(live_data.candles["5m"].values()))
    replay = next(iter(replay_data.candles["5m"].values()))
    assert live.canonical_hash == replay.canonical_hash
    assert live.identity == replay.identity
