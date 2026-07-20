"""Configured HTTPS webhook outbox for the restricted public First Launch runtime.

This module implements the explicitly configured HTTPS webhook transport for
the durable notification outbox. It does not own persistence: the
``RuntimeStore`` persists the notification and its pending outbox row before
any send is attempted. The dispatcher here only reads pending rows, attempts
delivery, and records the durable outcome.

The supported claim is durable local de-duplication plus stable idempotency
identity. Network-level exactly-once delivery is not claimed.

Tests must mock the HTTP transport; no real webhook is sent during this task.
"""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Literal, Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from trader_assist_v0.runtime.first_launch_runtime_store import (
    NotificationOutboxRecord,
    NotificationStatusError,
    RuntimeStore,
    RuntimeStoreError,
)

_HTTPS_SCHEME: Final[str] = "https"
_IDEMPOTENCY_HEADER: Final[str] = "Idempotency-Key"
_CONTENT_TYPE_HEADER: Final[str] = "Content-Type"
_CONTENT_TYPE_VALUE: Final[str] = "application/json"
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0
_MIN_TIMEOUT_SECONDS: Final[float] = 1.0
_MAX_TIMEOUT_SECONDS: Final[float] = 60.0
_MAX_URL_LENGTH: Final[int] = 2048
_RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({408, 429, 500, 502, 503, 504})
# GA-03: prohibited Hyperliquid exchange-write endpoint policy.
# The notification transport is operation-specific (fixed POST, fixed
# notification payload, no exchange action body).  These hosts and path
# suffixes identify Hyperliquid exchange-write endpoints that must never be
# targeted by the notification webhook, regardless of credentials.
_PROHIBITED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "api.hyperliquid.xyz",
        "api.hyperliquid-testnet.xyz",
    }
)
_PROHIBITED_PATH_SUFFIXES: Final[tuple[str, ...]] = (
    "/exchange",
    "/exchange/",
)
# Path tokens that identify a Hyperliquid exchange action endpoint under any
# recognized routing variant (query parameters are evaluated separately).
_PROHIBITED_PATH_TOKENS: Final[tuple[str, ...]] = ("exchange",)


class NotificationConfigError(ValueError):
    """Raised when notification configuration is missing or unauthorized."""


class NotificationDeliveryError(RuntimeError):
    """Raised when a delivery attempt cannot be classified."""


def _reject_prohibited_endpoint(*, parsed_url: object) -> None:
    """Reject Hyperliquid exchange-write endpoints, URL userinfo and malformed host/path.

    The notification transport is operation-specific: fixed POST, fixed notification
    payload, no configurable method, no exchange action body, no account or signing
    data.  The endpoint itself must be rejected before persistence or network access,
    independent of whether credentials are present.

    Rejects:
    - ``api.hyperliquid.xyz`` and ``api.hyperliquid-testnet.xyz`` with ``/exchange``
      or any routing variant that resolves to the exchange action path;
    - URL userinfo (``https://user:pass@host/...``), which has no legitimate role
      for a notification webhook and can hide redirect or credential injection;
    - malformed host/path (whitespace, control characters).
    """
    username = getattr(parsed_url, "username", None)
    password = getattr(parsed_url, "password", None)
    if username is not None or password is not None:
        raise NotificationConfigError("webhook URL must not carry userinfo")
    hostname = getattr(parsed_url, "hostname", None)
    if type(hostname) is not str or not hostname:
        raise NotificationConfigError("webhook URL must have a host")
    if hostname != hostname.strip().lower():
        raise NotificationConfigError("webhook URL host is malformed")
    if any(ch.isspace() or ord(ch) < 0x20 for ch in hostname):
        raise NotificationConfigError("webhook URL host is malformed")
    path = getattr(parsed_url, "path", "")
    if type(path) is not str:
        raise NotificationConfigError("webhook URL path is malformed")
    if any(ord(ch) < 0x20 for ch in path):
        raise NotificationConfigError("webhook URL path is malformed")
    normalized_host = hostname.lower()
    normalized_path = path.rstrip("/")
    if normalized_host in _PROHIBITED_HOSTS:
        # Reject the exchange action endpoint under any recognized routing,
        # including trailing slash and query-parameter variants.  A bare
        # prohibited host with a non-exchange path (e.g. ``/info``) is not
        # an exchange-write endpoint and is not blocked here; the policy is
        # operation-specific, not host-specific.
        lowered = normalized_path.lower()
        for suffix in _PROHIBITED_PATH_SUFFIXES:
            if lowered == suffix.rstrip("/") or lowered.endswith(suffix):
                raise NotificationConfigError(
                    "webhook URL must not target a Hyperliquid exchange-write endpoint"
                )
        tokens = [token for token in normalized_path.split("/") if token]
        if any(token in _PROHIBITED_PATH_TOKENS for token in tokens):
            raise NotificationConfigError(
                "webhook URL must not target a Hyperliquid exchange-write endpoint"
            )


