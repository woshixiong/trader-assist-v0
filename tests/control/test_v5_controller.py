from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "v5_controller", ROOT / "scripts/control/v5_controller.py"
)
assert SPEC and SPEC.loader
controller = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controller
SPEC.loader.exec_module(controller)


def state(**kw):
    value = dict(
        schema_version="1",
        revision=0,
        package_id="V5-B",
        governance_epoch="a" * 64,
        task_packet_hash="b" * 64,
        exact_main="c" * 40,
        exact_base="d" * 40,
        exact_head="e" * 40,
        exact_tree="f" * 40,
        route="C",
        current_stage="CONTROL_FREEZE",
        resume_stage="CONTROL_FREEZE",
        codex_thread_id="thread",
        worktree_identity="/work",
        pr_number=251,
        ci_head=None,
        ci_run_or_check_locators=[],
        semantic_repair_count=0,
        pause_class=None,
        completed_work=[],
        retained_gates=[],
        last_canonical_evidence="issue",
        next_allowed_transition="PLAN",
    )
    value.update(kw)
    return controller.PackageState(**value)


def test_codec_and_ambiguous_state_fail_closed():
    encoded = controller.serialize_state(state())
    assert controller.parse_state(encoded) == state()
    with pytest.raises(controller.ControlError):
        controller.parse_state(encoded + encoded)


@pytest.mark.parametrize(
    "target", [controller.Stage.PLAN, controller.Stage.PRECODE_REVIEW, controller.Stage.IMPLEMENT]
)
def test_normal_transition_table(target):
    current = state()
    for i, next_stage in enumerate(
        (controller.Stage.PLAN, controller.Stage.PRECODE_REVIEW, controller.Stage.IMPLEMENT)
    ):
        current = controller.transition(current, next_stage, event_key=str(i))
        assert current.current_stage == next_stage
        if next_stage == target:
            break


def test_resume_pause_repair_stale_and_idempotency():
    with pytest.raises(controller.ControlError):
        controller.validate_resume_identity(state(), "other", "/work", True)
    paused = controller.transition(state(), controller.Stage.PAUSED_TRANSPORT, event_key="pause")
    assert paused.pause_class == controller.Stage.PAUSED_TRANSPORT
    assert (
        controller.transition(
            paused, controller.Stage.CONTROL_FREEZE, event_key="resume"
        ).current_stage
        == controller.Stage.CONTROL_FREEZE
    )
    with pytest.raises(controller.ControlError):
        controller.transition(state(), controller.Stage.PLAN, event_key="bad", exact_head="0" * 40)
    implemented = state(current_stage="LOCAL_VALIDATE", resume_stage="LOCAL_VALIDATE")
    assert (
        controller.transition(
            implemented, controller.Stage.REPAIR_1, event_key="r1"
        ).semantic_repair_count
        == 1
    )


def test_stdin_workflow_review_and_handoff_guards():
    assert controller.render_resume_command("t", "prompt").endswith("</dev/null")
    assert " < " in controller.render_resume_command("t", "", prompt_file="/tmp/prompt")
    with pytest.raises(controller.ControlError):
        controller.validate_workflow_publication([".github/workflows/ci.yml"], False)
    controller.validate_workflow_publication(["x"], False)
    with pytest.raises(controller.ControlError):
        controller.validate_review({}, state(), set())
    assert "DECISION=x" in controller.render_handoff(
        {key: "x" for key in controller.HANDOFF_FIELDS}
    )


def test_canonical_readback_ci_and_push_reconciliation():
    saved = controller.serialize_state(state())
    store = controller.CanonicalCommentStore("1", lambda _: saved, lambda _, __: None)
    with pytest.raises(controller.ControlError, match="readback"):
        store.update(0, controller.Stage.CONTROL_FREEZE, "plan", controller.Stage.PLAN)
    assert (
        controller.route_ci(state(), controller.CiObservation("e" * 40, "success", ""))
        == controller.Stage.OPTIONAL_INTERNAL_REVIEW
    )
    assert (
        controller.route_ci(
            state(), controller.CiObservation("e" * 40, "failure", "TRANSIENT_OR_KNOWN_FLAKE")
        )
        == controller.Stage.CI_WAIT
    )
    assert (
        controller.route_ci(
            state(semantic_repair_count=2),
            controller.CiObservation("e" * 40, "failure", "SEMANTIC"),
        )
        == controller.Stage.CONTROL_REPLAN
    )
    assert controller.reconcile_push("e" * 40, "e" * 40, False) == "PUSH_CONFIRMED"
    with pytest.raises(controller.ControlError, match="ambiguous mutation"):
        controller.reconcile_push(None, "e" * 40, False)


def test_pr_and_review_exact_head_validation():
    controller.validate_draft_pr(
        {"number": 251, "headRefOid": "e" * 40, "isDraft": True, "state": "OPEN"}, state()
    )
    with pytest.raises(controller.ControlError, match="Draft"):
        controller.validate_draft_pr(
            {"number": 251, "headRefOid": "e" * 40, "isDraft": False, "state": "OPEN"}, state()
        )
    with pytest.raises(controller.ControlError, match="stale review"):
        controller.validate_review(
            {
                "REVIEW_TYPE": "PRE_CODE",
                "REVIEW_RESULT_KEY": "a",
                "DECISION": "PASS",
                "RESULT_EGRESS": "GITHUB_CANONICAL",
                "HEAD": "0" * 40,
            },
            state(),
            set(),
        )
