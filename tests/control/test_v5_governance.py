from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_v5", ROOT / "scripts/check_v5_governance.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


def test_v5_candidate_consistency():
    assert checker.run(ROOT) == []


def test_false_runtime_claim_rejected(monkeypatch):
    value = checker.manifest(ROOT)
    value["codex"]["runtime_qualification"] = "QUALIFIED"
    monkeypatch.setattr(checker, "manifest", lambda _: value)
    with pytest.raises(checker.CheckFailure, match="false runtime"):
        checker.check_manifest(ROOT)
