"""HTTPS webhook outbox tests for the restricted public runtime.

Covers Section 16 category G (Notification):
- HTTPS-only configuration (http:// rejected);
- stable Idempotency-Key header (equals notification_id);
- 2xx response -> DELIVERED (durable, no resend);
- timeout / 5xx / 408 / 429 -> PENDING (retryable);
- non-retryable 4xx -> FAILED_CONFIGURATION (terminal);
- no resend after durable success;
- persist-before-send: the dispatcher reads pending rows, never creates them.
"""

from __future__ import annotations

import email.message
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.first_launch.configuration import RiskConfiguration
from trader_assist_v0.runtime.first_launch_notification import (
    HttpResponse,
    NotificationConfig,
    NotificationConfigError,
    NotificationDeliveryError,
    NotificationDispatcher,
    _classify_response,
    _headers_for,
    encode_payload,
)
from trader_assist_v0.runtime.first_launch_public_runtime import (
    RestrictedPublicRuntimeConfig,
)
from trader_assist_v0.runtime.first_launch_runtime_store import (
    NotificationOutboxRecord,
    RuntimeStore,
)

NOW = datetime(2026, 7, 14, tzinfo=UTC)
_VALID_PLAN_ID = "a" * 64
_VALID_NOTIFICATION_ID = "b" * 64
_VALID_SIGNAL_ID = "c" * 64
_VALID_SHADOW_ORDER_ID = "d" * 64
_VALID_BUNDLE_HASH = "e" * 64
_VALID_CARD_ID = "f" * 64


def _open_store(tmp_path: Path) -> RuntimeStore:
    return RuntimeStore.open(tmp_path / "test_notification.db")


def _insert_session(store: RuntimeStore, *, session_id: str = "session-1") -> str:
    store.record_runtime_session(
        session_id=session_id,
        runtime_mode="RESTRICTED_PUBLIC_LIVE_SHADOW",
        scope="ETH_ONLY",
        process_start_time=NOW,
        configuration_hash=None,
        database_path=Path("/tmp/test.db"),
        manual_only_authority=True,
        not_submitted_authority=True,
        now=NOW,
    )
    return session_id


def _insert_publication_and_notification(
    store: RuntimeStore,
    *,
    session_id: str = "session-1",
    plan_id: str = _VALID_PLAN_ID,
    notification_id: str = _VALID_NOTIFICATION_ID,
    signal_id: str = _VALID_SIGNAL_ID,
    shadow_order_id: str = _VALID_SHADOW_ORDER_ID,
    status: str = "PENDING",
    payload: dict[str, object] | None = None,
) -> NotificationOutboxRecord:
    """Directly insert a publication bundle and notification outbox row.

    This bypasses the full strategy chain to isolate notification behavior.
    The publication bundle is required because notification_outbox has a
    FOREIGN KEY on plan_id referencing publication_bundles.
    """
    if payload is None:
        payload = {"notification_id": notification_id, "plan_id": plan_id}
    payload_json = json.dumps(payload, separators=(",", ":"))
    bundle_payload_json = json.dumps({"signal_id": signal_id}, separators=(",", ":"))
    created_at = NOW.isoformat()
    store._connection.execute(
        "INSERT INTO publication_bundles "
        "(signal_id, plan_id, shadow_order_id, notification_id, session_id, "
        "strategy_output_setup_id, volatility_snapshot_hash, overlay_decision_hash, "
        "trade_plan_canonical_hash, operator_review_card_id, bundle_canonical_hash, "
        "strategy_output_evidence_json, volatility_snapshot_json, overlay_decision_json, "
        "trade_plan_json, operator_review_card_json, shadow_order_json, "
        "notification_payload_json, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            signal_id,
            plan_id,
            shadow_order_id,
            notification_id,
            session_id,
            signal_id,
            _VALID_BUNDLE_HASH,
            _VALID_BUNDLE_HASH,
            _VALID_BUNDLE_HASH,
            _VALID_CARD_ID,
            _VALID_BUNDLE_HASH,
            bundle_payload_json,
            bundle_payload_json,
            bundle_payload_json,
            bundle_payload_json,
            bundle_payload_json,
            bundle_payload_json,
            payload_json,
            created_at,
        ),
    )
    store._connection.execute(
        "INSERT INTO notification_outbox "
        "(notification_id, plan_id, shadow_order_id, payload_json, status, "
        "idempotency_key, attempt_count, last_attempt_at, delivered_at, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)",
        (
            notification_id,
            plan_id,
            shadow_order_id,
            payload_json,
            status,
            notification_id,
            0,
            created_at,
        ),
    )
    store._connection.commit()
    return store.get_notification(notification_id)


