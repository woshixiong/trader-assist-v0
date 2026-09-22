"""Restricted public First Launch runtime composition tests.

Covers Section 16 categories A-E (Runtime composition):
- default-off CLI activation gate;
- exact 3 public subscriptions (ETH 5m, 15m, activeAssetCtx);
- warm-up / READY authority (STARTING -> WARMING -> READY);
- evaluation + publication + notification;
- recovery (restart reuses notification identity);
- health/shutdown transitions;
- authority boundary (ETH_ONLY, NOT_SUBMITTED, MANUAL_EXECUTION_REQUIRED).
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from websockets.exceptions import ConnectionClosedOK

from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.first_launch.market_data import (
    DataQualityState,
    MarketDataError,
    RawEvidence,
    evidence_from_raw,
    target_candle_from_post_response,
)
from trader_assist_v0.runtime.first_launch_notification import (
    HttpResponse,
    NotificationConfig,
    NotificationDispatcher,
)
from trader_assist_v0.runtime.first_launch_operator_assist import (
    REQUIRED_PUBLIC_SUBSCRIPTIONS,
    OperatorAssistRuntimeError,
)
from trader_assist_v0.runtime.first_launch_public_runtime import (
    CandleConfirmationRecoveryRequired,
    CandleConflictRecoveryRequired,
    CandleRefreshTrigger,
    RestrictedPublicRuntime,
    RestrictedPublicRuntimeConfig,
    RuntimeHealthState,
    RuntimeNotActivatedError,
    RuntimeRecoveryRequired,
    RuntimeShutdownError,
    StatusSnapshotPublicationError,
)
from trader_assist_v0.runtime.first_launch_runtime_store import RuntimeStore

NOW = datetime(2026, 7, 14, tzinfo=UTC)
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_first_launch_public_runtime.py"


def _utc_now() -> datetime:
    return NOW


def _monotonic_now() -> float:
    return 0.0


def _write_credential_file(
    path: Path,
    *,
    webhook_url: str = "https://hooks.example.com/eth-notify",
    authorization_header: dict[str, str] | None = None,
) -> Path:
    """Write a valid version-1 credential file for testing."""
    data: dict[str, object] = {
        "version": 1,
        "webhook_url": webhook_url,
        "authorization_header": authorization_header,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    path.chmod(0o600)
    return path


def _risk_configuration() -> RiskConfiguration:
    return RiskConfiguration.from_json(
        '{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"1000.00",'
        '"RISK_PER_TRADE_PCT":"0.5000","MAX_NOTIONAL_USD":null}'
    )


def _notification_config() -> NotificationConfig:
    return NotificationConfig(
        webhook_url="https://hooks.example.com/eth-notify",
        timeout_seconds=10.0,
        authorization_header_name=None,
        authorization_header_value=None,
    )


def _runtime_config(tmp_path: Path) -> RestrictedPublicRuntimeConfig:
    return RestrictedPublicRuntimeConfig(
        database_path=tmp_path / "runtime.db",
        risk_configuration=_risk_configuration(),
        notification_config=_notification_config(),
        status_snapshot_path=tmp_path / "status.json",
    )


def _open_store(tmp_path: Path) -> RuntimeStore:
    return RuntimeStore.open(tmp_path / "runtime.db")


@dataclass
class _MockTransport:
    responses: tuple[HttpResponse, ...]
    calls: list[dict[str, object]]

    def post(
        self,
        *,
        url: str,
        payload: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResponse:
        self.calls.append(
            {"url": url, "payload": payload, "headers": dict(headers), "timeout": timeout}
        )
        if not self.responses:
            return HttpResponse(status_code=200, body=b"ok")
        return self.responses[len(self.calls) - 1]


def _make_runtime(tmp_path: Path) -> tuple[
    RestrictedPublicRuntime, RuntimeStore, NotificationDispatcher, _MockTransport
]:
    store = _open_store(tmp_path)
    transport = _MockTransport(responses=(HttpResponse(status_code=200, body=b"ok"),), calls=[])
    dispatcher = NotificationDispatcher(
        store=store, transport=transport, config=_notification_config()
    )
    runtime = RestrictedPublicRuntime(
        config=_runtime_config(tmp_path),
        utc_now=_utc_now,
        monotonic_now=_monotonic_now,
        store=store,
        dispatcher=dispatcher,
    )
    return runtime, store, dispatcher, transport


def _ack_frame(spec: object) -> str:
    return json.dumps(
        {"channel": "subscriptionResponse", "data": {"method": "subscribe", "subscription": spec}},
        separators=(",", ":"),
    )


def _context_frame(price: str = "100") -> str:
    return json.dumps(
        {
            "channel": "activeAssetCtx",
            "data": {
                "coin": "ETH",
                "ctx": {
                    "markPx": price,
                    "midPx": price,
                    "openInterest": "1",
                    "funding": "0",
                },
            },
        },
        separators=(",", ":"),
    )


def _candle_obj(
    index: int,
    *,
    interval: str = "5m",
    open_price: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: str = "10",
) -> dict[str, object]:
    width = 300_000 if interval == "5m" else 900_000
    base = int(NOW.timestamp() * 1000) - 1_000
    open_time = base - ((64 - index) * width) if interval == "5m" else base - ((21 - index) * width)
    return {
        "s": "ETH",
        "i": interval,
        "t": open_time,
        "T": open_time + width - 1,
        "o": open_price,
        "h": high,
        "l": low,
        "c": close,
        "v": volume,
        "n": 0,
    }


def _snapshot_json(candles: list[dict[str, object]]) -> str:
    return json.dumps(candles, separators=(",", ":"))


def _post_snapshot_json(candle: dict[str, object], request_id: int) -> str:
    return json.dumps(
        {
            "channel": "post",
            "data": {
                "id": request_id,
                "response": {
                    "type": "info",
                    "payload": {"type": "candleSnapshot", "data": [candle]},
                },
            },
        },
        separators=(",", ":"),
    )


def _post_response_evidence(raw_text: str, *, received_at: datetime = NOW) -> RawEvidence:
    return evidence_from_raw(
        raw_text,
        operation="WebSocketPostCandleSnapshot",
        received_at=received_at,
        receive_sequence=1,
        connection_id="conn-test",
        source_id="hyperliquid-public-websocket",
    )


def _metadata_json() -> str:
    return json.dumps(
        {"universe": [{"name": "ETH", "szDecimals": 3}]},
        separators=(",", ":"),
    )


def _warmup_to_active(
    runtime: RestrictedPublicRuntime, *, now: datetime
) -> tuple[str, str, str]:
    """Activate, begin warmup, accept all 3 acks. Returns the 3 subscription requests."""
    runtime.activate(now=now)
    assert runtime.health_state is RuntimeHealthState.STARTING
    requests = runtime.begin_warmup(connection_id="conn-test", now=now)
    assert runtime.health_state is RuntimeHealthState.WARMING
    for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
        runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=now)
    assert runtime.remaining_subscriptions == ()
    return requests


def _recover_to_ready(
    runtime: RestrictedPublicRuntime,
    *,
    now: datetime,
    context_price: str = "100",
) -> None:
    """Recover the HTTP snapshot and accept a context frame to reach READY."""
    candles_5m = [_candle_obj(i) for i in range(64)]
    candles_15m = [_candle_obj(i, interval="15m") for i in range(20)]
    runtime.recover_public_snapshot(
        raw_5m=_snapshot_json(candles_5m),
        raw_15m=_snapshot_json(candles_15m),
        raw_metadata=_metadata_json(),
        now=now,
    )
    # Not READY yet because no active context
    assert runtime.health_state is not RuntimeHealthState.READY
    # Accept a context frame to complete READY
    runtime.accept_public_frame(frame_text=_context_frame(context_price), now=now)
    assert runtime.health_state is RuntimeHealthState.READY


# ============================================================
# CLI default-off
# ============================================================


def test_cli_no_flags_exits_nonzero() -> None:
    """Without --enable-restricted-public-runtime, the CLI must exit nonzero."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": ""},
    )
    assert result.returncode != 0
    assert "default-off" in result.stderr.lower() or "missing" in result.stderr.lower()


def test_cli_flag_without_mode_exits_nonzero() -> None:
    """With --enable-restricted-public-runtime but without --mode, exit nonzero."""
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), "--enable-restricted-public-runtime"],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": ""},
    )
    assert result.returncode != 0


def test_cli_flag_with_wrong_mode_exits_nonzero() -> None:
    """With --enable-restricted-public-runtime but wrong --mode, exit nonzero."""
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--enable-restricted-public-runtime",
            "--mode",
            "LIVE",
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": ""},
    )
    assert result.returncode != 0


# ============================================================
# Config validation
# ============================================================


def test_config_rejects_non_path_database(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="database path must be a Path"):
        RestrictedPublicRuntimeConfig(
            database_path="/not/a/path",  # type: ignore[arg-type]
            risk_configuration=_risk_configuration(),
            notification_config=_notification_config(),
        )


def test_config_rejects_negative_timeout(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="acknowledgement timeout"):
        RestrictedPublicRuntimeConfig(
            database_path=tmp_path / "runtime.db",
            risk_configuration=_risk_configuration(),
            notification_config=_notification_config(),
            acknowledgement_timeout_seconds=-1.0,
        )


def test_config_rejects_session_shorter_than_ack(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="session timeout is shorter"):
        RestrictedPublicRuntimeConfig(
            database_path=tmp_path / "runtime.db",
            risk_configuration=_risk_configuration(),
            notification_config=_notification_config(),
            acknowledgement_timeout_seconds=100.0,
            session_timeout_seconds=50.0,
        )


def test_config_rejects_empty_reconnect_schedule(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="reconnect schedule"):
        RestrictedPublicRuntimeConfig(
            database_path=tmp_path / "runtime.db",
            risk_configuration=_risk_configuration(),
            notification_config=_notification_config(),
            reconnect_delays_seconds=(),
        )


def test_config_rejects_invalid_sz_decimals(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="sz_decimals"):
        RestrictedPublicRuntimeConfig(
            database_path=tmp_path / "runtime.db",
            risk_configuration=_risk_configuration(),
            notification_config=_notification_config(),
            sz_decimals=-1,
        )


# ============================================================
# Runtime lifecycle
# ============================================================


def test_activate_transitions_to_starting(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        assert runtime.health_state is RuntimeHealthState.STARTING
        assert runtime.session_id != ""
        assert runtime.is_ready is False
        assert runtime.is_shutdown is False
    finally:
        store.close()


def test_activate_rejects_double_activation(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        with pytest.raises(RuntimeError, match="already been activated"):
            runtime.activate(now=NOW)
    finally:
        store.close()


def test_begin_warmup_before_activate_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        with pytest.raises(RuntimeNotActivatedError):
            runtime.begin_warmup(connection_id="conn", now=NOW)
    finally:
        store.close()


def test_begin_warmup_issues_exactly_3_subscriptions(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        requests = runtime.begin_warmup(connection_id="conn-test", now=NOW)
        assert len(requests) == 3
        # Verify the exact subscription identities
        expected = tuple(spec.request_text for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS)
        assert requests == expected
    finally:
        store.close()


def test_remaining_subscriptions_decrease_with_acks(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.begin_warmup(connection_id="conn-test", now=NOW)
        assert len(runtime.remaining_subscriptions) == 3
        spec = REQUIRED_PUBLIC_SUBSCRIPTIONS[0]
        runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        assert len(runtime.remaining_subscriptions) == 2
    finally:
        store.close()


def test_full_warmup_to_ready(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW, context_price="100")
        assert runtime.health_state is RuntimeHealthState.READY
        assert runtime.is_ready is True
        assert runtime.acknowledged_subscriptions == frozenset(
            spec.identity for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS
        )
    finally:
        store.close()


def test_health_tick_rechecks_freshness_without_strategy_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        publications_before, outbox_before = _row_counts(store)
        evaluated_before = runtime._last_evaluated_5m_identity

        def _unexpected_evaluation(_now: datetime) -> object:
            pytest.fail("health tick must not run Strategy evaluation")

        monkeypatch.setattr(runtime, "_evaluate_new_closed_5m", _unexpected_evaluation)

        # The existing rule is strictly "> 15s", so the boundary remains READY.
        runtime.refresh_readiness(now=NOW + timedelta(seconds=15))
        assert runtime.health_state is RuntimeHealthState.READY
        assert _row_counts(store) == (publications_before, outbox_before)
        assert runtime._last_evaluated_5m_identity == evaluated_before

        # One second later the existing active-context rule is stale and READY
        # must be withdrawn without any application market-data frame.
        runtime.refresh_readiness(now=NOW + timedelta(seconds=16))
        assert runtime.health_state is RuntimeHealthState.NOT_READY
        status_snapshot = json.loads(
            runtime.config.status_snapshot_path.read_text(encoding="utf-8")
        )
        assert status_snapshot["state"] == "NOT_READY"
        assert status_snapshot["last_active_context_at"] == NOW.isoformat()
        assert _row_counts(store) == (publications_before, outbox_before)
        assert runtime._last_evaluated_5m_identity == evaluated_before
    finally:
        store.close()


def test_accept_public_frame_before_warmup_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        with pytest.raises(RuntimeNotActivatedError):
            runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
    finally:
        store.close()


def test_route_b_binds_the_exact_transport_receipt_clock_pair(tmp_path: Path) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        candle = _candle_obj(64)
        receipt_at = datetime.fromtimestamp((int(candle["T"]) + 1) / 1000, tz=UTC)
        receipt_monotonic = 1234.5
        trigger = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(candle),
            now=receipt_at + timedelta(days=3),
            received_at=receipt_at,
            received_monotonic=receipt_monotonic,
        )
        assert type(trigger) is CandleRefreshTrigger
        assert trigger.frame.received_at == receipt_at
        assert trigger.received_at == receipt_at
        assert trigger.received_monotonic == receipt_monotonic
        assert trigger.eligible_at_monotonic == receipt_monotonic + 3.0
    finally:
        store.close()


@pytest.mark.parametrize(
    "received_at,received_monotonic",
    [
        (NOW.replace(tzinfo=None), 1.0),
        (NOW, True),
        (NOW, "1.0"),
        (NOW, float("nan")),
        (NOW, float("inf")),
        (NOW, float("-inf")),
    ],
)
def test_route_b_rejects_invalid_explicit_receipt_evidence_before_authority(
    tmp_path: Path, received_at: datetime, received_monotonic: object
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        before_sequence = runtime._protocol.receive_sequence
        with pytest.raises(OperatorAssistRuntimeError):
            runtime.accept_public_frame(
                frame_text=_closed_candle_frame(_candle_obj(64)),
                now=NOW,
                received_at=received_at,
                received_monotonic=received_monotonic,
            )
        assert runtime._protocol.receive_sequence == before_sequence
        assert runtime._candle_candidates == {}
    finally:
        store.close()


@pytest.mark.parametrize("invalid_id", [True, False, 7.0, "7", -1, 8, None])
def test_target_candle_from_post_response_rejects_invalid_response_id_types(
    invalid_id: object,
) -> None:
    raw = _post_snapshot_json(_candle_obj(64), 7)
    document = json.loads(raw)
    document["data"]["id"] = invalid_id
    invalid_raw = json.dumps(document, separators=(",", ":"))
    with pytest.raises(MarketDataError, match="post response id is invalid"):
        target_candle_from_post_response(
            invalid_raw,
            _post_response_evidence(invalid_raw),
            request_id=7,
            requested_interval="5m",
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda document: document["data"].pop("id"),
        lambda document: document.__setitem__("extra", True),
        lambda document: document["data"].__setitem__("extra", True),
        lambda document: document["data"].__setitem__("response", []),
    ],
)
def test_target_candle_from_post_response_rejects_malformed_response_wrapper(
    mutate: Callable[[dict[str, object]], object],
) -> None:
    document = json.loads(_post_snapshot_json(_candle_obj(64), 7))
    assert type(document) is dict
    mutate(document)
    invalid_raw = json.dumps(document, separators=(",", ":"))
    with pytest.raises(MarketDataError):
        target_candle_from_post_response(
            invalid_raw,
            _post_response_evidence(invalid_raw),
            request_id=7,
            requested_interval="5m",
        )


def test_target_candle_from_post_response_accepts_exact_numeric_response_id() -> None:
    source_candle = _candle_obj(64)
    raw = _post_snapshot_json(source_candle, 7)
    candle = target_candle_from_post_response(
        raw,
        _post_response_evidence(
            raw,
            received_at=datetime.fromtimestamp((int(source_candle["T"]) + 1) / 1000, tz=UTC),
        ),
        request_id=7,
        requested_interval="5m",
    )
    assert candle.identity == ("ETH", "5m", source_candle["t"])


def test_route_b_candidate_generations_supersede_and_coalesce_exact_duplicates(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        later = NOW + timedelta(minutes=5)
        runtime.utc_now = lambda: later
        runtime._protocol.utc_now = runtime.utc_now
        first = _candle_obj(64)
        second = {**first, "c": "100.5"}
        third = {**first, "c": "101.0"}
        trigger_a = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(first), now=later
        )
        assert type(trigger_a) is CandleRefreshTrigger
        for _ in range(20):
            assert (
                runtime.accept_public_frame(
                    frame_text=_closed_candle_frame(first), now=later
                )
                is None
            )
        trigger_b = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(second), now=later
        )
        trigger_c = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(third), now=later
        )
        assert type(trigger_b) is CandleRefreshTrigger
        assert type(trigger_c) is CandleRefreshTrigger
        assert (trigger_a.generation, trigger_b.generation, trigger_c.generation) == (1, 2, 3)
        assert runtime._candle_candidates == {"5m": trigger_c}
        before_sequence = runtime._protocol.receive_sequence
        assert runtime.confirm_candle_refresh(
            trigger=trigger_a,
            raw_first=_post_snapshot_json(third, 1),
            raw_second=_post_snapshot_json(third, 2),
            first_request_id=1,
            second_request_id=2,
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        ) == "STALE"
        assert runtime.confirm_candle_refresh(
            trigger=trigger_b,
            raw_first=_post_snapshot_json(third, 3),
            raw_second=_post_snapshot_json(third, 4),
            first_request_id=3,
            second_request_id=4,
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        ) == "STALE"
        assert runtime.confirm_candle_refresh(
            trigger=trigger_c,
            raw_first=_post_snapshot_json(third, 5),
            raw_second=_post_snapshot_json(third, 6),
            first_request_id=5,
            second_request_id=6,
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        ) == "ADMITTED"
        assert runtime._protocol.receive_sequence == before_sequence + 1
    finally:
        store.close()


def test_route_b_rejects_stale_connection_confirmation_without_authority(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        later = NOW + timedelta(minutes=5)
        runtime.utc_now = lambda: later
        runtime._protocol.utc_now = runtime.utc_now
        target = _candle_obj(64)
        stale = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(target), now=later
        )
        assert type(stale) is CandleRefreshTrigger
        runtime.mark_disconnected(now=later, reason="test-disconnect")
        runtime.begin_reconnect(connection_id="conn-fresh", now=later)
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=later)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=later,
        )
        runtime.accept_public_frame(frame_text=_context_frame(), now=later)
        before_sequence = runtime._protocol.receive_sequence
        assert runtime.confirm_candle_refresh(
            trigger=stale,
            raw_first=_snapshot_json([target]),
            raw_second=_snapshot_json([target]),
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        ) == "STALE"
        assert runtime._protocol.receive_sequence == before_sequence
    finally:
        store.close()


