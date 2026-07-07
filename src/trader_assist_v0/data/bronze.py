from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from trader_assist_v0.contracts.events import (
    MANIFEST_GENESIS_HASH,
    RawEventV0,
    RawManifestEntryV0,
)

_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,159}$")
_PAYLOAD_RE = re.compile(r"^payloads/sha256/[0-9a-f]{2}/[0-9a-f]{64}\.payload$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)


class BronzeIntegrityError(ValueError):
    pass


class PathConfinementError(BronzeIntegrityError):
    pass


class ObservationConflictError(BronzeIntegrityError):
    pass


class SingleWriterError(BronzeIntegrityError):
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


def _validate_relative_path(value: str) -> tuple[str, ...]:
    if not value or "\x00" in value:
        raise PathConfinementError("relative path is empty or contains NUL")
    if value.startswith("/") or "\\" in value or re.match(r"^[A-Za-z]:", value):
        raise PathConfinementError("relative path must use canonical portable POSIX syntax")
    components = tuple(value.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise PathConfinementError("relative path contains a forbidden component")
    if PurePosixPath(*components).as_posix() != value:
        raise PathConfinementError("relative path is not canonical")
    return components


def _reject_symlink_ancestors(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(metadata.st_mode):
            raise PathConfinementError("persistence root contains a symlink component")


def _reject_symlink(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise PathConfinementError("symlink is not an authoritative storage object")


def _fsync_directory_fd(fd: int) -> None:
    os.fsync(fd)


def _open_root_fd(root: Path) -> int:
    return os.open(root, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)


def _open_verified_at(parent_fd: int, name: str, flags: int, *, kind: str) -> int:
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode):
        raise PathConfinementError("symlink is not an authoritative storage object")
    if kind == "directory" and not stat.S_ISDIR(metadata.st_mode):
        raise PathConfinementError("storage path component is not a directory")
    if kind == "regular" and not stat.S_ISREG(metadata.st_mode):
        raise BronzeIntegrityError("storage object is not a regular file")
    descriptor = os.open(name, flags | _NOFOLLOW, dir_fd=parent_fd)
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
        os.close(descriptor)
        raise PathConfinementError("storage object changed during secure open")
    return descriptor


def _open_dir_chain(root_fd: int, parts: tuple[str, ...], *, create: bool) -> int:
    current = os.dup(root_fd)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=current)
                    _fsync_directory_fd(current)
                except FileExistsError:
                    pass
            next_fd = _open_verified_at(
                current, part, os.O_RDONLY | _DIRECTORY, kind="directory"
            )
            os.close(current)
            current = next_fd
        return current
    except BaseException:
        os.close(current)
        raise


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write while persisting payload")
        view = view[written:]


def _read_all(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _verify_regular_fd(fd: int, expected_size: int, expected_hash: str) -> None:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        raise BronzeIntegrityError("authoritative payload is not a regular file")
    if metadata.st_size != expected_size:
        raise BronzeIntegrityError("authoritative payload size mismatch")
    os.lseek(fd, 0, os.SEEK_SET)
    hasher = hashlib.sha256()
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        hasher.update(chunk)
    if hasher.hexdigest() != expected_hash:
        raise BronzeIntegrityError("authoritative payload hash mismatch")


class BronzeStore:
    def __init__(self, root: Path) -> None:
        if _NOFOLLOW == 0 or _DIRECTORY == 0:
            raise RuntimeError("V0-01A0 requires O_NOFOLLOW and O_DIRECTORY support")
        _reject_symlink_ancestors(root)
        root.mkdir(parents=True, exist_ok=True)
        _reject_symlink(root)
        self.root = root.resolve(strict=True)
        descriptor = _open_root_fd(self.root)
        os.close(descriptor)

    def path(self, relative_path: str) -> Path:
        components = _validate_relative_path(relative_path)
        candidate = self.root.joinpath(*components)
        current = self.root
        for component in components:
            current /= component
            _reject_symlink(current)
        try:
            candidate.resolve(strict=False).relative_to(self.root)
        except ValueError as exc:
            raise PathConfinementError("resolved path escapes persistence root") from exc
        return candidate

    def _open_parent(self, relative_path: str, *, create: bool) -> tuple[int, str]:
        parts = _validate_relative_path(relative_path)
        root_fd = _open_root_fd(self.root)
        try:
            parent_fd = _open_dir_chain(root_fd, parts[:-1], create=create)
        finally:
            os.close(root_fd)
        return parent_fd, parts[-1]

    def write_payload(self, payload: bytes) -> PayloadWriteResult:
        digest = payload_sha256(payload)
        relative = payload_relative_path(digest)
        parent_fd, final_name = self._open_parent(relative, create=True)
        temporary_name = f".payload-{secrets.token_hex(16)}.tmp"
        temporary_created = False
        try:
            try:
                existing_fd = _open_verified_at(
                    parent_fd, final_name, os.O_RDONLY, kind="regular"
                )
            except FileNotFoundError:
                existing_fd = -1
            if existing_fd >= 0:
                try:
                    _verify_regular_fd(existing_fd, len(payload), digest)
                finally:
                    os.close(existing_fd)
                return PayloadWriteResult(digest, len(payload), relative, False)

            temp_fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                0o600,
                dir_fd=parent_fd,
            )
            temporary_created = True
            try:
                _write_all(temp_fd, payload)
                os.fsync(temp_fd)
            finally:
                os.close(temp_fd)

            try:
                os.link(
                    temporary_name,
                    final_name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                created = True
            except FileExistsError:
                created = False
            os.unlink(temporary_name, dir_fd=parent_fd)
            temporary_created = False
            _fsync_directory_fd(parent_fd)

            final_fd = _open_verified_at(parent_fd, final_name, os.O_RDONLY, kind="regular")
            try:
                _verify_regular_fd(final_fd, len(payload), digest)
            finally:
                os.close(final_fd)
            return PayloadWriteResult(digest, len(payload), relative, created)
        finally:
            if temporary_created:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)

    def verify_payload(self, event: RawEventV0) -> None:
        if type(event) is not RawEventV0:
            raise BronzeIntegrityError("payload verification requires exact RawEventV0")
        expected_ref = payload_relative_path(event.payload_sha256)
        if event.payload_ref != expected_ref:
            raise BronzeIntegrityError("payload reference is not content-addressed")
        parent_fd, filename = self._open_parent(event.payload_ref, create=False)
        try:
            try:
                payload_fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
            except FileNotFoundError as exc:
                raise BronzeIntegrityError("manifest references a missing payload") from exc
            try:
                _verify_regular_fd(payload_fd, event.payload_size_bytes, event.payload_sha256)
            finally:
                os.close(payload_fd)
        finally:
            os.close(parent_fd)

    def manifest_ref(self, manifest_date: date, segment_id: str) -> str:
        if _SEGMENT_RE.fullmatch(segment_id) is None:
            raise ValueError("invalid manifest segment ID")
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.jsonl"

    def lock_ref(self, manifest_date: date, segment_id: str) -> str:
        if _SEGMENT_RE.fullmatch(segment_id) is None:
            raise ValueError("invalid manifest segment ID")
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.lock"

    def read_bytes(self, relative_path: str) -> bytes:
        parent_fd, filename = self._open_parent(relative_path, create=False)
        try:
            fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
            try:
                return _read_all(fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)

    def read_manifest_bytes(self, manifest_date: date, segment_id: str) -> bytes:
        return self.read_bytes(self.manifest_ref(manifest_date, segment_id))

    def payload_refs(self) -> set[str]:
        payload_root = self.root / "payloads" / "sha256"
        if not payload_root.exists():
            return set()
        _reject_symlink(payload_root)
        refs: set[str] = set()
        for prefix in os.scandir(payload_root):
            if prefix.is_symlink() or not prefix.is_dir(follow_symlinks=False):
                raise BronzeIntegrityError("unexpected payload-tree entry")
            if re.fullmatch(r"[0-9a-f]{2}", prefix.name) is None:
                raise BronzeIntegrityError("unexpected payload prefix directory")
            for item in os.scandir(prefix.path):
                if item.is_symlink() or not item.is_file(follow_symlinks=False):
                    raise BronzeIntegrityError("unexpected payload object")
                relative = f"payloads/sha256/{prefix.name}/{item.name}"
                if _PAYLOAD_RE.fullmatch(relative) is None:
                    raise BronzeIntegrityError("unexpected payload path")
                digest = item.name.removesuffix(".payload")
                if digest[:2] != prefix.name:
                    raise BronzeIntegrityError("payload path prefix does not match digest")
                refs.add(relative)
        return refs

    def manifest_files(self) -> tuple[tuple[date, str], ...]:
        manifests_root = self.root / "manifests"
        if not manifests_root.exists():
            return ()
        _reject_symlink(manifests_root)
        found: list[tuple[date, str]] = []
        for day_entry in os.scandir(manifests_root):
            if day_entry.is_symlink() or not day_entry.is_dir(follow_symlinks=False):
                raise BronzeIntegrityError("unexpected manifest-tree entry")
            if _DATE_RE.fullmatch(day_entry.name) is None:
                raise BronzeIntegrityError("unexpected manifest date directory")
            day = date.fromisoformat(day_entry.name)
            for item in os.scandir(day_entry.path):
                if item.is_symlink() or not item.is_file(follow_symlinks=False):
                    raise BronzeIntegrityError("unexpected manifest object")
                if item.name.endswith(".lock"):
                    raise SingleWriterError("manifest tree contains an active or stale writer lock")
                if not item.name.endswith(".jsonl"):
                    raise BronzeIntegrityError("unexpected manifest file")
                segment_id = item.name.removesuffix(".jsonl")
                if _SEGMENT_RE.fullmatch(segment_id) is None:
                    raise BronzeIntegrityError("invalid manifest segment filename")
                found.append((day, segment_id))
        return tuple(sorted(found, key=lambda value: (value[0], value[1])))


def parse_manifest_bytes(
    raw: bytes,
    *,
    expected_segment_id: str | None = None,
) -> tuple[RawManifestEntryV0, ...]:
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
        target_segment = expected_segment_id or (
            entries[0].segment_id if entries else entry.segment_id
        )
        if entry.segment_id != target_segment:
            raise BronzeIntegrityError("manifest contains an unexpected segment ID")
        entries.append(entry)
    return tuple(entries)


def read_manifest_entries(
    store: BronzeStore,
    manifest_date: date,
    segment_id: str,
) -> tuple[RawManifestEntryV0, ...]:
    return parse_manifest_bytes(
        store.read_manifest_bytes(manifest_date, segment_id),
        expected_segment_id=segment_id,
    )


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
        self._closed = False
        self._manifest_ref = store.manifest_ref(manifest_date, segment_id)
        self._lock_ref = store.lock_ref(manifest_date, segment_id)
        self._lock_parent_fd, self._lock_name = store._open_parent(self._lock_ref, create=True)
        try:
            lock_fd = os.open(
                self._lock_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                0o600,
                dir_fd=self._lock_parent_fd,
            )
        except FileExistsError as exc:
            os.close(self._lock_parent_fd)
            raise SingleWriterError(
                "manifest segment already has an active or stale writer lock"
            ) from exc
        try:
            os.fsync(lock_fd)
        finally:
            os.close(lock_fd)
        _fsync_directory_fd(self._lock_parent_fd)

        try:
            try:
                self.entries = list(read_manifest_entries(store, manifest_date, segment_id))
            except FileNotFoundError:
                self.entries = []
            self._by_slot: dict[str, RawManifestEntryV0] = {}
            for entry in self.entries:
                slot = entry.raw_event.observation_slot_id
                if slot in self._by_slot:
                    raise BronzeIntegrityError(
                        "manifest repeats an authoritative observation slot"
                    )
                self._by_slot[slot] = entry
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> ManifestWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        if self._closed:
            return
        try:
            os.unlink(self._lock_name, dir_fd=self._lock_parent_fd)
            _fsync_directory_fd(self._lock_parent_fd)
        finally:
            os.close(self._lock_parent_fd)
            self._closed = True

    def append(self, event: RawEventV0) -> ManifestAppendResult:
        if self._closed:
            raise SingleWriterError("manifest writer is closed")
        exact_event = RawEventV0.model_validate(event)
        self.store.verify_payload(exact_event)
        existing = self._by_slot.get(exact_event.observation_slot_id)
        if existing is not None:
            if existing.raw_event == exact_event:
                return ManifestAppendResult(AppendDisposition.IDEMPOTENT, existing)
            raise ObservationConflictError("observation slot has conflicting raw payload identity")

        previous_hash = self.entries[-1].entry_hash if self.entries else MANIFEST_GENESIS_HASH
        entry = RawManifestEntryV0.bind(
            schema_version=self.schema_version,
            segment_id=self.segment_id,
            entry_index=len(self.entries),
            previous_entry_hash=previous_hash,
            raw_event=exact_event,
        )
        line = entry.model_dump_json().encode("utf-8") + b"\n"
        parent_fd, filename = self.store._open_parent(self._manifest_ref, create=True)
        try:
            try:
                fd = os.open(
                    filename,
                    os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                    0o600,
                    dir_fd=parent_fd,
                )
            except FileExistsError:
                fd = _open_verified_at(
                    parent_fd, filename, os.O_WRONLY | os.O_APPEND, kind="regular"
                )
            try:
                written = os.write(fd, line)
                if written != len(line):
                    os.fsync(fd)
                    raise OSError("short manifest append")
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_directory_fd(parent_fd)
        finally:
            os.close(parent_fd)
        self.entries.append(entry)
        self._by_slot[exact_event.observation_slot_id] = entry
        return ManifestAppendResult(AppendDisposition.APPENDED, entry)
