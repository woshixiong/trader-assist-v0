import json
from datetime import UTC, datetime

from trader_assist_v0.fast_decision_model_lab.contracts import ModelIdentity
from trader_assist_v0.fast_decision_model_lab.dataset_export import (
    EXPORT_FIELDS,
    LEDGER_EXPORT_FIELDS,
    build_ledger_export_record,
    export_csv,
    export_jsonl,
    validate_schema,
)
from trader_assist_v0.fast_decision_model_lab.experiment import (
    ExperimentEvidenceV0,
    ExperimentRecordV0,
)
from trader_assist_v0.fast_decision_model_lab.outcome import OutcomeRecord, evaluate_prediction


def _records():
    return [
        {
            "experiment_id": "b",
            "state_hash": "hash-b",
            "model_identity": "model-v1",
            "decision": "UP",
            "confidence": 0.8,
            "outcome": "POSITIVE",
            "evaluation": "CORRECT",
        },
        {
            "experiment_id": "a",
            "state_hash": "hash-a",
            "model_identity": "model-v1",
            "decision": "DOWN",
            "confidence": 0.4,
            "outcome": "NEGATIVE",
            "evaluation": "CORRECT",
        },
    ]


def test_schema_validation():
    assert validate_schema(_records()[0])
    assert EXPORT_FIELDS[0] == "experiment_id"


def test_jsonl_export_is_deterministic():
    assert export_jsonl(_records()) == export_jsonl(reversed(_records()))


def test_csv_export_is_deterministic():
    assert export_csv(_records()) == export_csv(reversed(_records()))


def test_ledger_linked_export_preserves_frozen_fields_and_identities():
    experiment = ExperimentRecordV0(
        experiment_id="experiment-1",
        timestamp=datetime(2026, 9, 22, tzinfo=UTC),
        state_hash="sha256:state",
        model_identity=ModelIdentity("provider", "requested", "returned"),
        decision_event_id="decision-1",
        request_identity="sha256:request",
        result_identity="sha256:result",
    )
    evidence = ExperimentEvidenceV0(
        experiment_record=experiment,
        output_decision="UP",
        validation_metadata={"schema_valid": True},
    )
    outcome = OutcomeRecord(
        experiment_id=experiment.experiment_id,
        observation_timestamp=datetime(2026, 9, 22, 0, 5, tzinfo=UTC),
        evaluation_window=5,
        reference_price=100.0,
        future_price=101.0,
        price_change=1.0,
        volatility_change=0.1,
    )
    evaluation = evaluate_prediction(
        experiment_id=experiment.experiment_id,
        prediction="UP",
        outcome=outcome,
        confidence=0.8,
        evaluation_timestamp=datetime(2026, 9, 22, 0, 6, tzinfo=UTC),
    )
    record = build_ledger_export_record(
        evidence=evidence,
        confidence=0.8,
        outcome=outcome,
        evaluation=evaluation,
    )

    assert validate_schema(record)
    assert tuple(record) == LEDGER_EXPORT_FIELDS
    assert tuple(record)[: len(EXPORT_FIELDS)] == EXPORT_FIELDS
    assert record["experiment_record_identity"] == experiment.record_identity
    assert record["evidence_identity"] == evidence.evidence_identity
    assert json.loads(export_jsonl([record]))["request_identity"] == "sha256:request"
    assert export_csv([record]).splitlines()[0].split(",") == list(LEDGER_EXPORT_FIELDS)
