from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import threading
import secrets
import stat
import time
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from trader_assist_v0.contracts.events import (
    MANIFEST_GENESIS_HASH,
    RawEventV0,
    RawManifestCheckpointV0,
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


class LockOwnershipError(SingleWriterError):
    pass


class SegmentFinalizedError(BronzeIntegrityError):
    pass


class AppendDisposition(StrEnum):
    APPENDED = "APPENDED"
    IDEMPOTENT = "IDEMPOTENT"


class _LockState(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    COMPROMISED = "COMPROMISED"
    FORK_INVALID = "FORK_INVALID"


class _FdState(StrEnum):
    OPEN_OWNED = "OPEN_OWNED"
    UNLOCKING = "UNLOCKING"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    CLOSE_OUTCOME_UNKNOWN = "CLOSE_OUTCOME_UNKNOWN"
    POISONED = "POISONED"
    FORK_INVALID = "FORK_INVALID"


class _WriterState(StrEnum):
    ACTIVE = "ACTIVE"
    FINALIZING = "FINALIZING"
    FINALIZED = "FINALIZED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    COMPROMISED = "COMPROMISED"
    FORK_INVALID = "FORK_INVALID"


# Process-global poison gate: 0 = clean, 1 = poisoned
_BRONZE_POISON_GATE = 0


# Module-level tracking for fork safety
_owned_locks: list = []


def _after_fork_child() -> None:
    """Mark all owned locks as FORK_INVALID in the child process."""
    global _BRONZE_POISON_GATE
    for lock in _owned_locks:
        lock._fd_state = _FdState.FORK_INVALID
        lock._state = _LockState.FORK_INVALID
    _owned_locks.clear()


os.register_at_fork(after_in_child=_after_fork_child)


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

    def _open_parent(
        self,
        relative_path: str,
        *,
        create: bool,
        authority_fd: int | None = None,
    ) -> tuple[int, str]:
        parts = _validate_relative_path(relative_path)
        if authority_fd is not None:
            parent_fd = _open_dir_chain(authority_fd, parts[:-1], create=create)
            return parent_fd, parts[-1]
        root_fd = _open_root_fd(self.root)
        try:
            parent_fd = _open_dir_chain(root_fd, parts[:-1], create=create)
        finally:
            os.close(root_fd)
        return parent_fd, parts[-1]

    def exists_regular(self, relative_path: str, *, authority_fd: int | None = None) -> bool:
        try:
            parent_fd, name = self._open_parent(
                relative_path,
                create=False,
                authority_fd=authority_fd,
            )
        except FileNotFoundError:
            return False
        try:
            try:
                fd = _open_verified_at(parent_fd, name, os.O_RDONLY, kind="regular")
            except FileNotFoundError:
                return False
            else:
                os.close(fd)
                return True
        finally:
            os.close(parent_fd)

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

    def verify_payload(self, event: RawEventV0, *, authority_fd: int | None = None) -> None:
        exact_event = RawEventV0.model_validate(event)
        expected_ref = payload_relative_path(exact_event.payload_sha256)
        if exact_event.payload_ref != expected_ref:
            raise BronzeIntegrityError("payload reference is not content-addressed")
        parent_fd, filename = self._open_parent(
            exact_event.payload_ref,
            create=False,
            authority_fd=authority_fd,
        )
        try:
            try:
                payload_fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
            except FileNotFoundError as exc:
                raise BronzeIntegrityError("manifest references a missing payload") from exc
            try:
                _verify_regular_fd(
                    payload_fd,
                    exact_event.payload_size_bytes,
                    exact_event.payload_sha256,
                )
            finally:
                os.close(payload_fd)
        finally:
            os.close(parent_fd)

    def manifest_ref(self, manifest_date: date, segment_id: str) -> str:
        _validate_segment(segment_id)
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.jsonl"

    def checkpoint_ref(self, manifest_date: date, segment_id: str) -> str:
        _validate_segment(segment_id)
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.checkpoint.json"

    def lock_ref(self, manifest_date: date, segment_id: str) -> str:
        _validate_segment(segment_id)
        return f"manifests/{manifest_date.isoformat()}/{segment_id}.lock"

    def global_authority_lock_ref(self) -> str:
        return ".bronze-global-observation-authority.lock"

    def read_bytes(self, relative_path: str, *, authority_fd: int | None = None) -> bytes:
        parent_fd, filename = self._open_parent(
            relative_path,
            create=False,
            authority_fd=authority_fd,
        )
        try:
            fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
            try:
                return _read_all(fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)

    def read_manifest_bytes(
        self,
        manifest_date: date,
        segment_id: str,
        *,
        authority_fd: int | None = None,
    ) -> bytes:
        return self.read_bytes(
            self.manifest_ref(manifest_date, segment_id),
            authority_fd=authority_fd,
        )

    def read_checkpoint_bytes(
        self,
        manifest_date: date,
        segment_id: str,
        *,
        authority_fd: int | None = None,
    ) -> bytes:
        return self.read_bytes(
            self.checkpoint_ref(manifest_date, segment_id),
            authority_fd=authority_fd,
        )

    def fsync_file(self, relative_path: str, *, authority_fd: int | None = None) -> None:
        parent_fd, filename = self._open_parent(
            relative_path,
            create=False,
            authority_fd=authority_fd,
        )
        try:
            fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_directory_fd(parent_fd)
        finally:
            os.close(parent_fd)

    def ensure_empty_file(
        self,
        relative_path: str,
        *,
        authority_fd: int | None = None,
    ) -> None:
        parent_fd, filename = self._open_parent(
            relative_path,
            create=True,
            authority_fd=authority_fd,
        )
        try:
            try:
                fd = os.open(
                    filename,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                    0o600,
                    dir_fd=parent_fd,
                )
            except FileExistsError:
                existing = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
                os.close(existing)
                return
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_directory_fd(parent_fd)
        finally:
            os.close(parent_fd)

    def publish_checkpoint(
        self,
        manifest_date: date,
        segment_id: str,
        checkpoint: RawManifestCheckpointV0,
        *,
        authority_fd: int | None = None,
    ) -> None:
        exact = RawManifestCheckpointV0.model_validate(checkpoint)
        relative = self.checkpoint_ref(manifest_date, segment_id)
        payload = exact.model_dump_json().encode("utf-8") + b"\n"
        parent_fd, final_name = self._open_parent(
            relative,
            create=True,
            authority_fd=authority_fd,
        )
        temporary_name = f".checkpoint-{secrets.token_hex(16)}.tmp"
        temp_created = False
        try:
            try:
                existing = _open_verified_at(parent_fd, final_name, os.O_RDONLY, kind="regular")
            except FileNotFoundError:
                pass
            else:
                os.close(existing)
                raise SegmentFinalizedError("checkpoint already exists and cannot be overwritten")
            temp_fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
                0o600,
                dir_fd=parent_fd,
            )
            temp_created = True
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
            except FileExistsError as exc:
                raise SegmentFinalizedError(
                    "checkpoint was concurrently published and cannot be overwritten"
                ) from exc
            os.unlink(temporary_name, dir_fd=parent_fd)
            temp_created = False
            _fsync_directory_fd(parent_fd)
        finally:
            if temp_created:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)

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

    def manifest_files(
        self,
        *,
        authority_fd: int | None = None,
    ) -> tuple[tuple[date, str], ...]:
        owned_root_fd = authority_fd is None
        root_fd = _open_root_fd(self.root) if owned_root_fd else authority_fd
        assert root_fd is not None
        try:
            try:
                manifests_fd = _open_dir_chain(root_fd, ("manifests",), create=False)
            except FileNotFoundError:
                return ()
            try:
                found: list[tuple[date, str]] = []
                with os.scandir(manifests_fd) as day_entries:
                    for day_entry in day_entries:
                        if day_entry.is_symlink() or not day_entry.is_dir(
                            follow_symlinks=False
                        ):
                            raise BronzeIntegrityError("unexpected manifest-tree entry")
                        if _DATE_RE.fullmatch(day_entry.name) is None:
                            raise BronzeIntegrityError("unexpected manifest date directory")
                        day = date.fromisoformat(day_entry.name)
                        day_fd = _open_verified_at(
                            manifests_fd,
                            day_entry.name,
                            os.O_RDONLY | _DIRECTORY,
                            kind="directory",
                        )
                        try:
                            with os.scandir(day_fd) as items:
                                for item in items:
                                    if item.is_symlink() or not item.is_file(
                                        follow_symlinks=False
                                    ):
                                        raise BronzeIntegrityError(
                                            "unexpected manifest object"
                                        )
                                    if item.name.endswith(".lock") or item.name.endswith(
                                        ".checkpoint.json"
                                    ):
                                        continue
                                    if not item.name.endswith(".jsonl"):
                                        raise BronzeIntegrityError(
                                            "unexpected manifest file"
                                        )
                                    segment_id = item.name.removesuffix(".jsonl")
                                    _validate_segment(segment_id)
                                    found.append((day, segment_id))
                        finally:
                            os.close(day_fd)
                return tuple(sorted(found, key=lambda value: (value[0], value[1])))
            finally:
                os.close(manifests_fd)
        finally:
            if owned_root_fd:
                os.close(root_fd)


