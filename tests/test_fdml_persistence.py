from __future__ import annotations

import json
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

    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)


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

    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)


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
                UNIQUE (experiment_id, record_identity),
                FOREIGN KEY (experiment_id, experiment_record_identity)
                    REFERENCES fdml_experiments(experiment_id, record_identity)
            );
            CREATE TABLE fdml_outcomes (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE, experiment_record_identity TEXT NOT NULL,
                evidence_identity TEXT NOT NULL,
                FOREIGN KEY (experiment_id, experiment_record_identity)
                    REFERENCES fdml_experiments(experiment_id, record_identity),
                FOREIGN KEY (experiment_id, evidence_identity)
                    REFERENCES fdml_evidence(experiment_id, record_identity)
            );
            CREATE TABLE fdml_evaluations (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE, outcome_identity TEXT NOT NULL,
                FOREIGN KEY (experiment_id, outcome_identity)
                    REFERENCES fdml_outcomes(experiment_id, record_identity)
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


def _legacy_snapshot(path):
    with sqlite3.connect(path) as connection:
        schema = tuple(
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )
        )
        rows = tuple(
            tuple(connection.execute(f"SELECT * FROM {table} ORDER BY experiment_id"))
            for table in (
                "fdml_experiments",
                "fdml_evidence",
                "fdml_outcomes",
                "fdml_evaluations",
            )
        )
        return schema, rows, connection.execute("PRAGMA user_version").fetchone()[0]


