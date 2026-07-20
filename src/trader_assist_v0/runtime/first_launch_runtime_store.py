"""Durable SQLite persistence for the restricted public First Launch runtime.

This module owns the local-only durability surface for the restricted public
runtime. It uses the Python standard library ``sqlite3`` module only. It does
not claim distributed persistence, high availability, or cross-instance
coordination: a single process owns one database file at a time.

The store binds the already-issued authorities (StrategyOutput, VolatilitySnapshot,
OverlayDecision, TradePlan, OperatorReviewCard, ShadowOrder) into one linked
publication bundle and pairs that bundle with a stable notification outbox row
in a single transaction. The publication bundle and the pending notification
are committed before any webhook send is attempted, so a crash between
persistence and delivery leaves a retryable pending notification. A restart
must not create a second publication bundle or notification identity for the
same already-persisted signal/plan; this is enforced by UNIQUE constraints on
``signal_id``, ``plan_id``, ``shadow_order_id`` and ``notification_id``.
"""

from __future__ import annotations

import hashlib
import sqlite3
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final, Literal, cast
from uuid import uuid4

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.operator_review import (
    OperatorReviewCard,
    OperatorReviewError,
    ShadowOrder,
    _validated_card,
    _validated_shadow,
)
from trader_assist_v0.first_launch.strategy import (
    OverlayDecision,
    PlanError,
    StrategyOutput,
    TradePlan,
    VolatilitySnapshot,
    _validated_overlay_decision,
    _validated_strategy_output,
    _validated_volatility_snapshot,
)

_RUNTIME_MODE_VALUES: Final[frozenset[str]] = frozenset(
    {"RESTRICTED_PUBLIC_LIVE_SHADOW"}
)
_SCOPE_VALUES: Final[frozenset[str]] = frozenset({"ETH_ONLY"})
_NOTIFICATION_STATUS_VALUES: Final[frozenset[str]] = frozenset(
    {"PENDING", "DELIVERED", "FAILED_CONFIGURATION"}
)
_NOTIFICATION_ID_DOMAIN: Final[bytes] = b"trader-assist-v0/first-launch/notification-id/v1"
_PUBLICATION_BUNDLE_DOMAIN: Final[bytes] = b"trader-assist-v0/first-launch/publication-bundle-id/v1"
_SCHEMA_VERSION: Final[str] = "1"
_SCHEMA_USER_VERSION: Final[int] = 1


class RuntimeStoreError(RuntimeError):
    """Raised when the local durable store rejects an operation."""


class PublicationConflictError(RuntimeStoreError):
    """Raised when a signal/plan identity already has a publication bundle."""


class PersistenceAuthorityError(RuntimeStoreError):
    """Raised when persistence ingress rejects reconstructed or unissued authority."""


class NotificationStatusError(RuntimeStoreError):
    """Raised when a notification status transition is illegal."""


class HealthTransitionError(RuntimeStoreError):
    """Raised when a recorded health transition is illegal."""


@dataclass(frozen=True)
class RuntimeSessionRecord:
    session_id: str
    runtime_mode: str
    scope: str
    process_start_time: datetime
    configuration_hash: str | None
    database_path: str
    manual_only_authority: bool
    not_submitted_authority: bool
    created_at: datetime
    closed_at: datetime | None


@dataclass(frozen=True)
class PublicationBundleRecord:
    signal_id: str
    plan_id: str
    shadow_order_id: str
    notification_id: str
    session_id: str
    strategy_output_setup_id: str
    volatility_snapshot_hash: str
    overlay_decision_hash: str
    trade_plan_canonical_hash: str
    operator_review_card_id: str
    bundle_canonical_hash: str
    strategy_output_evidence_json: str
    volatility_snapshot_json: str
    overlay_decision_json: str
    trade_plan_json: str
    operator_review_card_json: str
    shadow_order_json: str
    notification_payload_json: str
    created_at: datetime


@dataclass(frozen=True)
class NotificationOutboxRecord:
    notification_id: str
    plan_id: str
    shadow_order_id: str
    payload_json: str
    status: Literal["PENDING", "DELIVERED", "FAILED_CONFIGURATION"]
    idempotency_key: str
    attempt_count: int
    last_attempt_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class HealthEventRecord:
    event_id: str
    session_id: str
    from_state: str
    to_state: str
    reason: str
    recorded_at: datetime