def _validate_segment(segment_id: str) -> None:
    if _SEGMENT_RE.fullmatch(segment_id) is None:
        raise ValueError("invalid manifest segment ID")


class OwnedLock:
    """Root-wide kernel-backed authority held on the Bronze root directory inode.

    ``relative_path`` is retained only for API compatibility and diagnostics. No lock
    pathname is created, verified, unlinked, cleaned, or used as an exclusivity
    namespace. The open root directory descriptor is the authority for the complete
    lock lifetime.
    """

    def __init__(
        self,
        *,
        store: BronzeStore,
        relative_path: str,
        fd: int,
        st_dev: int,
        st_ino: int,
        _parent_fd: int = -1,
    ) -> None:
        self.store = store
        self.relative_path = relative_path
        self._fd = fd
        self._parent_fd = _parent_fd
        self._st_dev = st_dev
        self._st_ino = st_ino
        self._owner_pid = os.getpid()
        self._state = _LockState.ACTIVE
        self._fd_state = _FdState.OPEN_OWNED
        _owned_locks.append(self)

    @classmethod
    def acquire(
        cls,
        store: BronzeStore,
        relative_path: str,
        *,
        wait_timeout: float = 0.0,
    ) -> OwnedLock:
        _validate_relative_path(relative_path)
        # Lock the parent directory of the Bronze root to ensure
        # authority survives root rename/replacement
        parent_dir = str(store.root.parent)
        parent_fd = os.open(parent_dir, os.O_RDONLY | _DIRECTORY | _NOFOLLOW)
        locked = False
        deadline = time.monotonic() + wait_timeout
        try:
            while True:
                try:
                    fcntl.flock(parent_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise SingleWriterError(
                            "Bronze root already has an active manifest writer"
                        ) from exc
                    time.sleep(0.005)
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                        raise
                    if time.monotonic() >= deadline:
                        raise SingleWriterError(
                            "Bronze root already has an active manifest writer"
                        ) from exc
                    time.sleep(0.005)
            # Open root through the locked parent directory
            root_fd = os.open(
                store.root.name,
                os.O_RDONLY | _DIRECTORY | _NOFOLLOW,
                dir_fd=parent_fd,
            )
            try:
                opened = os.fstat(root_fd)
                if not stat.S_ISDIR(opened.st_mode):
                    raise LockOwnershipError("root authority descriptor is not a directory")
                # Verify root identity through parent_fd
                root_meta = os.stat(
                    store.root.name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                if not stat.S_ISDIR(root_meta.st_mode):
                    raise LockOwnershipError("Bronze root path is not a directory")
                if (root_meta.st_dev, root_meta.st_ino) != (
                    opened.st_dev,
                    opened.st_ino,
                ):
                    raise LockOwnershipError(
                        "Bronze root changed while acquiring root-wide authority"
                    )
                return cls(
                    store=store,
                    relative_path=relative_path,
                    fd=root_fd,
                    st_dev=opened.st_dev,
                    st_ino=opened.st_ino,
                    _parent_fd=parent_fd,
                )
            except BaseException:
                os.close(root_fd)
                raise
        except BaseException:
            if locked:
                try:
                    fcntl.flock(parent_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(parent_fd)
            raise

    @property
    def released(self) -> bool:
        return self._state is not _LockState.ACTIVE

    @property
    def fork_invalid(self) -> bool:
        return self._state is _LockState.FORK_INVALID

    @property
    def compromised(self) -> bool:
        return self._state is _LockState.COMPROMISED

    @property
    def authority_fd(self) -> int:
        if self._state is _LockState.FORK_INVALID:
            raise LockOwnershipError("root authority is invalid after fork")
        if self._state is not _LockState.ACTIVE:
            raise LockOwnershipError("root authority is no longer active")
        if os.getpid() != self._owner_pid:
            self._state = _LockState.FORK_INVALID
            self._fd_state = _FdState.FORK_INVALID
            raise LockOwnershipError("root authority belongs to a different process")
        return self._fd

    def _close_owned_descriptor(self, *, state: _LockState) -> None:
        global _BRONZE_POISON_GATE
        if self._state is _LockState.FORK_INVALID:
            self._fd_state = _FdState.FORK_INVALID
            self._state = state
            return
        root_fd = self._fd
        parent_fd = self._parent_fd
        if root_fd < 0:
            self._fd_state = _FdState.CLOSED
            self._state = state
            return
        self._fd_state = _FdState.UNLOCKING
        # Unlock the parent directory (the lock is on parent_fd)
        if parent_fd >= 0:
            try:
                fcntl.flock(parent_fd, fcntl.LOCK_UN)
            except OSError:
                self._fd_state = _FdState.CLOSE_OUTCOME_UNKNOWN
                _BRONZE_POISON_GATE = 1
                self._fd = -1
                self._parent_fd = -1
                self._state = state
                raise
        self._fd_state = _FdState.CLOSING
        # Close root_fd
        try:
            os.close(root_fd)
        except OSError:
            pass
        # Close parent_fd
        if parent_fd >= 0:
            try:
                os.close(parent_fd)
            except OSError:
                self._fd_state = _FdState.POISONED
                _BRONZE_POISON_GATE = 1
                self._fd = -1
                self._parent_fd = -1
                self._state = state
                return
        self._fd = -1
        self._parent_fd = -1
        self._fd_state = _FdState.CLOSED
        self._state = state

    def _verify_owned(self) -> None:
        if self._state is _LockState.FORK_INVALID:
            raise LockOwnershipError("root authority is invalid after fork")
        if os.getpid() != self._owner_pid:
            self._state = _LockState.FORK_INVALID
            self._fd_state = _FdState.FORK_INVALID
            raise LockOwnershipError("root authority belongs to a different process")
        if self._state is _LockState.RELEASED:
            raise LockOwnershipError("root authority is already released")
        if self._state is _LockState.COMPROMISED:
            raise LockOwnershipError("root authority is compromised")
        try:
            # Verify root_fd is still a valid directory
            opened = os.fstat(self._fd)
            if not stat.S_ISDIR(opened.st_mode):
                raise LockOwnershipError("root authority descriptor is not a directory")
            if (opened.st_dev, opened.st_ino) != (self._st_dev, self._st_ino):
                raise LockOwnershipError("root authority descriptor identity changed")
            # Verify root identity through parent_fd if available
            if self._parent_fd >= 0:
                try:
                    root_meta = os.stat(
                        self.store.root.name,
                        dir_fd=self._parent_fd,
                        follow_symlinks=False,
                    )
                    if not stat.S_ISDIR(root_meta.st_mode):
                        raise LockOwnershipError("Bronze root path is not a directory")
                    if (root_meta.st_dev, root_meta.st_ino) != (
                        self._st_dev,
                        self._st_ino,
                    ):
                        raise LockOwnershipError(
                            "Bronze root path no longer names the locked root inode"
                        )
                except FileNotFoundError:
                    raise LockOwnershipError(
                        "Bronze root no longer exists under parent directory"
                    )
            else:
                # Fallback to path-based check (backward compatibility)
                path_metadata = os.stat(self.store.root, follow_symlinks=False)
                if not stat.S_ISDIR(path_metadata.st_mode):
                    raise LockOwnershipError("Bronze root path is not a directory")
                if (path_metadata.st_dev, path_metadata.st_ino) != (
                    self._st_dev,
                    self._st_ino,
                ):
                    raise LockOwnershipError(
                        "Bronze root path no longer names the locked root inode"
                    )
        except BaseException as exc:
            try:
                self._close_owned_descriptor(state=_LockState.COMPROMISED)
            except OSError as close_error:
                raise LockOwnershipError(
                    "root authority verification and descriptor cleanup failed"
                ) from close_error
            if isinstance(exc, LockOwnershipError):
                raise
            raise LockOwnershipError("root authority verification failed") from exc

    def assert_owned(self) -> None:
        self._verify_owned()

    def release(self) -> None:
        if self._state is _LockState.FORK_INVALID:
            raise LockOwnershipError("root authority is invalid after fork")
        self._verify_owned()
        try:
            self._close_owned_descriptor(state=_LockState.RELEASED)
        except OSError as exc:
            self._state = _LockState.COMPROMISED
            raise LockOwnershipError("root authority release failed") from exc


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


def parse_checkpoint_bytes(
    raw: bytes,
    *,
    manifest_date: date,
    segment_id: str,
) -> RawManifestCheckpointV0:
    if not raw or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise BronzeIntegrityError(
            "checkpoint must be one complete newline-terminated JSON object"
        )
    try:
        checkpoint = RawManifestCheckpointV0.model_validate_json(raw[:-1])
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise BronzeIntegrityError("invalid manifest checkpoint") from exc
    if checkpoint.manifest_date != manifest_date or checkpoint.segment_id != segment_id:
        raise BronzeIntegrityError("checkpoint does not match manifest path authority")
    return checkpoint


def read_manifest_entries(
    store: BronzeStore,
    manifest_date: date,
    segment_id: str,
    *,
    authority_fd: int | None = None,
) -> tuple[RawManifestEntryV0, ...]:
    return parse_manifest_bytes(
        store.read_manifest_bytes(
            manifest_date,
            segment_id,
            authority_fd=authority_fd,
        ),
        expected_segment_id=segment_id,
    )


def read_manifest_checkpoint(
    store: BronzeStore,
    manifest_date: date,
    segment_id: str,
    *,
    authority_fd: int | None = None,
) -> RawManifestCheckpointV0:
    return parse_checkpoint_bytes(
        store.read_checkpoint_bytes(
            manifest_date,
            segment_id,
            authority_fd=authority_fd,
        ),
        manifest_date=manifest_date,
        segment_id=segment_id,
    )


def verify_checkpoint_against_entries(
    checkpoint: RawManifestCheckpointV0,
    entries: tuple[RawManifestEntryV0, ...],
) -> None:
    terminal = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
    if checkpoint.expected_entry_count != len(entries):
        raise BronzeIntegrityError("checkpoint entry count does not match manifest")
    if checkpoint.terminal_entry_hash != terminal:
        raise BronzeIntegrityError("checkpoint terminal hash does not match manifest")


def scan_global_observation_authority(
    store: BronzeStore,
    *,
    authority_fd: int | None = None,
) -> tuple[
    dict[str, RawManifestEntryV0],
    dict[str, RawManifestEntryV0],
]:
    by_slot: dict[str, RawManifestEntryV0] = {}
    by_event_id: dict[str, RawManifestEntryV0] = {}
    for manifest_date, segment_id in store.manifest_files(authority_fd=authority_fd):
        entries = read_manifest_entries(
            store,
            manifest_date,
            segment_id,
            authority_fd=authority_fd,
        )
        try:
            checkpoint = read_manifest_checkpoint(
                store,
                manifest_date,
                segment_id,
                authority_fd=authority_fd,
            )
        except FileNotFoundError:
            checkpoint = None
        if checkpoint is not None:
            verify_checkpoint_against_entries(checkpoint, entries)
        for entry in entries:
            event = entry.raw_event
            existing_slot = by_slot.get(event.observation_slot_id)
            if existing_slot is not None:
                raise BronzeIntegrityError("global observation slot authority is duplicated")
            existing_event = by_event_id.get(event.source_event_id)
            if existing_event is not None:
                raise BronzeIntegrityError("global source_event_id authority is duplicated")
            by_slot[event.observation_slot_id] = entry
            by_event_id[event.source_event_id] = entry
    return by_slot, by_event_id


class ManifestWriter:
    def __init__(
        self,
        store: BronzeStore,
        *,
        manifest_date: date,
        segment_id: str,
    ) -> None:
        self._lock = threading.RLock()
        self._writer_state = _WriterState.ACTIVE
        self.store = store
        self.manifest_date = manifest_date
        self.segment_id = segment_id
        self._closed = False
        self._finalized = False
        self._terminal_error: LockOwnershipError | None = None
        self._manifest_ref = store.manifest_ref(manifest_date, segment_id)
        self._checkpoint_ref = store.checkpoint_ref(manifest_date, segment_id)
        self._authority_lock = OwnedLock.acquire(
            store,
            store.global_authority_lock_ref(),
        )
        try:
            authority_fd = self._authority_lock.authority_fd
            if store.exists_regular(self._checkpoint_ref, authority_fd=authority_fd):
                raise SegmentFinalizedError("manifest segment is permanently finalized")
            store.ensure_empty_file(self._manifest_ref, authority_fd=authority_fd)
            self.entries = list(
                read_manifest_entries(
                    store,
                    manifest_date,
                    segment_id,
                    authority_fd=authority_fd,
                )
            )
            self._by_slot: dict[str, RawManifestEntryV0] = {}
            for entry in self.entries:
                slot = entry.raw_event.observation_slot_id
                if slot in self._by_slot:
                    raise BronzeIntegrityError(
                        "manifest repeats an authoritative observation slot"
                    )
                self._by_slot[slot] = entry
        except BaseException as initialization_error:
            try:
                self._authority_lock.release()
            except SingleWriterError as ownership_error:
                self._closed = True
                self._terminal_error = LockOwnershipError(str(ownership_error))
                raise ownership_error from initialization_error
            self._closed = True
            raise

    def __enter__(self) -> ManifestWriter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        with self._lock:
            if self._writer_state is _WriterState.ACTIVE:
                self.close()

    @property
    def finalized(self) -> bool:
        return self._finalized

    def _assert_active(self) -> int:
        if _BRONZE_POISON_GATE:
            raise LockOwnershipError("process bronze state is poisoned and cannot create new writers")
        if self._writer_state is _WriterState.FORK_INVALID:
            raise LockOwnershipError("manifest writer is invalid after fork")
        if self._writer_state is _WriterState.COMPROMISED:
            raise LockOwnershipError("manifest writer is terminal after authority failure")
        if self._writer_state is _WriterState.CLOSED:
            raise SingleWriterError("manifest writer is closed")
        if self._writer_state is _WriterState.FINALIZED:
            raise SegmentFinalizedError("manifest segment is already finalized")
        if self._terminal_error is not None:
            raise LockOwnershipError("manifest writer is terminal after authority failure") from (
                self._terminal_error
            )
        if self._closed:
            raise SingleWriterError("manifest writer is closed")
        try:
            self._authority_lock.assert_owned()
        except LockOwnershipError as exc:
            self._writer_state = _WriterState.COMPROMISED
            self._closed = True
            self._terminal_error = exc
            raise
        return self._authority_lock.authority_fd

    def close(self) -> None:
        with self._lock:
            if self._writer_state is _WriterState.CLOSED:
                return
            if self._writer_state is _WriterState.FINALIZED:
                return
            if self._writer_state is _WriterState.COMPROMISED:
                raise LockOwnershipError("manifest writer is terminal after authority failure")
            if self._writer_state is _WriterState.FORK_INVALID:
                raise LockOwnershipError("manifest writer is invalid after fork")
            if self._terminal_error is not None:
                raise LockOwnershipError("manifest writer is terminal after authority failure") from (
                    self._terminal_error
                )
            if self._closed:
                return
            self._writer_state = _WriterState.CLOSING
            try:
                self._authority_lock.release()
            except LockOwnershipError as exc:
                self._writer_state = _WriterState.COMPROMISED
                self._closed = True
                self._terminal_error = exc
                raise
            self._writer_state = _WriterState.CLOSED
            self._closed = True

    def _close_locked(self) -> None:
        """Internal close without acquiring the lock (caller must hold lock)."""
        if self._writer_state is _WriterState.CLOSED:
            return
        if self._writer_state is _WriterState.COMPROMISED:
            return
        if self._writer_state is _WriterState.FORK_INVALID:
            return
        self._writer_state = _WriterState.CLOSING
        try:
            self._authority_lock.release()
        except LockOwnershipError as exc:
            self._writer_state = _WriterState.COMPROMISED
            self._closed = True
            self._terminal_error = exc
            raise
        self._writer_state = _WriterState.CLOSED
        self._closed = True

    def append(self, event: RawEventV0) -> ManifestAppendResult:
        with self._lock:
            return self._append_locked(event)

    def _append_locked(self, event: RawEventV0) -> ManifestAppendResult:
        authority_fd = self._assert_active()
        if self._finalized or self.store.exists_regular(
            self._checkpoint_ref,
            authority_fd=authority_fd,
        ):
            raise SegmentFinalizedError("cannot append after segment finalization")
        exact_event = RawEventV0.model_validate(event)
        self.store.verify_payload(exact_event, authority_fd=authority_fd)
        by_slot, by_event_id = scan_global_observation_authority(
            self.store,
            authority_fd=authority_fd,
        )
        existing = by_slot.get(exact_event.observation_slot_id)
        if existing is not None:
            if existing.raw_event == exact_event:
                return ManifestAppendResult(AppendDisposition.IDEMPOTENT, existing)
            raise ObservationConflictError(
                "global observation slot has conflicting RawEvent authority"
            )
        existing_event = by_event_id.get(exact_event.source_event_id)
        if existing_event is not None:
            if existing_event.raw_event == exact_event:
                return ManifestAppendResult(AppendDisposition.IDEMPOTENT, existing_event)
            raise ObservationConflictError(
                "global source_event_id has conflicting RawEvent authority"
            )
        previous_hash = self.entries[-1].entry_hash if self.entries else MANIFEST_GENESIS_HASH
        entry = RawManifestEntryV0.bind(
            segment_id=self.segment_id,
            entry_index=len(self.entries),
            previous_entry_hash=previous_hash,
            raw_event=exact_event,
        )
        line = entry.model_dump_json().encode("utf-8") + b"\n"

        authority_fd = self._assert_active()
        parent_fd, filename = self.store._open_parent(
            self._manifest_ref,
            create=False,
            authority_fd=authority_fd,
        )
        try:
            fd = _open_verified_at(
                parent_fd,
                filename,
                os.O_WRONLY | os.O_APPEND,
                kind="regular",
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

    def finalize(self) -> RawManifestCheckpointV0:
        with self._lock:
            return self._finalize_locked()

    def _finalize_locked(self) -> RawManifestCheckpointV0:
        authority_fd = self._assert_active()
        if self._finalized or self.store.exists_regular(
            self._checkpoint_ref,
            authority_fd=authority_fd,
        ):
            raise SegmentFinalizedError("manifest segment is already finalized")
        self.store.fsync_file(self._manifest_ref, authority_fd=authority_fd)
        entries = read_manifest_entries(
            self.store,
            self.manifest_date,
            self.segment_id,
            authority_fd=authority_fd,
        )
        if tuple(self.entries) != entries:
            raise BronzeIntegrityError("manifest changed outside the active writer")
        terminal = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
        checkpoint = RawManifestCheckpointV0.bind(
            manifest_date=self.manifest_date,
            segment_id=self.segment_id,
            expected_entry_count=len(entries),
            terminal_entry_hash=terminal,
        )
        authority_fd = self._assert_active()
        self.store.publish_checkpoint(
            self.manifest_date,
            self.segment_id,
            checkpoint,
            authority_fd=authority_fd,
        )
        self._finalized = True
        self._writer_state = _WriterState.FINALIZED
        self._close_locked()
        return checkpoint
