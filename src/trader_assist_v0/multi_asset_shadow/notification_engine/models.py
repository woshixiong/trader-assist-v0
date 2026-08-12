"""Immutable notification contracts for the multi-asset Shadow route.

This package deliberately contains presentation and delivery-boundary models
only.  It neither decides a trade nor owns the durable outbox.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from trader_assist_v0.multi_asset_shadow.models import RegistryTier


class NotificationKind(StrEnum):
    FORMAL_SIGNAL = "FORMAL_SIGNAL"
    WATCH = "WATCH"
    RESEARCH_FAILED_BREAKOUT = "RESEARCH_FAILED_BREAKOUT"


class DeliveryState(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"


class NotificationContractError(ValueError):
    """Raised when a notification view would overstate its authority."""


def _non_empty(value: str, field: str) -> None:
    if type(value) is not str or not value.strip():
        raise NotificationContractError(f"{field} must be non-empty")


def _utc(value: datetime, field: str) -> None:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise NotificationContractError(f"{field} must be an exact UTC datetime")


def _price(value: Decimal | None, field: str, *, required: bool) -> None:
    if value is None and not required:
        return
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise NotificationContractError(f"{field} must be a positive finite Decimal")


@dataclass(frozen=True)
class SignalNotificationView:
    """The small, immutable projection needed by a human manual trader.

    ``FORMAL_SIGNAL`` carries a reviewed plan projection but is always marked
    ``NOT_SUBMITTED``. ``WATCH`` and research evidence are explicitly barred
    from carrying actionable entry/stop/target values.
    """

    kind: NotificationKind
    market_display: str
    tier: RegistryTier
    setup_family: str
    setup_mode: str
    side: str | None
    signal_time: datetime
    planned_entry: Decimal | None
    stop: Decimal | None
    tp1: Decimal | None
    tp2: Decimal | None
    entry_quality: str | None
    htf_relation: str
    zone_context: str
    reference_risk_sizing: str
    liquidity_attribution: str
    strategy_version: str
    parameter_version: str
    signal_id: str
    shadow_order_id: str | None = None
    session_warning: str | None = None
    submission_status: str = "NOT_SUBMITTED"

    def __post_init__(self) -> None:
        for field in (
            "market_display",
            "setup_family",
            "setup_mode",
            "htf_relation",
            "zone_context",
            "reference_risk_sizing",
            "liquidity_attribution",
            "strategy_version",
            "parameter_version",
            "signal_id",
        ):
            _non_empty(getattr(self, field), field)
        _utc(self.signal_time, "signal_time")
        if self.submission_status != "NOT_SUBMITTED":
            raise NotificationContractError("notification submission status must be NOT_SUBMITTED")
        if self.shadow_order_id is not None:
            _non_empty(self.shadow_order_id, "shadow_order_id")
        if self.session_warning is not None:
            _non_empty(self.session_warning, "session_warning")
        if self.kind is NotificationKind.FORMAL_SIGNAL:
            _non_empty(self.side or "", "side")
            _non_empty(self.entry_quality or "", "entry_quality")
            for field in ("planned_entry", "stop", "tp1"):
                _price(getattr(self, field), field, required=True)
            _price(self.tp2, "tp2", required=False)
            return
        if any(value is not None for value in (self.planned_entry, self.stop, self.tp1, self.tp2)):
            raise NotificationContractError(
                "non-formal notifications cannot carry actionable prices"
            )
        if self.entry_quality is not None or self.side is not None:
            raise NotificationContractError(
                "non-formal notifications cannot carry side or entry quality"
            )


@dataclass(frozen=True)
class MessageEnvelope:
    """Stable outbox payload; persistence is supplied by the Evidence lane."""

    schema_version: str
    kind: NotificationKind
    idempotency_key: str
    content: str
    created_at: datetime

    def __post_init__(self) -> None:
        _non_empty(self.schema_version, "schema_version")
        _non_empty(self.idempotency_key, "idempotency_key")
        _non_empty(self.content, "content")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True)
class EnqueueReceipt:
    """Result of atomic outbox insert-or-coalesce by idempotency key."""

    envelope: MessageEnvelope
    coalesced: bool


@dataclass(frozen=True)
class ClaimedOutboxMessage:
    """A durable claim. ``claim_token`` prevents stale workers from completing it."""

    envelope: MessageEnvelope
    attempt_count: int
    claim_token: str

    def __post_init__(self) -> None:
        if self.attempt_count < 1:
            raise NotificationContractError("claimed attempt_count must be positive")
        _non_empty(self.claim_token, "claim_token")


@dataclass(frozen=True)
class DeliveryTransition:
    """The only state-machine result the persistence adapter needs to apply."""

    state: DeliveryState
    reason: str
    completed_at: datetime
    response_status: int | None = None
    next_attempt_at: datetime | None = None

    def __post_init__(self) -> None:
        _non_empty(self.reason, "reason")
        _utc(self.completed_at, "completed_at")
        if self.state is DeliveryState.PENDING:
            if self.next_attempt_at is None:
                raise NotificationContractError("pending transition requires next_attempt_at")
            _utc(self.next_attempt_at, "next_attempt_at")
        elif self.next_attempt_at is not None:
            raise NotificationContractError("terminal transition cannot carry next_attempt_at")
