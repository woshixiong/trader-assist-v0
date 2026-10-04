"""Bounded supplied-file reference import; no download or source acquisition."""

import csv
import io
from pathlib import Path
from typing import Literal

from pydantic import Field

from trader_assist_v0.contracts.common import sha256_hex

from .admission import ExternalReferenceAdmission, ExternalReferenceLedger
from .contracts import (
    BarPayload,
    BoundRecord,
    ExternalReferenceEvent,
    SourceMode,
    TimestampProvenance,
)


class FreeReferenceImportSpec(BoundRecord):
    format: Literal["EXTERNAL_EVENT_JSONL", "BAR_CSV_V1"]
    checksum: str = Field(pattern="^[a-f0-9]{64}$")
    max_bytes: int = Field(gt=0, le=4_000_000)
    max_rows: int = Field(gt=0, le=100_000)
    timezone: str = Field(min_length=1)
    session: str = Field(min_length=1)
    adjustment_policy: Literal["UNADJUSTED_EXPLICIT", "SOURCE_ADJUSTED_VERIFIED"]
    adjustment_provenance: str = Field(min_length=1)


def import_free_reference(
    path: Path,
    spec: FreeReferenceImportSpec,
    admission: ExternalReferenceAdmission,
    *,
    observed_at_ns: int,
) -> ExternalReferenceLedger:
    spec = FreeReferenceImportSpec.model_validate_json(spec.model_dump_json())
    admission.dataset.require_access("PIPELINE_CORRECTNESS_ONLY", admission.satisfied)
    dataset = admission.dataset
    if (
        spec.checksum != dataset.checksum
        or spec.timezone != dataset.timezone
        or spec.session != dataset.session_semantics
    ):
        raise ValueError("import provenance/dataset binding mismatch")
    # Rights and sealed checks precede file access. Only explicitly supplied files are read.
    with path.open("rb") as handle:
        raw = handle.read(spec.max_bytes + 1)
    if len(raw) > spec.max_bytes or sha256_hex(raw) != spec.checksum:
        raise ValueError("import bytes/checksum mismatch")
    text = raw.decode("utf-8", errors="strict")
    events: list[ExternalReferenceEvent] = []
    if spec.format == "EXTERNAL_EVENT_JSONL":
        lines = text.splitlines()
        if len(lines) > spec.max_rows:
            raise ValueError("import row bound exceeded")
        for line in lines:
            # Bound event hash and strict Pydantic schema reject malformed supplied contracts.
            events.append(ExternalReferenceEvent.model_validate_json(line))
    else:
        if any(not line.strip() for line in text.splitlines()):
            raise ValueError("blank record in strict CSV profile")
        reader = csv.DictReader(io.StringIO(text))
        columns = {
            "instrument_id",
            "native_id",
            "source_ts_ns",
            "interval_minutes",
            "start_ns",
            "end_ns",
            "timestamp_meaning",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }
        if (
            reader.fieldnames is None
            or set(reader.fieldnames) != columns
            or len(reader.fieldnames) != len(columns)
        ):
            raise ValueError("strict CSV profile columns required")
        rights = dataset.rights
        assert rights is not None
        for ordinal, row in enumerate(reader):
            if ordinal >= spec.max_rows or None in row or any(v is None for v in row.values()):
                raise ValueError("row bound or malformed CSV")
            timestamp = row["source_ts_ns"]
            if not timestamp.isascii() or not timestamp.isdecimal():
                raise ValueError("ambiguous/DST timestamp; exact source nanoseconds required")
            minutes = int(row["interval_minutes"])
            capability = next(
                c
                for c in admission.capabilities
                if c.datatype == f"BAR_{minutes}M"
                and c.source_mode == SourceMode.FREE_REFERENCE_IMPORT
            )
            payload = BarPayload.model_validate(
                dict(
                    interval_minutes=minutes,
                    start_ns=int(row["start_ns"]),
                    end_ns=int(row["end_ns"]),
                    timestamp_meaning=row["timestamp_meaning"],
                    finalized=True,
                    aggregation_origin=spec.adjustment_provenance,
                    **{key: row[key] for key in ("open", "high", "low", "close", "volume")},
                )
            )
            events.append(
                ExternalReferenceEvent.create(
                    version="1",
                    provider=capability.provider,
                    venue=capability.venue,
                    product=capability.product,
                    instrument_id=row["instrument_id"],
                    mapping_hash=dataset.mapping_hash,
                    dataset_hash=dataset.record_hash,
                    capability_hash=capability.record_hash,
                    rights_hash=rights.record_hash,
                    source_mode=SourceMode.FREE_REFERENCE_IMPORT,
                    native_id=row["native_id"],
                    sequence=None,
                    timestamps=TimestampProvenance(
                        source_ts=timestamp,
                        source_unit="ns",
                        ts_event=int(timestamp),
                        ts_init=None,
                        true_network_receive_ts=None,
                        receive_provenance="NOT_EXPOSED",
                        observed_at_ns=observed_at_ns,
                    ),
                    payload=payload,
                )
            )
    if not events:
        raise ValueError("empty reference import")
    ledger = ExternalReferenceLedger(admission)
    for event in events:
        if event.source_mode != SourceMode.FREE_REFERENCE_IMPORT:
            raise ValueError("import cannot relabel live/history acquisition")
        ledger.observe(event, evaluated_at_ns=observed_at_ns)
    return ledger
