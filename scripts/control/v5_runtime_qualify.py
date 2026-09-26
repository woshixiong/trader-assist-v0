#!/usr/bin/env python3
"""Bounded, non-mutating V5 runtime qualification evidence collector."""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_EVIDENCE_BYTES = 65_536
PASS = "PASS"
PENDING = "PENDING"
SKIPPED = "SKIPPED"


def probe(command: list[str]) -> dict[str, str]:
    """Run only non-model discovery commands with explicit closed stdin."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "evidence": str(exc)[:240]}
    return {
        "status": PASS if result.returncode == 0 else "FAIL",
        "evidence": (result.stdout or result.stderr)[:240],
    }


def pending(reason: str) -> dict[str, str]:
    return {"status": PENDING, "evidence": reason}


def observed(evidence: Mapping[str, Any], key: str, expected: str) -> dict[str, str]:
    value = evidence.get(key)
    if value is None:
        return pending(f"runtime evidence missing: {key}")
    if value != expected:
        return {"status": "FAIL", "evidence": f"{key} mismatch"}
    return {"status": PASS, "evidence": f"observed {key}"}


def load_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read runtime evidence: {exc}") from exc
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise ValueError("runtime evidence exceeds bounded input size")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("runtime evidence is not valid JSON") from exc
    if not isinstance(value, dict) or value.get("schema_version") != "1":
        raise ValueError("runtime evidence has invalid schema")
    return value


def optional_child_check(evidence: Mapping[str, Any]) -> dict[str, str]:
    child = evidence.get("optional_child")
    if child is None:
        return {"status": SKIPPED, "evidence": "no child used without verifiable identity"}
    if not isinstance(child, Mapping):
        return {"status": "FAIL", "evidence": "optional child evidence is malformed"}
    if child.get("status") == SKIPPED:
        return {"status": SKIPPED, "evidence": "optional child explicitly skipped"}
    if child.get("model") == "gpt-6-luna" and child.get("reasoning") in {"low", "high"}:
        return {"status": PASS, "evidence": "optional child runtime identity observed"}
    return {"status": "FAIL", "evidence": "optional child identity is unverifiable"}


def qualify(
    repository: Path,
    evidence: Mapping[str, Any] | None = None,
    expected_thread: str | None = None,
    expected_pr_head: str | None = None,
) -> dict[str, object]:
    """Validate observed evidence; never infer runtime facts from static config."""
    evidence = evidence or {}
    try:
        config = tomllib.loads((repository / ".codex/config.toml").read_text(encoding="utf-8"))
        config_status = PASS
    except (OSError, tomllib.TOMLDecodeError) as exc:
        config, config_status = {}, f"FAIL:{exc}"
    checks: dict[str, dict[str, str]] = {
        "codex_version": probe(["codex", "--version"]),
        "resume_syntax": probe(["codex", "exec", "resume", "--help"]),
        "config_parse": {
            "status": PASS if config_status == PASS else "FAIL",
            "evidence": config_status,
        },
        "primary_route_intent": {
            "status": PASS
            if config.get("model") == "gpt-6-sol"
            and config.get("model_reasoning_effort") == "medium"
            else "FAIL",
            "evidence": "static config only",
        },
        "actual_model": observed(evidence, "actual_model", "gpt-6-sol"),
        "actual_reasoning": observed(evidence, "actual_reasoning_effort", "medium"),
        "approval_policy": observed(evidence, "approval_policy", "on-request"),
        "approvals_reviewer": observed(evidence, "approvals_reviewer", "auto_review"),
        "sandbox": observed(evidence, "sandbox_mode", "workspace-write"),
        "exact_resume": observed(evidence, "exact_thread_resume", PASS),
        "workspace_write": observed(evidence, "workspace_write", PASS),
        "worktree_clean": observed(evidence, "worktree_clean", PASS),
        "github_read_network": observed(evidence, "github_read_network", PASS),
        "hook_loading": observed(evidence, "hook_loading", PASS),
        "protected_action_nonregression": observed(
            evidence, "protected_action_nonregression", PASS
        ),
        "no_silent_fallback": observed(evidence, "silent_model_fallback", "NO"),
        "optional_child": optional_child_check(evidence),
    }
    if expected_thread is not None:
        checks["exact_thread"] = observed(evidence, "codex_thread_id", expected_thread)
    if expected_pr_head is not None:
        checks["github_pr_head"] = observed(evidence, "github_pr_head", expected_pr_head)
    overall = (
        "QUALIFIED"
        if all(value["status"] == PASS for key, value in checks.items() if key != "optional_child")
        else "NOT_QUALIFIED"
    )
    return {
        "schema_version": "1",
        "overall": overall,
        "MODEL_EXECUTOR_STDIN_SOURCE": "EXPLICIT",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=".")
    parser.add_argument("--evidence-json", type=Path)
    parser.add_argument("--expected-thread")
    parser.add_argument("--expected-pr-head")
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()
    try:
        evidence = load_evidence(args.evidence_json)
    except ValueError as exc:
        print(json.dumps({"overall": "NOT_QUALIFIED", "reason": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            qualify(
                Path(args.repository).resolve(),
                evidence,
                args.expected_thread,
                args.expected_pr_head,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
