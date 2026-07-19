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

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.runtime.first_launch_notification import (
    HttpResponse,
    NotificationConfig,
    NotificationDispatcher,
)
from trader_assist_v0.runtime.first_launch_operator_assist import (
    REQUIRED_PUBLIC_SUBSCRIPTIONS,
)
from trader_assist_v0.runtime.first_launch_public_runtime import (
    RestrictedPublicRuntime,
    RestrictedPublicRuntimeConfig,
    RuntimeHealthState,
    RuntimeNotActivatedError,
    RuntimeShutdownError,
)
from trader_assist_v0.runtime.first_launch_runtime_store import RuntimeStore

NOW = datetime(2026, 7, 14, tzinfo=UTC)
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_first_launch_public_runtime.py"


def _utc_now() -> datetime:
    return NOW


def _monotonic_now() -> float:
    return 0.0


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
        "T": open_time + width,
        "o": open_price,
        "h": high,
        "l": low,
        "c": close,
        "v": volume,
        "n": 0,
    }


def _snapshot_json(candles: list[dict[str, object]]) -> str:
    return json.dumps(candles, separators=(",", ":"))


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


def test_accept_public_frame_before_warmup_rejected(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        runtime.activate(now=NOW)
        with pytest.raises(RuntimeNotActivatedError):
            runtime.accept_public_frame(frame_text=_context_frame(), now=NOW)
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


def test_reconnect_budget_exhausted_returns_none(tmp_path: Path) -> None:
    runtime, store, _, _ = _make_runtime(tmp_path)
    try:
        _warmup_to_active(runtime, now=NOW)
        _recover_to_ready(runtime, now=NOW)
        # Exhaust all reconnect attempts
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