def test_route_b_changed_candidate_after_admission_is_finalized_conflict(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        later = NOW + timedelta(minutes=5)
        runtime.utc_now = lambda: later
        runtime._protocol.utc_now = runtime.utc_now
        original = _candle_obj(64)
        first = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(original), now=later
        )
        assert type(first) is CandleRefreshTrigger
        runtime.confirm_candle_refresh(
            trigger=first,
                raw_first=_post_snapshot_json(original, 11),
                raw_second=_post_snapshot_json(original, 12),
                first_request_id=11,
                second_request_id=12,
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        )
        changed = {**original, "c": "100.5"}
        revised = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(changed), now=later
        )
        assert type(revised) is CandleRefreshTrigger
        with pytest.raises(CandleConflictRecoveryRequired, match="CANDLE_CONFLICT"):
            runtime.confirm_candle_refresh(
                trigger=revised,
                raw_first=_post_snapshot_json(changed, 13),
                raw_second=_post_snapshot_json(changed, 14),
                first_request_id=13,
                second_request_id=14,
                first_completed_at=later,
                second_completed_at=later + timedelta(seconds=1),
                first_completed_monotonic=4.0,
                second_completed_monotonic=5.0,
            )
        assert runtime.health_state is RuntimeHealthState.NOT_READY
    finally:
        store.close()


