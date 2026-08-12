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
from typing import Protocol, cast

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
    FormalShadowOutcome,
    FormalShadowView,
    OneMinuteProvider,
    OutcomeEngine,
    OutcomeSink,
    PathPrimaryResult,
    ShadowState,
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
from .shadow_records import (
    Candidate as EvidenceCandidate,
)
from .shadow_records import (
    EvidenceStore,
    FormalSignal,
    HumanReview,
    HumanReviewAction,
    NotificationOutboxReference,
    OutcomeEnvelope,
    PlanRecord,
    ProvenanceRecord,
    RecordError,
    ScannerEvidence,
    ShadowOrder,
)
from .shadow_records import (
    MarketEvent as EvidenceMarketEvent,
)
from .strategy_kernel import (
    PARAMETER_VERSION,
    SCANNER_VERSION,
    STRATEGY_VERSION,
    Bar,
    DecisionKind,
    EventLedger,
    KernelResult,
    RetestType,
    ScannerCandidate,
    ScannerLinkage,
    ScannerMarketInput,
    ScannerObservation,
    SetupFamily,
    SetupMode,
    StrategyDecision,
    StrategyEvaluationInput,
    TargetKind,
    ZoneBook,
    aggregate_closed_5m_causally,
    evaluate_strategy,
    scan_cross_section,
)


