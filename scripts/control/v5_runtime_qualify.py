#!/usr/bin/env python3
"""Bounded, non-mutating V5 runtime qualification evidence collector."""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path


def probe(command: list[str]) -> dict[str, str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAIL", "evidence": str(exc)[:240]}
    return {
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "evidence": (result.stdout or result.stderr)[:240],
    }


def qualify(repository: Path) -> dict[str, object]:
    config_path = repository / ".codex/config.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        config_status = "PASS"
    except (OSError, tomllib.TOMLDecodeError) as exc:
        config = {}
        config_status = f"FAIL:{exc}"
    checks = {
        "codex_version": probe(["codex", "--version"]),
        "resume_syntax": probe(["codex", "exec", "resume", "--help"]),
        "config_parse": {
            "status": "PASS" if config_status == "PASS" else "FAIL",
            "evidence": config_status,
        },
        "primary_route_intent": {
            "status": "PASS"
            if config.get("model") == "gpt-6-sol"
            and config.get("model_reasoning_effort") == "medium"
            else "FAIL",
            "evidence": "static config only",
        },
        "actual_model_reasoning": {
            "status": "PENDING",
            "evidence": "requires actual CLI session evidence",
        },
        "exact_resume": {"status": "PENDING", "evidence": "requires exact session resume evidence"},
        "workspace_write": {"status": "PENDING", "evidence": "requires bounded local observation"},
        "approval_auto_review_network": {
            "status": "PENDING",
            "evidence": "requires authorized non-production observation",
        },
        "github_lifecycle": {
            "status": "PENDING",
            "evidence": "requires authorized non-production observation",
        },
        "hook_loading": {"status": "PENDING", "evidence": "requires runtime hook observation"},
        "optional_child": {
            "status": "SKIPPED",
            "evidence": "no child used without verifiable identity",
        },
    }
    overall = (
        "NOT_QUALIFIED"
        if any(v["status"] in {"FAIL", "PENDING"} for v in checks.values())
        else "QUALIFIED"
    )
    return {
        "schema_version": "1",
        "overall": overall,
        "MODEL_EXECUTOR_STDIN_SOURCE": "EXPLICIT",
        "checks": checks,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", default=".")
    p.add_argument("--output", choices=("json",), default="json")
    args = p.parse_args()
    print(json.dumps(qualify(Path(args.repository).resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
