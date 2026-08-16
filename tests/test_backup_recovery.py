from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

from trader_assist_v0.operations.backup_recovery import (
    _FIRST_LAUNCH_PUBLIC_ENV,
    _FIRST_LAUNCH_RISK_CONFIG,
    _FIRST_LAUNCH_RUNTIME,
    FIRST_LAUNCH_PROFILE,
    FULL_MULTI_ASSET_PROFILE,
    METADATA_SCHEMA,
    REPOSITORY_IDENTITY,
    THREE_SETUP_PROFILE,
    BackupEvidence,
    CommandResult,
    RecoveryError,
    RecoveryPaths,
    _backup_recovery,
    _canonical_json,
    _RecoveryPaths,
    _stage,
    backup_recovery,
    check_repository,
    verify_snapshot,
)

SHA = "a" * 40
SNAPSHOT_ID = "b" * 64


def _database(path: Path, value: str = "one") -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE records (value TEXT NOT NULL)")
        connection.execute("INSERT INTO records VALUES (?)", (value,))


def _paths(tmp_path: Path, *, full: bool = False) -> _RecoveryPaths:
    tmp_path.mkdir(parents=True, exist_ok=True)
    runtime = tmp_path / "runtime.db"
    _database(runtime, "runtime")
    public = tmp_path / "public.env"
    public.write_text("PUBLIC_SETTING=yes\n", encoding="utf-8")
    risk = tmp_path / "risk.json"
    risk.write_text('{"risk":"bounded"}\n', encoding="utf-8")
    if not full:
        return _RecoveryPaths(runtime, public, risk)
    evidence = tmp_path / "evidence.db"
    _database(evidence, "evidence")
    registry = tmp_path / "registry"
    (registry / "versions").mkdir(parents=True)
    (registry / "versions" / "one.json").write_text('{"version":"one"}\n', encoding="utf-8")
    (registry / "history").mkdir()
    (registry / "history" / "prior.json").write_text("{}\n", encoding="utf-8")
    return _RecoveryPaths(runtime, public, risk, evidence, registry)