@dataclass(frozen=True)
class NotificationConfig:
    """Explicitly configured HTTPS webhook destination.

    No URL or secret is hardcoded. The webhook URL must use HTTPS. An optional
    authorization header value may be supplied by the caller; it is never
    embedded in code, fixtures, logs, or Git history by this module.
    """

    webhook_url: str
    timeout_seconds: float
    authorization_header_name: str | None
    authorization_header_value: str | None

    def __post_init__(self) -> None:
        if type(self.webhook_url) is not str or not self.webhook_url:
            raise NotificationConfigError("webhook URL must be configured")
        if len(self.webhook_url) > _MAX_URL_LENGTH:
            raise NotificationConfigError("webhook URL exceeds the bounded length")
        # GA-03: reject control characters in the raw URL string before
        # ``urlparse`` strips them (Python's urlparse silently removes ``\n``,
        # ``\r`` and ``\t`` from URLs, which would bypass the parsed-path
        # control-character check below).
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in self.webhook_url):
            raise NotificationConfigError("webhook URL is malformed")
        parsed = urlparse(self.webhook_url)
        if parsed.scheme != _HTTPS_SCHEME:
            raise NotificationConfigError("webhook URL must use HTTPS")
        if not parsed.netloc or not parsed.hostname:
            raise NotificationConfigError("webhook URL must have a host")
        # GA-03: reject Hyperliquid exchange-write endpoints, URL userinfo,
        # and malformed host/path before persistence or network access.
        _reject_prohibited_endpoint(parsed_url=parsed)
        if (
            type(self.timeout_seconds) is not float
            and type(self.timeout_seconds) is not int
        ):
            raise NotificationConfigError("timeout must be a finite number")
        timeout = float(self.timeout_seconds)
        if not (_MIN_TIMEOUT_SECONDS <= timeout <= _MAX_TIMEOUT_SECONDS):
            raise NotificationConfigError("timeout is out of the bounded range")
        if (self.authorization_header_name is None) != (
            self.authorization_header_value is None
        ):
            raise NotificationConfigError(
                "authorization header name and value must be configured together"
            )
        if self.authorization_header_name is not None:
            if (
                type(self.authorization_header_name) is not str
                or not self.authorization_header_name
            ):
                raise NotificationConfigError("authorization header name is invalid")
            lower = self.authorization_header_name.lower()
            if lower in {f"{_IDEMPOTENCY_HEADER.lower()}", _CONTENT_TYPE_HEADER.lower()}:
                raise NotificationConfigError(
                    "authorization header name conflicts with reserved headers"
                )

    @property
    def timeout(self) -> float:
        return float(self.timeout_seconds)


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: bytes


