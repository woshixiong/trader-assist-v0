"""Fixed-profile local staging and Restic recovery verification.

This module deliberately owns only the application-specific staging contract.
Restic owns encryption, repository storage, locking, integrity and transport.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

REPOSITORY_IDENTITY = "woshixiong/trader-assist-v0"
METADATA_SCHEMA = "trader-assist-v0/recovery-metadata/v1"
FIRST_LAUNCH_PROFILE = "first-launch"
FULL_MULTI_ASSET_PROFILE = "full-multi-asset"
_FIRST_LAUNCH_RUNTIME = Path("/var/lib/trader-assist-v0/runtime.db")
_FIRST_LAUNCH_PUBLIC_ENV = Path("/etc/trader-assist-v0/public.env")
_FIRST_LAUNCH_RISK_CONFIG = Path("/etc/trader-assist-v0/risk-configuration.json")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SNAPSHOT_ID = re.compile(r"^[0-9a-f]{64}$")


class RecoveryError(RuntimeError):
    """The fixed recovery contract could not be staged or validated."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


ResticRunner = Callable[[Sequence[str]], CommandResult]


@dataclass(frozen=True)
class BackupEvidence:
    snapshot_id: str
    recovery_profile: str
    deployed_git_sha: str


@dataclass(frozen=True)
class RecoveryPaths:
    """Operator-supplied paths for the currently unbound MultiAsset sources only."""

    multi_asset_evidence: Path | None = None
    multi_asset_registry: Path | None = None


@dataclass(frozen=True)
class _RecoveryPaths:
    """Private path injection seam for deterministic offline staging tests."""

    first_launch_runtime: Path
    first_launch_public_env: Path
    first_launch_risk_config: Path
    multi_asset_evidence: Path | None = None
    multi_asset_registry: Path | None = None


@dataclass(frozen=True)
class _AssetDefinition:
    logical_id: str
    kind: str
    staged_path: str


_FIRST_LAUNCH_ASSETS = (
    _AssetDefinition("first-launch-runtime", "sqlite", "first-launch-runtime/database.sqlite"),
    _AssetDefinition("first-launch-public-env", "file", "first-launch-public-env/file"),
    _AssetDefinition("first-launch-risk-config", "file", "first-launch-risk-config/file"),
)
_MULTI_ASSET_ASSETS = (
    _AssetDefinition("multi-asset-evidence", "sqlite", "multi-asset-evidence/database.sqlite"),
    _AssetDefinition("multi-asset-registry", "directory", "multi-asset-registry/tree"),
)