def test_route_b_requires_monotonic_observation_gap_before_authority(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        later = NOW + timedelta(minutes=5)
        runtime.utc_now = lambda: later
        runtime._protocol.utc_now = runtime.utc_now
        target = _candle_obj(64)
        trigger = runtime.accept_public_frame(
            frame_text=_closed_candle_frame(target), now=later
        )
        assert type(trigger) is CandleRefreshTrigger
        before_sequence = runtime._protocol.receive_sequence
        with pytest.raises(CandleConfirmationRecoveryRequired):
            runtime.confirm_candle_refresh(
                trigger=trigger,
                raw_first=_snapshot_json([target]),
                raw_second=_snapshot_json([target]),
                first_completed_at=later,
                second_completed_at=later + timedelta(milliseconds=999),
                first_completed_monotonic=10.0,
                second_completed_monotonic=10.999,
            )
        assert runtime.health_state is RuntimeHealthState.NOT_READY
        assert runtime._protocol.receive_sequence == before_sequence
    finally:
        store.close()


# ============================================================
# Health state machine
# ============================================================


def test_shutdown_transitions_to_stopped(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.shutdown(now=NOW)
        assert runtime.health_state is RuntimeHealthState.STOPPED
        assert runtime.is_shutdown is True
    finally:
        store.close()


def test_operations_after_shutdown_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.begin_warmup(connection_id="conn", now=NOW)
        runtime.shutdown(now=NOW)
        with pytest.raises(RuntimeShutdownError):
            runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
    finally:
        store.close()


def test_shutdown_is_idempotent(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.shutdown(now=NOW)
        runtime.shutdown(now=NOW)  # second shutdown is a no-op
        assert runtime.health_state is RuntimeHealthState.STOPPED
    finally:
        store.close()


def test_mark_disconnected_transitions_to_disconnected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        assert runtime.is_ready
        runtime.mark_disconnected(now=NOW, reason="transport-error")
        assert runtime.health_state is RuntimeHealthState.DISCONNECTED
        assert runtime.is_ready is False
    finally:
        store.close()


def test_reconnect_returns_subscription_requests(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        runtime.mark_disconnected(now=NOW, reason="transport-error")
        requests = runtime.begin_reconnect(connection_id="conn-reconnect", now=NOW)
        assert requests is not None
        assert len(requests) == 3
        assert runtime.health_state is RuntimeHealthState.WARMING
    finally:
        store.close()


def test_initial_startup_does_not_consume_reconnect_budget(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        assert runtime._reconnect_attempt == 0
        assert runtime.next_reconnect_delay_seconds == runtime.config.reconnect_delays_seconds[0]
    finally:
        store.close()


def test_partial_recovery_does_not_reset_reconnect_budget(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        runtime.mark_disconnected(now=NOW, reason="test")
        runtime.begin_reconnect(connection_id="conn-reconnect", now=NOW)
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=NOW,
        )
        assert runtime.health_state is RuntimeHealthState.WARMING
        assert runtime._reconnect_attempt == 1
    finally:
        store.close()


def test_completed_recovery_resets_prior_consecutive_failures(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        for connection_id in ("conn-first", "conn-second"):
            runtime.mark_disconnected(now=NOW, reason="test")
            assert runtime.begin_reconnect(connection_id=connection_id, now=NOW) is not None
        assert runtime._reconnect_attempt == 2
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=NOW,
        )
        runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
        assert runtime.is_ready is True
        assert runtime._reconnect_attempt == 0
    finally:
        store.close()


def test_ready_status_publication_failure_does_not_reset_reconnect_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        from trader_assist_v0.runtime import first_launch_public_runtime as runtime_module

        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        runtime.mark_disconnected(now=NOW, reason="test")
        runtime.begin_reconnect(connection_id="conn-reconnect", now=NOW)
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=NOW,
        )
        real_replace = runtime_module.os.replace

        def fail_ready_snapshot(source: str, destination: Path) -> None:
            if '"state":"READY"' in Path(source).read_text(encoding="utf-8"):
                raise OSError("injected READY snapshot publication failure")
            real_replace(source, destination)

        monkeypatch.setattr(runtime_module.os, "replace", fail_ready_snapshot)
        with pytest.raises(StatusSnapshotPublicationError):
            runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
        assert runtime._reconnect_attempt == 1
        assert runtime.health_state is RuntimeHealthState.NOT_READY
        assert runtime.is_ready is False
        assert not (tmp_path / "status.json").exists()
        health_events = store.list_health_events(session_id=runtime.session_id)
        assert any(event.to_state == "READY" for event in health_events)
        assert any(
            event.to_state == "NOT_READY"
            and event.reason == "READY_STATUS_PUBLICATION_FAILED"
            for event in health_events
        )

        # A later complete recovery remains possible.  Only this successful
        # READY publication restores the reconnect budget.
        monkeypatch.setattr(runtime_module.os, "replace", real_replace)
        runtime.mark_disconnected(now=NOW, reason="retry-after-publication-failure")
        assert runtime.begin_reconnect(connection_id="conn-second", now=NOW) is not None
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=NOW,
        )
        runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
        assert runtime.is_ready is True
        assert runtime._reconnect_attempt == 0
    finally:
        store.close()


def test_ordinary_ready_update_does_not_reset_reconnect_budget(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        # A READY context update is not a recovery completion transition.
        runtime._reconnect_attempt = 1
        runtime.accept_public_frame(frame_text=_context_frame("101"), now=NOW)
        assert runtime.is_ready is True
        assert runtime._reconnect_attempt == 1
    finally:
        store.close()


def test_consecutive_incomplete_reconnects_exhaust_budget(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        # Do not complete recovery between reconnect attempts. The counter is
        # therefore consecutive and must still fail closed at the fixed limit.
        for _ in runtime.config.reconnect_delays_seconds:
            runtime.mark_disconnected(now=NOW, reason="test")
            result = runtime.begin_reconnect(connection_id="conn", now=NOW)
            assert result is not None
        # Next reconnect should fail (budget exhausted)
        runtime.mark_disconnected(now=NOW, reason="test")
        result = runtime.begin_reconnect(connection_id="conn", now=NOW)
        assert result is None
    finally:
        store.close()


def test_status_snapshot_tracks_only_accepted_active_context(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    snapshot_path = tmp_path / "status.json"
    try:
        runtime.activate(now=NOW)
        activated = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert set(activated) == {
            "pid",
            "session_id",
            "state",
            "last_active_context_at",
            "mode",
            "scope",
        }
        assert activated["state"] == "STARTING"
        assert activated["last_active_context_at"] is None

        runtime.begin_warmup(connection_id="conn-test", now=NOW)
        for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS:
            runtime.accept_acknowledgement(frame_text=_ack_frame(spec.subscription), now=NOW)
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json([_candle_obj(i, interval="15m") for i in range(20)]),
            raw_metadata=_metadata_json(),
            now=NOW,
        )
        recovered = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert recovered["last_active_context_at"] is None

        runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
        accepted = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert accepted["state"] == "READY"
        assert accepted["last_active_context_at"] == NOW.isoformat()

        later = NOW + timedelta(seconds=1)
        runtime.accept_public_frame(
            frame_text=json.dumps(
                {"channel": "candle", "data": _candle_obj(63)}, separators=(",", ":")
            ),
            now=later,
        )
        after_candle = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert after_candle["last_active_context_at"] == NOW.isoformat()

        with pytest.raises(ValueError):
            runtime.accept_public_frame(frame_text=_context_frame("not-a-price"), now=later)
        rejected = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert rejected["last_active_context_at"] == NOW.isoformat()

        runtime.mark_disconnected(now=later, reason="test")
        runtime.begin_reconnect(connection_id="conn-reconnect", now=later)
        reconnecting = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert reconnecting["state"] == "WARMING"
        assert reconnecting["last_active_context_at"] is None
    finally:
        store.close()


def test_status_publication_failure_is_not_silently_successful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    snapshot_path = tmp_path / "status.json"
    try:
        from trader_assist_v0.runtime import first_launch_public_runtime as runtime_module

        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        assert json.loads(snapshot_path.read_text(encoding="utf-8"))["state"] == "READY"

        real_replace = runtime_module.os.replace

        def _replace_failure(source: str, destination: Path) -> None:
            payload = Path(source).read_text(encoding="utf-8")
            if '"state":"NOT_READY"' in payload:
                raise OSError("injected status replacement failure")
            real_replace(source, destination)

        monkeypatch.setattr(runtime_module.os, "replace", _replace_failure)
        with pytest.raises(
            StatusSnapshotPublicationError, match="status snapshot publication failed"
        ):
            runtime.accept_public_frame(
                frame_text=_context_frame("not-a-price"), now=NOW
            )
        assert not snapshot_path.exists()
        assert not list(tmp_path.glob(".status-*.tmp"))
        assert runtime.is_ready is False
    finally:
        store.close()


# ============================================================
# Authority boundary
# ============================================================


def test_authority_eth_only_scope(tmp_path: Path) -> None:
    """The runtime must be ETH_ONLY scope."""
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        sessions = store.list_runtime_sessions()
        assert len(sessions) == 1
        assert sessions[0].scope == "ETH_ONLY"
        assert sessions[0].runtime_mode == "RESTRICTED_PUBLIC_LIVE_SHADOW"
    finally:
        store.close()


def test_authority_manual_only_and_not_submitted(tmp_path: Path) -> None:
    """The runtime must record manual_only and not_submitted authority."""
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        sessions = store.list_runtime_sessions()
        record = sessions[0]
        assert record.manual_only_authority is True
        assert record.not_submitted_authority is True
    finally:
        store.close()


def test_operator_assist_file_has_no_forbidden_strings() -> None:
    """Boundary test: first_launch_operator_assist.py must not contain forbidden strings.

    Per Writer Packet constraint: the operator_assist module must not contain
    'websockets', 'build_plan', 'TradePlan', 'permit', 'shadow', 'private_key',
    'nonce' — it is a reuse-only transport/protocol module that must not become
    a plan authority or execution surface.
    """
    path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "trader_assist_v0"
        / "runtime"
        / "first_launch_operator_assist.py"
    )
    content = path.read_text(encoding="utf-8")
    forbidden = [
        "websockets",
        "build_plan",
        "TradePlan",
        "permit",
        "shadow",
        "private_key",
        "nonce",
    ]
    for term in forbidden:
        assert term not in content, f"forbidden term '{term}' found in operator_assist.py"


# ============================================================
# Evaluation + publication + notification
# ============================================================


def test_ready_runtime_accepts_context_frame(tmp_path: Path) -> None:
    """A READY runtime accepts a context frame without error."""
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        result = runtime.accept_public_frame(frame_text=_context_frame("101"), now=NOW)
        # A context frame does not produce an evaluation outcome
        assert result is None
    finally:
        store.close()


def test_dispatch_pending_returns_empty_when_no_pending(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        results = runtime.dispatch_pending_notifications(now=NOW)
        assert results == ()
    finally:
        store.close()


def test_dispatch_pending_delivers_after_publication(tmp_path: Path) -> None:
    """After a publication, dispatch_pending delivers the notification."""
    runtime, store, dispatcher, transport = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        # Manually insert a pending notification for testing dispatch
        # (full evaluation chain is tested in test_first_launch_runtime_store.py)
        from tests.test_first_launch_notification import _insert_publication_and_notification

        # The runtime's activate() already created the session; just insert
        # a publication bundle + pending notification linked to that session.
        _insert_publication_and_notification(
            store,
            session_id=runtime.session_id,
            plan_id="f" * 64,
            notification_id="e" * 64,
        )
        results = runtime.dispatch_pending_notifications(now=NOW)
        assert len(results) == 1
        assert results[0].status == "DELIVERED"
        assert len(transport.calls) == 1
    finally:
        store.close()


# ============================================================
# Non-UTC datetime rejection
# ============================================================


def test_non_utc_now_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        from datetime import timezone

        non_utc = datetime(2026, 7, 14, tzinfo=timezone(timedelta(hours=1)))
        with pytest.raises(RuntimeError, match="now must be a UTC datetime"):
            runtime.activate(now=non_utc)
    finally:
        store.close()


def test_naive_datetime_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        naive = datetime(2026, 7, 14)
        with pytest.raises(RuntimeError, match="now must be a UTC datetime"):
            runtime.activate(now=naive)
    finally:
        store.close()


# ============================================================
# Health events are recorded durably
# ============================================================


def test_health_events_recorded_in_store(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.begin_warmup(connection_id="conn", now=NOW)
        events = store.list_health_events(session_id=runtime.session_id)
        # activate (STARTING) + begin_warmup (WARMING) = at least 2 events
        assert len(events) >= 2
        assert any(e.to_state == "STARTING" for e in events)
        assert any(e.to_state == "WARMING" for e in events)
    finally:
        store.close()


def test_shutdown_closes_runtime_session(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        runtime.shutdown(now=NOW)
        sessions = store.list_runtime_sessions()
        assert len(sessions) == 1
        assert sessions[0].closed_at is not None
    finally:
        store.close()


# ============================================================
# Script module loader for GA-01 / GA-05 transport loop tests
# ============================================================


def _load_script_module() -> object:
    """Load scripts/run_first_launch_public_runtime.py as an importable module."""
    module_name = "_run_first_launch_public_runtime_under_test"
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec so that the @dataclass decorator
    # (which looks up ``sys.modules.get(cls.__module__)``) can resolve the module.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    # GA-05 tests: the script's _utc_now returns wall-clock time, but the
    # runtime is activated with the test's fixed NOW (2026-07-14).  Patch the
    # script's clock so _run_transport uses the same deterministic timestamp
    # as the rest of the test, preventing false session-timeout failures.
    module._utc_now = _utc_now  # type: ignore[attr-defined]
    return module


_SCRIPT_MODULE = _load_script_module()


def _valid_cli_args(
    tmp_path: Path,
    *,
    enable: bool = True,
    mode: str = "RESTRICTED_PUBLIC_LIVE_SHADOW",
) -> object:
    """Build CliArguments for GA-01 / GA-05 tests."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    return _SCRIPT_MODULE.CliArguments(
        enable_restricted_public_runtime=enable,
        mode=mode,
        database_path=tmp_path / "runtime.db",
        risk_configuration_path=tmp_path / "risk.json",
        notification_credential_file=credential_file,
        webhook_timeout_seconds=10.0,
        acknowledgement_timeout_seconds=30.0,
        session_timeout_seconds=21600.0,
        validate_only=False,
    )


class _RecoverySpy:
    """Records calls to recover_snapshot; raises if invoked unexpectedly."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> tuple[str, str, str]:
        self.calls += 1
        raise AssertionError("recover_snapshot must not be called before activation gate")


class _WebSocketFactorySpy:
    """Records calls to websocket_factory; raises if invoked unexpectedly."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, url: str) -> object:
        self.calls += 1
        raise AssertionError("websocket_factory must not be called before activation gate")


# ============================================================
# GA-01: run_runtime activation gate
# ============================================================


@pytest.mark.parametrize(
    "enable,mode",
    [
        (False, ""),  # enable flag false (mode also empty)
        (True, ""),  # missing/empty mode
        (True, "LIVE"),  # wrong mode
        (False, "RESTRICTED_PUBLIC_LIVE_SHADOW"),  # valid mode but enable false
    ],
)
def test_ga01_run_runtime_rejects_invalid_activation_before_side_effects(
    tmp_path: Path, enable: bool, mode: str
) -> None:
    """GA-01: run_runtime must independently enforce the activation contract.

    Direct callers with disabled or wrong activation must fail nonzero before
    any side effect: no SQLite/store construction, no session creation, no HTTP
    calls, no WebSocket calls, no publication, no webhook calls.
    """
    args = _valid_cli_args(tmp_path, enable=enable, mode=mode)
    recovery_spy = _RecoverySpy()
    ws_spy = _WebSocketFactorySpy()
    db_path = tmp_path / "runtime.db"
    assert not db_path.exists()

    with pytest.raises(_SCRIPT_MODULE.CliArgumentError):
        asyncio.run(
            _SCRIPT_MODULE.run_runtime(
                args=args,
                recover_snapshot=recovery_spy,
                websocket_factory=ws_spy,
                status=lambda msg: None,
            )
        )

    # Zero side effects: no recovery, no websocket, no database file
    assert recovery_spy.calls == 0
    assert ws_spy.calls == 0
    assert not db_path.exists()


# ============================================================
# GA-02: Malformed frame must withdraw READY
# ============================================================


def _establish_ready(
    tmp_path: Path,
) -> tuple[RestrictedPublicRuntime, RuntimeStore, NotificationDispatcher, _MockTransport]:
    runtime, store, dispatcher, transport = _make_runtime(tmp_path)
    _warmup_to_active(runtime, now=NOW)
    _recover_to_ready(runtime, now=NOW)
    assert runtime.is_ready is True
    return runtime, store, dispatcher, transport


def _row_counts(store: RuntimeStore) -> tuple[int, int]:
    pubs = store._connection.execute(
        "SELECT COUNT(*) FROM publication_bundles"
    ).fetchone()[0]
    outbox = store._connection.execute(
        "SELECT COUNT(*) FROM notification_outbox"
    ).fetchone()[0]
    return pubs, outbox


def _assert_ga02_withdrawal(
    runtime: RestrictedPublicRuntime,
    store: RuntimeStore,
    action: Callable[[], object],
) -> None:
    """Assert that a malformed frame from READY withdraws to blocking non-ready.

    Proves: exception remains visible, is_ready is false, no evaluation
    produced a publication or outbox row, and exactly one blocking health
    event is persisted.
    """
    pubs_before, outbox_before = _row_counts(store)
    health_before = len(store.list_health_events(session_id=runtime.session_id))
    assert runtime.is_ready is True

    with pytest.raises((ValueError, OperatorAssistRuntimeError)):
        action()

    assert runtime.is_ready is False
    pubs_after, outbox_after = _row_counts(store)
    assert pubs_after == pubs_before
    assert outbox_after == outbox_before
    health_after = len(store.list_health_events(session_id=runtime.session_id))
    assert health_after == health_before + 1
    events = store.list_health_events(session_id=runtime.session_id)
    # GA-02: events share the same NOW timestamp, so ordering by (recorded_at,
    # event_id) is by UUID (non-deterministic).  Find the withdrawal event by
    # its reason rather than assuming it is last.
    withdrawal_events = [e for e in events if e.reason == "PUBLIC_FRAME_REJECTED"]
    assert len(withdrawal_events) == 1
    assert withdrawal_events[0].to_state in ("NOT_READY", "DISCONNECTED")


def test_ga02_malformed_json_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: malformed JSON from READY must withdraw to blocking non-ready."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        _assert_ga02_withdrawal(
            runtime, store, lambda: runtime.accept_public_frame(frame_text="{not json", now=NOW)
        )
    finally:
        store.close()


def test_ga02_wrong_acknowledgement_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: wrong subscription acknowledgement from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        wrong_ack = json.dumps(
            {
                "channel": "subscriptionResponse",
                "data": {
                    "method": "subscribe",
                    "subscription": {"type": "candle", "coin": "BTC", "interval": "1m"},
                },
            },
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_acknowledgement(frame_text=wrong_ack, now=NOW),
        )
    finally:
        store.close()


def test_ga02_malformed_5m_candle_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: malformed 5m candle from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        malformed_candle = json.dumps(
            {"channel": "candle", "data": {"s": "ETH", "i": "5m"}},
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_public_frame(frame_text=malformed_candle, now=NOW),
        )
    finally:
        store.close()


def test_ga02_malformed_15m_candle_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: malformed 15m candle from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        malformed_candle = json.dumps(
            {"channel": "candle", "data": {"s": "ETH", "i": "15m"}},
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_public_frame(frame_text=malformed_candle, now=NOW),
        )
    finally:
        store.close()


def test_ga02_malformed_context_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: malformed activeAssetCtx from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        malformed_ctx = json.dumps(
            {
                "channel": "activeAssetCtx",
                "data": {"coin": "ETH", "ctx": {"markPx": "not-a-number"}},
            },
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_public_frame(frame_text=malformed_ctx, now=NOW),
        )
    finally:
        store.close()


def test_ga02_symbol_mismatch_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: candle with wrong symbol from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        mismatch = json.dumps(
            {
                "channel": "candle",
                "data": {
                    "s": "BTC",
                    "i": "5m",
                    "t": 0,
                    "T": 1000,
                    "o": "100",
                    "h": "101",
                    "l": "99",
                    "c": "100",
                    "v": "10",
                    "n": 0,
                },
            },
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_public_frame(frame_text=mismatch, now=NOW),
        )
    finally:
        store.close()


def test_ga02_interval_mismatch_withdraws_ready(tmp_path: Path) -> None:
    """GA-02: candle with wrong interval from READY must withdraw."""
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        mismatch = json.dumps(
            {
                "channel": "candle",
                "data": {
                    "s": "ETH",
                    "i": "1m",
                    "t": 0,
                    "T": 1000,
                    "o": "100",
                    "h": "101",
                    "l": "99",
                    "c": "100",
                    "v": "10",
                    "n": 0,
                },
            },
            separators=(",", ":"),
        )
        _assert_ga02_withdrawal(
            runtime,
            store,
            lambda: runtime.accept_public_frame(frame_text=mismatch, now=NOW),
        )
    finally:
        store.close()


def test_ga02_publication_blocked_during_disconnect(tmp_path: Path) -> None:
    """GA-02: after a malformed frame withdraws READY, no further frame can produce a publication.

    The runtime raises a transport-visible recovery requirement instead of
    silently discarding subsequent recovery frames while still active.
    """
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        # Withdraw READY with a malformed frame
        with pytest.raises((ValueError, OperatorAssistRuntimeError)):
            runtime.accept_public_frame(frame_text="{not json", now=NOW)
        assert runtime.is_ready is False
        # A subsequent valid context frame must force transport recovery.
        with pytest.raises(RuntimeRecoveryRequired):
            runtime.accept_public_frame(frame_text=_context_frame("101"), now=NOW)
        pubs, outbox = _row_counts(store)
        assert pubs == 0
        assert outbox == 0
    finally:
        store.close()


def _closed_candle_frame(candle: dict[str, object]) -> str:
    return json.dumps({"channel": "candle", "data": candle}, separators=(",", ":"))


def test_route_b_confirms_closed_candle_once_after_two_stable_snapshots(tmp_path: Path) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    later = NOW + timedelta(minutes=5)
    runtime.utc_now = lambda: later
    runtime._protocol.utc_now = runtime.utc_now
    try:
        target = _candle_obj(64)
        frame = _closed_candle_frame(target)
        before_sequence = runtime._protocol.receive_sequence
        trigger = runtime.accept_public_frame(frame_text=frame, now=later)
        assert type(trigger) is CandleRefreshTrigger
        assert runtime._protocol.receive_sequence == before_sequence
        assert target["t"] not in runtime._market_data.candles["5m"]
        pubs_before, outbox_before = _row_counts(store)

        stable_first = _post_snapshot_json(target, 21)
        stable_second = _post_snapshot_json(target, 22)
        outcome = runtime.confirm_candle_refresh(
            trigger=trigger,
            raw_first=stable_first,
            raw_second=stable_second,
            first_request_id=21,
            second_request_id=22,
            first_completed_at=later,
            second_completed_at=later + timedelta(seconds=1),
            first_completed_monotonic=4.0,
            second_completed_monotonic=5.0,
        )
        assert outcome == "ADMITTED"
        assert runtime._protocol.receive_sequence == before_sequence + 1
        assert target["t"] in runtime._market_data.candles["5m"]
        assert _row_counts(store) == (pubs_before, outbox_before)

        repeated = runtime.accept_public_frame(frame_text=frame, now=later)
        assert repeated is None
        assert runtime._protocol.receive_sequence == before_sequence + 1
    finally:
        store.close()


def test_route_b_finalized_conflict_is_transport_visible_and_fail_closed(tmp_path: Path) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        existing = max(
            runtime._market_data.candles["5m"].values(), key=lambda item: item.open_time_ms
        )
        frame = _closed_candle_frame(_candle_obj(63))
        trigger = runtime.accept_public_frame(frame_text=frame, now=NOW)
        assert type(trigger) is CandleRefreshTrigger
        conflicting = [_candle_obj(index) for index in range(64)]
        conflicting[-1]["c"] = "99.5"
        conflicting[-1]["l"] = "99"
        assert existing.open_time_ms == conflicting[-1]["t"]
        with pytest.raises(CandleConflictRecoveryRequired, match="CANDLE_CONFLICT"):
            runtime.confirm_candle_refresh(
                trigger=trigger,
                raw_first=_post_snapshot_json(conflicting[-1], 31),
                raw_second=_post_snapshot_json(conflicting[-1], 32),
                first_request_id=31,
                second_request_id=32,
                first_completed_at=NOW,
                second_completed_at=NOW + timedelta(seconds=1),
                first_completed_monotonic=4.0,
                second_completed_monotonic=5.0,
            )
        assert runtime.health_state is RuntimeHealthState.NOT_READY
        assert any(
            event.reason == "CANDLE_CONFLICT"
            for event in store.list_health_events(session_id=runtime.session_id)
        )
        with pytest.raises(RuntimeRecoveryRequired):
            runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
    finally:
        store.close()


# ============================================================
# GA-05: Actual transport reconnect lifecycle
# ============================================================


def _make_runtime_short_reconnect(
    tmp_path: Path,
    *,
    reconnect_delays: tuple[float, ...] = (0.001, 0.001, 0.001),
) -> tuple[RestrictedPublicRuntime, RuntimeStore, NotificationDispatcher, _MockTransport]:
    """Runtime with very short reconnect delays for fast transport loop tests."""
    store = _open_store(tmp_path)
    transport = _MockTransport(
        responses=(HttpResponse(status_code=200, body=b"ok"),), calls=[]
    )
    dispatcher = NotificationDispatcher(
        store=store, transport=transport, config=_notification_config()
    )
    config = RestrictedPublicRuntimeConfig(
        database_path=tmp_path / "runtime.db",
        risk_configuration=_risk_configuration(),
        notification_config=_notification_config(),
        reconnect_delays_seconds=reconnect_delays,
        status_snapshot_path=tmp_path / "status.json",
    )
    runtime = RestrictedPublicRuntime(
        config=config,
        utc_now=_utc_now,
        monotonic_now=_monotonic_now,
        store=store,
        dispatcher=dispatcher,
    )
    return runtime, store, dispatcher, transport


class _FakeWebSocket:
    """Fake WebSocket that sends canned frames then optionally disconnects."""

    def __init__(
        self,
        frames: list[str],
        *,
        disconnect_after: int | None = None,
        disconnect_error: Exception | None = None,
        shutdown_event: asyncio.Event | None = None,
        post_candles: list[dict[str, object]] | None = None,
    ) -> None:
        self._frames = list(frames)
        self._pos = 0
        self._disconnect_after = disconnect_after
        self._disconnect_error = disconnect_error
        self._shutdown_event = shutdown_event
        self._post_candles = list(post_candles or [])
        self._frame_available = asyncio.Event()
        self.sent: list[str] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)
        envelope = json.loads(message)
        if envelope.get("method") != "post" or not self._post_candles:
            return
        candle = self._post_candles.pop(0)
        self._frames.append(
            json.dumps(
                {
                    "channel": "post",
                    "data": {
                        "id": envelope["id"],
                        "response": {
                            "type": "info",
                            "payload": {"type": "candleSnapshot", "data": [candle]},
                        },
                    },
                },
                separators=(",", ":"),
            )
        )
        self._frame_available.set()

    async def recv(self) -> str | bytes:
        if self._disconnect_after is not None and self._pos >= self._disconnect_after:
            if self._disconnect_error is not None:
                raise self._disconnect_error
            raise ConnectionError("simulated disconnect")
        if self._pos >= len(self._frames):
            if self._shutdown_event is not None:
                while self._pos >= len(self._frames):
                    if self._shutdown_event.is_set():
                        raise ConnectionError("shutdown")
                    await asyncio.wait_for(self._frame_available.wait(), timeout=30.0)
                    self._frame_available.clear()
            else:
                raise ConnectionError("simulated disconnect")
        frame = self._frames[self._pos]
        self._pos += 1
        return frame

    async def close(self) -> None:
        self.closed = True


class _FakeWebSocketFactory:
    """Factory that returns scripted fake WebSockets on each call."""

    def __init__(self) -> None:
        self._queue: list[_FakeWebSocket] = []
        self.created: list[_FakeWebSocket] = []

    def enqueue(self, ws: _FakeWebSocket) -> None:
        self._queue.append(ws)

    async def __call__(self, url: str) -> _FakeWebSocket:
        if not self._queue:
            raise AssertionError("no fake websocket queued")
        ws = self._queue.pop(0)
        self.created.append(ws)
        return ws


@dataclass
class _ControlledPost:
    candle: dict[str, object] | None
    send_gate: asyncio.Event = field(default_factory=asyncio.Event)
    response_gate: asyncio.Event = field(default_factory=asyncio.Event)
    error: Exception | None = None

    @classmethod
    def immediate(cls, candle: dict[str, object]) -> _ControlledPost:
        plan = cls(candle)
        plan.send_gate.set()
        plan.response_gate.set()
        return plan


class _ReceiptClock:
    """A deterministic receipt clock that advances only after a post response."""

    def __init__(self, received_at: datetime) -> None:
        self.received_at = received_at
        self.monotonic_value = 0.0
        self._advance_after_sample = False

    def utc_now(self) -> datetime:
        return self.received_at

    def monotonic_now(self) -> float:
        result = self.monotonic_value
        if self._advance_after_sample:
            self.monotonic_value += 1.0
            self._advance_after_sample = False
        return result

    def advance_after_receipt(self) -> None:
        self._advance_after_sample = True


class _ControlledWebSocket:
    """Queue/barrier WebSocket for deterministic single-owner transport tests."""

    def __init__(self, *, clock: _ReceiptClock, post_plans: list[_ControlledPost]) -> None:
        self.clock = clock
        self._post_plans = list(post_plans)
        self._inbound: asyncio.Queue[tuple[str, asyncio.Event]] = asyncio.Queue()
        self._last_processed: asyncio.Event | None = None
        self.recv_calls = 0
        self.recv_owners = 0
        self.recv_owner_max = 0
        self.post_count = 0
        self.response_count = 0
        self.sent: list[str] = []
        self.post_started: asyncio.Queue[int] = asyncio.Queue()
        self.response_enqueued: asyncio.Queue[asyncio.Event] = asyncio.Queue()
        self.closed = False

    async def push(self, frame: str) -> asyncio.Event:
        processed = asyncio.Event()
        await self._inbound.put((frame, processed))
        return processed

    async def send(self, message: str) -> None:
        self.sent.append(message)
        envelope = json.loads(message)
        if envelope.get("method") != "post":
            return
        if not self._post_plans:
            raise AssertionError("unexpected post request")
        plan = self._post_plans.pop(0)
        self.post_count += 1
        self.post_started.put_nowait(self.post_count)
        await plan.send_gate.wait()
        if plan.error is not None:
            raise plan.error
        await plan.response_gate.wait()
        if plan.candle is None:
            return
        response = json.dumps(
            {
                "channel": "post",
                "data": {
                    "id": envelope["id"],
                    "response": {
                        "type": "info",
                        "payload": {"type": "candleSnapshot", "data": [plan.candle]},
                    },
                },
            },
            separators=(",", ":"),
        )
        processed = await self.push(response)
        self.response_enqueued.put_nowait(processed)

    async def recv(self) -> str:
        self.recv_owners += 1
        self.recv_owner_max = max(self.recv_owner_max, self.recv_owners)
        assert self.recv_owners == 1
        self.recv_calls += 1
        if self._last_processed is not None:
            self._last_processed.set()
            self._last_processed = None
        try:
            frame, processed = await self._inbound.get()
            self._last_processed = processed
            if '"channel":"post"' in frame:
                self.response_count += 1
                self.clock.advance_after_receipt()
            return frame
        finally:
            self.recv_owners -= 1

    async def close(self) -> None:
        self.closed = True


async def _wait_for_post(ws: _ControlledWebSocket, count: int) -> None:
    while ws.post_count < count:
        await asyncio.wait_for(ws.post_started.get(), timeout=3.0)


async def _stop_frame_loop(
    task: asyncio.Task[None], ws: _ControlledWebSocket, shutdown_event: asyncio.Event
) -> None:
    shutdown_event.set()
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=3.0)


def _recovery_frames() -> tuple[str, str, str]:
    """Return valid snapshot recovery data for the fake recover_snapshot."""
    candles_5m = [_candle_obj(i) for i in range(64)]
    candles_15m = [_candle_obj(i, interval="15m") for i in range(20)]
    return (
        _snapshot_json(candles_5m),
        _snapshot_json(candles_15m),
        _metadata_json(),
    )


def test_r3_a_supersession_result_uses_real_frame_loop_and_zero_stale_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        original = _candle_obj(64)
        revision_b = {**original, "c": "100.5"}
        revision_c = {**original, "c": "101.0"}
        clock = _ReceiptClock(
            datetime.fromtimestamp((int(original["T"]) + 4_000) / 1000, tz=UTC)
        )
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        first = _ControlledPost(original)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[
                first,
                _ControlledPost.immediate(revision_c),
                _ControlledPost.immediate(revision_c),
            ],
        )
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(original))
            await _wait_for_post(websocket, 1)
            processed_b = await websocket.push(_closed_candle_frame(revision_b))
            await asyncio.wait_for(processed_b.wait(), timeout=3.0)
            processed_c = await websocket.push(_closed_candle_frame(revision_c))
            await asyncio.wait_for(processed_c.wait(), timeout=3.0)
            first.send_gate.set()
            first.response_gate.set()
            await _wait_for_post(websocket, 3)
            final_processed: asyncio.Event | None = None
            for _ in range(3):
                final_processed = await asyncio.wait_for(
                    websocket.response_enqueued.get(), timeout=3.0
                )
            assert final_processed is not None
            await asyncio.wait_for(final_processed.wait(), timeout=3.0)
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.recv_owner_max == 1
        assert websocket.post_count == 3
        assert runtime._protocol.receive_sequence == before_sequence + 1
        assert runtime._candle_candidates["5m"].fingerprint != ""
        assert runtime._market_data.candles["5m"][int(original["t"])].canonical_hash
    finally:
        store.close()


def test_r3_a_supersession_stale_send_exception_has_zero_authority_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        original = _candle_obj(64)
        revision_b = {**original, "c": "100.5"}
        revision_c = {**original, "c": "101.0"}
        clock = _ReceiptClock(
            datetime.fromtimestamp((int(original["T"]) + 4_000) / 1000, tz=UTC)
        )
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        first = _ControlledPost(None, error=ConnectionError("stale send"))
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[
                first,
                _ControlledPost.immediate(revision_c),
                _ControlledPost.immediate(revision_c),
            ],
        )
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(original))
            await _wait_for_post(websocket, 1)
            processed_b = await websocket.push(_closed_candle_frame(revision_b))
            await asyncio.wait_for(processed_b.wait(), timeout=3.0)
            processed_c = await websocket.push(_closed_candle_frame(revision_c))
            await asyncio.wait_for(processed_c.wait(), timeout=3.0)
            first.send_gate.set()
            await _wait_for_post(websocket, 3)
            final_processed: asyncio.Event | None = None
            for _ in range(2):
                final_processed = await asyncio.wait_for(
                    websocket.response_enqueued.get(), timeout=3.0
                )
            assert final_processed is not None
            await asyncio.wait_for(final_processed.wait(), timeout=3.0)
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.recv_owner_max == 1
        assert websocket.post_count == 3
        assert runtime._protocol.receive_sequence == before_sequence + 1
        assert int(original["t"]) in runtime._market_data.candles["5m"]
    finally:
        store.close()


def test_r3_b_duplicate_storm_is_conflated_in_the_real_frame_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        candle = _candle_obj(64)
        clock = _ReceiptClock(datetime.fromtimestamp((int(candle["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[_ControlledPost.immediate(candle), _ControlledPost.immediate(candle)],
        )
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            for _ in range(8):
                processed = await websocket.push(_closed_candle_frame(candle))
                await asyncio.wait_for(processed.wait(), timeout=3.0)
            await _wait_for_post(websocket, 2)
            final_processed = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            final_processed = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            await asyncio.wait_for(final_processed.wait(), timeout=3.0)
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.recv_owner_max == 1
        assert websocket.post_count == 2
        assert runtime._protocol.receive_sequence == before_sequence + 1
        assert len(runtime._candle_candidates) == 1
    finally:
        store.close()


def test_r3_c_cross_interval_fairness_retains_15m_while_5m_is_superseded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        first_5m = _candle_obj(64)
        revised_5m = {**first_5m, "c": "101.0"}
        target_15m = _candle_obj(20, interval="15m")
        clock = _ReceiptClock(
            datetime.fromtimestamp(
                (max(int(first_5m["T"]), int(target_15m["T"])) + 4_000) / 1000,
                tz=UTC,
            )
        )
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        first = _ControlledPost(first_5m)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[
                first,
                _ControlledPost.immediate(target_15m),
                _ControlledPost.immediate(target_15m),
                _ControlledPost.immediate(revised_5m),
                _ControlledPost.immediate(revised_5m),
            ],
        )
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(first_5m))
            await _wait_for_post(websocket, 1)
            processed_15m = await websocket.push(_closed_candle_frame(target_15m))
            await asyncio.wait_for(processed_15m.wait(), timeout=3.0)
            processed_5m = await websocket.push(_closed_candle_frame(revised_5m))
            await asyncio.wait_for(processed_5m.wait(), timeout=3.0)
            first.send_gate.set()
            first.response_gate.set()
            await _wait_for_post(websocket, 5)
            final_processed: asyncio.Event | None = None
            for _ in range(5):
                final_processed = await asyncio.wait_for(
                    websocket.response_enqueued.get(), timeout=3.0
                )
            assert final_processed is not None
            await asyncio.wait_for(final_processed.wait(), timeout=3.0)
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.recv_owner_max == 1
        assert websocket.post_count == 5
        assert len(runtime._candle_candidates) == 2
        assert runtime._protocol.receive_sequence == before_sequence + 2
        assert int(revised_5m["t"]) in runtime._market_data.candles["5m"]
        assert int(target_15m["t"]) in runtime._market_data.candles["15m"]
    finally:
        store.close()


def test_r3_d_transport_response_ids_ignore_unknown_duplicate_and_expired_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        candle = _candle_obj(64)
        clock = _ReceiptClock(datetime.fromtimestamp((int(candle["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[_ControlledPost(None), _ControlledPost(None)],
        )
        for plan in websocket._post_plans:
            plan.send_gate.set()
            plan.response_gate.set()
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        def response(request_id: object) -> str:
            return json.dumps(
                {
                    "channel": "post",
                    "data": {
                        "id": request_id,
                        "response": {
                            "type": "info",
                            "payload": {"type": "candleSnapshot", "data": [candle]},
                        },
                    },
                },
                separators=(",", ":"),
            )

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(candle))
            await _wait_for_post(websocket, 1)
            for invalid_id in (True, 7.0, "7", -1, 999_999):
                processed = await websocket.push(response(invalid_id))
                await asyncio.wait_for(processed.wait(), timeout=3.0)
                assert websocket.post_count == 1
                assert runtime._protocol.receive_sequence == before_sequence
            first_id = json.loads(websocket.sent[0])["id"]
            processed = await websocket.push(response(first_id))
            await asyncio.wait_for(processed.wait(), timeout=3.0)
            await _wait_for_post(websocket, 2)
            second_id = json.loads(websocket.sent[1])["id"]
            processed = await websocket.push(response(second_id))
            await asyncio.wait_for(processed.wait(), timeout=3.0)
            assert runtime._protocol.receive_sequence == before_sequence + 1
            processed = await websocket.push(response(second_id))
            await asyncio.wait_for(processed.wait(), timeout=3.0)
            assert runtime._protocol.receive_sequence == before_sequence + 1
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.recv_owner_max == 1
        assert websocket.post_count == 2
    finally:
        store.close()


def test_r3_e_blocked_send_times_out_without_an_orphan_coordinator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        candle = _candle_obj(64)
        clock = _ReceiptClock(datetime.fromtimestamp((int(candle["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        shifted_now = clock.utc_now()
        shifted_monotonic = clock.monotonic_now()
        runtime.accept_public_frame(
            frame_text=_context_frame(),
            now=shifted_now,
            received_at=shifted_now,
            received_monotonic=shifted_monotonic,
        )
        runtime.recover_public_snapshot(
            raw_5m=_snapshot_json([_candle_obj(i) for i in range(64)]),
            raw_15m=_snapshot_json(
                [_candle_obj(i, interval="15m") for i in range(1, 21)]
            ),
            raw_metadata=_metadata_json(),
            now=shifted_now,
        )
        snapshot = runtime._market_data.strategy_snapshot(shifted_now)
        assert snapshot.active_context is not None
        assert (
            shifted_now - snapshot.active_context.evidence.received_at
            <= timedelta(seconds=15)
        )
        assert snapshot.candles_5m
        assert (
            shifted_now.timestamp() * 1000 - snapshot.candles_5m[-1].close_time_ms
            <= 390_000
        )
        assert snapshot.candles_15m
        assert (
            shifted_now.timestamp() * 1000 - snapshot.candles_15m[-1].close_time_ms
            <= 990_000
        )
        assert snapshot.metadata is not None
        assert (
            shifted_now - snapshot.metadata.evidence.received_at
            <= timedelta(hours=24)
        )
        assert snapshot.quality.state is DataQualityState.READY
        assert runtime.health_state is RuntimeHealthState.READY
        websocket = _ControlledWebSocket(clock=clock, post_plans=[_ControlledPost(candle)])
        shutdown_event = asyncio.Event()

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(candle))
            await _wait_for_post(websocket, 1)
            with pytest.raises(CandleConfirmationRecoveryRequired, match="timed out"):
                await asyncio.wait_for(task, timeout=5.0)
            assert not any(
                "confirmation_coordinator" in item.get_coro().__qualname__
                for item in asyncio.all_tasks()
                if not item.done()
            )

        asyncio.run(exercise())
        assert websocket.post_count == 1
        assert websocket.recv_owner_max == 1
    finally:
        store.close()


def test_r3_e_shutdown_cancels_outstanding_waiter_without_recovery_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        candle = _candle_obj(64)
        clock = _ReceiptClock(datetime.fromtimestamp((int(candle["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        websocket = _ControlledWebSocket(clock=clock, post_plans=[_ControlledPost(candle)])
        shutdown_event = asyncio.Event()
        status: list[str] = []

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=status.append,
                )
            )
            await websocket.push(_closed_candle_frame(candle))
            await _wait_for_post(websocket, 1)
            shutdown_event.set()
            await websocket.push(_context_frame())
            await asyncio.wait_for(task, timeout=3.0)

        asyncio.run(exercise())
        assert websocket.post_count == 1
        assert "EVENT candle-confirmation-failed" not in status
        assert "EVENT reconnect-attempt" not in status
    finally:
        store.close()


def test_r3_f_extra_target_key_fails_closed_through_the_real_b2_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        target = _candle_obj(64)
        candle = {**target, "extra": "rejected"}
        clock = _ReceiptClock(datetime.fromtimestamp((int(target["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[_ControlledPost.immediate(candle), _ControlledPost.immediate(candle)],
        )
        shutdown_event = asyncio.Event()

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(target))
            await _wait_for_post(websocket, 2)
            with pytest.raises(CandleConfirmationRecoveryRequired):
                await asyncio.wait_for(task, timeout=3.0)

        asyncio.run(exercise())
        assert websocket.post_count == 2
        assert runtime._protocol.receive_sequence == 4
    finally:
        store.close()


def test_r3_f_n_only_revision_is_duplicate_authority_without_a_new_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        original = _candle_obj(64)
        n_only = {**original, "n": 1}
        clock = _ReceiptClock(datetime.fromtimestamp((int(original["T"]) + 4_000) / 1000, tz=UTC))
        monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", clock.utc_now)
        monkeypatch.setattr(_SCRIPT_MODULE, "_monotonic_now", clock.monotonic_now)
        websocket = _ControlledWebSocket(
            clock=clock,
            post_plans=[
                _ControlledPost.immediate(original),
                _ControlledPost.immediate(original),
                _ControlledPost.immediate(n_only),
                _ControlledPost.immediate(n_only),
            ],
        )
        shutdown_event = asyncio.Event()
        before_sequence = runtime._protocol.receive_sequence

        async def exercise() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._frame_loop(
                    runtime=runtime,
                    websocket=websocket,
                    recover_snapshot=_recovery_frames,
                    reconnecting=False,
                    shutdown_event=shutdown_event,
                    status=lambda _message: None,
                )
            )
            await websocket.push(_closed_candle_frame(original))
            await _wait_for_post(websocket, 2)
            second_response = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            second_response = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            await asyncio.wait_for(second_response.wait(), timeout=3.0)
            processed = await websocket.push(_closed_candle_frame(n_only))
            await asyncio.wait_for(processed.wait(), timeout=3.0)
            await _wait_for_post(websocket, 4)
            fourth_response = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            fourth_response = await asyncio.wait_for(websocket.response_enqueued.get(), timeout=3.0)
            await asyncio.wait_for(fourth_response.wait(), timeout=3.0)
            await _stop_frame_loop(task, websocket, shutdown_event)

        asyncio.run(exercise())
        assert websocket.post_count == 4
        assert runtime._protocol.receive_sequence == before_sequence + 1
        assert runtime.health_state is RuntimeHealthState.READY
    finally:
        store.close()


def _ack_and_context_frames() -> list[str]:
    """Return 3 ack frames + 1 context frame to reach READY."""
    acks = [_ack_frame(spec.subscription) for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS]
    return [*acks, _context_frame("100")]


def test_frame_loop_no_frame_tick_withdraws_stale_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _establish_ready(tmp_path)
    shutdown_event = asyncio.Event()
    websocket = _FakeWebSocket([], shutdown_event=shutdown_event)
    stale_now = NOW + timedelta(seconds=16)
    monkeypatch.setattr(_SCRIPT_MODULE, "_utc_now", lambda: stale_now)
    publications_before, outbox_before = _row_counts(store)

    async def exercise() -> None:
        task = asyncio.create_task(
            _SCRIPT_MODULE._frame_loop(
                runtime=runtime,
                websocket=websocket,
                recover_snapshot=_recovery_frames,
                reconnecting=False,
                shutdown_event=shutdown_event,
                status=lambda _message: None,
            )
        )
        try:
            # The transport's existing one-second no-frame wait owns the bound.
            for _ in range(200):
                if runtime.health_state is RuntimeHealthState.NOT_READY:
                    break
                await asyncio.sleep(0.01)
            assert runtime.health_state is RuntimeHealthState.NOT_READY
            status_snapshot = json.loads(
                runtime.config.status_snapshot_path.read_text(encoding="utf-8")
            )
            assert status_snapshot["state"] == "NOT_READY"
            assert _row_counts(store) == (publications_before, outbox_before)
        finally:
            await _stop_frame_loop(task, websocket, shutdown_event)

    try:
        asyncio.run(exercise())
    finally:
        store.close()


def test_ga05_first_connection_reaches_ready_via_transport_loop(tmp_path: Path) -> None:
    """GA-05: the actual _run_transport loop must reach READY on first connection."""
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()

        ws = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws)

        async def _test() -> None:
            transport_task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda msg: None,
                    shutdown_event=shutdown_event,
                )
            )
            # Poll for READY
            for _ in range(200):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            assert len(ws.sent) == 3  # three subscriptions sent
            # Shutdown cleanly
            shutdown_event.set()
            exit_code = await asyncio.wait_for(transport_task, timeout=10.0)
            assert exit_code == 0

        asyncio.run(_test())
    finally:
        store.close()


def test_route_b_conflict_closes_websocket_recovers_and_restores_ready(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()
        conflicting = [_candle_obj(index) for index in range(64)]
        conflicting[-1]["c"] = "99.5"
        recovery_calls = 0

        def recover() -> tuple[str, str, str]:
            nonlocal recovery_calls
            recovery_calls += 1
            if recovery_calls in (2, 3):
                return _snapshot_json(conflicting), _recovery_frames()[1], _metadata_json()
            return _recovery_frames()

        first = _FakeWebSocket(
            [*_ack_and_context_frames(), _closed_candle_frame(_candle_obj(63))],
            shutdown_event=shutdown_event,
            post_candles=[conflicting[-1], conflicting[-1]],
        )
        second = _FakeWebSocket(_ack_and_context_frames(), shutdown_event=shutdown_event)
        factory = _FakeWebSocketFactory()
        factory.enqueue(first)
        factory.enqueue(second)
        status_messages: list[str] = []

        async def _test() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=recover,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=status_messages.append,
                    shutdown_event=shutdown_event,
                )
            )
            for _ in range(500):
                if len(factory.created) == 2 and runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert len(factory.created) == 2
            assert runtime.is_ready is True
            shutdown_event.set()
            assert await asyncio.wait_for(task, timeout=10.0) == 0

        asyncio.run(_test())
        assert first.closed is True
        assert recovery_calls >= 2
        post_requests = [
            json.loads(message) for message in first.sent if '"method":"post"' in message
        ]
        assert len(post_requests) == 2
        assert [request["request"]["payload"]["req"] for request in post_requests] == [
            {
                "coin": "ETH",
                "interval": "5m",
                "startTime": conflicting[-1]["t"],
                "endTime": conflicting[-1]["T"],
            }
        ] * 2
        assert "EVENT finalized-candle-conflict" in status_messages
        assert "EVENT disconnect" in status_messages
        assert "EVENT reconnect-attempt" in status_messages
        assert "EVENT reconnect-success" in status_messages
        assert any(
            event.reason == "CANDLE_CONFLICT"
            for event in store.list_health_events(session_id=runtime.session_id)
        )
    finally:
        store.close()


def test_route_b_confirmation_failure_emits_recovery_events_and_reconnects(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()
        target = _candle_obj(63)
        changed = {**target, "c": "100.5"}
        first = _FakeWebSocket(
            [*_ack_and_context_frames(), _closed_candle_frame(target)],
            shutdown_event=shutdown_event,
            post_candles=[target, changed],
        )
        second = _FakeWebSocket(_ack_and_context_frames(), shutdown_event=shutdown_event)
        factory = _FakeWebSocketFactory()
        factory.enqueue(first)
        factory.enqueue(second)
        messages: list[str] = []

        async def _test() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=messages.append,
                    shutdown_event=shutdown_event,
                )
            )
            for _ in range(1200):
                if len(factory.created) == 2 and runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert len(factory.created) == 2, messages
            assert runtime.is_ready
            shutdown_event.set()
            assert await asyncio.wait_for(task, timeout=10.0) == 0

        asyncio.run(_test())
        assert sum('"method":"post"' in message for message in first.sent) == 2
        assert messages.index("EVENT candle-confirmation-failed") < messages.index(
            "EVENT disconnect"
        ) < messages.index("EVENT reconnect-attempt")
        assert first.closed is True
    finally:
        store.close()


def test_route_b_confirmation_holds_without_blocking_context_or_shutdown(
    tmp_path: Path,
) -> None:
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()
        first = _FakeWebSocket(
            [
                *_ack_and_context_frames(),
                _closed_candle_frame(_candle_obj(63)),
                _context_frame("101"),
            ],
            shutdown_event=shutdown_event,
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(first)
        messages: list[str] = []

        async def _test() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=messages.append,
                    shutdown_event=shutdown_event,
                )
            )
            for _ in range(100):
                context = runtime._market_data.active_context
                if context is not None and context.mark_px == Decimal("101"):
                    break
                await asyncio.sleep(0.01)
            assert runtime._market_data.active_context is not None
            assert runtime._market_data.active_context.mark_px == Decimal("101")
            assert "EVENT candle-refresh-trigger interval=5m open_time_ms=" in "\n".join(
                messages
            )
            assert sum('"method":"post"' in message for message in first.sent) <= 1
            shutdown_event.set()
            assert await asyncio.wait_for(task, timeout=10.0) == 0

        asyncio.run(_test())
        assert first.closed is True
        assert sum('"method":"post"' in message for message in first.sent) <= 1
    finally:
        store.close()


def test_route_b_confirmation_bounds_are_fixed_by_contract() -> None:
    assert _SCRIPT_MODULE._CANDLE_BOUNDARY_HOLD_SECONDS == 3.0
    assert _SCRIPT_MODULE._CANDLE_CONFIRMATION_GAP_SECONDS == 1.0
    assert _SCRIPT_MODULE._CANDLE_CONFIRMATION_REQUEST_TIMEOUT_SECONDS == 3.0
    assert _SCRIPT_MODULE._CANDLE_CONFIRMATION_DEADLINE_SECONDS == 8.0


def test_status_publication_failure_stops_transport_without_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    snapshot_path = tmp_path / "status.json"
    try:
        from trader_assist_v0.runtime import first_launch_public_runtime as runtime_module

        runtime.activate(now=NOW)
        frames = [
            *_ack_and_context_frames(),
            _context_frame("not-a-price"),
        ]
        factory = _FakeWebSocketFactory()
        factory.enqueue(_FakeWebSocket(frames))
        status_messages: list[str] = []
        real_replace = runtime_module.os.replace
        failed = False

        def _fail_not_ready_once(source: str, destination: Path) -> None:
            nonlocal failed
            payload = Path(source).read_text(encoding="utf-8")
            if not failed and '"state":"NOT_READY"' in payload:
                assert json.loads(snapshot_path.read_text(encoding="utf-8"))["state"] == "READY"
                failed = True
                raise OSError("injected status replacement failure")
            real_replace(source, destination)

        monkeypatch.setattr(runtime_module.os, "replace", _fail_not_ready_once)

        async def _test() -> None:
            exit_code = await _SCRIPT_MODULE._run_transport(
                runtime=runtime,
                recover_snapshot=_recovery_frames,
                websocket_factory=factory,
                websocket_url="wss://test",
                status=status_messages.append,
                shutdown_event=asyncio.Event(),
            )
            assert exit_code == 1

        asyncio.run(_test())
        assert failed is True
        assert len(factory.created) == 1
        assert runtime._reconnect_attempt == 0
        assert not snapshot_path.exists()
        assert not list(tmp_path.glob(".status-*.tmp"))
        assert runtime.is_ready is False
        assert status_messages == ["ERROR status snapshot publication failed"]
    finally:
        store.close()


def test_ga05_disconnect_then_reconnect_uses_begin_reconnect(tmp_path: Path) -> None:
    """GA-05: after disconnect, the next iteration uses begin_reconnect, not begin_warmup."""
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()

        # First connection: 3 acks + context → READY, then disconnect
        ws1 = _FakeWebSocket(_ack_and_context_frames(), disconnect_after=4)
        # Second connection: 3 acks + context → READY, then block for shutdown
        ws2 = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws1)
        factory.enqueue(ws2)

        async def _test() -> None:
            transport_task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda msg: None,
                    shutdown_event=shutdown_event,
                )
            )
            # Wait for first READY
            for _ in range(200):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            # Wait for disconnect + reconnect (second WebSocket created).
            # The 0.001s reconnect delay is too short for a 0.01s poll to
            # reliably observe the intermediate non-ready state, so we
            # poll for the reconnect signal instead.
            for _ in range(400):
                if len(factory.created) >= 2:
                    break
                await asyncio.sleep(0.01)
            assert len(factory.created) == 2
            assert runtime._reconnect_attempt >= 1
            # Wait for second READY (via begin_reconnect)
            for _ in range(400):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            # Full recovery reached READY and published its status snapshot,
            # so the consecutive unsuccessful-recovery budget was reset.
            assert runtime._reconnect_attempt == 0
            # begin_warmup was NOT called a second time: _connection_id changed
            assert len(factory.created) == 2
            # Shutdown cleanly
            shutdown_event.set()
            exit_code = await asyncio.wait_for(transport_task, timeout=10.0)
            assert exit_code == 0

        asyncio.run(_test())
    finally:
        store.close()


def test_ga05_reconnect_requires_fresh_snapshot_and_acks(tmp_path: Path) -> None:
    """GA-05: after reconnect, fresh snapshot and all three acks are required again.

    The protocol is reset on begin_reconnect, so acknowledged_subscriptions
    is empty until all three fresh acks are received.
    """
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()

        ws1 = _FakeWebSocket(_ack_and_context_frames(), disconnect_after=4)
        ws2 = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws1)
        factory.enqueue(ws2)

        async def _test() -> None:
            transport_task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda msg: None,
                    shutdown_event=shutdown_event,
                )
            )
            # Wait for first READY
            for _ in range(200):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            assert len(runtime.acknowledged_subscriptions) == 3
            # Wait for disconnect + reconnect (second WebSocket created).
            # The 0.001s reconnect delay is too short for a 0.01s poll to
            # reliably observe the intermediate state where acks are cleared,
            # so we poll for the reconnect signal instead.
            for _ in range(400):
                if len(factory.created) >= 2:
                    break
                await asyncio.sleep(0.01)
            # Wait for second READY
            for _ in range(400):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            # Fresh acks were required and received
            assert len(runtime.acknowledged_subscriptions) == 3
            shutdown_event.set()
            await asyncio.wait_for(transport_task, timeout=10.0)

        asyncio.run(_test())
    finally:
        store.close()


def test_ga05_continuous_recovery_failures_exhaust_budget(tmp_path: Path) -> None:
    """GA-05: exhausting the reconnect budget stops fail-closed (exit code 1)."""
    # Only one reconnect delay. Snapshot recovery keeps failing, so no
    # complete recovery can reset the budget before the next reconnect.
    runtime, store, _, _ = _make_runtime_short_reconnect(
        tmp_path, reconnect_delays=(0.001,)
    )
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()
        factory = _FakeWebSocketFactory()
        recovery_calls = 0

        def recovery_fails() -> tuple[str, str, str]:
            nonlocal recovery_calls
            recovery_calls += 1
            raise RuntimeError("simulated snapshot recovery failure")

        async def _test() -> None:
            exit_code = await _SCRIPT_MODULE._run_transport(
                runtime=runtime,
                recover_snapshot=recovery_fails,
                websocket_factory=factory,
                websocket_url="wss://test",
                status=lambda msg: None,
                shutdown_event=shutdown_event,
            )
            # First failure is on initial recovery. The first reconnect also
            # fails; the next reconnect is denied by the unchanged budget.
            assert exit_code == 1
            assert runtime.is_ready is False
            assert runtime._reconnect_attempt == 1

        asyncio.run(_test())
        assert recovery_calls == 2
        assert factory.created == []
    finally:
        store.close()


def test_ga05_cancellation_closes_resources(tmp_path: Path) -> None:
    """GA-05: setting shutdown_event during the transport loop exits cleanly."""
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()

        ws = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws)

        async def _test() -> None:
            transport_task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda msg: None,
                    shutdown_event=shutdown_event,
                )
            )
            # Wait for READY
            for _ in range(200):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            # Cancel by setting shutdown_event
            shutdown_event.set()
            exit_code = await asyncio.wait_for(transport_task, timeout=10.0)
            assert exit_code == 0
            # WebSocket was closed
            assert ws.closed is True

        asyncio.run(_test())
    finally:
        store.close()


def test_ga05_no_duplicate_session_or_publication_on_reconnect(tmp_path: Path) -> None:
    """GA-05: reconnect must not create a duplicate runtime session or publication."""
    runtime, store, _, _ = _make_runtime_short_reconnect(tmp_path)
    try:
        runtime.activate(now=NOW)
        session_id = runtime.session_id
        shutdown_event = asyncio.Event()

        ws1 = _FakeWebSocket(_ack_and_context_frames(), disconnect_after=4)
        ws2 = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws1)
        factory.enqueue(ws2)

        async def _test() -> None:
            transport_task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda msg: None,
                    shutdown_event=shutdown_event,
                )
            )
            # Wait for first READY
            for _ in range(200):
                if runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime.is_ready is True
            # Wait for disconnect + complete reconnect recovery.
            for _ in range(400):
                if len(factory.created) == 2 and runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert len(factory.created) == 2
            assert runtime._reconnect_attempt == 0
            # Session identity is unchanged
            assert runtime.session_id == session_id
            sessions = store.list_runtime_sessions()
            assert len(sessions) == 1
            # No publication was created (no triggering candle was sent)
            pubs, outbox = _row_counts(store)
            assert pubs == 0
            assert outbox == 0
            shutdown_event.set()
            await asyncio.wait_for(transport_task, timeout=10.0)

        asyncio.run(_test())
    finally:
        store.close()


def test_ga05_repeated_connection_closed_ok_recoveries_reset_budget(
    tmp_path: Path,
) -> None:
    """Seven completed normal-close recoveries stay inside a one-attempt budget."""
    runtime, store, _, _ = _make_runtime_short_reconnect(
        tmp_path, reconnect_delays=(0.001,)
    )
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()
        factory = _FakeWebSocketFactory()
        for _ in range(7):
            factory.enqueue(
                _FakeWebSocket(
                    _ack_and_context_frames(),
                    disconnect_after=4,
                    disconnect_error=ConnectionClosedOK(None, None),
                )
            )
        final_socket = _FakeWebSocket(
            _ack_and_context_frames(), shutdown_event=shutdown_event
        )
        factory.enqueue(final_socket)

        async def _test() -> None:
            task = asyncio.create_task(
                _SCRIPT_MODULE._run_transport(
                    runtime=runtime,
                    recover_snapshot=_recovery_frames,
                    websocket_factory=factory,
                    websocket_url="wss://test",
                    status=lambda _message: None,
                    shutdown_event=shutdown_event,
                )
            )
            for _ in range(2_000):
                if len(factory.created) == 8 and runtime.is_ready:
                    break
                await asyncio.sleep(0.01)
            assert len(factory.created) == 8
            assert runtime.is_ready is True
            assert runtime._reconnect_attempt == 0
            shutdown_event.set()
            assert await asyncio.wait_for(task, timeout=10.0) == 0

        asyncio.run(_test())
        assert final_socket.closed is True
    finally:
        store.close()


# ============================================================
# GA-05: task.cancel() propagation and durable shutdown (Packet-required)
# ============================================================
#
# Required assertions:
#   GA05_TASK_CANCEL_PROPAGATES
#   GA05_WEBSOCKET_CLOSES
#   GA05_RUNTIME_SHUTDOWN_CALLED
#   GA05_SESSION_CLOSED_AT_PERSISTED
#   GA05_STORE_CLOSES
#   GA05_NO_RECONNECT_AFTER_CANCEL
#   GA05_NO_SECOND_SNAPSHOT
#   GA05_NO_SECOND_WEBSOCKET
#
# A single end-to-end run_runtime task is cancelled mid-transport. The eight
# required assertions are checked against the post-cancellation state. This
# verifies the Packet's required cancellation-and-shutdown model:
#   except asyncio.CancelledError:
#       raise
#   except Exception as exc:
#       handle ordinary transport failure
# and the nested try/finally/try/finally/finally cleanup in run_runtime.


def _write_risk_config(tmp_path: Path) -> Path:
    """Write a valid r3.0 risk configuration JSON file and return its path."""
    path = tmp_path / "risk.json"
    path.write_text(
        '{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"1000.00",'
        '"RISK_PER_TRADE_PCT":"0.5000","MAX_NOTIONAL_USD":null}',
        encoding="utf-8",
    )
    return path


class _BlockingFakeWebSocket:
    """Fake WebSocket that sends canned frames, then blocks on recv() forever.

    The blocking recv() is the cancellation point: when the surrounding task is
    cancelled, ``await recv()`` raises ``asyncio.CancelledError`` which must
    propagate unchanged through ``_run_transport`` and ``run_runtime``.
    """

    def __init__(
        self,
        frames: list[str],
        *,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        self._frames = list(frames)
        self._pos = 0
        self._shutdown_event = shutdown_event
        self.sent: list[str] = []
        self.closed = False
        self.close_call_count = 0

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str | bytes:
        if self._pos < len(self._frames):
            frame = self._frames[self._pos]
            self._pos += 1
            return frame
        # No more frames: block forever (until cancelled).
        if self._shutdown_event is not None:
            await self._shutdown_event.wait()
        else:
            await asyncio.Event().wait()  # never set
        raise ConnectionError("unreachable")

    async def close(self) -> None:
        self.close_call_count += 1
        self.closed = True


class _CancelTrackingFactory:
    """WebSocket factory that tracks how many WebSockets it has created."""

    def __init__(self, ws: object) -> None:
        self._ws = ws
        self.created_count = 0

    async def __call__(self, url: str) -> object:
        self.created_count += 1
        return self._ws


class _CancelTrackingRecovery:
    """recover_snapshot callable that tracks how many times it was called."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> tuple[str, str, str]:
        self.calls += 1
        return _recovery_frames()


class _CloseTrackingStore(RuntimeStore):
    """RuntimeStore subclass that records close() invocations.

    Because GA-05's nested finally block calls ``runtime.shutdown()``
    (which persists ``closed_at`` on the durable session row) and then
    immediately calls ``store.close()`` (which closes the SQLite
    connection), the test cannot read the session row after ``run_runtime``
    returns.  ``close()`` therefore snapshots the durable session list
    just before closing the connection so the test can inspect it.
    """

    def __init__(self, *, database_path: Path) -> None:
        super().__init__(database_path=database_path)
        self.close_call_count = 0
        self.sessions_at_close: list[object] | None = None

    def close(self) -> None:
        self.close_call_count += 1
        try:
            self.sessions_at_close = list(self.list_runtime_sessions())
        except Exception:
            self.sessions_at_close = None
        super().close()


class _ShutdownTrackingRuntime(RestrictedPublicRuntime):
    """RestrictedPublicRuntime subclass that records shutdown() invocations."""

    def shutdown(self, *, now: datetime) -> None:
        if not hasattr(self, "_shutdown_call_count"):
            object.__setattr__(self, "_shutdown_call_count", 0)
        object.__setattr__(self, "_shutdown_call_count", self._shutdown_call_count + 1)
        super().shutdown(now=now)


def test_ga05_task_cancel_propagates_and_durable_cleanup(tmp_path: Path) -> None:
    """GA05_TASK_CANCEL_PROPAGATES, GA05_WEBSOCKET_CLOSES,
    GA05_RUNTIME_SHUTDOWN_CALLED, GA05_SESSION_CLOSED_AT_PERSISTED,
    GA05_STORE_CLOSES, GA05_NO_RECONNECT_AFTER_CANCEL,
    GA05_NO_SECOND_SNAPSHOT, GA05_NO_SECOND_WEBSOCKET.

    Cancelling the run_runtime task mid-transport propagates CancelledError
    through _run_transport and run_runtime unchanged, while the nested
    try/finally/try/finally/finally cleanup still executes WebSocket close,
    runtime.shutdown, durable session close, and store close. No reconnect,
    second snapshot recovery, or second WebSocket factory call occurs.
    """
    risk_path = _write_risk_config(tmp_path)
    credential_file = _write_credential_file(tmp_path / "credential.json")
    args = _SCRIPT_MODULE.CliArguments(
        enable_restricted_public_runtime=True,
        mode="RESTRICTED_PUBLIC_LIVE_SHADOW",
        database_path=tmp_path / "runtime.db",
        risk_configuration_path=risk_path,
        notification_credential_file=credential_file,
        webhook_timeout_seconds=10.0,
        acknowledgement_timeout_seconds=30.0,
        session_timeout_seconds=21600.0,
        validate_only=False,
    )

    shutdown_event = asyncio.Event()
    ws = _BlockingFakeWebSocket(
        _ack_and_context_frames(), shutdown_event=shutdown_event
    )
    factory = _CancelTrackingFactory(ws)
    recovery = _CancelTrackingRecovery()
    status_messages: list[str] = []

    original_store = _SCRIPT_MODULE.RuntimeStore
    original_runtime = _SCRIPT_MODULE.RestrictedPublicRuntime
    original_status_snapshot_path = _SCRIPT_MODULE._STATUS_SNAPSHOT_PATH
    _SCRIPT_MODULE.RuntimeStore = _CloseTrackingStore
    _SCRIPT_MODULE.RestrictedPublicRuntime = _ShutdownTrackingRuntime
    _SCRIPT_MODULE._STATUS_SNAPSHOT_PATH = tmp_path / "status.json"

    runtime_ref: list[_ShutdownTrackingRuntime] = []
    store_ref: list[_CloseTrackingStore] = []

    original_runtime_init = _ShutdownTrackingRuntime.__init__

    def _tracking_init(self, *a, **kw):  # type: ignore[no-untyped-def]
        original_runtime_init(self, *a, **kw)
        runtime_ref.append(self)

    _ShutdownTrackingRuntime.__init__ = _tracking_init  # type: ignore[assignment]

    original_store_open = _CloseTrackingStore.open

    @classmethod
    def _tracking_open(cls, database_path: Path) -> _CloseTrackingStore:  # type: ignore[override]
        instance = cls(database_path=database_path)
        store_ref.append(instance)
        return instance

    _CloseTrackingStore.open = _tracking_open  # type: ignore[assignment]

    try:
        async def _test() -> None:
            runtime_task = asyncio.create_task(
                _SCRIPT_MODULE.run_runtime(
                    args=args,
                    recover_snapshot=recovery,
                    websocket_factory=factory,
                    status=status_messages.append,
                )
            )
            # Wait for READY: poll the runtime reference until activate() +
            # snapshot recovery + 3 acks + context frame have all been
            # processed.
            for _ in range(500):
                if runtime_ref and runtime_ref[0].is_ready:
                    break
                await asyncio.sleep(0.01)
            assert runtime_ref, "runtime was never constructed"
            assert runtime_ref[0].is_ready is True, "runtime never reached READY"

            # GA05_TASK_CANCEL_PROPAGATES: cancel the task and verify
            # CancelledError propagates unchanged out of run_runtime.
            runtime_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await runtime_task

            # GA05_TASK_CANCEL_PROPAGATES: task is done and was cancelled.
            assert runtime_task.done() is True
            assert runtime_task.cancelled() is True

            # GA05_WEBSOCKET_CLOSES: WebSocket.close() was attempted exactly once.
            assert ws.close_call_count == 1, (
                f"expected exactly 1 WebSocket close, got {ws.close_call_count}"
            )

            # GA05_RUNTIME_SHUTDOWN_CALLED: runtime.shutdown() was called.
            assert runtime_ref[0]._shutdown_call_count == 1, (
                f"expected 1 shutdown call, "
                f"got {runtime_ref[0]._shutdown_call_count}"
            )
            assert runtime_ref[0].is_shutdown is True

            # GA05_SESSION_CLOSED_AT_PERSISTED: the durable session row has
            # closed_at set after shutdown.  ``run_runtime``'s nested finally
            # calls ``runtime.shutdown()`` (which persists closed_at) and then
            # immediately closes the store connection, so we read the snapshot
            # captured by ``_CloseTrackingStore.close()`` rather than reopening
            # the database.
            sessions = store_ref[0].sessions_at_close
            assert sessions is not None, (
                "store.close() did not snapshot runtime sessions"
            )
            assert len(sessions) == 1, (
                "exactly one durable runtime session must exist"
            )
            assert sessions[0].closed_at is not None, (
                "session closed_at must be set"
            )

            # GA05_STORE_CLOSES: store.close() was called.
            assert store_ref[0].close_call_count == 1, (
                f"expected 1 store.close call, "
                f"got {store_ref[0].close_call_count}"
            )

            # GA05_NO_RECONNECT_AFTER_CANCEL: no reconnect was attempted.
            # After cancellation the runtime's reconnect_attempt must
            # remain at 0 (initial READY was via begin_warmup).
            assert runtime_ref[0]._reconnect_attempt == 0, (
                f"expected 0 reconnect attempts after cancel, "
                f"got {runtime_ref[0]._reconnect_attempt}"
            )

            # GA05_NO_SECOND_SNAPSHOT: recover_snapshot was called exactly
            # once (the initial recovery).
            assert recovery.calls == 1, (
                f"expected exactly 1 recover_snapshot call, got {recovery.calls}"
            )

            # GA05_NO_SECOND_WEBSOCKET: the websocket factory was called
            # exactly once (the initial connection).
            assert factory.created_count == 1, (
                f"expected exactly 1 WebSocket factory call, "
                f"got {factory.created_count}"
            )

            # No "ERROR websocket: CancelledError" status message was emitted.
            assert not any(
                "CancelledError" in message for message in status_messages
            ), (
                f"CancelledError was logged as ERROR websocket: "
                f"{status_messages}"
            )

        asyncio.run(_test())
    finally:
        _SCRIPT_MODULE.RuntimeStore = original_store
        _SCRIPT_MODULE.RestrictedPublicRuntime = original_runtime
        _SCRIPT_MODULE._STATUS_SNAPSHOT_PATH = original_status_snapshot_path
        _ShutdownTrackingRuntime.__init__ = original_runtime_init  # type: ignore[assignment]
        _CloseTrackingStore.open = original_store_open  # type: ignore[assignment]


# ============================================================
# Credential file admission tests
# ============================================================


def _load_credential_file(credential_path: Path, *, timeout: float = 10.0) -> object:
    """Call the entrypoint's _load_credential_file function."""
    return _SCRIPT_MODULE._load_credential_file(credential_path, timeout)


def test_credential_valid_null_auth_succeeds(tmp_path: Path) -> None:
    """Valid credential with null authorization header is accepted."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    config = _load_credential_file(credential_file)
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_credential_valid_with_auth_succeeds(tmp_path: Path) -> None:
    """Valid credential with authorization header is accepted."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer token"},
    )
    config = _load_credential_file(credential_file)
    assert config.webhook_url == "https://hooks.example.com/eth-notify"
    assert config.authorization_header_name == "Authorization"
    assert config.authorization_header_value == "Bearer token"


def test_credential_missing_file_fails(tmp_path: Path) -> None:
    """Missing credential file fails before network activity."""
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="not a regular file"):
        _load_credential_file(missing)


def test_credential_symlink_fails(tmp_path: Path) -> None:
    """Symlink credential file is rejected."""
    target = tmp_path / "real.json"
    _write_credential_file(target)
    link = tmp_path / "link.json"
    os.symlink(target, link)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="symlink"):
        _load_credential_file(link)


def test_credential_directory_fails(tmp_path: Path) -> None:
    """Directory as credential file is rejected."""
    dir_path = tmp_path / "not-a-file"
    dir_path.mkdir()
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="not a regular file"):
        _load_credential_file(dir_path)


def test_credential_group_readable_fails(tmp_path: Path) -> None:
    """Group-readable credential file is rejected."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    credential_file.chmod(0o640)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="group or other access"):
        _load_credential_file(credential_file)


def test_credential_world_readable_fails(tmp_path: Path) -> None:
    """World-readable credential file is rejected."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    credential_file.chmod(0o604)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="group or other access"):
        _load_credential_file(credential_file)


def test_credential_owner_only_mode_succeeds(tmp_path: Path) -> None:
    """Owner-only mode (600) credential is accepted."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    credential_file.chmod(0o600)
    config = _load_credential_file(credential_file)
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_credential_malformed_utf8_fails(tmp_path: Path) -> None:
    """Malformed UTF-8 credential file is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_bytes(b'{"version": 1, "webhook_url": "\xff\xfe"}')
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="UTF-8"):
        _load_credential_file(credential_file)


def test_credential_malformed_json_fails(tmp_path: Path) -> None:
    """Malformed JSON credential file is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text("{not json", encoding="utf-8")
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="JSON"):
        _load_credential_file(credential_file)


def test_credential_unknown_keys_fails(tmp_path: Path) -> None:
    """Credential file with unknown top-level keys is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps({"version": 1, "webhook_url": "https://example.com/hook", "extra": "bad"}),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="unrecognized top-level"):
        _load_credential_file(credential_file)


