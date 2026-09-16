"""Portable semantic evidence plus bounded column-oriented causal batches."""

from __future__ import annotations

import hmac
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, model_validator

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .contracts import AdmittedEvent, LifecycleRecord, PitUniverseSnapshot, RunManifest


class RawCatalogSink(Protocol):
    """Optional deterministic admission observer used by focused tests."""

    def write(self, events: Sequence[AdmittedEvent]) -> None: ...


class InMemoryCatalogSink:
    """Deterministic test sink; never a production persistence authority."""

    def __init__(self) -> None:
        self.batches: list[tuple[AdmittedEvent, ...]] = []

    def write(self, events: Sequence[AdmittedEvent]) -> None:
        if events:
            self.batches.append(tuple(events))

    @property
    def events(self) -> tuple[AdmittedEvent, ...]:
        return tuple(item for batch in self.batches for item in batch)


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def _write_bound_model(path: Path, model: BaseModel) -> None:
    payload = canonical_json_bytes(model.model_dump(mode="json"))
    _write_atomic(path, payload + b"\n")


class RuntimeCheckpoint(BaseModel):
    """Hash-bound current runtime state for one immutable root Capture run."""

    schema_version: Literal["E4_RUNTIME_CHECKPOINT_V1"] = "E4_RUNTIME_CHECKPOINT_V1"
    manifest_hash: str
    run_id: str
    pit_snapshot_hash: str
    segment_index: int
    checkpoint_sequence: int
    reason: str
    state: dict[str, Any]
    checkpoint_hash: str

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"checkpoint_hash"})

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if self.segment_index < 0 or self.checkpoint_sequence < 0:
            raise ValueError("runtime checkpoint indices must be non-negative")
        expected = sha256_hex(canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.checkpoint_hash, expected):
            raise ValueError("runtime checkpoint hash mismatch")
        return self

    @classmethod
    def create(cls, **values: Any) -> Self:
        payload = {**values, "schema_version": "E4_RUNTIME_CHECKPOINT_V1"}
        payload["checkpoint_hash"] = sha256_hex(canonical_json_bytes(payload))
        return cls.model_validate(payload)


