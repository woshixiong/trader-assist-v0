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
    outcome_identity,
)
from trader_assist_v0.fast_decision_model_lab.serialization import canonical_json, canonical_sha256


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


def _outcome(experiment_id: str = "experiment-1", evaluation_window: int = 5) -> OutcomeRecord:
    return OutcomeRecord(
        experiment_id=experiment_id,
        observation_timestamp=datetime(2026, 9, 22, 12, 35, tzinfo=UTC),
        evaluation_window=evaluation_window,
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
        assert ledger.load_outcome(experiment.experiment_id, outcome.evaluation_window) == outcome
        assert (
            ledger.load_evaluation(experiment.experiment_id, outcome.evaluation_window)
            == evaluation
        )
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


def test_multiple_windows_survive_restart_and_fail_closed_on_conflict(tmp_path) -> None:
    path = tmp_path / "fdml.sqlite"
    five_minute = _outcome(evaluation_window=5)
    fifteen_minute = _outcome(evaluation_window=15)
    with SQLiteDecisionEvidenceLedger(path) as ledger:
        ledger.append_evidence(_evidence())
        assert ledger.append_outcome(five_minute) is True
        assert ledger.append_outcome(fifteen_minute) is True
        assert ledger.append_outcome(five_minute) is False
        with pytest.raises(LedgerConflictError):
            ledger.append_outcome(five_minute.model_copy(update={"future_price": 102.0}))

    with SQLiteDecisionEvidenceLedger(path) as ledger:
        assert ledger.load_outcome("experiment-1", 5) == five_minute
        assert ledger.load_outcome("experiment-1", 15) == fifteen_minute
        assert (
            ledger.append_evaluation(
                evaluate_prediction(
                    experiment_id="experiment-1",
                    prediction="UP",
                    outcome=fifteen_minute,
                    confidence=0.8,
                    evaluation_timestamp=fifteen_minute.observation_timestamp,
                )
            )
            is True
        )
        assert ledger.validate_integrity() is True


def test_evaluation_cannot_be_created_from_another_experiment_outcome() -> None:
    with pytest.raises(ValueError, match="does not match"):
        evaluate_prediction(
            experiment_id="other-experiment",
            prediction="UP",
            outcome=_outcome(),
            confidence=0.8,
            evaluation_timestamp=datetime(2026, 9, 22, 12, 36, tzinfo=UTC),
        )


def _create_legacy_database(path, *, ambiguous: bool = False) -> None:
    evidence = _evidence()
    outcome = _outcome()
    legacy_evaluation = evaluate_prediction(
        experiment_id=outcome.experiment_id,
        prediction="UP",
        outcome=outcome,
        confidence=0.8,
        evaluation_timestamp=outcome.observation_timestamp,
    ).model_dump(mode="json")
    legacy_evaluation.pop("evaluation_window")
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE fdml_experiments (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                UNIQUE (experiment_id, record_identity)
            );
            CREATE TABLE fdml_evidence (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL,
                UNIQUE (experiment_id, record_identity)
            );
            CREATE TABLE fdml_outcomes (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE, experiment_record_identity TEXT NOT NULL,
                evidence_identity TEXT NOT NULL
            );
            CREATE TABLE fdml_evaluations (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE, outcome_identity TEXT NOT NULL
            );
            """
        )
        experiment = evidence.experiment_record
        connection.execute(
            "INSERT INTO fdml_experiments VALUES (?, ?, ?)",
            (experiment.experiment_id, experiment.canonical_json(), experiment.record_identity),
        )
        connection.execute(
            "INSERT INTO fdml_evidence VALUES (?, ?, ?, ?)",
            (
                evidence.experiment_id,
                evidence.canonical_json(),
                evidence.evidence_identity,
                experiment.record_identity,
            ),
        )
        connection.execute(
            "INSERT INTO fdml_outcomes VALUES (?, ?, ?, ?, ?)",
            (
                outcome.experiment_id,
                canonical_json(outcome.model_dump(mode="json")),
                outcome_identity(outcome),
                experiment.record_identity,
                evidence.evidence_identity,
            ),
        )
        connection.execute(
            "INSERT INTO fdml_evaluations VALUES (?, ?, ?, ?)",
            (
                outcome.experiment_id,
                canonical_json(legacy_evaluation),
                canonical_sha256(legacy_evaluation),
                "missing" if ambiguous else outcome_identity(outcome),
            ),
        )


def test_legacy_migration_is_transactional_and_rebinds_exact_window(tmp_path) -> None:
    path = tmp_path / "legacy.sqlite"
    _create_legacy_database(path)

    with SQLiteDecisionEvidenceLedger(path) as ledger:
        outcome = ledger.load_outcome("experiment-1", 5)
        evaluation = ledger.load_evaluation("experiment-1", 5)
        assert outcome is not None and evaluation is not None
        assert evaluation.evaluation_window == outcome.evaluation_window == 5
        assert ledger.validate_integrity() is True


def test_ambiguous_legacy_mapping_preserves_database_and_stops(tmp_path) -> None:
    path = tmp_path / "ambiguous.sqlite"
    _create_legacy_database(path, ambiguous=True)

    with pytest.raises(LedgerIntegrityError, match="cannot map exactly"):
        SQLiteDecisionEvidenceLedger(path)

    with sqlite3.connect(path) as connection:
        assert "evaluation_window" not in {
            row[1] for row in connection.execute("PRAGMA table_info(fdml_outcomes)")
        }
