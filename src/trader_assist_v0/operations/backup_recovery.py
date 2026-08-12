"""Consistent SQLite backup packaging and offline restore verification.

This is deliberately a small adapter around maintained command-line tools.  It
uses ``sqlite3.Connection.backup`` for a consistent copy of a live SQLite
database, while ``age`` performs encryption and ``rclone`` performs off-host
transfer.  The module neither configures either tool nor reads credentials.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol

BACKUP_FORMAT_VERSION = "1"
RESTORE_INSTRUCTIONS_VERSION = "1"


class BackupRecoveryError(RuntimeError):
    """Raised when a backup or restore verification is not safe to claim as successful."""


class CommandRunner(Protocol):
    """Narrow boundary for maintained encryption and transfer commands."""

    def run(self, arguments: Sequence[str]) -> None: ...


class SubprocessCommandRunner:
    """Run a command without a shell or command-output logging."""

    def run(self, arguments: Sequence[str]) -> None:
        try:
            subprocess.run(list(arguments), check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            executable = arguments[0] if arguments else "external command"
            raise BackupRecoveryError(f"{executable} command failed") from exc


@dataclass(frozen=True)
class BackupAsset:
    """One required, non-secretly named backup input.

    ``role`` is either ``sqlite`` or ``config``.  Configuration bytes are
    encrypted inside the package but are intentionally never represented in
    the plaintext manifest.
    """

    role: str
    name: str
    source_path: Path

    def archive_path(self) -> PurePosixPath:
        if self.role == "sqlite":
            suffix = ".db"
            directory = "database"
        elif self.role == "config":
            suffix = ""
            directory = "config"
        else:
            raise BackupRecoveryError("backup asset role must be sqlite or config")
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_"
        if not self.name or any(character not in allowed for character in self.name):
            raise BackupRecoveryError(
                "backup asset name must be lowercase ASCII, digits, hyphen, or underscore"
            )
        return PurePosixPath(directory, f"{self.name}{suffix}")


@dataclass(frozen=True)
class BackupRequest:
    assets: tuple[BackupAsset, ...]
    encrypted_output: Path
    repository: str
    deployed_sha: str
    service_name: str
    python_executable: str
    storage_destination_class: str
    age_recipient: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class BackupArtifact:
    encrypted_path: Path
    encrypted_sha256: str
    created_at: datetime
    manifest_sha256: str
    database_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_utc(value: datetime | None) -> datetime:
    now = datetime.now(tz=UTC) if value is None else value
    if now.tzinfo is not UTC:
        raise BackupRecoveryError("backup timestamp must be UTC")
    return now


def _required_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise BackupRecoveryError(f"{label} must be a non-empty text value")
    return value


def _validated_assets(assets: Iterable[BackupAsset]) -> tuple[BackupAsset, ...]:
    result = tuple(assets)
    if not result:
        raise BackupRecoveryError("at least one SQLite database is required")
    archive_paths: set[PurePosixPath] = set()
    sqlite_count = 0
    for asset in result:
        archive_path = asset.archive_path()
        if archive_path in archive_paths:
            raise BackupRecoveryError("backup asset names must be unique within a role")
        archive_paths.add(archive_path)
        path = asset.source_path.resolve()
        if not path.is_file() or path.is_symlink():
            raise BackupRecoveryError(f"required backup asset is not a regular file: {asset.name}")
        if asset.role == "sqlite":
            sqlite_count += 1
    if sqlite_count == 0:
        raise BackupRecoveryError("at least one SQLite database is required")
    return result


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def sqlite_integrity_metadata(path: Path) -> dict[str, int | str]:
    """Open a database read-only and return only non-secret integrity metadata."""
    try:
        with _read_only_connection(path) as connection:
            quick_check = [str(row[0]) for row in connection.execute("PRAGMA quick_check")]
            integrity_check = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
            if quick_check != ["ok"] or integrity_check != ["ok"]:
                raise BackupRecoveryError("SQLite quick_check or integrity_check did not return ok")
            return {
                "quick_check": "ok",
                "integrity_check": "ok",
                "page_count": int(connection.execute("PRAGMA page_count").fetchone()[0]),
                "schema_version": int(connection.execute("PRAGMA schema_version").fetchone()[0]),
                "user_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            }
    except sqlite3.Error as exc:
        raise BackupRecoveryError("SQLite read-only integrity verification failed") from exc


def consistent_sqlite_backup(source_path: Path, destination_path: Path) -> None:
    """Create a SQLite-consistent copy without writing to ``source_path``."""
    try:
        with (
            _read_only_connection(source_path) as source,
            sqlite3.connect(destination_path) as destination,
        ):
            source.backup(destination)
    except sqlite3.Error as exc:
        raise BackupRecoveryError("SQLite online backup failed") from exc


def _manifest_bytes(
    *,
    request: BackupRequest,
    created_at: datetime,
    copied_assets: tuple[tuple[BackupAsset, Path], ...],
    database_metadata: dict[str, dict[str, int | str]],
) -> bytes:
    records: list[dict[str, object]] = []
    for asset, copied_path in copied_assets:
        record: dict[str, object] = {
            "archive_path": str(asset.archive_path()),
            "name": asset.name,
            "role": asset.role,
            "sha256": _sha256(copied_path),
            "source_path": str(asset.source_path.resolve()),
            "size_bytes": copied_path.stat().st_size,
        }
        if asset.role == "sqlite":
            record["sqlite"] = database_metadata[asset.name]
        records.append(record)
    manifest = {
        "assets": records,
        "backup_created_at_utc": created_at.isoformat(),
        "backup_format_version": BACKUP_FORMAT_VERSION,
        "backup_method": "python-stdlib-sqlite-online-backup-api",
        "deployed_sha": request.deployed_sha,
        "encryption_method": "age-external-tool",
        "python_executable": request.python_executable,
        "repository": request.repository,
        "restore_instructions_version": RESTORE_INSTRUCTIONS_VERSION,
        "service_name": request.service_name,
        "storage_destination_class": request.storage_destination_class,
    }
    return (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _write_sha256sums(staging: Path, files: Sequence[Path]) -> Path:
    sums_path = staging / "SHA256SUMS"
    lines = [f"{_sha256(path)}  {path.relative_to(staging).as_posix()}\n" for path in files]
    sums_path.write_text("".join(sorted(lines)), encoding="utf-8")
    return sums_path


def _write_archive(staging: Path, archive_path: Path) -> None:
    files = sorted(
        (path for path in staging.rglob("*") if path.is_file()), key=lambda item: str(item)
    )
    with tarfile.open(archive_path, mode="w:gz") as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(staging).as_posix(), recursive=False)


def create_encrypted_backup(
    request: BackupRequest, *, runner: CommandRunner | None = None
) -> BackupArtifact:
    """Build, validate, package, encrypt, and clear the local plaintext workspace.

    Transfer remains intentionally separate, so a failed transfer cannot remove
    the newly-created encrypted artifact or an earlier known-good remote copy.
    """
    assets = _validated_assets(request.assets)
    created_at = _safe_utc(request.created_at)
    for value, label in (
        (request.repository, "repository"),
        (request.deployed_sha, "deployed SHA"),
        (request.service_name, "service name"),
        (request.python_executable, "Python executable"),
        (request.storage_destination_class, "storage destination class"),
        (request.age_recipient, "age recipient"),
    ):
        _required_text(value, label)
    if len(request.deployed_sha) != 40 or any(
        char not in "0123456789abcdef" for char in request.deployed_sha
    ):
        raise BackupRecoveryError("deployed SHA must be a lowercase 40-character Git SHA")
    output = request.encrypted_output.resolve()
    if output.exists():
        raise BackupRecoveryError(
            "encrypted output already exists; refusing to overwrite an artifact"
        )
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    active_runner = runner if runner is not None else SubprocessCommandRunner()
    workspace = Path(tempfile.mkdtemp(prefix=".backup-build-", dir=output.parent))
    try:
        staging = workspace / "package"
        staging.mkdir(mode=0o700)
        copied_assets: list[tuple[BackupAsset, Path]] = []
        database_metadata: dict[str, dict[str, int | str]] = {}
        for asset in assets:
            target = staging / asset.archive_path()
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if asset.role == "sqlite":
                consistent_sqlite_backup(asset.source_path, target)
                database_metadata[asset.name] = sqlite_integrity_metadata(target)
            else:
                shutil.copyfile(asset.source_path, target)
            os.chmod(target, 0o600)
            copied_assets.append((asset, target))
        manifest_path = staging / "manifest.json"
        manifest_path.write_bytes(
            _manifest_bytes(
                request=request,
                created_at=created_at,
                copied_assets=tuple(copied_assets),
                database_metadata=database_metadata,
            )
        )
        os.chmod(manifest_path, 0o600)
        payload_files = [path for _, path in copied_assets] + [manifest_path]
        _write_sha256sums(staging, payload_files)
        archive_path = workspace / "backup.tar.gz"
        _write_archive(staging, archive_path)
        active_runner.run(
            ("age", "-r", request.age_recipient, "-o", str(output), str(archive_path))
        )
        if not output.is_file():
            raise BackupRecoveryError("age did not create the encrypted artifact")
        os.chmod(output, 0o600)
        return BackupArtifact(
            encrypted_path=output,
            encrypted_sha256=_sha256(output),
            created_at=created_at,
            manifest_sha256=_sha256(manifest_path),
            database_count=len(database_metadata),
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def upload_encrypted_backup(
    artifact_path: Path, remote_destination: str, *, runner: CommandRunner | None = None
) -> None:
    """Copy an already-encrypted artifact with rclone; never delete remote objects."""
    artifact = artifact_path.resolve()
    if not artifact.is_file():
        raise BackupRecoveryError("encrypted backup artifact is missing")
    _required_text(remote_destination, "remote destination")
    active_runner = runner if runner is not None else SubprocessCommandRunner()
    active_runner.run(("rclone", "copyto", str(artifact), remote_destination))


def _safe_extract(archive_path: Path, target_directory: Path) -> None:
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = archive.getmembers()
            for member in members:
                member_path = PurePosixPath(member.name)
                if (
                    not member.isfile()
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                    or member_path == PurePosixPath(".")
                ):
                    raise BackupRecoveryError("backup archive contains an unsafe member")
            for member in members:
                archive.extract(member, path=target_directory, set_attrs=False, filter="data")
    except tarfile.TarError as exc:
        raise BackupRecoveryError("backup archive cannot be safely read") from exc


def _load_verified_manifest(extracted_directory: Path) -> dict[str, object]:
    manifest_path = extracted_directory / "manifest.json"
    sums_path = extracted_directory / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise BackupRecoveryError("backup archive lacks manifest or SHA256SUMS")
    expected: dict[str, str] = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", maxsplit=1)
        if len(parts) != 2 or len(parts[0]) != 64:
            raise BackupRecoveryError("SHA256SUMS is malformed")
        expected[parts[1]] = parts[0]
    for relative_name, expected_hash in expected.items():
        relative = PurePosixPath(relative_name)
        if relative.is_absolute() or ".." in relative.parts:
            raise BackupRecoveryError("SHA256SUMS contains an unsafe path")
        candidate = extracted_directory.joinpath(*relative.parts)
        if not candidate.is_file() or _sha256(candidate) != expected_hash:
            raise BackupRecoveryError("backup payload checksum verification failed")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupRecoveryError("manifest is not valid JSON") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("backup_format_version") != BACKUP_FORMAT_VERSION
    ):
        raise BackupRecoveryError("manifest format version is unsupported")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise BackupRecoveryError("manifest assets are invalid")
    for asset in assets:
        if not isinstance(asset, dict):
            raise BackupRecoveryError("manifest asset is invalid")
        archive_path = asset.get("archive_path")
        asset_hash = asset.get("sha256")
        if not isinstance(archive_path, str) or not isinstance(asset_hash, str):
            raise BackupRecoveryError("manifest asset hash is invalid")
        if expected.get(archive_path) != asset_hash:
            raise BackupRecoveryError("manifest asset hash does not match SHA256SUMS")
    return manifest


def verify_remote_backup(
    *,
    remote_source: str,
    expected_encrypted_sha256: str,
    age_identity_file: Path,
    workspace_parent: Path,
    runner: CommandRunner | None = None,
) -> dict[str, int | str]:
    """Download a new copy, decrypt it, and verify every declared SQLite database read-only."""
    _required_text(remote_source, "remote source")
    if len(expected_encrypted_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in expected_encrypted_sha256
    ):
        raise BackupRecoveryError("expected encrypted SHA256 is invalid")
    if not age_identity_file.is_file():
        raise BackupRecoveryError("age identity file is missing")
    parent = workspace_parent.resolve()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    active_runner = runner if runner is not None else SubprocessCommandRunner()
    workspace = Path(tempfile.mkdtemp(prefix=".backup-restore-", dir=parent))
    try:
        downloaded = workspace / "downloaded-backup.age"
        decrypted = workspace / "backup.tar.gz"
        extracted = workspace / "extracted"
        extracted.mkdir(mode=0o700)
        active_runner.run(("rclone", "copyto", remote_source, str(downloaded)))
        if not downloaded.is_file() or _sha256(downloaded) != expected_encrypted_sha256:
            raise BackupRecoveryError("downloaded encrypted artifact checksum verification failed")
        active_runner.run(
            ("age", "-d", "-i", str(age_identity_file), "-o", str(decrypted), str(downloaded))
        )
        if not decrypted.is_file():
            raise BackupRecoveryError("age did not create the decrypted archive")
        _safe_extract(decrypted, extracted)
        manifest = _load_verified_manifest(extracted)
        assets = manifest.get("assets")
        if not isinstance(assets, list):
            raise BackupRecoveryError("manifest assets are invalid")
        database_count = 0
        for asset in assets:
            if not isinstance(asset, dict) or asset.get("role") != "sqlite":
                continue
            archive_name = asset.get("archive_path")
            if not isinstance(archive_name, str):
                raise BackupRecoveryError("manifest SQLite asset path is invalid")
            database_path = extracted.joinpath(*PurePosixPath(archive_name).parts)
            sqlite_integrity_metadata(database_path)
            database_count += 1
        if database_count == 0:
            raise BackupRecoveryError("manifest does not declare a SQLite database")
        return {"database_count": database_count, "restore_verification": "PASS"}
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
