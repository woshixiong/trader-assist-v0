"""Immutable, integration-neutral records for multi-asset Shadow evidence.

This module deliberately owns data provenance only.  It does not calculate a
strategy result, read an account, or provide an exchange transport surface.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Self

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

SCHEMA_VERSION = "1"
SUBMISSION_STATUS = "NOT_SUBMITTED"
_HASH_PREFIX = "trader-assist-v0/multi-asset-shadow/records"


class RecordError(ValueError):
    """A record is incomplete, non-canonical, or outside the A2 contract."""


class HumanReviewAction(StrEnum):
    """Current authority terminology: T=TAKEN, S=SKIPPED, R=REJECTED."""

    TAKEN = "TAKEN"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"


def _canonical_mapping(value: Mapping[str, object], *, field: str) -> str:
    if not isinstance(value, Mapping) or not value:
        raise RecordError(f"{field} must be a non-empty mapping")
    try:
        return canonical_json_bytes(dict(value)).decode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RecordError(f"{field} is not canonical JSON data") from exc


def _object(value: str, *, field: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - guarded on write
        raise RecordError(f"{field} is invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise RecordError(f"{field} must encode an object")
    return decoded


def _digest(kind: str, value: Mapping[str, object]) -> str:
    return sha256_hex(f"{_HASH_PREFIX}/{kind}/v1\0".encode("ascii") + canonical_json_bytes(value))


@dataclass(frozen=True)
class ImmutableRecord:
    """A typed, identity-versioned immutable payload.

    ``record_id`` binds source identity while ``canonical_hash`` binds both
    identity and immutable content.  Thus an upstream retry is idempotent and
    a retry with changed content is detectable rather than silently rewritten.
    """

    record_id: str
    canonical_hash: str
    _identity_json: str
    _payload_json: str

    record_type: ClassVar[str] = "immutable_record"
    required_fields: ClassVar[frozenset[str]] = frozenset()

    def __post_init__(self) -> None:
        identity = _object(self._identity_json, field="identity")
        payload = _object(self._payload_json, field="payload")
        if canonical_json_bytes(identity).decode("utf-8") != self._identity_json:
            raise RecordError("identity is not canonical")
        if canonical_json_bytes(payload).decode("utf-8") != self._payload_json:
            raise RecordError("payload is not canonical")
        missing = self.required_fields - payload.keys()
        if missing:
            raise RecordError(f"{self.record_type} missing fields: {sorted(missing)}")
        self.validate_payload(payload)
        expected_id = _digest(f"{self.record_type}/identity", identity)
        expected_hash = _digest(
            f"{self.record_type}/content", {"identity": identity, "payload": payload}
        )
        if self.record_id != expected_id or self.canonical_hash != expected_hash:
            raise RecordError("record identifier/hash does not bind canonical content")

    @classmethod
    def create(cls, *, identity: Mapping[str, object], **payload: object) -> Self:
        identity_json = _canonical_mapping(identity, field="identity")
        payload_json = _canonical_mapping(payload, field="payload")
        canonical_identity = _object(identity_json, field="identity")
        canonical_payload = _object(payload_json, field="payload")
        return cls(
            record_id=_digest(f"{cls.record_type}/identity", canonical_identity),
            canonical_hash=_digest(
                f"{cls.record_type}/content",
                {"identity": canonical_identity, "payload": canonical_payload},
            ),
            _identity_json=identity_json,
            _payload_json=payload_json,
        )

    @classmethod
    def from_storage(
        cls, *, record_id: str, canonical_hash: str, identity_json: str, payload_json: str
    ) -> Self:
        return cls(record_id, canonical_hash, identity_json, payload_json)

    @property
    def identity(self) -> dict[str, Any]:
        """A fresh decoded copy; callers cannot rewrite the retained record."""
        return _object(self._identity_json, field="identity")

    @property
    def payload(self) -> dict[str, Any]:
        """A fresh decoded copy; callers cannot rewrite the retained record."""
        return _object(self._payload_json, field="payload")

    def canonical_row(self) -> dict[str, object]:
        return {
            "canonical_hash": self.canonical_hash,
            "identity": self.identity,
            "payload": self.payload,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "schema_version": SCHEMA_VERSION,
        }

    @classmethod
    def validate_payload(cls, payload: Mapping[str, object]) -> None:
        del payload


class ProvenanceRecord(ImmutableRecord):
    record_type = "provenance"
    required_fields = frozenset(
        {
            "strategy_version",
            "parameter_version",
            "registry_version",
            "registry_hash",
            "cost_model_version",
            "release_sha",
            "recorded_at",
        }
    )


class ScannerEvidence(ImmutableRecord):
    record_type = "scanner_evidence"
    required_fields = frozenset(
        {
            "scan_id",
            "observed_at",
            "scanner_version",
            "parameter_version",
            "registry_version",
            "registry_hash",
            "release_sha",
            "universe_snapshot_hash",
        }
    )


class Candidate(ImmutableRecord):
    record_type = "candidate"
    required_fields = frozenset(
        {"scanner_evidence_id", "scan_id", "market_id", "state", "alert_level", "created_at"}
    )


class CandidateTransition(ImmutableRecord):
    record_type = "candidate_transition"
    required_fields = frozenset({"candidate_id", "from_state", "to_state", "transitioned_at"})


class MarketEvent(ImmutableRecord):
    record_type = "market_event"
    required_fields = frozenset({"candidate_id", "market_id", "event_kind", "event_time"})


class FormalSignal(ImmutableRecord):
    record_type = "formal_signal"
    required_fields = frozenset(
        {
            "candidate_id",
            "market_event_id",
            "market_id",
            "setup_family",
            "setup_mode",
            "side",
            "approval_status",
            "tier",
            "confirmed_at",
            "provenance_id",
        }
    )

    @classmethod
    def validate_payload(cls, payload: Mapping[str, object]) -> None:
        if payload.get("setup_family") not in {
            "SWEEP_RECLAIM",
            "BREAKOUT_RETEST",
            "RANGE_EDGE_REJECTION",
        }:
            raise RecordError("formal_signal setup_family is not an authorized family")
        if payload.get("tier") not in {"P0", "P1", "P2"}:
            raise RecordError("formal_signal tier must be P0, P1, or P2")


class PlanRecord(ImmutableRecord):
    record_type = "plan_record"
    required_fields = frozenset(
        {
            "signal_id",
            "planned_entry",
            "stop",
            "tp1",
            "tp2",
            "risk_reference_sizing",
            "created_at",
            "provenance_id",
        }
    )


class ShadowOrder(ImmutableRecord):
    record_type = "shadow_order"
    required_fields = frozenset(
        {
            "signal_id",
            "plan_id",
            "market_event_id",
            "market_id",
            "setup_family",
            "setup_mode",
            "side",
            "planned_entry",
            "stop",
            "tp1",
            "tp2",
            "risk_reference_sizing",
            "provenance_id",
            "strategy_version",
            "parameter_version",
            "registry_version",
            "registry_hash",
            "cost_model_version",
            "created_at",
            "submission_status",
        }
    )

    @classmethod
    def validate_payload(cls, payload: Mapping[str, object]) -> None:
        if payload.get("submission_status") != SUBMISSION_STATUS:
            raise RecordError("shadow_order submission_status must be NOT_SUBMITTED")


class HumanReview(ImmutableRecord):
    record_type = "human_review"
    required_fields = frozenset(
        {"signal_id", "shadow_order_id", "action", "actor", "source", "reviewed_at"}
    )

    @classmethod
    def validate_payload(cls, payload: Mapping[str, object]) -> None:
        if payload.get("action") not in {item.value for item in HumanReviewAction}:
            raise RecordError("human_review action must be TAKEN, SKIPPED, or REJECTED")


class OutcomeEnvelope(ImmutableRecord):
    record_type = "outcome_envelope"
    required_fields = frozenset(
        {"signal_id", "shadow_order_id", "observed_at", "path_maturity_status"}
    )


class CorrelationIdentifier(ImmutableRecord):
    record_type = "correlation_identifier"
    required_fields = frozenset(
        {"signal_id", "shadow_order_id", "cluster_kind", "cluster_id", "correlation_version"}
    )


class NotificationOutboxReference(ImmutableRecord):
    record_type = "notification_outbox_reference"
    required_fields = frozenset({"signal_id", "publication_id", "published_at"})


RECORD_TYPES: dict[str, type[ImmutableRecord]] = {
    item.record_type: item
    for item in (
        ProvenanceRecord,
        ScannerEvidence,
        Candidate,
        CandidateTransition,
        MarketEvent,
        FormalSignal,
        PlanRecord,
        ShadowOrder,
        HumanReview,
        OutcomeEnvelope,
        CorrelationIdentifier,
        NotificationOutboxReference,
    )
}