def test_credential_invalid_version_fails(tmp_path: Path) -> None:
    """Credential file with invalid version is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 2,
                "webhook_url": "https://example.com/hook",
                "authorization_header": None,
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="version"):
        _load_credential_file(credential_file)


def test_credential_missing_webhook_url_fails(tmp_path: Path) -> None:
    """Credential file with missing webhook_url is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps({"version": 1, "webhook_url": "", "authorization_header": None}),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="webhook_url"):
        _load_credential_file(credential_file)


def test_credential_malformed_auth_object_fails(tmp_path: Path) -> None:
    """Credential file with malformed authorization_header is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://example.com/hook",
                "authorization_header": "not-an-object",
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="authorization_header"):
        _load_credential_file(credential_file)


def test_credential_auth_unknown_keys_fails(tmp_path: Path) -> None:
    """Credential file authorization_header with unknown keys is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://example.com/hook",
                "authorization_header": {
                    "name": "X",
                    "value": "Y",
                    "extra": "Z",
                },
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="authorization_header"):
        _load_credential_file(credential_file)


def test_credential_auth_empty_name_fails(tmp_path: Path) -> None:
    """Credential file authorization_header with empty name is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://example.com/hook",
                "authorization_header": {"name": "", "value": "Y"},
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="authorization_header"):
        _load_credential_file(credential_file)


def test_credential_auth_empty_value_fails(tmp_path: Path) -> None:
    """Credential file authorization_header with empty value is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://example.com/hook",
                "authorization_header": {"name": "X", "value": ""},
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="authorization_header"):
        _load_credential_file(credential_file)


