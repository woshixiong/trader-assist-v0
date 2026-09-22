"""Deterministic export helpers for FDML experiment analysis datasets."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from typing import Any


EXPORT_FIELDS = (
    "experiment_id",
    "state_hash",
    "model_identity",
    "decision",
    "confidence",
    "outcome",
    "evaluation",
)


def _normalise_record(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record.get(field) for field in EXPORT_FIELDS}


def export_jsonl(records: Iterable[dict[str, Any]]) -> str:
    """Return stable JSONL export ordered by experiment_id."""
    rows = sorted((_normalise_record(r) for r in records), key=lambda r: str(r["experiment_id"]))
    return "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    )


def export_csv(records: Iterable[dict[str, Any]]) -> str:
    """Return stable CSV export with fixed schema ordering."""
    rows = sorted((_normalise_record(r) for r in records), key=lambda r: str(r["experiment_id"]))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def validate_schema(record: dict[str, Any]) -> bool:
    """Validate the minimal frozen export schema."""
    return set(record) == set(EXPORT_FIELDS)
