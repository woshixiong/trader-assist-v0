from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import IO

from pydantic import ValidationError

from trader_assist_v0.contracts.events import (
    MANIFEST_GENESIS_HASH,
    RawEventV0,
    RawManifestEntryV0,
)

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$")
_PAYLOAD_RE = re.compile(r"^payloads/sha256/[0-9a-f]{2}/[0-9a-f]{64}\.payload$")


class BronzeIntegrityError(ValueError):
    pass


class PathConfinementError(BronzeIntegrityError):
    pass


class ObservationConflictError(BronzeIntegrityError):
    pass


class AppendDisposition(StrEnum):
    APPENDED = "APPENDED"
    IDEMPOTENT = "IDEMPOTENT"


@dataclass(frozen=True)
class PayloadWriteResult:
    payload_sha256: str
    payload_size_bytes: int
    payload_ref: str
    created: bool


@dataclass(frozen=True)
class ManifestAppendResult:
    disposition: AppendDisposition
    entry: RawManifestEntryV0


def payload_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def payload_relative_path(digest: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("payload digest must be lowercase SHA-256 hex")
    return f"payloads/sha256/{digest[:2]}/{digest}.payload"


def _validate_relative_path(value: str) -> PurePosixPath:
    if "\x00" in value:
        raise PathConfinementError("relative path contains NUL")
    if "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise PathConfinementError("relative path must use portable POSIX syntax")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/") or ".." in path.parts:
        raise PathConfinementError("relative path escapes persistence root")
    if any(part in {"", "."} for part in path.parts):
        raise PathConfinementError("relative path contains invalid components")
    return path


def confined_path(root: Path, relative_path: str) -> Path:
    relative = _validate_relative_path(relative_path)
    root.mkdir(parents=True, exist_ok=True)
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root.joinpath(*relative.parts)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise PathConfinementError("resolved path escapes persistence root") from exc
    return candidate


