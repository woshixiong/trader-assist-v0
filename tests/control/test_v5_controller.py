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
            state(),
            controller.CiObservation("e" * 40, "failure", "DETERMINISTIC_MECHANICAL"),
        )
        == controller.Stage.MECHANICAL_REPAIR
    )
    mechanical = controller.transition(
        state(current_stage="CI_WAIT", resume_stage="CI_WAIT", semantic_repair_count=1),
        controller.Stage.MECHANICAL_REPAIR,
        event_key="mechanical",
    )
    assert mechanical.semantic_repair_count == 1
    assert (
        controller.transition(
            mechanical, controller.Stage.LOCAL_VALIDATE, event_key="mechanical-validated"
        ).current_stage
        == controller.Stage.LOCAL_VALIDATE
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


def test_duplicate_delivery_ignores_original_preconditions_without_write():
    canonical = controller.transition(state(), controller.Stage.PLAN, event_key="plan")
    writes = []
    store = controller.CanonicalCommentStore(
        "1", lambda _: controller.serialize_state(canonical), lambda *_: writes.append(1)
    )
    duplicate = store.update(0, controller.Stage.CONTROL_FREEZE, "plan", controller.Stage.PLAN)
    assert duplicate == canonical
    assert writes == []


@pytest.mark.parametrize(
    ("repair_stage", "repair_count"),
    [(controller.Stage.REPAIR_1, 1), (controller.Stage.REPAIR_2, 2)],
)
def test_repair_continues_through_revalidation_publication_and_ci(repair_stage, repair_count):
    current = state(
        current_stage=repair_stage,
        resume_stage=repair_stage,
        semantic_repair_count=repair_count,
    )
    current = controller.transition(current, controller.Stage.LOCAL_VALIDATE, event_key="validated")
    current = controller.transition(current, controller.Stage.PUBLISH, event_key="publish")
    current = controller.transition(current, controller.Stage.CI_WAIT, event_key="ci")
    assert current.current_stage == controller.Stage.CI_WAIT


def test_stale_rebind_atomically_updates_head_tree_and_invalidates_ci():
    original = state(
        revision=7,
        current_stage="CI_WAIT",
        resume_stage="CI_WAIT",
        ci_head="e" * 40,
        ci_run_or_check_locators=["run-1"],
        semantic_repair_count=2,
        retained_gates=["MARK_READY", "MERGE"],
    )
    stale = controller.invalidate_old_head_evidence(original, "1" * 40, "2" * 40)

    assert stale.exact_head == "1" * 40
    assert stale.exact_tree == "2" * 40
    assert stale.ci_head is None
    assert stale.ci_run_or_check_locators == []
    assert stale.last_canonical_evidence == "STALE_HEAD_INVALIDATED"
    assert stale.current_stage == controller.Stage.STALE_REBIND
    assert stale.resume_stage == controller.Stage.STALE_REBIND
    assert stale.next_allowed_transition == controller.Stage.LOCAL_VALIDATE
    assert stale.revision == original.revision + 1
    assert stale.semantic_repair_count == original.semantic_repair_count
    assert stale.retained_gates == original.retained_gates


def test_stale_rebind_same_head_same_tree_is_idempotent():
    original = state(revision=4)
    rebound = controller.invalidate_old_head_evidence(
        original, original.exact_head, original.exact_tree
    )
    assert rebound is original


def test_stale_rebind_same_head_different_tree_fails_closed():
    original = state()
    with pytest.raises(controller.ControlError, match="same head has different tree"):
        controller.invalidate_old_head_evidence(original, original.exact_head, "0" * 40)


def test_stale_rebind_requires_revalidation_then_can_publish():
    stale = controller.invalidate_old_head_evidence(
        state(current_stage="CI_WAIT", resume_stage="CI_WAIT"), "1" * 40, "2" * 40
    )
    validated = controller.transition(
        stale, controller.Stage.LOCAL_VALIDATE, event_key="revalidate"
    )
    assert (
        controller.transition(
            validated, controller.Stage.PUBLISH, event_key="republish"
        ).current_stage
        == controller.Stage.PUBLISH
    )


# Route-B candidate admission and exact-head executable-evidence matrix.
PRECODE = {
    "REVIEW_TYPE": "PRE_CODE",
    "DECISION": "PASS",
    "FAIL_ROUTE": "NONE",
    "RESULT_EGRESS": "GITHUB_CANONICAL",
    "REVIEWER_MODE": "FRESH_ORDINARY_CHATGPT_READ_ONLY",
    "PACKAGE_ID": "V5-B",
    "FROZEN_BASE": "d" * 40,
    "REVIEW_RESULT_KEY": "V5_PRECODE_PASS",
    "PLAN_REF": "https://github.com/example/repo/issues/1#issuecomment-1",
    "CANONICAL_REF": "https://github.com/example/repo/issues/1#issuecomment-42",
}
CHATGPT_ID = {
    "executor": "FRESH_ORDINARY_CHATGPT_WRITER",
    "provider": "OPENAI",
    "surface": "CHATGPT_ORDINARY_GITHUB_NATIVE",
    "model": "GPT-5.6 Sol",
    "reasoning": "HIGH",
}
CODEX_ID = {
    "executor": "CODEX",
    "provider": "OPENAI",
    "surface": "CODEX_CLI",
    "model": "gpt-6.1-sol",
    "reasoning": "medium",
}
MECHANICAL_ID = {
    "executor": "NONE",
    "provider": "NONE",
    "surface": "GITHUB_NATIVE",
    "model": "NONE",
    "reasoning": "NONE",
}


def admission(current, identity, **kw):
    values = dict(
        requested_route=current.route,
        actor="WRITER",
        stage=current.current_stage,
        event_key="implement-turn-1",
        observed_head=current.exact_head,
        authorized_identity=identity,
        actual_identity=identity,
        precode_evidence=PRECODE,
    )
    values.update(kw)
    return controller.validate_execution_admission(current, **values)


def test_route_family_recognizes_only_canonical_families():
    for name in ("A", "B_SMALL_FROZEN", "C", "C_LARGE_CODEX", "D"):
        assert controller.route_family(name) == name[0]
    for name in ("", "E", "b", "CHATGPT", "C-SWITCH", "C_WUT!"):
        with pytest.raises(controller.ControlError, match="execution route"):
            controller.route_family(name)


def test_route_b_exact_writer_and_verified_precode_are_required():
    current = state(
        route="B_SMALL_FROZEN_BOUNDED_ORDINARY_CHATGPT_HIGH",
        current_stage="IMPLEMENT",
        completed_work=["INDEPENDENT_PRECODE_PASS_42"],
    )
    admission(current, CHATGPT_ID)

    for overrides in (
        {"requested_route": "C"},
        {"actor": "ENGINEERING_CONTROL"},
        {"stage": "PLAN"},
        {"observed_head": "0" * 40},
        {"event_key": "INDEPENDENT_PRECODE_PASS_42"},
        {"precode_evidence": None},
        {"precode_evidence": {**PRECODE, "DECISION": "PLAN_REVISE"}},
        {"precode_evidence": {**PRECODE, "RESULT_EGRESS": "NOT_WRITTEN"}},
        {"precode_evidence": {**PRECODE, "CANONICAL_REF": PRECODE["PLAN_REF"]}},
        {"actual_identity": {**CHATGPT_ID, "model": "other"}},
        {"actual_identity": {**CHATGPT_ID, "surface": "CODEX_CLI"}},
    ):
        with pytest.raises(controller.ControlError):
            admission(current, CHATGPT_ID, **overrides)


def test_route_b_cannot_dispatch_codex_even_when_requested_actual_match():
    current = state(
        route="B_SMALL_FROZEN_BOUNDED_ORDINARY_CHATGPT_HIGH",
        current_stage="IMPLEMENT",
        completed_work=["INDEPENDENT_PRECODE_PASS_42"],
    )
    with pytest.raises(controller.ControlError, match="Route B"):
        admission(current, CODEX_ID)


def test_route_c_plan_and_original_resume_but_never_b_to_c_fallback():
    plan = state(current_stage="PLAN")
    admission(plan, CODEX_ID)
    implement = state(
        current_stage="IMPLEMENT", completed_work=["INDEPENDENT_PRECODE_PASS_42"]
    )
    admission(
        implement, CODEX_ID,
        codex_thread_id="thread", worktree_identity="/work", resume_verifiable=True
    )
    for changes in (
        {"codex_thread_id": "new"},
        {"worktree_identity": "/other"},
        {"resume_verifiable": False},
        {"precode_evidence": None},
    ):
        with pytest.raises(controller.ControlError):
            admission(
                implement, CODEX_ID,
                **{
                    **dict(
                        codex_thread_id="thread",
                        worktree_identity="/work",
                        resume_verifiable=True,
                    ),
                    **changes,
                }
            )


def test_routes_a_and_d_are_model_free_and_authority_bounded():
    mechanical = state(route="A", current_stage="CI_WAIT")
    admission(mechanical, MECHANICAL_ID, actor="DETERMINISTIC_CONTROLLER")
    with pytest.raises(controller.ControlError):
        admission(mechanical, CODEX_ID, actor="DETERMINISTIC_CONTROLLER")
    control = state(route="D", current_stage="CONTROL_REPLAN")
    admission(control, MECHANICAL_ID, actor="ENGINEERING_CONTROL")
    with pytest.raises(controller.ControlError):
        admission(control, MECHANICAL_ID, actor="WRITER")


def test_reviewer_requires_fresh_independent_read_only_admission():
    current = state(current_stage="FINAL_INDEPENDENT_REVIEW")
    kwargs = dict(
        observed_head=current.exact_head,
        actor="FRESH_INDEPENDENT_REVIEWER",
        surface="CHATGPT_ORDINARY_GITHUB_NATIVE",
        reasoning="HIGH",
        read_only=True,
    )
    controller.validate_independent_reviewer_admission(current, **kwargs)
    for overrides in ({"read_only": False}, {"actor": "WRITER"},
                      {"reasoning": "medium"}, {"observed_head": "0" * 40}):
        with pytest.raises(controller.ControlError):
            controller.validate_independent_reviewer_admission(
                current, **{**kwargs, **overrides}
            )


def ci_fixture():
    head = "e" * 40
    checks = [
        dict(name="contracts", id=10, head_sha=head, status="completed", conclusion="success"),
        dict(name="e4-capture", id=11, head_sha=head, status="completed", conclusion="success"),
    ]
    jobs = {
        "contracts": {
            "head_sha": head, "check_run_id": 10, "run_id": 101,
            "status": "completed", "conclusion": "success",
            "steps": [{
                "number": 7, "name": "Tests", "status": "completed",
                "conclusion": "success", "started_at": "2026-10-07T00:00:00Z",
                "completed_at": "2026-10-07T00:01:00Z",
            }],
        },
        "e4-capture": {
            "head_sha": head, "check_run_id": 11, "run_id": 102,
            "status": "completed", "conclusion": "success",
            "steps": [{
                "number": 5, "name": "Focused E4 Capture gates", "status": "completed",
                "conclusion": "success", "started_at": "2026-10-07T00:00:00Z",
                "completed_at": "2026-10-07T00:01:00Z",
            }],
        },
    }
    return dict(
        observed_head=head,
        required_checks=["contracts", "e4-capture"],
        checks=checks,
        mandatory_steps={
            "contracts": ["Tests"],
            "e4-capture": ["Focused E4 Capture gates"],
        },
        job_evidence=jobs,
    )


def test_final_review_readiness_requires_executed_exact_head_checks():
    current = state(
        current_stage="CI_WAIT", ci_head="e" * 40
    )
    kwargs = ci_fixture()
    assert controller.final_review_readiness(current, **kwargs).decision == "READY"
    assert controller.final_review_readiness(
        current, **{**kwargs, "observed_head": "0" * 40}
    ).decision == "STALE_REBIND"
    assert controller.final_review_readiness(
        state(current_stage="CI_WAIT"), **kwargs
    ).decision == "CONTROL_REPLAN"


def test_final_review_waits_for_pending_and_missing_required_ci():
    current = state(current_stage="CI_WAIT", ci_head="e" * 40)
    kwargs = ci_fixture()
    assert controller.final_review_readiness(
        current, **{**kwargs, "checks": kwargs["checks"][:1]}
    ).decision == "WAIT"
    checks = [dict(item) for item in kwargs["checks"]]
    checks[1]["status"] = "in_progress"
    assert controller.final_review_readiness(
        current, **{**kwargs, "checks": checks}
    ).decision == "WAIT"


@pytest.mark.parametrize("failed", ["failure", "cancelled", "skipped", "neutral"])
def test_final_review_rejects_failed_or_skipped_native_ci(failed):
    current = state(current_stage="CI_WAIT", ci_head="e" * 40)
    kwargs = ci_fixture()
    checks = [dict(item) for item in kwargs["checks"]]
    checks[1]["conclusion"] = failed
    assert controller.final_review_readiness(
        current, **{**kwargs, "checks": checks}
    ).decision == "CONTROL_REPLAN"


def test_final_review_fail_closes_on_missing_wrong_head_or_unexecuted_steps():
    current = state(current_stage="CI_WAIT", ci_head="e" * 40)
    kwargs = ci_fixture()
    assert controller.final_review_readiness(
        current, **{**kwargs, "mandatory_steps": {}}
    ).decision == "CONTROL_REPLAN"
    checks = [dict(item) for item in kwargs["checks"]]
    checks[1]["head_sha"] = "0" * 40
    assert controller.final_review_readiness(
        current, **{**kwargs, "checks": checks}
    ).decision == "STALE_REBIND"
    for mutation in (
        lambda x: x.pop("e4-capture"),
        lambda x: x["e4-capture"].update(check_run_id=17),
        lambda x: x["e4-capture"]["steps"][0].update(conclusion="skipped"),
        lambda x: x["e4-capture"]["steps"][0].update(started_at=None),
    ):
        import copy

        jobs = copy.deepcopy(kwargs["job_evidence"])
        mutation(jobs)
        assert controller.final_review_readiness(
            current, **{**kwargs, "job_evidence": jobs}
        ).decision == "CONTROL_REPLAN"
