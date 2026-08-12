"""Thin webhook delivery adapter and bounded retry state machine.

The transport is injected.  This module does not construct an HTTP client or
read a URL from configuration, so it cannot perform a real network send by
itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from .models import ClaimedOutboxMessage, DeliveryState, DeliveryTransition, MessageEnvelope
from .outbox import OutboxPort


class WebhookDeliveryError(RuntimeError):
    """A transport failure whose details must not be persisted or rendered."""


@dataclass(frozen=True)
class WebhookResponse:
    status_code: int


class WebhookPort(Protocol):
    def post(
        self, *, url: str, payload: bytes, headers: dict[str, str], timeout_seconds: float
    ) -> WebhookResponse:
        ...


@dataclass(frozen=True)
class WebhookConfig:
    """Externally supplied destination; URL and auth value are never rendered."""

    url: str = field(repr=False)
    timeout_seconds: float = 10.0
    authorization_header_name: str | None = field(default=None, repr=False)
    authorization_header_value: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.url) is not str or not self.url.startswith("https://"):
            raise ValueError("webhook URL must be externally supplied HTTPS")
        if not 1 <= self.timeout_seconds <= 60:
            raise ValueError("webhook timeout must be between 1 and 60 seconds")
        if (self.authorization_header_name is None) != (self.authorization_header_value is None):
            raise ValueError("webhook authorization header must be supplied as a pair")


class WebhookDeliveryAdapter:
    """Serializes an envelope for an injected webhook client."""

    def __init__(self, *, client: WebhookPort, config: WebhookConfig) -> None:
        self._client = client
        self._config = config

    def deliver(self, envelope: MessageEnvelope) -> WebhookResponse:
        payload = json.dumps(
            {"content": envelope.content},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._config.authorization_header_name is not None:
            headers[self._config.authorization_header_name] = (
                self._config.authorization_header_value or ""
            )
        return self._client.post(
            url=self._config.url,
            payload=payload,
            headers=headers,
            timeout_seconds=self._config.timeout_seconds,
        )


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 30
    max_delay_seconds: int = 900

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.base_delay_seconds < 1 or self.max_delay_seconds < 1:
            raise ValueError("retry policy values must be positive")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise ValueError("retry base delay cannot exceed maximum delay")

    def next_attempt_at(self, *, now: datetime, attempt_count: int) -> datetime:
        if now.tzinfo is not UTC or attempt_count < 1:
            raise ValueError("retry timing requires UTC and positive attempt count")
        delay = min(self.base_delay_seconds * (2 ** (attempt_count - 1)), self.max_delay_seconds)
        return now + timedelta(seconds=delay)


@dataclass(frozen=True)
class DeliveryResult:
    idempotency_key: str
    transition: DeliveryTransition


class OutboxDispatcher:
    """Applies delivery classification to durable claims supplied by ``OutboxPort``."""

    def __init__(
        self,
        *,
        outbox: OutboxPort,
        adapter: WebhookDeliveryAdapter,
        retry_policy: RetryPolicy | None = None,
        lease_seconds: int = 60,
    ) -> None:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        self._outbox = outbox
        self._adapter = adapter
        self._retry_policy = retry_policy or RetryPolicy()
        self._lease_seconds = lease_seconds

    def _retry_or_fail(
        self, item: ClaimedOutboxMessage, now: datetime, reason: str
    ) -> DeliveryTransition:
        if item.attempt_count >= self._retry_policy.max_attempts:
            return DeliveryTransition(
                state=DeliveryState.PERMANENT_FAILURE,
                reason="retry-exhausted",
                completed_at=now,
            )
        return DeliveryTransition(
            state=DeliveryState.PENDING,
            reason=reason,
            completed_at=now,
            next_attempt_at=self._retry_policy.next_attempt_at(
                now=now, attempt_count=item.attempt_count
            ),
        )

    def _transition(self, item: ClaimedOutboxMessage, now: datetime) -> DeliveryTransition:
        try:
            response = self._adapter.deliver(item.envelope)
        except WebhookDeliveryError:
            return self._retry_or_fail(item, now, "transport-error")
        status = response.status_code
        if 200 <= status < 300:
            return DeliveryTransition(
                state=DeliveryState.DELIVERED,
                reason="2xx",
                completed_at=now,
                response_status=status,
            )
        if status in {408, 429} or 500 <= status < 600:
            return self._retry_or_fail(item, now, "retryable-status")
        return DeliveryTransition(
            state=DeliveryState.PERMANENT_FAILURE,
            reason="permanent-status",
            completed_at=now,
            response_status=status,
        )

    def dispatch_due(self, *, now: datetime, limit: int = 100) -> tuple[DeliveryResult, ...]:
        if now.tzinfo is not UTC or limit < 1:
            raise ValueError("dispatch requires UTC and positive limit")
        results: list[DeliveryResult] = []
        for item in self._outbox.claim_due(now=now, limit=limit, lease_seconds=self._lease_seconds):
            transition = self._transition(item, now)
            self._outbox.complete(claim_token=item.claim_token, transition=transition)
            results.append(DeliveryResult(item.envelope.idempotency_key, transition))
        return tuple(results)