@dataclass
class _MockTransport:
    """Mock HTTPS transport that returns canned responses for testing."""

    responses: tuple[HttpResponse, ...]
    calls: list[dict[str, object]]
    raise_error: Exception | None = None

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
        if self.raise_error is not None:
            raise self.raise_error
        if not self.responses:
            raise NotificationDeliveryError("no canned response")
        return self.responses[len(self.calls) - 1]


def _config(
    *,
    url: str = "https://hooks.example.com/eth-notify",
    timeout: float = 10.0,
    auth_name: str | None = None,
    auth_value: str | None = None,
) -> NotificationConfig:
    return NotificationConfig(
        webhook_url=url,
        timeout_seconds=timeout,
        authorization_header_name=auth_name,
        authorization_header_value=auth_value,
    )


# ============================================================
# NotificationConfig validation
# ============================================================


def test_https_only_http_rejected() -> None:
    with pytest.raises(NotificationConfigError, match="HTTPS"):
        _config(url="http://hooks.example.com/notify")


def test_https_only_ftp_rejected() -> None:
    with pytest.raises(NotificationConfigError, match="HTTPS"):
        _config(url="ftp://hooks.example.com/notify")


def test_https_url_accepted() -> None:
    config = _config(url="https://hooks.example.com/notify")
    assert config.webhook_url == "https://hooks.example.com/notify"


def test_empty_url_rejected() -> None:
    with pytest.raises(NotificationConfigError):
        _config(url="")


def test_missing_host_rejected() -> None:
    with pytest.raises(NotificationConfigError):
        _config(url="https://")


def test_timeout_below_minimum_rejected() -> None:
    with pytest.raises(NotificationConfigError):
        _config(timeout=0.5)


def test_timeout_above_maximum_rejected() -> None:
    with pytest.raises(NotificationConfigError):
        _config(timeout=61.0)


def test_timeout_at_bounds_accepted() -> None:
    assert _config(timeout=1.0).timeout == 1.0
    assert _config(timeout=60.0).timeout == 60.0


def test_authorization_header_pairing_required() -> None:
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://hooks.example.com/notify",
            timeout_seconds=10.0,
            authorization_header_name="Authorization",
            authorization_header_value=None,
        )
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://hooks.example.com/notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value="Bearer token",
        )


def test_authorization_header_conflict_with_idempotency_rejected() -> None:
    with pytest.raises(NotificationConfigError, match="reserved"):
        NotificationConfig(
            webhook_url="https://hooks.example.com/notify",
            timeout_seconds=10.0,
            authorization_header_name="Idempotency-Key",
            authorization_header_value="secret",
        )


def test_authorization_header_conflict_with_content_type_rejected() -> None:
    with pytest.raises(NotificationConfigError, match="reserved"):
        NotificationConfig(
            webhook_url="https://hooks.example.com/notify",
            timeout_seconds=10.0,
            authorization_header_name="Content-Type",
            authorization_header_value="text/plain",
        )


# ============================================================
# _classify_response
# ============================================================


@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_2xx_classified_as_delivered(status_code: int) -> None:
    assert _classify_response(status_code) == "DELIVERED"


@pytest.mark.parametrize("status_code", [408, 429, 500, 502, 503, 504])
def test_retryable_status_codes_classified_as_pending(status_code: int) -> None:
    assert _classify_response(status_code) == "PENDING"


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 410, 422])
def test_non_retryable_4xx_classified_as_failed_configuration(status_code: int) -> None:
    assert _classify_response(status_code) == "FAILED_CONFIGURATION"


def test_unknown_status_classified_as_failed_configuration() -> None:
    assert _classify_response(600) == "FAILED_CONFIGURATION"


# ============================================================
# Idempotency-Key header
# ============================================================


