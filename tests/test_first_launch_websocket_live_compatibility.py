from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import pytest

from tests.test_first_launch_public_runtime import (
    NOW,
    _make_runtime,
    _recover_to_ready,
    _warmup_to_active,
)
from trader_assist_v0.runtime.first_launch_operator_assist import (
    REQUIRED_PUBLIC_SUBSCRIPTIONS,
    ProtocolAcknowledgementError,
    PublicRuntimeProtocol,
    PublicSessionState,
)
from trader_assist_v0.runtime.first_launch_public_runtime import CandleRefreshTrigger


def _acknowledgement(subscription: object) -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": subscription,
            },
        },
        separators=(",", ":"),
    )


def _candle_frame(
    now: datetime,
    *,
    interval: Literal["5m", "15m"] = "5m",
    open_candle: bool,
    symbol: str = "ETH",
    volume: str = "3",
    omit: str | None = None,
) -> str:
    assert now.tzinfo is UTC
    width = 300_000 if interval == "5m" else 900_000
    now_ms = int(now.timestamp() * 1000)
    if open_candle:
        open_time = (now_ms // width) * width
        close_time = open_time + width - 1
    else:
        close_time = now_ms - 1
        open_time = close_time - width + 1
    payload: dict[str, object] = {
        "s": symbol,
        "i": interval,
        "t": open_time,
        "T": close_time,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": "101",
        "v": volume,
        "n": 1,
    }
    if omit is not None:
        del payload[omit]
    return json.dumps(
        {"channel": "candle", "data": payload},
        separators=(",", ":"),
    )


def _candle_frame_at_close(
    *,
    open_time_ms: int,
    interval: Literal["5m", "15m"] = "5m",
) -> str:
    width = 300_000 if interval == "5m" else 900_000
    return json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": open_time_ms,
                "T": open_time_ms + width - 1,
                "o": "100",
                "h": "102",
                "l": "99",
                "c": "101",
                "v": "3",
                "n": 1,
            },
        },
        separators=(",", ":"),
    )


def _context_frame(*, coin: str = "ETH", mark_px: str = "101") -> str:
    return json.dumps(
        {
            "channel": "activeAssetCtx",
            "data": {
                "coin": coin,
                "ctx": {
                    "markPx": mark_px,
                    "midPx": "100.9",
                    "openInterest": "5",
                    "funding": "0.001",
                },
            },
        },
        separators=(",", ":"),
    )


def _active_protocol(now: datetime) -> PublicRuntimeProtocol:
    protocol = PublicRuntimeProtocol(
        connection_id="connection-live",
        utc_now=lambda: now,
        monotonic_now=lambda: 0.0,
    )
    protocol.start()
    for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
        assert protocol.accept_frame(_acknowledgement(spec.subscription)) is None
    assert protocol.state is PublicSessionState.ACTIVE
    return protocol


def test_authorized_public_frames_may_interleave_with_acknowledgements() -> None:
    protocol = PublicRuntimeProtocol(
        connection_id="connection-interleaved",
        utc_now=lambda: NOW,
        monotonic_now=lambda: 0.0,
    )
    protocol.start()
    first, second, third = REQUIRED_PUBLIC_SUBSCRIPTIONS

    assert protocol.accept_frame(_acknowledgement(first.subscription)) is None
    assert protocol.receive_sequence == 1
    assert protocol.acknowledged_subscriptions == {first.identity}

    assert protocol.accept_frame(
        _candle_frame(NOW, interval="5m", open_candle=True)
    ) is None
    assert protocol.receive_sequence == 1
    assert protocol.state is PublicSessionState.AWAITING_ACKNOWLEDGEMENTS
    assert protocol.acknowledged_subscriptions == {first.identity}

    assert protocol.accept_frame(_acknowledgement(second.subscription)) is None
    assert protocol.receive_sequence == 2

    assert protocol.accept_frame(_context_frame()) is None
    assert protocol.receive_sequence == 2
    assert protocol.state is PublicSessionState.AWAITING_ACKNOWLEDGEMENTS
    assert protocol.acknowledged_subscriptions == {first.identity, second.identity}

    assert protocol.accept_frame(_acknowledgement(third.subscription)) is None
    assert protocol.receive_sequence == 3
    assert protocol.state is PublicSessionState.ACTIVE
    assert protocol.acknowledged_subscriptions == {
        first.identity,
        second.identity,
        third.identity,
    }