def _canonical_json(value: object) -> bytes:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return encoded.encode() + b"\n"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_regular(path: Path, *, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise RecoveryError(f"required {label} is missing") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise RecoveryError(f"required {label} must be a regular file, not a link or special file")


def _require_directory(path: Path, *, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise RecoveryError(f"required {label} is missing") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise RecoveryError(f"required {label} must be a directory, not a link or special file")


def _validate_git_sha(deployed_git_sha: str) -> None:
    if not _GIT_SHA.fullmatch(deployed_git_sha):
        raise RecoveryError("deployed Git SHA must be exactly 40 lowercase hexadecimal characters")


def _asset_definitions(profile: str, paths: _RecoveryPaths) -> tuple[_AssetDefinition, ...]:
    if profile == FIRST_LAUNCH_PROFILE:
        if paths.multi_asset_evidence is not None or paths.multi_asset_registry is not None:
            raise RecoveryError("First Launch profile cannot include MultiAsset assets")
        return _FIRST_LAUNCH_ASSETS
    if profile == FULL_MULTI_ASSET_PROFILE:
        if paths.multi_asset_evidence is None or paths.multi_asset_registry is None:
            raise RecoveryError("Full MultiAsset profile requires both explicit MultiAsset paths")
        return _FIRST_LAUNCH_ASSETS + _MULTI_ASSET_ASSETS
    raise RecoveryError("unknown recovery profile")


def _source_for(asset: _AssetDefinition, paths: _RecoveryPaths) -> Path:
    sources = {
        "first-launch-runtime": paths.first_launch_runtime,
        "first-launch-public-env": paths.first_launch_public_env,
        "first-launch-risk-config": paths.first_launch_risk_config,
        "multi-asset-evidence": paths.multi_asset_evidence,
        "multi-asset-registry": paths.multi_asset_registry,
    }
    source = sources[asset.logical_id]
    if source is None:  # safeguarded by _asset_definitions
        raise RecoveryError(f"missing fixed source for {asset.logical_id}")
    return source


def _sqlite_snapshot(source: Path, destination: Path) -> tuple[str, str]:
    _require_regular(source, label="SQLite source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    uri = f"file:{quote(str(source.resolve()), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as source_connection:
            with sqlite3.connect(destination) as destination_connection:
                source_connection.backup(destination_connection)
                quick = [row[0] for row in destination_connection.execute("PRAGMA quick_check")]
                integrity = [
                    row[0] for row in destination_connection.execute("PRAGMA integrity_check")
                ]
    except sqlite3.Error as exc:
        destination.unlink(missing_ok=True)
        raise RecoveryError("SQLite consistent snapshot or validation failed") from exc
    if quick != ["ok"] or integrity != ["ok"]:
        destination.unlink(missing_ok=True)
        raise RecoveryError("SQLite quick_check or integrity_check failed")
    return "ok", "ok"


def _copy_tree(source: Path, destination: Path) -> list[dict[str, str]]:
    _require_directory(source, label="Registry source")
    files: list[dict[str, str]] = []
    destination.mkdir(parents=True, exist_ok=False)
    stack = [(source, destination)]
    while stack:
        source_directory, destination_directory = stack.pop()
        with os.scandir(source_directory) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(source)
                target = destination / relative
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise RecoveryError("Registry source contains a symlink or special file")
                if stat.S_ISDIR(mode):
                    target.mkdir()
                    stack.append((Path(entry.path), target))
                else:
                    shutil.copyfile(entry.path, target, follow_symlinks=False)
                    files.append({"path": relative.as_posix(), "sha256": _sha256(target)})
    return sorted(files, key=lambda item: item["path"])


def _stage(profile: str, paths: _RecoveryPaths, deployed_git_sha: str, staging_root: Path) -> Path:
    _validate_git_sha(deployed_git_sha)
    capture_time = _utc_now()
    staging_root.mkdir(parents=True, exist_ok=True)
    recovery_root = staging_root / "recovery"
    recovery_root.mkdir()
    inventory: list[dict[str, Any]] = []
    for order, asset in enumerate(_asset_definitions(profile, paths), start=1):
        source = _source_for(asset, paths)
        target = recovery_root / asset.staged_path
        if asset.kind == "sqlite":
            quick, integrity = _sqlite_snapshot(source, target)
            inventory.append(
                {
                    "logical_id": asset.logical_id,
                    "type": asset.kind,
                    "path": asset.staged_path,
                    "files": [{"path": asset.staged_path, "sha256": _sha256(target)}],
                    "sqlite_validation": {
                        "quick_check": quick,
                        "integrity_check": integrity,
                        "capture_order": order,
                        "capture_utc": _utc_now(),
                    },
                }
            )
        elif asset.kind == "file":
            _require_regular(source, label=asset.logical_id)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target, follow_symlinks=False)
            inventory.append(
                {
                    "logical_id": asset.logical_id,
                    "type": asset.kind,
                    "path": asset.staged_path,
                    "files": [{"path": asset.staged_path, "sha256": _sha256(target)}],
                }
            )
        else:
            files = _copy_tree(source, target)
            inventory.append(
                {
                    "logical_id": asset.logical_id,
                    "type": asset.kind,
                    "path": asset.staged_path,
                    "files": [
                        {"path": f"{asset.staged_path}/{item['path']}", "sha256": item["sha256"]}
                        for item in files
                    ],
                }
            )
    metadata = {
        "schema": METADATA_SCHEMA,
        "repository_identity": REPOSITORY_IDENTITY,
        "deployed_git_sha": deployed_git_sha,
        "capture_utc": capture_time,
        "recovery_profile": profile,
        "assets": inventory,
        "per_database_consistency": True,
        "cross_database_atomic_snapshot": False,
    }
    (recovery_root / "recovery-metadata.json").write_bytes(_canonical_json(metadata))
    return recovery_root


def _run_subprocess(argv: Sequence[str]) -> CommandResult:
    completed = subprocess.run(list(argv), capture_output=True, check=False, text=True)
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _credential_args(password_file: Path | None, password_command: str | None) -> tuple[str, ...]:
    if (password_file is None) == (password_command is None):
        raise RecoveryError("supply exactly one external Restic password file or password command")
    if password_file is not None:
        return ("--password-file", str(password_file))
    assert password_command is not None
    return ("--password-command", password_command)


def _restic_prefix(repository: str, credential_args: Sequence[str]) -> list[str]:
    if not repository:
        raise RecoveryError("Restic repository location is required")
    return ["restic", "--repo", repository, *credential_args]


def _snapshot_id(stdout: str) -> str:
    snapshot_id: str | None = None
    for line in stdout.splitlines():
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RecoveryError("Restic backup did not emit valid JSON lines") from exc
        if message.get("message_type") == "summary":
            value = message.get("snapshot_id")
            if isinstance(value, str):
                snapshot_id = value
    if snapshot_id is None or not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise RecoveryError("Restic backup did not provide a concrete snapshot_id")
    return snapshot_id


def _fixed_recovery_paths(paths: RecoveryPaths) -> _RecoveryPaths:
    return _RecoveryPaths(
        first_launch_runtime=_FIRST_LAUNCH_RUNTIME,
        first_launch_public_env=_FIRST_LAUNCH_PUBLIC_ENV,
        first_launch_risk_config=_FIRST_LAUNCH_RISK_CONFIG,
        multi_asset_evidence=paths.multi_asset_evidence,
        multi_asset_registry=paths.multi_asset_registry,
    )


def backup_recovery(
    *,
    profile: str,
    paths: RecoveryPaths,
    deployed_git_sha: str,
    repository: str,
    password_file: Path | None = None,
    password_command: str | None = None,
    runner: ResticRunner = _run_subprocess,
    temporary_parent: Path | None = None,
) -> BackupEvidence:
    """Create and back up one fixed recovery profile; always removes plain staging."""
    return _backup_recovery(
        profile=profile,
        paths=_fixed_recovery_paths(paths),
        deployed_git_sha=deployed_git_sha,
        repository=repository,
        password_file=password_file,
        password_command=password_command,
        runner=runner,
        temporary_parent=temporary_parent,
    )


def _backup_recovery(
    *,
    profile: str,
    paths: _RecoveryPaths,
    deployed_git_sha: str,
    repository: str,
    password_file: Path | None = None,
    password_command: str | None = None,
    runner: ResticRunner = _run_subprocess,
    temporary_parent: Path | None = None,
) -> BackupEvidence:
    """Private deterministic-test seam for fixed-profile backup staging."""
    credentials = _credential_args(password_file, password_command)
    with tempfile.TemporaryDirectory(
        prefix="trader-assist-recovery-", dir=temporary_parent
    ) as workspace:
        recovery_root = _stage(profile, paths, deployed_git_sha, Path(workspace))
        command = [*_restic_prefix(repository, credentials),
            "--json",
            "backup",
            "--tag",
            "trader-assist",
            "--tag",
            f"recovery-profile={profile}",
            "--tag",
            f"git-sha={deployed_git_sha}",
            str(recovery_root),
        ]
        result = runner(command)
        if result.returncode != 0:
            raise RecoveryError("Restic backup failed")
        snapshot_id = _snapshot_id(result.stdout)
    return BackupEvidence(snapshot_id, profile, deployed_git_sha)


def _expected_assets(profile: str) -> tuple[_AssetDefinition, ...]:
    if profile == FIRST_LAUNCH_PROFILE:
        return _FIRST_LAUNCH_ASSETS
    if profile == FULL_MULTI_ASSET_PROFILE:
        return _FIRST_LAUNCH_ASSETS + _MULTI_ASSET_ASSETS
    raise RecoveryError("unknown recovery profile")


def _read_metadata(recovery_root: Path) -> dict[str, Any]:
    metadata_path = recovery_root / "recovery-metadata.json"
    _require_regular(metadata_path, label="recovery metadata")
    try:
        raw = metadata_path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError("recovery metadata is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryError("recovery metadata must be an object")
    if raw != _canonical_json(value):
        raise RecoveryError("recovery metadata must be canonical JSON")
    return value


def _validate_restored_tree(
    recovery_root: Path, *, expected_git_sha: str, expected_profile: str
) -> None:
    _validate_git_sha(expected_git_sha)
    metadata = _read_metadata(recovery_root)
    if metadata.get("schema") != METADATA_SCHEMA:
        raise RecoveryError("unsupported recovery metadata schema")
    if metadata.get("repository_identity") != REPOSITORY_IDENTITY:
        raise RecoveryError("recovery metadata repository identity does not match")
    if metadata.get("deployed_git_sha") != expected_git_sha:
        raise RecoveryError("recovery metadata deployed Git SHA does not match")
    if metadata.get("recovery_profile") != expected_profile:
        raise RecoveryError("recovery metadata profile does not match")
    if metadata.get("per_database_consistency") is not True:
        raise RecoveryError("per-database consistency declaration is missing")
    if metadata.get("cross_database_atomic_snapshot") is not False:
        raise RecoveryError("cross-database atomic snapshot declaration is invalid")
    assets = metadata.get("assets")
    if not isinstance(assets, list) or not all(isinstance(item, dict) for item in assets):
        raise RecoveryError("recovery metadata assets are invalid")
    expected = _expected_assets(expected_profile)
    if [(item.get("logical_id"), item.get("type"), item.get("path")) for item in assets] != [
        (item.logical_id, item.kind, item.staged_path) for item in expected
    ]:
        raise RecoveryError("recovery metadata asset inventory does not exactly match profile")
    top_level = {
        "recovery-metadata.json",
        *(item.staged_path.split("/", 1)[0] for item in expected),
    }
    found_top_level = {entry.name for entry in recovery_root.iterdir()}
    if found_top_level != top_level:
        raise RecoveryError("restored recovery tree contains undeclared top-level assets")
    for item, expected_asset in zip(assets, expected, strict=True):
        files = item.get("files")
        if not isinstance(files, list):
            raise RecoveryError("recovery metadata file inventory is invalid")
        declared_paths: set[str] = set()
        for declared in files:
            if not isinstance(declared, dict):
                raise RecoveryError("recovery metadata file declaration is invalid")
            relative = declared.get("path")
            digest = declared.get("sha256")
            if (
                not isinstance(relative, str)
                or not isinstance(digest, str)
                or not _SHA256.fullmatch(digest)
            ):
                raise RecoveryError("recovery metadata file declaration is invalid")
            if relative in declared_paths:
                raise RecoveryError("recovery metadata declares a file more than once")
            relative_path = Path(relative)
            if relative_path.is_absolute() or any(
                part in {"", ".", ".."} for part in relative_path.parts
            ):
                raise RecoveryError("recovery metadata payload path is invalid")
            declared_paths.add(relative)
            candidate = recovery_root / relative_path
            _require_regular(candidate, label="restored payload")
            if _sha256(candidate) != digest:
                raise RecoveryError("restored payload hash does not match recovery metadata")
        root = recovery_root / expected_asset.staged_path
        if expected_asset.kind == "sqlite":
            if declared_paths != {expected_asset.staged_path}:
                raise RecoveryError("SQLite inventory is invalid")
            quick, integrity = _sqlite_snapshot_readonly(root)
            validation = item.get("sqlite_validation")
            if (
                not isinstance(validation, dict)
                or validation.get("quick_check") != quick
                or validation.get("integrity_check") != integrity
                or not isinstance(validation.get("capture_order"), int)
                or validation["capture_order"] < 1
                or not isinstance(validation.get("capture_utc"), str)
            ):
                raise RecoveryError("restored SQLite validation metadata is invalid")
        elif expected_asset.kind == "file":
            if declared_paths != {expected_asset.staged_path}:
                raise RecoveryError("file inventory is invalid")
        actual = _tree_file_paths(
            recovery_root / expected_asset.staged_path.split("/", 1)[0], recovery_root
        )
        if actual != declared_paths:
            raise RecoveryError("restored asset tree does not match recovery metadata")


def _sqlite_snapshot_readonly(path: Path) -> tuple[str, str]:
    _require_regular(path, label="restored SQLite database")
    uri = f"file:{quote(str(path.resolve()), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            quick = [row[0] for row in connection.execute("PRAGMA quick_check")]
            integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    except sqlite3.Error as exc:
        raise RecoveryError("restored SQLite validation failed") from exc
    if quick != ["ok"] or integrity != ["ok"]:
        raise RecoveryError("restored SQLite quick_check or integrity_check failed")
    return "ok", "ok"


def _tree_file_paths(root: Path, recovery_root: Path) -> set[str]:
    _require_directory(root, label="restored Registry tree")
    found: set[str] = set()
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                mode = entry.stat(follow_symlinks=False).st_mode
                entry_path = Path(entry.path)
                if stat.S_ISLNK(mode) or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise RecoveryError("restored Registry tree contains a link or special file")
                if stat.S_ISDIR(mode):
                    stack.append(entry_path)
                else:
                    found.add(entry_path.relative_to(recovery_root).as_posix())
    return found


def verify_snapshot(
    *,
    snapshot_id: str,
    repository: str,
    expected_git_sha: str,
    expected_profile: str,
    password_file: Path | None = None,
    password_command: str | None = None,
    runner: ResticRunner = _run_subprocess,
    temporary_parent: Path | None = None,
) -> str:
    """Restore one exact Restic snapshot to temporary space and validate only our contract."""
    if not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise RecoveryError("snapshot ID must be exactly 64 lowercase hexadecimal characters")
    credentials = _credential_args(password_file, password_command)
    with tempfile.TemporaryDirectory(
        prefix="trader-assist-restore-", dir=temporary_parent
    ) as workspace:
        target = Path(workspace) / "restored"
        target.mkdir()
        command = [*_restic_prefix(repository, credentials),
            "restore",
            "--target",
            str(target),
            snapshot_id,
        ]
        result = runner(command)
        if result.returncode != 0:
            raise RecoveryError("Restic restore failed")
        metadata_paths = list(target.rglob("recovery-metadata.json"))
        if len(metadata_paths) != 1:
            raise RecoveryError("Restic restore did not produce exactly one recovery metadata file")
        _validate_restored_tree(
            metadata_paths[0].parent,
            expected_git_sha=expected_git_sha,
            expected_profile=expected_profile,
        )
    return "RESTIC_SNAPSHOT_RECOVERY_ARTIFACT_VERIFIED"


def check_repository(
    *,
    repository: str,
    password_file: Path | None = None,
    password_command: str | None = None,
    read_data: bool = False,
    runner: ResticRunner = _run_subprocess,
) -> None:
    """Run normal Restic check, or the separately selected full-data qualification."""
    credentials = _credential_args(password_file, password_command)
    command = [*_restic_prefix(repository, credentials), "check"]
    if read_data:
        command.append("--read-data")
    result = runner(command)
    if result.returncode != 0:
        raise RecoveryError("Restic repository check failed")
