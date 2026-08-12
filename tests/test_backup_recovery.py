"""Focused tests for the bounded, encrypted off-host backup helper."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tarfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trader_assist_v0.operations.backup_recovery import (
    BackupAsset,
    BackupRecoveryError,
    BackupRequest,
    CommandRunner,
    create_encrypted_backup,
    sqlite_integrity_metadata,
    upload_encrypted_backup,
    verify_remote_backup,
)

SHA = "ac6496596ebdb0b8c2b0a40753dbed1771a0c85d"
NOW = datetime(2026, 8, 12, 3, 4, 5, tzinfo=UTC)


class CopyingRunner(CommandRunner):
    """Test double standing in for age and rclone, never real cryptography."""

    def __init__(self, *, fail_rclone: bool = False) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail_rclone = fail_rclone

    def run(self, arguments: Sequence[str]) -> None:
        command = tuple(arguments)
        self.calls.append(command)
        if command[0] == "age":
            output = Path(command[command.index("-o") + 1])
            shutil.copyfile(Path(command[-1]), output)
        elif command[0] == "rclone":
            if self.fail_rclone:
                raise BackupRecoveryError("rclone command failed")
            shutil.copyfile(Path(command[-2]), Path(command[-1]))
        else:  # pragma: no cover - defensive assertion for a narrow fake
            raise AssertionError(command)


def _sqlite_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence(value) VALUES ('captured')")


def _request(tmp_path: Path) -> BackupRequest:
    database = tmp_path / "runtime.db"
    _sqlite_database(database)
    public_env = tmp_path / "public.env"
    public_env.write_text("NO_SECRET_PLACEHOLDER=configuration\n", encoding="utf-8")
    risk_configuration = tmp_path / "risk-configuration.json"
    risk_configuration.write_text('{"risk":"reviewed"}\n', encoding="utf-8")
    return BackupRequest(
        assets=(
            BackupAsset("sqlite", "runtime", database),
            BackupAsset("config", "public-env", public_env),
            BackupAsset("config", "risk-configuration", risk_configuration),
        ),
        encrypted_output=tmp_path / "artifacts" / "backup.tar.gz.age",
        repository="woshixiong/trader-assist-v0",
        deployed_sha=SHA,
        service_name="trader-assist-v0-public.service",
        python_executable="/opt/trader-assist-v0/venv/bin/python",
        storage_destination_class="independent-object-storage",
        age_recipient="age1testrecipient",
        created_at=NOW,
    )


def test_create_uses_online_backup_and_cleans_plaintext_workspace(tmp_path: Path) -> None:
    request = _request(tmp_path)
    source_before = request.assets[0].source_path.read_bytes()
    runner = CopyingRunner()

    artifact = create_encrypted_backup(request, runner=runner)

    assert request.assets[0].source_path.read_bytes() == source_before
    assert artifact.encrypted_path.is_file()
    assert artifact.database_count == 1
    assert not list(artifact.encrypted_path.parent.glob(".backup-build-*"))
    assert runner.calls[0][0] == "age"
    with tarfile.open(artifact.encrypted_path, mode="r:gz") as archive:
        names = sorted(member.name for member in archive.getmembers() if member.isfile())
    assert names == [
        "SHA256SUMS",
        "config/public-env",
        "config/risk-configuration",
        "database/runtime.db",
        "manifest.json",
    ]


def test_manifest_has_hashes_but_never_configuration_contents(tmp_path: Path) -> None:
    request = _request(tmp_path)
    secret_like_text = "this-must-stay-inside-the-encrypted-payload"
    request.assets[1].source_path.write_text(secret_like_text, encoding="utf-8")

    artifact = create_encrypted_backup(request, runner=CopyingRunner())

    with tarfile.open(artifact.encrypted_path, mode="r:gz") as archive:
        manifest_file = archive.extractfile("manifest.json")
        assert manifest_file is not None
        manifest_bytes = manifest_file.read()
        manifest = json.loads(manifest_bytes)
        config_payload = archive.extractfile("config/public-env").read().decode("utf-8")
    manifest_text = json.dumps(manifest, sort_keys=True)
    assert secret_like_text not in manifest_text
    assert secret_like_text in config_payload
    assert manifest["encryption_method"] == "age-external-tool"
    assert manifest["assets"][0]["sqlite"]["integrity_check"] == "ok"
    assert artifact.manifest_sha256 == hashlib.sha256(manifest_bytes).hexdigest()


def test_missing_required_asset_keeps_no_artifact(tmp_path: Path) -> None:
    request = _request(tmp_path)
    request.assets[2].source_path.unlink()

    with pytest.raises(BackupRecoveryError, match="required backup asset"):
        create_encrypted_backup(request, runner=CopyingRunner())

    assert not request.encrypted_output.exists()


def test_invalid_database_fails_read_only_integrity_check(tmp_path: Path) -> None:
    damaged = tmp_path / "damaged.db"
    damaged.write_bytes(b"not a sqlite database")

    with pytest.raises(BackupRecoveryError, match="integrity"):
        sqlite_integrity_metadata(damaged)


def test_upload_failure_leaves_existing_remote_copy_untouched(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.age"
    artifact.write_bytes(b"new encrypted data")
    remote = tmp_path / "remote.age"
    remote.write_bytes(b"previous good encrypted data")

    with pytest.raises(BackupRecoveryError, match="rclone"):
        upload_encrypted_backup(artifact, str(remote), runner=CopyingRunner(fail_rclone=True))

    assert remote.read_bytes() == b"previous good encrypted data"


def test_download_decrypt_and_read_only_restore_verification(tmp_path: Path) -> None:
    request = _request(tmp_path)
    runner = CopyingRunner()
    artifact = create_encrypted_backup(request, runner=runner)
    remote = tmp_path / "remote-copy.age"
    upload_encrypted_backup(artifact.encrypted_path, str(remote), runner=runner)
    identity = tmp_path / "test-age-identity.txt"
    identity.write_text("test-only identity placeholder\n", encoding="utf-8")

    result = verify_remote_backup(
        remote_source=str(remote),
        expected_encrypted_sha256=artifact.encrypted_sha256,
        age_identity_file=identity,
        workspace_parent=tmp_path / "restore-workspaces",
        runner=runner,
    )

    assert result == {"database_count": 1, "restore_verification": "PASS"}
    assert not list((tmp_path / "restore-workspaces").glob(".backup-restore-*"))
    assert any(call[0] == "rclone" for call in runner.calls)
    assert any(call[:2] == ("age", "-d") for call in runner.calls)


def test_download_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    request = _request(tmp_path)
    artifact = create_encrypted_backup(request, runner=CopyingRunner())
    identity = tmp_path / "test-age-identity.txt"
    identity.write_text("test-only identity placeholder\n", encoding="utf-8")

    with pytest.raises(BackupRecoveryError, match="checksum"):
        verify_remote_backup(
            remote_source=str(artifact.encrypted_path),
            expected_encrypted_sha256="0" * 64,
            age_identity_file=identity,
            workspace_parent=tmp_path / "restore-workspaces",
            runner=CopyingRunner(),
        )


def test_corrupted_download_fails_before_a_restore_claim(tmp_path: Path) -> None:
    remote = tmp_path / "corrupted-remote.age"
    remote.write_bytes(b"not an archive")
    identity = tmp_path / "test-age-identity.txt"
    identity.write_text("test-only identity placeholder\n", encoding="utf-8")

    with pytest.raises(BackupRecoveryError, match="archive"):
        verify_remote_backup(
            remote_source=str(remote),
            expected_encrypted_sha256=hashlib.sha256(remote.read_bytes()).hexdigest(),
            age_identity_file=identity,
            workspace_parent=tmp_path / "restore-workspaces",
            runner=CopyingRunner(),
        )
