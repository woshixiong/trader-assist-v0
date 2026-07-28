from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    EthMarketData,
    MarketDataError,
    OpenCandleIgnored,
    RawEvidence,
    ReconnectController,
    candle_from_websocket,
    candles_from_snapshot,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)
from trader_assist_v0.first_launch.outcome import OutcomeError, read_candle_evidence

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
_MISSING = object()


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
                "t": close_time - width + 1,
                "T": close_time,
                "o": "100",
                "h": "102",
                "l": "99",
                "c": "101",
                "v": "12",
                "n": 0,
            },
        },
        separators=(",", ":"),
    )
    return candle_from_websocket(raw, _evidence(raw, sequence=offset + 1))


def _ready_data() -> EthMarketData:
    data = EthMarketData()
    data.begin_connection()
    for interval, count in (("5m", 64), ("15m", 20)):
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
        '{"channel":"candle","data":{"s":"ETH","i":"5m","t":0,"T":299999,'
        '"o":"1","h":"2","l":"1","c":"2","v":"3","n":0}}'
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


def test_strategy_snapshot_is_strictly_causal_at_the_requested_cutoff() -> None:
    data = _ready_data()
    # The same stored observations are valid at equality, but must never make an
    # earlier decision ready merely because they arrived later in memory.
    assert data.strategy_snapshot(NOW).quality.state is DataQualityState.READY
    earlier = data.strategy_snapshot(NOW - timedelta(microseconds=1))
    assert earlier.quality.state is DataQualityState.METADATA_UNAVAILABLE
    assert not earlier.candles_5m and not earlier.candles_15m

    future_context = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"101","openInterest":"5","funding":"0"}}}'
    )
    data.accept_context(
        context_from_websocket(
            future_context,
            evidence_from_raw(
                future_context,
                operation="WebSocket",
                received_at=NOW + timedelta(seconds=1),
                receive_sequence=999,
                connection_id="future",
            ),
        )
    )
    assert data.strategy_snapshot(NOW).quality.state is DataQualityState.WARMING


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
    assert gap.accept_candle(_candle("5m", 64)) == "ACCEPTED"
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
        '"T":299999,"o":"1","h":"2","l":"1","c":"2","v":"3","n":0}}'
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
        '"T":300999,"o":"1","h":"2","l":"1","c":"2","v":"3","n":0}}'
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


@pytest.mark.parametrize("trade_count", [1, 0])
def test_closed_websocket_and_snapshot_candles_require_valid_trade_counts(
    trade_count: int,
) -> None:
    close_time = int(NOW.timestamp() * 1000) - 1_000
    candle = {
        "s": "ETH",
        "i": "5m",
        "t": close_time - 300_000 + 1,
        "T": close_time,
        "o": "1",
        "h": "2",
        "l": "1",
        "c": "2",
        "v": "3",
        "n": trade_count,
    }
    websocket = json.dumps({"channel": "candle", "data": candle}, separators=(",", ":"))
    snapshot = json.dumps([candle], separators=(",", ":"))
    assert candle_from_websocket(websocket, _evidence(websocket)).interval == "5m"
    assert (
        len(
            candles_from_snapshot(
                snapshot,
                _evidence(snapshot, "candleSnapshot"),
                requested_interval="5m",
            )
        )
        == 1
    )