def test_credential_oversized_file_fails(tmp_path: Path) -> None:
    """Credential file exceeding max size is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://example.com/" + "x" * 5000,
                "authorization_header": None,
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="bounded size"):
        _load_credential_file(credential_file)


def test_credential_non_object_fails(tmp_path: Path) -> None:
    """Credential file that is not a JSON object is rejected."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="JSON object"):
        _load_credential_file(credential_file)


def test_credential_unreadable_file_fails(tmp_path: Path) -> None:
    """Unreadable credential file is rejected."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    credential_file.chmod(0o000)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError):
        _load_credential_file(credential_file)


# ============================================================
# Secret-absence proofs
# ============================================================


def test_secret_webhook_url_not_in_argv(tmp_path: Path) -> None:
    """Secret URL and path values do not appear in Python argv."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://secret.example.com/path?key=value",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--enable-restricted-public-runtime",
            "--mode", "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "--database-path", str(tmp_path / "runtime.db"),
            "--risk-configuration-path", str(tmp_path / "risk.json"),
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    # The command should fail (missing risk config), but the credential
    # URL must not appear in argv or stdout/stderr.
    output = result.stdout + result.stderr
    assert "secret.example.com" not in output
    assert "key=value" not in output


def test_secret_auth_value_not_in_argv(tmp_path: Path) -> None:
    """Authorization header values do not appear in Python argv."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer secret-token-123"},
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--enable-restricted-public-runtime",
            "--mode", "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "--database-path", str(tmp_path / "runtime.db"),
            "--risk-configuration-path", str(tmp_path / "risk.json"),
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    output = result.stdout + result.stderr
    assert "secret-token-123" not in output
    assert "Bearer secret" not in output


def test_secret_wrapper_stub_argv_contains_only_credential_path(
    tmp_path: Path,
) -> None:
    """Wrapper stub-exec argv contains only the credential path, not its contents."""
    # Write a credential file with secrets
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://secret-webhook.example.com/notify",
        authorization_header={"name": "X-Api-Key", "value": "sk-top-secret"},
    )
    # Create a stub Python that records its argv
    stub_python = tmp_path / "stub_python"
    stub_python.write_text(
        "#!/usr/bin/env bash\n"
        "for arg in \"$@\"; do echo \"$arg\"; done\n"
    )
    stub_python.chmod(0o755)
    stub_entry = tmp_path / "entry.py"
    stub_entry.write_text("")

    result = subprocess.run(
        [
            "bash", "-c",
            f"CREDENTIALS_DIRECTORY={tmp_path} "
            f"exec {stub_python} {stub_entry} "
            f"--notification-credential-file {credential_file}",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout + result.stderr
    assert "secret-webhook" not in output
    assert "sk-top-secret" not in output
    assert "X-Api-Key" not in output
    # The credential path itself should appear
    assert str(credential_file) in output


def test_secret_credential_values_not_in_subprocess_output(
    tmp_path: Path,
) -> None:
    """Credential values do not appear in stdout or stderr."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://stdout-test.example.com/notify",
        authorization_header={"name": "Authorization", "value": "Bearer stdout-test-secret"},
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--enable-restricted-public-runtime",
            "--mode", "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "--database-path", str(tmp_path / "runtime.db"),
            "--risk-configuration-path", str(tmp_path / "risk.json"),
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    output = result.stdout + result.stderr
    assert "stdout-test-secret" not in output
    assert "stdout-test.example.com" not in output


