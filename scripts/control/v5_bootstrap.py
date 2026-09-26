#!/usr/bin/env python3
"""Fail-closed V5 package bootstrap, adapted from the V4 verifier."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_v4_bootstrap", Path(__file__).with_name("v4_bootstrap.py")
)
assert _SPEC and _SPEC.loader
_V4 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _V4
_SPEC.loader.exec_module(_V4)
BootstrapError = _V4.BootstrapError
binding_key = _V4.binding_key
require_hex = _V4.require_hex
run_git = _V4.run_git

_V5_SPEC = importlib.util.spec_from_file_location(
    "_v5_controller", Path(__file__).with_name("v5_controller.py")
)
assert _V5_SPEC and _V5_SPEC.loader
_V5 = importlib.util.module_from_spec(_V5_SPEC)
sys.modules[_V5_SPEC.name] = _V5
_V5_SPEC.loader.exec_module(_V5)

GITHUB_COMMENT = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/\d+"
    r"#issuecomment-(?P<comment_id>\d+)"
)


def read_canonical_comment(locator: str) -> str:
    """Read the exact GitHub Issue comment; do not accept caller attestations."""
    match = GITHUB_COMMENT.fullmatch(locator)
    if match is None:
        raise BootstrapError("canonical package-state locator is invalid")
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{match['owner']}/{match['repo']}/issues/comments/{match['comment_id']}",
            "--jq",
            ".body",
        ],
        check=False,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=30,
    )
    if result.returncode != 0:
        raise BootstrapError(f"canonical package-state read failed: {result.stderr[:240].strip()}")
    return result.stdout


def verify_canonical_state(args: argparse.Namespace, exact_tree: str) -> None:
    if args.control_capsule_ref != args.package_state_locator:
        raise BootstrapError("Control Capsule must bind the canonical V5 package-state record")
    try:
        state = _V5.parse_state(read_canonical_comment(args.package_state_locator))
    except _V5.ControlError as exc:
        raise BootstrapError(f"canonical package state is invalid: {exc}") from exc
    bindings = (
        ("package id", args.package_id, state.package_id),
        ("governance epoch", args.governance_epoch, state.governance_epoch),
        ("task packet hash", args.task_packet_hash, state.task_packet_hash),
        ("exact main", args.exact_main, state.exact_main),
        ("package base", args.package_base, state.exact_base),
        ("exact head", args.exact_base, state.exact_head),
        ("exact tree", exact_tree, state.exact_tree),
        ("route", args.route, state.route),
        ("Codex thread", args.codex_thread_id, state.codex_thread_id),
        ("worktree", args.worktree_identity, state.worktree_identity),
        ("PR", args.pr_number, state.pr_number),
    )
    for label, expected, observed in bindings:
        if expected != observed:
            raise BootstrapError(f"canonical package-state {label} mismatch")
    if not state.last_canonical_evidence or not state.next_allowed_transition:
        raise BootstrapError("canonical Control Capsule content is incomplete")


@dataclass(frozen=True)
class V5BootstrapEvidence:
    repository: str
    origin: str
    remote_ref: str
    exact_base: str
    exact_tree: str
    package_state_locator: str
    codex_thread_id: str
    worktree_identity: str
    model: str
    reasoning: str
    semantic_phase: str
    result: str = "PASS"


def verify(args: argparse.Namespace) -> V5BootstrapEvidence:
    repository = Path(args.repository).resolve()
    for value, name, pattern in (
        (args.exact_base, "exact base", _V4.HEX_40),
        (args.task_packet_hash, "task packet hash", _V4.HEX_64),
        (args.governance_epoch, "governance epoch", _V4.HEX_64),
        (args.preflight_binding_key, "preflight binding key", _V4.HEX_64),
    ):
        require_hex(value, pattern, name)
    if not args.package_state_locator or not args.control_capsule_ref:
        raise BootstrapError("package-state locator and Control Capsule are required")
    for name in ("project_ruleset_preflight", "engineering_preflight", "semantic_readiness"):
        if getattr(args, name) != "PASS":
            raise BootstrapError(f"{name.upper()} must equal PASS")
    if args.active_governance != "V5":
        raise BootstrapError("active governance must be V5 for post-merge V5 packages")
    expected_route = {
        "PLAN": ("gpt-6-sol", "medium"),
        "IMPLEMENT": ("gpt-6-sol", "medium"),
        "REPAIR_1": ("gpt-6-sol", "medium"),
        "REPAIR_2": ("gpt-6-sol", "high"),
    }
    if args.semantic_phase not in expected_route:
        raise BootstrapError("unsupported post-merge V5 semantic phase")
    if (args.model, args.reasoning) != expected_route[args.semantic_phase]:
        raise BootstrapError("post-merge V5 route mismatch")
    if args.freshen_remote:
        _V4.freshen_remote(repository, args.remote_ref)
    else:
        raise BootstrapError("fresh remote/base verification is required")
    origin = run_git(repository, "config", "--get", "remote.origin.url")
    if origin != args.expected_origin:
        raise BootstrapError("origin mismatch")
    if run_git(repository, "rev-parse", args.remote_ref) != args.exact_base:
        raise BootstrapError("remote/base mismatch")
    if run_git(repository, "rev-parse", "HEAD") != args.exact_base:
        raise BootstrapError("worktree HEAD mismatch")
    tree = run_git(repository, "rev-parse", "HEAD^{tree}")
    if args.exact_tree and tree != args.exact_tree:
        raise BootstrapError("tree mismatch")
    if run_git(repository, "status", "--porcelain=v1"):
        raise BootstrapError("worktree is dirty or ambiguous")
    verify_canonical_state(args, tree)
    if (
        binding_key(
            args.governance_epoch, args.task_packet_hash, args.exact_base, args.execution_surface
        )
        != args.preflight_binding_key
    ):
        raise BootstrapError("preflight binding mismatch")
    pairs = (
        ("executor", args.requested_executor, args.actual_executor),
        ("provider", args.requested_provider, args.actual_provider),
        ("execution surface", args.execution_surface, args.actual_execution_surface),
        ("model", args.model, args.actual_model),
        ("reasoning", args.reasoning, args.actual_reasoning),
        ("web search", args.requested_web_search, args.actual_web_search),
        ("tool state", args.requested_tool_state, args.actual_tool_state),
        ("session policy", args.requested_session_policy, args.actual_session_policy),
        ("resource state", args.requested_resource_state, args.actual_resource_state),
        ("worktree policy", args.requested_worktree_policy, args.actual_worktree_policy),
        ("stdin source", args.requested_stdin_source, args.actual_stdin_source),
    )
    for label, requested, actual in pairs:
        if requested != actual:
            raise BootstrapError(f"{label} mismatch")
    if args.resume_required and (
        not args.resume_verifiable
        or args.codex_thread_id != args.actual_codex_thread_id
        or args.worktree_identity != args.actual_worktree_identity
    ):
        raise BootstrapError("PAUSED_CAPABILITY: exact resume identity unavailable")
    return V5BootstrapEvidence(
        str(repository),
        origin,
        args.remote_ref,
        args.exact_base,
        tree,
        args.package_state_locator,
        args.codex_thread_id,
        args.worktree_identity,
        args.actual_model,
        args.actual_reasoning,
        args.semantic_phase,
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    for key in (
        "repository",
        "exact-base",
        "task-packet-hash",
        "governance-epoch",
        "preflight-binding-key",
        "control-capsule-ref",
        "package-state-locator",
        "package-id",
        "exact-main",
        "package-base",
        "route",
        "expected-origin",
        "remote-ref",
        "execution-surface",
        "actual-execution-surface",
        "requested-executor",
        "actual-executor",
        "requested-provider",
        "actual-provider",
        "model",
        "actual-model",
        "reasoning",
        "actual-reasoning",
        "requested-web-search",
        "actual-web-search",
        "requested-tool-state",
        "actual-tool-state",
        "requested-session-policy",
        "actual-session-policy",
        "requested-resource-state",
        "actual-resource-state",
        "requested-worktree-policy",
        "actual-worktree-policy",
        "requested-stdin-source",
        "actual-stdin-source",
        "active-governance",
        "semantic-phase",
        "codex-thread-id",
        "actual-codex-thread-id",
        "worktree-identity",
        "actual-worktree-identity",
    ):
        p.add_argument("--" + key, required=True)
    p.add_argument("--exact-tree")
    p.add_argument("--pr-number", required=True, type=int)
    p.add_argument("--freshen-remote", action="store_true")
    p.add_argument("--project-ruleset-preflight", required=True)
    p.add_argument("--engineering-preflight", required=True)
    p.add_argument("--semantic-readiness", required=True)
    p.add_argument("--resume-required", action="store_true")
    p.add_argument("--resume-verifiable", action="store_true")
    p.add_argument("--output", choices=("json", "text"), default="text")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        value = verify(args)
    except BootstrapError as exc:
        print(
            json.dumps({"result": "FAIL", "reason": str(exc)})
            if args.output == "json"
            else f"V5_BOOTSTRAP=FAIL\nREASON={exc}"
        )
        return 1
    print(
        json.dumps(asdict(value), sort_keys=True) if args.output == "json" else "V5_BOOTSTRAP=PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