@pytest.mark.parametrize("trade_count", [_MISSING, None, True, False, "1", 1.0, -1])
def test_invalid_or_missing_trade_count_is_rejected_before_issuance(
    monkeypatch: pytest.MonkeyPatch, trade_count: object
) -> None:
    import trader_assist_v0.first_launch.market_data as market_data

    close_time = int(NOW.timestamp() * 1000) - 1_000
    candle: dict[str, object] = {
        "s": "ETH",
        "i": "5m",
        "t": close_time - 300_000 + 1,
        "T": close_time,
        "o": "1",
        "h": "2",
        "l": "1",
        "c": "2",
        "v": "3",
    }
    if trade_count is not _MISSING:
        candle["n"] = trade_count
    issued: list[object] = []
    original_issue = market_data._issue

    def issue_spy(value: object, fingerprint: str) -> object:
        issued.append(value)
        return original_issue(value, fingerprint)

    monkeypatch.setattr(market_data, "_issue", issue_spy)
    websocket = json.dumps({"channel": "candle", "data": candle}, separators=(",", ":"))
    snapshot = json.dumps([candle], separators=(",", ":"))
    with pytest.raises(MarketDataError):
        candle_from_websocket(websocket, _evidence(websocket))
    with pytest.raises(MarketDataError):
        candles_from_snapshot(
            snapshot,
            _evidence(snapshot, "candleSnapshot"),
            requested_interval="5m",
        )
    data = EthMarketData()
    data.begin_connection()
    with pytest.raises(MarketDataError):
        data.ingest_websocket(
            websocket,
            received_at=NOW,
            receive_sequence=1,
            connection_id="connection-1",
        )
    assert data.candles["5m"] == {}
    assert issued == []


def test_open_websocket_candle_raises_control_flow_exception_and_ingest_ignores_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import trader_assist_v0.first_launch.market_data as market_data

    close_time = int(NOW.timestamp() * 1000)
    candle = {
        "s": "ETH",
        "i": "5m",
        "t": close_time - 300_000 + 1,
        "T": close_time,
        "o": "1",
        "h": "2",
        "l": "1",
        "c": "2",
        "v": "3",
        "n": 0,
    }
    issued: list[object] = []
    original_issue = market_data._issue

    def issue_spy(value: object, fingerprint: str) -> object:
        issued.append(value)
        return original_issue(value, fingerprint)

    monkeypatch.setattr(market_data, "_issue", issue_spy)
    websocket = json.dumps({"channel": "candle", "data": candle}, separators=(",", ":"))
    snapshot = json.dumps([candle], separators=(",", ":"))
    with pytest.raises(OpenCandleIgnored) as raised:
        candle_from_websocket(websocket, _evidence(websocket))
    assert not isinstance(raised.value, Candle)
    assert (
        candles_from_snapshot(
            snapshot,
            _evidence(snapshot, "candleSnapshot"),
            requested_interval="5m",
        )
        == ()
    )
    data = EthMarketData()
    data.begin_connection()
    accepted: list[object] = []

    def accept_spy(value: Candle) -> str:
        accepted.append(value)
        return "ACCEPTED"

    monkeypatch.setattr(data, "accept_candle", accept_spy)
    assert (
        data.ingest_websocket(
            websocket,
            received_at=NOW,
            receive_sequence=1,
            connection_id="connection-1",
        )
        == "IGNORED_OPEN"
    )
    assert data.candles["5m"] == {}
    assert data.invalid_reason is None
    assert accepted == []
    assert issued == []


def test_snapshot_order_and_interval_are_fail_closed_without_repair() -> None:
    close_time = int(NOW.timestamp() * 1000) - 1_000
    first = {
        "s": "ETH",
        "i": "5m",
        "t": close_time - 600_000 + 1,
        "T": close_time - 300_000,
        "o": "1",
        "h": "2",
        "l": "1",
        "c": "2",
        "v": "3",
        "n": 0,
    }
    second = {**first, "t": close_time - 300_000 + 1, "T": close_time}
    ordered = json.dumps([first, second], separators=(",", ":"))
    unsorted = json.dumps([second, first], separators=(",", ":"))
    wrong_interval = json.dumps([{**first, "i": "15m"}], separators=(",", ":"))
    with pytest.raises(MarketDataError, match="strictly increasing"):
        candles_from_snapshot(
            unsorted,
            _evidence(unsorted, "candleSnapshot"),
            requested_interval="5m",
        )
    assert [
        candle.open_time_ms
        for candle in candles_from_snapshot(
            ordered,
            _evidence(ordered, "candleSnapshot"),
            requested_interval="5m",
        )
    ] == [first["t"], second["t"]]
    with pytest.raises(MarketDataError, match="interval"):
        candles_from_snapshot(
            wrong_interval,
            _evidence(wrong_interval, "candleSnapshot"),
            requested_interval="5m",
        )


