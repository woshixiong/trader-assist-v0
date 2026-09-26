from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "qualify", ROOT / "scripts/control/v5_runtime_qualify.py"
)
assert SPEC and SPEC.loader
qualify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualify
SPEC.loader.exec_module(qualify)


def test_static_qualification_is_machine_readable_and_fail_closed(monkeypatch):
    monkeypatch.setattr(qualify, "probe", lambda _: {"status": "PASS", "evidence": "ok"})
    value = qualify.qualify(ROOT)
    assert value["overall"] == "NOT_QUALIFIED"
    assert value["MODEL_EXECUTOR_STDIN_SOURCE"] == "EXPLICIT"


def test_observed_runtime_evidence_is_validated(monkeypatch):
    monkeypatch.setattr(qualify, "probe", lambda _: {"status": "PASS", "evidence": "ok"})
    evidence = {
        "schema_version": "1",
        "actual_model": "gpt-6-sol",
        "actual_reasoning_effort": "medium",
        "approval_policy": "on-request",
        "approvals_reviewer": "auto_review",
        "sandbox_mode": "workspace-write",
        "exact_thread_resume": "PASS",
        "workspace_write": "PASS",
        "worktree_clean": "PASS",
        "github_read_network": "PASS",
        "hook_loading": "PASS",
        "protected_action_nonregression": "PASS",
        "silent_model_fallback": "NO",
        "codex_thread_id": "thread",
        "github_pr_head": "a" * 40,
        "optional_child": {"status": "SKIPPED"},
    }
    value = qualify.qualify(ROOT, evidence, "thread", "a" * 40)
    assert value["overall"] == "QUALIFIED"
    assert value["checks"]["optional_child"]["status"] == "SKIPPED"


def test_invalid_or_mismatched_evidence_fails_closed(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text('{"schema_version":"wrong"}', encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        qualify.load_evidence(path)
