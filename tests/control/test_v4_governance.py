from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_v4_governance.py"
SPEC = importlib.util.spec_from_file_location("check_v4_governance", SCRIPT)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def test_v4_governance_consistency() -> None:
    assert checker.run(ROOT) == []


def test_required_smoke_labels_are_unique() -> None:
    labels = [label for label, _ in checker.checks()]
    assert len(labels) == len(set(labels))
    assert labels == [
        "V4_SINGLE_CONSTITUTION",
        "ACTIVE_GOVERNANCE_MANIFEST",
        "AGENTS_ROUTER",
        "PROJECT_RULES_INDEX",
        "CODEX_CONFIG_PARSE",
        "EXPLORER_READ_ONLY",
        "CODE_REVIEWER_READ_ONLY",
        "MODEL_ROUTING_POLICY",
        "GITHUB_TRANSPORT_NONREGRESSION",
        "SKILL_DISCOVERY",
        "EXACT_BASE_BOOTSTRAP",
        "DIRTY_WORKTREE_REJECTION",
        "MODEL_ROUTE_ATTESTATION",
        "CI_ZERO_MODEL_CONTRACT",
        "COMMENT_ONLY_REVIEW_FALLBACK",
        "ABILITY_BOUNDARY_CONTINUATION",
        "ORDINARY_CHATGPT_WRITER_BRANCH",
        "PROTECTED_ACTION_GATE",
    ]


def test_post_checkpoint_model_and_transport_rules_are_enforced() -> None:
    checker.check_model_routing(ROOT)
    checker.check_transport_nonregression(ROOT)
    checker.check_agent(
        ROOT, ".codex/agents/explorer.toml", "gpt-5.6-luna", "low"
    )
    checker.check_agent(
        ROOT, ".codex/agents/code-reviewer.toml", "gpt-5.6-terra", "medium"
    )