class HttpTransport(Protocol):
    def post(
        self,
        *,
        url: str,
        payload: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResponse:
        ...


@dataclass(frozen=True)
class NotificationDeliveryResult:
    notification_id: str
    status: Literal["DELIVERED", "PENDING", "FAILED_CONFIGURATION"]
    status_code: int | None
    reason: str
    attempt_count: int


class HttpsWebhookTransport:
    """Default HTTPS webhook transport using the Python standard library."""

    def post(
        self,
        *,
        url: str,
        payload: bytes,
        headers: dict[str, str],
        timeout: float,
    ) -> HttpResponse:
        if type(url) is not str or not url:
            raise NotificationDeliveryError("URL is invalid")
        if type(payload) is not bytes:
            raise NotificationDeliveryError("payload must be bytes")
        if type(headers) is not dict:
            raise NotificationDeliveryError("headers must be a dict")
        if type(timeout) not in {int, float} or isinstance(timeout, bool):
            raise NotificationDeliveryError("timeout is invalid")
        request = Request(
            url,
            data=payload,
            method="POST",
            headers=headers,
        )
        context = ssl.create_default_context()
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                body = response.read()
                status_code = int(response.status)
        except TimeoutError as exc:
            raise NotificationDeliveryError("timeout") from exc
        except OSError as exc:
            raise NotificationDeliveryError("network error") from exc
        return HttpResponse(status_code=status_code, body=body)


def _exact_utc(value: datetime, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise RuntimeStoreError(error)
    return value


def _headers_for(
    config: NotificationConfig, notification_id: str
) -> dict[str, str]:
    headers: dict[str, str] = {
        _CONTENT_TYPE_HEADER: _CONTENT_TYPE_VALUE,
        _IDEMPOTENCY_HEADER: notification_id,
    }
    if config.authorization_header_name is not None:
        headers[config.authorization_header_name] = config.authorization_header_value  # type: ignore[assignment]
    return headers


def _classify_response(status_code: int) -> Literal["DELIVERED", "PENDING", "FAILED_CONFIGURATION"]:
    if 200 <= status_code < 300:
        return "DELIVERED"
    if status_code in _RETRYABLE_STATUS_CODES:
        return "PENDING"
    if 400 <= status_code < 500:
        return "FAILED_CONFIGURATION"
    if 500 <= status_code < 600:
        return "PENDING"
    return "FAILED_CONFIGURATION"


@dataclass
class NotificationDispatcher:
    """Coordinates the durable outbox with the configured HTTPS transport.

    The dispatcher never persists a new notification: that is the
    ``RuntimeStore``'s responsibility. The dispatcher only reads pending rows,
    attempts delivery, and records the durable outcome. A crash during a send
    leaves the row PENDING because the durable success transition is only
    applied after a 2xx response.
    """

    store: RuntimeStore
    transport: HttpTransport
    config: NotificationConfig

    def _attempt_one(
        self, record: NotificationOutboxRecord, now: datetime
    ) -> NotificationDeliveryResult:
        timestamp = _exact_utc(now, "now is not UTC")
        if record.status != "PENDING":
            return NotificationDeliveryResult(
                notification_id=record.notification_id,
                status=record.status,
                status_code=None,
                reason=f"already-{record.status}",
                attempt_count=record.attempt_count,
            )
        try:
            updated = self.store.begin_notification_attempt(
                notification_id=record.notification_id, now=timestamp
            )
        except NotificationStatusError:
            return NotificationDeliveryResult(
                notification_id=record.notification_id,
                status=record.status,
                status_code=None,
                reason="no-longer-pending",
                attempt_count=record.attempt_count,
            )
        payload = updated.payload_json.encode("utf-8")
        headers = _headers_for(self.config, updated.notification_id)
        try:
            response = self.transport.post(
                url=self.config.webhook_url,
                payload=payload,
                headers=headers,
                timeout=self.config.timeout,
            )
        except NotificationDeliveryError as exc:
            self.store.mark_notification_pending(
                notification_id=updated.notification_id, now=timestamp
            )
            return NotificationDeliveryResult(
                notification_id=updated.notification_id,
                status="PENDING",
                status_code=None,
                reason=str(exc),
                attempt_count=updated.attempt_count,
            )
        classification = _classify_response(response.status_code)
        if classification == "DELIVERED":
            delivered = self.store.mark_notification_delivered(
                notification_id=updated.notification_id, now=timestamp
            )
            return NotificationDeliveryResult(
                notification_id=delivered.notification_id,
                status="DELIVERED",
                status_code=response.status_code,
                reason="2xx",
                attempt_count=delivered.attempt_count,
            )
        if classification == "FAILED_CONFIGURATION":
            failed = self.store.mark_notification_configuration_failed(
                notification_id=updated.notification_id, now=timestamp
            )
            return NotificationDeliveryResult(
                notification_id=failed.notification_id,
                status="FAILED_CONFIGURATION",
                status_code=response.status_code,
                reason="non-retryable-client-error",
                attempt_count=failed.attempt_count,
            )
        self.store.mark_notification_pending(
            notification_id=updated.notification_id, now=timestamp
        )
        return NotificationDeliveryResult(
            notification_id=updated.notification_id,
            status="PENDING",
            status_code=response.status_code,
            reason="retryable-status",
            attempt_count=updated.attempt_count,
        )

    def dispatch_one(
        self, *, notification_id: str, now: datetime
    ) -> NotificationDeliveryResult:
        record = self.store.get_notification(notification_id)
        return self._attempt_one(record, now)

    def dispatch_pending(self, *, now: datetime) -> tuple[NotificationDeliveryResult, ...]:
        timestamp = _exact_utc(now, "now is not UTC")
        results: list[NotificationDeliveryResult] = []
        for record in self.store.list_pending_notifications():
            results.append(self._attempt_one(record, timestamp))
        return tuple(results)


def encode_payload(record: NotificationOutboxRecord) -> bytes:
    """Return the canonical JSON payload bytes for a notification outbox row."""
    if type(record) is not NotificationOutboxRecord:
        raise NotificationDeliveryError("record must be a NotificationOutboxRecord")
    try:
        json.loads(record.payload_json)
    except json.JSONDecodeError as exc:
        raise NotificationDeliveryError("payload is not valid JSON") from exc
    return record.payload_json.encode("utf-8")
