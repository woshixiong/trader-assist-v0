"""Deterministic, deliberately conservative notification formatting."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

from .models import (
    MessageEnvelope,
    NotificationKind,
    NotificationView,
    ResearchNotificationView,
    ScannerWatchNotificationView,
    SignalNotificationView,
)

_SCHEMA_VERSION = "MULTI_ASSET_SHADOW_NOTIFICATION_V1"


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def idempotency_key(view: NotificationView) -> str:
    """Return the stable identity for one semantic notification, not its rendering."""
    if isinstance(view, SignalNotificationView):
        identity_value = view.signal_id
    elif isinstance(view, ScannerWatchNotificationView):
        identity_value = view.watch_id
    else:
        identity_value = view.research_id
    identity = f"{_SCHEMA_VERSION}|{view.kind.value}|{identity_value}".encode()
    return f"masn-v1-{hashlib.sha256(identity).hexdigest()}"


def format_notification(view: NotificationView) -> str:
    """Render a human-readable message with unambiguous actionability labels."""
    if isinstance(view, ScannerWatchNotificationView):
        scanner_lines = [
            "WATCH — NOT ACTIONABLE",
            "NOT_YET_SETUP_CONFIRMED",
            f"Market: {view.market_display}",
            f"Tier: {view.tier.value}",
        ]
        if view.side is not None:
            scanner_lines.append(f"Side: {view.side}")
        scanner_lines.extend(
            [
                f"Observation time: {_timestamp(view.observation_time)}",
                f"15m return: {_decimal(view.return_15m)}",
                f"30m return: {_decimal(view.return_30m)}",
                f"60m return: {_decimal(view.return_60m)}",
                f"Rank: {view.rank}",
                f"Move ATR: {_decimal(view.move_atr)}",
                f"Relative volume: {_decimal(view.relative_volume)}",
                f"Prior level: {view.prior_level}",
                f"Distance to level: {_decimal(view.distance_to_level)}",
                f"Liquidity: {view.liquidity_summary}",
                f"Scanner R3 state: {view.scanner_r3_state}",
                f"Session: {view.session}",
                f"Scanner / parameters: {view.scanner_parameter_version}",
                f"Watch ID: {view.watch_id}",
            ]
        )
        if view.do_not_chase:
            scanner_lines.append("DO_NOT_CHASE")
        return "\n".join(scanner_lines)
    if isinstance(view, ResearchNotificationView):
        return "\n".join(
            (
                "RESEARCH / FAILED_BREAKOUT EVIDENCE",
                "NOT ACTIONABLE",
                "NOT A FORMAL SIGNAL",
                f"Market: {view.market_display}",
                f"Tier: {view.tier.value}",
                f"Original side: {view.side}",
                f"Evidence time: {_timestamp(view.evidence_time)}",
                f"Outcome ID: {view.outcome_id}",
                "Failed transition IDs: "
                + (", ".join(view.failed_transition_ids) or "OUTCOME_DERIVED"),
                f"Path maturity: {view.path_maturity_status}",
                f"Required end ms: {view.required_end_ms}",
                "Accepted re-entry time ms: "
                + (
                    "NONE"
                    if view.accepted_reentry_time_ms is None
                    else str(view.accepted_reentry_time_ms)
                ),
                f"Reclaim status: {view.reclaim_status}",
                f"Conflict count: {view.conflict_count}",
                f"Gap present: {'YES' if view.has_gap else 'NO'}",
                f"Strategy / parameters: {view.strategy_version} / {view.parameter_version}",
                f"Source ShadowOrder ID: {view.source_shadow_order_id}",
                f"Research ID: {view.research_id}",
            )
        )
    common = [
        f"Market: {view.market_display}",
        f"Tier: {view.tier.value}",
        f"Setup: {view.setup_family}"
        + (f" / {view.setup_mode}" if view.setup_mode is not None else ""),
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
    raise AssertionError("SignalNotificationView must be FORMAL_SIGNAL")


def build_envelope(*, view: NotificationView, created_at: datetime) -> MessageEnvelope:
    return MessageEnvelope(
        schema_version=_SCHEMA_VERSION,
        kind=view.kind,
        idempotency_key=idempotency_key(view),
        content=format_notification(view),
        created_at=created_at,
    )
