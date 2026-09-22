from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from os import PathLike
from typing import Any

from .experiment import ExperimentEvidenceV0, ExperimentRecordV0
from .outcome import EvaluationResult, OutcomeRecord
from .serialization import canonical_json, canonical_sha256


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
    """Standard-library SQLite store for immutable FDML evidence linkage."""

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

    def _initialize_schema(self) -> None:
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
                experiment_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                experiment_record_identity TEXT NOT NULL,
                evidence_identity TEXT NOT NULL,
                UNIQUE (experiment_id, record_identity),
                FOREIGN KEY (experiment_id, experiment_record_identity)
                    REFERENCES fdml_experiments(experiment_id, record_identity),
                FOREIGN KEY (experiment_id, evidence_identity)
                    REFERENCES fdml_evidence(experiment_id, record_identity)
            );
            CREATE TABLE IF NOT EXISTS fdml_evaluations (
                experiment_id TEXT PRIMARY KEY,
                record_json TEXT NOT NULL,
                record_identity TEXT NOT NULL UNIQUE,
                outcome_identity TEXT NOT NULL,
                FOREIGN KEY (experiment_id, outcome_identity)
                    REFERENCES fdml_outcomes(experiment_id, record_identity)
            );

            CREATE TRIGGER IF NOT EXISTS fdml_experiments_no_update
            BEFORE UPDATE ON fdml_experiments
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_experiments_no_delete
            BEFORE DELETE ON fdml_experiments
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_evidence_no_update
            BEFORE UPDATE ON fdml_evidence
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_evidence_no_delete
            BEFORE DELETE ON fdml_evidence
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_outcomes_no_update
            BEFORE UPDATE ON fdml_outcomes
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_outcomes_no_delete
            BEFORE DELETE ON fdml_outcomes
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_evaluations_no_update
            BEFORE UPDATE ON fdml_evaluations
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fdml_evaluations_no_delete
            BEFORE DELETE ON fdml_evaluations
            BEGIN SELECT RAISE(ABORT, 'fdml evidence ledger is append-only'); END;
            """
        )
        self._connection.commit()

    def _append(
        self,
        *,
        table: str,
        experiment_id: str,
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
        if table not in expected_linkage:
            raise ValueError("unsupported evidence table")
        linkage_names = tuple(name for name, _value in linkage)
        if linkage_names != expected_linkage[table]:
            raise ValueError("invalid evidence linkage columns")
        column_names = ("experiment_id", "record_json", "record_identity", *linkage_names)
        values = (experiment_id, record_json, record_identity, *(value for _name, value in linkage))
        placeholders = ", ".join("?" for _name in column_names)
        columns = ", ".join(column_names)
        with self._connection:
            cursor = self._connection.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
                "ON CONFLICT(experiment_id) DO NOTHING",
                values,
            )
            row = self._connection.execute(
                f"SELECT * FROM {table} WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
            if row is None:
                raise LedgerIntegrityError("ledger append did not produce a durable row")
            if row["record_json"] != record_json or row["record_identity"] != record_identity:
                raise LedgerConflictError(
                    f"conflicting immutable evidence for experiment_id {experiment_id!r}"
                )
            if any(row[name] != value for name, value in linkage):
                raise LedgerConflictError(
                    f"conflicting immutable linkage for experiment_id {experiment_id!r}"
                )
            return cursor.rowcount == 1

    def append_experiment(self, record: ExperimentRecordV0) -> bool:
        return self._append(
            table="fdml_experiments",
            experiment_id=record.experiment_id,
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
            record_json=canonical_json(payload),
            record_identity=canonical_sha256(payload),
            linkage=(
                ("experiment_record_identity", evidence.experiment_record.record_identity),
                ("evidence_identity", evidence.evidence_identity),
            ),
        )

    def append_evaluation(self, record: EvaluationResult) -> bool:
        outcome = self.load_outcome(record.experiment_id)
        if outcome is None:
            raise LedgerIntegrityError("evaluation requires an existing outcome record")
        payload = _pydantic_payload(record)
        return self._append(
            table="fdml_evaluations",
            experiment_id=record.experiment_id,
            record_json=canonical_json(payload),
            record_identity=canonical_sha256(payload),
            linkage=(("outcome_identity", outcome_identity(outcome)),),
        )

    def append_evidence(self, evidence: ExperimentEvidenceV0) -> bool:
        self.append_experiment(evidence.experiment_record)
        return self._append(
            table="fdml_evidence",
            experiment_id=evidence.experiment_id,
            record_json=evidence.canonical_json(),
            record_identity=evidence.evidence_identity,
            linkage=(
                (
                    "experiment_record_identity",
                    evidence.experiment_record.record_identity,
                ),
            ),
        )

    def _load_row(self, table: str, experiment_id: str) -> sqlite3.Row | None:
        if table not in {
            "fdml_experiments",
            "fdml_evidence",
            "fdml_outcomes",
            "fdml_evaluations",
        }:
            raise ValueError("unsupported evidence table")
        return self._connection.execute(
            f"SELECT * FROM {table} WHERE experiment_id = ?",
            (experiment_id,),
        ).fetchone()

    @staticmethod
    def _validated_payload(row: sqlite3.Row) -> dict[str, Any]:
        try:
            payload = json.loads(row["record_json"])
        except (json.JSONDecodeError, TypeError) as error:
            raise LedgerIntegrityError("ledger row does not contain valid JSON") from error
        if not isinstance(payload, dict):
            raise LedgerIntegrityError("ledger row payload must be an object")
        if canonical_json(payload) != row["record_json"]:
            raise LedgerIntegrityError("ledger row JSON is not canonical")
        if canonical_sha256(payload) != row["record_identity"]:
            raise LedgerIntegrityError("ledger row identity does not match its payload")
        if payload.get("experiment_id") != row["experiment_id"]:
            raise LedgerIntegrityError("ledger row experiment linkage is inconsistent")
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
        if experiment is None:
            raise LedgerIntegrityError("experiment evidence has no experiment record")
        if evidence.experiment_record != experiment:
            raise LedgerIntegrityError("experiment evidence record linkage is inconsistent")
        if row["experiment_record_identity"] != experiment.record_identity:
            raise LedgerIntegrityError("experiment evidence identity linkage is inconsistent")
        if evidence.evidence_identity != row["record_identity"]:
            raise LedgerIntegrityError("experiment evidence identity failed reconstruction")
        return evidence

    def load_outcome(self, experiment_id: str) -> OutcomeRecord | None:
        row = self._load_row("fdml_outcomes", experiment_id)
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

    def load_evaluation(self, experiment_id: str) -> EvaluationResult | None:
        row = self._load_row("fdml_evaluations", experiment_id)
        if row is None:
            return None
        try:
            record = EvaluationResult.model_validate(self._validated_payload(row))
        except (TypeError, ValueError) as error:
            raise LedgerIntegrityError("invalid stored evaluation record") from error
        if evaluation_identity(record) != row["record_identity"]:
            raise LedgerIntegrityError("evaluation identity failed reconstruction")
        outcome = self.load_outcome(experiment_id)
        if outcome is None:
            raise LedgerIntegrityError("evaluation has no outcome record")
        if row["outcome_identity"] != outcome_identity(outcome):
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
        checks = self._connection.execute("PRAGMA quick_check").fetchall()
        if [row[0] for row in checks] != ["ok"]:
            raise LedgerIntegrityError("SQLite quick_check failed")
        if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise LedgerIntegrityError("ledger foreign-key linkage failed")
        experiment_ids = {
            row[0]
            for row in self._connection.execute(
                "SELECT experiment_id FROM fdml_experiments ORDER BY experiment_id"
            )
        }
        outcome_ids = {
            row[0]
            for row in self._connection.execute(
                "SELECT experiment_id FROM fdml_outcomes ORDER BY experiment_id"
            )
        }
        evidence_ids = {
            row[0]
            for row in self._connection.execute(
                "SELECT experiment_id FROM fdml_evidence ORDER BY experiment_id"
            )
        }
        evaluation_ids = {
            row[0]
            for row in self._connection.execute(
                "SELECT experiment_id FROM fdml_evaluations ORDER BY experiment_id"
            )
        }
        if not evaluation_ids <= outcome_ids <= evidence_ids <= experiment_ids:
            raise LedgerIntegrityError("ledger evidence linkage is incomplete")
        for experiment_id in sorted(experiment_ids):
            self.load_experiment(experiment_id)
        for experiment_id in sorted(evidence_ids):
            self.load_evidence(experiment_id)
        for experiment_id in sorted(outcome_ids):
            self.load_outcome(experiment_id)
        for experiment_id in sorted(evaluation_ids):
            self.load_evaluation(experiment_id)
        return True


DecisionEvidenceLedger = SQLiteDecisionEvidenceLedger
