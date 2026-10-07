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
) -> list[str]:
    work = args.replay_root / "work"
    proof = args.replay_root / "proof"
    properties = _systemd_properties(
        work=work,
        proof=proof,
        stage_root=args.stage_root,
        native_log=args.native_log,
        manifest=args.manifest,
        replay_facts=args.replay_facts,
    )
    internal = [
        str(args.staged_python),
        "-B",
        str(Path(__file__).absolute()),
        "--inside-unit",
        "--execute-authorized-replay",
        "--unit-name",
        args.unit_name,
        "--replay-root",
        str(args.replay_root),
        "--stage-root",
        str(args.stage_root),
        "--staged-python",
        str(args.staged_python),
        "--verifier",
        str(args.verifier),
        "--native-log",
        str(args.native_log),
        "--manifest",
        str(args.manifest),
        "--production-service",
        args.production_service,
        "--activation-permit",
        str(args.activation_permit),
        "--host-preflight",
        _encode_internal(host_preflight),
    ]
    if args.replay_facts is not None:
        internal.extend(("--replay-facts", str(args.replay_facts)))
    command = [
        "systemd-run",
        "--unit",
        args.unit_name,
        "--wait",
        "--collect",
        "--service-type=exec",
    ]
    command.extend(f"--property={value}" for value in properties)
    command.append("--")
    command.extend(internal)
    return command


def _drop_replay_credentials() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    pr_set_no_new_privs = 38
    if libc.prctl(pr_set_no_new_privs, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    os.setgroups([])
    os.setgid(REPLAY_GID)
    os.setuid(REPLAY_UID)


def _status_fields() -> dict[str, str]:
    wanted = {"Uid", "Gid", "Groups", "CapEff", "NoNewPrivs"}
    result: dict[str, str] = {}
    for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in wanted:
            result[key] = value.strip()
    return result


def _probe_one_source(path: Path, expected: dict[str, object]) -> dict[str, object]:
    flags_common = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, os.O_RDONLY | flags_common)
    try:
        state = os.fstat(fd)
        if state.st_dev != expected.get("dev") or state.st_ino != expected.get("inode"):
            raise ReplayControllerError(f"read-only probe identity mismatch: {path}")
    finally:
        os.close(fd)
    denials: dict[str, str] = {}
    for label, mode in (("O_WRONLY", os.O_WRONLY), ("O_RDWR", os.O_RDWR)):
        try:
            write_fd = os.open(path, mode | flags_common)
        except OSError as exc:
            if exc.errno != errno.EROFS:
                raise ReplayControllerError(
                    f"{label} must fail with EROFS for {path}; got errno={exc.errno}"
                ) from exc
            denials[label] = "EROFS"
        else:
            os.close(write_fd)
            raise ReplayControllerError(f"{label} unexpectedly succeeded for {path}")
    return {
        "path": str(path),
        "read_only": "PASS",
        "dev": expected["dev"],
        "inode": expected["inode"],
        "write_denials": denials,
    }


