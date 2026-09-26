#!/usr/bin/env python3
"""Fail-closed V5 package bootstrap, adapted from the V4 verifier."""

from __future__ import annotations

import argparse
import importlib.util
import json
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


@dataclass(frozen=True)
class V5BootstrapEvidence:
    exact_base: str
    exact_tree: str
    package_state_locator: str
    codex_thread_id: str
    worktree_identity: str
    model: str
    reasoning: str
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
    if run_git(repository, "rev-parse", "HEAD") != args.exact_base:
        raise BootstrapError("worktree HEAD mismatch")
    tree = run_git(repository, "rev-parse", "HEAD^{tree}")
    if args.exact_tree and tree != args.exact_tree:
        raise BootstrapError("tree mismatch")
    if run_git(repository, "status", "--porcelain=v1"):
        raise BootstrapError("worktree is dirty or ambiguous")
    if (
        binding_key(
            args.governance_epoch, args.task_packet_hash, args.exact_base, args.execution_surface
        )
        != args.preflight_binding_key
    ):
        raise BootstrapError("preflight binding mismatch")
    pairs = (
        ("execution surface", args.execution_surface, args.actual_execution_surface),
        ("model", args.model, args.actual_model),
        ("reasoning", args.reasoning, args.actual_reasoning),
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
        args.exact_base,
        tree,
        args.package_state_locator,
        args.codex_thread_id,
        args.worktree_identity,
        args.actual_model,
        args.actual_reasoning,
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
        "execution-surface",
        "actual-execution-surface",
        "model",
        "actual-model",
        "reasoning",
        "actual-reasoning",
        "codex-thread-id",
        "actual-codex-thread-id",
        "worktree-identity",
        "actual-worktree-identity",
    ):
        p.add_argument("--" + key, required=True)
    p.add_argument("--exact-tree")
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
