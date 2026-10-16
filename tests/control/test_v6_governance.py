from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("check_v6", ROOT / "scripts/check_v6_governance.py")
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


def test_v6_pilot_single_active_constitution() -> None:
    assert checker.run(ROOT) == [
        "V6_MANIFEST", "V6_AUTHORITY", "V6_PROTECTED_GATES", "V6_CI_SELECTOR",
    ]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("governance_version", "V5"),
        ("status", "PRE_MERGE_CANDIDATE"),
        ("sole_project_wide_constitution", checker.V5_ARCHIVE),
        ("active_skills", [".agents/skills/trade-os-v5-review/SKILL.md"]),
        ("protected_actions", list(checker.PROTECTED[:-1])),
        ("archived_governance", {}),
        ("codex", {"execution_surface": "CLOUD_WITH_CLI_AUTO_FALLBACK"}),
        ("entrypoints", ["AGENTS.md"]),
        ("user_decision", {"protected_actions_require_current_authority": False}),
    ],
)
def test_manifest_weakening_fails_closed(path: str, value: Any) -> None:
    manifest = copy.deepcopy(checker.load_manifest(ROOT))
    manifest[path] = value
    with pytest.raises(checker.CheckFailure):
        checker.check_manifest(manifest)


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("AGENTS.md", checker.FOUR_GATES[0]),
        ("AGENTS.md", checker.CONTEXT_MARKERS[0]),
        ("AGENTS.md", checker.TWO_FIX),
        ("governance/ENGINEERING_GOVERNANCE_V6_PILOT.md", checker.FOUR_GATES[2]),
        ("governance/ENGINEERING_GOVERNANCE_V6_PILOT.md", checker.USER_OVERRIDE),
        ("governance/CHATGPT_PROJECT_GOVERNANCE_BRIDGE.md", checker.FOUR_GATES[3]),
        (".agents/skills/trade-os-v6/SKILL.md", checker.CONTEXT_MARKERS[1]),
        (".github/workflows/ci.yml", "V6 candidate/main governance downgrade"),
        (".github/workflows/ci.yml", "--ignore=tests/control/test_v5_governance.py"),
    ],
)
def test_required_document_tokens_are_nonoptional(
    monkeypatch: pytest.MonkeyPatch, path: str, marker: str,
) -> None:
    original = checker.content

    def without_marker(root: Path, requested: str) -> str:
        result = original(root, requested)
        return result.replace(marker, "REMOVED_POLICY_TOKEN") if path == requested else result

    monkeypatch.setattr(checker, "content", without_marker)
    with pytest.raises(checker.CheckFailure):
        checker.check_documents(ROOT)


def test_invalid_manifest_json_fails_closed(tmp_path: Path) -> None:
    directory = tmp_path / "governance"
    directory.mkdir()
    (directory / "ACTIVE_GOVERNANCE_MANIFEST.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(checker.CheckFailure, match="malformed"):
        checker.load_manifest(tmp_path)