def _operator_cli_module() -> object:
    script = Path(__file__).parents[1] / "scripts" / "first_launch_backup_recovery.py"
    spec = importlib.util.spec_from_file_location("first_launch_backup_recovery", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _stage_profile(tmp_path: Path, *, full: bool = False) -> Path:
    root = tmp_path / "staging"
    root.mkdir(parents=True)
    return _stage(
        FULL_MULTI_ASSET_PROFILE if full else FIRST_LAUNCH_PROFILE,
        _paths(tmp_path / "source", full=full),
        SHA,
        root,
    )


def _metadata(root: Path) -> dict[str, object]:
    return json.loads((root / "recovery-metadata.json").read_text(encoding="utf-8"))


def _summary(snapshot_id: str = SNAPSHOT_ID) -> str:
    return json.dumps({"message_type": "summary", "snapshot_id": snapshot_id}) + "\n"


def test_normal_sqlite_snapshot_metadata_and_source_unchanged(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    before = paths.first_launch_runtime.read_bytes()
    root = _stage(FIRST_LAUNCH_PROFILE, paths, SHA, tmp_path / "staging")
    with sqlite3.connect(root / "first-launch-runtime" / "database.sqlite") as connection:
        assert connection.execute("SELECT value FROM records").fetchone() == ("runtime",)
    assert paths.first_launch_runtime.read_bytes() == before
    metadata = _metadata(root)
    assert metadata["schema"] == METADATA_SCHEMA
    assert metadata["repository_identity"] == REPOSITORY_IDENTITY
    assert metadata["deployed_git_sha"] == SHA
    assert [asset["logical_id"] for asset in metadata["assets"]] == [
        "first-launch-runtime",
        "first-launch-public-env",
        "first-launch-risk-config",
    ]
    assert metadata["per_database_consistency"] is True
    assert metadata["cross_database_atomic_snapshot"] is False
    sqlite = metadata["assets"][0]
    assert sqlite["sqlite_validation"]["quick_check"] == "ok"
    assert sqlite["sqlite_validation"]["integrity_check"] == "ok"


def test_live_wal_snapshot_includes_committed_data_without_source_change(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    connection = sqlite3.connect(paths.first_launch_runtime)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("INSERT INTO records VALUES ('wal-data')")
    connection.commit()
    before = paths.first_launch_runtime.read_bytes()
    wal_path = paths.first_launch_runtime.with_name(f"{paths.first_launch_runtime.name}-wal")
    wal_before = wal_path.read_bytes()
    root = tmp_path / "staging"
    root.mkdir()
    try:
        staged = _stage(FIRST_LAUNCH_PROFILE, paths, SHA, root)
    finally:
        connection.close()
    with sqlite3.connect(staged / "first-launch-runtime" / "database.sqlite") as copied:
        assert copied.execute("SELECT value FROM records ORDER BY value").fetchall() == [
            ("runtime",),
            ("wal-data",),
        ]
    assert paths.first_launch_runtime.read_bytes() == before
    assert wal_path.read_bytes() == wal_before


def test_corrupt_sqlite_fails_and_two_databases_record_sequential_capture(tmp_path: Path) -> None:
    paths = _paths(tmp_path, full=True)
    root = tmp_path / "staging"
    root.mkdir()
    staged = _stage(FULL_MULTI_ASSET_PROFILE, paths, SHA, root)
    metadata = _metadata(staged)
    sqlite_entries = [item for item in metadata["assets"] if item["type"] == "sqlite"]
    assert [item["sqlite_validation"]["capture_order"] for item in sqlite_entries] == [1, 4]
    assert metadata["cross_database_atomic_snapshot"] is False
    paths.first_launch_runtime.write_bytes(b"not a sqlite database")
    broken = tmp_path / "broken"
    broken.mkdir()
    with pytest.raises(RecoveryError, match="SQLite"):
        _stage(
            FIRST_LAUNCH_PROFILE,
            _RecoveryPaths(
                paths.first_launch_runtime,
                paths.first_launch_public_env,
                paths.first_launch_risk_config,
            ),
            SHA,
            broken,
        )


def test_fixed_asset_policy_requires_exact_profiles_and_no_extra_assets(tmp_path: Path) -> None:
    paths = _paths(tmp_path, full=True)
    with pytest.raises(RecoveryError, match="cannot include MultiAsset"):
        _stage(FIRST_LAUNCH_PROFILE, paths, SHA, tmp_path / "wrong-profile")
    incomplete = _RecoveryPaths(
        paths.first_launch_runtime,
        paths.first_launch_public_env,
        paths.first_launch_risk_config,
        paths.multi_asset_evidence,
    )
    with pytest.raises(RecoveryError, match="requires both"):
        _stage(FULL_MULTI_ASSET_PROFILE, incomplete, SHA, tmp_path / "incomplete")
    with pytest.raises(TypeError):
        _RecoveryPaths(  # type: ignore[call-arg]
            paths.first_launch_runtime,
            paths.first_launch_public_env,
            paths.first_launch_risk_config,
            arbitrary_extra_asset=tmp_path / "private-key",  # type: ignore[call-arg]
        )


def test_missing_asset_registry_tree_symlink_and_special_file_fail_closed(tmp_path: Path) -> None:
    paths = _paths(tmp_path, full=True)
    paths.first_launch_public_env.unlink()
    with pytest.raises(RecoveryError, match="missing"):
        _stage(FULL_MULTI_ASSET_PROFILE, paths, SHA, tmp_path / "missing")
    paths = _paths(tmp_path / "symlink", full=True)
    assert paths.multi_asset_registry is not None
    os.symlink(
        paths.multi_asset_registry / "versions" / "one.json", paths.multi_asset_registry / "bad"
    )
    with pytest.raises(RecoveryError, match="symlink"):
        _stage(FULL_MULTI_ASSET_PROFILE, paths, SHA, tmp_path / "symlink-stage")
    paths = _paths(tmp_path / "fifo", full=True)
    assert paths.multi_asset_registry is not None
    fifo = paths.multi_asset_registry / "bad-fifo"
    os.mkfifo(fifo)
    with pytest.raises(RecoveryError, match="special"):
        _stage(FULL_MULTI_ASSET_PROFILE, paths, SHA, tmp_path / "fifo-stage")


def test_full_profile_copies_nested_registry_regular_tree(tmp_path: Path) -> None:
    staged = _stage_profile(tmp_path, full=True)
    assert (staged / "multi-asset-registry" / "tree" / "versions" / "one.json").is_file()
    metadata = _metadata(staged)
    assert [asset["logical_id"] for asset in metadata["assets"]] == [
        "first-launch-runtime",
        "first-launch-public-env",
        "first-launch-risk-config",
        "multi-asset-evidence",
        "multi-asset-registry",
    ]
    registry = metadata["assets"][-1]
    assert [item["path"] for item in registry["files"]] == [
        "multi-asset-registry/tree/history/prior.json",
        "multi-asset-registry/tree/versions/one.json",
    ]


def test_three_setup_profile_has_exact_fixed_inventory_and_excludes_closed_bars(
    tmp_path: Path,
) -> None:
    source = _paths(tmp_path / "source")
    evidence = tmp_path / "evidence.sqlite"
    _database(evidence, "evidence")
    registry = tmp_path / "registry"
    (registry / "versions").mkdir(parents=True)
    (registry / "versions" / "one.json").write_text('{"version":"one"}\n', encoding="utf-8")
    config = tmp_path / "three-setup.json"
    config.write_text('{"schema":"three-setup"}\n', encoding="utf-8")
    staged = _stage(
        THREE_SETUP_PROFILE,
        _RecoveryPaths(
            source.first_launch_runtime,
            source.first_launch_public_env,
            source.first_launch_risk_config,
            three_setup_evidence=evidence,
            three_setup_registry=registry,
            three_setup_config=config,
        ),
        SHA,
        tmp_path / "staging",
    )
    metadata = _metadata(staged)
    assert [asset["logical_id"] for asset in metadata["assets"]] == [
        "three-setup-evidence",
        "three-setup-registry",
        "three-setup-config",
    ]
    assert "runtime.db" not in json.dumps(metadata)
    assert "closed-bars" not in json.dumps(metadata)


@pytest.mark.parametrize("bad_sha", ["A" * 40, "a" * 39, "a" * 41, "not-a-sha"])
def test_malformed_deployed_sha_is_rejected(tmp_path: Path, bad_sha: str) -> None:
    with pytest.raises(RecoveryError, match="Git SHA"):
        _stage(FIRST_LAUNCH_PROFILE, _paths(tmp_path), bad_sha, tmp_path / "stage")


def test_backup_uses_argv_json_snapshot_and_cleans_staging(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def runner(argv: object) -> CommandResult:
        commands.append(list(argv))
        return CommandResult(0, _summary())

    evidence = _backup_recovery(
        profile=FIRST_LAUNCH_PROFILE,
        paths=_paths(tmp_path),
        deployed_git_sha=SHA,
        repository="s3:https://example.invalid/recovery",
        password_file=tmp_path / "externally-managed-password",
        runner=runner,
        temporary_parent=tmp_path,
    )
    command = commands[0]
    assert evidence.snapshot_id == SNAPSHOT_ID
    assert command[:3] == ["restic", "--repo", "s3:https://example.invalid/recovery"]
    assert "--json" in command and "backup" in command
    assert "recovery-profile=first-launch" in command and f"git-sha={SHA}" in command
    assert not {"age", "rclone", "tar"} & set(command)
    assert not list(tmp_path.glob("trader-assist-recovery-*"))


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (CommandResult(1, _summary()), "backup failed"),
        (CommandResult(0, ""), "concrete snapshot_id"),
        (CommandResult(0, _summary("short")), "concrete snapshot_id"),
        (CommandResult(0, "not-json\n"), "valid JSON"),
    ],
)
def test_backup_fails_closed_and_cleans_staging(
    tmp_path: Path, result: CommandResult, message: str
) -> None:
    with pytest.raises(RecoveryError, match=message):
        _backup_recovery(
            profile=FIRST_LAUNCH_PROFILE,
            paths=_paths(tmp_path),
            deployed_git_sha=SHA,
            repository="rest:https://example.invalid/",
            password_file=tmp_path / "password-file",
            runner=lambda _argv: result,
            temporary_parent=tmp_path,
        )
    assert not list(tmp_path.glob("trader-assist-recovery-*"))


@pytest.mark.parametrize(
    ("argument", "secret_path"),
    [
        ("first_launch_public_env", "/secure/notification-credential"),
        ("first_launch_runtime", "/secure/restic-password"),
        ("first_launch_risk_config", "/secure/backend-private-key"),
    ],
)
def test_public_api_rejects_first_launch_secret_path_substitution(
    argument: str, secret_path: str
) -> None:
    with pytest.raises(TypeError):
        RecoveryPaths(**{argument: Path(secret_path)})  # type: ignore[call-arg]


def test_public_api_uses_fixed_first_launch_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    recovery = importlib.import_module("trader_assist_v0.operations.backup_recovery")

    staged_paths: list[_RecoveryPaths] = []

    def stage(
        profile: str, paths: _RecoveryPaths, deployed_git_sha: str, staging_root: Path
    ) -> Path:
        assert profile == FIRST_LAUNCH_PROFILE and deployed_git_sha == SHA
        staged_paths.append(paths)
        root = staging_root / "recovery"
        root.mkdir()
        return root

    monkeypatch.setattr(recovery, "_stage", stage)
    backup_recovery(
        profile=FIRST_LAUNCH_PROFILE,
        paths=RecoveryPaths(),
        deployed_git_sha=SHA,
        repository="repo",
        password_file=tmp_path / "password",
        runner=lambda _argv: CommandResult(0, _summary()),
        temporary_parent=tmp_path,
    )
    assert staged_paths == [
        _RecoveryPaths(_FIRST_LAUNCH_RUNTIME, _FIRST_LAUNCH_PUBLIC_ENV, _FIRST_LAUNCH_RISK_CONFIG)
    ]


@pytest.mark.parametrize(
    "argument",
    [
        "--first-launch-runtime",
        "--first-launch-public-env",
        "--first-launch-risk-config",
    ],
)
def test_operator_cli_rejects_first_launch_path_override(
    monkeypatch: pytest.MonkeyPatch, argument: str
) -> None:
    cli = _operator_cli_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "first_launch_backup_recovery.py",
            "backup",
            "--repository",
            "repo",
            "--deployed-git-sha",
            SHA,
            "--profile",
            FIRST_LAUNCH_PROFILE,
            "--restic-password-file",
            "/secure/password",
            argument,
            "/secure/secret",
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        cli.main()


def test_operator_cli_accepts_explicit_multi_asset_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cli = _operator_cli_module()
    captured: dict[str, object] = {}

    def fake_backup(**kwargs: object) -> BackupEvidence:
        captured.update(kwargs)
        return BackupEvidence(SNAPSHOT_ID, FULL_MULTI_ASSET_PROFILE, SHA)

    monkeypatch.setattr(cli, "backup_recovery", fake_backup)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "first_launch_backup_recovery.py",
            "backup",
            "--repository",
            "repo",
            "--deployed-git-sha",
            SHA,
            "--profile",
            FULL_MULTI_ASSET_PROFILE,
            "--restic-password-file",
            str(tmp_path / "password"),
            "--multi-asset-evidence",
            str(tmp_path / "evidence.db"),
            "--multi-asset-registry",
            str(tmp_path / "registry"),
        ],
    )
    cli.main()
    assert captured["paths"] == RecoveryPaths(
        multi_asset_evidence=tmp_path / "evidence.db",
        multi_asset_registry=tmp_path / "registry",
    )


