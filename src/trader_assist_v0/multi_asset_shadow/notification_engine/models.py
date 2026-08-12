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
    WATCH_NEW_MARKET = "WATCH_NEW_MARKET"
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


def _finite_decimal(value: Decimal, field: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise NotificationContractError(f"{field} must be a finite Decimal")


_SETUP_FAMILIES = frozenset({"SWEEP_RECLAIM", "BREAKOUT_RETEST", "RANGE_EDGE_REJECTION"})
_BREAKOUT_MODES = frozenset({"MICRO_FAST", "STANDARD"})
_DIRECTIONAL_SIDES = frozenset({"LONG", "SHORT"})


@dataclass(frozen=True)
class SignalNotificationView:
    """The small, immutable projection needed by a human manual trader.

    ``FORMAL_SIGNAL`` carries a reviewed plan projection but is always marked
    ``NOT_SUBMITTED``. Scanner observations use ``ScannerWatchNotificationView``
    so they cannot acquire plan fields by accident.
    """

    kind: NotificationKind
    market_display: str
    tier: RegistryTier
    setup_family: str
    setup_mode: str | None
    side: str
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
        if self.kind is not NotificationKind.FORMAL_SIGNAL:
            raise NotificationContractError("SignalNotificationView is only for FORMAL_SIGNAL")
        if self.setup_family not in _SETUP_FAMILIES:
            raise NotificationContractError("setup_family is not an approved formal family")
        if self.setup_family == "BREAKOUT_RETEST":
            if self.setup_mode not in _BREAKOUT_MODES:
                raise NotificationContractError(
                    "BREAKOUT_RETEST requires an approved breakout mode"
                )
        elif self.setup_mode is not None:
            raise NotificationContractError("non-breakout setups cannot carry a breakout mode")
        if self.side not in _DIRECTIONAL_SIDES:
            raise NotificationContractError("formal signal side must be LONG or SHORT")
        if self.submission_status != "NOT_SUBMITTED":
            raise NotificationContractError("notification submission status must be NOT_SUBMITTED")
        if self.shadow_order_id is not None:
            _non_empty(self.shadow_order_id, "shadow_order_id")
        if self.session_warning is not None:
            _non_empty(self.session_warning, "session_warning")
        _non_empty(self.entry_quality or "", "entry_quality")
        for field in ("planned_entry", "stop", "tp1"):
            _price(getattr(self, field), field, required=True)
        _price(self.tp2, "tp2", required=False)


@dataclass(frozen=True)
class ScannerWatchNotificationView:
    """Immutable scanner-only observation with no trade-plan fields.

    A directional ``WATCH`` must name ``LONG`` or ``SHORT``. A
    ``WATCH_NEW_MARKET`` may omit a direction while the scanner is still
    establishing a candidate. The distinct shape prevents watch messages from
    ever carrying a planned entry, risk control, target, or order reference.
    """

    kind: NotificationKind
    market_display: str
    tier: RegistryTier
    side: str | None
    observation_time: datetime
    return_15m: Decimal
    return_30m: Decimal
    return_60m: Decimal
    rank: int
    move_atr: Decimal
    relative_volume: Decimal
    prior_level: str
    distance_to_level: Decimal
    liquidity_summary: str
    scanner_r3_state: str
    session: str
    scanner_parameter_version: str
    watch_id: str
    do_not_chase: bool = False

    def __post_init__(self) -> None:
        if self.kind not in {NotificationKind.WATCH, NotificationKind.WATCH_NEW_MARKET}:
            raise NotificationContractError("ScannerWatchNotificationView requires a watch kind")
        for field in (
            "market_display",
            "prior_level",
            "liquidity_summary",
            "scanner_r3_state",
            "session",
            "scanner_parameter_version",
            "watch_id",
        ):
            _non_empty(getattr(self, field), field)
        _utc(self.observation_time, "observation_time")
        for field in (
            "return_15m",
            "return_30m",
            "return_60m",
            "move_atr",
            "relative_volume",
            "distance_to_level",
        ):
            _finite_decimal(getattr(self, field), field)
        if type(self.rank) is not int or self.rank < 1:
            raise NotificationContractError("rank must be a positive integer")
        if self.kind is NotificationKind.WATCH and self.side not in _DIRECTIONAL_SIDES:
            raise NotificationContractError("directional WATCH side must be LONG or SHORT")
        if self.kind is NotificationKind.WATCH_NEW_MARKET and self.side is not None:
            if self.side not in _DIRECTIONAL_SIDES:
                raise NotificationContractError(
                    "WATCH_NEW_MARKET side must be LONG, SHORT, or absent"
                )
        if type(self.do_not_chase) is not bool:
            raise NotificationContractError("do_not_chase must be bool")


@dataclass(frozen=True)
class ResearchNotificationView:
    """Non-actionable failed-breakout evidence with no plan or order fields."""

    kind: NotificationKind
    market_display: str
    tier: RegistryTier
    evidence_time: datetime
    side: str
    research_id: str
    source_shadow_order_id: str
    evidence_summary: str
    outcome_summary: str
    strategy_version: str
    parameter_version: str

    def __post_init__(self) -> None:
        if self.kind is not NotificationKind.RESEARCH_FAILED_BREAKOUT:
            raise NotificationContractError(
                "ResearchNotificationView requires RESEARCH_FAILED_BREAKOUT"
            )
        for field in (
            "market_display",
            "research_id",
            "source_shadow_order_id",
            "evidence_summary",
            "outcome_summary",
            "strategy_version",
            "parameter_version",
        ):
            _non_empty(getattr(self, field), field)
        _utc(self.evidence_time, "evidence_time")
        if self.side not in _DIRECTIONAL_SIDES:
            raise NotificationContractError("research evidence side must be LONG or SHORT")


NotificationView = SignalNotificationView | ScannerWatchNotificationView | ResearchNotificationView


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
