from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "control" / "v4_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("v4_bootstrap", SCRIPT)
assert SPEC and SPEC.loader
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", str(bare))
    git(tmp_path, "init", "-b", "main", str(repo))
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "V4 Test")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "base")
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-u", "origin", "main")
    return repo


def arguments(repository: Path) -> argparse.Namespace:
    exact_base = git(repository, "rev-parse", "HEAD")
    task_hash = "1" * 64
    governance_epoch = "2" * 64
    surface = "CODEX_DESKTOP"
    return argparse.Namespace(
        repository=str(repository),
        expected_origin=git(repository, "config", "--get", "remote.origin.url"),
        remote_ref="origin/main",
        freshen_remote=False,
        exact_base=exact_base,
        exact_tree=git(repository, "rev-parse", "HEAD^{tree}"),
        task_packet_hash=task_hash,
        governance_epoch=governance_epoch,
        preflight_binding_key=bootstrap.binding_key(
            governance_epoch, task_hash, exact_base, surface
        ),
        control_capsule_ref="ISSUE_232_COMMENT_5789214494",
        execution_surface=surface,
        project_ruleset_preflight="PASS",
        engineering_preflight="PASS",
        semantic_readiness="PASS",
        requested_model="GPT-5.6-SOL",
        actual_model="GPT-5.6-SOL",
        requested_reasoning="MEDIUM",
        actual_reasoning="MEDIUM",
        requested_web_search="DISABLED",
        actual_web_search="DISABLED",
        output="json",
    )


def test_exact_base_bootstrap_passes(repository: Path) -> None:
    evidence = bootstrap.verify(arguments(repository))
    assert evidence.result == "PASS"
    assert evidence.worktree_clean is True
    assert evidence.exact_base == git(repository, "rev-parse", "HEAD")


def test_dirty_worktree_is_rejected(repository: Path) -> None:
    (repository / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(bootstrap.BootstrapError, match="dirty or ambiguous"):
        bootstrap.verify(arguments(repository))


def test_base_and_binding_mismatches_are_rejected(repository: Path) -> None:
    args = arguments(repository)
    args.exact_base = "a" * 40
    with pytest.raises(bootstrap.BootstrapError, match="remote/base mismatch"):
        bootstrap.verify(args)

    args = arguments(repository)
    args.preflight_binding_key = "f" * 64
    with pytest.raises(bootstrap.BootstrapError, match="preflight binding mismatch"):
        bootstrap.verify(args)


def test_model_reasoning_and_pass_attestations_fail_closed(repository: Path) -> None:
    args = arguments(repository)
    args.actual_model = "OTHER"
    with pytest.raises(bootstrap.BootstrapError, match="model mismatch"):
        bootstrap.verify(args)

    args = arguments(repository)
    args.actual_reasoning = "HIGH"
    with pytest.raises(bootstrap.BootstrapError, match="reasoning mismatch"):
        bootstrap.verify(args)

    args = arguments(repository)
    args.engineering_preflight = "FAIL"
    with pytest.raises(bootstrap.BootstrapError, match="ENGINEERING_PREFLIGHT"):
        bootstrap.verify(args)