def _probe_child(args: argparse.Namespace) -> int:
    expected = _decode_internal(args.probe_expected)
    status_fields = _status_fields()
    expected_uid = str(REPLAY_UID)
    expected_gid = str(REPLAY_GID)
    if os.getuid() != REPLAY_UID or os.geteuid() != REPLAY_UID:
        raise ReplayControllerError("probe UID is not exact replay UID")
    if os.getgid() != REPLAY_GID or os.getegid() != REPLAY_GID:
        raise ReplayControllerError("probe GID is not exact replay GID")
    if os.getgroups():
        raise ReplayControllerError("probe supplementary groups are not empty")
    if int(status_fields.get("CapEff", "1"), 16) != 0:
        raise ReplayControllerError("probe effective capabilities are not empty")
    if status_fields.get("NoNewPrivs") != "1":
        raise ReplayControllerError("probe no-new-privileges is not active")
    uid_fields = status_fields.get("Uid", "").split()
    gid_fields = status_fields.get("Gid", "").split()
    if not uid_fields or any(value != expected_uid for value in uid_fields):
        raise ReplayControllerError("probe /proc UID state is inconsistent")
    if not gid_fields or any(value != expected_gid for value in gid_fields):
        raise ReplayControllerError("probe /proc GID state is inconsistent")

    sources = []
    for key, source_path in (("native_log", args.native_log), ("manifest", args.manifest)):
        binding = expected.get(key)
        if not isinstance(binding, dict):
            raise ReplayControllerError("probe expected source binding is missing")
        sources.append(_probe_one_source(source_path, binding))
    if args.replay_facts is not None:
        binding = expected.get("replay_facts")
        if not isinstance(binding, dict):
            raise ReplayControllerError("probe expected facts binding is missing")
        sources.append(_probe_one_source(args.replay_facts, binding))

    sentinel = args.proof_dir / ".child-write-probe"
    try:
        proof_fd = os.open(
            sentinel,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EROFS, errno.EPERM):
            raise ReplayControllerError(f"unexpected PROOF denial errno={exc.errno}") from exc
        proof_denial = errno.errorcode.get(exc.errno, str(exc.errno))
    else:
        os.close(proof_fd)
        try:
            sentinel.unlink()
        except OSError:
            pass
        raise ReplayControllerError("replay identity unexpectedly wrote DURABLE_PROOF")

    print(
        _canonical_bytes(
            {
                "uid": REPLAY_UID,
                "gid": REPLAY_GID,
                "supplementary_groups": [],
                "cap_eff": 0,
                "no_new_privileges": True,
                "sources": sources,
                "proof_write_denial": proof_denial,
            }
        ).decode()
    )
    return 0


def _minimal_child_env(work: Path) -> dict[str, str]:
    home = work / "home"
    temp = work / "tmp"
    cache = work / "cache"
    for directory in (home, temp, cache):
        if directory.exists() or directory.is_symlink():
            raise ReplayControllerError(f"child environment path collision: {directory}")
        directory.mkdir(mode=0o770)
        os.chown(directory, 0, REPLAY_GID)
        os.chmod(directory, 0o770)
    return {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "HOME": str(home),
        "TMPDIR": str(temp),
        "TMP": str(temp),
        "TEMP": str(temp),
        "SQLITE_TMPDIR": str(temp),
        "XDG_CACHE_HOME": str(cache),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
    }