def _restore_runner(template: Path, commands: list[list[str]], *, result: int = 0):
    def runner(argv: object) -> CommandResult:
        command = list(argv)
        commands.append(command)
        if result == 0:
            target = Path(command[command.index("--target") + 1])
            shutil.copytree(template, target / "recovery")
        return CommandResult(result)

    return runner


def test_restore_validates_exact_snapshot_and_cleans_workspace(tmp_path: Path) -> None:
    template = _stage_profile(tmp_path / "template")
    commands: list[list[str]] = []
    status = verify_snapshot(
        snapshot_id=SNAPSHOT_ID,
        repository="sftp:user@example.invalid:/repo",
        expected_git_sha=SHA,
        expected_profile=FIRST_LAUNCH_PROFILE,
        password_file=tmp_path / "recovery-password",
        runner=_restore_runner(template, commands),
        temporary_parent=tmp_path,
    )
    assert status == "RESTIC_SNAPSHOT_RECOVERY_ARTIFACT_VERIFIED"
    command = commands[0]
    assert command[-1] == SNAPSHOT_ID
    restore_index = command.index("restore")
    assert command[restore_index + 1 : restore_index + 3] == ["--target", command[-2]]
    assert not list(tmp_path.glob("trader-assist-restore-*"))


@pytest.mark.parametrize(
    ("edit", "profile", "message"),
    [
        (
            lambda root: _change_metadata(root, "deployed_git_sha", "c" * 40),
            FIRST_LAUNCH_PROFILE,
            "Git SHA",
        ),
        (
            lambda root: _change_metadata(root, "repository_identity", "other/repo"),
            FIRST_LAUNCH_PROFILE,
            "identity",
        ),
        (
            lambda root: _change_metadata(root, "recovery_profile", FULL_MULTI_ASSET_PROFILE),
            FIRST_LAUNCH_PROFILE,
            "profile",
        ),
        (lambda root: (root / "unexpected").mkdir(), FIRST_LAUNCH_PROFILE, "undeclared"),
    ],
)
def test_restore_rejects_wrong_metadata_or_undeclared_asset(
    tmp_path: Path, edit: object, profile: str, message: str
) -> None:
    template = _stage_profile(tmp_path / "template")
    edit(template)
    with pytest.raises(RecoveryError, match=message):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=profile,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, []),
            temporary_parent=tmp_path,
        )
    assert not list(tmp_path.glob("trader-assist-restore-*"))