def _snapshot_candle(close_time: int, *, n: object = 0, interval: str = "5m") -> dict[str, object]:
    width = 300_000 if interval == "5m" else 900_000
    return {
        "s": "ETH",
        "i": interval,
        "t": close_time - width + 1,
        "T": close_time,
        "o": "1",
        "h": "2",
        "l": "1",
        "c": "2",
        "v": "3",
        "n": n,
    }


def _snapshot_raw(candles: list[dict[str, object]]) -> str:
    return json.dumps(candles, separators=(",", ":"))


def test_closed_websocket_and_snapshot_results_are_exact_issued_candles() -> None:
    import trader_assist_v0.first_launch.market_data as market_data

    now_ms = int(NOW.timestamp() * 1000)
    closed = _snapshot_candle(now_ms - 1_000)
    websocket = json.dumps({"channel": "candle", "data": closed}, separators=(",", ":"))
    result = candle_from_websocket(websocket, _evidence(websocket))
    assert type(result) is Candle
    assert market_data._validated_candle(result) is result

    snapshot = _snapshot_raw([closed])
    recovered = candles_from_snapshot(
        snapshot, _evidence(snapshot, "candleSnapshot"), requested_interval="5m"
    )
    assert len(recovered) == 1 and type(recovered[0]) is Candle
    assert market_data._validated_candle(recovered[0]) is recovered[0]

    equal = _snapshot_candle(now_ms)
    equal_raw = json.dumps({"channel": "candle", "data": equal}, separators=(",", ":"))
    with pytest.raises(OpenCandleIgnored):
        candle_from_websocket(equal_raw, _evidence(equal_raw))


@pytest.mark.parametrize(
    "second",
    [
        pytest.param(lambda now_ms: {**_snapshot_candle(now_ms - 1_000), "v": "bad"}),
        pytest.param(lambda now_ms: {**_snapshot_candle(now_ms), "n": "bad"}),
        pytest.param(
            lambda now_ms: {
                key: value for key, value in _snapshot_candle(now_ms - 1_000).items() if key != "n"
            }
        ),
    ],
)
def test_malformed_snapshot_is_atomic_before_any_issuance(
    monkeypatch: pytest.MonkeyPatch,
    second: Callable[[int], dict[str, object]],
) -> None:
    import trader_assist_v0.first_launch.market_data as market_data

    now_ms = int(NOW.timestamp() * 1000)
    valid = _snapshot_candle(now_ms - 301_000)
    malformed = second(now_ms)
    raw = _snapshot_raw([valid, malformed])
    issued: list[object] = []
    original_issue = market_data._issue

    def issue_spy(value: object, fingerprint: str) -> object:
        issued.append(value)
        return original_issue(value, fingerprint)

    monkeypatch.setattr(market_data, "_issue", issue_spy)
    data = EthMarketData()
    data.begin_connection()
    with pytest.raises(MarketDataError):
        candles_from_snapshot(raw, _evidence(raw, "candleSnapshot"), requested_interval="5m")
    assert issued == [] and data.candles["5m"] == {}


def test_snapshot_open_filtering_preserves_only_closed_prefix_and_rejects_bad_open() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    first = _snapshot_candle(now_ms - 600_000)
    second = _snapshot_candle(now_ms - 300_000)
    trailing_open = _snapshot_candle(now_ms)
    next_open = _snapshot_candle(now_ms + 300_000)
    mixed = _snapshot_raw([first, second, trailing_open])
    multiple = _snapshot_raw([first, second, trailing_open, next_open])
    all_open = _snapshot_raw([trailing_open, next_open])
    assert [
        item.open_time_ms
        for item in candles_from_snapshot(
            mixed, _evidence(mixed, "candleSnapshot"), requested_interval="5m"
        )
    ] == [first["t"], second["t"]]
    assert [
        item.open_time_ms
        for item in candles_from_snapshot(
            multiple, _evidence(multiple, "candleSnapshot"), requested_interval="5m"
        )
    ] == [first["t"], second["t"]]
    assert (
        candles_from_snapshot(
            all_open, _evidence(all_open, "candleSnapshot"), requested_interval="5m"
        )
        == ()
    )
    malformed_open = _snapshot_raw([first, second, {**trailing_open, "n": "bad"}])
    with pytest.raises(MarketDataError):
        candles_from_snapshot(
            malformed_open,
            _evidence(malformed_open, "candleSnapshot"),
            requested_interval="5m",
        )


