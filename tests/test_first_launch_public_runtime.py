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
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable
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
    OperatorAssistRuntimeError,
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

    The runtime stays in a blocking non-ready state. ``accept_public_frame``
    returns ``None`` for any subsequent frame because the health state is in
    ``_BLOCKING_HEALTH_STATES``.
    """
    runtime, store, _, _ = _establish_ready(tmp_path)
    try:
        # Withdraw READY with a malformed frame
        with pytest.raises((ValueError, OperatorAssistRuntimeError)):
            runtime.accept_public_frame(frame_text="{not json", now=NOW)
        assert runtime.is_ready is False
        # A subsequent valid context frame must not produce an evaluation
        result = runtime.accept_public_frame(frame_text=_context_frame("101"), now=NOW)
        assert result is None
        pubs, outbox = _row_counts(store)
        assert pubs == 0
        assert outbox == 0
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
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        self._frames = list(frames)
        self._pos = 0
        self._disconnect_after = (
            disconnect_after if disconnect_after is not None else len(frames)
        )
        self._shutdown_event = shutdown_event
        self.sent: list[str] = []
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str | bytes:
        if self._pos >= self._disconnect_after:
            if self._shutdown_event is not None:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=30.0)
                raise ConnectionError("shutdown")
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


def _recovery_frames() -> tuple[str, str, str]:
    """Return valid snapshot recovery data for the fake recover_snapshot."""
    candles_5m = [_candle_obj(i) for i in range(64)]
    candles_15m = [_candle_obj(i, interval="15m") for i in range(20)]
    return (
        _snapshot_json(candles_5m),
        _snapshot_json(candles_15m),
        _metadata_json(),
    )


def _ack_and_context_frames() -> list[str]:
    """Return 3 ack frames + 1 context frame to reach READY."""
    acks = [_ack_frame(spec.subscription) for spec in REQUIRED_PUBLIC_SUBSCRIPTIONS]
    return [*acks, _context_frame("100")]


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
            # begin_reconnect was used (reconnect_attempt > 0)
            assert runtime._reconnect_attempt >= 1
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


def test_ga05_budget_exhaustion_exits_fail_closed(tmp_path: Path) -> None:
    """GA-05: exhausting the reconnect budget stops fail-closed (exit code 1)."""
    # Only 1 reconnect delay: first reconnect succeeds, second fails
    runtime, store, _, _ = _make_runtime_short_reconnect(
        tmp_path, reconnect_delays=(0.001,)
    )
    try:
        runtime.activate(now=NOW)
        shutdown_event = asyncio.Event()

        # First connection: 3 acks + context → READY, then disconnect
        ws1 = _FakeWebSocket(_ack_and_context_frames(), disconnect_after=4)
        # Second connection (reconnect): 3 acks + context → READY, then disconnect
        ws2 = _FakeWebSocket(_ack_and_context_frames(), disconnect_after=4)
        factory = _FakeWebSocketFactory()
        factory.enqueue(ws1)
        factory.enqueue(ws2)

        async def _test() -> None:
            exit_code = await _SCRIPT_MODULE._run_transport(
                runtime=runtime,
                recover_snapshot=_recovery_frames,
                websocket_factory=factory,
                websocket_url="wss://test",
                status=lambda msg: None,
                shutdown_event=shutdown_event,
            )
            # Budget exhausted: first reconnect used the only delay, second
            # begin_reconnect returned None → exit 1.
            assert exit_code == 1
            assert runtime.is_ready is False

        asyncio.run(_test())
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
            # Wait for disconnect + reconnect
            for _ in range(400):
                if runtime.is_ready and runtime._reconnect_attempt >= 1:
                    break
                await asyncio.sleep(0.01)
            assert runtime._reconnect_attempt >= 1
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
    _SCRIPT_MODULE.RuntimeStore = _CloseTrackingStore
    _SCRIPT_MODULE.RestrictedPublicRuntime = _ShutdownTrackingRuntime

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
        _ShutdownTrackingRuntime.__init__ = original_runtime_init  # type: ignore[assignment]
        _CloseTrackingStore.open = original_store_open  # type: ignore[assignment]


# ============================================================
# Credential file admission tests
# ============================================================


def _load_credential_file(credential_path: Path) -> object:
    """Call the entrypoint's _load_credential_file function."""
    return _SCRIPT_MODULE._load_credential_file(credential_path)


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
