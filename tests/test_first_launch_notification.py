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

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

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
    ],
)
def test_ga03_prohibited_hyperliquid_exchange_endpoints_rejected(url: str) -> None:
    """GA-03: Hyperliquid exchange-write endpoints must be rejected before any network call."""
    with pytest.raises(NotificationConfigError, match="exchange-write endpoint"):
        _config(url=url)


def test_ga03_url_userinfo_rejected() -> None:
    """GA-03: URL userinfo must be rejected."""
    with pytest.raises(NotificationConfigError, match="userinfo"):
        _config(url="https://user:pass@hooks.example.com/notify")


def test_ga03_malformed_host_whitespace_rejected() -> None:
    """GA-03: hosts with whitespace must be rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://hooks .example.com/notify")


def test_ga03_malformed_path_control_char_rejected() -> None:
    """GA-03: paths with control characters must be rejected."""
    with pytest.raises(NotificationConfigError, match="malformed"):
        _config(url="https://hooks.example.com/notify\n")


def test_ga03_normal_https_webhook_remains_accepted() -> None:
    """GA-03: a normal HTTPS webhook must remain accepted."""
    config = _config(url="https://hooks.example.com/eth-notify")
    assert config.webhook_url == "https://hooks.example.com/eth-notify"


def test_ga03_hyperliquid_info_endpoint_remains_accepted() -> None:
    """GA-03: a Hyperliquid non-exchange endpoint (e.g. /info) is not blocked.

    The policy is operation-specific (exchange-write), not host-specific.
    """
    config = _config(url="https://api.hyperliquid.xyz/info")
    assert config.webhook_url == "https://api.hyperliquid.xyz/info"


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
    """GA-03: case-insensitive matching of the exchange path token."""
    # urlparse lowercases the scheme and host, but the path is case-sensitive.
    # The policy lowercases the path before matching, so Exchange/EXCHANGE
    # are also rejected.
    with pytest.raises(NotificationConfigError, match="exchange-write endpoint"):
        _config(url="https://api.hyperliquid.xyz/Exchange")
    with pytest.raises(NotificationConfigError, match="exchange-write endpoint"):
        _config(url="https://api.hyperliquid.xyz/EXCHANGE")