@pytest.mark.parametrize(
    "frame",
    [
        _candle_frame(NOW, interval="5m", open_candle=True, symbol="BTC"),
        _candle_frame(NOW, interval="5m", open_candle=True, omit="v"),
        _context_frame(coin="BTC"),
        _context_frame(mark_px="not-a-price"),
        '{"channel":"candle","channel":"candle","data":{}}',
    ],
)
def test_invalid_interleaved_public_frames_remain_fail_closed(frame: str) -> None:
    protocol = PublicRuntimeProtocol(
        connection_id="connection-invalid-interleaved",
        utc_now=lambda: NOW,
        monotonic_now=lambda: 0.0,
    )
    protocol.start()
    first = REQUIRED_PUBLIC_SUBSCRIPTIONS[0]
    assert protocol.accept_frame(_acknowledgement(first.subscription)) is None

    with pytest.raises(ProtocolAcknowledgementError):
        protocol.accept_frame(frame)

    assert protocol.state is PublicSessionState.FAILED
    assert protocol.receive_sequence == 1
    assert protocol.acknowledged_subscriptions == {first.identity}


def test_active_protocol_ignores_open_candles_without_sequence_or_state_change() -> None:
    protocol = _active_protocol(NOW)

    assert protocol.accept_frame(
        _candle_frame(NOW, interval="5m", open_candle=True)
    ) is None
    assert protocol.accept_frame(
        _candle_frame(NOW, interval="15m", open_candle=True)
    ) is None
    assert protocol.state is PublicSessionState.ACTIVE
    assert protocol.receive_sequence == 3

    accepted = protocol.accept_frame(
        _candle_frame(NOW, interval="5m", open_candle=False)
    )
    assert accepted is not None
    assert accepted.channel == "candle"
    assert accepted.authoritative is False
    assert accepted.receive_sequence == 3
    assert protocol.allocate_authoritative_sequence() == 4
    assert protocol.state is PublicSessionState.ACTIVE


def test_malformed_open_candle_after_activation_withdraws_ready(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    snapshot_path = tmp_path / "status.json"
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        assert runtime.is_ready is True

        with pytest.raises(ValueError):
            runtime.accept_public_frame(
                frame_text=_candle_frame(
                    NOW,
                    interval="5m",
                    open_candle=True,
                    volume="-1",
                ),
                now=NOW,
            )

        rejected = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert runtime.is_ready is False
        assert rejected["state"] == "NOT_READY"
    finally:
        store.close()


def test_ready_runtime_ignores_open_candles_without_withdrawing_ready(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    snapshot_path = tmp_path / "status.json"
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        before = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert before["state"] == "READY"
        assert before["pid"] == os.getpid()

        assert runtime.accept_public_frame(
            frame_text=_candle_frame(NOW, interval="5m", open_candle=True),
            now=NOW,
        ) is None
        assert runtime.accept_public_frame(
            frame_text=_candle_frame(NOW, interval="15m", open_candle=True),
            now=NOW,
        ) is None

        after = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert runtime.is_ready is True
        assert runtime.health_state.value == "READY"
        assert runtime.remaining_subscriptions == ()
        assert after["state"] == "READY"
        assert after["pid"] == before["pid"] == os.getpid()
        assert after["session_id"] == before["session_id"]
    finally:
        store.close()


def test_runtime_uses_protocol_receipt_time_at_millisecond_close_boundary(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    snapshot_path = tmp_path / "status.json"
    clock = {"now": NOW}
    runtime.utc_now = lambda: clock["now"]
    runtime._lifecycle.utc_now = runtime.utc_now

    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        before = json.loads(snapshot_path.read_text(encoding="utf-8"))
        latest = max(
            runtime._market_data.candles["5m"].values(),
            key=lambda candle: candle.open_time_ms,
        )
        next_open_time_ms = latest.open_time_ms + 300_000
        close_time_ms = next_open_time_ms + 299_999
        caller_now = datetime.fromtimestamp(close_time_ms / 1000, tz=UTC)
        protocol_received_at = caller_now + timedelta(milliseconds=1)
        clock["now"] = protocol_received_at

        runtime.accept_public_frame(frame_text=_context_frame(), now=caller_now)
        frame_text = _candle_frame_at_close(open_time_ms=next_open_time_ms)
        trigger = runtime.accept_public_frame(
            frame_text=frame_text,
            now=caller_now,
        )
        assert type(trigger) is CandleRefreshTrigger
        snapshot = json.dumps([json.loads(frame_text)["data"]], separators=(",", ":"))
        runtime.confirm_candle_refresh(
            trigger=trigger,
            raw_first=snapshot,
            raw_second=snapshot,
            now=protocol_received_at,
        )

        after = json.loads(snapshot_path.read_text(encoding="utf-8"))
        accepted = runtime._market_data.candles["5m"][next_open_time_ms]
        assert accepted.close_time_ms == close_time_ms
        assert accepted.evidence.received_at == protocol_received_at
        assert runtime.is_ready is True
        assert runtime.health_state.value == "READY"
        assert runtime._protocol.state is PublicSessionState.ACTIVE
        assert runtime._protocol.connection_id == "conn-test"
        assert runtime._reconnect_attempt == 0
        assert after["state"] == "READY"
        assert after["pid"] == before["pid"] == os.getpid()
        assert after["session_id"] == before["session_id"]
    finally:
        store.close()