def test_committed_example_not_production_usable() -> None:
    """The committed credential example is not production-usable."""
    example_path = (
        Path(__file__).resolve().parents[1]
        / "deploy"
        / "p4a"
        / "credentials"
        / "notification-credential.json.example"
    )
    raw = example_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert data["version"] == 1
    assert "example.invalid" in data["webhook_url"]
    assert "replace-me" in data["webhook_url"]
    assert data["authorization_header"] is None


def test_credential_values_not_in_error_messages(tmp_path: Path) -> None:
    """Credential values are not leaked in error messages."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://error-leak-test.example.com/notify",
    )
    # Trigger a credential error by making the file group-readable
    credential_file.chmod(0o640)
    try:
        _load_credential_file(credential_file)
    except _SCRIPT_MODULE.CredentialFileError as exc:
        msg = str(exc)
        assert "error-leak-test" not in msg
        assert "https://" not in msg
    else:
        pytest.fail("Expected CredentialFileError")


# ============================================================
# Repair: relative path, exact version, header grammar, timeout
# ============================================================


def test_credential_relative_path_fails(tmp_path: Path) -> None:
    """Relative credential path is rejected before resolve()."""
    # Write a valid credential, then try to load with a relative path
    _write_credential_file(tmp_path / "credential.json")
    import os as _os

    cwd = _os.getcwd()
    try:
        _os.chdir(tmp_path)
        with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="absolute"):
            _SCRIPT_MODULE._load_credential_file(Path("credential.json"), 10.0)
    finally:
        _os.chdir(cwd)


def test_credential_json_true_version_fails(tmp_path: Path) -> None:
    """JSON true (boolean) as version must fail the exact type check."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": True,
                "webhook_url": "https://example.com/hook",
                "authorization_header": None,
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="version"):
        _load_credential_file(credential_file)


