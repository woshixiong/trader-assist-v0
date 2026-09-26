from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "v5_bootstrap", ROOT / "scripts/control/v5_bootstrap.py"
)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


def git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, text=True, capture_output=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-b", "main", str(repo))
    git(repo, "config", "user.email", "x@y.z")
    git(repo, "config", "user.name", "x")
    (repo / "x").write_text("x")
    git(repo, "add", "x")
    git(repo, "commit", "-m", "x")
    return repo


def args(repo: Path) -> argparse.Namespace:
    head = git(repo, "rev-parse", "HEAD")
    epoch = "a" * 64
    packet = "b" * 64
    return argparse.Namespace(
        repository=str(repo),
        exact_base=head,
        exact_tree=git(repo, "rev-parse", "HEAD^{tree}"),
        task_packet_hash=packet,
        governance_epoch=epoch,
        preflight_binding_key=bootstrap.binding_key(epoch, packet, head, "CODEX_CLI"),
        control_capsule_ref="issue",
        package_state_locator="comment:1",
        execution_surface="CODEX_CLI",
        actual_execution_surface="CODEX_CLI",
        model="gpt-5.6-terra",
        actual_model="gpt-5.6-terra",
        reasoning="medium",
        actual_reasoning="medium",
        codex_thread_id="thread",
        actual_codex_thread_id="thread",
        worktree_identity=str(repo),
        actual_worktree_identity=str(repo),
        resume_required=True,
        resume_verifiable=True,
        output="json",
    )


def test_v5_bootstrap_exact_identity(repository: Path):
    assert bootstrap.verify(args(repository)).result == "PASS"


def test_v5_bootstrap_rejects_resume_substitution(repository: Path):
    value = args(repository)
    value.actual_codex_thread_id = "new"
    with pytest.raises(bootstrap.BootstrapError, match="PAUSED_CAPABILITY"):
        bootstrap.verify(value)