def test_idempotency_key_equals_notification_id() -> None:
    config = _config()
    headers = _headers_for(config, _VALID_NOTIFICATION_ID)
    assert headers["Idempotency-Key"] == _VALID_NOTIFICATION_ID
    assert headers["Content-Type"] == "application/json"


def test_idempotency_key_is_stable_across_calls() -> None:
    config = _config()
    first = _headers_for(config, _VALID_NOTIFICATION_ID)
    second = _headers_for(config, _VALID_NOTIFICATION_ID)
    assert first["Idempotency-Key"] == second["Idempotency-Key"] == _VALID_NOTIFICATION_ID


def test_authorization_header_included_when_configured() -> None:
    config = _config(auth_name="Authorization", auth_value="Bearer token")
    headers = _headers_for(config, _VALID_NOTIFICATION_ID)
    assert headers["Authorization"] == "Bearer token"
    assert headers["Idempotency-Key"] == _VALID_NOTIFICATION_ID


# ============================================================
# NotificationDispatcher.dispatch_one
# ============================================================


def test_2xx_marks_delivered_and_no_resend(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=200, body=b"ok"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "DELIVERED"
        assert result.status_code == 200
        assert len(transport.calls) == 1
        # Second dispatch should not send (already DELIVERED)
        second = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert second.status == "DELIVERED"
        assert second.reason == "already-DELIVERED"
        assert len(transport.calls) == 1
    finally:
        store.close()


def test_timeout_leaves_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(),
            calls=[],
            raise_error=NotificationDeliveryError("timeout"),
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "PENDING"
        assert result.reason == "timeout"
        assert len(transport.calls) == 1
        # Still pending in store
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "PENDING"
    finally:
        store.close()


def test_5xx_leaves_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=503, body=b"unavailable"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "PENDING"
        assert result.status_code == 503
        assert result.reason == "retryable-status"
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "PENDING"
    finally:
        store.close()


def test_408_leaves_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=408, body=b"timeout"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "PENDING"
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "PENDING"
    finally:
        store.close()


def test_429_leaves_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=429, body=b"slow down"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "PENDING"
    finally:
        store.close()


def test_4xx_marks_failed_configuration_terminal(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=404, body=b"not found"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert result.status == "FAILED_CONFIGURATION"
        assert result.status_code == 404
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "FAILED_CONFIGURATION"
        # No resend for terminal failure
        second = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert second.status == "FAILED_CONFIGURATION"
        assert second.reason == "already-FAILED_CONFIGURATION"
        assert len(transport.calls) == 1
    finally:
        store.close()


def test_idempotency_key_sent_in_header(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=200, body=b"ok"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert len(transport.calls) == 1
        call = transport.calls[0]
        headers = call["headers"]
        assert headers["Idempotency-Key"] == _VALID_NOTIFICATION_ID
        assert headers["Content-Type"] == "application/json"
    finally:
        store.close()


def test_authorization_header_sent_when_configured(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=200, body=b"ok"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store,
            transport=transport,
            config=_config(auth_name="X-Api-Key", auth_value="secret-value"),
        )
        dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert len(transport.calls) == 1
        headers = transport.calls[0]["headers"]
        assert headers["X-Api-Key"] == "secret-value"
        assert headers["Idempotency-Key"] == _VALID_NOTIFICATION_ID
    finally:
        store.close()


# ============================================================
# dispatch_pending
# ============================================================


def test_dispatch_pending_delivers_all_pending(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(
            store, plan_id="1" * 64, notification_id="2" * 64, shadow_order_id="3" * 64
        )
        _insert_publication_and_notification(
            store,
            plan_id="4" * 64,
            notification_id="5" * 64,
            shadow_order_id="6" * 64,
            signal_id="7" * 64,
        )
        transport = _MockTransport(
            responses=(
                HttpResponse(status_code=200, body=b"ok"),
                HttpResponse(status_code=200, body=b"ok"),
            ),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        results = dispatcher.dispatch_pending(now=NOW)
        assert len(results) == 2
        assert all(r.status == "DELIVERED" for r in results)
        assert len(transport.calls) == 2
        assert store.list_pending_notifications() == ()
    finally:
        store.close()


def test_dispatch_pending_empty_returns_empty(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        transport = _MockTransport(responses=(), calls=[])
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        results = dispatcher.dispatch_pending(now=NOW)
        assert results == ()
        assert len(transport.calls) == 0
    finally:
        store.close()


def test_dispatch_pending_mixed_outcomes(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(
            store, plan_id="1" * 64, notification_id="2" * 64, shadow_order_id="3" * 64
        )
        _insert_publication_and_notification(
            store,
            plan_id="4" * 64,
            notification_id="5" * 64,
            shadow_order_id="6" * 64,
            signal_id="7" * 64,
        )
        transport = _MockTransport(
            responses=(
                HttpResponse(status_code=200, body=b"ok"),
                HttpResponse(status_code=503, body=b"unavailable"),
            ),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        results = dispatcher.dispatch_pending(now=NOW)
        assert len(results) == 2
        statuses = {r.status for r in results}
        assert "DELIVERED" in statuses
        assert "PENDING" in statuses
    finally:
        store.close()


# ============================================================
# encode_payload
# ============================================================


def test_encode_payload_returns_bytes(tmp_path: Path) -> None:
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        record = _insert_publication_and_notification(store)
        encoded = encode_payload(record)
        assert type(encoded) is bytes
        decoded = json.loads(encoded.decode("utf-8"))
        assert decoded["notification_id"] == _VALID_NOTIFICATION_ID
    finally:
        store.close()


def test_encode_payload_rejects_non_record() -> None:
    with pytest.raises(NotificationDeliveryError):
        encode_payload("not a record")  # type: ignore[arg-type]


# ============================================================
# Crash safety: persist-before-send
# ============================================================


def test_crash_before_send_leaves_pending(tmp_path: Path) -> None:
    """A crash during send leaves the notification PENDING.

    The store persists the notification before any send. If the transport
    raises an unhandled exception (not NotificationDeliveryError), the
    notification remains PENDING because no durable success was recorded.
    """
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(),
            calls=[],
            raise_error=RuntimeError("unexpected crash"),
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        # An unhandled exception propagates; the notification stays PENDING
        # because begin_notification_attempt already incremented attempt_count
        # but no mark_notification_delivered was called.
        with pytest.raises(RuntimeError, match="unexpected crash"):
            dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "PENDING"
        assert record.attempt_count == 1
    finally:
        store.close()


def test_attempt_count_increments_on_retry(tmp_path: Path) -> None:
    """Each retryable failure increments attempt_count."""
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(
                HttpResponse(status_code=503, body=b"unavailable"),
                HttpResponse(status_code=503, body=b"unavailable"),
                HttpResponse(status_code=200, body=b"ok"),
            ),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        first = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert first.status == "PENDING"
        assert first.attempt_count == 1
        second = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert second.status == "PENDING"
        assert second.attempt_count == 2
        third = dispatcher.dispatch_one(notification_id=_VALID_NOTIFICATION_ID, now=NOW)
        assert third.status == "DELIVERED"
        assert third.attempt_count == 3
        assert len(transport.calls) == 3
    finally:
        store.close()


# ============================================================
# GA-03: Webhook endpoint policy
# ============================================================


@pytest.mark.parametrize(
    "url",
    [
        "https://api.hyperliquid.xyz/exchange",
        "https://api.hyperliquid-testnet.xyz/exchange",
        "https://api.hyperliquid.xyz/exchange/",
        "https://api.hyperliquid-testnet.xyz/exchange/",
        "https://api.hyperliquid.xyz/exchange?foo=bar",
        "https://api.hyperliquid.xyz:443/exchange",
        "https://api.hyperliquid.xyz/path/exchange",
        "https://api.hyperliquid.xyz/exchange/sub",
        "https://api.hyperliquid.xyz/info",
        "https://api.hyperliquid.xyz/anything",
        "https://api.hyperliquid-testnet.xyz/",
    ],
)
def test_ga03_prohibited_hyperliquid_exchange_endpoints_rejected(url: str) -> None:
    """GA-03: both Hyperliquid API hosts are rejected entirely before any network call.

    The notification transport is operation-specific; both Hyperliquid API hosts
    are rejected regardless of port/path/query because any accepted configuration
    could be redirected or normalized to reach an exchange-write endpoint.
    """
    with pytest.raises(NotificationConfigError, match="Hyperliquid API host"):
        _config(url=url)


def test_ga03_url_userinfo_rejected() -> None:
    """GA-03: URL userinfo must be rejected."""
    with pytest.raises(NotificationConfigError, match="userinfo"):
        _config(url="https://user:pass@hooks.example.com/notify")


def test_ga03_malformed_host_whitespace_rejected() -> None:
    """GA-03: hosts with whitespace must be rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://hooks .example.com/notify")


def test_ga03_malformed_non_numeric_port_rejected() -> None:
    """GA-03: non-numeric port is rejected at admission."""
    with pytest.raises(NotificationConfigError, match="port"):
        _config(url="https://hooks.example.com:bad/notify")


def test_ga03_malformed_non_numeric_port_zero_network() -> None:
    """GA-03: non-numeric port: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://hooks.example.com:bad/notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_malformed_out_of_range_port_rejected() -> None:
    """GA-03: out-of-range port is rejected at admission."""
    with pytest.raises(NotificationConfigError, match="port"):
        _config(url="https://hooks.example.com:65536/notify")


def test_ga03_malformed_out_of_range_port_zero_network() -> None:
    """GA-03: out-of-range port: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://hooks.example.com:65536/notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_malformed_path_control_char_rejected() -> None:
    """GA-03: paths with control characters must be rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://hooks.example.com/notify\n")


def test_ga03_normal_https_webhook_remains_accepted() -> None:
    """GA-03: a normal HTTPS webhook must remain accepted."""
    config = _config(url="https://hooks.example.com/eth-notify")
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_ga03_no_dispatch_attempt_for_invalid_endpoint(tmp_path: Path) -> None:
    """GA-03: no outbox dispatch attempt can occur because configuration admission itself rejects.

    The endpoint is rejected at NotificationConfig construction time, before
    any dispatcher is created or any network call is attempted.  This test
    proves that the rejection happens before persistence or network access.
    """
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_case_variant_of_prohibited_target_rejected() -> None:
    """GA-03: case and trailing-dot variants of a prohibited host are rejected.

    Variants are rejected after IDNA canonicalization.
    ``urlparse`` already lowercases the parsed hostname, and the canonicalization
    re-lowercases after IDNA encoding so that uppercase or trailing-dot variants
    cannot bypass the prohibited-host list.
    """
    with pytest.raises(NotificationConfigError, match="Hyperliquid API host"):
        _config(url="https://api.hyperliquid.xyz/Exchange")
    with pytest.raises(NotificationConfigError, match="Hyperliquid API host"):
        _config(url="https://api.hyperliquid.xyz/EXCHANGE")


# ============================================================
# GA-03 required closure assertions
# ============================================================


def test_ga03_redirect_not_followed() -> None:
    """GA03_REDIRECT_NOT_FOLLOWED: ``_NoRedirectHandler.redirect_request`` returns None.

    When the redirect handler returns None, urllib's ``http_error_30x`` returns
    None and falls through to the default error handler that raises
    ``HTTPError``.  ``HttpsWebhookTransport.post`` catches ``HTTPError`` and
    converts it to an ``HttpResponse`` with the 3xx status code, which
    ``_classify_response`` then maps to ``FAILED_CONFIGURATION``.
    """
    from trader_assist_v0.runtime.first_launch_notification import _NoRedirectHandler

    handler = _NoRedirectHandler()
    headers = email.message.Message()
    headers["Location"] = "https://evil.example/redirected"
    for code in (301, 302, 303, 307, 308):
        result = handler.redirect_request(
            req=None,
            fp=None,
            code=code,
            msg="Redirect",
            headers=headers,
            newurl="https://evil.example/redirected",
        )
        assert result is None, f"redirect was followed for {code}"


def test_ga03_redirect_location_not_called() -> None:
    """GA03_REDIRECT_LOCATION_NOT_CALLED: no Request is built for the Location URL.

    Because ``_NoRedirectHandler.redirect_request`` returns None, urllib never
    constructs a new ``Request`` for the redirect target and never invokes
    ``OpenerDirector.open`` on it.  The only URL ever opened is the originally
    authorized URL.  This test monkey-patches the opener to assert that the
    Location URL is never fetched.
    """
    from trader_assist_v0.runtime.first_launch_notification import (
        _WEBHOOK_OPENER,
        HttpsWebhookTransport,
    )

    opened_urls: list[str] = []

    class _FakeResponse:
        def __init__(self, status: int, url: str) -> None:
            self.status = status
            self._url = url

        def read(self) -> bytes:
            return b""

        def geturl(self) -> str:
            return self._url

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    def fake_open(req: object, timeout: float | None = None) -> _FakeResponse:
        url = getattr(req, "full_url", str(req))
        opened_urls.append(url)
        # Return a 302 response with a Location header in the body.  The opener
        # must NOT call this for the Location URL.
        return _FakeResponse(302, url)

    original_open = _WEBHOOK_OPENER.open
    _WEBHOOK_OPENER.open = fake_open  # type: ignore[method-assign]
    try:
        transport = HttpsWebhookTransport()
        response = transport.post(
            url="https://accepted-webhook.example/notify",
            payload=b"{}",
            headers={"Content-Type": "application/json"},
            timeout=5.0,
        )
    finally:
        _WEBHOOK_OPENER.open = original_open  # type: ignore[method-assign]
    assert response.status_code == 302
    # The Location URL must never have been opened.
    assert opened_urls == ["https://accepted-webhook.example/notify"]
    assert all("evil" not in url for url in opened_urls)


def test_ga03_encoded_exchange_zero_network() -> None:
    """GA03_ENCODED_EXCHANGE_ZERO_NETWORK: percent-encoded ``/exchange`` is rejected at admission.

    ``https://api.hyperliquid.xyz/%65xchange`` percent-decodes once to
    ``/exchange``, but the host ``api.hyperliquid.xyz`` is rejected entirely
    at configuration admission.  No dispatcher, no transport and no network
    call is constructed for this URL.
    """
    with pytest.raises(NotificationConfigError, match="Hyperliquid API host"):
        _config(url="https://api.hyperliquid.xyz/%65xchange")


def test_ga03_double_encoded_path_rejected() -> None:
    """GA03_DOUBLE_ENCODED_PATH_REJECTED: ``%2565`` decodes once to ``%65``.

    ``%65`` is still a percent escape.
    A path that contains a double-encoded percent escape must be rejected at
    configuration admission, even when the host itself is not prohibited.
    """
    with pytest.raises(NotificationConfigError, match="double percent encoding"):
        _config(url="https://accepted.example/%2565xchange")


@pytest.mark.parametrize(
    "url",
    [
        "https://api.hyperliquid.xyz/exchange",
        "https://API.HYPERLIQUID.XYZ/exchange",
        "https://api.HYPERLIQUID.xyz/exchange",
        "https://api.hyperliquid-testnet.xyz/exchange",
    ],
)
def test_ga03_canonical_host_variants_rejected(url: str) -> None:
    """GA03_CANONICAL_HOST_VARIANTS_REJECTED.

    Case variants are rejected after IDNA canonicalization.
    """
    with pytest.raises(NotificationConfigError, match="Hyperliquid API host"):
        _config(url=url)


@pytest.mark.parametrize(
    "url",
    [
        "https://API.HYPERLIQUID.XYZ./exchange",
        "https://api.hyperliquid.xyz./exchange",
        "https://API.HYPERLIQUID-TESTNET.XYZ./exchange",
    ],
)
def test_ga03_trailing_dot_variants_rejected_at_validation(url: str) -> None:
    """Trailing-dot FQDN forms are rejected at post-IDNA validation.

    The terminal dot is not stripped and then accepted; the hostname is
    rejected as malformed before any prohibited-host comparison.
    """
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url=url)


# ============================================================
# GA-03: Post-IDNA Unicode separator bypass (U+3002, U+FF0E, U+FF61)
# ============================================================


def test_ga03_u3002_ideographic_full_stop_rejected() -> None:
    """U+3002 IDEOGRAPHIC FULL STOP separator is rejected at admission.

    ``https://api.hyperliquid.xyz。/exchange`` — the U+3002 separator is
    converted to an ASCII dot by IDNA, producing a trailing-dot hostname that
    is rejected by post-IDNA validation before any prohibited-host comparison.
    """
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid.xyz\u3002/exchange")


def test_ga03_u3002_zero_network() -> None:
    """U+3002 separator: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz\u3002/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_uff0e_fullwidth_full_stop_rejected() -> None:
    """U+FF0E FULLWIDTH FULL STOP separator is rejected at admission."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid.xyz\uff0e/exchange")


def test_ga03_uff0e_zero_network() -> None:
    """U+FF0E separator: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz\uff0e/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_uff61_halfwidth_ideographic_full_stop_rejected() -> None:
    """U+FF61 HALFWIDTH IDEOGRAPHIC FULL STOP separator is rejected at admission."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid.xyz\uff61/exchange")


def test_ga03_uff61_zero_network() -> None:
    """U+FF61 separator: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz\uff61/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_uppercase_plus_u3002_rejected() -> None:
    """Uppercase hostname plus U+3002 separator is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://API.HYPERLIQUID.XYZ\u3002/exchange")


def test_ga03_uppercase_plus_u3002_zero_network() -> None:
    """Uppercase + U+3002: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://API.HYPERLIQUID.XYZ\u3002/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_testnet_plus_u3002_rejected() -> None:
    """Testnet hostname plus U+3002 separator is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid-testnet.xyz\u3002/exchange")


def test_ga03_testnet_plus_u3002_zero_network() -> None:
    """Testnet + U+3002: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid-testnet.xyz\u3002/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_u3002_with_explicit_port_rejected() -> None:
    """U+3002 separator plus explicit port is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid.xyz\u3002:443/exchange")


def test_ga03_u3002_with_port_zero_network() -> None:
    """U+3002 + explicit port: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz\u3002:443/exchange",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_u3002_with_path_and_query_rejected() -> None:
    """U+3002 separator plus path and query is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://api.hyperliquid.xyz\u3002/exchange?x=1")


def test_ga03_u3002_with_path_and_query_zero_network() -> None:
    """U+3002 + path/query: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://api.hyperliquid.xyz\u3002/exchange?x=1",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


# ============================================================
# Post-IDNA hostname structural validation
# ============================================================


def test_ga03_leading_dot_rejected() -> None:
    """Leading ASCII dot hostname is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://.example.com/notify")


def test_ga03_leading_dot_zero_network() -> None:
    """Leading dot: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://.example.com/notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_consecutive_dots_rejected() -> None:
    """Consecutive ASCII dots in hostname are rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://example..com/notify")


def test_ga03_consecutive_dots_zero_network() -> None:
    """Consecutive dots: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://example..com/notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_terminal_dot_rejected() -> None:
    """Terminal ASCII dot FQDN form is rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://example.com./notify")


def test_ga03_terminal_dot_zero_network() -> None:
    """Terminal dot: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://example.com./notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


def test_ga03_multiple_terminal_dots_rejected() -> None:
    """Multiple terminal ASCII dots are rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://example.com../notify")


def test_ga03_multiple_terminal_dots_zero_network() -> None:
    """Multiple terminal dots: no network call is attempted."""
    with pytest.raises(NotificationConfigError):
        NotificationConfig(
            webhook_url="https://example.com../notify",
            timeout_seconds=10.0,
            authorization_header_name=None,
            authorization_header_value=None,
        )


# ============================================================
# Legitimate webhook remains accepted
# ============================================================


def test_ga03_legitimate_webhook_remains_accepted() -> None:
    """Legitimate webhook ``https://hooks.example.com/notify`` is accepted."""
    config = _config(url="https://hooks.example.com/notify")
    assert config.webhook_url == "https://hooks.example.com/notify"


def test_outbox_delivered_on_redirect_false(tmp_path: Path) -> None:
    """OUTBOX_DELIVERED_ON_REDIRECT_FALSE.

    A 302 redirect response must NOT mark the outbox as DELIVERED.
    The mock transport returns a 302 response.  ``_classify_response`` maps 302
    to ``FAILED_CONFIGURATION``, so the dispatcher marks the outbox row as
    ``FAILED_CONFIGURATION``, never as ``DELIVERED``.
    """
    store = _open_store(tmp_path)
    try:
        _insert_session(store)
        _insert_publication_and_notification(store)
        transport = _MockTransport(
            responses=(HttpResponse(status_code=302, body=b"redirect"),),
            calls=[],
        )
        dispatcher = NotificationDispatcher(
            store=store, transport=transport, config=_config()
        )
        result = dispatcher.dispatch_one(
            notification_id=_VALID_NOTIFICATION_ID, now=NOW
        )
        assert result.status == "FAILED_CONFIGURATION"
        assert result.status_code == 302
        record = store.get_notification(_VALID_NOTIFICATION_ID)
        assert record.status == "FAILED_CONFIGURATION"
        assert record.status != "DELIVERED"
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Credential representation tests
# ---------------------------------------------------------------------------

_SECRET_URL = "https://hooks.example.com/secret-webhook-path?key=secret-token"
_SECRET_HEADER_NAME = "X-Api-Key"
_SECRET_HEADER_VALUE = "sk-1234567890abcdef"


def _make_config() -> NotificationConfig:
    return NotificationConfig(
        webhook_url=_SECRET_URL,
        timeout_seconds=10.0,
        authorization_header_name=_SECRET_HEADER_NAME,
        authorization_header_value=_SECRET_HEADER_VALUE,
    )


def _make_risk_configuration() -> RiskConfiguration:
    return RiskConfiguration.from_json(
        json.dumps({
            "CONFIGURATION_VERSION": "r3.0",
            "ACCOUNT_EQUITY_USD": "1000.00",
            "RISK_PER_TRADE_PCT": "0.5000",
            "MAX_NOTIONAL_USD": None,
        })
    )


def test_repr_notification_config_does_not_leak_webhook_url() -> None:
    """repr(NotificationConfig) must not contain the complete webhook URL."""
    config = _make_config()
    r = repr(config)
    assert _SECRET_URL not in r


def test_repr_notification_config_does_not_leak_secret_path() -> None:
    """repr(NotificationConfig) must not contain the secret-bearing path."""
    config = _make_config()
    r = repr(config)
    assert "secret-webhook-path" not in r


def test_repr_notification_config_does_not_leak_secret_query() -> None:
    """repr(NotificationConfig) must not contain the secret-bearing query."""
    config = _make_config()
    r = repr(config)
    assert "secret-token" not in r


def test_repr_notification_config_does_not_leak_auth_header_name() -> None:
    """repr(NotificationConfig) must not contain the authorization header name."""
    config = _make_config()
    r = repr(config)
    assert _SECRET_HEADER_NAME not in r


def test_repr_notification_config_does_not_leak_auth_header_value() -> None:
    """repr(NotificationConfig) must not contain the authorization header value."""
    config = _make_config()
    r = repr(config)
    assert _SECRET_HEADER_VALUE not in r


def test_repr_notification_dispatcher_does_not_leak_credentials(tmp_path: Path) -> None:
    """repr(NotificationDispatcher) must not leak credential values."""
    store = _open_store(tmp_path)
    try:
        dispatcher = NotificationDispatcher(
            store=store,
            transport=_MockTransport(responses=(), calls=[]),
            config=_make_config(),
        )
        r = repr(dispatcher)
        assert _SECRET_URL not in r
        assert "secret-webhook-path" not in r
        assert "secret-token" not in r
        assert _SECRET_HEADER_NAME not in r
        assert _SECRET_HEADER_VALUE not in r
    finally:
        store.close()


def test_repr_restricted_public_runtime_config_does_not_leak_credentials() -> None:
    """repr(RestrictedPublicRuntimeConfig) must not leak credential values."""
    runtime_config = RestrictedPublicRuntimeConfig(
        database_path=Path("/tmp/runtime.db"),
        risk_configuration=_make_risk_configuration(),
        notification_config=_make_config(),
        acknowledgement_timeout_seconds=30.0,
        session_timeout_seconds=3600.0,
    )
    r = repr(runtime_config)
    assert _SECRET_URL not in r
    assert "secret-webhook-path" not in r
    assert "secret-token" not in r
    assert _SECRET_HEADER_NAME not in r
    assert _SECRET_HEADER_VALUE not in r
