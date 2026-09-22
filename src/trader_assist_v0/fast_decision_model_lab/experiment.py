from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .contracts import DecisionEventModelOutput, DecisionRequest, DecisionResult, ModelIdentity
from .serialization import canonical_json, canonical_sha256, canonical_value

EXPERIMENT_RECORD_SCHEMA_VERSION = "fdml.experiment-record.v0"
EXPERIMENT_EVIDENCE_SCHEMA_VERSION = "fdml.experiment-evidence.v0"


def _required_text(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")


def _timestamp_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ExperimentRecordV0:
    """Immutable identity link between one FDML request and its recorded result."""

    experiment_id: str
    timestamp: datetime
    state_hash: str
    model_identity: ModelIdentity
    decision_event_id: str
    request_identity: str
    result_identity: str
    schema_version: str = EXPERIMENT_RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "experiment_id",
            "state_hash",
            "decision_event_id",
            "request_identity",
            "result_identity",
        ):
            _required_text(name, getattr(self, name))
        _timestamp_text(self.timestamp)
        if self.schema_version != EXPERIMENT_RECORD_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {EXPERIMENT_RECORD_SCHEMA_VERSION}")

    def to_payload(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "timestamp": _timestamp_text(self.timestamp),
            "state_hash": self.state_hash,
            "model_identity": canonical_value(self.model_identity),
            "decision_event_id": self.decision_event_id,
            "request_identity": self.request_identity,
            "result_identity": self.result_identity,
            "schema_version": self.schema_version,
        }

    def canonical_json(self) -> str:
        return canonical_json(self.to_payload())

    @property
    def record_identity(self) -> str:
        return canonical_sha256(self.to_payload())

    @property
    def stable_identity(self) -> str:
        return self.record_identity

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExperimentRecordV0:
        expected = {
            "experiment_id",
            "timestamp",
            "state_hash",
            "model_identity",
            "decision_event_id",
            "request_identity",
            "result_identity",
            "schema_version",
        }
        if set(payload) != expected:
            raise ValueError("experiment record payload fields do not match the frozen schema")
        model_payload = payload["model_identity"]
        if not isinstance(model_payload, dict):
            raise ValueError("model_identity must be an object")
        timestamp = payload["timestamp"]
        if not isinstance(timestamp, str):
            raise ValueError("timestamp must be an ISO-8601 string")
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            model_identity = ModelIdentity(**model_payload)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid experiment record payload") from error
        return cls(
            experiment_id=str(payload["experiment_id"]),
            timestamp=parsed_timestamp,
            state_hash=str(payload["state_hash"]),
            model_identity=model_identity,
            decision_event_id=str(payload["decision_event_id"]),
            request_identity=str(payload["request_identity"]),
            result_identity=str(payload["result_identity"]),
            schema_version=str(payload["schema_version"]),
        )

    @classmethod
    def from_request_result(
        cls,
        *,
        experiment_id: str,
        timestamp: datetime,
        request: DecisionRequest,
        result: DecisionResult,
    ) -> ExperimentRecordV0:
        DecisionEventModelOutput(request=request, response=result)
        return cls(
            experiment_id=experiment_id,
            timestamp=timestamp,
            state_hash=request.snapshot_hash,
            model_identity=result.model_identity,
            decision_event_id=request.decision_event_id,
            request_identity=canonical_sha256(request),
            result_identity=canonical_sha256(result),
        )


@dataclass(frozen=True, slots=True, init=False)
class ExperimentEvidenceV0:
    """Immutable snapshot of an experiment record and its decision evidence."""

    experiment_record: ExperimentRecordV0
    schema_version: str
    _output_decision_json: str
    _validation_metadata_json: str

    def __init__(
        self,
        *,
        experiment_record: ExperimentRecordV0,
        output_decision: object,
        validation_metadata: object,
        schema_version: str = EXPERIMENT_EVIDENCE_SCHEMA_VERSION,
    ) -> None:
        if schema_version != EXPERIMENT_EVIDENCE_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {EXPERIMENT_EVIDENCE_SCHEMA_VERSION}")
        object.__setattr__(self, "experiment_record", experiment_record)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "_output_decision_json", canonical_json(output_decision))
        object.__setattr__(
            self, "_validation_metadata_json", canonical_json(validation_metadata)
        )

    @property
    def experiment_id(self) -> str:
        return self.experiment_record.experiment_id

    @property
    def output_decision(self) -> object:
        return json.loads(self._output_decision_json)

    @property
    def validation_metadata(self) -> object:
        return json.loads(self._validation_metadata_json)

    def to_payload(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "experiment_record": self.experiment_record.to_payload(),
            "output_decision": self.output_decision,
            "validation_metadata": self.validation_metadata,
            "schema_version": self.schema_version,
        }

    def canonical_json(self) -> str:
        return canonical_json(self.to_payload())

    @property
    def evidence_identity(self) -> str:
        return canonical_sha256(self.to_payload())

    @property
    def stable_identity(self) -> str:
        return self.evidence_identity

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ExperimentEvidenceV0:
        expected = {
            "experiment_id",
            "experiment_record",
            "output_decision",
            "validation_metadata",
            "schema_version",
        }
        if set(payload) != expected:
            raise ValueError("experiment evidence fields do not match the frozen schema")
        experiment_payload = payload["experiment_record"]
        if not isinstance(experiment_payload, dict):
            raise ValueError("experiment_record must be an object")
        evidence = cls(
            experiment_record=ExperimentRecordV0.from_payload(experiment_payload),
            output_decision=payload["output_decision"],
            validation_metadata=payload["validation_metadata"],
            schema_version=str(payload["schema_version"]),
        )
        if payload["experiment_id"] != evidence.experiment_id:
            raise ValueError("experiment evidence identity linkage is inconsistent")
        return evidence


ExperimentEvidenceEnvelopeV0 = ExperimentEvidenceV0
