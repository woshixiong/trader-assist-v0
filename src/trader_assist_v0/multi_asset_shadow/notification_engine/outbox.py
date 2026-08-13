"""Persistence seam for the Evidence lane's durable notification outbox."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import (
    ClaimedOutboxMessage,
    DeliveryTransition,
    EnqueueReceipt,
    MessageEnvelope,
    NotificationContractError,
    NotificationKind,
)


class OutboxPort(Protocol):
    """Durable outbox contract; implementations must atomically enforce these rules.

    ``enqueue`` performs insert-or-coalesce using ``idempotency_key``.  ``claim_due``
    atomically increments the attempt count and leases eligible pending rows; it must
    reclaim expired leases after a process restart. ``complete`` applies only when
    the supplied claim token still owns the row, so a stale worker cannot overwrite a
    later attempt. This package intentionally provides no persistence implementation.
    """

    def enqueue(self, envelope: MessageEnvelope) -> EnqueueReceipt:
        ...

    def claim_due(
        self, *, now: datetime, limit: int, lease_seconds: int
    ) -> tuple[ClaimedOutboxMessage, ...]:
        ...

    def complete(self, *, claim_token: str, transition: DeliveryTransition) -> None:
        ...


class NotificationPublisher:
    """Creates canonical envelopes and delegates atomic de-duplication to the outbox."""

    def __init__(self, outbox: OutboxPort) -> None:
        self._outbox = outbox

    def publish(self, envelope: MessageEnvelope) -> EnqueueReceipt:
        if envelope.kind is NotificationKind.FORMAL_SIGNAL:
            raise NotificationContractError(
                "FORMAL_SIGNAL must be published by EvidenceStore.publish_formal_bundle"
            )
        return self._outbox.enqueue(envelope)