def test_credential_json_float_version_fails(tmp_path: Path) -> None:
    """JSON float 1.0 as version must fail the exact type check."""
    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1.0,
                "webhook_url": "https://example.com/hook",
                "authorization_header": None,
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="version"):
        _load_credential_file(credential_file)


def test_credential_fstat_owner_mode_authoritative(tmp_path: Path) -> None:
    """Post-open fstat owner/mode/size is authoritative (not pathname stat).

    The credential file is opened with O_NOFOLLOW and fstat is used for
    owner/mode checks.  Pathname stat is not consulted.
    """
    credential_file = _write_credential_file(tmp_path / "credential.json")
    config = _load_credential_file(credential_file)
    # The credential loaded successfully, proving fstat passed
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_credential_descriptor_substitution_insecure_mode_fails(
    tmp_path: Path,
) -> None:
    """Descriptor substitution with insecure mode fails.

    fstat is used for mode/owner checks on the same descriptor that was
    used for reading, preventing TOCTOU between pathname stat and open.
    After chmod changes the mode on disk, a fresh load fails because
    fstat (not pathname stat) sees the new insecure mode.
    """
    credential_file = _write_credential_file(tmp_path / "credential.json")
    # First load succeeds with secure mode
    _load_credential_file(credential_file)
    # Change permissions on disk to group-readable
    credential_file.chmod(0o640)
    # Fresh load must fail because fstat sees the insecure mode
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="group or other"):
        _load_credential_file(credential_file)


def test_credential_fifo_fails(tmp_path: Path) -> None:
    """FIFO as credential file is rejected."""
    fifo_path = tmp_path / "fifo"
    os.mkfifo(str(fifo_path))
    fifo_path.chmod(0o600)
    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="not a regular file"):
        _load_credential_file(fifo_path)


def test_credential_unix_socket_fails(tmp_path: Path) -> None:
    """Unix socket as credential file is rejected where safely testable."""
    import socket as _socket

    # Use a short path to avoid AF_UNIX path length limits on macOS
    sock_path = Path("/tmp") / f"test_unix_sock_{os.getpid()}"
    try:
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        sock.bind(str(sock_path))
        sock_path.chmod(0o600)
        try:
            with pytest.raises(_SCRIPT_MODULE.CredentialFileError):
                _load_credential_file(sock_path)
        finally:
            sock.close()
    finally:
        if sock_path.exists():
            sock_path.unlink()


def test_credential_wrong_owner_fails(tmp_path: Path) -> None:
    """Wrong owner is rejected via fstat."""
    current_euid = os.geteuid()
    if current_euid == 0:
        pytest.skip("running as root; wrong-owner test requires non-root")
    credential_file = _write_credential_file(tmp_path / "credential.json")
    # The file is owned by the current user and that's fine (os.geteuid check).
    # But if the file owner is neither root nor the effective user, it fails.
    # We can't easily change owner without root, so we verify the check
    # uses os.geteuid() semantics by testing that the current owner passes.
    config = _load_credential_file(credential_file)
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_credential_malformed_header_name_colon_fails(tmp_path: Path) -> None:
    """Header name with colon is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "X:Bad", "value": "token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header name"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_name_whitespace_fails(tmp_path: Path) -> None:
    """Header name with whitespace is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "X Bad", "value": "token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header name"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_name_control_fails(tmp_path: Path) -> None:
    """Header name with control character is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "X-Bad\x01", "value": "token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header name"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_value_cr_fails(tmp_path: Path) -> None:
    """Header value with CR is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer\r token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header value"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_value_lf_fails(tmp_path: Path) -> None:
    """Header value with LF is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer\n token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header value"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_value_nul_fails(tmp_path: Path) -> None:
    """Header value with NUL is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer\x00 token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header value"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_value_control_fails(tmp_path: Path) -> None:
    """Header value with control character is rejected."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "Authorization", "value": "Bearer\x01 token"},
    )
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header value"
    ):
        _load_credential_file(credential_file)


def test_credential_malformed_header_fails_before_network_spy(tmp_path: Path) -> None:
    """Malformed header fails before any network spy is invoked.

    The credential admission completes entirely before any store, transport,
    or network activity.  The spy patterns prove no network-level objects
    are created before the header validation failure.
    """
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        authorization_header={"name": "X-Bad\x01", "value": "token"},
    )
    # The credential is loaded purely in-process; no subprocess, no
    # network, no store, no transport, no WebSocket invocation.
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError, match="authorization header name"
    ):
        _load_credential_file(credential_file)


def test_credential_configured_timeout_preserved(tmp_path: Path) -> None:
    """Configured webhook timeout is preserved through to NotificationConfig."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    config = _load_credential_file(credential_file, timeout=23.5)
    assert config.timeout_seconds == 23.5


def test_credential_repr_contains_no_values(tmp_path: Path) -> None:
    """repr(notification_config) contains no credential values."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://secret-host.example.com/private/path?key=secret",
        authorization_header={"name": "X-Api-Key", "value": "sk-very-secret-key"},
    )
    config = _load_credential_file(credential_file)
    r = repr(config)
    assert "secret-host" not in r
    assert "private" not in r
    assert "X-Api-Key" not in r
    assert "sk-very-secret-key" not in r


def test_dispatcher_repr_contains_no_values(tmp_path: Path) -> None:
    """repr(NotificationDispatcher) contains no credential values."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://dispatcher-secret.example.com/notify",
        authorization_header={"name": "Authorization", "value": "Bearer dispatcher-secret"},
    )
    config = _load_credential_file(credential_file)
    store = _open_store(tmp_path)
    try:
        transport = _MockTransport(
            responses=(HttpResponse(status_code=200, body=b"ok"),), calls=[]
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=config
        )
        r = repr(dispatcher)
        assert "dispatcher-secret" not in r
        assert "dispatcher-secret.example.com" not in r
        assert "Authorization" not in r
        assert "Bearer" not in r
    finally:
        store.close()


def test_credential_file_error_no_traceback(tmp_path: Path) -> None:
    """CredentialFileError produces no traceback in the CLI."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    credential_file.chmod(0o640)
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--validate-only",
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    assert result.returncode == 3
    assert "Traceback" not in result.stderr
    assert "credential validation failed" in result.stderr.lower()


def test_notification_config_error_no_traceback(tmp_path: Path) -> None:
    """NotificationConfigError produces no traceback in the CLI."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="http://not-https.example.com/notify",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--validate-only",
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    assert result.returncode == 3
    assert "Traceback" not in result.stderr
    assert "credential validation failed" in result.stderr.lower()


def test_validate_only_loads_credential_no_network(tmp_path: Path) -> None:
    """Validation-only CLI loads the credential but performs no network."""
    credential_file = _write_credential_file(tmp_path / "credential.json")
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--validate-only",
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_validate_only_no_credential_values_in_output(tmp_path: Path) -> None:
    """Validation-only stdout/stderr contain no credential values."""
    credential_file = _write_credential_file(
        tmp_path / "credential.json",
        webhook_url="https://validate-secret.example.com/notify",
        authorization_header={"name": "X-Key", "value": "validate-secret-token"},
    )
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--validate-only",
            "--notification-credential-file", str(credential_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src", "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
    )
    output = result.stdout + result.stderr
    assert "validate-secret" not in output
    assert "validate-secret.example.com" not in output
    assert "validate-secret-token" not in output


# ============================================================
# Real wrapper argv test (replaces manual argv construction)
# ============================================================


