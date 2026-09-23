#!/usr/bin/env python3
"""Deterministic V4 exact-base and preflight-binding verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

HEX_40 = re.compile(r"[0-9a-f]{40}", re.ASCII)
HEX_64 = re.compile(r"[0-9a-f]{64}", re.ASCII)


class BootstrapError(RuntimeError):
    """Raised when a fail-closed bootstrap invariant does not hold."""


@dataclass(frozen=True)
class BootstrapEvidence:
    repository: str
    origin: str
    remote_ref: str
    exact_base: str
    exact_tree: str
    task_packet_hash: str
    governance_epoch: str
    preflight_binding_key: str
    control_capsule_ref: str
    execution_surface: str
    model: str
    reasoning: str
    web_search: str
    worktree_clean: bool
    result: str = "PASS"


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        message = result.stderr.strip()[:500]
        raise BootstrapError(f"git {' '.join(arguments)} failed: {message}")
    return result.stdout.strip()


def binding_key(
    governance_epoch: str,
    task_packet_hash: str,
    exact_base: str,
    execution_surface: str,
) -> str:
    payload = "\n".join(
        (governance_epoch, task_packet_hash, exact_base, execution_surface)
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def require_hex(value: str, pattern: re.Pattern[str], field: str) -> None:
    if pattern.fullmatch(value) is None:
        raise BootstrapError(f"{field} has invalid identity format")


def freshen_remote(repository: Path, remote_ref: str) -> None:
    if "/" not in remote_ref:
        raise BootstrapError("remote ref must use <remote>/<branch>")
    remote, branch = remote_ref.split("/", 1)
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "fetch",
            "--prune",
            remote,
            f"refs/heads/{branch}:refs/remotes/{remote}/{branch}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        message = result.stderr.strip()[:500]
        raise BootstrapError(f"remote freshness check failed: {message}")


def verify(args: argparse.Namespace) -> BootstrapEvidence:
    repository = Path(args.repository).resolve()
    if not (repository / ".git").exists():
        # Linked worktrees use a .git file, while normal repositories use a directory.
        raise BootstrapError("repository is not a Git worktree")

    require_hex(args.exact_base, HEX_40, "exact base")
    require_hex(args.task_packet_hash, HEX_64, "task packet hash")
    require_hex(args.governance_epoch, HEX_64, "governance epoch")
    require_hex(args.preflight_binding_key, HEX_64, "preflight binding key")
    if args.exact_tree is not None:
        require_hex(args.exact_tree, HEX_40, "exact tree")

    for name in (
        "project_ruleset_preflight",
        "engineering_preflight",
        "semantic_readiness",
    ):
        if getattr(args, name) != "PASS":
            raise BootstrapError(f"{name.upper()} must equal PASS")
    if not args.control_capsule_ref.strip():
        raise BootstrapError("CONTROL_CAPSULE_REF is required")

    if args.freshen_remote:
        freshen_remote(repository, args.remote_ref)

    origin = run_git(repository, "config", "--get", "remote.origin.url")
    if origin != args.expected_origin:
        raise BootstrapError(f"origin mismatch: expected {args.expected_origin}, observed {origin}")

    remote_head = run_git(repository, "rev-parse", args.remote_ref)
    if remote_head != args.exact_base:
        raise BootstrapError(
            f"remote/base mismatch: {args.remote_ref}={remote_head}, expected {args.exact_base}"
        )

    head = run_git(repository, "rev-parse", "HEAD")
    if head != args.exact_base:
        raise BootstrapError(f"worktree HEAD mismatch: observed {head}, expected {args.exact_base}")

    tree = run_git(repository, "rev-parse", "HEAD^{tree}")
    if args.exact_tree is not None and tree != args.exact_tree:
        raise BootstrapError(f"tree mismatch: observed {tree}, expected {args.exact_tree}")

    status = run_git(repository, "status", "--porcelain=v1")
    if status:
        raise BootstrapError("worktree is dirty or ambiguous")

    expected_key = binding_key(
        args.governance_epoch,
        args.task_packet_hash,
        args.exact_base,
        args.execution_surface,
    )
    if expected_key != args.preflight_binding_key:
        raise BootstrapError(
            "preflight binding mismatch: packet/governance/base/surface are not bound together"
        )

    if args.requested_model != args.actual_model:
        raise BootstrapError(
            f"model mismatch: requested {args.requested_model}, observed {args.actual_model}"
        )
    if args.requested_reasoning != args.actual_reasoning:
        raise BootstrapError(
            "reasoning mismatch: "
            f"requested {args.requested_reasoning}, observed {args.actual_reasoning}"
        )
    if args.requested_web_search != args.actual_web_search:
        raise BootstrapError(
            "web-search mismatch: "
            f"requested {args.requested_web_search}, observed {args.actual_web_search}"
        )

    return BootstrapEvidence(
        repository=str(repository),
        origin=origin,
        remote_ref=args.remote_ref,
        exact_base=head,
        exact_tree=tree,
        task_packet_hash=args.task_packet_hash,
        governance_epoch=args.governance_epoch,
        preflight_binding_key=expected_key,
        control_capsule_ref=args.control_capsule_ref,
        execution_surface=args.execution_surface,
        model=args.actual_model,
        reasoning=args.actual_reasoning,
        web_search=args.actual_web_search,
        worktree_clean=True,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository", required=True)
    result.add_argument("--expected-origin", required=True)
    result.add_argument("--remote-ref", default="origin/main")
    result.add_argument("--freshen-remote", action="store_true")
    result.add_argument("--exact-base", required=True)
    result.add_argument("--exact-tree")
    result.add_argument("--task-packet-hash", required=True)
    result.add_argument("--governance-epoch", required=True)
    result.add_argument("--preflight-binding-key", required=True)
    result.add_argument("--control-capsule-ref", required=True)
    result.add_argument("--execution-surface", required=True)
    result.add_argument("--project-ruleset-preflight", required=True)
    result.add_argument("--engineering-preflight", required=True)
    result.add_argument("--semantic-readiness", required=True)
    result.add_argument("--requested-model", required=True)
    result.add_argument("--actual-model", required=True)
    result.add_argument("--requested-reasoning", required=True)
    result.add_argument("--actual-reasoning", required=True)
    result.add_argument("--requested-web-search", required=True)
    result.add_argument("--actual-web-search", required=True)
    result.add_argument("--output", choices=("text", "json"), default="text")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        evidence = verify(args)
    except BootstrapError as exc:
        if args.output == "json":
            print(json.dumps({"result": "FAIL", "reason": str(exc)}, sort_keys=True))
        else:
            print(f"V4_BOOTSTRAP=FAIL\nREASON={exc}")
        return 1

    if args.output == "json":
        print(json.dumps(asdict(evidence), indent=2, sort_keys=True))
    else:
        print("V4_BOOTSTRAP=PASS")
        for key, value in asdict(evidence).items():
            print(f"{key.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
