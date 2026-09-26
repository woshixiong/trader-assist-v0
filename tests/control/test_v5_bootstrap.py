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

CANONICAL_COMMENTS: dict[str, str] = {}


@pytest.fixture(autouse=True)
def canonical_comment_readback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bootstrap,
        "read_canonical_comment",
        lambda locator: CANONICAL_COMMENTS[locator],
    )


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
    locator = "https://github.com/example/repo/issues/250#issuecomment-1"
    bound = argparse.Namespace(
        repository=str(repo),
        exact_base=head,
        exact_tree=git(repo, "rev-parse", "HEAD^{tree}"),
        exact_main="c" * 40,
        package_base="d" * 40,
        package_id="V5-B",
        route="C",
        pr_number=251,
        task_packet_hash=packet,
        governance_epoch=epoch,
        preflight_binding_key=bootstrap.binding_key(epoch, packet, head, "CODEX_CLI"),
        control_capsule_ref=locator,
        package_state_locator=locator,
        expected_origin=git(repo, "config", "--get", "remote.origin.url"),
        remote_ref="origin/main",
        freshen_remote=True,
        project_ruleset_preflight="PASS",
        engineering_preflight="PASS",
        semantic_readiness="PASS",
        active_governance="V5",
        semantic_phase="IMPLEMENT",
        requested_executor="CODEX",
        actual_executor="CODEX",
        requested_provider="OPENAI",
        actual_provider="OPENAI",
        execution_surface="CODEX_CLI",
        actual_execution_surface="CODEX_CLI",
        model="gpt-6-sol",
        actual_model="gpt-6-sol",
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
    state = bootstrap._V5.PackageState(
        schema_version="1",
        revision=1,
        package_id=bound.package_id,
        governance_epoch=bound.governance_epoch,
        task_packet_hash=bound.task_packet_hash,
        exact_main=bound.exact_main,
        exact_base=bound.package_base,
        exact_head=bound.exact_base,
        exact_tree=bound.exact_tree,
        route=bound.route,
        current_stage="REPAIR_2",
        resume_stage="REPAIR_2",
        codex_thread_id=bound.codex_thread_id,
        worktree_identity=bound.worktree_identity,
        pr_number=bound.pr_number,
        ci_head=None,
        ci_run_or_check_locators=[],
        semantic_repair_count=2,
        pause_class=None,
        completed_work=[],
        retained_gates=["MARK_READY", "MERGE"],
        last_canonical_evidence=locator,
        next_allowed_transition="LOCAL_VALIDATE",
    )
    CANONICAL_COMMENTS[locator] = bootstrap._V5.serialize_state(state)
    return bound


def test_v5_bootstrap_exact_identity(repository: Path) -> None:
    assert bootstrap.verify(args(repository)).result == "PASS"


def test_v5_bootstrap_rejects_resume_substitution(repository: Path) -> None:
    value = args(repository)
    value.actual_codex_thread_id = "new"
    with pytest.raises(bootstrap.BootstrapError, match="PAUSED_CAPABILITY"):
        bootstrap.verify(value)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("freshen_remote", False, "fresh remote"),
        ("control_capsule_ref", "other", "Control Capsule"),
        ("actual_provider", "OTHER", "provider mismatch"),
        ("actual_stdin_source", "SHARED", "stdin source mismatch"),
    ],
)
def test_v5_bootstrap_rejects_incomplete_binding(
    repository: Path, field: str, value: object, message: str
) -> None:
    bound = args(repository)
    setattr(bound, field, value)
    with pytest.raises(bootstrap.BootstrapError, match=message):
        bootstrap.verify(bound)