def _run_credential_probe(
    args: argparse.Namespace, expected: dict[str, object], env: dict[str, str]
) -> dict[str, object]:
    command = [
        str(args.staged_python),
        "-B",
        str(Path(__file__).absolute()),
        "--probe-child",
        "--native-log",
        str(args.native_log),
        "--manifest",
        str(args.manifest),
        "--proof-dir",
        str(args.replay_root / "proof"),
        "--probe-expected",
        _encode_internal(expected),
    ]
    if args.replay_facts is not None:
        command.extend(("--replay-facts", str(args.replay_facts)))
    completed = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=_drop_replay_credentials,
        close_fds=True,
        shell=False,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        raise ReplayControllerError(
            "exact replay-credential read-only probe failed: "
            + completed.stderr.decode("utf-8", "replace")[-2048:]
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ReplayControllerError("credential probe did not emit canonical JSON") from exc
    if not isinstance(value, dict):
        raise ReplayControllerError("credential probe output is not an object")
    return value


class _BoundedCapture(threading.Thread):
    def __init__(self, stream: Any, path: Path) -> None:
        super().__init__(daemon=True)
        self.stream = stream
        self.path = path
        self.digest = hashlib.sha256()
        self.byte_count = 0
        self.retained_bytes = 0
        self.error: BaseException | None = None

    def run(self) -> None:
        fd = -1
        try:
            fd = os.open(
                self.path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            while True:
                data = self.stream.read(COPY_CHUNK_BYTES)
                if not data:
                    break
                self.digest.update(data)
                self.byte_count += len(data)
                if self.retained_bytes < STREAM_RETAIN_MAX_BYTES:
                    retained = data[: STREAM_RETAIN_MAX_BYTES - self.retained_bytes]
                    view = memoryview(retained)
                    while view:
                        written = os.write(fd, view)
                        if written <= 0:
                            raise ReplayControllerError(f"short bounded-log write: {self.path}")
                        view = view[written:]
                    self.retained_bytes += len(retained)
            os.fsync(fd)
        except BaseException as exc:  # surfaced in supervisor thread
            self.error = exc
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                self.stream.close()
            except Exception:
                pass

    def payload(self) -> dict[str, object]:
        if self.error is not None:
            raise ReplayControllerError(f"stream capture failed: {self.path}") from self.error
        return {
            "full_stream_sha256": self.digest.hexdigest(),
            "byte_count": self.byte_count,
            "retained_bytes": self.retained_bytes,
            "retain_cap_bytes": STREAM_RETAIN_MAX_BYTES,
            "truncated": self.byte_count > self.retained_bytes,
            "truncation_marker": (
                "TRUNCATED=YES" if self.byte_count > self.retained_bytes else "TRUNCATED=NO"
            ),
        }


def _verifier_argv(args: argparse.Namespace, scratch: Path) -> list[str]:
    command = [
        str(args.staged_python),
        "-B",
        str(args.verifier),
        "--replay-native-log",
        str(args.native_log),
        "--manifest",
        str(args.manifest),
        "--verifier-scratch-root",
        str(scratch),
        "--result-path",
        str(scratch / "replay-diagnostic.json"),
    ]
    if args.replay_facts is not None:
        command.extend(("--replay-facts", str(args.replay_facts)))
    return command


def _run_verifier_child(
    args: argparse.Namespace, work: Path, env: dict[str, str]
) -> dict[str, object]:
    scratch = work / "verifier"
    scratch.mkdir(mode=0o770)
    os.chown(scratch, 0, REPLAY_GID)
    os.chmod(scratch, 0o770)
    if any(scratch.iterdir()):
        raise ReplayControllerError("verifier scratch must begin empty")

    command = _verifier_argv(args, scratch)
    started_ns = time.time_ns()
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=_drop_replay_credentials,
        close_fds=True,
        shell=False,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    stdout_capture = _BoundedCapture(process.stdout, work / "child.stdout.log")
    stderr_capture = _BoundedCapture(process.stderr, work / "child.stderr.log")
    stdout_capture.start()
    stderr_capture.start()

    timed_out = False
    term_sent = False
    kill_sent = False
    try:
        returncode = process.wait(timeout=CHILD_DEADLINE_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        term_sent = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            returncode = process.wait(timeout=TERM_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            kill_sent = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = process.wait()
    stdout_capture.join()
    stderr_capture.join()
    finished_ns = time.time_ns()
    return {
        "argv": command,
        "started_ns": started_ns,
        "finished_ns": finished_ns,
        "deadline_seconds": CHILD_DEADLINE_SECONDS,
        "term_grace_seconds": TERM_GRACE_SECONDS,
        "timed_out": timed_out,
        "sigterm_sent": term_sent,
        "sigkill_sent": kill_sent,
        "returncode": returncode,
        "signal": -returncode if returncode < 0 else None,
        "stdout": stdout_capture.payload(),
        "stderr": stderr_capture.payload(),
    }


def _decode_mount_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _work_mount_evidence(work: Path) -> dict[str, object]:
    target = str(work.resolve(strict=True))
    found: dict[str, object] | None = None
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        left, separator, right = line.partition(" - ")
        if not separator:
            continue
        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 6 or len(right_fields) < 3:
            continue
        mount_point = _decode_mount_field(left_fields[4])
        if mount_point != target:
            continue
        mount_options = set(left_fields[5].split(","))
        super_options = set(right_fields[2].split(","))
        found = {
            "mount_point": mount_point,
            "mount_options": sorted(mount_options),
            "fs_type": right_fields[0],
            "mount_source": right_fields[1],
            "super_options": sorted(super_options),
        }
        break
    if found is None or found["fs_type"] != "tmpfs":
        raise ReplayControllerError("WORK is not the exact transient tmpfs")
    options = set(found["mount_options"])
    if not {"rw", "nosuid", "nodev", "noexec"}.issubset(options):
        raise ReplayControllerError("WORK tmpfs mount options are incomplete")
    state = work.lstat()
    if state.st_uid != 0 or state.st_gid != REPLAY_GID or stat.S_IMODE(state.st_mode) != 0o770:
        raise ReplayControllerError("WORK tmpfs ownership/mode is not exact")
    stats = os.statvfs(work)
    total_bytes = stats.f_frsize * stats.f_blocks
    if total_bytes > WORK_TMPFS_MAX_BYTES:
        raise ReplayControllerError("WORK tmpfs allocation exceeds 768MiB")
    found.update(
        {
            "uid": state.st_uid,
            "gid": state.st_gid,
            "mode": stat.S_IMODE(state.st_mode),
            "allocation_bytes": total_bytes,
            "allocation_max_bytes": WORK_TMPFS_MAX_BYTES,
        }
    )
    return found


def _systemd_unit_evidence(
    unit_name: str, expected_properties: tuple[str, ...]
) -> dict[str, object]:
    names = (
        "ProtectSystem",
        "ProtectHome",
        "PrivateNetwork",
        "PrivateDevices",
        "NoNewPrivileges",
        "CapabilityBoundingSet",
        "MemoryMax",
        "TasksMax",
        "RuntimeMaxUSec",
        "Restart",
        "PrivateTmp",
        "BindReadOnlyPaths",
        "ReadWritePaths",
        "TemporaryFileSystem",
    )
    completed = subprocess.run(
        ("systemctl", "show", unit_name, "--no-pager", *(f"--property={name}" for name in names)),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        close_fds=True,
    )
    if completed.returncode != 0:
        raise ReplayControllerError("cannot read back transient systemd properties")
    actual: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            actual[key] = value
    required = {
        "ProtectSystem": "strict",
        "ProtectHome": "yes",
        "PrivateNetwork": "yes",
        "PrivateDevices": "yes",
        "NoNewPrivileges": "yes",
        "MemoryMax": str(CGROUP_MEMORY_MAX_BYTES),
        "TasksMax": str(TASKS_MAX),
        "Restart": "no",
        "PrivateTmp": "no",
    }
    for key, value in required.items():
        if actual.get(key) != value:
            raise ReplayControllerError(f"transient unit property mismatch: {key}")
    caps = {item.lower() for item in actual.get("CapabilityBoundingSet", "").split()}
    if caps != {"cap_setuid", "cap_setgid", "cap_kill"}:
        raise ReplayControllerError("transient unit capability set mismatch")
    runtime = actual.get("RuntimeMaxUSec", "")
    if runtime not in ("40min", "2400s", "2400000000"):
        raise ReplayControllerError("transient unit RuntimeMaxSec mismatch")
    return {
        "unit": unit_name,
        "requested": list(expected_properties),
        "actual": actual,
        "forbidden_properties_absent_from_request": all(
            not any(value.startswith(name + "=") for value in expected_properties)
            for name in FORBIDDEN_SYSTEMD_PROPERTIES
        ),
    }


def _work_inventory(work: Path) -> dict[str, object]:
    root_state = work.lstat()
    entries: list[dict[str, object]] = [
        {
            "path": ".",
            "type": "directory",
            "mode": stat.S_IMODE(root_state.st_mode),
            "uid": root_state.st_uid,
            "gid": root_state.st_gid,
            "size": root_state.st_size,
        }
    ]
    regular_count = 0
    total_regular_bytes = 0
    stack = [work]
    while stack:
        directory = stack.pop()
        children = sorted(os.scandir(directory), key=lambda item: item.name, reverse=True)
        for item in children:
            item_path = Path(item.path)
            state = item_path.lstat()
            relative = item_path.relative_to(work).as_posix()
            common = {
                "path": relative,
                "mode": stat.S_IMODE(state.st_mode),
                "uid": state.st_uid,
                "gid": state.st_gid,
                "size": state.st_size,
            }
            if stat.S_ISDIR(state.st_mode):
                entries.append({**common, "type": "directory"})
                stack.append(item_path)
                continue
            if not stat.S_ISREG(state.st_mode):
                raise ReplayControllerError(f"WORK contains non-regular special entry: {relative}")
            if state.st_nlink != 1:
                raise ReplayControllerError(f"WORK contains hardlink ambiguity: {relative}")
            digest, size = _hash_path(item_path)
            if size != state.st_size:
                raise ReplayControllerError(f"WORK file changed during inventory: {relative}")
            regular_count += 1
            total_regular_bytes += size
            entries.append({**common, "type": "regular", "sha256": digest})
    entries.sort(key=lambda entry: str(entry["path"]))
    return {
        "schema": "trade-os/e4-replay-work-inventory/v1",
        "entry_count": len(entries),
        "regular_file_count": regular_count,
        "total_regular_file_bytes": total_regular_bytes,
        "entries": entries,
    }


def _source_bindings_from_host(
    args: argparse.Namespace, host_preflight: dict[str, Any]
) -> dict[str, dict[str, object]]:
    names = [("native_log", args.native_log), ("manifest", args.manifest)]
    if args.replay_facts is not None:
        names.append(("replay_facts", args.replay_facts))
    expected: dict[str, dict[str, object]] = {}
    host_bindings = host_preflight.get("source_bindings")
    if not isinstance(host_bindings, dict):
        raise ReplayControllerError("host source binding evidence is missing")
    for name, source_path in names:
        binding = host_bindings.get(name)
        if not isinstance(binding, dict):
            raise ReplayControllerError(f"host source binding is missing: {name}")
        current_binding = _file_binding(source_path)
        if current_binding != binding:
            raise ReplayControllerError(f"source drift before replay credential probe: {name}")
        expected[name] = current_binding
    return expected


def _proof_inventory(proof: Path) -> list[dict[str, object]]:
    values = []
    for name in PROOF_FILES:
        proof_path = proof / name
        if proof_path.is_file() and not proof_path.is_symlink():
            digest, size = _hash_path(proof_path)
            values.append({"path": name, "sha256": digest, "size": size})
    return values


def _readback_exact(proof: Path, files: list[dict[str, object]]) -> bool:
    for entry in files:
        proof_path = proof / str(entry["path"])
        digest, size = _hash_path(proof_path)
        if digest != entry["sha256"] or size != entry["size"]:
            return False
    return True


def _finalize_proof(
    proof: Path,
    *,
    export_status: str,
    blockers: list[str],
    source_binding: dict[str, object] | None,
    unit_properties: dict[str, object] | None,
) -> dict[str, object]:
    _fsync_dir(proof)
    files = _proof_inventory(proof)
    readback = _readback_exact(proof, files)
    if not readback:
        export_status = "FAIL"
        blockers.append("PROOF_POST_FSYNC_READBACK_MISMATCH")
    manifest = {
        "schema": "trade-os/e4-replay-proof-manifest/v1",
        "files": files,
        "directory_fsync_completion": True,
        "post_fsync_readback_sha256_equality": readback,
        "source_binding": source_binding,
        "unit_properties_bound": unit_properties is not None,
        "DURABLE_EVIDENCE_EXPORT": export_status,
        "blockers": sorted(set(blockers)),
    }
    final_bytes = _write_json_replace(proof / "proof-manifest.json", manifest)
    with (proof / "proof-manifest.json").open("rb") as stream:
        if stream.read() != final_bytes:
            manifest["DURABLE_EVIDENCE_EXPORT"] = "FAIL"
            manifest["blockers"] = sorted(
                set(manifest["blockers"] + ["PROOF_MANIFEST_SELF_READBACK_MISMATCH"])
            )
            _write_json_replace(proof / "proof-manifest.json", manifest)
    _fsync_dir(proof)
    return manifest


def _inside_unit(args: argparse.Namespace) -> int:
    if os.geteuid() != 0:
        raise ReplayControllerError("transient replay controller supervisor must run as root")
    host_preflight = _decode_internal(args.host_preflight)
    work = args.replay_root / "work"
    proof = args.replay_root / "proof"
    if not work.is_dir() or not proof.is_dir():
        raise ReplayControllerError("WORK/PROOF runtime roots are unavailable")
    proof_state = proof.lstat()
    if (
        proof_state.st_uid != 0
        or proof_state.st_gid != 0
        or stat.S_IMODE(proof_state.st_mode) != 0o750
    ):
        raise ReplayControllerError("PROOF must be root-owned mode 0750")

