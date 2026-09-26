from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "qualify", ROOT / "scripts/control/v5_runtime_qualify.py"
)
assert SPEC and SPEC.loader
qualify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qualify
SPEC.loader.exec_module(qualify)


def test_qualification_is_machine_readable_and_fail_closed(monkeypatch):
    monkeypatch.setattr(qualify, "probe", lambda _: {"status": "PASS", "evidence": "ok"})
    value = qualify.qualify(ROOT)
    assert value["overall"] == "NOT_QUALIFIED"
    assert value["MODEL_EXECUTOR_STDIN_SOURCE"] == "EXPLICIT"