def _reject_symlink(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise PathConfinementError("symlink is not an authoritative storage object")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_file(path: Path, expected_size: int, expected_hash: str) -> None:
    _reject_symlink(path)
    if not path.is_file():
        raise BronzeIntegrityError("authoritative payload is not a regular file")
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise BronzeIntegrityError("authoritative payload size mismatch")
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != expected_hash:
        raise BronzeIntegrityError("authoritative payload hash mismatch")


def _write_and_sync(handle: IO[bytes], payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = handle.write(view)
        if written is None or written <= 0:
            raise OSError("short write while persisting payload")
        view = view[written:]
    handle.flush()
    os.fsync(handle.fileno())


class BronzeStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        _reject_symlink(self.root)
        self.root = self.root.resolve(strict=True)

    def path(self, relative_path: str) -> Path:
        return confined_path(self.root, relative_path)

    def write_payload(self, payload: bytes) -> PayloadWriteResult:
        digest = payload_sha256(payload)
        relative = payload_relative_path(digest)
        final_path = self.path(relative)
        parent = final_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        confined_path(self.root, str(PurePosixPath(relative).parent))
        _reject_symlink(parent)

        if final_path.exists() or final_path.is_symlink():
            _verify_file(final_path, len(payload), digest)
            return PayloadWriteResult(digest, len(payload), relative, False)

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=".payload-",
                suffix=".tmp",
                dir=parent,
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                _write_and_sync(temporary.file, payload)
            temporary_path = Path(temporary_name)
            _reject_symlink(temporary_path)
            os.replace(temporary_path, final_path)
            temporary_name = None
            _fsync_directory(parent)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

        _verify_file(final_path, len(payload), digest)
        return PayloadWriteResult(digest, len(payload), relative, True)

    def verify_payload(self, event: RawEventV0) -> None:
        expected_ref = payload_relative_path(event.payload_sha256)
        if event.payload_ref != expected_ref:
            raise BronzeIntegrityError("payload reference is not content-addressed")
        path = self.path(event.payload_ref)
        if not path.exists():
            raise BronzeIntegrityError("manifest references a missing payload")
        _verify_file(path, event.payload_size_bytes, event.payload_sha256)

    def manifest_ref(self, manifest_date: date, segment_id: str) -> str:
        if _SEGMENT_RE.fullmatch(segment_id) is None:
            raise ValueError("invalid manifest segment ID")
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.jsonl"

    def manifest_path(self, manifest_date: date, segment_id: str) -> Path:
        return self.path(self.manifest_ref(manifest_date, segment_id))

    def payload_refs(self) -> set[str]:
        payload_root = self.path("payloads/sha256")
        if not payload_root.exists():
            return set()
        refs: set[str] = set()
        for path in payload_root.rglob("*.payload"):
            _reject_symlink(path)
            resolved = path.resolve(strict=True)
            try:
                relative = resolved.relative_to(self.root).as_posix()
            except ValueError as exc:
                raise PathConfinementError("payload scan escaped persistence root") from exc
            if _PAYLOAD_RE.fullmatch(relative) is None:
                raise BronzeIntegrityError("unexpected payload path")
            refs.add(relative)
        return refs


def read_manifest_entries(path: Path) -> tuple[RawManifestEntryV0, ...]:
    _reject_symlink(path)
    if not path.exists():
        return ()
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise BronzeIntegrityError("manifest has a truncated final line")
    entries: list[RawManifestEntryV0] = []
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        if not raw_line:
            raise BronzeIntegrityError(f"manifest contains an empty line at {line_number}")
        try:
            entry = RawManifestEntryV0.model_validate_json(raw_line)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            raise BronzeIntegrityError(f"invalid manifest line {line_number}") from exc
        expected_index = len(entries)
        expected_previous = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
        if entry.entry_index != expected_index:
            raise BronzeIntegrityError("manifest entry index is not contiguous")
        if entry.previous_entry_hash != expected_previous:
            raise BronzeIntegrityError("manifest previous hash does not match chain")
        if entries and entry.segment_id != entries[0].segment_id:
            raise BronzeIntegrityError("manifest contains multiple segment IDs")
        entries.append(entry)
    return tuple(entries)


class ManifestWriter:
    def __init__(
        self,
        store: BronzeStore,
        *,
        manifest_date: date,
        segment_id: str,
        schema_version: str = "0.1.0",
    ) -> None:
        self.store = store
        self.manifest_date = manifest_date
        self.segment_id = segment_id
        self.schema_version = schema_version
        self.path = store.manifest_path(manifest_date, segment_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        confined_path(store.root, store.manifest_ref(manifest_date, segment_id))
        _reject_symlink(self.path.parent)
        self.entries = list(read_manifest_entries(self.path))
        self._by_slot: dict[str, RawManifestEntryV0] = {}
        for entry in self.entries:
            if entry.raw_event.observation_slot_id in self._by_slot:
                raise BronzeIntegrityError("manifest repeats an authoritative observation slot")
            self._by_slot[entry.raw_event.observation_slot_id] = entry

    def append(self, event: RawEventV0) -> ManifestAppendResult:
        self.store.verify_payload(event)
        existing = self._by_slot.get(event.observation_slot_id)
        if existing is not None:
            if existing.raw_event == event:
                return ManifestAppendResult(AppendDisposition.IDEMPOTENT, existing)
            raise ObservationConflictError("observation slot has conflicting raw payload identity")

        previous_hash = self.entries[-1].entry_hash if self.entries else MANIFEST_GENESIS_HASH
        entry = RawManifestEntryV0.bind(
            schema_version=self.schema_version,
            segment_id=self.segment_id,
            entry_index=len(self.entries),
            previous_entry_hash=previous_hash,
            raw_event=event,
        )
        line = entry.model_dump_json().encode("utf-8") + b"\n"
        with self.path.open("ab", buffering=0) as handle:
            written = handle.write(line)
            if written != len(line):
                raise OSError("short manifest append")
            os.fsync(handle.fileno())
        _fsync_directory(self.path.parent)
        self.entries.append(entry)
        self._by_slot[event.observation_slot_id] = entry
        return ManifestAppendResult(AppendDisposition.APPENDED, entry)