class IntegrationError(ValueError):
    """Mandatory cross-lane identity or provenance is inconsistent."""


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

    def save_outcome(self, outcome: FormalShadowOutcome) -> None:
        shadow = self._store.get(outcome.shadow_order_id)
        if not isinstance(shadow, ShadowOrder):
            raise RecordError("outcome shadow_order_id is not retained")
        horizon_120 = next((item for item in outcome.horizons if item.horizon_minutes == 120), None)
        outcome_r: str | None
        if outcome.path.primary_result is PathPrimaryResult.STOP_FIRST:
            outcome_r = "-1"
        elif outcome.path.primary_result is PathPrimaryResult.TP_FIRST:
            outcome_r = "1"
        else:
            outcome_r = None
        observed_at = datetime.fromtimestamp(outcome.evaluated_at_ms / 1000, tz=UTC)
        record = OutcomeEnvelope.create(
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
        self._store.write((record,))

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
        return OutcomeEngine.reconstruct(
            shadows=tuple(views),
            transitions=(),
            bars=(),
            now_ms=now_ms,
            provider=provider,
            sink=self,
            recover=False,
        )


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
        latest: dict[str, OutcomeEnvelope] = {}
        for record_id in _record_ids(self._store, "outcome_envelope"):
            record = self._store.get(record_id)
            if not isinstance(record, OutcomeEnvelope):  # pragma: no cover
                continue
            payload = record.payload
            if payload.get("path_maturity_status") != "MATURE" or payload.get("unresolved"):
                continue
            shadow_order_id = str(payload["shadow_order_id"])
            prior = latest.get(shadow_order_id)
            if prior is None or int(payload.get("evaluated_at_ms", -1)) > int(
                prior.payload.get("evaluated_at_ms", -1)
            ):
                latest[shadow_order_id] = record
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
                        None
                        if outcome.payload.get("outcome_r") is None
                        else _as_decimal(outcome.payload["outcome_r"], "outcome_r")
                    ),
                    outcome_mfe=(
                        None
                        if outcome.payload.get("outcome_mfe") is None
                        else _as_decimal(outcome.payload["outcome_mfe"], "outcome_mfe")
                    ),
                    outcome_mae=(
                        None
                        if outcome.payload.get("outcome_mae") is None
                        else _as_decimal(outcome.payload["outcome_mae"], "outcome_mae")
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
    ) -> None:
        if outbox.evidence_store is not evidence or outcome_adapter.evidence_store is not evidence:
            raise IntegrationError("outbox and outcome persistence must use the Evidence store")
        if outcome_engine.sink is not outcome_adapter:
            raise IntegrationError("Outcome Engine sink must be the Evidence adapter")
        if len(release_sha) != 40 or any(value not in "0123456789abcdef" for value in release_sha):
            raise IntegrationError("release_sha must be exact lowercase git SHA-1")
        self._registry = registry
        self._data = data_authority
        self._evidence = evidence
        self._outbox = outbox
        self._outcome = outcome_engine
        self._planning_data = planning_data
        self._cost_model = cost_model
        self._release_sha = release_sha
        self._ledgers: dict[str, EventLedger] = {}

    def _active_registry(self) -> RegistryVersion:
        active = self._registry.active()
        if active is None:
            raise IntegrationError("no active Registry authority")
        return active

    def _market(self, market_id: str, *, allow_draining: bool = False) -> RegistryMarket:
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
        if not allow_draining and not self._data.can_formalize(market):
            raise IntegrationError("market data authority prohibits new activity")
        return market

    def _retained_closed_5m(self, market: RegistryMarket) -> tuple[ClosedBar, ...]:
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
        latest = rows[-1]
        if latest[1] != active.version or latest[2] != active.content_hash:
            raise IntegrationError("latest closed 5m bar is not bound to active Registry authority")
        return tuple(ClosedBar.model_validate_json(row[0]) for row in rows)

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
        ledger: EventLedger | None = None,
    ) -> KernelResult:
        market = self._market(market_id)
        retained = self._retained_closed_5m(market)
        bars_5m = tuple(self._strategy_bar(item) for item in retained)
        bars_15m = aggregate_closed_5m_causally(bars_5m, minutes=15)
        bars_1h = aggregate_closed_5m_causally(bars_5m, minutes=60)
        current_ledger = ledger if ledger is not None else self._ledgers.get(market_id)
        result = evaluate_strategy(
            StrategyEvaluationInput(
                bars_5m=bars_5m,
                minimum_tick=minimum_tick(
                    bars_5m[-1].close,
                    max_decimals=market.price_max_decimals,
                    significant_figures=market.price_max_significant_figures,
                ),
                bars_15m=bars_15m,
                bars_1h=bars_1h,
                zone_book=zone_book,
                scanner_linkage=scanner_linkage,
                mandatory_data_valid=True,
            ),
            current_ledger,
        )
        self._ledgers[market_id] = result.ledger
        return result

    def scan_finalized(
        self, snapshots: Mapping[str, ScannerPublicSnapshot]
    ) -> tuple[ScannerObservation, ...]:
        active = self._active_registry()
        active_markets = tuple(
            market for market in active.markets if market.lifecycle is MarketLifecycle.ACTIVE
        )
        active_ids = {market.identity.market_id for market in active_markets}
        if set(snapshots) != active_ids:
            raise IntegrationError("Scanner cadence requires every ACTIVE market exactly once")
        inputs: list[ScannerMarketInput] = []
        for market in active_markets:
            self._market(market.identity.market_id)
            bars = tuple(self._strategy_bar(item) for item in self._retained_closed_5m(market))
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
        return scan_cross_section(tuple(inputs))

    def persist_scanner_candidate(
        self, candidate: ScannerCandidate, *, observed_at: datetime
    ) -> EvidenceCandidate:
        observed = _utc(observed_at, "observed_at")
        self._market(candidate.market_id)
        active = self._active_registry()
        universe: list[dict[str, str]] = []
        for market in active.markets:
            if market.lifecycle is not MarketLifecycle.ACTIVE:
                continue
            bars = self._retained_closed_5m(market)
            universe.append(
                {
                    "market_id": market.identity.market_id,
                    "latest_closed_5m_hash": bars[-1].canonical_hash,
                }
            )
        universe_hash = sha256_hex(canonical_json_bytes(universe))
        scan_id = sha256_hex(
            canonical_json_bytes(
                {
                    "registry_hash": active.content_hash,
                    "observed_at": observed,
                    "universe_snapshot_hash": universe_hash,
                }
            )
        )
        scan = ScannerEvidence.create(
            identity={"scan_id": scan_id},
            scan_id=scan_id,
            observed_at=_timestamp(observed),
            scanner_version=SCANNER_VERSION,
            parameter_version=PARAMETER_VERSION,
            registry_version=active.version,
            registry_hash=active.content_hash,
            release_sha=self._release_sha,
            universe_snapshot_hash=universe_hash,
            eligible_count=len(universe),
        )
        record = EvidenceCandidate.create(
            identity={"scanner_candidate_id": candidate.candidate_id},
            scanner_evidence_id=scan.record_id,
            scan_id=scan_id,
            scanner_candidate_id=candidate.candidate_id,
            market_id=candidate.market_id,
            state=candidate.state.value,
            side=None if candidate.side is None else candidate.side.value,
            alert_level="WATCH",
            created_at=_timestamp(observed),
            reason=candidate.reason,
            scanner_version=candidate.scanner_version,
            parameter_version=candidate.parameter_version,
        )
        self._evidence.write((scan, record))
        return record

    def publish_watch(self, view: ScannerWatchNotificationView) -> EnqueueReceipt:
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
        self._market(market.identity.market_id)
        return self._outbox.enqueue(build_envelope(view=view, created_at=view.observation_time))

    def publish_research(self, view: ResearchNotificationView) -> EnqueueReceipt:
        shadow = self._evidence.get(view.source_shadow_order_id)
        if not isinstance(shadow, ShadowOrder):
            raise IntegrationError("research notification has no retained ShadowOrder")
        market = self._market(str(shadow.payload["market_id"]), allow_draining=True)
        if market.display != view.market_display or market.tier is not view.tier:
            raise IntegrationError("research presentation does not bind retained market")
        return self._outbox.enqueue(build_envelope(view=view, created_at=view.evidence_time))

    def _candidate_link(self, decision: StrategyDecision, candidate_id: str | None) -> str | None:
        linkage = decision.scanner_linkage
        if candidate_id is None:
            if linkage is not None:
                raise IntegrationError(
                    "scanner-linked decision requires retained Candidate evidence"
                )
            return None
        candidate = self._evidence.get(candidate_id)
        if not isinstance(candidate, EvidenceCandidate):
            raise IntegrationError("supplied Candidate linkage is not retained")
        payload = candidate.payload
        if (
            linkage is None
            or payload.get("market_id") != decision.market_id
            or payload.get("scanner_candidate_id") != linkage.candidate_id
            or payload.get("scanner_version") != linkage.scanner_version
        ):
            raise IntegrationError("supplied Candidate linkage contradicts strategy evidence")
        return candidate.record_id

    @staticmethod
    def _target(decision: StrategyDecision, resolved: Decimal | None) -> Decimal:
        reference = decision.target_reference
        if reference is None:
            raise IntegrationError("formal decision has no target reference")
        if reference.price is not None:
            if resolved is not None and resolved != reference.price:
                raise IntegrationError("resolved target contradicts frozen strategy target")
            target = reference.price
        else:
            if resolved is None:
                raise IntegrationError("price-less frozen target requires explicit resolution")
            target = resolved
            if reference.kind is TargetKind.DIRECTIONAL_ZONE_SET_FROZEN:
                if decision.side.value == "LONG" and not any(
                    zone.low <= target <= zone.high for zone in reference.frozen_directional_zones
                ):
                    raise IntegrationError("resolved target is outside frozen directional zones")
                if decision.side.value == "SHORT" and not any(
                    zone.low <= target <= zone.high for zone in reference.frozen_directional_zones
                ):
                    raise IntegrationError("resolved target is outside frozen directional zones")
        if not target.is_finite() or target <= 0:
            raise IntegrationError("resolved target must be positive and finite")
        return target

    def process_formal_decision(
        self,
        *,
        decision: StrategyDecision,
        confirmed_bar: ClosedBar,
        now_ms: int,
        candidate_id: str | None = None,
        resolved_structural_target: Decimal | None = None,
        correlation_market_metrics: CorrelationMarketMetrics | None = None,
        session_warning: str | None = None,
    ) -> FormalizationArtifacts | PlanRejection:
        if decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
            raise IntegrationError("only a Formal Setup decision can enter planning")
        market = self._market(decision.market_id)
        active = self._active_registry()
        retained = self._retained_closed_5m(market)
        if confirmed_bar != retained[-1] or confirmed_bar.market_id != decision.market_id:
            raise IntegrationError(
                "formal decision does not bind latest retained closed 5m evidence"
            )
        candidate_record_id = self._candidate_link(decision, candidate_id)
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
        self._evidence.write((provenance, event, signal, plan_record, shadow))
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
        receipt = self._outbox.enqueue(envelope)
        notification_reference = NotificationOutboxReference.create(
            identity={"signal_id": signal.record_id, "publication_id": envelope.idempotency_key},
            signal_id=signal.record_id,
            publication_id=envelope.idempotency_key,
            published_at=_timestamp(confirmed_at),
            outbox_reference=envelope.idempotency_key,
        )
        self._evidence.write((notification_reference,))
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