def _change_metadata(root: Path, key: str, value: object) -> None:
    metadata = _metadata(root)
    metadata[key] = value
    (root / "recovery-metadata.json").write_bytes(_canonical_json(metadata))


def test_restore_rejects_hash_mismatch_inventory_and_restore_failure(tmp_path: Path) -> None:
    template = _stage_profile(tmp_path / "template")
    (template / "first-launch-public-env" / "file").write_text("changed", encoding="utf-8")
    with pytest.raises(RecoveryError, match="hash"):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=FIRST_LAUNCH_PROFILE,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, []),
        )
    with pytest.raises(RecoveryError, match="restore failed"):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=FIRST_LAUNCH_PROFILE,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, [], result=1),
            temporary_parent=tmp_path,
        )
    assert not list(tmp_path.glob("trader-assist-restore-*"))


def test_restore_requires_exact_inventory_sqlite_validation_and_registry_tree(
    tmp_path: Path,
) -> None:
    template = _stage_profile(tmp_path / "inventory", full=True)
    metadata = _metadata(template)
    metadata["assets"].pop()
    (template / "recovery-metadata.json").write_bytes(_canonical_json(metadata))
    with pytest.raises(RecoveryError, match="inventory"):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=FULL_MULTI_ASSET_PROFILE,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, []),
        )
    template = _stage_profile(tmp_path / "sqlite-validation")
    metadata = _metadata(template)
    metadata["assets"][0]["sqlite_validation"]["quick_check"] = "not-ok"
    (template / "recovery-metadata.json").write_bytes(_canonical_json(metadata))
    with pytest.raises(RecoveryError, match="SQLite validation"):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=FIRST_LAUNCH_PROFILE,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, []),
        )
    template = _stage_profile(tmp_path / "registry", full=True)
    extra = template / "multi-asset-registry" / "tree" / "extra.json"
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RecoveryError, match="tree"):
        verify_snapshot(
            snapshot_id=SNAPSHOT_ID,
            repository="repo",
            expected_git_sha=SHA,
            expected_profile=FULL_MULTI_ASSET_PROFILE,
            password_file=tmp_path / "password",
            runner=_restore_runner(template, []),
        )


def test_check_and_deep_check_are_separate_and_fail_closed(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def runner(argv: object) -> CommandResult:
        commands.append(list(argv))
        return CommandResult(0)

    check_repository(repository="repo", password_file=tmp_path / "password", runner=runner)
    check_repository(
        repository="repo", password_file=tmp_path / "password", read_data=True, runner=runner
    )
    assert commands[0][-1] == "check"
    assert commands[1][-2:] == ["check", "--read-data"]
    with pytest.raises(RecoveryError, match="check failed"):
        check_repository(
            repository="repo",
            password_file=tmp_path / "password",
            runner=lambda _argv: CommandResult(99),
        )


def test_metadata_excludes_restic_and_backend_credentials(tmp_path: Path) -> None:
    staged = _stage_profile(tmp_path)
    metadata = (staged / "recovery-metadata.json").read_text(encoding="utf-8")
    assert "password-file" not in metadata
    assert "backend-credential" not in metadata
    assert "RESTIC_PASSWORD" not in metadata
