"""Deterministic export helpers for FDML experiment analysis datasets."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from typing import Any

from .experiment import ExperimentEvidenceV0
from .outcome import EvaluationResult, OutcomeRecord
from .persistence import evaluation_identity, outcome_identity
from .serialization import canonical_value

EXPORT_FIELDS = (
    "experiment_id",
    "state_hash",
    "model_identity",
    "decision",
    "confidence",
    "outcome",
    "evaluation",
)

LEDGER_LINK_FIELDS = (
    "evaluation_window",
    "decision_event_id",
    "request_identity",
    "result_identity",
    "experiment_record_identity",
    "evidence_identity",
    "experiment_schema_version",
    "validation_metadata",
    "outcome_identity",
    "evaluation_identity",
)
LEDGER_EXPORT_FIELDS = EXPORT_FIELDS + LEDGER_LINK_FIELDS


def _normalise_record(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        LEDGER_EXPORT_FIELDS
        if any(field in record for field in LEDGER_LINK_FIELDS)
        else EXPORT_FIELDS
    )
    return {field: record.get(field) for field in fields}


def build_ledger_export_record(
    *,
    evidence: ExperimentEvidenceV0,
    confidence: float,
    outcome: OutcomeRecord | None = None,
    evaluation: EvaluationResult | None = None,
) -> dict[str, Any]:
    """Build one frozen-schema export row linked to immutable ledger identities."""
    experiment = evidence.experiment_record
    if outcome is not None and outcome.experiment_id != experiment.experiment_id:
        raise ValueError("outcome does not belong to the experiment")
    if evaluation is not None:
        if outcome is None:
            raise ValueError("evaluation export requires its linked outcome")
        if evaluation.experiment_id != experiment.experiment_id:
            raise ValueError("evaluation does not belong to the experiment")
        if evaluation.evaluation_window != outcome.evaluation_window:
            raise ValueError("evaluation does not bind the outcome evaluation window")
    return {
        "experiment_id": experiment.experiment_id,
        "state_hash": experiment.state_hash,
        "model_identity": canonical_value(experiment.model_identity),
        "decision": evidence.output_decision,
        "confidence": confidence,
        "outcome": None if outcome is None else outcome.model_dump(mode="json"),
        "evaluation": None if evaluation is None else evaluation.model_dump(mode="json"),
        "evaluation_window": None if outcome is None else outcome.evaluation_window,
        "decision_event_id": experiment.decision_event_id,
        "request_identity": experiment.request_identity,
        "result_identity": experiment.result_identity,
        "experiment_record_identity": experiment.record_identity,
        "evidence_identity": evidence.evidence_identity,
        "experiment_schema_version": experiment.schema_version,
        "validation_metadata": evidence.validation_metadata,
        "outcome_identity": None if outcome is None else outcome_identity(outcome),
        "evaluation_identity": (None if evaluation is None else evaluation_identity(evaluation)),
    }


def _ordered_rows(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [_normalise_record(record) for record in records]
    return sorted(
        rows,
        key=lambda row: (
            str(row["experiment_id"]),
            json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        ),
    )


def export_jsonl(records: Iterable[dict[str, Any]]) -> str:
    """Return stable JSONL export ordered by experiment_id."""
    rows = _ordered_rows(records)
    return "".join(
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
        for row in rows
    )


def export_csv(records: Iterable[dict[str, Any]]) -> str:
    """Return stable CSV export with fixed schema ordering."""
    rows = _ordered_rows(records)
    fields = tuple(rows[0]) if rows else EXPORT_FIELDS
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(
        {
            field: (
                json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                if isinstance(value, dict | list)
                else value
            )
            for field, value in row.items()
        }
        for row in rows
    )
    return output.getvalue()


def validate_schema(record: dict[str, Any]) -> bool:
    """Validate the minimal frozen export schema."""
    return frozenset(record) in {frozenset(EXPORT_FIELDS), frozenset(LEDGER_EXPORT_FIELDS)}