def _rewrite_legacy_evaluation_payload(path, mutate) -> None:
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT record_json FROM fdml_evaluations").fetchone()
        payload = json.loads(row[0])
        mutate(payload)
        connection.execute(
            "UPDATE fdml_evaluations SET record_json = ?, record_identity = ?",
            (canonical_json(payload), canonical_sha256(payload)),
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


def test_migration_rolls_back_after_v2_ddl_before_first_copy(tmp_path, monkeypatch) -> None:
    path = tmp_path / "legacy.sqlite"
    _create_legacy_database(path)
    before = _legacy_snapshot(path)
    original = SQLiteDecisionEvidenceLedger._create_migration_tables

    def create_then_fail(ledger) -> None:
        original(ledger)
        raise LedgerIntegrityError("injected before copy")

    monkeypatch.setattr(SQLiteDecisionEvidenceLedger, "_create_migration_tables", create_then_fail)
    with pytest.raises(LedgerIntegrityError, match="before copy"):
        SQLiteDecisionEvidenceLedger(path)
    assert _legacy_snapshot(path) == before


def test_migration_rolls_back_after_post_rename_integrity_failure(tmp_path, monkeypatch) -> None:
    path = tmp_path / "legacy.sqlite"
    _create_legacy_database(path)
    before = _legacy_snapshot(path)

    def fail_integrity(_ledger) -> bool:
        raise LedgerIntegrityError("injected post-rename integrity failure")

    monkeypatch.setattr(SQLiteDecisionEvidenceLedger, "validate_integrity", fail_integrity)
    with pytest.raises(LedgerIntegrityError, match="post-rename"):
        SQLiteDecisionEvidenceLedger(path)
    assert _legacy_snapshot(path) == before


@pytest.mark.parametrize(
    "mutate",
    (
        lambda payload: payload.update({"unexpected": "value"}),
        lambda payload: payload.update({"evaluation_window": 60}),
    ),
)
def test_legacy_evaluation_ambiguous_payload_is_preserved_and_rejected(tmp_path, mutate) -> None:
    path = tmp_path / "legacy.sqlite"
    _create_legacy_database(path)
    _rewrite_legacy_evaluation_payload(path, mutate)
    before = _legacy_snapshot(path)
    with pytest.raises(LedgerIntegrityError, match="unsupported field set"):
        SQLiteDecisionEvidenceLedger(path)
    assert _legacy_snapshot(path) == before


def test_partial_v2_like_schema_is_rejected_without_version_stamp(tmp_path) -> None:
    path = tmp_path / "partial.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE fdml_outcomes (experiment_id TEXT, evaluation_window INTEGER)"
        )
    with pytest.raises(LedgerIntegrityError, match="partial or ambiguous"):
        SQLiteDecisionEvidenceLedger(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0


def test_v2_like_schema_with_wrong_composite_key_is_rejected(tmp_path) -> None:
    path = tmp_path / "malformed.sqlite"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE fdml_experiments (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE
            );
            CREATE TABLE fdml_evidence (
                experiment_id TEXT PRIMARY KEY, record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL
            );
            CREATE TABLE fdml_outcomes (
                experiment_id TEXT PRIMARY KEY, evaluation_window INTEGER NOT NULL,
                record_json TEXT NOT NULL, record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL, evidence_identity TEXT NOT NULL
            );
            CREATE TABLE fdml_evaluations (
                experiment_id TEXT PRIMARY KEY, evaluation_window INTEGER NOT NULL,
                record_json TEXT NOT NULL, record_identity TEXT NOT NULL UNIQUE,
                outcome_identity TEXT NOT NULL
            );
            """
        )
        connection.execute("PRAGMA user_version = 2")
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def _create_exact_v2_database(path) -> None:
    with SQLiteDecisionEvidenceLedger(path):
        pass


def _clone_v2_schema(path, mutate) -> None:
    source = path.with_name("source.sqlite")
    _create_exact_v2_database(source)
    with sqlite3.connect(source) as connection:
        statements = [
            row[0]
            for row in connection.execute(
                "SELECT sql FROM sqlite_master WHERE type IN ('table', 'trigger') "
                "AND name NOT LIKE 'sqlite_%' "
                "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name"
            )
        ]
    with sqlite3.connect(path) as connection:
        connection.executescript(";\n".join(mutate(statements)) + ";")
        connection.execute("PRAGMA user_version = 2")


def test_exact_v2_schema_requires_exact_user_version(tmp_path) -> None:
    path = tmp_path / "current.sqlite"
    _create_exact_v2_database(path)
    with SQLiteDecisionEvidenceLedger(path):
        pass
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version = 9")
    with pytest.raises(LedgerIntegrityError, match="unsupported user version"):
        SQLiteDecisionEvidenceLedger(path)
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9


def test_current_schema_rejects_extra_unique_and_trigger_behavior(tmp_path) -> None:
    path = tmp_path / "current.sqlite"
    _create_exact_v2_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE UNIQUE INDEX extra_window_blocker ON fdml_outcomes(experiment_id)"
        )
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)

    path = tmp_path / "trigger.sqlite"
    _create_exact_v2_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER fdml_outcomes_no_update")
        connection.execute(
            "CREATE TRIGGER fdml_outcomes_no_update BEFORE UPDATE ON fdml_outcomes "
            "BEGIN SELECT 'fdml evidence ledger is append-only'; END"
        )
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)


def test_current_schema_rejects_missing_or_extra_trigger(tmp_path) -> None:
    path = tmp_path / "trigger.sqlite"
    _create_exact_v2_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER fdml_outcomes_no_delete")
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)


def test_current_schema_rejects_fk_action_and_extra_check(tmp_path) -> None:
    path = tmp_path / "fk.sqlite"
    _clone_v2_schema(
        path,
        lambda statements: [
            statement.replace(
                "REFERENCES fdml_evidence(experiment_id, record_identity)",
                "REFERENCES fdml_evidence(experiment_id, record_identity) ON DELETE CASCADE",
            )
            for statement in statements
        ],
    )
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)

    path = tmp_path / "check.sqlite"
    _clone_v2_schema(
        path,
        lambda statements: [
            statement.replace(
                "evidence_identity TEXT NOT NULL,",
                "evidence_identity TEXT NOT NULL CHECK (evidence_identity != ''),",
            )
            for statement in statements
        ],
    )
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)

    path = tmp_path / "extra-trigger.sqlite"
    _create_exact_v2_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER behavior_change AFTER INSERT ON fdml_outcomes BEGIN SELECT 1; END"
        )
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)


def test_fresh_and_legacy_migrated_v2_converge_to_one_descriptor(tmp_path) -> None:
    fresh = tmp_path / "fresh.sqlite"
    legacy = tmp_path / "legacy.sqlite"
    _create_exact_v2_database(fresh)
    _create_legacy_database(legacy)
    with SQLiteDecisionEvidenceLedger(legacy):
        pass
    with sqlite3.connect(fresh) as fresh_connection, sqlite3.connect(legacy) as legacy_connection:
        fresh_connection.row_factory = sqlite3.Row
        legacy_connection.row_factory = sqlite3.Row
        assert SQLiteDecisionEvidenceLedger._schema_descriptor(
            fresh_connection
        ) == SQLiteDecisionEvidenceLedger._schema_descriptor(legacy_connection)


@pytest.mark.parametrize(
    "name, mutate",
    (
        (
            "deferred_fk",
            lambda statements: [
                statement.replace(
                    "REFERENCES fdml_evidence(experiment_id, record_identity)",
                    "REFERENCES fdml_evidence(experiment_id, record_identity) "
                    "DEFERRABLE INITIALLY DEFERRED",
                )
                for statement in statements
            ],
        ),
        (
            "partial_unique",
            lambda statements: [
                statement.replace(
                    "record_identity TEXT NOT NULL UNIQUE", "record_identity TEXT NOT NULL"
                )
                for statement in statements
            ]
            + [
                "CREATE UNIQUE INDEX partial_identity ON fdml_outcomes(record_identity) "
                "WHERE record_identity <> ''"
            ],
        ),
        (
            "extra_non_unique_index",
            lambda statements: [
                *statements,
                "CREATE INDEX extra_index ON fdml_outcomes(evaluation_window COLLATE NOCASE DESC)",
            ],
        ),
    ),
)
def test_current_schema_descriptor_rejects_unrepresented_v3_semantic_attacks(
    tmp_path, name, mutate
) -> None:
    path = tmp_path / f"{name}.sqlite"
    _clone_v2_schema(path, mutate)
    before = _legacy_snapshot(path)
    with pytest.raises(LedgerIntegrityError, match="exact descriptor"):
        SQLiteDecisionEvidenceLedger(path)
    assert _legacy_snapshot(path) == before
