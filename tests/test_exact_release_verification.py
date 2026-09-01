"""Offline exact-artifact identity and fail-closed guard acceptance."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.verify_exact_release import (
    ExactReleaseError,
    build_release_manifest,
    exact_clean_head,
    release_paths,
    verify_manifest,
    verify_staged_release,
)
from scripts.verify_exact_release import main as exact_release_main
from trader_assist_v0.multi_asset_shadow.production import THREE_SETUP_CONFIG_SCHEMA


def test_repository_release_surface_binds_source_locks_deployment_and_schema() -> None:
    root = Path(__file__).parents[1]
    paths = {path.relative_to(root).as_posix() for path in release_paths(root)}
    assert {
        "pyproject.toml",
        "requirements-runtime.lock",
        "requirements-dev.lock",
        "scripts/run_three_setup_shadow_runtime.py",
        "scripts/run_first_launch_public_runtime.py",
        "scripts/p4a/run_three_setup_shadow_runtime.sh",
        "deploy/p4a/config/three-setup-shadow.json.example",
        "deploy/p4a/systemd/trader-assist-v0-three-setup.env.example",
        "deploy/p4a/systemd/trader-assist-v0-three-setup.service",
        "src/trader_assist_v0/multi_asset_shadow/production.py",
    } <= paths
    manifest = build_release_manifest(root, release_sha="a" * 40)
    assert manifest["config_schema"] == THREE_SETUP_CONFIG_SCHEMA
    assert manifest["source_file_count"] == len(paths)
    verify_manifest(root, json.loads(json.dumps(manifest)), release_sha="a" * 40)


def test_three_setup_entrypoint_direct_script_imports_are_release_selected() -> None:
    root = Path(__file__).parents[1]
    entrypoint = root / "scripts/run_three_setup_shadow_runtime.py"
    parsed = ast.parse(entrypoint.read_text(encoding="utf-8"))
    direct_script_imports: set[str] = set()
    for node in ast.walk(parsed):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("scripts."):
                direct_script_imports.add(node.module.replace(".", "/") + ".py")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("scripts."):
                    direct_script_imports.add(alias.name.replace(".", "/") + ".py")

    assert "scripts/run_first_launch_public_runtime.py" in direct_script_imports
    selected_paths = {
        path.relative_to(root).as_posix() for path in release_paths(root)
    }
    assert direct_script_imports <= selected_paths


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_release_surface(root: Path) -> None:
    for relative in (
        "src/trader_assist_v0/example.py",
        "scripts/run_three_setup_shadow_runtime.py",
        "scripts/run_first_launch_public_runtime.py",
        "scripts/p4a/run_three_setup_shadow_runtime.sh",
        "deploy/p4a/systemd/trader-assist-v0-three-setup.env.example",
        "deploy/p4a/systemd/trader-assist-v0-three-setup.service",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    (root / "deploy/p4a/config").mkdir(parents=True, exist_ok=True)
    (root / "deploy/p4a/config/three-setup-shadow.json.example").write_text(
        json.dumps({"schema": THREE_SETUP_CONFIG_SCHEMA}), encoding="utf-8"
    )
    for relative in ("pyproject.toml", "requirements-runtime.lock", "requirements-dev.lock"):
        (root / relative).write_text(relative, encoding="utf-8")


@pytest.fixture
def staged_release(
    tmp_path: Path,
) -> tuple[Path, dict[str, object], str]:
    candidate_root = tmp_path / "candidate"
    candidate_root.mkdir()
    _write_release_surface(candidate_root)
    _git(candidate_root, "init")
    _git(candidate_root, "config", "user.email", "release-test@example.invalid")
    _git(candidate_root, "config", "user.name", "Release Test")
    _git(candidate_root, "add", ".")
    _git(candidate_root, "commit", "-m", "candidate")
    release_sha = _git(candidate_root, "rev-parse", "HEAD")

    manifest_path = tmp_path / "release-manifest.json"
    assert (
        exact_release_main(
            (
                "--root",
                str(candidate_root),
                "--expected-head",
                release_sha,
                "--output",
                str(manifest_path),
            )
        )
        == 0
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)

    staged_root = tmp_path / "staged"
    for source in release_paths(candidate_root):
        destination = staged_root / source.relative_to(candidate_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return staged_root, manifest, release_sha


def test_staged_non_git_release_accepts_retained_canonical_manifest(
    staged_release: tuple[Path, dict[str, object], str],
) -> None:
    staged_root, manifest, release_sha = staged_release
    assert not (staged_root / ".git").exists()
    verify_staged_release(
        staged_root, manifest, expected_release_sha=release_sha
    )


@pytest.mark.parametrize(
    ("attack", "expected_error"),
    (
        pytest.param("mutate", "content is mutated", id="mutated-selected-content"),
        pytest.param("delete", "missing selected content", id="deleted-selected-content"),
        pytest.param(
            "mutate-runtime-dependency",
            "content is mutated",
            id="mutated-production-script-dependency",
        ),
        pytest.param(
            "delete-runtime-dependency",
            "missing selected content",
            id="deleted-production-script-dependency",
        ),
        pytest.param(
            "expected-sha",
            "embedded release SHA does not match expected release SHA",
            id="explicit-expected-release-sha-mismatch",
        ),
        pytest.param(
            "embedded-sha",
            "embedded release SHA does not match expected release SHA",
            id="embedded-manifest-release-sha-mismatch",
        ),
        pytest.param(
            "extra-selected-path",
            "selected path set does not match retained manifest",
            id="extra-selected-path",
        ),
    ),
)
def test_staged_non_git_release_fails_closed(
    staged_release: tuple[Path, dict[str, object], str],
    attack: str,
    expected_error: str,
) -> None:
    staged_root, manifest, release_sha = staged_release
    selected_source = staged_root / "src/trader_assist_v0/example.py"
    runtime_dependency = staged_root / "scripts/run_first_launch_public_runtime.py"
    expected_release_sha = release_sha

    if attack == "mutate":
        selected_source.write_text("mutated\n", encoding="utf-8")
    elif attack == "delete":
        selected_source.unlink()
    elif attack == "mutate-runtime-dependency":
        runtime_dependency.write_text("mutated\n", encoding="utf-8")
    elif attack == "delete-runtime-dependency":
        runtime_dependency.unlink()
    elif attack == "expected-sha":
        expected_release_sha = "0" * 40
    elif attack == "embedded-sha":
        manifest["release_sha"] = "0" * 40
    elif attack == "extra-selected-path":
        extra = staged_root / "src/trader_assist_v0/extra.py"
        extra.write_text("extra\n", encoding="utf-8")

    with pytest.raises(ExactReleaseError, match=expected_error):
        verify_staged_release(
            staged_root, manifest, expected_release_sha=expected_release_sha
        )


def test_exact_release_guard_rejects_dirty_or_wrong_head(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "release-test@example.invalid")
    _git(tmp_path, "config", "user.name", "Release Test")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("candidate\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "candidate")
    head = _git(tmp_path, "rev-parse", "HEAD")
    assert exact_clean_head(tmp_path, expected_head=head) == head
    with pytest.raises(ExactReleaseError, match="does not match"):
        exact_clean_head(tmp_path, expected_head="0" * 40)
    tracked.write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ExactReleaseError, match="must be clean"):
        exact_clean_head(tmp_path, expected_head=head)


def test_release_manifest_detects_any_selected_file_change(tmp_path: Path) -> None:
    _write_release_surface(tmp_path)
    first = build_release_manifest(tmp_path, release_sha="b" * 40)
    (tmp_path / "src/trader_assist_v0/example.py").write_text("changed", encoding="utf-8")
    second = build_release_manifest(tmp_path, release_sha="b" * 40)
    assert first["manifest_sha256"] != second["manifest_sha256"]