def _exact_utc(value: datetime, error: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not UTC:
        raise RuntimeStoreError(error)
    return value


def _validate_runtime_mode(value: str) -> str:
    if type(value) is not str or value not in _RUNTIME_MODE_VALUES:
        raise RuntimeStoreError("runtime mode is not authorized")
    return value


def _validate_scope(value: str) -> str:
    if type(value) is not str or value not in _SCOPE_VALUES:
        raise RuntimeStoreError("scope is not authorized")
    return value


_NOTIFICATION_STATUS_LITERAL = Literal["PENDING", "DELIVERED", "FAILED_CONFIGURATION"]


def _validate_notification_status(value: str) -> _NOTIFICATION_STATUS_LITERAL:
    if value not in _NOTIFICATION_STATUS_VALUES:
        raise RuntimeStoreError("notification status is not authorized")
    return cast(_NOTIFICATION_STATUS_LITERAL, value)


def _validate_sha256(value: str, error: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise RuntimeStoreError(error)
    for character in value:
        if character not in "0123456789abcdef":
            raise RuntimeStoreError(error)
    return value


def _decimal_text(value: Decimal) -> str:
    if type(value) is not Decimal or not value.is_finite():
        raise RuntimeStoreError("decimal value is not finite")
    return str(value)


def _datetime_text(value: datetime) -> str:
    return _exact_utc(value, "datetime is not UTC").isoformat()


def _datetime_from_text(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeStoreError("datetime is not ISO-8601") from exc
    if parsed.tzinfo is not UTC:
        raise RuntimeStoreError("datetime is not UTC")
    return parsed


def _validate_publication_authorities(
    *,
    strategy_output: StrategyOutput,
    volatility_snapshot: VolatilitySnapshot,
    overlay_decision: OverlayDecision,
    trade_plan: TradePlan,
    operator_review_card: OperatorReviewCard,
    shadow_order: ShadowOrder,
) -> None:
    """Validate the complete issuance chain before opening the persistence transaction.

    The store boundary must reject direct constructor objects, ``dataclasses.replace``
    results, shallow or deep copies, coherent rehash/reconstruction, and plan/card/shadow
    substitutions.  The reuse-only modules already publish validators that bind each
    issued authority to its process-local weakref registry; the store re-runs them here
    so that no unissued reconstruction can reach the SQLite transaction.

    ``TradePlan`` is not registered in a reuse-only issuance registry, so the store
    re-runs its ``__post_init__`` (which re-validates every embedded authority and the
    plan hash) and additionally enforces identity correspondence between the plan's
    embedded authorities and the top-level authorities passed to the store.  A
    ``dataclasses.replace`` plan with a forged ``plan_id`` cannot satisfy
    ``plan_id == _trade_digest(payload)``; a substitution that swaps in a different
    issued plan cannot satisfy the identity checks.
    """
    try:
        validated_output = _validated_strategy_output(strategy_output)
        validated_volatility = _validated_volatility_snapshot(volatility_snapshot)
        validated_overlay = _validated_overlay_decision(overlay_decision)
        _validated_card(operator_review_card)
        _validated_shadow(shadow_order)
    except (PlanError, OperatorReviewError) as exc:
        raise PersistenceAuthorityError(
            "publication authority was not issued by the restricted runtime"
        ) from exc
    # TradePlan has no reuse-only issuance registry entry; re-run its post-init
    # to revalidate embedded authorities, financial consistency and the plan hash.
    try:
        trade_plan.__post_init__()
    except PlanError as exc:
        raise PersistenceAuthorityError(
            "trade plan authority was not issued by the restricted runtime"
        ) from exc
    # Identity correspondence: the plan's embedded authorities must be the very
    # same issued objects passed to the store.  This rejects plan substitution
    # even when the substitute is itself a legitimately issued plan.
    if trade_plan.strategy_output is not validated_output:
        raise PersistenceAuthorityError(
            "trade plan strategy output does not match the publication chain"
        )
    if trade_plan.volatility_snapshot is not validated_volatility:
        raise PersistenceAuthorityError(
            "trade plan volatility snapshot does not match the publication chain"
        )
    if trade_plan.overlay is not validated_overlay:
        raise PersistenceAuthorityError(
            "trade plan overlay decision does not match the publication chain"
        )
    # Cross-object correspondence already enforced below for setup_id, plan_id,
    # shadow_order_id and card identities; the validators above guarantee that
    # each object's own hash and identity are internally coherent.
    # GA-04: also require the exact TradePlan object to be the one returned by
    # build_plan(). The reuse-only authorities above only check the embedded
    # chain identities; a coherent reconstruction (``dataclasses.replace`` with
    # no field changes, ``copy.copy``, or a freshly-built plan with the same
    # legitimate embedded authorities) would otherwise satisfy the ``is`` checks
    # because it shares the exact embedded authority objects. The P3B-local
    # weakref proof below binds the plan's own object identity.
    _validate_tradeplan_proof(
        trade_plan,
        strategy_output=strategy_output,
        volatility_snapshot=volatility_snapshot,
        overlay_decision=overlay_decision,
    )


@dataclass(frozen=True)
class _TradePlanProof:
    """Immutable process-local issuance fingerprint for one TradePlan object.

    Binds the exact TradePlan object identity (its ``id()``) to its
    ``plan_id``, ``canonical_hash`` and the exact identity of each embedded
    authority object (StrategyOutput, VolatilitySnapshot, OverlayDecision).
    The proof is never serialized or persisted; it lives only for the lifetime
    of the bound plan object inside this process.
    """

    plan_id: str
    canonical_hash: str
    strategy_output_id: int
    volatility_snapshot_id: int
    overlay_decision_id: int


# Module-private weakref registry keyed by ``id(trade_plan)``. Each value is
# a ``(weakref, proof)`` pair. The weakref's callback removes the entry when
# the bound plan is garbage-collected, so the registry cannot grow without
# bound and cannot be abused to resurrect a stale proof for a freed id.
_TRADEPLAN_PROOF_REGISTRY: dict[
    int, tuple[weakref.ref[TradePlan], _TradePlanProof]
] = {}


def _tradeplan_proof_finalizer(plan_key: int) -> Callable[[weakref.ref[TradePlan]], None]:
    """Return a weakref callback that drops the proof entry when the plan dies."""

    def _finalize(_ref: weakref.ref[TradePlan]) -> None:
        _TRADEPLAN_PROOF_REGISTRY.pop(plan_key, None)

    return _finalize


def _register_tradeplan_proof(
    plan: TradePlan,
    *,
    strategy_output: StrategyOutput,
    volatility_snapshot: VolatilitySnapshot,
    overlay_decision: OverlayDecision,
) -> None:
    """Register the process-local issuance proof for one TradePlan.

    This is called by the restricted public runtime immediately after
    ``build_plan()`` returns, before the OperatorReviewCard and ShadowOrder
    are derived and before ``RuntimeStore.persist_publication_bundle`` is
    called. The proof binds the exact plan object identity to its plan_id,
    canonical_hash, and the exact identity of each embedded authority. The
    proof is private to the P3B runtime store; it is never serialized or
    persisted and is never exported from ``runtime/__init__.py``.

    Re-registering the same exact plan object is a no-op so that a legitimate
    retry with the same plan after a failed persistence transaction still
    satisfies the proof check.
    """
    plan_key = id(plan)
    proof = _TradePlanProof(
        plan_id=plan.plan_id,
        canonical_hash=plan.canonical_hash,
        strategy_output_id=id(strategy_output),
        volatility_snapshot_id=id(volatility_snapshot),
        overlay_decision_id=id(overlay_decision),
    )
    existing = _TRADEPLAN_PROOF_REGISTRY.get(plan_key)
    if existing is not None:
        existing_ref, existing_proof = existing
        if existing_ref() is plan and existing_proof == proof:
            return
    _TRADEPLAN_PROOF_REGISTRY[plan_key] = (
        weakref.ref(plan, _tradeplan_proof_finalizer(plan_key)),
        proof,
    )


def _validate_tradeplan_proof(
    plan: TradePlan,
    *,
    strategy_output: StrategyOutput,
    volatility_snapshot: VolatilitySnapshot,
    overlay_decision: OverlayDecision,
) -> None:
    """Validate that the plan is the exact object registered after build_plan().

    Rejects (raising ``PersistenceAuthorityError``) when:
    - the plan was never registered (direct constructor, ``dataclasses.replace``,
      ``copy.copy``, ``copy.deepcopy``, or coherent reconstruction);
    - the registered plan was garbage-collected and the proof no longer exists;
    - the registered proof's plan_id/canonical_hash do not match the passed plan;
    - the embedded authority identities differ from the registered proof
      (cross-bundle substitution or embedded authority swap).
    """
    plan_key = id(plan)
    entry = _TRADEPLAN_PROOF_REGISTRY.get(plan_key)
    if entry is None:
        raise PersistenceAuthorityError(
            "trade plan was not issued by the restricted runtime build_plan()"
        )
    ref, proof = entry
    if ref() is not plan:
        raise PersistenceAuthorityError(
            "trade plan identity does not match the registered proof"
        )
    if proof.plan_id != plan.plan_id:
        raise PersistenceAuthorityError(
            "trade plan plan_id does not match the registered proof"
        )
    if proof.canonical_hash != plan.canonical_hash:
        raise PersistenceAuthorityError(
            "trade plan canonical_hash does not match the registered proof"
        )
    if proof.strategy_output_id != id(strategy_output):
        raise PersistenceAuthorityError(
            "trade plan embedded strategy output identity differs from the proof"
        )
    if proof.volatility_snapshot_id != id(volatility_snapshot):
        raise PersistenceAuthorityError(
            "trade plan embedded volatility snapshot identity differs from the proof"
        )
    if proof.overlay_decision_id != id(overlay_decision):
        raise PersistenceAuthorityError(
            "trade plan embedded overlay decision identity differs from the proof"
        )


def notification_id_for_plan(plan_id: str) -> str:
    """Return the stable notification identity for a given plan identity.

    The notification identity is deterministic in the plan identity, so a
    restart that re-encounters the same already-persisted plan reuses the same
    notification identity instead of creating a second outbox row.
    """
    plan_id = _validate_sha256(plan_id, "plan identity is invalid")
    return hashlib.sha256(_NOTIFICATION_ID_DOMAIN + b"\0" + plan_id.encode("utf-8")).hexdigest()


def publication_bundle_hash(
    *,
    signal_id: str,
    plan_id: str,
    shadow_order_id: str,
    notification_id: str,
    session_id: str,
    strategy_output_evidence: dict[str, object],
    volatility_snapshot_hash: str,
    overlay_decision_hash: str,
    trade_plan_canonical_hash: str,
    operator_review_card_id: str,
) -> str:
    """Return the canonical publication bundle hash for the bound authorities."""
    payload: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "signal_id": _validate_sha256(signal_id, "signal identity is invalid"),
        "plan_id": _validate_sha256(plan_id, "plan identity is invalid"),
        "shadow_order_id": _validate_sha256(shadow_order_id, "shadow order identity is invalid"),
        "notification_id": _validate_sha256(notification_id, "notification identity is invalid"),
        "session_id": session_id,
        "strategy_output_evidence": strategy_output_evidence,
        "volatility_snapshot_hash": _validate_sha256(
            volatility_snapshot_hash, "volatility snapshot hash is invalid"
        ),
        "overlay_decision_hash": _validate_sha256(
            overlay_decision_hash, "overlay decision hash is invalid"
        ),
        "trade_plan_canonical_hash": _validate_sha256(
            trade_plan_canonical_hash, "trade plan hash is invalid"
        ),
        "operator_review_card_id": _validate_sha256(
            operator_review_card_id, "operator review card identity is invalid"
        ),
    }
    return hashlib.sha256(
        _PUBLICATION_BUNDLE_DOMAIN + b"\0" + canonical_json_bytes(payload)
    ).hexdigest()


def _strategy_output_evidence(output: StrategyOutput) -> dict[str, object]:
    return {
        "setup_id": output.setup_id,
        "speed": output.speed,
        "decision_trigger_identity": list(output.decision_trigger_identity),
        "decision_trigger_open_time_ms": output.decision_trigger_open_time_ms,
        "decision_trigger_canonical_hash": output.decision_trigger_canonical_hash,
        "decision_trigger_received_at": _datetime_text(output.decision_trigger_received_at),
        "material_extreme": _decimal_text(output.material_extreme),
        "raw_entry_low": _decimal_text(output.raw_entry_low),
        "raw_entry_high": _decimal_text(output.raw_entry_high),
        "raw_chase_limit": _decimal_text(output.raw_chase_limit),
        "raw_stop": _decimal_text(output.raw_stop),
        "created_at": _datetime_text(output.created_at),
        "expires_at": _datetime_text(output.expires_at),
        "reason": output.reason,
        "do_not_chase": output.do_not_chase,
    }


def _volatility_snapshot_payload(snapshot: VolatilitySnapshot) -> dict[str, object]:
    return {
        "current_atr": _decimal_text(snapshot.current_atr),
        "previous_48_median_atr": _decimal_text(snapshot.previous_48_median_atr),
        "atr_ratio": _decimal_text(snapshot.atr_ratio),
        "regime": snapshot.regime.value,
        "candle_cutoff_identity": list(snapshot.candle_cutoff_identity),
        "candle_cutoff_close_time_ms": snapshot.candle_cutoff_close_time_ms,
        "candle_identities": [list(item) for item in snapshot.candle_identities],
        "candle_hashes": list(snapshot.candle_hashes),
        "canonical_hash": snapshot.canonical_hash,
    }


def _overlay_decision_payload(overlay: OverlayDecision) -> dict[str, object]:
    return {
        "state": overlay.state.value,
        "actionable": overlay.actionable,
        "regime": overlay.regime.value,
        "selected_decision_span": overlay.selected_decision_span,
        "action": overlay.action,
        "reason": overlay.reason,
        "effective_raw_chase_limit": _decimal_text(overlay.effective_raw_chase_limit),
        "volatility_hash": overlay.volatility_hash,
        "rolling_30m_hash": overlay.rolling_30m_hash,
        "rolling_60m_hash": overlay.rolling_60m_hash,
        "reference_price": _decimal_text(overlay.reference_price),
        "candle_cutoff_identity": list(overlay.candle_cutoff_identity),
        "canonical_hash": overlay.canonical_hash,
        "prepared_setup_id": (
            None if overlay.prepared_setup is None else overlay.prepared_setup.setup_id
        ),
    }


def _trade_plan_payload(plan: TradePlan) -> dict[str, object]:
    payload = plan.payload()
    return cast(dict[str, object], _normalize_decimals_in_payload(payload))


def _operator_review_card_payload(card: OperatorReviewCard) -> dict[str, object]:
    return cast(dict[str, object], _normalize_decimals_in_payload(card.payload))


def _shadow_order_payload(shadow: ShadowOrder) -> dict[str, object]:
    return dict(shadow.payload())


def _normalize_decimals_in_payload(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, dict):
        return {key: _normalize_decimals_in_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_decimals_in_payload(item) for item in value]
    if isinstance(value, datetime):
        return _datetime_text(value)
    return value


def _notification_payload(
    *,
    session_id: str,
    signal_id: str,
    plan_id: str,
    shadow_order_id: str,
    notification_id: str,
    bundle_canonical_hash: str,
    trade_plan_payload: dict[str, object],
    operator_review_card_payload: dict[str, object],
    shadow_order_payload: dict[str, object],
    now: datetime,
) -> dict[str, object]:
    return {
        "notification_version": _SCHEMA_VERSION,
        "notification_id": notification_id,
        "idempotency_key": notification_id,
        "session_id": session_id,
        "signal_id": signal_id,
        "plan_id": plan_id,
        "shadow_order_id": shadow_order_id,
        "bundle_canonical_hash": bundle_canonical_hash,
        "symbol": "ETH",
        "submission_status": "NOT_SUBMITTED",
        "manual_execution_required": True,
        "trade_plan": trade_plan_payload,
        "operator_review_card": operator_review_card_payload,
        "shadow_order": shadow_order_payload,
        "created_at": _datetime_text(now),
    }


_CREATE_RUNTIME_SESSIONS = """
CREATE TABLE IF NOT EXISTS runtime_sessions (
    session_id TEXT PRIMARY KEY,
    runtime_mode TEXT NOT NULL,
    scope TEXT NOT NULL,
    process_start_time TEXT NOT NULL,
    configuration_hash TEXT,
    database_path TEXT NOT NULL,
    manual_only_authority INTEGER NOT NULL CHECK (manual_only_authority IN (0, 1)),
    not_submitted_authority INTEGER NOT NULL CHECK (not_submitted_authority IN (0, 1)),
    created_at TEXT NOT NULL,
    closed_at TEXT
);
"""

_CREATE_PUBLICATION_BUNDLES = """
CREATE TABLE IF NOT EXISTS publication_bundles (
    signal_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    shadow_order_id TEXT NOT NULL UNIQUE,
    notification_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    strategy_output_setup_id TEXT NOT NULL,
    volatility_snapshot_hash TEXT NOT NULL,
    overlay_decision_hash TEXT NOT NULL,
    trade_plan_canonical_hash TEXT NOT NULL,
    operator_review_card_id TEXT NOT NULL,
    bundle_canonical_hash TEXT NOT NULL,
    strategy_output_evidence_json TEXT NOT NULL,
    volatility_snapshot_json TEXT NOT NULL,
    overlay_decision_json TEXT NOT NULL,
    trade_plan_json TEXT NOT NULL,
    operator_review_card_json TEXT NOT NULL,
    shadow_order_json TEXT NOT NULL,
    notification_payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES runtime_sessions (session_id)
);
"""

_CREATE_NOTIFICATION_OUTBOX = """
CREATE TABLE IF NOT EXISTS notification_outbox (
    notification_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    shadow_order_id TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'DELIVERED', 'FAILED_CONFIGURATION')),
    idempotency_key TEXT NOT NULL,
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    last_attempt_at TEXT,
    delivered_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES publication_bundles (plan_id)
);
"""

_CREATE_HEALTH_EVENTS = """
CREATE TABLE IF NOT EXISTS health_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES runtime_sessions (session_id)
);
"""

_CREATE_HEALTH_EVENTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_health_events_session_recorded
    ON health_events (session_id, recorded_at);
"""

_CREATE_PUBLICATION_SESSION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_publication_bundles_session_created
    ON publication_bundles (session_id, created_at);
"""

_CREATE_OUTBOX_STATUS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_notification_outbox_status_created
    ON notification_outbox (status, created_at);
"""


class RuntimeStore:
    """Local SQLite durability for one restricted public runtime process."""

    __slots__ = ("_connection", "database_path")

    def __init__(self, *, database_path: Path) -> None:
        if not isinstance(database_path, Path):
            raise RuntimeStoreError("database path must be a Path")
        self.database_path = database_path
        connection = sqlite3.connect(
            str(database_path),
            isolation_level="DEFERRED",
            check_same_thread=True,
            timeout=30.0,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")
            self._initialize_schema(connection)
        except BaseException:
            connection.close()
            raise
        self._connection = connection

    @staticmethod
    def _initialize_schema(connection: sqlite3.Connection) -> None:
        current_user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_user_version == 0:
            connection.executescript(
                _CREATE_RUNTIME_SESSIONS
                + "\n"
                + _CREATE_PUBLICATION_BUNDLES
                + "\n"
                + _CREATE_NOTIFICATION_OUTBOX
                + "\n"
                + _CREATE_HEALTH_EVENTS
                + "\n"
                + _CREATE_HEALTH_EVENTS_INDEX
                + "\n"
                + _CREATE_PUBLICATION_SESSION_INDEX
                + "\n"
                + _CREATE_OUTBOX_STATUS_INDEX
            )
            connection.execute(f"PRAGMA user_version = {_SCHEMA_USER_VERSION}")
            connection.commit()
        elif current_user_version != _SCHEMA_USER_VERSION:
            raise RuntimeStoreError(
                f"database user_version {current_user_version} is not supported"
            )

    @classmethod
    def open(cls, database_path: Path) -> RuntimeStore:
        return cls(database_path=database_path)

    def close(self) -> None:
        try:
            self._connection.commit()
        finally:
            self._connection.close()

    def __enter__(self) -> RuntimeStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _execute(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> sqlite3.Cursor:
        return self._connection.execute(sql, parameters)

    def record_runtime_session(
        self,
        *,
        session_id: str,
        runtime_mode: str,
        scope: str,
        process_start_time: datetime,
        configuration_hash: str | None,
        database_path: Path,
        manual_only_authority: bool,
        not_submitted_authority: bool,
        now: datetime,
    ) -> RuntimeSessionRecord:
        if type(session_id) is not str or not session_id:
            raise RuntimeStoreError("session identity is invalid")
        mode = _validate_runtime_mode(runtime_mode)
        scoped = _validate_scope(scope)
        started = _exact_utc(process_start_time, "process start time is not UTC")
        timestamp = _exact_utc(now, "now is not UTC")
        if configuration_hash is not None:
            configuration_hash = _validate_sha256(
                configuration_hash, "configuration hash is invalid"
            )
        if not isinstance(database_path, Path):
            raise RuntimeStoreError("database path must be a Path")
        if type(manual_only_authority) is not bool or type(not_submitted_authority) is not bool:
            raise RuntimeStoreError("authority flags must be bool")
        record = RuntimeSessionRecord(
            session_id,
            mode,
            scoped,
            started,
            configuration_hash,
            str(database_path),
            manual_only_authority,
            not_submitted_authority,
            timestamp,
            None,
        )
        self._execute(
            "INSERT INTO runtime_sessions "
            "(session_id, runtime_mode, scope, process_start_time, configuration_hash, "
            "database_path, manual_only_authority, not_submitted_authority, created_at, closed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                record.session_id,
                record.runtime_mode,
                record.scope,
                _datetime_text(record.process_start_time),
                record.configuration_hash,
                record.database_path,
                1 if record.manual_only_authority else 0,
                1 if record.not_submitted_authority else 0,
                _datetime_text(record.created_at),
            ),
        )
        self._connection.commit()
        return record

    def close_runtime_session(self, *, session_id: str, now: datetime) -> None:
        if type(session_id) is not str or not session_id:
            raise RuntimeStoreError("session identity is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        cursor = self._execute(
            "UPDATE runtime_sessions SET closed_at = ? WHERE session_id = ? AND closed_at IS NULL",
            (_datetime_text(timestamp), session_id),
        )
        if cursor.rowcount == 0:
            raise RuntimeStoreError("runtime session is missing or already closed")
        self._connection.commit()

    def publication_exists_for_signal(self, signal_id: str) -> bool:
        signal_id = _validate_sha256(signal_id, "signal identity is invalid")
        row = self._execute(
            "SELECT 1 FROM publication_bundles WHERE signal_id = ? LIMIT 1",
            (signal_id,),
        ).fetchone()
        return row is not None

    def publication_exists_for_plan(self, plan_id: str) -> bool:
        plan_id = _validate_sha256(plan_id, "plan identity is invalid")
        row = self._execute(
            "SELECT 1 FROM publication_bundles WHERE plan_id = ? LIMIT 1",
            (plan_id,),
        ).fetchone()
        return row is not None

    def get_publication_bundle_for_signal(self, signal_id: str) -> PublicationBundleRecord:
        signal_id = _validate_sha256(signal_id, "signal identity is invalid")
        row = self._execute(
            "SELECT * FROM publication_bundles WHERE signal_id = ? LIMIT 1",
            (signal_id,),
        ).fetchone()
        if row is None:
            raise RuntimeStoreError("publication bundle is missing")
        return _row_to_publication_bundle(row)

    def persist_publication_bundle(
        self,
        *,
        session_id: str,
        strategy_output: StrategyOutput,
        volatility_snapshot: VolatilitySnapshot,
        overlay_decision: OverlayDecision,
        trade_plan: TradePlan,
        operator_review_card: OperatorReviewCard,
        shadow_order: ShadowOrder,
        now: datetime,
    ) -> tuple[PublicationBundleRecord, NotificationOutboxRecord]:
        """Atomically persist one publication bundle and its pending notification.

        The publication bundle and the pending notification outbox row are
        committed in a single transaction before this method returns. A caller
        that crashes after this commit and before the webhook send leaves a
        retryable pending notification; a restart reuses the same notification
        identity because the UNIQUE constraints on signal_id/plan_id/
        shadow_order_id/notification_id reject any second insertion.
        """
        if type(session_id) is not str or not session_id:
            raise RuntimeStoreError("session identity is invalid")
        # GA-04: validate the complete issuance chain before any side effect.
        # This rejects direct constructor objects, dataclasses.replace results,
        # shallow/deep copies, coherent rehash/reconstruction and plan/card/shadow
        # substitutions before the SQLite transaction begins.
        _validate_publication_authorities(
            strategy_output=strategy_output,
            volatility_snapshot=volatility_snapshot,
            overlay_decision=overlay_decision,
            trade_plan=trade_plan,
            operator_review_card=operator_review_card,
            shadow_order=shadow_order,
        )
        timestamp = _exact_utc(now, "now is not UTC")
        signal_id = _validate_sha256(strategy_output.setup_id, "signal identity is invalid")
        plan_id = _validate_sha256(trade_plan.plan_id, "plan identity is invalid")
        shadow_order_id = _validate_sha256(
            shadow_order.shadow_order_id, "shadow order identity is invalid"
        )
        if trade_plan.setup_id != signal_id:
            raise RuntimeStoreError("trade plan setup identity mismatch")
        if shadow_order.plan_id != plan_id:
            raise RuntimeStoreError("shadow order plan identity mismatch")
        if shadow_order.setup_id != signal_id:
            raise RuntimeStoreError("shadow order setup identity mismatch")
        card_payload = operator_review_card.payload
        if not operator_review_card.actionable:
            raise RuntimeStoreError("operator review card is not actionable")
        if card_payload["setup_id"] != signal_id:
            raise RuntimeStoreError("operator review card setup identity mismatch")
        if card_payload["plan_id"] != plan_id:
            raise RuntimeStoreError("operator review card plan identity mismatch")
        notification_id = notification_id_for_plan(plan_id)
        volatility_snapshot_hash = _validate_sha256(
            volatility_snapshot.canonical_hash, "volatility snapshot hash is invalid"
        )
        overlay_decision_hash = _validate_sha256(
            overlay_decision.canonical_hash, "overlay decision hash is invalid"
        )
        trade_plan_canonical_hash = _validate_sha256(
            trade_plan.canonical_hash, "trade plan hash is invalid"
        )
        operator_review_card_id = _validate_sha256(
            operator_review_card.card_id, "operator review card identity is invalid"
        )
        strategy_output_evidence = _strategy_output_evidence(strategy_output)
        bundle_canonical_hash = publication_bundle_hash(
            signal_id=signal_id,
            plan_id=plan_id,
            shadow_order_id=shadow_order_id,
            notification_id=notification_id,
            session_id=session_id,
            strategy_output_evidence=strategy_output_evidence,
            volatility_snapshot_hash=volatility_snapshot_hash,
            overlay_decision_hash=overlay_decision_hash,
            trade_plan_canonical_hash=trade_plan_canonical_hash,
            operator_review_card_id=operator_review_card_id,
        )
        volatility_payload = _volatility_snapshot_payload(volatility_snapshot)
        overlay_payload = _overlay_decision_payload(overlay_decision)
        trade_payload = _trade_plan_payload(trade_plan)
        card_payload = _operator_review_card_payload(operator_review_card)
        shadow_payload = _shadow_order_payload(shadow_order)
        notification_payload = _notification_payload(
            session_id=session_id,
            signal_id=signal_id,
            plan_id=plan_id,
            shadow_order_id=shadow_order_id,
            notification_id=notification_id,
            bundle_canonical_hash=bundle_canonical_hash,
            trade_plan_payload=trade_payload,
            operator_review_card_payload=card_payload,
            shadow_order_payload=shadow_payload,
            now=timestamp,
        )
        strategy_output_evidence_json = (
            canonical_json_bytes(strategy_output_evidence).decode("utf-8")
        )
        volatility_snapshot_json = canonical_json_bytes(volatility_payload).decode("utf-8")
        overlay_decision_json = canonical_json_bytes(overlay_payload).decode("utf-8")
        trade_plan_json = canonical_json_bytes(trade_payload).decode("utf-8")
        operator_review_card_json = canonical_json_bytes(card_payload).decode("utf-8")
        shadow_order_json = canonical_json_bytes(shadow_payload).decode("utf-8")
        notification_payload_json = canonical_json_bytes(notification_payload).decode("utf-8")
        created_at_text = _datetime_text(timestamp)
        bundle_record = PublicationBundleRecord(
            signal_id=signal_id,
            plan_id=plan_id,
            shadow_order_id=shadow_order_id,
            notification_id=notification_id,
            session_id=session_id,
            strategy_output_setup_id=strategy_output.setup_id,
            volatility_snapshot_hash=volatility_snapshot_hash,
            overlay_decision_hash=overlay_decision_hash,
            trade_plan_canonical_hash=trade_plan_canonical_hash,
            operator_review_card_id=operator_review_card_id,
            bundle_canonical_hash=bundle_canonical_hash,
            strategy_output_evidence_json=strategy_output_evidence_json,
            volatility_snapshot_json=volatility_snapshot_json,
            overlay_decision_json=overlay_decision_json,
            trade_plan_json=trade_plan_json,
            operator_review_card_json=operator_review_card_json,
            shadow_order_json=shadow_order_json,
            notification_payload_json=notification_payload_json,
            created_at=timestamp,
        )
        outbox_record = NotificationOutboxRecord(
            notification_id=notification_id,
            plan_id=plan_id,
            shadow_order_id=shadow_order_id,
            payload_json=notification_payload_json,
            status="PENDING",
            idempotency_key=notification_id,
            attempt_count=0,
            last_attempt_at=None,
            delivered_at=None,
            created_at=timestamp,
        )
        try:
            self._execute(
                "INSERT INTO publication_bundles "
                "(signal_id, plan_id, shadow_order_id, notification_id, session_id, "
                "strategy_output_setup_id, volatility_snapshot_hash, overlay_decision_hash, "
                "trade_plan_canonical_hash, operator_review_card_id, bundle_canonical_hash, "
                "strategy_output_evidence_json, volatility_snapshot_json, overlay_decision_json, "
                "trade_plan_json, operator_review_card_json, shadow_order_json, "
                "notification_payload_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    bundle_record.signal_id,
                    bundle_record.plan_id,
                    bundle_record.shadow_order_id,
                    bundle_record.notification_id,
                    bundle_record.session_id,
                    bundle_record.strategy_output_setup_id,
                    bundle_record.volatility_snapshot_hash,
                    bundle_record.overlay_decision_hash,
                    bundle_record.trade_plan_canonical_hash,
                    bundle_record.operator_review_card_id,
                    bundle_record.bundle_canonical_hash,
                    bundle_record.strategy_output_evidence_json,
                    bundle_record.volatility_snapshot_json,
                    bundle_record.overlay_decision_json,
                    bundle_record.trade_plan_json,
                    bundle_record.operator_review_card_json,
                    bundle_record.shadow_order_json,
                    bundle_record.notification_payload_json,
                    created_at_text,
                ),
            )
            self._execute(
                "INSERT INTO notification_outbox "
                "(notification_id, plan_id, shadow_order_id, payload_json, status, "
                "idempotency_key, attempt_count, last_attempt_at, delivered_at, created_at) "
                "VALUES (?, ?, ?, ?, 'PENDING', ?, 0, NULL, NULL, ?)",
                (
                    outbox_record.notification_id,
                    outbox_record.plan_id,
                    outbox_record.shadow_order_id,
                    outbox_record.payload_json,
                    outbox_record.idempotency_key,
                    created_at_text,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            # GA-06: IntegrityError remains a deterministic PublicationConflictError.
            self._connection.rollback()
            raise PublicationConflictError(
                "publication bundle or notification identity already persists"
            ) from exc
        except BaseException:
            # GA-06: every other failure after the transaction begins must roll
            # back so that no partial insert can be committed by a later op.
            self._connection.rollback()
            raise
        return bundle_record, outbox_record

    def list_pending_notifications(self) -> tuple[NotificationOutboxRecord, ...]:
        rows = self._execute(
            "SELECT * FROM notification_outbox WHERE status = 'PENDING' "
            "ORDER BY created_at ASC, notification_id ASC"
        ).fetchall()
        return tuple(_row_to_outbox(row) for row in rows)

    def get_notification(self, notification_id: str) -> NotificationOutboxRecord:
        notification_id = _validate_sha256(notification_id, "notification identity is invalid")
        row = self._execute(
            "SELECT * FROM notification_outbox WHERE notification_id = ? LIMIT 1",
            (notification_id,),
        ).fetchone()
        if row is None:
            raise RuntimeStoreError("notification is missing")
        return _row_to_outbox(row)

    def begin_notification_attempt(
        self, *, notification_id: str, now: datetime
    ) -> NotificationOutboxRecord:
        notification_id = _validate_sha256(notification_id, "notification identity is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        cursor = self._execute(
            "UPDATE notification_outbox "
            "SET attempt_count = attempt_count + 1, last_attempt_at = ? "
            "WHERE notification_id = ? AND status = 'PENDING'",
            (_datetime_text(timestamp), notification_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise NotificationStatusError("notification is not pending")
        self._connection.commit()
        return self.get_notification(notification_id)

    def mark_notification_delivered(
        self, *, notification_id: str, now: datetime
    ) -> NotificationOutboxRecord:
        notification_id = _validate_sha256(notification_id, "notification identity is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        cursor = self._execute(
            "UPDATE notification_outbox "
            "SET status = 'DELIVERED', delivered_at = ? "
            "WHERE notification_id = ? AND status = 'PENDING'",
            (_datetime_text(timestamp), notification_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise NotificationStatusError("notification is not pending")
        self._connection.commit()
        return self.get_notification(notification_id)

    def mark_notification_pending(
        self, *, notification_id: str, now: datetime
    ) -> NotificationOutboxRecord:
        """Record a retryable delivery failure; the notification stays PENDING."""
        notification_id = _validate_sha256(notification_id, "notification identity is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        cursor = self._execute(
            "UPDATE notification_outbox "
            "SET last_attempt_at = ? "
            "WHERE notification_id = ? AND status = 'PENDING'",
            (_datetime_text(timestamp), notification_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise NotificationStatusError("notification is not pending")
        self._connection.commit()
        return self.get_notification(notification_id)

    def mark_notification_configuration_failed(
        self, *, notification_id: str, now: datetime
    ) -> NotificationOutboxRecord:
        """Mark a terminal non-retryable configuration failure.

        The notification stays in the outbox as a durable health/failure record
        but is never retried or falsely recorded as delivered.
        """
        notification_id = _validate_sha256(notification_id, "notification identity is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        cursor = self._execute(
            "UPDATE notification_outbox "
            "SET status = 'FAILED_CONFIGURATION', last_attempt_at = ? "
            "WHERE notification_id = ? AND status = 'PENDING'",
            (_datetime_text(timestamp), notification_id),
        )
        if cursor.rowcount == 0:
            self._connection.rollback()
            raise NotificationStatusError("notification is not pending")
        self._connection.commit()
        return self.get_notification(notification_id)

    def record_health_event(
        self,
        *,
        session_id: str,
        from_state: str,
        to_state: str,
        reason: str,
        now: datetime,
    ) -> HealthEventRecord:
        if type(session_id) is not str or not session_id:
            raise RuntimeStoreError("session identity is invalid")
        if type(from_state) is not str or not from_state:
            raise RuntimeStoreError("from_state is invalid")
        if type(to_state) is not str or not to_state:
            raise RuntimeStoreError("to_state is invalid")
        if type(reason) is not str or not reason or reason.strip() != reason:
            raise RuntimeStoreError("reason is invalid")
        timestamp = _exact_utc(now, "now is not UTC")
        event_id = uuid4().hex
        record = HealthEventRecord(
            event_id=event_id,
            session_id=session_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            recorded_at=timestamp,
        )
        self._execute(
            "INSERT INTO health_events "
            "(event_id, session_id, from_state, to_state, reason, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                record.event_id,
                record.session_id,
                record.from_state,
                record.to_state,
                record.reason,
                _datetime_text(record.recorded_at),
            ),
        )
        self._connection.commit()
        return record

    def list_health_events(
        self, *, session_id: str, limit: int = 100
    ) -> tuple[HealthEventRecord, ...]:
        if type(session_id) is not str or not session_id:
            raise RuntimeStoreError("session identity is invalid")
        if type(limit) is not int or limit <= 0 or limit > 1000:
            raise RuntimeStoreError("limit is invalid")
        rows = self._execute(
            "SELECT * FROM health_events WHERE session_id = ? "
            "ORDER BY recorded_at ASC, event_id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return tuple(_row_to_health_event(row) for row in rows)

    def list_runtime_sessions(self) -> tuple[RuntimeSessionRecord, ...]:
        rows = self._execute(
            "SELECT * FROM runtime_sessions ORDER BY created_at ASC, session_id ASC"
        ).fetchall()
        return tuple(_row_to_session(row) for row in rows)


def _row_to_session(row: sqlite3.Row) -> RuntimeSessionRecord:
    closed_at_text = row["closed_at"]
    return RuntimeSessionRecord(
        session_id=row["session_id"],
        runtime_mode=row["runtime_mode"],
        scope=row["scope"],
        process_start_time=_datetime_from_text(row["process_start_time"]),
        configuration_hash=row["configuration_hash"],
        database_path=row["database_path"],
        manual_only_authority=bool(row["manual_only_authority"]),
        not_submitted_authority=bool(row["not_submitted_authority"]),
        created_at=_datetime_from_text(row["created_at"]),
        closed_at=None if closed_at_text is None else _datetime_from_text(closed_at_text),
    )


def _row_to_publication_bundle(row: sqlite3.Row) -> PublicationBundleRecord:
    return PublicationBundleRecord(
        signal_id=row["signal_id"],
        plan_id=row["plan_id"],
        shadow_order_id=row["shadow_order_id"],
        notification_id=row["notification_id"],
        session_id=row["session_id"],
        strategy_output_setup_id=row["strategy_output_setup_id"],
        volatility_snapshot_hash=row["volatility_snapshot_hash"],
        overlay_decision_hash=row["overlay_decision_hash"],
        trade_plan_canonical_hash=row["trade_plan_canonical_hash"],
        operator_review_card_id=row["operator_review_card_id"],
        bundle_canonical_hash=row["bundle_canonical_hash"],
        strategy_output_evidence_json=row["strategy_output_evidence_json"],
        volatility_snapshot_json=row["volatility_snapshot_json"],
        overlay_decision_json=row["overlay_decision_json"],
        trade_plan_json=row["trade_plan_json"],
        operator_review_card_json=row["operator_review_card_json"],
        shadow_order_json=row["shadow_order_json"],
        notification_payload_json=row["notification_payload_json"],
        created_at=_datetime_from_text(row["created_at"]),
    )


def _row_to_outbox(row: sqlite3.Row) -> NotificationOutboxRecord:
    last_attempt_text = row["last_attempt_at"]
    delivered_at_text = row["delivered_at"]
    return NotificationOutboxRecord(
        notification_id=row["notification_id"],
        plan_id=row["plan_id"],
        shadow_order_id=row["shadow_order_id"],
        payload_json=row["payload_json"],
        status=_validate_notification_status(row["status"]),
        idempotency_key=row["idempotency_key"],
        attempt_count=row["attempt_count"],
        last_attempt_at=(
            None if last_attempt_text is None else _datetime_from_text(last_attempt_text)
        ),
        delivered_at=(
            None if delivered_at_text is None else _datetime_from_text(delivered_at_text)
        ),
        created_at=_datetime_from_text(row["created_at"]),
    )


def _row_to_health_event(row: sqlite3.Row) -> HealthEventRecord:
    return HealthEventRecord(
        event_id=row["event_id"],
        session_id=row["session_id"],
        from_state=row["from_state"],
        to_state=row["to_state"],
        reason=row["reason"],
        recorded_at=_datetime_from_text(row["recorded_at"]),
    )
