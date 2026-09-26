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
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", str(bare))
    git(tmp_path, "init", "-b", "main", str(repo))
    git(repo, "config", "user.email", "x@y.z")
    git(repo, "config", "user.name", "x")
    (repo / "x").write_text("x")
    git(repo, "add", "x")
    git(repo, "commit", "-m", "x")
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-u", "origin", "main")
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
        actual_control_capsule_ref="issue",
        package_state_locator="comment:1",
        actual_package_state_locator="comment:1",
        package_state_verified="PASS",
        expected_origin=git(repo, "config", "--get", "remote.origin.url"),
        remote_ref="origin/main",
        freshen_remote=True,
        project_ruleset_preflight="PASS",
        engineering_preflight="PASS",
        semantic_readiness="PASS",
        active_governance="V4",
        semantic_phase="REPAIR_1",
        requested_executor="CODEX",
        actual_executor="CODEX",
        requested_provider="OPENAI",
        actual_provider="OPENAI",
        execution_surface="CODEX_CLI",
        actual_execution_surface="CODEX_CLI",
        model="gpt-5.6-terra",
        actual_model="gpt-5.6-terra",
        reasoning="medium",
        actual_reasoning="medium",
        requested_web_search="DISABLED",
        actual_web_search="DISABLED",
        requested_tool_state="GITHUB_CONNECTED",
        actual_tool_state="GITHUB_CONNECTED",
        requested_session_policy="EXACT_THREAD_RESUME",
        actual_session_policy="EXACT_THREAD_RESUME",
        requested_resource_state="NORMAL",
        actual_resource_state="NORMAL",
        requested_worktree_policy="EXACT_BASE_CLEAN",
        actual_worktree_policy="EXACT_BASE_CLEAN",
        requested_stdin_source="EXPLICIT",
        actual_stdin_source="EXPLICIT",
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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("freshen_remote", False, "fresh remote"),
        ("package_state_verified", "FAIL", "PACKAGE_STATE_VERIFIED"),
        ("actual_package_state_locator", "comment:2", "package-state locator"),
        ("actual_control_capsule_ref", "other", "Control Capsule"),
        ("actual_provider", "OTHER", "provider mismatch"),
        ("actual_stdin_source", "SHARED", "stdin source mismatch"),
    ],
)
def test_v5_bootstrap_rejects_incomplete_binding(
    repository: Path, field: str, value: object, message: str
):
    bound = args(repository)
    setattr(bound, field, value)
    with pytest.raises(bootstrap.BootstrapError, match=message):
        bootstrap.verify(bound)


def test_active_v4_repair2_route_precedence(repository: Path):
    bound = args(repository)
    bound.semantic_phase = "REPAIR_2"
    bound.model = bound.actual_model = "gpt-5.6-sol"
    assert bootstrap.verify(bound).model == "gpt-5.6-sol"
    bound.model = bound.actual_model = "gpt-6-sol"
    with pytest.raises(bootstrap.BootstrapError, match="active-V4 route precedence"):
        bootstrap.verify(bound)
