#!/usr/bin/env python3
"""Run one future-authorized E4 retained-log replay in a bounded transient systemd unit.

This controller is deliberately inert unless the explicit replay execution flag is
present.  It creates no static unit and owns only the frozen replay diagnostic
boundary: preflight, the exact replay-identity read-only probe, verifier child
lifecycle, bounded stream capture, and durable proof retention.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import errno
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Final

REPLAY_UID: Final = 999
REPLAY_GID: Final = 988
CHILD_DEADLINE_SECONDS: Final = 1800
EVIDENCE_ALLOWANCE_SECONDS: Final = 300
RUNTIME_MAX_SECONDS: Final = 2400
WORK_TMPFS_MAX_BYTES: Final = 768 * 1024 * 1024
CGROUP_MEMORY_MAX_BYTES: Final = 1280 * 1024 * 1024
PRESTART_MEMAVAILABLE_MIN_BYTES: Final = 1408 * 1024 * 1024
VERIFIER_HWM_MAX_BYTES: Final = 256 * 1024 * 1024
TASKS_MAX: Final = 16
STREAM_RETAIN_MAX_BYTES: Final = 8 * 1024 * 1024
COPY_CHUNK_BYTES: Final = 64 * 1024
TERM_GRACE_SECONDS: Final = 10

PROOF_FILES: Final = (
    "controller-result.json",
    "replay-diagnostic.json",
    "replay-verifier-resources.json",
    "child-exit.json",
    "source-binding.json",
    "unit-properties.json",
    "child.stdout.log",
    "child.stderr.log",
    "work-inventory.json",
)
FORBIDDEN_SYSTEMD_PROPERTIES: Final = (
    "SystemCallFilter",
    "RestrictNamespaces",
    "RestrictAddressFamilies",
    "SystemCallArchitectures",
    "MemoryDenyWriteExecute",
    "LockPersonality",
    "RestrictRealtime",
)


class ReplayControllerError(RuntimeError):
    """The frozen controller contract cannot be satisfied."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha256_fd(fd: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    os.lseek(fd, 0, os.SEEK_SET)
    while True:
        chunk = os.read(fd, COPY_CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def _open_regular_ro(path: Path) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    state = os.fstat(fd)
    if not stat.S_ISREG(state.st_mode):
        os.close(fd)
        raise ReplayControllerError(f"not a regular file: {path}")
    return fd, state


def _file_binding(path: Path) -> dict[str, object]:
    absolute = path.absolute()
    fd, state = _open_regular_ro(absolute)
    try:
        digest, size = _sha256_fd(fd)
    finally:
        os.close(fd)
    if size != state.st_size:
        raise ReplayControllerError(f"file size changed while hashing: {absolute}")
    return {
        "path": str(absolute),
        "dev": state.st_dev,
        "inode": state.st_ino,
        "mode": stat.S_IMODE(state.st_mode),
        "uid": state.st_uid,
        "gid": state.st_gid,
        "size": state.st_size,
        "mtime_ns": state.st_mtime_ns,
        "ctime_ns": state.st_ctime_ns,
        "sha256": digest,
    }


def _mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            fields = line.split()
            if len(fields) != 3 or fields[2] != "kB":
                break
            return int(fields[1]) * 1024
    raise ReplayControllerError("/proc/meminfo MemAvailable is unavailable")


def _swap_counters() -> dict[str, int]:
    wanted = {"pswpin", "pswpout"}
    found: dict[str, int] = {}
    for line in Path("/proc/vmstat").read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] in wanted:
            found[fields[0]] = int(fields[1])
    if set(found) != wanted:
        raise ReplayControllerError("swap counters are unavailable")
    return found


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_exclusive(path: Path, data: bytes, mode: int = 0o600) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags, mode)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise ReplayControllerError(f"short write: {path}")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_json_exclusive(path: Path, value: object) -> None:
    _write_exclusive(path, _canonical_bytes(value) + b"\n")


def _write_json_replace(path: Path, value: object) -> bytes:
    data = _canonical_bytes(value) + b"\n"
    temp = path.with_name(path.name + ".tmp")
    if temp.exists() or temp.is_symlink():
        raise ReplayControllerError(f"proof temp collision: {temp}")
    _write_exclusive(temp, data)
    os.replace(temp, path)
    _fsync_dir(path.parent)
    return data


def _hash_path(path: Path) -> tuple[str, int]:
    fd, state = _open_regular_ro(path)
    try:
        digest, size = _sha256_fd(fd)
    finally:
        os.close(fd)
    if size != state.st_size:
        raise ReplayControllerError(f"file size changed during proof hash: {path}")
    return digest, size


