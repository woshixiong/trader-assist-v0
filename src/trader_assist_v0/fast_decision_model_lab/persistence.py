from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from os import PathLike
from typing import Any, cast

from .experiment import ExperimentEvidenceV0, ExperimentRecordV0
from .outcome import EvaluationResult, OutcomeRecord
from .serialization import canonical_json, canonical_sha256

SCHEMA_VERSION = 2


class LedgerError(RuntimeError):
    """Base error for deterministic FDML ledger failures."""


class LedgerConflictError(LedgerError):
    """An immutable ledger identity was reused for different evidence."""


class LedgerIntegrityError(LedgerError):
    """Stored evidence or its linkage failed integrity validation."""


def _pydantic_payload(record: OutcomeRecord | EvaluationResult) -> dict[str, Any]:
    return record.model_dump(mode="json")


def outcome_identity(record: OutcomeRecord) -> str:
    return canonical_sha256(_pydantic_payload(record))


def evaluation_identity(record: EvaluationResult) -> str:
    return canonical_sha256(_pydantic_payload(record))


class SQLiteDecisionEvidenceLedger:
    """Append-only SQLite evidence store keyed by exact outcome windows."""

    def __init__(self, path: str | PathLike[str]) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def __enter__(self) -> SQLiteDecisionEvidenceLedger:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
            ).fetchone()
            is not None
        )

    @staticmethod
    def _table_columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
        return tuple(row["name"] for row in connection.execute(f"PRAGMA table_info({table})"))

    def _initialize_schema(self) -> None:
        if not self._table_exists(self._connection, "fdml_outcomes"):
            with self._connection:
                self._create_current_schema()
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            return
        columns = self._table_columns(self._connection, "fdml_outcomes")
        if "evaluation_window" in columns:
            with self._connection:
                self._create_current_schema()
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            return
        self._migrate_legacy_schema()

    def _create_current_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS fdml_experiments (
                experiment_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                UNIQUE (experiment_id, record_identity)
            );
            CREATE TABLE IF NOT EXISTS fdml_evidence (
                experiment_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL,
                UNIQUE (experiment_id, record_identity),
                FOREIGN KEY (experiment_id, experiment_record_identity)
                    REFERENCES fdml_experiments(experiment_id, record_identity)
            );
            CREATE TABLE IF NOT EXISTS fdml_outcomes (
                experiment_id TEXT NOT NULL,
                evaluation_window INTEGER NOT NULL CHECK (evaluation_window > 0),
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL,
                evidence_identity TEXT NOT NULL,
                PRIMARY KEY (experiment_id, evaluation_window),
                UNIQUE (experiment_id, evaluation_window, record_identity),
                FOREIGN KEY (experiment_id, experiment_record_identity)
                    REFERENCES fdml_experiments(experiment_id, record_identity),
                FOREIGN KEY (experiment_id, evidence_identity)
                    REFERENCES fdml_evidence(experiment_id, record_identity)
            );
            CREATE TABLE IF NOT EXISTS fdml_evaluations (
                experiment_id TEXT NOT NULL,
                evaluation_window INTEGER NOT NULL CHECK (evaluation_window > 0),
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                outcome_identity TEXT NOT NULL,
                PRIMARY KEY (experiment_id, evaluation_window),
                FOREIGN KEY (experiment_id, evaluation_window, outcome_identity)
                    REFERENCES fdml_outcomes(
                        experiment_id, evaluation_window, record_identity
                    )
            );
            """
        )
        self._create_append_only_triggers()

    def _create_append_only_triggers(self) -> None:
        for table in (
            "fdml_experiments",
            "fdml_evidence",
            "fdml_outcomes",
            "fdml_evaluations",
        ):
            self._connection.execute(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_update "
                f"BEFORE UPDATE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END"
            )
            self._connection.execute(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete "
                f"BEFORE DELETE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END"
            )

    @staticmethod
    def _legacy_payload(row: sqlite3.Row) -> dict[str, Any]:
        try:
            payload = json.loads(row["record_json"])
        except (json.JSONDecodeError, TypeError) as error:
            raise LedgerIntegrityError("legacy ledger row does not contain valid JSON") from error
        if not isinstance(payload, dict):
            raise LedgerIntegrityError("legacy ledger row payload must be an object")
        if canonical_json(payload) != row["record_json"]:
            raise LedgerIntegrityError("legacy ledger row JSON is not canonical")
        if canonical_sha256(payload) != row["record_identity"]:
            raise LedgerIntegrityError("legacy ledger identity does not match its payload")
        if payload.get("experiment_id") != row["experiment_id"]:
            raise LedgerIntegrityError("legacy ledger experiment linkage is inconsistent")
        return payload

    def _migrate_legacy_schema(self) -> None:
        expected_outcome_columns = (
            "experiment_id",
            "record_json",
            "record_identity",
            "experiment_record_identity",
            "evidence_identity",
        )
        expected_evaluation_columns = (
            "experiment_id",
            "record_json",
            "record_identity",
            "outcome_identity",
        )
        if self._table_columns(self._connection, "fdml_outcomes") != expected_outcome_columns:
            raise LedgerIntegrityError("unsupported or ambiguous legacy outcome schema")
        if self._table_columns(self._connection, "fdml_evaluations") != expected_evaluation_columns:
            raise LedgerIntegrityError("unsupported or ambiguous legacy evaluation schema")
        outcomes = self._connection.execute(
            "SELECT * FROM fdml_outcomes ORDER BY experiment_id"
        ).fetchall()
        evaluations = self._connection.execute(
            "SELECT * FROM fdml_evaluations ORDER BY experiment_id"
        ).fetchall()
        migrated_evaluations: list[tuple[sqlite3.Row, EvaluationResult, str]] = []
        outcomes_by_identity: dict[tuple[str, str], OutcomeRecord] = {}
        for row in outcomes:
            payload = self._legacy_payload(row)
            try:
                outcome = OutcomeRecord.model_validate(payload)
            except (TypeError, ValueError) as error:
                raise LedgerIntegrityError("invalid legacy outcome record") from error
            outcomes_by_identity[(outcome.experiment_id, row["record_identity"])] = outcome
        for row in evaluations:
            payload = self._legacy_payload(row)
            linked_outcome = outcomes_by_identity.get(
                (row["experiment_id"], row["outcome_identity"])
            )
            if linked_outcome is None:
                raise LedgerIntegrityError("legacy evaluation cannot map exactly to an outcome")
            payload["evaluation_window"] = linked_outcome.evaluation_window
            try:
                evaluation = EvaluationResult.model_validate(payload)
            except (TypeError, ValueError) as error:
                raise LedgerIntegrityError("invalid legacy evaluation record") from error
            migrated_evaluations.append(
                (row, evaluation, canonical_json(_pydantic_payload(evaluation)))
            )
        try:
            with self._connection:
                self._connection.execute(
                    "CREATE TABLE fdml_outcomes_v2 ("
                    "experiment_id TEXT NOT NULL, evaluation_window INTEGER NOT NULL "
                    "CHECK (evaluation_window > 0), record_json TEXT NOT NULL, "
                    "record_identity TEXT NOT NULL UNIQUE, "
                    "experiment_record_identity TEXT NOT NULL, "
                    "evidence_identity TEXT NOT NULL, "
                    "PRIMARY KEY (experiment_id, evaluation_window), "
                    "UNIQUE (experiment_id, evaluation_window, record_identity), "
                    "FOREIGN KEY (experiment_id, experiment_record_identity) "
                    "REFERENCES fdml_experiments(experiment_id, record_identity), "
                    "FOREIGN KEY (experiment_id, evidence_identity) "
                    "REFERENCES fdml_evidence(experiment_id, record_identity))"
                )
                self._connection.execute(
                    "CREATE TABLE fdml_evaluations_v2 ("
                    "experiment_id TEXT NOT NULL, evaluation_window INTEGER NOT NULL "
                    "CHECK (evaluation_window > 0), record_json TEXT NOT NULL, "
                    "record_identity TEXT NOT NULL UNIQUE, outcome_identity TEXT NOT NULL, "
                    "PRIMARY KEY (experiment_id, evaluation_window), "
                    "FOREIGN KEY (experiment_id, evaluation_window, outcome_identity) "
                    "REFERENCES fdml_outcomes_v2("
                    "experiment_id, evaluation_window, record_identity))"
                )
                for row in outcomes:
                    outcome = outcomes_by_identity[(row["experiment_id"], row["record_identity"])]
                    self._connection.execute(
                        "INSERT INTO fdml_outcomes_v2 VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            row["experiment_id"],
                            outcome.evaluation_window,
                            row["record_json"],
                            row["record_identity"],
                            row["experiment_record_identity"],
                            row["evidence_identity"],
                        ),
                    )
                for row, evaluation, record_json in migrated_evaluations:
                    self._connection.execute(
                        "INSERT INTO fdml_evaluations_v2 VALUES (?, ?, ?, ?, ?)",
                        (
                            row["experiment_id"],
                            evaluation.evaluation_window,
                            record_json,
                            evaluation_identity(evaluation),
                            row["outcome_identity"],
                        ),
                    )
                self._connection.execute("DROP TABLE fdml_evaluations")
                self._connection.execute("DROP TABLE fdml_outcomes")
                self._connection.execute("ALTER TABLE fdml_outcomes_v2 RENAME TO fdml_outcomes")
                self._connection.execute(
                    "ALTER TABLE fdml_evaluations_v2 RENAME TO fdml_evaluations"
                )
                if self._connection.execute("SELECT COUNT(*) FROM fdml_outcomes").fetchone()[
                    0
                ] != len(outcomes):
                    raise LedgerIntegrityError("legacy migration outcome row count changed")
                if self._connection.execute("SELECT COUNT(*) FROM fdml_evaluations").fetchone()[
                    0
                ] != len(evaluations):
                    raise LedgerIntegrityError("legacy migration evaluation row count changed")
                self._create_append_only_triggers()
                self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        except sqlite3.DatabaseError as error:
            raise LedgerIntegrityError("legacy migration failed without committing") from error
        self.validate_integrity()

    def _append(
        self,
        *,
        table: str,
        experiment_id: str,
        evaluation_window: int | None,
        record_json: str,
        record_identity: str,
        linkage: tuple[tuple[str, str], ...] = (),
    ) -> bool:
        expected_linkage = {
            "fdml_experiments": (),
            "fdml_evidence": ("experiment_record_identity",),
            "fdml_outcomes": ("experiment_record_identity", "evidence_identity"),
            "fdml_evaluations": ("outcome_identity",),
        }
        window_tables = {"fdml_outcomes", "fdml_evaluations"}
        if table not in expected_linkage:
            raise ValueError("unsupported evidence table")
        if (table in window_tables) != (evaluation_window is not None):
            raise ValueError("invalid outcome identity")
        linkage_names = tuple(name for name, _value in linkage)
        if linkage_names != expected_linkage[table]:
            raise ValueError("invalid evidence linkage columns")
        identity_names = ("experiment_id",) + (
            ("evaluation_window",) if evaluation_window is not None else ()
        )
        column_names = (*identity_names, "record_json", "record_identity", *linkage_names)
        values = (
            experiment_id,
            *((evaluation_window,) if evaluation_window is not None else ()),
            record_json,
            record_identity,
            *(value for _name, value in linkage),
        )
        placeholders = ", ".join("?" for _name in column_names)
        columns = ", ".join(column_names)
        conflict_columns = ", ".join(identity_names)
        with self._connection:
            cursor = self._connection.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                f"ON CONFLICT({conflict_columns}) DO NOTHING",
                values,
            )
            row = self._load_row(table, experiment_id, evaluation_window)
            if row is None:
                raise LedgerIntegrityError("ledger append did not produce a durable row")
            if row["record_json"] != record_json or row["record_identity"] != record_identity:
                raise LedgerConflictError("conflicting immutable evidence for outcome identity")
            if any(row[name] != value for name, value in linkage):
                raise LedgerConflictError("conflicting immutable linkage for outcome identity")
            return cursor.rowcount == 1

    def append_experiment(self, record: ExperimentRecordV0) -> bool:
        return self._append(
            table="fdml_experiments",
            experiment_id=record.experiment_id,
            evaluation_window=None,
            record_json=record.canonical_json(),
            record_identity=record.record_identity,
        )

    def append_outcome(self, record: OutcomeRecord) -> bool:
        evidence = self.load_evidence(record.experiment_id)
        if evidence is None:
            raise LedgerIntegrityError("outcome requires existing experiment evidence")
        payload = _pydantic_payload(record)
        return self._append(
            table="fdml_outcomes",
            experiment_id=record.experiment_id,
            evaluation_window=record.evaluation_window,
            record_json=canonical_json(payload),
            record_identity=outcome_identity(record),
            linkage=(
                ("experiment_record_identity", evidence.experiment_record.record_identity),
                ("evidence_identity", evidence.evidence_identity),
            ),
        )

    def append_evaluation(self, record: EvaluationResult) -> bool:
        outcome = self.load_outcome(record.experiment_id, record.evaluation_window)
        if outcome is None:
            raise LedgerIntegrityError(
                "evaluation requires an existing outcome for its exact window"
            )
        payload = _pydantic_payload(record)
        return self._append(
            table="fdml_evaluations",
            experiment_id=record.experiment_id,
            evaluation_window=record.evaluation_window,
            record_json=canonical_json(payload),
            record_identity=evaluation_identity(record),
            linkage=(("outcome_identity", outcome_identity(outcome)),),
        )

    def append_evidence(self, evidence: ExperimentEvidenceV0) -> bool:
        self.append_experiment(evidence.experiment_record)
        return self._append(
            table="fdml_evidence",
            experiment_id=evidence.experiment_id,
            evaluation_window=None,
            record_json=evidence.canonical_json(),
            record_identity=evidence.evidence_identity,
            linkage=(("experiment_record_identity", evidence.experiment_record.record_identity),),
        )

    def _load_row(
        self, table: str, experiment_id: str, evaluation_window: int | None = None
    ) -> sqlite3.Row | None:
        window_tables = {"fdml_outcomes", "fdml_evaluations"}
        if table not in {"fdml_experiments", "fdml_evidence", *window_tables}:
            raise ValueError("unsupported evidence table")
        if (table in window_tables) != (evaluation_window is not None):
            raise ValueError("invalid outcome identity")
        query = f"SELECT * FROM {table} WHERE experiment_id = ?"
        values: tuple[object, ...] = (experiment_id,)
        if evaluation_window is not None:
            query += " AND evaluation_window = ?"
            values += (evaluation_window,)
        return cast(sqlite3.Row | None, self._connection.execute(query, values).fetchone())

    @staticmethod
    def _validated_payload(row: sqlite3.Row) -> dict[str, Any]:
        payload = SQLiteDecisionEvidenceLedger._legacy_payload(row)
        if (
            "evaluation_window" in row.keys()
            and payload.get("evaluation_window") != row["evaluation_window"]
        ):
            raise LedgerIntegrityError("ledger outcome window linkage is inconsistent")
        return payload

    def load_experiment(self, experiment_id: str) -> ExperimentRecordV0 | None:
        row = self._load_row("fdml_experiments", experiment_id)
        if row is None:
            return None
        try:
            record = ExperimentRecordV0.from_payload(self._validated_payload(row))
        except (TypeError, ValueError) as error:
            raise LedgerIntegrityError("invalid stored experiment record") from error
        if record.record_identity != row["record_identity"]:
            raise LedgerIntegrityError("experiment record identity failed reconstruction")
        return record

    def load_evidence(self, experiment_id: str) -> ExperimentEvidenceV0 | None:
        row = self._load_row("fdml_evidence", experiment_id)
        if row is None:
            return None
        try:
            evidence = ExperimentEvidenceV0.from_payload(self._validated_payload(row))
        except (TypeError, ValueError) as error:
            raise LedgerIntegrityError("invalid stored experiment evidence") from error
        experiment = self.load_experiment(experiment_id)
        if experiment is None or evidence.experiment_record != experiment:
            raise LedgerIntegrityError("experiment evidence record linkage is inconsistent")
        if row["experiment_record_identity"] != experiment.record_identity:
            raise LedgerIntegrityError("experiment evidence identity linkage is inconsistent")
        if evidence.evidence_identity != row["record_identity"]:
            raise LedgerIntegrityError("experiment evidence identity failed reconstruction")
        return evidence

    def load_outcome(self, experiment_id: str, evaluation_window: int) -> OutcomeRecord | None:
        row = self._load_row("fdml_outcomes", experiment_id, evaluation_window)
        if row is None:
            return None
        try:
            record = OutcomeRecord.model_validate(self._validated_payload(row))
        except (TypeError, ValueError) as error:
            raise LedgerIntegrityError("invalid stored outcome record") from error
        if outcome_identity(record) != row["record_identity"]:
            raise LedgerIntegrityError("outcome identity failed reconstruction")
        evidence = self.load_evidence(experiment_id)
        if evidence is None:
            raise LedgerIntegrityError("outcome has no experiment evidence")
        if row["experiment_record_identity"] != evidence.experiment_record.record_identity:
            raise LedgerIntegrityError("outcome experiment linkage is inconsistent")
        if row["evidence_identity"] != evidence.evidence_identity:
            raise LedgerIntegrityError("outcome evidence linkage is inconsistent")
        return record

    def load_evaluation(
        self, experiment_id: str, evaluation_window: int
    ) -> EvaluationResult | None:
        row = self._load_row("fdml_evaluations", experiment_id, evaluation_window)
        if row is None:
            return None
        try:
            record = EvaluationResult.model_validate(self._validated_payload(row))
        except (TypeError, ValueError) as error:
            raise LedgerIntegrityError("invalid stored evaluation record") from error
        if evaluation_identity(record) != row["record_identity"]:
            raise LedgerIntegrityError("evaluation identity failed reconstruction")
        outcome = self.load_outcome(experiment_id, evaluation_window)
        if outcome is None or row["outcome_identity"] != outcome_identity(outcome):
            raise LedgerIntegrityError("evaluation outcome linkage is inconsistent")
        return record

    def iter_experiments(self) -> Iterator[ExperimentRecordV0]:
        rows = self._connection.execute(
            "SELECT experiment_id FROM fdml_experiments ORDER BY experiment_id"
        ).fetchall()
        for row in rows:
            record = self.load_experiment(row["experiment_id"])
            if record is None:
                raise LedgerIntegrityError("experiment disappeared during deterministic load")
            yield record

    def validate_integrity(self) -> bool:
        if [row[0] for row in self._connection.execute("PRAGMA quick_check")] != ["ok"]:
            raise LedgerIntegrityError("SQLite quick_check failed")
        if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise LedgerIntegrityError("ledger foreign-key linkage failed")
        experiment_ids = {
            row[0] for row in self._connection.execute("SELECT experiment_id FROM fdml_experiments")
        }
        evidence_ids = {
            row[0] for row in self._connection.execute("SELECT experiment_id FROM fdml_evidence")
        }
        outcome_keys = {
            tuple(row)
            for row in self._connection.execute(
                "SELECT experiment_id, evaluation_window FROM fdml_outcomes"
            )
        }
        evaluation_keys = {
            tuple(row)
            for row in self._connection.execute(
                "SELECT experiment_id, evaluation_window FROM fdml_evaluations"
            )
        }
        if not evaluation_keys <= outcome_keys:
            raise LedgerIntegrityError("ledger evaluation linkage is incomplete")
        if (
            not {experiment_id for experiment_id, _window in outcome_keys}
            <= evidence_ids
            <= experiment_ids
        ):
            raise LedgerIntegrityError("ledger evidence linkage is incomplete")
        for experiment_id in sorted(experiment_ids):
            self.load_experiment(experiment_id)
        for experiment_id in sorted(evidence_ids):
            self.load_evidence(experiment_id)
        for experiment_id, evaluation_window in sorted(outcome_keys):
            self.load_outcome(experiment_id, evaluation_window)
        for experiment_id, evaluation_window in sorted(evaluation_keys):
            self.load_evaluation(experiment_id, evaluation_window)
        return True


DecisionEvidenceLedger = SQLiteDecisionEvidenceLedger
