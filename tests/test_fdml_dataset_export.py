from trader_assist_v0.fast_decision_model_lab.dataset_export import (
    EXPORT_FIELDS,
    export_csv,
    export_jsonl,
    validate_schema,
)


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