def _stream_copy_exclusive(source: Path, destination: Path) -> dict[str, object]:
    source_fd, source_state = _open_regular_ro(source)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    destination_fd = os.open(destination, flags, 0o600)
    digest = hashlib.sha256()
    total = 0
    try:
        while True:
            chunk = os.read(source_fd, COPY_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_fd, view)
                if written <= 0:
                    raise ReplayControllerError(f"short copy write: {destination}")
                view = view[written:]
        os.fsync(destination_fd)
    finally:
        os.close(source_fd)
        os.close(destination_fd)
    if total != source_state.st_size:
        raise ReplayControllerError(f"source changed during durable copy: {source}")
    copied_digest, copied_size = _hash_path(destination)
    if copied_digest != digest.hexdigest() or copied_size != total:
        raise ReplayControllerError(f"durable copy readback mismatch: {destination}")
    return {"sha256": copied_digest, "size": copied_size}


def _require_absolute_regular(path: Path, *, name: str) -> Path:
    if not path.is_absolute():
        raise ReplayControllerError(f"{name} must be absolute")
    if path.is_symlink() or not path.is_file():
        raise ReplayControllerError(f"{name} must be a non-symlink regular file")
    return path


def _require_beneath(child: Path, parent: Path, *, name: str) -> None:
    child_resolved = child.resolve(strict=True)
    parent_resolved = parent.resolve(strict=True)
    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError as exc:
        raise ReplayControllerError(f"{name} is outside the exact staged root") from exc


def _ensure_new_directory(path: Path, *, mode: int, uid: int, gid: int) -> None:
    if path.exists() or path.is_symlink():
        raise ReplayControllerError(f"runtime path must be absent: {path}")
    path.mkdir(mode=mode)
    os.chown(path, uid, gid)
    os.chmod(path, mode)


def _systemctl_value(*arguments: str) -> tuple[int, str]:
    completed = subprocess.run(
        ("systemctl", *arguments),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        close_fds=True,
    )
    return completed.returncode, completed.stdout.strip()


def _assert_production_default_off(service: str, permit: Path) -> dict[str, object]:
    active_rc, active = _systemctl_value("is-active", service)
    enabled_rc, enabled = _systemctl_value("is-enabled", service)
    if active != "inactive" or active_rc not in (0, 3):
        raise ReplayControllerError("production service is not exactly inactive")
    if enabled != "disabled" or enabled_rc not in (0, 1):
        raise ReplayControllerError("production service unit is not exactly disabled")
    if permit.exists() or permit.is_symlink():
        raise ReplayControllerError("activation permit must be absent")
    return {
        "production_service": service,
        "active": active,
        "unitfile": enabled,
        "activation_permit": str(permit),
        "activation_permit_absent": True,
    }


def _encode_internal(value: object) -> str:
    return base64.urlsafe_b64encode(_canonical_bytes(value)).decode("ascii")


def _decode_internal(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ReplayControllerError("internal host preflight payload is invalid") from exc
    if not isinstance(decoded, dict):
        raise ReplayControllerError("internal host preflight payload is not an object")
    return decoded


def _systemd_properties(
    *, work: Path, proof: Path, stage_root: Path, native_log: Path, manifest: Path,
    replay_facts: Path | None,
) -> tuple[str, ...]:
    properties = [
        "ProtectSystem=strict",
        f"BindReadOnlyPaths={stage_root}",
        f"BindReadOnlyPaths={native_log}",
        f"BindReadOnlyPaths={manifest}",
        f"TemporaryFileSystem={work}:size=768M,nosuid,nodev,noexec,mode=0770,uid=0,gid=988",
        f"ReadWritePaths={proof}",
        "ProtectHome=yes",
        "PrivateNetwork=yes",
        "PrivateDevices=yes",
        "NoNewPrivileges=yes",
        "CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_KILL",
        "MemoryMax=1280M",
        "TasksMax=16",
        "RuntimeMaxSec=2400s",
        "Restart=no",
        "PrivateTmp=no",
    ]
    if replay_facts is not None:
        properties.insert(4, f"BindReadOnlyPaths={replay_facts}")
    for property_value in properties:
        if any(property_value.startswith(name + "=") for name in FORBIDDEN_SYSTEMD_PROPERTIES):
            raise ReplayControllerError("forbidden systemd hardening property requested")
    return tuple(properties)


def build_systemd_run_argv(
    args: argparse.Namespace, host_preflight: dict[str, object]
