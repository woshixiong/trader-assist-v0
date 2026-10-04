"""Fail-closed, display-only operator dashboard projection."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from trader_assist_v0.multi_asset_shadow.shadow_records.records import RecordError
from trader_assist_v0.multi_asset_shadow.shadow_records.store import ReadOnlyEvidenceSnapshot

from .approval import OperatorBlocked, OperatorEngine
from .contracts import DashboardEvent, DashboardModel, OperatorConfig
from .registry import validate_registry
from .runtime_health import read_runtime_health

EVENT_LIMIT = 20


def _recent_events(path: Path) -> tuple[tuple[DashboardEvent, ...], bool]:
    # A cold Operator has no retained events yet; this is not a display fault.
    if not path.exists():
        return (), True
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.1)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        rows = connection.execute(
            "SELECT event_key, package_id, state, server_ms, reason_codes_json, "
            "submission_status FROM ts8_transitions "
            "WHERE state IN ('EXPIRED', 'SUPERSEDED', 'THESIS_INVALID', "
            "'WAITING_FRESH_TRIGGER', 'REJECTED', 'WOULD_SUBMIT', 'NO_SUBMIT') "
            "ORDER BY server_ms DESC, event_key DESC LIMIT ?", (EVENT_LIMIT,)
        ).fetchall()
        events = []
        for row in rows:
            reasons = json.loads(str(row["reason_codes_json"]))
            if (row["submission_status"] != "NOT_SUBMITTED" or not isinstance(reasons, list)
                    or any(not isinstance(item, str) for item in reasons)):
                raise ValueError("invalid retained operator event")
            events.append(DashboardEvent(
                str(row["event_key"]), str(row["package_id"]), str(row["state"]),
                int(row["server_ms"]), tuple(reasons),
            ))
        return tuple(events), True
    except (sqlite3.Error, ValueError, TypeError, KeyError):
        return (), False
    finally:
        if connection is not None:
            connection.close()


def build_dashboard(operator: OperatorEngine, config: OperatorConfig) -> DashboardModel:
    module = validate_registry()[0]
    if module.builder != "three_setup_current":
        raise ValueError("unknown dashboard builder")
    now_ms = time.time_ns() // 1_000_000
    health = read_runtime_health(config.runtime_evidence_path, now_ms=now_ms)
    events, events_available = _recent_events(config.operator_ledger_path)
    package = None
    details: dict[str, object] = {}
    state = "BLOCKED"
    gate: str = "BLOCKED"
    reasons: list[str] = []
    try:
        with ReadOnlyEvidenceSnapshot(config.runtime_evidence_path) as source:
            no_opportunity = source.latest_shadow() is None
        if no_opportunity:
            state = "NO_OPPORTUNITY"
            reasons.append("NO_RETAINED_OPPORTUNITY")
        else:
            projection, state = operator.latest(now_ms=now_ms)
            package = projection.package
            details = package.ts8_details or {}
            if (state == "AWAITING_HUMAN_APPROVAL"
                    and details.get("approval_mode") == "POST_ACTIVATION"
                    and details.get("submission_status") == "NOT_SUBMITTED"
                    and details.get("execution_eligible") is False
                    and now_ms < package.expires_server_ms):
                gate = "PASS"
            else:
                reasons.append("PACKAGE_NOT_REVIEWABLE")
    except (OperatorBlocked, sqlite3.Error, RecordError):
        reasons.append("SOURCE_OR_PACKAGE_UNAVAILABLE")
    reasons.extend(health.reasons)
    if not health.ready:
        gate = "BLOCKED"
    if not events_available:
        reasons.append("OPERATOR_EVENTS_NOT_AVAILABLE")
    reasons.extend(("ENVIRONMENT_UNKNOWN",
                    "TARGET_HOST_RESOURCE_NOT_AVAILABLE", "BACKUP_STATUS_NOT_AVAILABLE"))
    overall: str = "BLOCKED" if not health.ready or (
        "SOURCE_OR_PACKAGE_UNAVAILABLE" in reasons
    ) or (package is not None and gate == "BLOCKED") else (
        "READY" if events_available else "DEGRADED"
    )
    return DashboardModel(
        overall=overall,  # type: ignore[arg-type]
        reasons=tuple(reasons), package_gate=gate,  # type: ignore[arg-type]
        package=package, details=details, state=state, observed_ms=now_ms,
        events=events, events_available=events_available, module_id=module.module_id,
        module_renderer=module.renderer,
        runtime_health=health,
    )