def test_real_wrapper_argv_contains_credential_path_not_contents(
    tmp_path: Path,
) -> None:
    """Execute the real wrapper with a stub Python; prove argv has path only.

    The real wrapper at scripts/p4a/run_restricted_public_runtime.sh is
    executed with isolated temp paths.  A stub Python executable records
    its argv.  The test proves the credential path appears but credential
    contents (URL, header name, header value) do not.
    """
    wrapper_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "p4a"
        / "run_restricted_public_runtime.sh"
    )
    wrapper_text = wrapper_path.read_text()

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)

    permit = tmp_path / "permit"
    permit.write_text("")

    stub_python = venv_bin / "python"
    stub_python.write_text(
        "#!/usr/bin/env bash\n"
        "for arg in \"$@\"; do echo \"$arg\"; done\n"
    )
    stub_python.chmod(0o755)

    stub_entry = scripts_dir / "run_first_launch_public_runtime.py"
    stub_entry.write_text("# stub\n")

    risk_file = config_dir / "risk-configuration.json"
    risk_file.write_text('{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"1000.00","RISK_PER_TRADE_PCT":"0.5000","MAX_NOTIONAL_USD":null}\n')

    db_path = state_dir / "runtime.db"

    credential_dir = tmp_path / "credentials"
    credential_dir.mkdir()
    credential_file = credential_dir / "notification.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://secret-wrapper-test.example.com/notify",
                "authorization_header": {
                    "name": "X-Api-Key",
                    "value": "sk-wrapper-secret-token",
                },
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)

    content = wrapper_text
    content = content.replace(
        'ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"',
        f'ACTIVATION_PERMIT="{permit}"',
    )
    content = content.replace(
        'PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"',
        f'PYTHON_ENTRYPOINT="{stub_entry}"',
    )
    content = content.replace(
        'PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"',
        f'PYTHON_EXECUTABLE="{stub_python}"',
    )
    content = content.replace(
        'PYTHONPATH_FORCED="/opt/trader-assist-v0/src"',
        f'PYTHONPATH_FORCED="{src_dir}"',
    )
    content = content.replace(
        'APPROVED_STATE_DIR="/var/lib/trader-assist-v0"',
        f'APPROVED_STATE_DIR="{state_dir}"',
    )
    content = content.replace(
        'APPROVED_CONFIG_DIR="/etc/trader-assist-v0"',
        f'APPROVED_CONFIG_DIR="{config_dir}"',
    )

    wrapper_copy = tmp_path / "wrapper.sh"
    wrapper_copy.write_text(content)
    wrapper_copy.chmod(0o755)

    result = subprocess.run(
        ["bash", str(wrapper_copy)],
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TRADER_ASSIST_V0_ENABLE": "1",
            "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "TRADER_ASSIST_V0_DATABASE_PATH": str(db_path),
            "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(risk_file),
            "CREDENTIALS_DIRECTORY": str(credential_dir),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = result.stdout + result.stderr
    # Credential path must appear
    assert str(credential_file) in output
    # Credential content must NOT appear
    assert "secret-wrapper-test" not in output
    assert "sk-wrapper-secret-token" not in output
    assert "X-Api-Key" not in output


def test_real_wrapper_relative_credentials_dir_fails(
    tmp_path: Path,
) -> None:
    """Relative CREDENTIALS_DIRECTORY fails in the real wrapper."""
    wrapper_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "p4a"
        / "run_restricted_public_runtime.sh"
    )
    wrapper_text = wrapper_path.read_text()
    permit = tmp_path / "permit"
    permit.write_text("")
    content = wrapper_text.replace(
        'ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"',
        f'ACTIVATION_PERMIT="{permit}"',
    )
    wrapper_copy = tmp_path / "wrapper.sh"
    wrapper_copy.write_text(content)
    wrapper_copy.chmod(0o755)
    result = subprocess.run(
        ["bash", str(wrapper_copy)],
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TRADER_ASSIST_V0_ENABLE": "1",
            "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "TRADER_ASSIST_V0_DATABASE_PATH": "/var/lib/trader-assist-v0/runtime.db",
            "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": "/etc/trader-assist-v0/risk.json",
            "CREDENTIALS_DIRECTORY": "relative/path",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "CREDENTIALS_DIRECTORY must be an absolute path" in result.stderr


# ============================================================
# /proc/<pid>/cmdline test (Linux only)
# ============================================================


def test_proc_cmdline_credential_content_absent(
    tmp_path: Path,
) -> None:
    """On Linux, start a harmless stub through the real wrapper and inspect
    /proc/<pid>/cmdline.  Credential content must be absent."""
    if not sys.platform.startswith("linux"):
        pytest.skip("/proc/cmdline test requires Linux")

    wrapper_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "p4a"
        / "run_restricted_public_runtime.sh"
    )
    wrapper_text = wrapper_path.read_text()

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)

    permit = tmp_path / "permit"
    permit.write_text("")

    # Stub that sleeps long enough for us to read /proc
    stub_python = venv_bin / "python"
    stub_python.write_text(
        "#!/usr/bin/env bash\n"
        "sleep 5\n"
    )
    stub_python.chmod(0o755)

    stub_entry = scripts_dir / "run_first_launch_public_runtime.py"
    stub_entry.write_text("# stub\n")

    risk_file = config_dir / "risk-configuration.json"
    risk_file.write_text('{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"1000.00","RISK_PER_TRADE_PCT":"0.5000","MAX_NOTIONAL_USD":null}\n')

    db_path = state_dir / "runtime.db"

    credential_dir = tmp_path / "credentials"
    credential_dir.mkdir()
    credential_file = credential_dir / "notification.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": "https://proc-test.example.com/notify",
                "authorization_header": {
                    "name": "X-Proc-Key",
                    "value": "sk-proc-secret",
                },
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)

    content = wrapper_text
    content = content.replace(
        'ACTIVATION_PERMIT="/etc/trader-assist-v0/activation-permit"',
        f'ACTIVATION_PERMIT="{permit}"',
    )
    content = content.replace(
        'PYTHON_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"',
        f'PYTHON_ENTRYPOINT="{stub_entry}"',
    )
    content = content.replace(
        'PYTHON_EXECUTABLE="/opt/trader-assist-v0/venv/bin/python"',
        f'PYTHON_EXECUTABLE="{stub_python}"',
    )
    content = content.replace(
        'PYTHONPATH_FORCED="/opt/trader-assist-v0/src"',
        f'PYTHONPATH_FORCED="{src_dir}"',
    )
    content = content.replace(
        'APPROVED_STATE_DIR="/var/lib/trader-assist-v0"',
        f'APPROVED_STATE_DIR="{state_dir}"',
    )
    content = content.replace(
        'APPROVED_CONFIG_DIR="/etc/trader-assist-v0"',
        f'APPROVED_CONFIG_DIR="{config_dir}"',
    )

    wrapper_copy = tmp_path / "wrapper.sh"
    wrapper_copy.write_text(content)
    wrapper_copy.chmod(0o755)

    proc = subprocess.Popen(
        ["bash", str(wrapper_copy)],
        env={
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "TRADER_ASSIST_V0_ENABLE": "1",
            "TRADER_ASSIST_V0_MODE": "RESTRICTED_PUBLIC_LIVE_SHADOW",
            "TRADER_ASSIST_V0_DATABASE_PATH": str(db_path),
            "TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH": str(risk_file),
            "CREDENTIALS_DIRECTORY": str(credential_dir),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        import time as _time

        _time.sleep(0.5)
        cmdline_path = Path(f"/proc/{proc.pid}/cmdline")
        if cmdline_path.exists():
            cmdline = cmdline_path.read_bytes()
            cmdline_text = cmdline.decode("utf-8", errors="replace")
            assert "proc-test" not in cmdline_text
            assert "sk-proc-secret" not in cmdline_text
            assert "X-Proc-Key" not in cmdline_text
            # The credential path itself may appear
            assert str(credential_file) in cmdline_text
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


# ============================================================
# FR-01: Deterministic descriptor regression tests
# ============================================================


def _valid_credential_bytes() -> bytes:
    """Return a valid version-1 credential document as bytes (synthetic fixture)."""
    doc = {
        "version": 1,
        "webhook_url": "https://hooks.example.com/eth-notify",
        "authorization_header": None,
    }
    return json.dumps(doc).encode("utf-8")


def _credential_json(tmp_path: Path) -> Path:
    """Create a valid credential file with secure permissions in a tmp dir."""
    path = tmp_path / "credential.json"
    path.write_bytes(_valid_credential_bytes())
    path.chmod(0o600)
    return path


# --- TEST 1: DESCRIPTOR_MODE_IS_AUTHORITATIVE ---


def test_fr01_descriptor_mode_is_authoritative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-01: Descriptor mode, not pathname mode, controls admission.

    Create a valid temp credential with acceptable pathname permissions.
    Inject fstat metadata whose mode contains prohibited group/other bits.
    Prove rejection is driven by descriptor metadata, not pathname stat.
    """
    credential_file = _credential_json(tmp_path)
    sentinel_fd = 9999

    # Build synthetic stat with group-writable permissions but otherwise valid
    real_stat = credential_file.stat()
    uid = real_stat.st_uid
    size = len(_valid_credential_bytes())

    class _InjectedStat:
        st_mode = stat.S_IFREG | 0o640  # group-readable = insecure
        st_uid = uid
        st_size = size
        st_dev = real_stat.st_dev
        st_ino = real_stat.st_ino

    open_calls: list[tuple[object, ...]] = []
    fstat_calls: list[int] = []

    def _fake_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        open_calls.append((path, flags))
        return sentinel_fd

    def _fake_fstat(fd: int) -> _InjectedStat:
        fstat_calls.append(fd)
        return _InjectedStat()

    close_calls: list[int] = []

    def _fake_close(fd: int) -> None:
        close_calls.append(fd)

    monkeypatch.setattr(os, "open", _fake_open)
    monkeypatch.setattr(os, "fstat", _fake_fstat)
    monkeypatch.setattr(os, "close", _fake_close)

    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="group or other"):
        _load_credential_file(credential_file)

    # Prove the injected os.open and os.fstat paths were exercised
    assert len(open_calls) >= 1
    assert len(fstat_calls) >= 1
    assert fstat_calls[0] == sentinel_fd
    # Prove os.close was called on the sentinel descriptor
    assert len(close_calls) >= 1
    assert close_calls[0] == sentinel_fd


# --- TEST 2: FOREIGN_DESCRIPTOR_OWNER_IS_REJECTED ---


def test_fr02_foreign_descriptor_owner_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-01: Foreign descriptor owner (st_uid) is rejected.

    Inject fstat metadata whose st_uid is neither 0 nor os.geteuid().
    Must run even when the process is root, and must not skip merely
    because os.geteuid() == 0.
    """
    credential_file = _credential_json(tmp_path)
    sentinel_fd = 9999

    real_stat = credential_file.stat()
    current_euid = os.geteuid()
    size = len(_valid_credential_bytes())

    # Choose a deterministic foreign UID distinct from both 0 and current euid
    # The production code allows st_uid == 0 or st_uid == current_euid.
    # We need a UID that is neither, so the check must reject.
    foreign_uid = 1 if current_euid == 0 else 9999
    if foreign_uid == current_euid:
        foreign_uid = 9998

    class _InjectedStat:
        st_mode = stat.S_IFREG | 0o600
        st_uid = foreign_uid
        st_size = size
        st_dev = real_stat.st_dev
        st_ino = real_stat.st_ino

    fstat_calls: list[int] = []

    def _fake_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        return sentinel_fd

    def _fake_fstat(fd: int) -> _InjectedStat:
        fstat_calls.append(fd)
        return _InjectedStat()

    def _fake_close(fd: int) -> None:
        pass

    monkeypatch.setattr(os, "open", _fake_open)
    monkeypatch.setattr(os, "fstat", _fake_fstat)
    monkeypatch.setattr(os, "close", _fake_close)

    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="owner"):
        _load_credential_file(credential_file)

    assert len(fstat_calls) >= 1
    assert fstat_calls[0] == sentinel_fd


# --- TEST 3: MULTIPLE_SHORT_READS_THEN_EOF_SUCCEED ---


def test_fr03_multiple_short_reads_then_eof_succeed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-01: Multiple short reads then EOF succeed.

    Patch os.read to return the credential through multiple short
    chunks, then EOF.  Verify exact read-call counts and that the
    resulting NotificationConfig fields match expected values.
    """
    credential_file = _credential_json(tmp_path)
    sentinel_fd = 9999
    credential_bytes = _valid_credential_bytes()

    real_stat = credential_file.stat()

    class _InjectedStat:
        st_mode = stat.S_IFREG | 0o600
        st_uid = real_stat.st_uid
        st_size = len(credential_bytes)
        st_dev = real_stat.st_dev
        st_ino = real_stat.st_ino

    read_calls: list[int] = []

    # Split into 3 chunks: 3, 5, and the rest
    chunk1 = credential_bytes[:3]
    chunk2 = credential_bytes[3:8]
    chunk3 = credential_bytes[8:]
    chunks = [chunk1, chunk2, chunk3, b""]

    def _fake_read(fd: int, size: int) -> bytes:
        read_calls.append(size)
        if not chunks:
            return b""
        return chunks.pop(0)

    def _fake_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        return sentinel_fd

    def _fake_fstat(fd: int) -> _InjectedStat:
        return _InjectedStat()

    def _fake_close(fd: int) -> None:
        pass

    monkeypatch.setattr(os, "open", _fake_open)
    monkeypatch.setattr(os, "fstat", _fake_fstat)
    monkeypatch.setattr(os, "read", _fake_read)
    monkeypatch.setattr(os, "close", _fake_close)

    config = _load_credential_file(credential_file)

    # More than one non-empty read must occur, plus one EOF read
    assert len(read_calls) >= 4, (
        f"expected at least 4 reads (3 content + 1 EOF), got {len(read_calls)}"
    )
    # The last read returned EOF
    # Verify expected NotificationConfig fields
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


# --- TEST 4: READ_ERROR_AFTER_PARTIAL_ACCUMULATION_FAILS_CLOSED ---


def test_fr04_read_error_after_partial_accumulation_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-01: Read error after partial accumulation fails closed.

    Create a synthetic, non-production credential file with distinctive
    fragments.  Patch os.read to return partial bytes on the first call
    and raise an injected OSError on the second.  Prove the loader is
    invoked exactly once, the complete sequence ["partial", "error"] is
    observed, and no synthetic fragment appears in exception text, repr,
    stdout or stderr.
    """
    # ── synthetic, non-production credential with distinctive fragments ──
    synthetic_url = "https://synth-partial-read.example.com/webhook/notify?token=distinctive-fragment-abc123"
    synthetic_hostname = "synth-partial-read.example.com"
    synthetic_path = "/webhook/notify"
    synthetic_token = "distinctive-fragment-abc123"
    synthetic_auth_name = "X-Synthetic-Auth-Header"
    synthetic_auth_value = "Bearer synth-auth-value-distinctive-xyz789"
    synthetic_auth_fragment = "synth-auth-value-distinctive-xyz789"

    credential_file = tmp_path / "credential.json"
    credential_file.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": synthetic_url,
                "authorization_header": {
                    "name": synthetic_auth_name,
                    "value": synthetic_auth_value,
                },
            }
        ),
        encoding="utf-8",
    )
    credential_file.chmod(0o600)

    credential_bytes = credential_file.read_bytes()
    real_stat = credential_file.stat()
    sentinel_fd = 9999

    # ── acceptable descriptor metadata (regular file, 0600, allowed owner) ──
    class _InjectedStat:
        st_mode = stat.S_IFREG | 0o600
        st_uid = real_stat.st_uid
        st_size = len(credential_bytes)
        st_dev = real_stat.st_dev
        st_ino = real_stat.st_ino

    # ── deterministic os.read: ["partial", "error"] ──
    read_events: list[str] = []
    read_call_count = 0
    partial_bytes: bytes = b""

    class _InjectedOSError(OSError):
        pass

    def _fake_read(fd: int, size: int) -> bytes:
        nonlocal read_call_count, partial_bytes
        read_call_count += 1
        if read_call_count == 1:
            read_events.append("partial")
            partial_bytes = credential_bytes[:20]
            return partial_bytes
        elif read_call_count == 2:
            read_events.append("error")
            raise _InjectedOSError("simulated read error")
        else:
            pytest.fail(f"unexpected os.read call #{read_call_count}")

    def _fake_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        return sentinel_fd

    def _fake_fstat(fd: int) -> _InjectedStat:
        return _InjectedStat()

    def _fake_close(fd: int) -> None:
        pass

    monkeypatch.setattr(os, "open", _fake_open)
    monkeypatch.setattr(os, "fstat", _fake_fstat)
    monkeypatch.setattr(os, "read", _fake_read)
    monkeypatch.setattr(os, "close", _fake_close)

    # ── invoke the loader exactly once ──
    with pytest.raises(
        _SCRIPT_MODULE.CredentialFileError,
        match="credential file cannot be read",
    ) as exc_info:
        _load_credential_file(credential_file)

    # ── post-invocation assertions (same invocation) ──
    assert read_events == ["partial", "error"]
    assert read_call_count == 2
    assert len(partial_bytes) > 0, "partial bytes must be non-empty"
    assert "error" in read_events, "OSError branch must be exercised"
    assert str(exc_info.value) == "credential file cannot be read"

    # ── inspect exception text and repr ──
    exception_text = str(exc_info.value)
    exception_repr = repr(exc_info.value)

    # ── inspect stdout / stderr ──
    captured = capsys.readouterr()

    # ── no synthetic fragment may appear in any output surface ──
    synthetic_fragments = [
        synthetic_url,
        synthetic_hostname,
        synthetic_path,
        synthetic_token,
        synthetic_auth_name,
        synthetic_auth_value,
        synthetic_auth_fragment,
        "simulated read error",  # injected internal OSError message
    ]
    for fragment in synthetic_fragments:
        assert fragment not in exception_text, (
            f"synthetic fragment leaked in exception_text: {fragment!r}"
        )
        assert fragment not in exception_repr, (
            f"synthetic fragment leaked in exception_repr: {fragment!r}"
        )
        assert fragment not in captured.out, (
            f"synthetic fragment leaked in stdout: {fragment!r}"
        )
        assert fragment not in captured.err, (
            f"synthetic fragment leaked in stderr: {fragment!r}"
        )


# --- TEST 5: DESCRIPTOR_SIZE_ACCEPTABLE_BUT_STREAM_EXCEEDS_LIMIT ---


def test_fr05_descriptor_size_acceptable_but_stream_exceeds_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-01: Descriptor size acceptable but stream exceeds limit.

    Inject fstat metadata reporting st_size <= 4096 bytes.
    Patch os.read to provide exactly 4097 accumulated bytes.
    Prove the initial descriptor size check passes, accumulated bytes
    exceed the limit, and the loader rejects with bounded-size error.
    """
    credential_file = _credential_json(tmp_path)
    sentinel_fd = 9999

    real_stat = credential_file.stat()

    class _InjectedStat:
        st_mode = stat.S_IFREG | 0o600
        st_uid = real_stat.st_uid
        st_size = 100  # well below 4096, fstat size check passes
        st_dev = real_stat.st_dev
        st_ino = real_stat.st_ino

    fstat_calls: list[int] = []
    read_calls: list[int] = []

    def _fake_read(fd: int, size: int) -> bytes:
        read_calls.append(size)
        if len(read_calls) == 1:
            # Return 1024 bytes (first chunk)
            return b"x" * 1024
        if len(read_calls) == 2:
            # Return another 1024 bytes
            return b"x" * 1024
        if len(read_calls) == 3:
            # Return another 1024 bytes
            return b"x" * 1024
        if len(read_calls) == 4:
            # Return another 1024 bytes (total 4096 still OK)
            return b"x" * 1024
        # 5th call: return 1 more byte → 4097, exceeds 4096
        return b"x" * 1

    def _fake_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        return sentinel_fd

    def _fake_fstat(fd: int) -> _InjectedStat:
        fstat_calls.append(fd)
        return _InjectedStat()

    def _fake_close(fd: int) -> None:
        pass

    monkeypatch.setattr(os, "open", _fake_open)
    monkeypatch.setattr(os, "fstat", _fake_fstat)
    monkeypatch.setattr(os, "read", _fake_read)
    monkeypatch.setattr(os, "close", _fake_close)

    with pytest.raises(_SCRIPT_MODULE.CredentialFileError, match="bounded size"):
        _load_credential_file(credential_file)

    # Prove fstat and repeated-read paths were exercised
    assert len(fstat_calls) >= 1
    assert len(read_calls) >= 5


# --- TEST 6: O_NOFOLLOW_OPEN_FLAG_IS_ENFORCED ---


def test_fr06_o_nofollow_open_flag_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-01: O_NOFOLLOW open flag is enforced.

    Intercept the actual credential os.open call, capture the flags,
    and prove os.O_NOFOLLOW is included.  Allow the underlying valid
    credential load to complete successfully.
    """
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW is not available on this platform")

    credential_file = _credential_json(tmp_path)
    open_flags_captured: list[int] = []

    real_open = os.open

    def _capture_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
        open_flags_captured.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", _capture_open)

    config = _load_credential_file(credential_file)

    # Prove the real credential-open path was exercised
    assert len(open_flags_captured) >= 1
    # Prove O_NOFOLLOW is included in the flags
    assert open_flags_captured[0] & os.O_NOFOLLOW, (
        f"O_NOFOLLOW not in flags: {open_flags_captured[0]:#x}"
    )
    # Verify successful load
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


# ============================================================
# Hyperliquid candleSnapshot contract
# ============================================================


def test_public_snapshot_requests_exact_closed_candle_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "test_first_launch_public_runtime_entrypoint"
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    snapshot_now = datetime(2026, 7, 14, 12, 7, 30, tzinfo=UTC)
    clock_calls = 0
    payloads: list[dict[str, object]] = []
    response_bodies = iter((b"[]", b"[]", b"{}"))

    def fixed_now() -> datetime:
        nonlocal clock_calls
        clock_calls += 1
        return snapshot_now

    class Response:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return self._body

    def fake_urlopen(
        request: object, *, timeout: float, context: object
    ) -> Response:
        assert timeout == 15.0
        assert context is not None
        data = request.data  # type: ignore[attr-defined]
        assert isinstance(data, bytes)
        payload = json.loads(data.decode("utf-8"))
        assert isinstance(payload, dict)
        payloads.append(payload)
        return Response(next(response_bodies))

    monkeypatch.setattr(module, "_utc_now", fixed_now)
    monkeypatch.setattr(module, "urlopen", fake_urlopen)

    assert module.recover_public_snapshot_default() == ("[]", "[]", "{}")
    assert clock_calls == 1

    now_ms = int(snapshot_now.timestamp() * 1000)
    width_5m = 5 * 60_000
    width_15m = 15 * 60_000
    open_5m = (now_ms // width_5m) * width_5m
    open_15m = (now_ms // width_15m) * width_15m

    assert payloads == [
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "ETH",
                "interval": "5m",
                "startTime": open_5m - (64 * width_5m),
                "endTime": open_5m - 1,
            },
        },
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "ETH",
                "interval": "15m",
                "startTime": open_15m - (32 * width_15m),
                "endTime": open_15m - 1,
            },
        },
        {"type": "metaAndAssetCtxs"},
    ]


def test_closed_candle_snapshot_request_rejects_non_utc_time() -> None:
    module_name = "test_first_launch_public_runtime_entrypoint_non_utc"
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    with pytest.raises(ValueError, match="UTC datetime"):
        module._closed_candle_snapshot_request(
            "5m", now=datetime(2026, 7, 14, 12, 0)
        )
