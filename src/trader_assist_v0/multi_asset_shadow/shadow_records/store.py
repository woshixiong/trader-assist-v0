"""Small transactional SQLite store for immutable multi-asset Shadow records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .records import RECORD_TYPES, ImmutableRecord, RecordError

if TYPE_CHECKING:
    from ..notification_engine import MessageEnvelope
    from .records import NotificationOutboxReference

SCHEMA_NAME = "multi_asset_shadow_evidence_v1"


class RecordConflictError(RecordError):
    """A deterministic identity was retried with different immutable content."""


_TABLE_BY_TYPE = {
    "provenance": "provenance_records",
    "scanner_evidence": "scanner_evidence",
    "strategy_evaluation": "strategy_evaluations",
    "candidate": "candidates",
    "candidate_transition": "candidate_transitions",
    "market_event": "market_events",
    "formal_signal": "formal_signals",
    "plan_record": "plan_records",
    "shadow_order": "shadow_orders",
    "human_review": "human_reviews",
    "outcome_envelope": "outcome_envelopes",
    "outcome_transition": "outcome_transitions",
    "outcome_bar": "outcome_bars",
    "correlation_identifier": "correlation_identifiers",
    "notification_outbox_reference": "notification_outbox_references",
}

_LINK_COLUMNS = {
    "provenance": (),
    "scanner_evidence": (),
    "strategy_evaluation": (),
    "candidate": ("scanner_evidence_id",),
    "candidate_transition": ("candidate_id",),
    "market_event": ("candidate_id",),
    "formal_signal": ("candidate_id", "market_event_id", "provenance_id"),
    "plan_record": ("signal_id", "provenance_id"),
    "shadow_order": ("signal_id", "plan_id", "market_event_id", "provenance_id"),
    "human_review": ("signal_id", "shadow_order_id"),
    "outcome_envelope": ("signal_id", "shadow_order_id"),
    "outcome_transition": ("shadow_order_id",),
    "outcome_bar": (),
    "correlation_identifier": ("signal_id", "shadow_order_id"),
    "notification_outbox_reference": ("signal_id",),
}

# Generic persistence is intentionally limited to ordinary source/user evidence.
# Computed authority and projections enter through their bounded producers below.
_GENERIC_WRITE_TYPES = frozenset({"provenance", "human_review"})
_CONTROLLED_WRITE_TYPES = frozenset(
    {
        "scanner_evidence",
        "strategy_evaluation",
        "candidate",
        "candidate_transition",
        "outcome_envelope",
        "outcome_transition",
        "outcome_bar",
    }
)


class EvidenceStore:
    """A new database only; this class never opens or migrates legacy runtime.db."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> EvidenceStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    schema_name TEXT PRIMARY KEY NOT NULL,
                    schema_version TEXT NOT NULL
                ) STRICT;
                CREATE TABLE IF NOT EXISTS immutable_records (
                    record_id TEXT PRIMARY KEY NOT NULL,
                    record_type TEXT NOT NULL,
                    canonical_hash TEXT NOT NULL,
                    identity_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                ) STRICT;
                CREATE TABLE IF NOT EXISTS provenance_records (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS scanner_evidence (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS strategy_evaluations (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS candidates (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    scanner_evidence_id TEXT NOT NULL REFERENCES scanner_evidence(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS candidate_transitions (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    candidate_id TEXT NOT NULL REFERENCES candidates(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS market_events (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    candidate_id TEXT REFERENCES candidates(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS formal_signals (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    candidate_id TEXT REFERENCES candidates(record_id),
                    market_event_id TEXT NOT NULL REFERENCES market_events(record_id),
                    provenance_id TEXT NOT NULL REFERENCES provenance_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS plan_records (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id),
                    provenance_id TEXT NOT NULL REFERENCES provenance_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS shadow_orders (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id),
                    plan_id TEXT NOT NULL REFERENCES plan_records(record_id),
                    market_event_id TEXT NOT NULL REFERENCES market_events(record_id),
                    provenance_id TEXT NOT NULL REFERENCES provenance_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS human_reviews (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id),
                    shadow_order_id TEXT NOT NULL REFERENCES shadow_orders(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS outcome_envelopes (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id),
                    shadow_order_id TEXT NOT NULL REFERENCES shadow_orders(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS outcome_transitions (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    shadow_order_id TEXT NOT NULL REFERENCES shadow_orders(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS outcome_bars (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS correlation_identifiers (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id),
                    shadow_order_id TEXT NOT NULL REFERENCES shadow_orders(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS notification_outbox_references (
                    record_id TEXT PRIMARY KEY NOT NULL REFERENCES immutable_records(record_id),
                    signal_id TEXT NOT NULL REFERENCES formal_signals(record_id)
                ) STRICT;
                CREATE TABLE IF NOT EXISTS notification_outbox (
                    idempotency_key TEXT PRIMARY KEY NOT NULL,
                    schema_version TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('PENDING', 'DELIVERED', 'PERMANENT_FAILURE')
                    ),
                    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
                    next_attempt_at TEXT NOT NULL,
                    claim_token TEXT,
                    claim_expires_at TEXT,
                    completed_at TEXT,
                    response_status INTEGER,
                    last_reason TEXT
                ) STRICT;
                CREATE UNIQUE INDEX IF NOT EXISTS notification_outbox_claim_token
                    ON notification_outbox(claim_token)
                    WHERE claim_token IS NOT NULL;
                """
            )
            row = self._connection.execute(
                "SELECT schema_version FROM schema_metadata WHERE schema_name = ?", (SCHEMA_NAME,)
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_metadata(schema_name, schema_version) VALUES (?, ?)",
                    (SCHEMA_NAME, "1"),
                )
            elif row["schema_version"] != "1":
                raise RecordError("unsupported evidence schema version")
            for table in ("immutable_records", *_TABLE_BY_TYPE.values()):
                self._connection.executescript(
                    f"""
                    CREATE TRIGGER IF NOT EXISTS {table}_append_only_update
                    BEFORE UPDATE ON {table}
                    BEGIN SELECT RAISE(ABORT, 'append-only evidence'); END;
                    CREATE TRIGGER IF NOT EXISTS {table}_append_only_delete
                    BEFORE DELETE ON {table}
                    BEGIN SELECT RAISE(ABORT, 'append-only evidence'); END;
                    """
                )

    def write(self, records: Iterable[ImmutableRecord]) -> tuple[bool, ...]:
        """Persist only ordinary/source/user evidence through the generic surface."""
        materialized = tuple(records)
        if any(record.record_type not in _GENERIC_WRITE_TYPES for record in materialized):
            raise RecordError("record type requires its controlled producer")
        return self._write_transaction(materialized)

    def _write_controlled(self, records: Iterable[ImmutableRecord]) -> tuple[bool, ...]:
        """Package-private persistence for validated coordinator/Outcome output."""
        materialized = tuple(records)
        if any(record.record_type not in _CONTROLLED_WRITE_TYPES for record in materialized):
            raise RecordError("record type requires a different controlled producer")
        return self._write_transaction(materialized)

    def _write_transaction(
        self, materialized: tuple[ImmutableRecord, ...]
    ) -> tuple[bool, ...]:
        try:
            with self._connection:
                return tuple(self._write_one(record) for record in materialized)
        except sqlite3.IntegrityError as exc:
            raise RecordError("record linkage integrity failure") from exc

    def publish_formal_bundle(
        self,
        *,
        records: Iterable[ImmutableRecord],
        notification_reference: NotificationOutboxReference,
        envelope: MessageEnvelope,
    ) -> bool:
        """Atomically retain one complete Formal bundle and its pending notification."""
        from ..notification_engine import NotificationKind
        from .records import (
            FormalSignal,
            MarketEvent,
            NotificationOutboxReference,
            PlanRecord,
            ProvenanceRecord,
            ShadowOrder,
        )

        materialized = tuple(records)
        required_types = {
            ProvenanceRecord,
            MarketEvent,
            FormalSignal,
            PlanRecord,
            ShadowOrder,
        }
        if len(materialized) != len(required_types) or {
            type(record) for record in materialized
        } != required_types:
            raise RecordError("formal publication requires one complete typed record bundle")
        if type(notification_reference) is not NotificationOutboxReference:
            raise RecordError("formal publication requires a typed outbox reference")
        if envelope.kind is not NotificationKind.FORMAL_SIGNAL:
            raise RecordError("formal publication requires a FORMAL_SIGNAL envelope")
        signal = next(record for record in materialized if isinstance(record, FormalSignal))
        if notification_reference.payload.get("signal_id") != signal.record_id:
            raise RecordError("formal outbox reference does not match Formal Signal")
        if notification_reference.payload.get("publication_id") != envelope.idempotency_key:
            raise RecordError("formal outbox reference does not match notification envelope")

        connection = self._connection
        connection.execute("BEGIN IMMEDIATE")
        try:
            for record in materialized:
                self._write_one(record)
            created_at = envelope.created_at.isoformat().replace("+00:00", "Z")
            inserted = self._insert_outbox(envelope, created_at=created_at)
            row = connection.execute(
                """SELECT schema_version, kind, content, created_at
                   FROM notification_outbox WHERE idempotency_key = ?""",
                (envelope.idempotency_key,),
            ).fetchone()
            if row is None or (
                row["schema_version"],
                row["kind"],
                row["content"],
                row["created_at"],
            ) != (
                envelope.schema_version,
                envelope.kind.value,
                envelope.content,
                created_at,
            ):
                raise RecordError(
                    "notification idempotency identity conflicts with retained content"
                )
            self._write_one(notification_reference)
            connection.commit()
            return inserted == 0
        except BaseException:
            connection.rollback()
            raise

    def _insert_outbox(self, envelope: MessageEnvelope, *, created_at: str) -> int:
        return int(
            self._connection.execute(
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
        )

    def _write_one(self, record: ImmutableRecord) -> bool:
        expected = RECORD_TYPES.get(record.record_type)
        if expected is None or type(record) is not expected:
            raise RecordError("unknown or forged record type")
        existing = self._connection.execute(
            "SELECT canonical_hash FROM immutable_records WHERE record_id = ?", (record.record_id,)
        ).fetchone()
        if existing is not None:
            if existing["canonical_hash"] == record.canonical_hash:
                return False
            raise RecordConflictError("immutable identity conflicts with retained content")
        self._validate_links(record)
        self._connection.execute(
            "INSERT INTO immutable_records VALUES (?, ?, ?, ?, ?)",
            (
                record.record_id,
                record.record_type,
                record.canonical_hash,
                record._identity_json,
                record._payload_json,
            ),
        )
        payload = record.payload
        table = _TABLE_BY_TYPE[record.record_type]
        columns = ("record_id",) + _LINK_COLUMNS[record.record_type]
        values = (
            record.record_id,
            *(payload.get(name) for name in _LINK_COLUMNS[record.record_type]),
        )
        placeholders = ", ".join("?" for _ in columns)
        self._connection.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values
        )
        return True

    def _linked_payload(self, record_id: object) -> dict[str, object]:
        if not isinstance(record_id, str):
            raise RecordError("record linkage identifier must be a string")
        row = self._connection.execute(
            "SELECT payload_json FROM immutable_records WHERE record_id = ?", (record_id,)
        ).fetchone()
        if row is None:
            raise RecordError("record linkage target is not retained")
        payload = json.loads(row["payload_json"])
        if not isinstance(payload, dict):  # pragma: no cover - retained rows are verified
            raise RecordError("retained linkage payload is invalid")
        return payload

    def _validate_links(self, record: ImmutableRecord) -> None:
        """Check cross-record correspondence beyond SQLite's individual FKs."""
        payload = record.payload
        if record.record_type == "candidate":
            scan = self._linked_payload(payload["scanner_evidence_id"])
            if scan.get("scan_id") != payload["scan_id"]:
                raise RecordError("candidate scan_id does not match scanner evidence")
            content = payload["candidate_content"]
            expected_hash = sha256_hex(
                b"trader-assist-v0/scanner-candidate/v1\0" + canonical_json_bytes(content)
            )
            if payload["candidate_content_hash"] != expected_hash:
                raise RecordError("candidate content hash is invalid")
            observations = scan.get("observations")
            if not isinstance(observations, list) or not any(
                isinstance(observation, dict)
                and observation.get("market_id") == payload["market_id"]
                and observation.get("candidate") == content
                for observation in observations
            ):
                raise RecordError("candidate is absent from retained Scanner observations")
            if not isinstance(content, dict) or (
                content.get("candidate_id") != payload.get("scanner_candidate_id")
                or content.get("market_id") != payload["market_id"]
                or content.get("state") != payload["state"]
                or content.get("scanner_version") != payload["scanner_version"]
                or content.get("parameter_version") != payload["parameter_version"]
                or content.get("transitions") != payload["transitions"]
            ):
                raise RecordError("candidate projection contradicts retained Scanner content")
        elif record.record_type == "candidate_transition":
            candidate = self._linked_payload(payload["candidate_id"])
            transition = f"{payload['from_state']}->{payload['to_state']}"
            transitions = candidate.get("transitions")
            if not isinstance(transitions, list) or transition not in transitions:
                raise RecordError("candidate transition is absent from retained Scanner evidence")
        elif record.record_type == "formal_signal":
            event = self._linked_payload(payload["market_event_id"])
            if event.get("candidate_id") != payload.get("candidate_id"):
                raise RecordError("formal signal market event does not match candidate")
        elif record.record_type == "shadow_order":
            signal = self._linked_payload(payload["signal_id"])
            plan = self._linked_payload(payload["plan_id"])
            if signal.get("approval_status") != "APPROVED":
                raise RecordError("shadow order requires an approved formal signal")
            if plan.get("signal_id") != payload["signal_id"]:
                raise RecordError("shadow order plan does not match signal")
        elif record.record_type in {
            "human_review",
            "outcome_envelope",
            "correlation_identifier",
        }:
            shadow = self._linked_payload(payload["shadow_order_id"])
            if shadow.get("signal_id") != payload["signal_id"]:
                raise RecordError("linked shadow order does not match signal")
        elif record.record_type == "outcome_transition":
            shadow = self._linked_payload(payload["shadow_order_id"])
            if shadow.get("market_id") != payload["market_id"]:
                raise RecordError("outcome transition does not match ShadowOrder market")

    def get(self, record_id: str) -> ImmutableRecord | None:
        row = self._connection.execute(
            "SELECT record_id, record_type, canonical_hash, identity_json, payload_json "
            "FROM immutable_records WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        record_class = RECORD_TYPES[row["record_type"]]
        return record_class.from_storage(
            record_id=row["record_id"],
            canonical_hash=row["canonical_hash"],
            identity_json=row["identity_json"],
            payload_json=row["payload_json"],
        )

    def count(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM immutable_records").fetchone()[0])

    def export_jsonl(self) -> bytes:
        """Return deterministic canonical JSONL suitable for offline research."""
        rows = self._connection.execute(
            "SELECT record_id, record_type, canonical_hash, identity_json, payload_json "
            "FROM immutable_records ORDER BY record_type, record_id"
        ).fetchall()
        exported = []
        for row in rows:
            record_class = RECORD_TYPES[row["record_type"]]
            exported.append(
                record_class.from_storage(
                    record_id=row["record_id"],
                    canonical_hash=row["canonical_hash"],
                    identity_json=row["identity_json"],
                    payload_json=row["payload_json"],
                ).canonical_row()
            )
        return b"".join(canonical_json_bytes(row) + b"\n" for row in exported)

    def export_hash(self) -> str:
        return sha256_hex(self.export_jsonl())