def test_snapshot_order_duplicate_gap_and_interval_rules_remain_fail_closed() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    first = _snapshot_candle(now_ms - 600_000)
    second = _snapshot_candle(now_ms - 300_000)
    trailing_open = _snapshot_candle(now_ms)
    for payload in (
        [second, first],
        [trailing_open, trailing_open],
        [
            _snapshot_candle(now_ms - 900_000),
            _snapshot_candle(now_ms - 300_000),
        ],
        [{**first, "i": "15m", "t": first["t"] - 600_000}],
    ):
        raw = _snapshot_raw(payload)
        with pytest.raises(MarketDataError):
            candles_from_snapshot(raw, _evidence(raw, "candleSnapshot"), requested_interval="5m")


def test_malformed_and_all_open_snapshots_do_not_invoke_downstream_work() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    malformed = _snapshot_raw(
        [_snapshot_candle(now_ms - 1_000), {**_snapshot_candle(now_ms), "n": "bad"}]
    )
    all_open = _snapshot_raw([_snapshot_candle(now_ms), _snapshot_candle(now_ms + 300_000)])

    def guarded_pipeline(raw: str) -> tuple[int, int, int]:
        calls = [0, 0, 0]
        try:
            candles = candles_from_snapshot(
                raw, _evidence(raw, "candleSnapshot"), requested_interval="5m"
            )
        except MarketDataError:
            return tuple(calls)
        if not candles:
            return tuple(calls)
        calls[0] += 1
        calls[1] += 1
        calls[2] += 1
        return tuple(calls)

    assert guarded_pipeline(malformed) == (0, 0, 0)
    assert guarded_pipeline(all_open) == (0, 0, 0)


def test_direct_integer_subclasses_are_rejected_at_the_integer_boundary() -> None:
    import trader_assist_v0.first_launch.market_data as market_data

    class IntegerSubclass(int):
        pass

    with pytest.raises(MarketDataError):
        market_data._integer(IntegerSubclass(1), "candle trade count")


def test_existing_outcome_reader_fails_closed_on_open_candle_evidence() -> None:
    now_ms = int(NOW.timestamp() * 1000)
    candle = _snapshot_candle(now_ms)
    websocket = json.dumps({"channel": "candle", "data": candle}, separators=(",", ":"))
    payload = canonical_json_bytes(
        {
            "candle_evidence_version": "1",
            "candles": [
                {
                    "raw_text": websocket,
                    "received_at": NOW.isoformat(),
                    "receive_sequence": 1,
                    "connection_id": "connection-1",
                }
            ],
        }
    )
    with pytest.raises(OutcomeError, match="CANDLE_EVIDENCE_INVALID"):
        read_candle_evidence(payload)


def test_hyperliquid_inclusive_close_boundary_is_required() -> None:
    for interval, width in (("5m", 300_000), ("15m", 900_000)):
        good_raw = json.dumps(
            {
                "channel": "candle",
                "data": {
                    "s": "ETH",
                    "i": interval,
                    "t": 0,
                    "T": width - 1,
                    "o": "1",
                    "h": "2",
                    "l": "1",
                    "c": "2",
                    "v": "3",
                    "n": 0,
                },
            },
            separators=(",", ":"),
        )
        candle = candle_from_websocket(good_raw, _evidence(good_raw))
        assert candle.open_time_ms == 0
        assert candle.close_time_ms == width - 1

        legacy_raw = json.dumps(
            {
                "channel": "candle",
                "data": {
                    "s": "ETH",
                    "i": interval,
                    "t": 0,
                    "T": width,
                    "o": "1",
                    "h": "2",
                    "l": "1",
                    "c": "2",
                    "v": "3",
                    "n": 0,
                },
            },
            separators=(",", ":"),
        )
        with pytest.raises(MarketDataError, match="interval boundary"):
            candle_from_websocket(legacy_raw, _evidence(legacy_raw))
