"""Deterministic, deliberately conservative notification formatting."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

from .models import MessageEnvelope, NotificationKind, SignalNotificationView

_SCHEMA_VERSION = "MULTI_ASSET_SHADOW_NOTIFICATION_V1"


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def idempotency_key(view: SignalNotificationView) -> str:
    """Return the stable identity for one semantic notification, not its rendering."""
    identity = f"{_SCHEMA_VERSION}|{view.kind.value}|{view.signal_id}".encode()
    return f"masn-v1-{hashlib.sha256(identity).hexdigest()}"


def format_notification(view: SignalNotificationView) -> str:
    """Render a human-readable message with unambiguous actionability labels."""
    common = [
        f"Market: {view.market_display}",
        f"Tier: {view.tier.value}",
        f"Setup: {view.setup_family} / {view.setup_mode}",
        f"Signal time: {_timestamp(view.signal_time)}",
        f"HTF relation: {view.htf_relation}",
        f"Zone context: {view.zone_context}",
        f"Liquidity: {view.liquidity_attribution}",
        f"Strategy / parameters: {view.strategy_version} / {view.parameter_version}",
        f"Signal ID: {view.signal_id}",
    ]
    if view.shadow_order_id is not None:
        common.append(f"ShadowOrder ID: {view.shadow_order_id}")
    if view.session_warning is not None:
        common.append(f"SESSION WARNING: {view.session_warning}")
    if view.kind is NotificationKind.FORMAL_SIGNAL:
        assert view.side is not None
        assert view.planned_entry is not None
        assert view.stop is not None
        assert view.tp1 is not None
        assert view.entry_quality is not None
        plan = [
            "FORMAL SIGNAL — MANUAL REVIEW REQUIRED",
            "NOT_SUBMITTED — NO ORDER SENT",
            f"Side: {view.side}",
            f"Planned entry: {_decimal(view.planned_entry)}",
            f"Stop: {_decimal(view.stop)}",
            f"TP1: {_decimal(view.tp1)}",
        ]
        if view.tp2 is not None:
            plan.append(f"TP2: {_decimal(view.tp2)}")
        plan.extend(
            [
                f"Entry Quality: {view.entry_quality}",
                f"Reference risk sizing: {view.reference_risk_sizing}",
                *common,
            ]
        )
        return "\n".join(plan)
    if view.kind is NotificationKind.WATCH:
        return "\n".join(
            [
                "WATCH — NOT ACTIONABLE",
                "Observation only. No entry, stop, target, or order instruction.",
                *common,
            ]
        )
    return "\n".join(
        [
            "RESEARCH / FAILED_BREAKOUT EVIDENCE — NOT ACTIONABLE",
            "Evidence record only. It is not a Formal Signal or order instruction.",
            *common,
        ]
    )


def build_envelope(*, view: SignalNotificationView, created_at: datetime) -> MessageEnvelope:
    return MessageEnvelope(
        schema_version=_SCHEMA_VERSION,
        kind=view.kind,
        idempotency_key=idempotency_key(view),
        content=format_notification(view),
        created_at=created_at,
    )
