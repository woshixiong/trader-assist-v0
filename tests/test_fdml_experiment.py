from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import ModelIdentity
from trader_assist_v0.fast_decision_model_lab.experiment import (
    ExperimentEvidenceV0,
    ExperimentRecordV0,
)


def _record() -> ExperimentRecordV0:
    return ExperimentRecordV0(
        experiment_id="experiment-1",
        timestamp=datetime(2026, 9, 22, 12, 30, tzinfo=UTC),
        state_hash="sha256:state",
        model_identity=ModelIdentity("provider", "requested", "returned"),
        decision_event_id="decision-1",
        request_identity="sha256:request",
        result_identity="sha256:result",
    )


def test_experiment_record_is_immutable_and_roundtrips_canonically() -> None:
    record = _record()
    rebuilt = ExperimentRecordV0.from_payload(record.to_payload())

    assert rebuilt == record
    assert rebuilt.canonical_json() == record.canonical_json()
    assert rebuilt.record_identity == record.record_identity
    with pytest.raises(FrozenInstanceError):
        record.experiment_id = "other"  # type: ignore[misc]


def test_experiment_identity_covers_immutable_linkage() -> None:
    record = _record()
    assert (
        replace(record, request_identity="sha256:other").record_identity
        != record.record_identity
    )
    assert replace(record, result_identity="sha256:other").record_identity != record.record_identity
    assert replace(record, state_hash="sha256:other").record_identity != record.record_identity


def test_experiment_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_record(), timestamp=datetime(2026, 9, 22))


def test_experiment_evidence_snapshots_decision_and_validation_metadata() -> None:
    decision = {"label": "UP", "probabilities": [0.2, 0.8]}
    metadata = {"validated": True, "checks": ["schema", "identity"]}
    evidence = ExperimentEvidenceV0(
        experiment_record=_record(),
        output_decision=decision,
        validation_metadata=metadata,
    )
    rebuilt = ExperimentEvidenceV0.from_payload(evidence.to_payload())

    decision["label"] = "DOWN"
    metadata["validated"] = False
    assert evidence.output_decision == {"label": "UP", "probabilities": [0.2, 0.8]}
    assert evidence.validation_metadata == {
        "validated": True,
        "checks": ["schema", "identity"],
    }
    assert rebuilt.evidence_identity == evidence.evidence_identity
    assert (
        ExperimentEvidenceV0(
            experiment_record=_record(),
            output_decision={"label": "DOWN"},
            validation_metadata=evidence.validation_metadata,
        ).evidence_identity
        != evidence.evidence_identity
    )
    assert (
        ExperimentEvidenceV0(
            experiment_record=_record(),
            output_decision=evidence.output_decision,
            validation_metadata={"validated": False},
        ).evidence_identity
        != evidence.evidence_identity
    )