class EvidenceStore:
    """Versioned project truth; high-rate admissions are appended in column batches."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = root / "run-manifest.json"
        self.snapshot_path = root / "pit-universe-snapshot.json"
        self.lifecycle_path = root / "lifecycle.jsonl"
        self.admission_columns_path = root / "causal-admission-columns.jsonl"
        self.runtime_checkpoint_path = root / "runtime-checkpoint.json"
        self.process_segments_path = root / "process-segments.jsonl"

    def initialize(self, manifest: RunManifest, snapshot: PitUniverseSnapshot) -> None:
        if manifest.pit_snapshot_hash != snapshot.snapshot_hash:
            raise ValueError("manifest and PIT snapshot identity conflict")
        if self.manifest_path.exists() or self.snapshot_path.exists():
            raise FileExistsError("Capture evidence identity already exists")
        _write_bound_model(self.manifest_path, manifest)
        _write_bound_model(self.snapshot_path, snapshot)

    def append_lifecycle(self, records: Iterable[LifecycleRecord]) -> None:
        with self.lifecycle_path.open("ab") as stream:
            for record in records:
                stream.write(canonical_json_bytes(record.model_dump(mode="json")) + b"\n")

    def append_admission_batch(self, events: Sequence[AdmittedEvent]) -> None:
        if not events:
            return
        fields = tuple(AdmittedEvent.model_fields)
        columns = {
            field: [event.model_dump(mode="json")[field] for event in events] for field in fields
        }
        payload = {
            "schema": "E4_CAUSAL_COLUMN_BATCH_V1",
            "row_count": len(events),
            "first_ordinal": events[0].admission_ordinal,
            "last_ordinal": events[-1].admission_ordinal,
            "columns": columns,
        }
        with self.admission_columns_path.open("ab") as stream:
            stream.write(canonical_json_bytes(payload) + b"\n")

    def load_manifest(self) -> RunManifest:
        raw = self.manifest_path.read_bytes()
        return RunManifest.model_validate_json(raw)

    def load_snapshot(self) -> PitUniverseSnapshot:
        return PitUniverseSnapshot.model_validate_json(self.snapshot_path.read_bytes())

    def load_lifecycle(self) -> tuple[LifecycleRecord, ...]:
        if not self.lifecycle_path.exists():
            return ()
        return tuple(
            LifecycleRecord.model_validate_json(line)
            for line in self.lifecycle_path.read_bytes().splitlines()
            if line
        )

    def load_admissions(self) -> tuple[AdmittedEvent, ...]:
        if not self.admission_columns_path.exists():
            return ()
        events: list[AdmittedEvent] = []
        for line in self.admission_columns_path.read_bytes().splitlines():
            batch = json.loads(line)
            if batch.get("schema") != "E4_CAUSAL_COLUMN_BATCH_V1":
                raise ValueError("unsupported causal column batch")
            columns = batch["columns"]
            row_count = batch["row_count"]
            if not isinstance(columns, dict) or any(
                not isinstance(values, list) or len(values) != row_count
                for values in columns.values()
            ):
                raise ValueError("corrupt causal column batch")
            for index in range(row_count):
                events.append(
                    AdmittedEvent.model_validate(
                        {field: values[index] for field, values in columns.items()}
                    )
                )
        ordinals = [item.admission_ordinal for item in events]
        if ordinals != sorted(ordinals):
            raise ValueError("stored causal admission order is not deterministic")
        return tuple(events)

    def artifact_hashes(self) -> dict[str, str]:
        paths = (
            self.manifest_path,
            self.snapshot_path,
            self.lifecycle_path,
            self.admission_columns_path,
            self.runtime_checkpoint_path,
            self.process_segments_path,
        )
        return {
            path.name: sha256_hex(path.read_bytes()) for path in paths if path.exists()
        }

    def round_trip_proof(self) -> dict[str, object]:
        manifest = self.load_manifest()
        snapshot = self.load_snapshot()
        lifecycle = self.load_lifecycle()
        admissions = self.load_admissions()
        checkpoint = self.load_runtime_checkpoint(manifest)
        segments = self.load_process_segments()
        return {
            "manifest_hash": manifest.manifest_hash,
            "pit_snapshot_hash": snapshot.snapshot_hash,
            "lifecycle_records": len(lifecycle),
            "admission_records": len(admissions),
            "source_identities": [item.source_identity for item in admissions],
            "causal_ordinals": [item.admission_ordinal for item in admissions],
            "runtime_checkpoint_hash": (
                None if checkpoint is None else checkpoint.checkpoint_hash
            ),
            "process_segment_count": len(segments),
            "readable": True,
            "deterministic": True,
        }

    def write_operational_artifacts(self, artifacts: dict[str, dict[str, object]]) -> None:
        allowed = {
            "capture-source-counts.json",
            "causal-order-replay-proof.json",
            "duplicate-gap-reconnect-prebuffer.json",
            "missingness-not-evaluable-counts.json",
            "catalog-semantic-round-trip.json",
            "capture-health-resource-freshness.json",
            "credential-negative-zero-write.json",
        }
        if set(artifacts) != allowed:
            raise ValueError("operational artifact set is incomplete or unsupported")
        for name, payload in artifacts.items():
            path = self.root / name
            _write_atomic(path, canonical_json_bytes(payload) + b"\n")

    def write_runtime_checkpoint(
        self,
        *,
        manifest: RunManifest,
        state: dict[str, Any],
        segment_index: int,
        checkpoint_sequence: int,
        reason: str,
    ) -> RuntimeCheckpoint:
        checkpoint = RuntimeCheckpoint.create(
            manifest_hash=manifest.manifest_hash,
            run_id=manifest.run_id,
            pit_snapshot_hash=manifest.pit_snapshot_hash,
            segment_index=segment_index,
            checkpoint_sequence=checkpoint_sequence,
            reason=reason,
            state=state,
        )
        _write_bound_model(self.runtime_checkpoint_path, checkpoint)
        return checkpoint

    def load_runtime_checkpoint(self, manifest: RunManifest) -> RuntimeCheckpoint | None:
        if not self.runtime_checkpoint_path.exists():
            return None
        checkpoint = RuntimeCheckpoint.model_validate_json(
            self.runtime_checkpoint_path.read_bytes()
        )
        expected = (manifest.manifest_hash, manifest.run_id, manifest.pit_snapshot_hash)
        actual = (
            checkpoint.manifest_hash,
            checkpoint.run_id,
            checkpoint.pit_snapshot_hash,
        )
        if actual != expected:
            raise ValueError("runtime checkpoint contradicts immutable run/PIT identity")
        return checkpoint

    def append_process_segment(self, payload: dict[str, object]) -> None:
        existing = self.load_process_segments()
        segment_index = payload.get("segment_index")
        if not isinstance(segment_index, int) or segment_index < 0:
            raise ValueError("process segment index must be non-negative")
        if existing and segment_index <= existing[-1]["segment_index"]:
            raise ValueError("process segment identity must be strictly increasing")
        record = {
            "schema_version": "E4_PROCESS_SEGMENT_V1",
            **payload,
        }
        record["record_hash"] = sha256_hex(canonical_json_bytes(record))
        with self.process_segments_path.open("ab") as stream:
            stream.write(canonical_json_bytes(record) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())

    def load_process_segments(self) -> tuple[dict[str, Any], ...]:
        if not self.process_segments_path.exists():
            return ()
        records: list[dict[str, Any]] = []
        for line in self.process_segments_path.read_bytes().splitlines():
            raw = json.loads(line)
            if raw.get("schema_version") != "E4_PROCESS_SEGMENT_V1":
                raise ValueError("unsupported process segment record")
            record_hash = raw.get("record_hash")
            expected = sha256_hex(
                canonical_json_bytes(
                    {key: value for key, value in raw.items() if key != "record_hash"}
                )
            )
            if not isinstance(record_hash, str) or not hmac.compare_digest(
                record_hash, expected
            ):
                raise ValueError("process segment record hash mismatch")
            if records and raw.get("segment_index", -1) <= records[-1]["segment_index"]:
                raise ValueError("process segment history is not strictly ordered")
            records.append(raw)
        return tuple(records)

    def verify_manifest_hash(self, expected: str) -> None:
        actual = self.load_manifest().manifest_hash
        if not hmac.compare_digest(actual, expected):
            raise ValueError("manifest hash does not match replay authority")
