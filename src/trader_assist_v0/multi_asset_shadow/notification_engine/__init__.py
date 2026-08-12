"""Formal Signal notification domain and thin delivery boundary."""

from .delivery import (
    DeliveryResult,
    OutboxDispatcher,
    RetryPolicy,
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookDeliveryError,
    WebhookPort,
    WebhookResponse,
)
from .formatting import build_envelope, format_notification, idempotency_key
from .models import (
    ClaimedOutboxMessage,
    DeliveryState,
    DeliveryTransition,
    EnqueueReceipt,
    MessageEnvelope,
    NotificationContractError,
    NotificationKind,
    SignalNotificationView,
)
from .outbox import NotificationPublisher, OutboxPort

__all__ = [
    "ClaimedOutboxMessage",
    "DeliveryResult",
    "DeliveryState",
    "DeliveryTransition",
    "EnqueueReceipt",
    "MessageEnvelope",
    "NotificationContractError",
    "NotificationKind",
    "NotificationPublisher",
    "OutboxDispatcher",
    "OutboxPort",
    "RetryPolicy",
    "SignalNotificationView",
    "WebhookConfig",
    "WebhookDeliveryAdapter",
    "WebhookDeliveryError",
    "WebhookPort",
    "WebhookResponse",
    "build_envelope",
    "format_notification",
    "idempotency_key",
]
