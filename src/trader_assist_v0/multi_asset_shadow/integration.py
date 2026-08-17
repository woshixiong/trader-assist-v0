"""Thin composition for the public-data-only multi-asset Shadow route.

The coordinator joins the accepted bounded components without becoming a new
runtime framework.  It has no account, credential, signing, order-submission,
or exchange-write surface.  Public BBO/L2 and 1m providers are injected.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, cast

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.runtime.first_launch_notification import (
    HttpTransport,
    NotificationConfig,
    NotificationDeliveryError,
)

from .correlation_engine import (
    CloseObservation,
    CorrelationReport,
    ShadowSignal,
    build_correlation_report,
)
from .data import MultiAssetDataAuthority
from .models import ClosedBar, MarketLifecycle, RegistryMarket, RegistryVersion
from .notification_engine import (
    ClaimedOutboxMessage,
    DeliveryState,
    DeliveryTransition,
    EnqueueReceipt,
    MessageEnvelope,
    NotificationContractError,
    NotificationKind,
    ResearchNotificationView,
    ScannerWatchNotificationView,
    SignalNotificationView,
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookDeliveryError,
    WebhookResponse,
    build_envelope,
)
from .outcome_engine import (
    AdmissionStatus,
    FormalShadowOutcome,
    FormalShadowView,
    MaturityStatus,
    OneMinuteBar,
    OneMinuteProvider,
    OutcomeEngine,
    OutcomeEngineError,
    OutcomeSink,
    OutcomeTransitionView,
    PathPrimaryResult,
    ShadowState,
    TransitionKind,
)
from .outcome_engine import (
    SetupFamily as OutcomeSetupFamily,
)
from .outcome_engine import (
    Side as OutcomeSide,
)
from .planning import (
    CostModel,
    PlanDraft,
    PlanInputs,
    PlanningError,
    PlanRejection,
    PublicBbo,
    assess_l2,
    make_plan,
    minimum_tick,
)
from .planning import (
    Side as PlanningSide,
)
from .registry import MarketRegistryManager
from .runtime import BoundaryMode, RuntimeReadinessSnapshot
from .shadow_records import (
    Candidate as EvidenceCandidate,
)
from .shadow_records import (
    CandidateTransition,
    EvidenceStore,
    FormalizationDisposition,
    FormalizationDispositionStatus,
    FormalSignal,
    HumanReview,
    HumanReviewAction,
    NotificationOutboxReference,
    OutcomeBarEvidence,
    OutcomeEnvelope,
    OutcomeTransitionEvidence,
    PlanRecord,
    ProvenanceRecord,
    RecordError,
    ScannerEvidence,
    ShadowOrder,
    StrategyEvaluation,
)
from .shadow_records import (
    MarketEvent as EvidenceMarketEvent,
)
from .shadow_records.records import ImmutableRecord
from .strategy_kernel import (
    PARAMETER_VERSION,
    SCANNER_VERSION,
    STRATEGY_VERSION,
    Bar,
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfContext,
    HtfMomentum,
    HtfRelation,
    HtfStructure,
    KernelResult,
    RetestType,
    ScannerCandidate,
    ScannerChase,
    ScannerLinkage,
    ScannerMarketInput,
    ScannerMetrics,
    ScannerObservation,
    ScannerState,
    SetupFamily,
    SetupMode,
    StrategyDecision,
    StrategyEvaluationInput,
    TargetKind,
    TargetReference,
    ZoneBook,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
    aggregate_closed_5m_causally,
    evaluate_strategy,
    scan_cross_section,
)
from .strategy_kernel import (
    MarketEvent as KernelMarketEvent,
)
from .strategy_kernel import (
    Side as StrategySide,
)
from .strategy_kernel.scanner import (
    ScannerCandidateClass,
    advance_scanner_candidate,
    classify_scanner_state,
)


class IntegrationError(ValueError):
    """Mandatory cross-lane identity or provenance is inconsistent."""


class TargetResolutionError(IntegrationError):
    """Deterministic fail-closed frozen target rejection."""


class RuntimeReadinessAuthority(Protocol):
    def readiness_snapshot(self) -> RuntimeReadinessSnapshot: ...


def _utc(value: datetime, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise IntegrationError(f"{field} must be an exact UTC datetime")
    return value


def _timestamp(value: datetime) -> str:
    return _utc(value, "timestamp").isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise IntegrationError(f"{field} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntegrationError(f"{field} is not a timestamp") from exc
    return parsed.astimezone(UTC)


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _optional_decimal(value: Decimal | None) -> str | None:
    return None if value is None else _decimal(value)


def _as_decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, str):
        raise IntegrationError(f"{field} is not retained decimal evidence")
    try:
        parsed = Decimal(value)
    except ArithmeticError as exc:
        raise IntegrationError(f"{field} is not retained decimal evidence") from exc
    if not parsed.is_finite():
        raise IntegrationError(f"{field} is not retained decimal evidence")
    return parsed


def _canonical_dataclass(value: Any) -> dict[str, object]:
    decoded = __import__("json").loads(canonical_json_bytes(asdict(value)))
    if not isinstance(decoded, dict):  # pragma: no cover - dataclass invariant
        raise IntegrationError("typed evidence did not encode an object")
    return cast(dict[str, object], decoded)


def _typed_hash(kind: str, payload: object) -> str:
    return sha256_hex(f"trader-assist-v0/{kind}/v1\0".encode() + canonical_json_bytes(payload))


def _bar_from_payload(value: object) -> Bar:
    if not isinstance(value, dict):
        raise IntegrationError("retained strategy bar is invalid")
    return Bar(
        market_id=str(value["market_id"]),
        interval=str(value["interval"]),
        open_time_ms=int(value["open_time_ms"]),
        close_time_ms=int(value["close_time_ms"]),
        open=_as_decimal(value["open"], "bar open"),
        high=_as_decimal(value["high"], "bar high"),
        low=_as_decimal(value["low"], "bar low"),
        close=_as_decimal(value["close"], "bar close"),
        volume=_as_decimal(value["volume"], "bar volume"),
        source_identity=str(value["source_identity"]),
    )


def _zone_from_payload(value: object) -> ZoneSnapshot:
    if not isinstance(value, dict):
        raise IntegrationError("retained strategy zone is invalid")
    members = value.get("member_reaction_ids")
    if not isinstance(members, list):
        raise IntegrationError("retained strategy zone membership is invalid")
    return ZoneSnapshot(
        zone_id=str(value["zone_id"]),
        market_id=str(value["market_id"]),
        zone_type=ZoneType(str(value["zone_type"])),
        center=_as_decimal(value["center"], "zone center"),
        low=_as_decimal(value["low"], "zone low"),
        high=_as_decimal(value["high"], "zone high"),
        half_width=_as_decimal(value["half_width"], "zone half_width"),
        quality=ZoneQuality(str(value["quality"])),
        reaction_count=int(value["reaction_count"]),
        latest_reaction_bar_index=int(value["latest_reaction_bar_index"]),
        member_reaction_ids=tuple(str(item) for item in members),
        active_for_new_event=bool(value["active_for_new_event"]),
        suppressed=bool(value["suppressed"]),
    )


def _scanner_linkage_from_payload(value: object) -> ScannerLinkage | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise IntegrationError("retained scanner linkage is invalid")
    return ScannerLinkage(
        candidate_id=str(value["candidate_id"]),
        state=ScannerState(str(value["state"])),
        scanner_version=str(value["scanner_version"]),
    )


def _scanner_candidate_from_payload(value: object) -> ScannerCandidate:
    if not isinstance(value, dict):
        raise IntegrationError("retained Scanner Candidate is invalid")
    transitions = value.get("transitions")
    if not isinstance(transitions, list):
        raise IntegrationError("retained Scanner transitions are invalid")
    return ScannerCandidate(
        candidate_id=str(value["candidate_id"]),
        market_id=str(value["market_id"]),
        side=None if value.get("side") is None else StrategySide(str(value["side"])),
        state=ScannerState(str(value["state"])),
        created_bar_open_time_ms=int(value["created_bar_open_time_ms"]),
        breakout_bar_open_time_ms=(
            None
            if value.get("breakout_bar_open_time_ms") is None
            else int(value["breakout_bar_open_time_ms"])
        ),
        breakout_level=(
            None
            if value.get("breakout_level") is None
            else _as_decimal(value["breakout_level"], "breakout_level")
        ),
        breakout_buffer=(
            None
            if value.get("breakout_buffer") is None
            else _as_decimal(value["breakout_buffer"], "breakout_buffer")
        ),
        secondary_level_broken=bool(value["secondary_level_broken"]),
        retest_touch_bar_open_time_ms=(
            None
            if value.get("retest_touch_bar_open_time_ms") is None
            else int(value["retest_touch_bar_open_time_ms"])
        ),
        chase=None if value.get("chase") is None else ScannerChase(str(value["chase"])),
        chase_distance_atr=(
            None
            if value.get("chase_distance_atr") is None
            else _as_decimal(value["chase_distance_atr"], "chase_distance_atr")
        ),
        reason=str(value["reason"]),
        transitions=tuple(str(item) for item in transitions),
        scanner_version=str(value["scanner_version"]),
        parameter_version=str(value["parameter_version"]),
    )


def _scanner_metrics_from_payload(value: object) -> ScannerMetrics | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise IntegrationError("retained Scanner metrics are invalid")

    def required(name: str) -> Decimal:
        return _as_decimal(value[name], f"Scanner metric {name}")

    def optional(name: str) -> Decimal | None:
        return (
            None
            if value.get(name) is None
            else _as_decimal(value[name], f"Scanner metric {name}")
        )

    return ScannerMetrics(
        return_15m=required("return_15m"),
        return_30m=required("return_30m"),
        return_60m=required("return_60m"),
        relative_universe_15m=required("relative_universe_15m"),
        relative_universe_30m=required("relative_universe_30m"),
        relative_universe_60m=required("relative_universe_60m"),
        relative_btc_15m=optional("relative_btc_15m"),
        relative_btc_30m=optional("relative_btc_30m"),
        relative_btc_60m=optional("relative_btc_60m"),
        move_atr_15m=required("move_atr_15m"),
        move_atr_30m=required("move_atr_30m"),
        move_atr_60m=required("move_atr_60m"),
        relative_volume_5m=required("relative_volume_5m"),
        er_15m=required("er_15m"),
        er_30m=required("er_30m"),
        er_60m=required("er_60m"),
        prior_high_12=required("prior_high_12"),
        prior_low_12=required("prior_low_12"),
        prior_high_36=required("prior_high_36"),
        prior_low_36=required("prior_low_36"),
    )


def _scanner_observation_from_payload(value: object) -> ScannerObservation:
    if not isinstance(value, dict):
        raise IntegrationError("retained Scanner observation is invalid")
    return ScannerObservation(
        market_id=str(value["market_id"]),
        metrics=_scanner_metrics_from_payload(value.get("metrics")),
        candidate=(
            None
            if value.get("candidate") is None
            else _scanner_candidate_from_payload(value["candidate"])
        ),
    )


def _target_from_payload(value: object) -> TargetReference | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise IntegrationError("retained target reference is invalid")
    zones = value.get("frozen_directional_zones")
    if not isinstance(zones, list):
        raise IntegrationError("retained directional zones are invalid")
    return TargetReference(
        kind=TargetKind(str(value["kind"])),
        price=None if value.get("price") is None else _as_decimal(value["price"], "target"),
        zone_id=None if value.get("zone_id") is None else str(value["zone_id"]),
        frozen_directional_zones=tuple(_zone_from_payload(item) for item in zones),
    )


def _breakout_linkage_from_payload(value: object) -> BreakoutLinkage | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise IntegrationError("retained breakout linkage is invalid")
    return BreakoutLinkage(
        underlying_breakout_event_id=str(value["underlying_breakout_event_id"]),
        initial_breakout_candle_id=str(value["initial_breakout_candle_id"]),
        accepted_reentry_source_event_id=(
            None
            if value.get("accepted_reentry_source_event_id") is None
            else str(value["accepted_reentry_source_event_id"])
        ),
    )


def _decision_from_payload(value: object) -> StrategyDecision:
    if not isinstance(value, dict):
        raise IntegrationError("retained StrategyDecision is invalid")
    return StrategyDecision(
        market_id=str(value["market_id"]),
        setup_family=SetupFamily(str(value["setup_family"])),
        setup_mode=(
            None if value.get("setup_mode") is None else SetupMode(str(value["setup_mode"]))
        ),
        retest_type=(
            None if value.get("retest_type") is None else RetestType(str(value["retest_type"]))
        ),
        side=StrategySide(str(value["side"])),
        decision=DecisionKind(str(value["decision"])),
        reason=str(value["reason"]),
        market_event_id=str(value["market_event_id"]),
        zone_id=str(value["zone_id"]),
        zone_snapshot=_zone_from_payload(value["zone_snapshot"]),
        a5_event=_as_decimal(value["a5_event"], "a5_event"),
        m20_event=_as_decimal(value["m20_event"], "m20_event"),
        htf_relation=HtfRelation(str(value["htf_relation"])),
        breakout_linkage=_breakout_linkage_from_payload(value.get("breakout_linkage")),
        ideal_entry_low=(
            None
            if value.get("ideal_entry_low") is None
            else _as_decimal(value["ideal_entry_low"], "ideal_entry_low")
        ),
        ideal_entry_high=(
            None
            if value.get("ideal_entry_high") is None
            else _as_decimal(value["ideal_entry_high"], "ideal_entry_high")
        ),
        chase_limit=(
            None
            if value.get("chase_limit") is None
            else _as_decimal(value["chase_limit"], "chase_limit")
        ),
        structural_stop=(
            None
            if value.get("structural_stop") is None
            else _as_decimal(value["structural_stop"], "structural_stop")
        ),
        target_reference=_target_from_payload(value.get("target_reference")),
        transition=str(value["transition"]),
        scanner_linkage=_scanner_linkage_from_payload(value.get("scanner_linkage")),
        strategy_version=str(value["strategy_version"]),
        parameter_version=str(value["parameter_version"]),
        scanner_version=str(value["scanner_version"]),
        schema_version=str(value["schema_version"]),
    )


def _optional_payload_decimal(value: dict[str, object], key: str) -> Decimal | None:
    return None if value.get(key) is None else _as_decimal(value[key], key)


def _market_event_from_payload(value: object) -> KernelMarketEvent:
    if not isinstance(value, dict):
        raise IntegrationError("retained strategy event is invalid")
    return KernelMarketEvent(
        market_event_id=str(value["market_event_id"]),
        market_id=str(value["market_id"]),
        setup_family=SetupFamily(str(value["setup_family"])),
        side=StrategySide(str(value["side"])),
        status=EventStatus(str(value["status"])),
        transition=str(value["transition"]),
        zone=_zone_from_payload(value["zone"]),
        created_bar=_bar_from_payload(value["created_bar"]),
        latest_bar=_bar_from_payload(value["latest_bar"]),
        a5_event=_as_decimal(value["a5_event"], "a5_event"),
        m20_event=_as_decimal(value["m20_event"], "m20_event"),
        htf_relation=HtfRelation(str(value["htf_relation"])),
        scanner_linkage=_scanner_linkage_from_payload(value.get("scanner_linkage")),
        breakout_linkage=_breakout_linkage_from_payload(value.get("breakout_linkage")),
        reclaim_candle_high=_optional_payload_decimal(value, "reclaim_candle_high"),
        reclaim_candle_low=_optional_payload_decimal(value, "reclaim_candle_low"),
        sweep_extreme=_optional_payload_decimal(value, "sweep_extreme"),
        initial_breakout_open=_optional_payload_decimal(value, "initial_breakout_open"),
        initial_breakout_high=_optional_payload_decimal(value, "initial_breakout_high"),
        initial_breakout_low=_optional_payload_decimal(value, "initial_breakout_low"),
        initial_breakout_close=_optional_payload_decimal(value, "initial_breakout_close"),
        previous_close=_optional_payload_decimal(value, "previous_close"),
        previous_high=_optional_payload_decimal(value, "previous_high"),
        previous_low=_optional_payload_decimal(value, "previous_low"),
        pullback_started=bool(value["pullback_started"]),
        impulse_extreme=_optional_payload_decimal(value, "impulse_extreme"),
        pullback_extreme=_optional_payload_decimal(value, "pullback_extreme"),
        retest_type=(
            None if value.get("retest_type") is None else RetestType(str(value["retest_type"]))
        ),
        retest_seen_bar_time_ms=(
            None
            if value.get("retest_seen_bar_time_ms") is None
            else int(value["retest_seen_bar_time_ms"])
        ),
        formal_mode=(
            None if value.get("formal_mode") is None else SetupMode(str(value["formal_mode"]))
        ),
        ideal_entry_low=_optional_payload_decimal(value, "ideal_entry_low"),
        ideal_entry_high=_optional_payload_decimal(value, "ideal_entry_high"),
        chase_limit=_optional_payload_decimal(value, "chase_limit"),
        structural_stop=_optional_payload_decimal(value, "structural_stop"),
        target_reference=_target_from_payload(value.get("target_reference")),
    )


def _ledger_payload(value: EventLedger) -> dict[str, object]:
    return {"events": [_canonical_dataclass(event) for event in value.events]}


def _ledger_from_payload(value: object) -> EventLedger:
    if not isinstance(value, dict) or not isinstance(value.get("events"), list):
        raise IntegrationError("retained EventLedger checkpoint is invalid")
    return EventLedger(tuple(_market_event_from_payload(item) for item in value["events"]))


def _kernel_result_from_payload(payload: Mapping[str, object]) -> KernelResult:
    decisions = payload.get("decisions")
    zones = payload.get("zones")
    htf = payload.get("htf_context")
    if not isinstance(decisions, list) or not isinstance(zones, list) or not isinstance(htf, dict):
        raise IntegrationError("retained KernelResult checkpoint is incomplete")
    decoded_decisions: list[StrategyDecision] = []
    for item in decisions:
        if not isinstance(item, dict):
            raise IntegrationError("retained StrategyDecision checkpoint is invalid")
        decision = _decision_from_payload(item.get("content"))
        if item.get("decision_id") != _typed_hash(
            "strategy-decision", _canonical_dataclass(decision)
        ):
            raise IntegrationError("retained StrategyDecision identity is invalid")
        decoded_decisions.append(decision)
    ledger = _ledger_from_payload(payload.get("output_ledger"))
    if payload.get("output_ledger_hash") != _typed_hash(
        "event-ledger", _ledger_payload(ledger)
    ):
        raise IntegrationError("retained EventLedger checkpoint hash is invalid")
    return KernelResult(
        ledger=ledger,
        decisions=tuple(decoded_decisions),
        zones=tuple(_zone_from_payload(item) for item in zones),
        active_support=(
            None
            if payload.get("active_support") is None
            else _zone_from_payload(payload["active_support"])
        ),
        active_resistance=(
            None
            if payload.get("active_resistance") is None
            else _zone_from_payload(payload["active_resistance"])
        ),
        htf_context=HtfContext(
            momentum=HtfMomentum(str(htf["momentum"])),
            structure=HtfStructure(str(htf["structure"])),
            er8_1h=(
                None if htf.get("er8_1h") is None else _as_decimal(htf["er8_1h"], "er8_1h")
            ),
            d8_1h=(
                None if htf.get("d8_1h") is None else _as_decimal(htf["d8_1h"], "d8_1h")
            ),
        ),
    )


def _row_envelope(row: sqlite3.Row) -> MessageEnvelope:
    return MessageEnvelope(
        schema_version=str(row["schema_version"]),
        kind=NotificationKind(str(row["kind"])),
        idempotency_key=str(row["idempotency_key"]),
        content=str(row["content"]),
        created_at=_parse_timestamp(row["created_at"], "outbox created_at"),
    )


class EvidenceOutbox:
    """Notification Engine port backed by the Evidence-owned SQLite connection."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    @property
    def evidence_store(self) -> EvidenceStore:
        return self._store

    def enqueue(self, envelope: MessageEnvelope) -> EnqueueReceipt:
        if envelope.kind is NotificationKind.FORMAL_SIGNAL:
            raise NotificationContractError(
                "FORMAL_SIGNAL must be published by EvidenceStore.publish_formal_bundle"
            )
        created_at = _timestamp(envelope.created_at)
        with self._store._connection:
            inserted = self._store._connection.execute(
                """INSERT OR IGNORE INTO notification_outbox (
                    idempotency_key, schema_version, kind, content, created_at,
                    state, attempt_count, next_attempt_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?)""",
                (
                    envelope.idempotency_key,
                    envelope.schema_version,
                    envelope.kind.value,
                    envelope.content,
                    created_at,
                    created_at,
                ),
            ).rowcount
            row = self._store._connection.execute(
                "SELECT * FROM notification_outbox WHERE idempotency_key = ?",
                (envelope.idempotency_key,),
            ).fetchone()
        if row is None:  # pragma: no cover - SQLite insert/select is atomic
            raise RecordError("notification outbox insert was not retained")
        if _row_envelope(row) != envelope:
            raise RecordError("notification idempotency identity conflicts with retained content")
        return EnqueueReceipt(envelope=envelope, coalesced=inserted == 0)

    def claim_due(
        self, *, now: datetime, limit: int, lease_seconds: int
    ) -> tuple[ClaimedOutboxMessage, ...]:
        timestamp = _timestamp(now)
        if (
            type(limit) is not int
            or limit < 1
            or type(lease_seconds) is not int
            or lease_seconds < 1
        ):
            raise NotificationContractError("outbox claim bounds must be positive integers")
        expires = _timestamp(now + timedelta(seconds=lease_seconds))
        connection = self._store._connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            rows = connection.execute(
                """SELECT * FROM notification_outbox
                   WHERE state = 'PENDING' AND next_attempt_at <= ?
                     AND (claim_token IS NULL OR claim_expires_at <= ?)
                   ORDER BY next_attempt_at, created_at, idempotency_key
                   LIMIT ?""",
                (timestamp, timestamp, limit),
            ).fetchall()
            claimed: list[ClaimedOutboxMessage] = []
            for row in rows:
                attempt_count = int(row["attempt_count"]) + 1
                token = sha256_hex(
                    canonical_json_bytes(
                        {
                            "idempotency_key": row["idempotency_key"],
                            "attempt_count": attempt_count,
                            "claimed_at": timestamp,
                        }
                    )
                )
                updated = connection.execute(
                    """UPDATE notification_outbox
                       SET attempt_count = ?, claim_token = ?, claim_expires_at = ?
                       WHERE idempotency_key = ? AND state = 'PENDING'
                         AND attempt_count = ?
                         AND (claim_token IS NULL OR claim_expires_at <= ?)""",
                    (
                        attempt_count,
                        token,
                        expires,
                        row["idempotency_key"],
                        row["attempt_count"],
                        timestamp,
                    ),
                ).rowcount
                if updated != 1:  # pragma: no cover - immediate transaction owns the rows
                    raise RecordError("notification outbox claim lost atomic ownership")
                claimed.append(
                    ClaimedOutboxMessage(
                        envelope=_row_envelope(row),
                        attempt_count=attempt_count,
                        claim_token=token,
                    )
                )
            connection.commit()
            return tuple(claimed)
        except BaseException:
            connection.rollback()
            raise

    def complete(self, *, claim_token: str, transition: DeliveryTransition) -> None:
        completed_at = _timestamp(transition.completed_at)
        next_attempt_at = (
            _timestamp(transition.next_attempt_at)
            if transition.next_attempt_at is not None
            else completed_at
        )
        connection = self._store._connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            row = connection.execute(
                "SELECT idempotency_key FROM notification_outbox WHERE claim_token = ?",
                (claim_token,),
            ).fetchone()
            if row is None:
                connection.commit()
                return
            connection.execute(
                """UPDATE notification_outbox
                   SET state = ?, next_attempt_at = ?, claim_token = NULL,
                       claim_expires_at = NULL, completed_at = ?, response_status = ?,
                       last_reason = ?
                   WHERE idempotency_key = ? AND claim_token = ?""",
                (
                    transition.state.value,
                    next_attempt_at,
                    completed_at,
                    transition.response_status,
                    transition.reason,
                    row["idempotency_key"],
                    claim_token,
                ),
            )
            connection.commit()
        except BaseException:
            connection.rollback()
            raise

    def state(self, idempotency_key: str) -> DeliveryState | None:
        row = self._store._connection.execute(
            "SELECT state FROM notification_outbox WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return None if row is None else DeliveryState(str(row["state"]))


class MatureHttpsWebhookPort:
    """Bridge the mature restricted-runtime HTTPS transport to the new port."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def post(
        self, *, url: str, payload: bytes, headers: dict[str, str], timeout_seconds: float
    ) -> WebhookResponse:
        try:
            response = self._transport.post(
                url=url,
                payload=payload,
                headers=headers,
                timeout=timeout_seconds,
            )
        except NotificationDeliveryError as exc:
            raise WebhookDeliveryError("mature HTTPS transport failed") from exc
        return WebhookResponse(status_code=response.status_code)


def mature_discord_delivery_adapter(
    *, config: NotificationConfig, transport: HttpTransport
) -> WebhookDeliveryAdapter:
    """Reuse mature URL/config validation without its legacy idempotency header."""
    return WebhookDeliveryAdapter(
        client=MatureHttpsWebhookPort(transport),
        config=WebhookConfig(
            url=config.webhook_url,
            timeout_seconds=config.timeout,
            authorization_header_name=config.authorization_header_name,
            authorization_header_value=config.authorization_header_value,
        ),
    )


def _record_ids(store: EvidenceStore, record_type: str) -> tuple[str, ...]:
    rows = store._connection.execute(
        "SELECT record_id FROM immutable_records WHERE record_type = ? ORDER BY record_id",
        (record_type,),
    ).fetchall()
    return tuple(str(row["record_id"]) for row in rows)


class EvidenceOutcomeAdapter(OutcomeSink):
    """Persist outcome snapshots and rebuild Formal 1m demand from Evidence."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    @property
    def evidence_store(self) -> EvidenceStore:
        return self._store

    def _outcome_record(self, outcome: FormalShadowOutcome) -> OutcomeEnvelope:
        shadow = self._store.get(outcome.shadow_order_id)
        if not isinstance(shadow, ShadowOrder):
            raise RecordError("outcome shadow_order_id is not retained")
        if shadow.payload.get("market_id") != outcome.market_id:
            raise RecordError("outcome market does not match retained ShadowOrder")
        horizon_120 = next((item for item in outcome.horizons if item.horizon_minutes == 120), None)
        outcome_r: str | None
        if outcome.path.primary_result is PathPrimaryResult.STOP_FIRST:
            outcome_r = "-1"
        elif outcome.path.primary_result is PathPrimaryResult.TP_FIRST:
            outcome_r = "1"
        else:
            outcome_r = None
        observed_at = datetime.fromtimestamp(outcome.evaluated_at_ms / 1000, tz=UTC)
        return OutcomeEnvelope.create(
            identity={
                "shadow_order_id": outcome.shadow_order_id,
                "evaluated_at_ms": outcome.evaluated_at_ms,
            },
            signal_id=shadow.payload["signal_id"],
            shadow_order_id=outcome.shadow_order_id,
            observed_at=_timestamp(observed_at),
            evaluated_at_ms=outcome.evaluated_at_ms,
            path_maturity_status=outcome.path_maturity_status.value,
            unresolved=outcome.unresolved,
            outcome_source="ON_DEMAND_PUBLIC_1M",
            outcome_r=outcome_r,
            outcome_mfe=None if horizon_120 is None else _optional_decimal(horizon_120.mfe),
            outcome_mae=None if horizon_120 is None else _optional_decimal(horizon_120.mae),
            required_start_ms=outcome.required_start_ms,
            original_deadline_ms=outcome.original_deadline_ms,
            required_end_ms=outcome.required_end_ms,
            failed_breakout=outcome.failed_breakout,
            projection=asdict(outcome),
        )

    def save_outcome(self, outcome: FormalShadowOutcome) -> None:
        engine = self.restore_engine(now_ms=outcome.evaluated_at_ms)
        if outcome.shadow_order_id not in engine.attached_shadow_ids:
            raise RecordError("outcome has no reconstructable ShadowOrder")
        if engine.evaluate(
            outcome.shadow_order_id, as_of_ms=outcome.evaluated_at_ms
        ) != outcome:
            raise RecordError("outcome contradicts retained transition or 1m authority")
        self._store._write_controlled((self._outcome_record(outcome),))

    def canonical_outcome(self, record: OutcomeEnvelope) -> FormalShadowOutcome:
        """Strictly validate one projection against the accepted B05 reconstruction."""
        payload = record.payload
        evaluated_value = payload.get("evaluated_at_ms")
        shadow_value = payload.get("shadow_order_id")
        if type(evaluated_value) is not int or evaluated_value < 0 or not isinstance(
            shadow_value, str
        ):
            raise RecordError("outcome projection identity is invalid")
        evaluated_at_ms = evaluated_value
        shadow_order_id = shadow_value
        engine = self.restore_engine(now_ms=evaluated_at_ms)
        if shadow_order_id not in engine.attached_shadow_ids:
            raise RecordError("outcome projection has no reconstructable ShadowOrder")
        outcome = engine.evaluate(shadow_order_id, as_of_ms=evaluated_at_ms)
        if self._outcome_record(outcome) != record:
            raise RecordError("outcome projection contradicts canonical reconstruction")
        return outcome

    def persisted_outcomes(self, shadow_order_id: str) -> tuple[OutcomeEnvelope, ...]:
        values: list[OutcomeEnvelope] = []
        for record_id in _record_ids(self._store, "outcome_envelope"):
            record = self._store.get(record_id)
            if (
                isinstance(record, OutcomeEnvelope)
                and record.payload.get("shadow_order_id") == shadow_order_id
            ):
                values.append(record)
        return tuple(sorted(values, key=lambda item: int(item.payload.get("evaluated_at_ms", -1))))

    def _persist_provider_bars(
        self, bars: tuple[OneMinuteBar, ...]
    ) -> tuple[OutcomeBarEvidence, ...]:
        records = tuple(
            OutcomeBarEvidence.create(
                identity={
                    "market_id": bar.market_id,
                    "open_time_ms": bar.open_time_ms,
                    "canonical_hash": bar.canonical_hash,
                },
                **_canonical_dataclass(bar),
            )
            for bar in bars
        )
        self._store._write_controlled(records)
        return records

    def _retained_transitions(self) -> tuple[OutcomeTransitionView, ...]:
        if _record_ids(self._store, "outcome_transition"):
            raise RecordError("retained Outcome transitions have no production authority")
        return ()

    def _retained_bars(self) -> tuple[OneMinuteBar, ...]:
        values: list[OneMinuteBar] = []
        for record_id in _record_ids(self._store, "outcome_bar"):
            record = self._store.get(record_id)
            if not isinstance(record, OutcomeBarEvidence):
                continue
            payload = record.payload
            values.append(
                OneMinuteBar(
                    market_id=str(payload["market_id"]),
                    open_time_ms=int(payload["open_time_ms"]),
                    close_time_ms=int(payload["close_time_ms"]),
                    open=_as_decimal(payload["open"], "1m open"),
                    high=_as_decimal(payload["high"], "1m high"),
                    low=_as_decimal(payload["low"], "1m low"),
                    close=_as_decimal(payload["close"], "1m close"),
                    canonical_hash=str(payload["canonical_hash"]),
                    source_id=str(payload["source_id"]),
                )
            )
        return tuple(values)

    def restore_engine(
        self, *, now_ms: int, provider: OneMinuteProvider | None = None
    ) -> OutcomeEngine:
        views: list[FormalShadowView] = []
        for record_id in _record_ids(self._store, "shadow_order"):
            record = self._store.get(record_id)
            if not isinstance(record, ShadowOrder):  # pragma: no cover - typed table invariant
                continue
            payload = record.payload
            required = {
                "outcome_start_ms",
                "planned_entry",
                "stop",
                "tp1",
                "atr",
                "market_id",
                "side",
                "setup_family",
            }
            if required - payload.keys():
                continue
            views.append(
                FormalShadowView(
                    shadow_order_id=record.record_id,
                    market_id=str(payload["market_id"]),
                    side=OutcomeSide(str(payload["side"])),
                    setup_family=OutcomeSetupFamily(str(payload["setup_family"])),
                    outcome_start_ms=int(payload["outcome_start_ms"]),
                    planned_entry=_as_decimal(payload["planned_entry"], "planned_entry"),
                    stop=_as_decimal(payload["stop"], "stop"),
                    tp1=_as_decimal(payload["tp1"], "tp1"),
                    tp2=(
                        None if payload.get("tp2") is None else _as_decimal(payload["tp2"], "tp2")
                    ),
                    atr=_as_decimal(payload["atr"], "atr"),
                    zone_low=(
                        None
                        if payload.get("zone_low") is None
                        else _as_decimal(payload["zone_low"], "zone_low")
                    ),
                    zone_high=(
                        None
                        if payload.get("zone_high") is None
                        else _as_decimal(payload["zone_high"], "zone_high")
                    ),
                    state=ShadowState.FORMAL_SHADOW_PLAN,
                    active=True,
                )
            )
        evidence_provider = (
            None
            if provider is None
            else EvidenceOneMinuteProvider(provider=provider, adapter=self)
        )
        return OutcomeEngine.reconstruct(
            shadows=tuple(views),
            transitions=self._retained_transitions(),
            bars=self._retained_bars(),
            now_ms=now_ms,
            provider=evidence_provider,
            sink=self,
            recover=False,
        )


class EvidenceOneMinuteProvider:
    """Persist configured public-provider bars before Outcome Engine admission."""

    def __init__(
        self, *, provider: OneMinuteProvider, adapter: EvidenceOutcomeAdapter
    ) -> None:
        self.provider = provider
        self.adapter = adapter

    def subscribe_1m(self, *, market_id: str) -> None:
        self.provider.subscribe_1m(market_id=market_id)

    def unsubscribe_1m(self, *, market_id: str) -> None:
        self.provider.unsubscribe_1m(market_id=market_id)

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        bars = self.provider.backfill_1m(
            market_id=market_id, start_ms=start_ms, end_ms=end_ms
        )
        if type(bars) is not tuple or any(
            type(bar) is not OneMinuteBar
            or bar.market_id != market_id
            or not start_ms <= bar.open_time_ms < end_ms
            for bar in bars
        ):
            raise OutcomeEngineError("backfill returned a bar outside its request")
        self.adapter._persist_provider_bars(bars)
        return bars


@dataclass(frozen=True)
class CorrelationMarketMetrics:
    p10_weak_depth_10bps: Decimal
    p95_spread_bps: Decimal
    exchange_day_notional: Decimal
    oi_notional: Decimal

    def __post_init__(self) -> None:
        values = (
            self.p10_weak_depth_10bps,
            self.p95_spread_bps,
            self.exchange_day_notional,
            self.oi_notional,
        )
        if any(not value.is_finite() or value < 0 for value in values):
            raise IntegrationError("correlation market metrics must be finite and non-negative")

    def payload(self) -> dict[str, str]:
        return {
            "p10_weak_depth_10bps": _decimal(self.p10_weak_depth_10bps),
            "p95_spread_bps": _decimal(self.p95_spread_bps),
            "exchange_day_notional": _decimal(self.exchange_day_notional),
            "oi_notional": _decimal(self.oi_notional),
        }


class CorrelationResearchAdapter:
    """Project only completed retained outcomes into the pure research engine."""

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    def completed_signals(self) -> tuple[ShadowSignal, ...]:
        adapter = EvidenceOutcomeAdapter(self._store)
        latest_records: dict[str, OutcomeEnvelope] = {}
        for record_id in _record_ids(self._store, "outcome_envelope"):
            record = self._store.get(record_id)
            if not isinstance(record, OutcomeEnvelope):  # pragma: no cover
                continue
            payload = record.payload
            shadow_order_id = str(payload.get("shadow_order_id", ""))
            evaluated_at_ms = payload.get("evaluated_at_ms")
            if type(evaluated_at_ms) is not int:
                raise RecordError("outcome projection evaluation time is invalid")
            prior = latest_records.get(shadow_order_id)
            if prior is None or evaluated_at_ms > int(prior.payload["evaluated_at_ms"]):
                latest_records[shadow_order_id] = record
        latest: dict[str, FormalShadowOutcome] = {}
        for shadow_order_id, record in latest_records.items():
            outcome = adapter.canonical_outcome(record)
            if outcome.path_maturity_status is not MaturityStatus.MATURE or outcome.unresolved:
                continue
            latest[shadow_order_id] = outcome
        projected: list[ShadowSignal] = []
        for shadow_order_id, outcome in latest.items():
            shadow = self._store.get(shadow_order_id)
            if not isinstance(shadow, ShadowOrder):
                raise RecordError("completed outcome has no retained ShadowOrder")
            payload = shadow.payload
            metrics = payload.get("correlation_market_metrics")
            if not isinstance(metrics, dict):
                continue
            projected.append(
                ShadowSignal(
                    shadow_order_id=shadow_order_id,
                    market_id=str(payload["market_id"]),
                    setup_family=str(payload["setup_family"]),
                    direction=str(payload["side"]),
                    confirmed_at=_parse_timestamp(payload["confirmed_at"], "confirmed_at"),
                    strategy_version=str(payload["strategy_version"]),
                    parameter_version=str(payload["parameter_version"]),
                    p10_weak_depth_10bps=_as_decimal(
                        metrics.get("p10_weak_depth_10bps"), "p10_weak_depth_10bps"
                    ),
                    p95_spread_bps=_as_decimal(metrics.get("p95_spread_bps"), "p95_spread_bps"),
                    exchange_day_notional=_as_decimal(
                        metrics.get("exchange_day_notional"), "exchange_day_notional"
                    ),
                    oi_notional=_as_decimal(metrics.get("oi_notional"), "oi_notional"),
                    outcome_r=(
                        Decimal("-1")
                        if outcome.path.primary_result is PathPrimaryResult.STOP_FIRST
                        else (
                            Decimal("1")
                            if outcome.path.primary_result is PathPrimaryResult.TP_FIRST
                            else None
                        )
                    ),
                    outcome_mfe=next(
                        (
                            item.mfe
                            for item in outcome.horizons
                            if item.horizon_minutes == 120
                        ),
                        None,
                    ),
                    outcome_mae=next(
                        (
                            item.mae
                            for item in outcome.horizons
                            if item.horizon_minutes == 120
                        ),
                        None,
                    ),
                )
            )
        return tuple(
            sorted(
                projected,
                key=lambda item: (item.confirmed_at_utc, item.shadow_order_id),
            )
        )

    def build_report(
        self, observations_by_market: Mapping[str, Sequence[CloseObservation]]
    ) -> CorrelationReport:
        return build_correlation_report(self.completed_signals(), observations_by_market)


@dataclass(frozen=True)
class PublicL2Snapshot:
    market_id: str
    coin: str
    observed_at_ms: int
    best_bid: Decimal
    best_ask: Decimal
    levels: tuple[tuple[Decimal, Decimal], ...]
    provenance_hash: str


class PublicPlanningData(Protocol):
    """On-demand public-only planning evidence; no continuous L2 authority."""

    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> PublicBbo: ...

    def fetch_l2(
        self, *, market: RegistryMarket, side: PlanningSide, bbo: PublicBbo
    ) -> PublicL2Snapshot: ...


@dataclass(frozen=True)
class ScannerPublicSnapshot:
    current_spread_price: Decimal
    liquidity_healthy: bool
    btc_returns: tuple[Decimal | None, Decimal | None, Decimal | None] = (None, None, None)

    def __post_init__(self) -> None:
        if not self.current_spread_price.is_finite() or self.current_spread_price < 0:
            raise IntegrationError("scanner spread must be finite and non-negative")


@dataclass(frozen=True)
class ScannerRunReceipt:
    scan_id: str
    scanner_evidence_id: str
    scanner_evidence_hash: str
    observations: tuple[ScannerObservation, ...]
    candidate_record_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationReceipt:
    evaluation_id: str
    evaluation_record_id: str
    evaluation_record_hash: str
    market_id: str
    latest_closed_5m_hash: str
    registry_version: str
    registry_hash: str
    strategy_version: str
    parameter_version: str
    evaluation_boundary_ms: int
    input_ledger_hash: str
    output_ledger_hash: str
    evaluation_mode: BoundaryMode
    result: KernelResult

    @property
    def decision_ids(self) -> tuple[str, ...]:
        return tuple(
            _typed_hash("strategy-decision", _canonical_dataclass(decision))
            for decision in self.result.decisions
        )


@dataclass(frozen=True)
class ScannerCompositionReceipt:
    scan_receipt: ScannerRunReceipt
    market_id: str
    selected_candidate: ScannerCandidate | None
    selected_candidate_record: EvidenceCandidate | None
    raw_discovery: ScannerCandidate | None
    raw_discovery_suppressed: bool


@dataclass(frozen=True)
class RetainedFormalDecision:
    strategy_evaluation_id: str
    strategy_decision_id: str
    market_id: str
    source_open_time_ms: int


@dataclass(frozen=True)
class FormalizationArtifacts:
    decision: StrategyDecision
    plan: PlanDraft
    provenance: ProvenanceRecord
    market_event: EvidenceMarketEvent
    signal: FormalSignal
    plan_record: PlanRecord
    shadow_order: ShadowOrder
    outbox_receipt: EnqueueReceipt
    notification_reference: NotificationOutboxReference
    outcome_attached: bool


class MultiAssetShadowCoordinator:
    """Direct coordinator for one accepted public-data Shadow route."""

    def __init__(
        self,
        *,
        registry: MarketRegistryManager,
        data_authority: MultiAssetDataAuthority,
        evidence: EvidenceStore,
        outbox: EvidenceOutbox,
        outcome_engine: OutcomeEngine,
        outcome_adapter: EvidenceOutcomeAdapter,
        planning_data: PublicPlanningData,
        cost_model: CostModel,
        release_sha: str,
        runtime_readiness: RuntimeReadinessAuthority,
    ) -> None:
        if outbox.evidence_store is not evidence or outcome_adapter.evidence_store is not evidence:
            raise IntegrationError("outbox and outcome persistence must use the Evidence store")
        if outcome_engine.sink is not outcome_adapter:
            raise IntegrationError("Outcome Engine sink must be the Evidence adapter")
        if isinstance(outcome_engine.provider, EvidenceOneMinuteProvider):
            if outcome_engine.provider.adapter is not outcome_adapter:
                raise IntegrationError("1m provider persistence must use the Evidence adapter")
        elif outcome_engine.provider is not None:
            outcome_engine.provider = EvidenceOneMinuteProvider(
                provider=outcome_engine.provider,
                adapter=outcome_adapter,
            )
        if len(release_sha) != 40 or any(value not in "0123456789abcdef" for value in release_sha):
            raise IntegrationError("release_sha must be exact lowercase git SHA-1")
        self._registry = registry
        self._data = data_authority
        self._evidence = evidence
        self._outbox = outbox
        self._outcome = outcome_engine
        self._outcome_adapter = outcome_adapter
        self._planning_data = planning_data
        self._cost_model = cost_model
        self._release_sha = release_sha
        self._runtime_readiness = runtime_readiness
        self._ledgers: dict[str, EventLedger] = {}
        self._restore_ledgers()

    def _restore_ledgers(self) -> None:
        active = self._registry.active()
        if active is None:
            # A new deployment may have a validated acquisition Registry staged
            # before its first provider-admitted closed boundary.  It has no
            # application authority to restore, and the pending Registry must
            # not become one by implication.
            if self._registry.pending_version() is None:
                raise IntegrationError("no active Registry authority")
            retained = self._evidence._connection.execute(
                """SELECT EXISTS(SELECT 1 FROM immutable_records)
                   OR EXISTS(SELECT 1 FROM notification_outbox)"""
            ).fetchone()
            if retained is None:  # pragma: no cover - SQLite SELECT always returns one row
                raise IntegrationError("unable to inspect retained application evidence")
            if bool(retained[0]):
                raise IntegrationError(
                    "cannot restore retained application evidence without active Registry authority"
                )
            return
        latest: dict[str, tuple[int, EventLedger]] = {}
        authority_slots: set[tuple[str, str, str, str, str, int, int]] = set()
        for record_id in _record_ids(self._evidence, "strategy_evaluation"):
            record = self._evidence.get(record_id)
            if not isinstance(record, StrategyEvaluation):
                continue
            payload = record.payload
            if (
                payload.get("registry_version") != active.version
                or payload.get("strategy_version") != STRATEGY_VERSION
                or payload.get("parameter_version") != PARAMETER_VERSION
            ):
                continue
            if payload.get("registry_hash") != active.content_hash:
                raise IntegrationError(
                    "Registry version has conflicting retained strategy authority"
                )
            market_id = str(payload["market_id"])
            source_open_time_ms = int(payload.get("source_open_time_ms", -1))
            evaluation_boundary_ms = int(payload["evaluation_boundary_ms"])
            slot = (
                STRATEGY_VERSION,
                PARAMETER_VERSION,
                active.version,
                market_id,
                str(payload.get("source_interval", "")),
                source_open_time_ms,
                evaluation_boundary_ms,
            )
            if slot in authority_slots:
                raise IntegrationError("duplicate retained Strategy authority checkpoint")
            authority_slots.add(slot)
            ledger = _kernel_result_from_payload(payload).ledger
            prior = latest.get(market_id)
            if prior is None or source_open_time_ms > prior[0]:
                latest[market_id] = (source_open_time_ms, ledger)
        self._ledgers = {market_id: value[1] for market_id, value in latest.items()}

    def strategy_recovery_boundaries(
        self, *, market_id: str, current_source_open_time_ms: int
    ) -> tuple[int, ...]:
        """Derive missing chronological checkpoints from retained evidence and bars.

        Retained Strategy authority for a boundary dominates across Registry
        epochs: an evaluation bound to a predecessor Registry is valid history,
        never corruption, and is never re-created under a newer Registry.  Only
        an evaluation claiming the *active* version with a wrong hash is a
        conflict.
        """
        active = self._active_registry()
        latest: int | None = None
        seen: set[int] = set()
        for record_id in _record_ids(self._evidence, "strategy_evaluation"):
            record = self._evidence.get(record_id)
            if not isinstance(record, StrategyEvaluation):
                continue
            payload = record.payload
            if (
                payload.get("market_id") != market_id
                or payload.get("strategy_version") != STRATEGY_VERSION
                or payload.get("parameter_version") != PARAMETER_VERSION
            ):
                continue
            boundary = int(payload.get("source_open_time_ms", -1))
            if boundary in seen:
                raise IntegrationError("duplicate retained Strategy boundary authority")
            seen.add(boundary)
            if (
                payload.get("registry_version") == active.version
                and payload.get("registry_hash") != active.content_hash
            ):
                raise IntegrationError("retained Strategy checkpoint conflicts with Registry")
            latest = boundary if latest is None else max(latest, boundary)
        if latest is not None and latest > current_source_open_time_ms:
            raise IntegrationError("Strategy checkpoint is ahead of requested boundary")
        if latest == current_source_open_time_ms:
            return ()
        rows = self._data.store.connection.execute(
            """SELECT open_time_ms, registry_version, registry_content_hash
               FROM closed_bars
               WHERE market_id = ? AND interval = '5m' AND open_time_ms <= ?
               ORDER BY open_time_ms""",
            (market_id, current_source_open_time_ms),
        ).fetchall()
        available = tuple(int(row[0]) for row in rows)
        bindings = tuple((row[1], row[2]) for row in rows)
        if not available or available[-1] != current_source_open_time_ms:
            raise IntegrationError("requested Strategy recovery boundary is unavailable")
        if latest is None:
            fifteen_minute_opens = tuple(
                int(row[0])
                for row in self._data.store.connection.execute(
                    """SELECT open_time_ms FROM closed_bars
                       WHERE market_id = ? AND interval = '15m'
                       ORDER BY open_time_ms""",
                    (market_id,),
                )
            )
            # The frozen Kernel requires M20 plus a current A15. Earlier
            # prefixes remain data context but are not valid Strategy inputs.
            # Only rows already bound to the active Registry epoch may become
            # NEW evaluation checkpoints; predecessor-epoch rows are historical
            # context that must not gain retrospective action.
            active_binding = (active.version, active.content_hash)
            eligible = tuple(
                boundary
                for index, boundary in enumerate(available)
                if index >= 20
                and bindings[index] == active_binding
                and sum(
                    open_time_ms + 600_000 <= boundary
                    for open_time_ms in fifteen_minute_opens
                )
                >= 15
            )
            if not eligible:
                raise IntegrationError("Strategy recovery context is insufficient")
            return eligible
        missing = tuple(boundary for boundary in available if boundary > latest)
        if not missing or missing[-1] != current_source_open_time_ms:
            raise IntegrationError("Strategy recovery cannot reach requested boundary")
        return missing

    def has_retained_strategy_evaluation(
        self,
        *,
        market_id: str,
        source_open_time_ms: int,
        any_registry_epoch: bool = False,
    ) -> bool:
        """Report exact durable Strategy completion under current authority.

        With ``any_registry_epoch`` the check honors retained authority from
        predecessor Registry epochs too: a boundary already evaluated under an
        older epoch is never re-evaluated under a newer Registry.
        """
        active = self._active_registry()
        matches: list[StrategyEvaluation] = []
        for record_id in _record_ids(self._evidence, "strategy_evaluation"):
            record = self._evidence.get(record_id)
            if not isinstance(record, StrategyEvaluation):
                continue
            payload = record.payload
            if (
                payload.get("market_id") != market_id
                or payload.get("source_open_time_ms") != source_open_time_ms
                or payload.get("strategy_version") != STRATEGY_VERSION
                or payload.get("parameter_version") != PARAMETER_VERSION
            ):
                continue
            if not any_registry_epoch and payload.get("registry_version") != active.version:
                continue
            if (
                payload.get("registry_version") == active.version
                and payload.get("registry_hash") != active.content_hash
            ):
                raise IntegrationError("retained Strategy checkpoint conflicts with Registry")
            matches.append(record)
        if len(matches) > 1:
            raise IntegrationError("duplicate retained Strategy boundary authority")
        return bool(matches)

    def _active_registry(self) -> RegistryVersion:
        active = self._registry.active()
        if active is None:
            raise IntegrationError("no active Registry authority")
        return active

    def _readiness(self) -> RuntimeReadinessSnapshot:
        snapshot = self._runtime_readiness.readiness_snapshot()
        active = self._active_registry()
        if (
            snapshot.registry_version != active.version
            or snapshot.registry_content_hash != active.content_hash
        ):
            raise IntegrationError("runtime readiness does not bind active Registry authority")
        if not snapshot.data_ready:
            raise IntegrationError("runtime is disconnected or data is not ready")
        return snapshot

    def _market(
        self,
        market_id: str,
        *,
        allow_draining: bool = False,
        readiness: RuntimeReadinessSnapshot | None = None,
    ) -> RegistryMarket:
        active = self._active_registry()
        market = next(
            (item for item in active.markets if item.identity.market_id == market_id), None
        )
        if market is None:
            raise IntegrationError("market is absent from the active Registry")
        allowed = {MarketLifecycle.ACTIVE}
        if allow_draining:
            allowed.add(MarketLifecycle.DRAINING)
        if market.lifecycle not in allowed:
            raise IntegrationError("market lifecycle prohibits new activity")
        if not allow_draining:
            snapshot = readiness or self._readiness()
            if (
                market_id in snapshot.failed_market_ids
                or market_id not in snapshot.ready_market_ids
            ):
                raise IntegrationError("runtime readiness prohibits new activity")
            if not self._data.can_formalize(market):
                raise IntegrationError("market data authority prohibits new activity")
        return market

    def _retained_closed_5m(
        self,
        market: RegistryMarket,
        *,
        readiness: RuntimeReadinessSnapshot,
        source_open_time_ms: int | None = None,
    ) -> tuple[ClosedBar, ...]:
        active = self._active_registry()
        rows = self._data.store.connection.execute(
            """SELECT payload_json, registry_version, registry_content_hash
               FROM closed_bars
               WHERE market_id = ? AND interval = '5m'
               ORDER BY open_time_ms""",
            (market.identity.market_id,),
        ).fetchall()
        if not rows:
            raise IntegrationError("market has no retained provider-finalized 5m evidence")
        all_values = tuple(ClosedBar.model_validate_json(row[0]) for row in rows)
        requested = (
            readiness.latest_closed_5m_open_time_ms
            if source_open_time_ms is None
            else source_open_time_ms
        )
        if requested > readiness.latest_closed_5m_open_time_ms:
            raise IntegrationError("requested Strategy boundary is ahead of runtime authority")
        indexes = tuple(
            index for index, value in enumerate(all_values) if value.open_time_ms <= requested
        )
        if not indexes or all_values[indexes[-1]].open_time_ms != requested:
            raise IntegrationError("requested closed 5m boundary is not retained")
        last_index = indexes[-1]
        selected = rows[last_index]
        if selected[1] != active.version or selected[2] != active.content_hash:
            raise IntegrationError("selected 5m boundary is not bound to active Registry authority")
        return all_values[: last_index + 1]

    def _resolve_scanner_linkage(
        self,
        *,
        market_id: str,
        linkage: ScannerLinkage | None,
        candidate_record_id: str | None = None,
    ) -> tuple[ScannerLinkage | None, EvidenceCandidate | None]:
        if linkage is None:
            if candidate_record_id is not None:
                raise IntegrationError("Candidate record requires typed Scanner linkage")
            return None, None
        if candidate_record_id is not None:
            exact = self._evidence.get(candidate_record_id)
            matches = [exact] if isinstance(exact, EvidenceCandidate) else []
        else:
            matches = []
            for record_id in _record_ids(self._evidence, "candidate"):
                record = self._evidence.get(record_id)
                if (
                    isinstance(record, EvidenceCandidate)
                    and record.payload.get("scanner_candidate_id") == linkage.candidate_id
                    and record.payload.get("state") == linkage.state.value
                ):
                    matches.append(record)
        if len(matches) != 1:
            raise IntegrationError("Scanner linkage does not resolve to one retained Candidate")
        candidate = matches[0]
        payload = candidate.payload
        scan = self._evidence.get(str(payload.get("scanner_evidence_id")))
        active = self._active_registry()
        content = payload.get("candidate_content")
        observations = None if not isinstance(scan, ScannerEvidence) else scan.payload.get(
            "observations"
        )
        if (
            not isinstance(scan, ScannerEvidence)
            or scan.payload.get("scan_id") != payload.get("scan_id")
            or scan.payload.get("scanner_version") != SCANNER_VERSION
            or scan.payload.get("parameter_version") != PARAMETER_VERSION
            or scan.payload.get("registry_version") != active.version
            or scan.payload.get("registry_hash") != active.content_hash
            or payload.get("market_id") != market_id
            or payload.get("state") != linkage.state.value
            or payload.get("scanner_version") != linkage.scanner_version
            or payload.get("scanner_version") != SCANNER_VERSION
            or payload.get("parameter_version") != PARAMETER_VERSION
            or not isinstance(content, dict)
            or content.get("candidate_id") != linkage.candidate_id
            or content.get("market_id") != market_id
            or content.get("state") != linkage.state.value
            or content.get("side") != payload.get("side")
            or content.get("scanner_version") != payload.get("scanner_version")
            or content.get("parameter_version") != payload.get("parameter_version")
            or payload.get("candidate_content_hash")
            != _typed_hash("scanner-candidate", content)
            or not isinstance(observations, list)
            or not any(
                isinstance(observation, dict)
                and observation.get("market_id") == market_id
                and observation.get("candidate") == content
                for observation in observations
            )
        ):
            raise IntegrationError("Scanner linkage contradicts retained Scanner authority")
        return (
            ScannerLinkage(
                candidate_id=str(payload["scanner_candidate_id"]),
                state=ScannerState(str(payload["state"])),
                scanner_version=str(payload["scanner_version"]),
            ),
            candidate,
        )

    def _causal_candidate_record_id(
        self,
        *,
        decision: StrategyDecision,
        current_linkage: ScannerLinkage | None,
        current_candidate: EvidenceCandidate | None,
    ) -> str | None:
        """Carry the Candidate record frozen when a Strategy event was created."""
        linkage = decision.scanner_linkage
        if linkage is None:
            return None
        matches: set[str] = set()
        for record_id in _record_ids(self._evidence, "strategy_evaluation"):
            record = self._evidence.get(record_id)
            if not isinstance(record, StrategyEvaluation):
                continue
            decisions = record.payload.get("decisions")
            if not isinstance(decisions, list):
                raise IntegrationError("retained Strategy decisions are invalid")
            for item in decisions:
                if not isinstance(item, dict):
                    raise IntegrationError("retained Strategy decision is invalid")
                prior = _decision_from_payload(item.get("content"))
                candidate_id = item.get("scanner_candidate_record_id")
                if (
                    prior.market_event_id == decision.market_event_id
                    and prior.scanner_linkage == linkage
                    and isinstance(candidate_id, str)
                ):
                    matches.add(candidate_id)
        if len(matches) > 1:
            raise IntegrationError(
                "Strategy decision lacks one frozen causal Candidate record"
            )
        if matches:
            candidate_id = next(iter(matches))
        elif current_linkage == linkage and current_candidate is not None:
            candidate_id = current_candidate.record_id
        else:
            raise IntegrationError(
                "Strategy decision lacks one frozen causal Candidate record"
            )
        self._resolve_scanner_linkage(
            market_id=decision.market_id,
            linkage=linkage,
            candidate_record_id=candidate_id,
        )
        return candidate_id

    @staticmethod
    def _evaluation_receipt(record: StrategyEvaluation) -> EvaluationReceipt:
        payload = record.payload
        return EvaluationReceipt(
            evaluation_id=str(payload["evaluation_id"]),
            evaluation_record_id=record.record_id,
            evaluation_record_hash=record.canonical_hash,
            market_id=str(payload["market_id"]),
            latest_closed_5m_hash=str(payload["latest_closed_5m_hash"]),
            registry_version=str(payload["registry_version"]),
            registry_hash=str(payload["registry_hash"]),
            strategy_version=str(payload["strategy_version"]),
            parameter_version=str(payload["parameter_version"]),
            evaluation_boundary_ms=int(payload["evaluation_boundary_ms"]),
            input_ledger_hash=str(payload["input_ledger_hash"]),
            output_ledger_hash=str(payload["output_ledger_hash"]),
            evaluation_mode=BoundaryMode(str(payload["evaluation_mode"])),
            result=_kernel_result_from_payload(payload),
        )

    @staticmethod
    def _strategy_bar(value: ClosedBar) -> Bar:
        return Bar(
            market_id=value.market_id,
            interval=value.interval,
            open_time_ms=value.open_time_ms,
            close_time_ms=value.close_time_ms,
            open=value.open,
            high=value.high,
            low=value.low,
            close=value.close,
            volume=value.volume,
            source_identity=value.canonical_hash,
        )

    def evaluate_finalized_market(
        self,
        *,
        market_id: str,
        zone_book: ZoneBook | None = None,
        scanner_linkage: ScannerLinkage | None = None,
        scanner_candidate_record_id: str | None = None,
        source_open_time_ms: int | None = None,
        evaluation_mode: BoundaryMode = BoundaryMode.LIVE_ACTIONABLE,
    ) -> EvaluationReceipt:
        if zone_book is not None:
            raise IntegrationError(
                "production strategy authority requires canonical ZoneBook input"
            )
        readiness = self._readiness()
        market = self._market(market_id, readiness=readiness)
        if evaluation_mode is not BoundaryMode.LIVE_ACTIONABLE and (
            scanner_linkage is not None or scanner_candidate_record_id is not None
        ):
            raise IntegrationError(
                "context-only Strategy evaluation cannot receive Scanner linkage"
            )
        retained = self._retained_closed_5m(
            market,
            readiness=readiness,
            source_open_time_ms=source_open_time_ms,
        )
        bars_5m = tuple(self._strategy_bar(item) for item in retained)
        bars_15m = aggregate_closed_5m_causally(bars_5m, minutes=15)
        bars_1h = aggregate_closed_5m_causally(bars_5m, minutes=60)
        tick = minimum_tick(
            bars_5m[-1].close,
            max_decimals=market.price_max_decimals,
            significant_figures=market.price_max_significant_figures,
        )
        canonical_linkage, retained_candidate = self._resolve_scanner_linkage(
            market_id=market_id,
            linkage=scanner_linkage,
            candidate_record_id=scanner_candidate_record_id,
        )
        active = self._active_registry()
        evaluation_boundary_ms = retained[-1].close_time_ms + 1
        authority_slot = {
            "strategy_version": STRATEGY_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "registry_version": active.version,
            "market_id": market_id,
            "source_interval": "5m",
            "source_open_time_ms": retained[-1].open_time_ms,
            "evaluation_boundary_ms": evaluation_boundary_ms,
        }
        evaluation_id = _typed_hash("strategy-evaluation-authority", authority_slot)
        authoritative_input = {
            "source_bars": [
                {
                    "open_time_ms": item.open_time_ms,
                    "canonical_hash": item.canonical_hash,
                }
                for item in retained
            ],
            "minimum_tick": _decimal(tick),
            "scanner_candidate_record_id": (
                None if retained_candidate is None else retained_candidate.record_id
            ),
            "scanner_evidence_id": (
                None
                if retained_candidate is None
                else retained_candidate.payload.get("scanner_evidence_id")
            ),
            "scanner_linkage": (
                None
                if canonical_linkage is None
                else _canonical_dataclass(canonical_linkage)
            ),
        }
        authoritative_input_hash = _typed_hash("strategy-authoritative-input", authoritative_input)
        existing = tuple(
            record
            for row in self._evidence._connection.execute(
                """SELECT record_id FROM immutable_records
                   WHERE record_type = 'strategy_evaluation'
                   AND json_extract(payload_json, '$.evaluation_id') = ?""",
                (evaluation_id,),
            )
            if isinstance(
                (record := self._evidence.get(str(row["record_id"]))),
                StrategyEvaluation,
            )
        )
        if len(existing) > 1:
            raise IntegrationError("Strategy authority slot has multiple retained truths")
        if existing:
            record = existing[0]
            payload = record.payload
            expected = {
                **authority_slot,
                "evaluation_id": evaluation_id,
                "latest_closed_5m_hash": retained[-1].canonical_hash,
                "runtime_readiness_hash": readiness.snapshot_hash,
                "registry_hash": active.content_hash,
                "release_sha": self._release_sha,
                "authoritative_input_hash": authoritative_input_hash,
                "authoritative_input": authoritative_input,
                "evaluation_mode": evaluation_mode.value,
            }
            if any(payload.get(name) != value for name, value in expected.items()):
                raise IntegrationError("Strategy authority slot conflicts with current context")
            return self._evaluation_receipt(record)

        current_ledger = self._ledgers.get(market_id, EventLedger())
        result = evaluate_strategy(
            StrategyEvaluationInput(
                bars_5m=bars_5m,
                minimum_tick=tick,
                bars_15m=bars_15m,
                bars_1h=bars_1h,
                zone_book=None,
                scanner_linkage=canonical_linkage,
                mandatory_data_valid=True,
            ),
            current_ledger,
        )
        input_ledger = _ledger_payload(current_ledger)
        output_ledger = _ledger_payload(result.ledger)
        input_hash = _typed_hash("event-ledger", input_ledger)
        output_hash = _typed_hash("event-ledger", output_ledger)
        decisions = tuple(
            {
                "decision_id": _typed_hash("strategy-decision", _canonical_dataclass(decision)),
                "content": _canonical_dataclass(decision),
                "scanner_candidate_record_id": self._causal_candidate_record_id(
                    decision=decision,
                    current_linkage=canonical_linkage,
                    current_candidate=retained_candidate,
                ),
            }
            for decision in result.decisions
        )
        record = StrategyEvaluation.create(
            identity=authority_slot,
            evaluation_id=evaluation_id,
            market_id=market_id,
            latest_closed_5m_hash=retained[-1].canonical_hash,
            source_interval="5m",
            source_open_time_ms=retained[-1].open_time_ms,
            evaluation_boundary_ms=evaluation_boundary_ms,
            runtime_readiness_hash=readiness.snapshot_hash,
            registry_version=active.version,
            registry_hash=active.content_hash,
            strategy_version=STRATEGY_VERSION,
            parameter_version=PARAMETER_VERSION,
            release_sha=self._release_sha,
            evaluation_mode=evaluation_mode.value,
            authoritative_input_hash=authoritative_input_hash,
            authoritative_input=authoritative_input,
            input_ledger_hash=input_hash,
            output_ledger_hash=output_hash,
            output_ledger=output_ledger,
            decisions=decisions,
            zones=[_canonical_dataclass(item) for item in result.zones],
            active_support=(
                None
                if result.active_support is None
                else _canonical_dataclass(result.active_support)
            ),
            active_resistance=(
                None
                if result.active_resistance is None
                else _canonical_dataclass(result.active_resistance)
            ),
            htf_context=_canonical_dataclass(result.htf_context),
        )
        self._evidence._write_controlled((record,))
        self._ledgers[market_id] = result.ledger
        return EvaluationReceipt(
            evaluation_id=evaluation_id,
            evaluation_record_id=record.record_id,
            evaluation_record_hash=record.canonical_hash,
            market_id=market_id,
            latest_closed_5m_hash=retained[-1].canonical_hash,
            registry_version=active.version,
            registry_hash=active.content_hash,
            strategy_version=STRATEGY_VERSION,
            parameter_version=PARAMETER_VERSION,
            evaluation_boundary_ms=evaluation_boundary_ms,
            input_ledger_hash=input_hash,
            output_ledger_hash=output_hash,
            evaluation_mode=evaluation_mode,
            result=result,
        )

    def scan_finalized(
        self,
        snapshots: Mapping[str, ScannerPublicSnapshot],
        *,
        observed_at: datetime,
        evaluation_mode: BoundaryMode = BoundaryMode.LIVE_ACTIONABLE,
    ) -> ScannerRunReceipt:
        if evaluation_mode is not BoundaryMode.LIVE_ACTIONABLE:
            raise IntegrationError("Scanner is disabled for context-only boundaries")
        observed = _utc(observed_at, "observed_at")
        readiness = self._readiness()
        active = self._active_registry()
        active_markets = tuple(
            market
            for market in active.markets
            if market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id in readiness.ready_market_ids
        )
        active_ids = {market.identity.market_id for market in active_markets}
        if set(snapshots) != active_ids:
            raise IntegrationError("Scanner cadence requires every runtime-ready ACTIVE market")
        inputs: list[ScannerMarketInput] = []
        source_bars: list[dict[str, object]] = []
        for market in active_markets:
            self._market(market.identity.market_id, readiness=readiness)
            retained = self._retained_closed_5m(market, readiness=readiness)
            bars = tuple(self._strategy_bar(item) for item in retained)
            source_bars.append(
                {
                    "market_id": market.identity.market_id,
                    "latest_closed_5m_hash": retained[-1].canonical_hash,
                    "bars": [
                        {
                            "open_time_ms": item.open_time_ms,
                            "canonical_hash": item.canonical_hash,
                        }
                        for item in retained[-37:]
                    ],
                    "public_snapshot": _canonical_dataclass(
                        snapshots[market.identity.market_id]
                    ),
                }
            )
            snapshot = snapshots[market.identity.market_id]
            inputs.append(
                ScannerMarketInput(
                    market_id=market.identity.market_id,
                    bars_5m=bars,
                    minimum_tick=minimum_tick(
                        bars[-1].close,
                        max_decimals=market.price_max_decimals,
                        significant_figures=market.price_max_significant_figures,
                    ),
                    current_spread_price=snapshot.current_spread_price,
                    liquidity_healthy=snapshot.liquidity_healthy,
                    btc_returns=snapshot.btc_returns,
                )
            )
        observations = scan_cross_section(tuple(inputs))
        observation_payload = [_canonical_dataclass(item) for item in observations]
        universe_hash = _typed_hash("scanner-ready-universe", source_bars)
        observations_hash = _typed_hash("scanner-observations", observation_payload)
        scan_boundary_open_time_ms = readiness.latest_closed_5m_open_time_ms
        authority_slot = {
            "scanner_version": SCANNER_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "registry_version": active.version,
            "source_interval": "5m",
            "scan_boundary_open_time_ms": scan_boundary_open_time_ms,
            "evidence_role": "RAW_DISCOVERY",
        }
        scan_id = _typed_hash(
            "scanner-run-authority",
            authority_slot,
        )
        scan = ScannerEvidence.create(
            identity=authority_slot,
            scan_id=scan_id,
            source_interval="5m",
            scan_boundary_open_time_ms=scan_boundary_open_time_ms,
            observed_at=_timestamp(observed),
            scanner_version=SCANNER_VERSION,
            parameter_version=PARAMETER_VERSION,
            registry_version=active.version,
            registry_hash=active.content_hash,
            release_sha=self._release_sha,
            runtime_readiness_hash=readiness.snapshot_hash,
            universe_snapshot_hash=universe_hash,
            ready_universe=source_bars,
            observations_hash=observations_hash,
            observations=observation_payload,
            eligible_count=len(source_bars),
            evidence_role="RAW_DISCOVERY",
        )
        self._evidence._write_controlled((scan,))
        return ScannerRunReceipt(
            scan_id=scan_id,
            scanner_evidence_id=scan.record_id,
            scanner_evidence_hash=scan.canonical_hash,
            observations=observations,
            candidate_record_ids=(),
        )

    def persist_scanner_candidate(
        self, *, receipt: ScannerRunReceipt, candidate_id: str
    ) -> EvidenceCandidate:
        scan = self._validated_scanner_receipt(receipt)
        matches = tuple(
            observation.candidate
            for observation in receipt.observations
            if observation.candidate is not None
            and observation.candidate.candidate_id == candidate_id
        )
        if len(matches) != 1:
            raise IntegrationError("Candidate was not produced by retained raw discovery")
        candidate = matches[0]
        boundary = int(scan.payload["scan_boundary_open_time_ms"])
        existing = self._candidate_records(
            market_id=candidate.market_id, boundary_open_time_ms=boundary
        )
        if len(existing) > 1:
            raise IntegrationError("Scanner boundary has multiple live Candidate authorities")
        if existing:
            if existing[0].payload.get("scanner_candidate_id") != candidate_id:
                raise IntegrationError("raw discovery is suppressed by selected live authority")
            return existing[0]
        active = self._active_breakout_candidate_records(
            market_id=candidate.market_id, before_boundary_open_time_ms=boundary
        )
        if active:
            raise IntegrationError("raw discovery is suppressed by active Breakout authority")
        return self._persist_candidate_projection(
            scan=scan,
            candidate=candidate,
            observed_at=_parse_timestamp(scan.payload["observed_at"], "Scanner observed_at"),
            prior_candidate_record=None,
            raw_scanner_evidence_id=scan.record_id,
        )

    def retained_scanner_run(
        self, *, boundary_open_time_ms: int
    ) -> ScannerRunReceipt | None:
        """Retained raw-discovery Scanner authority for a boundary.

        Retained Scanner authority dominates across Registry epochs: a run
        bound to a predecessor Registry is durable truth for its boundary and
        is never re-created under a newer Registry.  Only a run claiming the
        *active* version with a wrong hash is a conflict.
        """
        active = self._active_registry()
        matches = tuple(
            record
            for record_id in _record_ids(self._evidence, "scanner_evidence")
            if isinstance((record := self._evidence.get(record_id)), ScannerEvidence)
            and record.payload.get("scan_boundary_open_time_ms") == boundary_open_time_ms
            and record.payload.get("evidence_role", "RAW_DISCOVERY") == "RAW_DISCOVERY"
        )
        if len(matches) > 1:
            raise IntegrationError("Scanner boundary has multiple retained raw discoveries")
        if not matches:
            return None
        scan = matches[0]
        if (
            scan.payload.get("scanner_version") != SCANNER_VERSION
            or scan.payload.get("parameter_version") != PARAMETER_VERSION
        ):
            raise IntegrationError("retained Scanner run conflicts with current authority")
        if scan.payload.get("registry_version") == active.version and (
            scan.payload.get("registry_hash") != active.content_hash
        ):
            raise IntegrationError("retained Scanner run conflicts with current authority")
        payload = scan.payload.get("observations")
        if not isinstance(payload, list):
            raise IntegrationError("retained Scanner observations are invalid")
        observations = tuple(_scanner_observation_from_payload(item) for item in payload)
        return ScannerRunReceipt(
            scan_id=str(scan.payload["scan_id"]),
            scanner_evidence_id=scan.record_id,
            scanner_evidence_hash=scan.canonical_hash,
            observations=observations,
            candidate_record_ids=tuple(
                record.record_id
                for record_id in _record_ids(self._evidence, "candidate")
                if isinstance((record := self._evidence.get(record_id)), EvidenceCandidate)
                and record.payload.get("raw_scanner_evidence_id") == scan.record_id
                and record.payload.get("live_authority") is True
            ),
        )

    def compose_scanner_market(
        self, *, receipt: ScannerRunReceipt, market_id: str
    ) -> ScannerCompositionReceipt:
        """Retain raw discovery, but select at most one live path per market."""
        raw_scan = self._validated_scanner_receipt(receipt)
        boundary = int(raw_scan.payload["scan_boundary_open_time_ms"])
        raw_matches = tuple(
            observation
            for observation in receipt.observations
            if observation.market_id == market_id
        )
        if len(raw_matches) != 1:
            raise IntegrationError("Scanner run lacks one raw market observation")
        raw = raw_matches[0]
        current = self._candidate_records(
            market_id=market_id, boundary_open_time_ms=boundary
        )
        if len(current) > 1:
            raise IntegrationError("Scanner boundary has contradictory live Candidate authority")
        if current:
            selected = self._candidate_from_record(current[0])
            return ScannerCompositionReceipt(
                receipt,
                market_id,
                selected,
                current[0],
                raw.candidate,
                raw.candidate is not None and raw.candidate.candidate_id != selected.candidate_id,
            )
        active = self._active_breakout_candidate_records(
            market_id=market_id, before_boundary_open_time_ms=boundary
        )
        if len(active) > 1:
            raise IntegrationError("multiple contradictory active Breakout paths")
        observed = _parse_timestamp(raw_scan.payload["observed_at"], "Scanner observed_at")
        if active:
            prior = active[0]
            candidate = self._candidate_from_record(prior)
            readiness = self._readiness()
            market = self._market(market_id, readiness=readiness)
            retained = self._retained_closed_5m(
                market, readiness=readiness, source_open_time_ms=boundary
            )
            source = raw_scan.payload.get("ready_universe")
            if not isinstance(source, list):
                raise IntegrationError("Scanner progression lacks retained public snapshot")
            market_source = next(
                (
                    item
                    for item in source
                    if isinstance(item, dict) and item.get("market_id") == market_id
                ),
                None,
            )
            public = None if market_source is None else market_source.get("public_snapshot")
            if not isinstance(public, dict) or type(public.get("liquidity_healthy")) is not bool:
                raise IntegrationError("Scanner progression public evidence is invalid")
            progressed = advance_scanner_candidate(
                candidate,
                bars_5m=tuple(self._strategy_bar(item) for item in retained),
                current_spread_price=_as_decimal(
                    public.get("current_spread_price"), "Scanner spread"
                ),
                liquidity_healthy=bool(public["liquidity_healthy"]),
            )
            projection_scan = self._progression_scanner_evidence(
                raw_scan=raw_scan,
                raw_observation=raw,
                candidate=progressed,
                prior_candidate_record=prior,
            )
            record = self._persist_candidate_projection(
                scan=projection_scan,
                candidate=progressed,
                observed_at=observed,
                prior_candidate_record=prior,
                raw_scanner_evidence_id=raw_scan.record_id,
            )
            return ScannerCompositionReceipt(
                receipt, market_id, progressed, record, raw.candidate, raw.candidate is not None
            )
        if raw.candidate is None:
            return ScannerCompositionReceipt(receipt, market_id, None, None, None, False)
        record = self.persist_scanner_candidate(
            receipt=receipt, candidate_id=raw.candidate.candidate_id
        )
        return ScannerCompositionReceipt(
            receipt, market_id, raw.candidate, record, raw.candidate, False
        )

    def _validated_scanner_receipt(self, receipt: ScannerRunReceipt) -> ScannerEvidence:
        scan = self._evidence.get(receipt.scanner_evidence_id)
        if (
            not isinstance(scan, ScannerEvidence)
            or scan.canonical_hash != receipt.scanner_evidence_hash
            or scan.payload.get("scan_id") != receipt.scan_id
            or scan.payload.get("evidence_role", "RAW_DISCOVERY") != "RAW_DISCOVERY"
            or _typed_hash(
                "scanner-observations",
                [_canonical_dataclass(item) for item in receipt.observations],
            )
            != scan.payload.get("observations_hash")
        ):
            raise IntegrationError("Scanner receipt contradicts retained raw evidence")
        return scan

    def _candidate_records(
        self, *, market_id: str, boundary_open_time_ms: int
    ) -> tuple[EvidenceCandidate, ...]:
        return tuple(
            record
            for record_id in _record_ids(self._evidence, "candidate")
            if isinstance((record := self._evidence.get(record_id)), EvidenceCandidate)
            and record.payload.get("live_authority") is True
            and record.payload.get("market_id") == market_id
            and record.payload.get("source_boundary_open_time_ms") == boundary_open_time_ms
        )

    def _candidate_from_record(self, record: EvidenceCandidate) -> ScannerCandidate:
        payload = record.payload
        content = payload.get("candidate_content")
        if (
            not isinstance(content, dict)
            or payload.get("candidate_content_hash") != _typed_hash("scanner-candidate", content)
            or payload.get("live_authority") is not True
        ):
            raise IntegrationError("retained live Candidate content is invalid")
        candidate = _scanner_candidate_from_payload(content)
        if (
            candidate.candidate_id != payload.get("scanner_candidate_id")
            or candidate.market_id != payload.get("market_id")
            or candidate.state.value != payload.get("state")
        ):
            raise IntegrationError("retained live Candidate projection is inconsistent")
        return candidate

    def _active_breakout_candidate_records(
        self, *, market_id: str, before_boundary_open_time_ms: int
    ) -> tuple[EvidenceCandidate, ...]:
        latest: dict[str, tuple[int, EvidenceCandidate]] = {}
        slots: set[tuple[str, int]] = set()
        for record_id in _record_ids(self._evidence, "candidate"):
            record = self._evidence.get(record_id)
            if (
                not isinstance(record, EvidenceCandidate)
                or record.payload.get("live_authority") is not True
                or record.payload.get("market_id") != market_id
            ):
                continue
            boundary = int(record.payload.get("source_boundary_open_time_ms", -1))
            if boundary >= before_boundary_open_time_ms:
                continue
            candidate = self._candidate_from_record(record)
            if candidate.breakout_bar_open_time_ms is None:
                continue
            slot = (candidate.candidate_id, boundary)
            if slot in slots:
                raise IntegrationError("duplicate retained Candidate progression checkpoint")
            slots.add(slot)
            prior = latest.get(candidate.candidate_id)
            if prior is None or boundary > prior[0]:
                latest[candidate.candidate_id] = (boundary, record)
        return tuple(
            record
            for _, record in latest.values()
            if classify_scanner_state(self._candidate_from_record(record).state)
            is ScannerCandidateClass.PROGRESSION_ELIGIBLE
        )

    def _progression_scanner_evidence(
        self,
        *,
        raw_scan: ScannerEvidence,
        raw_observation: ScannerObservation,
        candidate: ScannerCandidate,
        prior_candidate_record: EvidenceCandidate,
    ) -> ScannerEvidence:
        boundary = int(raw_scan.payload["scan_boundary_open_time_ms"])
        observation = ScannerObservation(
            raw_observation.market_id, raw_observation.metrics, candidate
        )
        observation_payload = [_canonical_dataclass(observation)]
        authority_slot = {
            "scanner_version": SCANNER_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "registry_version": raw_scan.payload["registry_version"],
            "source_interval": "5m",
            "scan_boundary_open_time_ms": boundary,
            "evidence_role": "SELECTED_LIVE_PROGRESSION",
            "scanner_candidate_id": candidate.candidate_id,
        }
        record = ScannerEvidence.create(
            identity=authority_slot,
            scan_id=_typed_hash("scanner-run-authority", authority_slot),
            source_interval="5m",
            scan_boundary_open_time_ms=boundary,
            observed_at=raw_scan.payload["observed_at"],
            scanner_version=SCANNER_VERSION,
            parameter_version=PARAMETER_VERSION,
            registry_version=raw_scan.payload["registry_version"],
            registry_hash=raw_scan.payload["registry_hash"],
            release_sha=raw_scan.payload["release_sha"],
            runtime_readiness_hash=raw_scan.payload["runtime_readiness_hash"],
            universe_snapshot_hash=raw_scan.payload["universe_snapshot_hash"],
            ready_universe=raw_scan.payload["ready_universe"],
            observations_hash=_typed_hash("scanner-observations", observation_payload),
            observations=observation_payload,
            eligible_count=raw_scan.payload.get("eligible_count"),
            evidence_role="SELECTED_LIVE_PROGRESSION",
            raw_scanner_evidence_id=raw_scan.record_id,
            prior_candidate_record_id=prior_candidate_record.record_id,
        )
        self._evidence._write_controlled((record,))
        return record

    def _persist_candidate_projection(
        self,
        *,
        scan: ScannerEvidence,
        candidate: ScannerCandidate,
        observed_at: datetime,
        prior_candidate_record: EvidenceCandidate | None,
        raw_scanner_evidence_id: str,
    ) -> EvidenceCandidate:
        boundary = int(scan.payload["scan_boundary_open_time_ms"])
        content = _canonical_dataclass(candidate)
        record = EvidenceCandidate.create(
            identity={
                "scanner_candidate_id": candidate.candidate_id,
                "state": candidate.state.value,
                "source_boundary_open_time_ms": boundary,
            },
            scanner_evidence_id=scan.record_id,
            scan_id=scan.payload["scan_id"],
            scanner_candidate_id=candidate.candidate_id,
            market_id=candidate.market_id,
            state=candidate.state.value,
            side=None if candidate.side is None else candidate.side.value,
            alert_level="WATCH",
            created_at=_timestamp(observed_at),
            reason=candidate.reason,
            scanner_version=candidate.scanner_version,
            parameter_version=candidate.parameter_version,
            candidate_content=content,
            candidate_content_hash=_typed_hash("scanner-candidate", content),
            transitions=list(candidate.transitions),
            live_authority=True,
            source_boundary_open_time_ms=boundary,
            raw_scanner_evidence_id=raw_scanner_evidence_id,
            prior_candidate_record_id=(
                None if prior_candidate_record is None else prior_candidate_record.record_id
            ),
        )
        records: list[ImmutableRecord] = [record]
        for index, transition in enumerate(candidate.transitions):
            if "->" not in transition:
                raise IntegrationError("Scanner transition evidence is invalid")
            from_state, to_state = transition.split("->", 1)
            records.append(
                CandidateTransition.create(
                    identity={"candidate_id": record.record_id, "transition_index": index},
                    candidate_id=record.record_id,
                    from_state=from_state,
                    to_state=to_state,
                    transition=transition,
                    transitioned_at=_timestamp(observed_at),
                )
            )
        self._evidence._write_controlled(records)
        return record

    def publish_watch(self, view: ScannerWatchNotificationView) -> EnqueueReceipt:
        readiness = self._readiness()
        market = next(
            (
                item
                for item in self._active_registry().markets
                if item.display == view.market_display
            ),
            None,
        )
        if market is None or market.tier is not view.tier:
            raise IntegrationError("WATCH presentation does not bind Registry market")
        self._market(market.identity.market_id, readiness=readiness)
        matches: list[EvidenceCandidate] = []
        for record_id in _record_ids(self._evidence, "candidate"):
            record = self._evidence.get(record_id)
            if (
                isinstance(record, EvidenceCandidate)
                and record.payload.get("scanner_candidate_id") == view.watch_id
                and record.payload.get("market_id") == market.identity.market_id
                and record.payload.get("state") == view.scanner_r3_state
                and record.payload.get("parameter_version") == view.scanner_parameter_version
            ):
                matches.append(record)
        if matches:
            latest_boundary = max(
                int(item.payload.get("source_boundary_open_time_ms", -1)) for item in matches
            )
            matches = [
                item
                for item in matches
                if int(item.payload.get("source_boundary_open_time_ms", -1)) == latest_boundary
            ]
        if len(matches) != 1:
            raise IntegrationError("WATCH notification lacks exact retained Scanner ancestry")
        expected_side = matches[0].payload.get("side")
        if expected_side != view.side:
            raise IntegrationError("WATCH notification side contradicts retained Candidate")
        return self._outbox.enqueue(build_envelope(view=view, created_at=view.observation_time))

    def publish_research(self, view: ResearchNotificationView) -> EnqueueReceipt:
        del view
        raise IntegrationError(
            "caller-authored research is prohibited; use retained failed-breakout evidence"
        )

    def publish_failed_breakout_research(self, *, shadow_order_id: str) -> EnqueueReceipt:
        shadow = self._evidence.get(shadow_order_id)
        if not isinstance(shadow, ShadowOrder):
            raise IntegrationError("research notification has no retained ShadowOrder")
        market = self._market(str(shadow.payload["market_id"]), allow_draining=True)
        if shadow.payload.get("setup_family") != SetupFamily.BREAKOUT_RETEST.value:
            raise IntegrationError("failed-breakout research requires BREAKOUT_RETEST")
        provenance = self._evidence.get(str(shadow.payload.get("provenance_id")))
        if not isinstance(provenance, ProvenanceRecord):
            raise IntegrationError("research ShadowOrder lacks retained provenance")
        if provenance.payload.get("strategy_version") != shadow.payload.get(
            "strategy_version"
        ) or provenance.payload.get("parameter_version") != shadow.payload.get("parameter_version"):
            raise IntegrationError("research strategy provenance is inconsistent")
        projections = self._outcome_adapter.persisted_outcomes(shadow_order_id)
        if not projections:
            raise IntegrationError("no canonical failed-breakout Outcome evidence")
        outcome_record = max(
            projections,
            key=lambda item: int(item.payload.get("evaluated_at_ms", -1)),
        )
        outcome = self._outcome_adapter.canonical_outcome(outcome_record)
        if not outcome.failed_breakout:
            raise IntegrationError("no canonical failed-breakout Outcome evidence")
        research = outcome.research
        if research is None or not research.failed_breakout:
            raise IntegrationError("Outcome lacks structured failed-breakout research evidence")
        transitions: list[str] = []
        for record_id in _record_ids(self._evidence, "outcome_transition"):
            record = self._evidence.get(record_id)
            if (
                isinstance(record, OutcomeTransitionEvidence)
                and record.payload.get("shadow_order_id") == shadow_order_id
                and record.payload.get("kind")
                in {
                    TransitionKind.RETURN_INSIDE_RANGE.value,
                    TransitionKind.ACCEPTED_REENTRY.value,
                    TransitionKind.FAILED_BREAKOUT.value,
                }
            ):
                transitions.append(str(record.payload["transition_id"]))
        evidence_time = datetime.fromtimestamp(outcome.evaluated_at_ms / 1000, tz=UTC)
        view = ResearchNotificationView(
            kind=NotificationKind.RESEARCH_FAILED_BREAKOUT,
            market_display=market.display,
            tier=market.tier,
            evidence_time=evidence_time,
            side=str(shadow.payload["side"]),
            research_id=_typed_hash(
                "failed-breakout-research",
                {"shadow_order_id": shadow_order_id, "outcome_id": outcome_record.record_id},
            ),
            source_shadow_order_id=shadow_order_id,
            outcome_id=outcome_record.record_id,
            failed_transition_ids=tuple(sorted(transitions)),
            path_maturity_status=outcome.path_maturity_status.value,
            required_end_ms=outcome.required_end_ms,
            accepted_reentry_time_ms=research.accepted_reentry_time_ms,
            reclaim_status=research.reclaim_status.value,
            conflict_count=len(outcome.conflicts),
            has_gap=outcome.path_maturity_status is MaturityStatus.GAPPED,
            strategy_version=str(shadow.payload["strategy_version"]),
            parameter_version=str(shadow.payload["parameter_version"]),
        )
        return self._outbox.enqueue(build_envelope(view=view, created_at=view.evidence_time))

    def pending_formal_decisions(self) -> tuple[RetainedFormalDecision, ...]:
        """Derive pending Formal work only from immutable retained completion truth."""
        successful: set[tuple[str, str]] = set()
        for record_id in _record_ids(self._evidence, "formal_signal"):
            record = self._evidence.get(record_id)
            if not isinstance(record, FormalSignal):
                continue
            evaluation_id = record.payload.get("strategy_evaluation_id")
            decision_id = record.payload.get("strategy_decision_id")
            if isinstance(evaluation_id, str) and isinstance(decision_id, str):
                successful.add((evaluation_id, decision_id))
        completed: set[tuple[str, str]] = set()
        for record_id in _record_ids(self._evidence, "formalization_disposition"):
            record = self._evidence.get(record_id)
            if not isinstance(record, FormalizationDisposition):
                continue
            completed.add(
                (
                    str(record.payload["strategy_evaluation_id"]),
                    str(record.payload["strategy_decision_id"]),
                )
            )
        pending: list[RetainedFormalDecision] = []
        for record_id in _record_ids(self._evidence, "strategy_evaluation"):
            record = self._evidence.get(record_id)
            if not isinstance(record, StrategyEvaluation):
                continue
            payload = record.payload
            if payload.get("evaluation_mode") != BoundaryMode.LIVE_ACTIONABLE.value:
                continue
            decisions = payload.get("decisions")
            if not isinstance(decisions, list):
                raise IntegrationError("retained Strategy decisions are invalid")
            for item in decisions:
                if not isinstance(item, dict):
                    raise IntegrationError("retained Strategy decision is invalid")
                decision = _decision_from_payload(item.get("content"))
                decision_id = str(item.get("decision_id"))
                if decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
                    continue
                key = (str(payload["evaluation_id"]), decision_id)
                if key in successful or key in completed:
                    continue
                pending.append(
                    RetainedFormalDecision(
                        strategy_evaluation_id=key[0],
                        strategy_decision_id=key[1],
                        market_id=decision.market_id,
                        source_open_time_ms=int(payload["source_open_time_ms"]),
                    )
                )
        return tuple(
            sorted(
                pending,
                key=lambda item: (
                    item.source_open_time_ms,
                    item.market_id,
                    item.strategy_evaluation_id,
                    item.strategy_decision_id,
                ),
            )
        )

    def record_formalization_disposition(
        self,
        *,
        decision: RetainedFormalDecision,
        status: FormalizationDispositionStatus,
        reason: str,
        decided_at: datetime,
    ) -> FormalizationDisposition:
        return self._evidence.record_formalization_disposition(
            strategy_evaluation_id=decision.strategy_evaluation_id,
            strategy_decision_id=decision.strategy_decision_id,
            market_id=decision.market_id,
            status=status,
            reason=reason,
            decided_at=_timestamp(_utc(decided_at, "decided_at")),
            strategy_version=STRATEGY_VERSION,
            parameter_version=PARAMETER_VERSION,
            release_sha=self._release_sha,
        )

    def process_retained_formal_decision(
        self,
        *,
        strategy_evaluation_id: str,
        strategy_decision_id: str,
        now_ms: int,
    ) -> FormalizationArtifacts | PlanRejection:
        matches = tuple(
            record
            for record_id in _record_ids(self._evidence, "strategy_evaluation")
            if isinstance((record := self._evidence.get(record_id)), StrategyEvaluation)
            and record.payload.get("evaluation_id") == strategy_evaluation_id
        )
        if len(matches) != 1:
            raise IntegrationError("retained Formal decision lacks one StrategyEvaluation")
        receipt = self._evaluation_receipt(matches[0])
        return self.process_formal_decision(
            evaluation_receipt=receipt,
            decision_id=strategy_decision_id,
            now_ms=now_ms,
        )

    def _candidate_link(self, decision: StrategyDecision, candidate_id: str | None) -> str | None:
        linkage = decision.scanner_linkage
        if candidate_id is None:
            if linkage is not None:
                raise IntegrationError(
                    "scanner-linked decision requires retained Candidate evidence"
                )
            return None
        canonical_linkage, candidate = self._resolve_scanner_linkage(
            market_id=decision.market_id,
            linkage=linkage,
            candidate_record_id=candidate_id,
        )
        if candidate is None or candidate.record_id != candidate_id:
            raise IntegrationError("supplied Candidate linkage is not retained")
        payload = candidate.payload
        side = payload.get("side")
        if (
            linkage is None
            or canonical_linkage != linkage
            or decision.scanner_version != SCANNER_VERSION
            or decision.parameter_version != PARAMETER_VERSION
            or payload.get("parameter_version") != PARAMETER_VERSION
            or (side is not None and side != decision.side.value)
        ):
            raise IntegrationError(
                "supplied Candidate linkage contradicts Formal strategy evidence"
            )
        return candidate.record_id

    @staticmethod
    def resolve_structural_target(decision: StrategyDecision) -> Decimal:
        """Resolve only immutable target geometry retained by Strategy."""
        reference = decision.target_reference
        if reference is None:
            raise TargetResolutionError("formal decision has no target reference")
        if reference.price is not None:
            target = reference.price
        elif reference.kind is TargetKind.DIRECTIONAL_ZONE_SET_FROZEN:
            if not reference.frozen_directional_zones:
                raise TargetResolutionError("directional target lacks frozen zone evidence")
            first = reference.frozen_directional_zones[0]
            target = first.low if decision.side is StrategySide.LONG else first.high
        elif reference.kind is TargetKind.OPEN_SPACE_REFERENCE:
            target = (
                decision.zone_snapshot.high + decision.a5_event
                if decision.side is StrategySide.LONG
                else decision.zone_snapshot.low - decision.a5_event
            )
        else:
            raise TargetResolutionError("price-less target shape has no production resolver")
        chase = decision.chase_limit
        stop = decision.structural_stop
        if (
            not target.is_finite()
            or target <= 0
            or chase is None
            or stop is None
            or not chase.is_finite()
            or not stop.is_finite()
            or chase <= 0
            or stop <= 0
        ):
            raise TargetResolutionError("resolved target geometry is incomplete or invalid")
        if decision.side is StrategySide.LONG:
            if not stop < chase < target:
                raise TargetResolutionError("LONG target is not favorable beyond chase and stop")
        elif not target < chase < stop:
            raise TargetResolutionError("SHORT target is not favorable beyond chase and stop")
        return target

    @classmethod
    def _target(cls, decision: StrategyDecision, resolved: Decimal | None) -> Decimal:
        target = cls.resolve_structural_target(decision)
        if resolved is not None and resolved != target:
            raise TargetResolutionError("resolved target contradicts frozen Strategy target")
        return target

    def process_formal_decision(
        self,
        *,
        evaluation_receipt: EvaluationReceipt,
        decision_id: str,
        now_ms: int,
        candidate_id: str | None = None,
        resolved_structural_target: Decimal | None = None,
        correlation_market_metrics: CorrelationMarketMetrics | None = None,
        session_warning: str | None = None,
    ) -> FormalizationArtifacts | PlanRejection:
        readiness = self._readiness()
        retained_evaluation = self._evidence.get(evaluation_receipt.evaluation_record_id)
        if (
            not isinstance(retained_evaluation, StrategyEvaluation)
            or retained_evaluation.canonical_hash != evaluation_receipt.evaluation_record_hash
            or retained_evaluation.payload.get("evaluation_id") != evaluation_receipt.evaluation_id
        ):
            raise IntegrationError("evaluation receipt is not retained by this Evidence authority")
        payload = retained_evaluation.payload
        receipt_fields = (
            ("market_id", evaluation_receipt.market_id),
            ("latest_closed_5m_hash", evaluation_receipt.latest_closed_5m_hash),
            ("registry_version", evaluation_receipt.registry_version),
            ("registry_hash", evaluation_receipt.registry_hash),
            ("strategy_version", evaluation_receipt.strategy_version),
            ("parameter_version", evaluation_receipt.parameter_version),
            ("evaluation_boundary_ms", evaluation_receipt.evaluation_boundary_ms),
            ("input_ledger_hash", evaluation_receipt.input_ledger_hash),
            ("output_ledger_hash", evaluation_receipt.output_ledger_hash),
            ("evaluation_mode", evaluation_receipt.evaluation_mode.value),
        )
        if any(payload.get(name) != value for name, value in receipt_fields):
            raise IntegrationError("evaluation receipt contradicts retained Evidence content")
        retained_decisions = payload.get("decisions")
        result_decisions = tuple(
            {
                "decision_id": _typed_hash("strategy-decision", _canonical_dataclass(decision)),
                "content": _canonical_dataclass(decision),
            }
            for decision in evaluation_receipt.result.decisions
        )
        if (
            not isinstance(retained_decisions, list)
            or len(retained_decisions) != len(result_decisions)
            or any(
                not isinstance(retained, dict)
                or retained.get("decision_id") != expected["decision_id"]
                or retained.get("content") != expected["content"]
                for retained, expected in zip(
                    retained_decisions, result_decisions, strict=True
                )
            )
        ):
            raise IntegrationError("evaluation receipt StrategyDecision content was changed")
        if payload.get("output_ledger") != _ledger_payload(evaluation_receipt.result.ledger):
            raise IntegrationError("evaluation receipt EventLedger content was changed")
        decision = next(
            (
                item
                for item in evaluation_receipt.result.decisions
                if _typed_hash("strategy-decision", _canonical_dataclass(item)) == decision_id
            ),
            None,
        )
        if decision is None:
            raise IntegrationError("decision identity is absent from retained evaluation")
        retained_decision = next(
            item
            for item in retained_decisions
            if item.get("decision_id") == decision_id
        )
        if decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
            raise IntegrationError("only a Formal Setup decision can enter planning")
        if payload.get("evaluation_mode") != BoundaryMode.LIVE_ACTIONABLE.value:
            raise IntegrationError("only LIVE_ACTIONABLE decisions may be formalized")
        market = self._market(decision.market_id, readiness=readiness)
        active = self._active_registry()
        retained = self._retained_closed_5m(
            market,
            readiness=readiness,
            source_open_time_ms=int(payload["source_open_time_ms"]),
        )
        confirmed_bar = retained[-1]
        if (
            confirmed_bar.canonical_hash != evaluation_receipt.latest_closed_5m_hash
            or confirmed_bar.market_id != decision.market_id
            or evaluation_receipt.registry_version != active.version
            or evaluation_receipt.registry_hash != active.content_hash
            or evaluation_receipt.strategy_version != STRATEGY_VERSION
            or evaluation_receipt.parameter_version != PARAMETER_VERSION
        ):
            raise IntegrationError("evaluation receipt mismatches retained authority")
        authoritative_input = payload.get("authoritative_input")
        if not isinstance(authoritative_input, dict):
            raise IntegrationError("StrategyEvaluation lacks authoritative input")
        frozen_candidate_id = retained_decision.get("scanner_candidate_record_id")
        if "scanner_candidate_record_id" not in retained_decision:
            frozen_candidate_id = authoritative_input.get("scanner_candidate_record_id")
        if frozen_candidate_id is not None and not isinstance(frozen_candidate_id, str):
            raise IntegrationError("StrategyEvaluation Candidate identity is invalid")
        if candidate_id is not None and candidate_id != frozen_candidate_id:
            raise IntegrationError("caller Candidate differs from frozen causal linkage")
        candidate_record_id = self._candidate_link(decision, frozen_candidate_id)
        if decision.setup_family is SetupFamily.BREAKOUT_RETEST:
            if decision.setup_mode not in {SetupMode.MICRO_FAST, SetupMode.STANDARD}:
                raise IntegrationError("Breakout Retest has no authorized external mode")
            if decision.setup_mode is SetupMode.STANDARD and not isinstance(
                decision.retest_type, RetestType
            ):
                raise IntegrationError("STANDARD Breakout Retest lacks internal classification")
        elif decision.setup_mode is not None or decision.retest_type is not None:
            raise IntegrationError("non-breakout formal decision leaked breakout mode")
        required_prices = (
            decision.ideal_entry_low,
            decision.ideal_entry_high,
            decision.chase_limit,
            decision.structural_stop,
        )
        if any(value is None for value in required_prices):
            raise IntegrationError("formal strategy decision is missing planning terms")
        ideal_low, ideal_high, chase, stop = cast(
            tuple[Decimal, Decimal, Decimal, Decimal], required_prices
        )
        target = self._target(decision, resolved_structural_target)
        bbo = self._planning_data.fetch_bbo(market=market, now_ms=now_ms)
        side = PlanningSide(decision.side.value)
        l2 = self._planning_data.fetch_l2(market=market, side=side, bbo=bbo)
        try:
            liquidity = assess_l2(
                market_id=l2.market_id,
                coin=l2.coin,
                side=side,
                observed_at_ms=l2.observed_at_ms,
                best_bid=l2.best_bid,
                best_ask=l2.best_ask,
                levels=l2.levels,
                provenance_hash=l2.provenance_hash,
            )
        except PlanningError:
            return PlanRejection.LIQUIDITY_HARD_LIMIT
        planned = make_plan(
            PlanInputs(
                market_id=market.identity.market_id,
                side=side,
                ideal_entry_low=ideal_low,
                ideal_entry_high=ideal_high,
                chase_limit=chase,
                structural_stop=stop,
                structural_target=target,
                liquidity=liquidity,
                cost_model=self._cost_model,
                now_ms=now_ms,
                price_max_decimals=market.price_max_decimals,
                price_max_significant_figures=market.price_max_significant_figures,
                size_decimals=market.size_decimals,
                max_leverage=market.max_leverage,
            ),
            bbo,
        )
        if isinstance(planned, PlanRejection):
            return planned
        confirmed_ms = confirmed_bar.close_time_ms + 1
        confirmed_at = datetime.fromtimestamp(confirmed_ms / 1000, tz=UTC)
        provenance = ProvenanceRecord.create(
            identity={
                "strategy_version": STRATEGY_VERSION,
                "parameter_version": PARAMETER_VERSION,
                "registry_hash": active.content_hash,
                "cost_model_version": self._cost_model.version,
                "release_sha": self._release_sha,
            },
            strategy_version=STRATEGY_VERSION,
            parameter_version=PARAMETER_VERSION,
            registry_version=active.version,
            registry_hash=active.content_hash,
            cost_model_version=self._cost_model.version,
            release_sha=self._release_sha,
            recorded_at=_timestamp(active.created_at.astimezone(UTC)),
        )
        event_payload: dict[str, object] = {
            "market_id": decision.market_id,
            "event_kind": decision.setup_family.value,
            "event_time": _timestamp(confirmed_at),
            "kernel_market_event_id": decision.market_event_id,
            "setup_family": decision.setup_family.value,
            "side": decision.side.value,
            "zone_id": decision.zone_id,
            "zone_low": _decimal(decision.zone_snapshot.low),
            "zone_high": _decimal(decision.zone_snapshot.high),
            "a5_event": _decimal(decision.a5_event),
            "m20_event": _decimal(decision.m20_event),
            "htf_relation": decision.htf_relation.value,
            "confirmed_5m_hash": confirmed_bar.canonical_hash,
            "strategy_version": decision.strategy_version,
            "parameter_version": decision.parameter_version,
            "decision_reason": decision.reason,
        }
        if candidate_record_id is not None:
            event_payload["candidate_id"] = candidate_record_id
        event = EvidenceMarketEvent.create(
            identity={
                "kernel_market_event_id": decision.market_event_id,
                "strategy_version": decision.strategy_version,
                "parameter_version": decision.parameter_version,
            },
            **event_payload,
        )
        signal_payload: dict[str, object] = {
            "market_event_id": event.record_id,
            "market_id": decision.market_id,
            "setup_family": decision.setup_family.value,
            "setup_mode": None if decision.setup_mode is None else decision.setup_mode.value,
            "internal_retest_type": (
                None if decision.retest_type is None else decision.retest_type.value
            ),
            "side": decision.side.value,
            "approval_status": "APPROVED",
            "tier": market.tier.value,
            "confirmed_at": _timestamp(confirmed_at),
            "provenance_id": provenance.record_id,
            "confirmed_5m_hash": confirmed_bar.canonical_hash,
            "strategy_evaluation_id": evaluation_receipt.evaluation_id,
            "strategy_decision_id": decision_id,
        }
        if candidate_record_id is not None:
            signal_payload["candidate_id"] = candidate_record_id
        signal = FormalSignal.create(
            identity={
                "kernel_market_event_id": decision.market_event_id,
                "confirmed_5m_hash": confirmed_bar.canonical_hash,
            },
            **signal_payload,
        )
        risk_reference = {
            "reference_equity_usd": "200",
            "risk_pct_1": "1.0",
            "risk_pct_2": "2.0",
            "reference_qty_1pct": _decimal(planned.reference_qty_1pct),
            "reference_qty_2pct": _decimal(planned.reference_qty_2pct),
            "reference_notional_1pct": _decimal(planned.reference_notional_1pct),
            "reference_notional_2pct": _decimal(planned.reference_notional_2pct),
            "reference_size_only": planned.reference_size_only,
            "not_account_authoritative": planned.not_account_authoritative,
        }
        plan_record = PlanRecord.create(
            identity={"signal_id": signal.record_id, "cost_model": self._cost_model.version},
            signal_id=signal.record_id,
            planned_entry=_decimal(planned.planned_entry),
            stop=_decimal(planned.stop),
            tp1=_decimal(planned.tp1),
            tp2=_optional_decimal(planned.tp2),
            risk_reference_sizing=risk_reference,
            created_at=_timestamp(confirmed_at),
            provenance_id=provenance.record_id,
            entry_quality=planned.entry_quality.value,
            net_r_to_target=_decimal(planned.net_r_to_target),
            liquidity_provenance_hash=liquidity.provenance_hash,
        )
        shadow_payload: dict[str, object] = {
            "signal_id": signal.record_id,
            "plan_id": plan_record.record_id,
            "market_event_id": event.record_id,
            "market_id": decision.market_id,
            "setup_family": decision.setup_family.value,
            "setup_mode": None if decision.setup_mode is None else decision.setup_mode.value,
            "side": decision.side.value,
            "planned_entry": _decimal(planned.planned_entry),
            "stop": _decimal(planned.stop),
            "tp1": _decimal(planned.tp1),
            "tp2": _optional_decimal(planned.tp2),
            "risk_reference_sizing": risk_reference,
            "provenance_id": provenance.record_id,
            "strategy_version": STRATEGY_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "registry_version": active.version,
            "registry_hash": active.content_hash,
            "cost_model_version": self._cost_model.version,
            "created_at": _timestamp(confirmed_at),
            "confirmed_at": _timestamp(confirmed_at),
            "confirmed_5m_hash": confirmed_bar.canonical_hash,
            "outcome_start_ms": confirmed_ms,
            "atr": _decimal(decision.a5_event),
            "zone_low": _decimal(decision.zone_snapshot.low),
            "zone_high": _decimal(decision.zone_snapshot.high),
            "submission_status": "NOT_SUBMITTED",
        }
        if correlation_market_metrics is not None:
            shadow_payload["correlation_market_metrics"] = correlation_market_metrics.payload()
        shadow = ShadowOrder.create(
            identity={"signal_id": signal.record_id, "submission_status": "NOT_SUBMITTED"},
            **shadow_payload,
        )
        view = SignalNotificationView(
            kind=NotificationKind.FORMAL_SIGNAL,
            market_display=market.display,
            tier=market.tier,
            setup_family=decision.setup_family.value,
            setup_mode=None if decision.setup_mode is None else decision.setup_mode.value,
            side=decision.side.value,
            signal_time=confirmed_at,
            planned_entry=planned.planned_entry,
            stop=planned.stop,
            tp1=planned.tp1,
            tp2=planned.tp2,
            entry_quality=planned.entry_quality.value,
            htf_relation=decision.htf_relation.value,
            zone_context=(
                f"{decision.zone_id}:{_decimal(decision.zone_snapshot.low)}-"
                f"{_decimal(decision.zone_snapshot.high)}"
            ),
            reference_risk_sizing=(
                f"1%={_decimal(planned.reference_qty_1pct)};"
                f"2%={_decimal(planned.reference_qty_2pct)};REFERENCE_SIZE_ONLY"
            ),
            liquidity_attribution=(
                f"$1000 one-way={_decimal(liquidity.one_way_slippage_bps or Decimal())}bps;"
                f"evidence={liquidity.provenance_hash}"
            ),
            strategy_version=STRATEGY_VERSION,
            parameter_version=PARAMETER_VERSION,
            signal_id=signal.record_id,
            shadow_order_id=shadow.record_id,
            session_warning=session_warning,
        )
        envelope = build_envelope(view=view, created_at=confirmed_at)
        notification_reference = NotificationOutboxReference.create(
            identity={"signal_id": signal.record_id, "publication_id": envelope.idempotency_key},
            signal_id=signal.record_id,
            publication_id=envelope.idempotency_key,
            published_at=_timestamp(confirmed_at),
            outbox_reference=envelope.idempotency_key,
        )
        coalesced = self._evidence.publish_formal_bundle(
            records=(provenance, event, signal, plan_record, shadow),
            notification_reference=notification_reference,
            envelope=envelope,
        )
        receipt = EnqueueReceipt(envelope=envelope, coalesced=coalesced)
        attached = self._outcome.attach(
            FormalShadowView(
                shadow_order_id=shadow.record_id,
                market_id=decision.market_id,
                side=OutcomeSide(decision.side.value),
                setup_family=OutcomeSetupFamily(decision.setup_family.value),
                outcome_start_ms=confirmed_ms,
                planned_entry=planned.planned_entry,
                stop=planned.stop,
                tp1=planned.tp1,
                tp2=planned.tp2,
                atr=decision.a5_event,
                zone_low=decision.zone_snapshot.low,
                zone_high=decision.zone_snapshot.high,
            ),
            now_ms=now_ms,
            recover=False,
        )
        return FormalizationArtifacts(
            decision=decision,
            plan=planned,
            provenance=provenance,
            market_event=event,
            signal=signal,
            plan_record=plan_record,
            shadow_order=shadow,
            outbox_receipt=receipt,
            notification_reference=notification_reference,
            outcome_attached=attached,
        )

    def record_human_review(
        self,
        *,
        shadow_order_id: str,
        action: HumanReviewAction,
        actor: str,
        source: str,
        reviewed_at: datetime,
        reason_code: str | None = None,
    ) -> HumanReview:
        reviewed = _utc(reviewed_at, "reviewed_at")
        shadow = self._evidence.get(shadow_order_id)
        if not isinstance(shadow, ShadowOrder):
            raise IntegrationError("human review requires retained ShadowOrder")
        record = HumanReview.create(
            identity={
                "shadow_order_id": shadow_order_id,
                "reviewed_at": _timestamp(reviewed),
                "actor": actor,
            },
            signal_id=shadow.payload["signal_id"],
            shadow_order_id=shadow_order_id,
            action=action,
            actor=actor,
            source=source,
            reviewed_at=_timestamp(reviewed),
            reason_code=reason_code,
        )
        self._evidence.write((record,))
        return record

    def admit_outcome_transition(
        self, transition: OutcomeTransitionView, *, now_ms: int, recover: bool = True
    ) -> bool:
        """Reject caller-authored Outcome facts at the application boundary."""
        del transition, now_ms, recover
        raise IntegrationError(
            "literal Outcome transitions are prohibited; no production authority exists"
        )

    def admit_outcome_bar(self, bar: OneMinuteBar) -> AdmissionStatus:
        """Reject caller-authored 1m truth at the application boundary."""
        del bar
        raise IntegrationError(
            "caller-authored 1m bars are prohibited; use the configured OneMinuteProvider"
        )

    def recover_outcome_bars(self, *, now_ms: int) -> tuple[tuple[str, int, int], ...]:
        """Recover provider-owned 1m bars through durable Evidence admission."""
        return self._outcome.recover(now_ms=now_ms)

    def human_review_status(self, shadow_order_id: str) -> str:
        reviews: list[HumanReview] = []
        for record_id in _record_ids(self._evidence, "human_review"):
            record = self._evidence.get(record_id)
            if (
                isinstance(record, HumanReview)
                and record.payload.get("shadow_order_id") == shadow_order_id
            ):
                reviews.append(record)
        if not reviews:
            return "UNLABELED"
        latest = max(
            reviews,
            key=lambda item: (
                _parse_timestamp(item.payload["reviewed_at"], "reviewed_at"),
                item.record_id,
            ),
        )
        return str(latest.payload["action"])