@pytest.mark.parametrize(
    ("phase", "reasoning"),
    [
        ("PLAN", "medium"),
        ("IMPLEMENT", "medium"),
        ("REPAIR_1", "medium"),
        ("REPAIR_2", "high"),
    ],
)
def test_post_merge_v5_route(repository: Path, phase: str, reasoning: str) -> None:
    bound = args(repository)
    bound.semantic_phase = phase
    bound.model = bound.actual_model = "gpt-6-sol"
    bound.reasoning = bound.actual_reasoning = reasoning
    evidence = bootstrap.verify(bound)
    assert evidence.model == "gpt-6-sol"
    assert evidence.reasoning == reasoning


def test_v5_gpt56_route_fails_closed(repository: Path) -> None:
    bound = args(repository)
    bound.model = bound.actual_model = "gpt-5.6-terra"
    with pytest.raises(bootstrap.BootstrapError, match="post-merge V5 route mismatch"):
        bootstrap.verify(bound)


def test_post_merge_v5_rejects_v4_active_governance(repository: Path) -> None:
    bound = args(repository)
    bound.active_governance = "V4"
    with pytest.raises(bootstrap.BootstrapError, match="active governance must be V5"):
        bootstrap.verify(bound)


def test_requested_actual_identity_mismatch_still_fails_closed(repository: Path) -> None:
    bound = args(repository)
    bound.actual_model = "gpt-6-luna"
    with pytest.raises(bootstrap.BootstrapError, match="model mismatch"):
        bootstrap.verify(bound)


def test_malformed_canonical_state_cannot_be_overridden_by_pass_string(repository: Path) -> None:
    bound = args(repository)
    bound.package_state_verified = "PASS"
    CANONICAL_COMMENTS[bound.package_state_locator] = "not package state"
    with pytest.raises(bootstrap.BootstrapError, match="canonical package state is invalid"):
        bootstrap.verify(bound)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("task_packet_hash", "0" * 64, "task packet hash mismatch"),
        ("governance_epoch", "0" * 64, "governance epoch mismatch"),
        ("codex_thread_id", "other-thread", "Codex thread mismatch"),
        ("pr_number", 999, "PR mismatch"),
    ],
)
def test_mismatched_canonical_binding_cannot_be_overridden_by_pass_string(
    repository: Path, field: str, value: object, message: str
) -> None:
    bound = args(repository)
    bound.package_state_verified = "PASS"
    setattr(bound, field, value)
    if field in {"task_packet_hash", "governance_epoch"}:
        bound.preflight_binding_key = bootstrap.binding_key(
            bound.governance_epoch,
            bound.task_packet_hash,
            bound.exact_base,
            bound.execution_surface,
        )
    with pytest.raises(bootstrap.BootstrapError, match=message):
        bootstrap.verify(bound)


def test_stale_rebind_binds_real_head_tree_for_bootstrap_verify(repository: Path) -> None:
    bound = args(repository)
    locator = bound.package_state_locator
    old_state = bootstrap._V5.parse_state(CANONICAL_COMMENTS[locator])
    old_tree = bound.exact_tree

    (repository / "x").write_text("changed")
    git(repository, "add", "x")
    git(repository, "commit", "-m", "advance")
    git(repository, "push", "origin", "main")
    new_head = git(repository, "rev-parse", "HEAD")
    new_tree = git(repository, "rev-parse", "HEAD^{tree}")

    bound.exact_base = new_head
    bound.exact_tree = new_tree
    bound.preflight_binding_key = bootstrap.binding_key(
        bound.governance_epoch,
        bound.task_packet_hash,
        new_head,
        bound.execution_surface,
    )

    mismatched = bootstrap._V5.invalidate_old_head_evidence(old_state, new_head, old_tree)
    CANONICAL_COMMENTS[locator] = bootstrap._V5.serialize_state(mismatched)
    with pytest.raises(bootstrap.BootstrapError, match="exact tree mismatch"):
        bootstrap.verify(bound)

    rebound = bootstrap._V5.invalidate_old_head_evidence(old_state, new_head, new_tree)
    CANONICAL_COMMENTS[locator] = bootstrap._V5.serialize_state(rebound)
    assert bootstrap.verify(bound).result == "PASS"
