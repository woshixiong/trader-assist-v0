from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import ModelIdentity
from trader_assist_v0.fast_decision_model_lab.experiment import (
    ExperimentEvidenceV0,
    ExperimentRecordV0,
)
from trader_assist_v0.fast_decision_model_lab.outcome import (
    OutcomeRecord,
    evaluate_prediction,
)
from trader_assist_v0.fast_decision_model_lab.persistence import (
    LedgerConflictError,
    LedgerIntegrityError,
    SQLiteDecisionEvidenceLedger,
)


def _experiment(experiment_id: str = "experiment-1") -> ExperimentRecordV0:
    return ExperimentRecordV0(
        experiment_id=experiment_id,
        timestamp=datetime(2026, 9, 22, 12, 30, tzinfo=UTC),
        state_hash="sha256:state",
        model_identity=ModelIdentity("provider", "requested", "returned"),
        decision_event_id="decision-1",
        request_identity="sha256:request",
        result_identity="sha256:result",
    )


def _outcome(experiment_id: str = "experiment-1") -> OutcomeRecord:
    return OutcomeRecord(
        experiment_id=experiment_id,
        observation_timestamp=datetime(2026, 9, 22, 12, 35, tzinfo=UTC),
        evaluation_window=5,
        reference_price=100.0,
        future_price=101.0,
        price_change=1.0,
        volatility_change=0.1,
    )


def _evidence(experiment_id: str = "experiment-1") -> ExperimentEvidenceV0:
    return ExperimentEvidenceV0(
        experiment_record=_experiment(experiment_id),
        output_decision={"label": "UP", "confidence": 0.8},
        validation_metadata={"schema_valid": True},
    )


def test_ledger_is_idempotent_append_only_and_deterministic(tmp_path) -> None:
    path = tmp_path / "fdml.sqlite"
    evidence = _evidence()
    experiment = evidence.experiment_record
    outcome = _outcome()
    evaluation = evaluate_prediction(
        experiment_id=experiment.experiment_id,
        prediction="UP",
        outcome=outcome,
        confidence=0.8,
        evaluation_timestamp=outcome.observation_timestamp + timedelta(seconds=1),
    )

    with SQLiteDecisionEvidenceLedger(path) as ledger:
        assert ledger.append_evidence(evidence) is True
        assert ledger.append_evidence(evidence) is False
        assert ledger.append_experiment(experiment) is False
        assert ledger.append_outcome(outcome) is True
        assert ledger.append_outcome(outcome) is False
        assert ledger.append_evaluation(evaluation) is True
        assert ledger.append_evaluation(evaluation) is False
        assert ledger.load_experiment(experiment.experiment_id) == experiment
        assert ledger.load_evidence(experiment.experiment_id) == evidence
        assert ledger.load_outcome(experiment.experiment_id) == outcome
        assert ledger.load_evaluation(experiment.experiment_id) == evaluation
        assert tuple(ledger.iter_experiments()) == (experiment,)
        assert ledger.validate_integrity() is True

        with pytest.raises(LedgerConflictError):
            ledger.append_experiment(replace(experiment, result_identity="sha256:conflict"))
        with pytest.raises(LedgerConflictError):
            ledger.append_evidence(
                ExperimentEvidenceV0(
                    experiment_record=experiment,
                    output_decision={"label": "DOWN"},
                    validation_metadata=evidence.validation_metadata,
                )
            )

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE fdml_experiments SET record_identity = ? WHERE experiment_id = ?",
                ("forged", experiment.experiment_id),
            )


def test_outcome_and_evaluation_require_existing_links(tmp_path) -> None:
    with SQLiteDecisionEvidenceLedger(tmp_path / "fdml.sqlite") as ledger:
        with pytest.raises(LedgerIntegrityError, match="experiment evidence"):
            ledger.append_outcome(_outcome())

        ledger.append_evidence(_evidence())
        evaluation = evaluate_prediction(
            experiment_id="experiment-1",
            prediction="UP",
            outcome=_outcome(),
            confidence=0.8,
            evaluation_timestamp=datetime(2026, 9, 22, 12, 36, tzinfo=UTC),
        )
        with pytest.raises(LedgerIntegrityError, match="existing outcome"):
            ledger.append_evaluation(evaluation)


def test_integrity_validation_detects_tampering(tmp_path) -> None:
    path = tmp_path / "fdml.sqlite"
    with SQLiteDecisionEvidenceLedger(path) as ledger:
        ledger.append_experiment(_experiment())

    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER fdml_experiments_no_update")
        connection.execute(
            "UPDATE fdml_experiments SET record_identity = ? WHERE experiment_id = ?",
            ("forged", "experiment-1"),
        )

    with SQLiteDecisionEvidenceLedger(path) as ledger:
        with pytest.raises(LedgerIntegrityError, match="identity"):
            ledger.validate_integrity()


def test_integrity_validation_detects_linkage_tampering(tmp_path) -> None:
    path = tmp_path / "fdml.sqlite"
    with SQLiteDecisionEvidenceLedger(path) as ledger:
        ledger.append_evidence(_evidence())
        ledger.append_outcome(_outcome())

    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER fdml_outcomes_no_update")
        connection.execute(
            "UPDATE fdml_outcomes SET evidence_identity = ? WHERE experiment_id = ?",
            ("forged", "experiment-1"),
        )

    with SQLiteDecisionEvidenceLedger(path) as ledger:
        with pytest.raises(LedgerIntegrityError):
            ledger.validate_integrity()
