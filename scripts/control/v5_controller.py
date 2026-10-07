#!/usr/bin/env python3
"""Small deterministic V5 package-state controller; GitHub remains canonical."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Any

MARKER = "<!-- TRADE_OS_V5_PACKAGE_STATE_V1 -->"
MODEL_EXECUTOR_STDIN_SOURCE = "EXPLICIT"
HANDOFF_FIELDS = (
    "DECISION",
    "CANONICAL_GITHUB_REF",
    "NEXT_DESTINATION",
    "NEXT_ACTION",
    "COPY_PASTE_COMMAND_OR_PROMPT",
)
REQUIRED_FIELDS = (
    "schema_version",
    "revision",
    "package_id",
    "governance_epoch",
    "task_packet_hash",
    "exact_main",
    "exact_base",
    "exact_head",
    "exact_tree",
    "route",
    "current_stage",
    "resume_stage",
    "codex_thread_id",
    "worktree_identity",
    "pr_number",
    "ci_head",
    "ci_run_or_check_locators",
    "semantic_repair_count",
    "pause_class",
    "completed_work",
    "retained_gates",
    "last_canonical_evidence",
    "next_allowed_transition",
)


class ControlError(RuntimeError):
    pass


class Stage(StrEnum):
    CONTROL_FREEZE = "CONTROL_FREEZE"
    PLAN = "PLAN"
    PRECODE_REVIEW = "PRECODE_REVIEW"
    IMPLEMENT = "IMPLEMENT"
    LOCAL_VALIDATE = "LOCAL_VALIDATE"
    PUBLISH = "PUBLISH"
    CI_WAIT = "CI_WAIT"
    OPTIONAL_INTERNAL_REVIEW = "OPTIONAL_INTERNAL_REVIEW"
    FINAL_REVIEW_READY = "FINAL_REVIEW_READY"
    FINAL_INDEPENDENT_REVIEW = "FINAL_INDEPENDENT_REVIEW"
    HUMAN_CLOSEOUT_GATE = "HUMAN_CLOSEOUT_GATE"
    DONE = "DONE"
    PLAN_REVISE = "PLAN_REVISE"
    CONTROL_REPLAN = "CONTROL_REPLAN"
    MECHANICAL_REPAIR = "MECHANICAL_REPAIR"
    REPAIR_1 = "REPAIR_1"
    REPAIR_2 = "REPAIR_2"
    PAUSED_QUOTA = "PAUSED_QUOTA"
    PAUSED_TRANSPORT = "PAUSED_TRANSPORT"
    PAUSED_CAPABILITY = "PAUSED_CAPABILITY"
    STALE_REBIND = "STALE_REBIND"


PAUSES = {Stage.PAUSED_QUOTA, Stage.PAUSED_TRANSPORT, Stage.PAUSED_CAPABILITY}
NORMAL = {
    Stage.CONTROL_FREEZE: {Stage.PLAN},
    Stage.PLAN: {Stage.PRECODE_REVIEW},
    Stage.PRECODE_REVIEW: {Stage.IMPLEMENT, Stage.PLAN_REVISE, Stage.CONTROL_REPLAN},
    Stage.PLAN_REVISE: {Stage.PRECODE_REVIEW},
    Stage.IMPLEMENT: {Stage.LOCAL_VALIDATE},
    Stage.LOCAL_VALIDATE: {Stage.PUBLISH, Stage.REPAIR_1, Stage.REPAIR_2, Stage.CONTROL_REPLAN},
    Stage.PUBLISH: {Stage.CI_WAIT},
    Stage.CI_WAIT: {
        Stage.OPTIONAL_INTERNAL_REVIEW,
        Stage.MECHANICAL_REPAIR,
        Stage.REPAIR_1,
        Stage.REPAIR_2,
        Stage.CONTROL_REPLAN,
        Stage.STALE_REBIND,
    },
    Stage.OPTIONAL_INTERNAL_REVIEW: {Stage.FINAL_REVIEW_READY},
    Stage.FINAL_REVIEW_READY: {Stage.FINAL_INDEPENDENT_REVIEW},
    Stage.FINAL_INDEPENDENT_REVIEW: {Stage.HUMAN_CLOSEOUT_GATE, Stage.STALE_REBIND},
    Stage.HUMAN_CLOSEOUT_GATE: {Stage.DONE},
    Stage.MECHANICAL_REPAIR: {Stage.LOCAL_VALIDATE, Stage.CONTROL_REPLAN},
    Stage.REPAIR_1: {Stage.LOCAL_VALIDATE, Stage.CONTROL_REPLAN},
    Stage.REPAIR_2: {Stage.LOCAL_VALIDATE, Stage.CONTROL_REPLAN},
    Stage.STALE_REBIND: {Stage.LOCAL_VALIDATE, Stage.CONTROL_REPLAN},
}


@dataclass(frozen=True)
class PackageState:
    schema_version: str
    revision: int
    package_id: str
    governance_epoch: str
    task_packet_hash: str
    exact_main: str
    exact_base: str
    exact_head: str
    exact_tree: str
    route: str
    current_stage: str
    resume_stage: str
    codex_thread_id: str
    worktree_identity: str
    pr_number: int
    ci_head: str | None
    ci_run_or_check_locators: list[str]
    semantic_repair_count: int
    pause_class: str | None
    completed_work: list[str]
    retained_gates: list[str]
    last_canonical_evidence: str
    next_allowed_transition: str


def validate_state(state: PackageState) -> None:
    if state.schema_version != "1":
        raise ControlError("unsupported package-state schema")
    if state.revision < 0 or not state.package_id or state.semantic_repair_count not in range(3):
        raise ControlError("invalid package-state identity or repair count")
    try:
        Stage(state.current_stage)
        Stage(state.resume_stage)
    except ValueError as exc:
        raise ControlError("unknown package-state stage") from exc


def serialize_state(state: PackageState) -> str:
    validate_state(state)
    return (
        MARKER
        + "\n```json\n"
        + json.dumps(asdict(state), sort_keys=True, separators=(",", ":"))
        + "\n```\n"
    )


def parse_state(comment: str) -> PackageState:
    if comment.count(MARKER) != 1:
        raise ControlError("canonical state marker missing or ambiguous")
    try:
        payload = comment.split(MARKER, 1)[1].split("```json", 1)[1].split("```", 1)[0]
        value = json.loads(payload)
    except (IndexError, json.JSONDecodeError) as exc:
        raise ControlError("corrupt canonical package state") from exc
    if not isinstance(value, dict) or set(value) != set(REQUIRED_FIELDS):
        raise ControlError("package-state fields are missing or ambiguous")
    try:
        state = PackageState(**value)
    except TypeError as exc:
        raise ControlError("invalid package-state shape") from exc
    validate_state(state)
    return state


def validate_resume_identity(
    state: PackageState, thread_id: str, worktree: str, resumable: bool
) -> None:
    if not resumable or thread_id != state.codex_thread_id or worktree != state.worktree_identity:
        raise ControlError(
            "PAUSED_CAPABILITY: exact Codex thread/worktree resume is unavailable or mismatched"
        )



def route_family(route: str) -> str:
    """Recognize a frozen V5 family, including legacy bare 'C', without guessing."""
    if not isinstance(route, str) or not re.fullmatch(r"[ABCD](?:_[A-Z0-9_]+)?", route):
        raise ControlError("invalid frozen execution route")
    return route[0]


def _require_independent_precode(
    state: PackageState, evidence: Mapping[str, str] | None
) -> None:
    """Caller must fresh-read this exact canonical comment; a PASS string is not proof."""
    if evidence is None:
        raise ControlError("canonical independent Pre-code PASS evidence missing")
    required = {
        "REVIEW_TYPE": "PRE_CODE",
        "DECISION": "PASS",
        "FAIL_ROUTE": "NONE",
        "RESULT_EGRESS": "GITHUB_CANONICAL",
        "REVIEWER_MODE": "FRESH_ORDINARY_CHATGPT_READ_ONLY",
        "PACKAGE_ID": state.package_id,
        "FROZEN_BASE": state.exact_base,
    }
    if any(evidence.get(key) != value for key, value in required.items()):
        raise ControlError("canonical independent Pre-code evidence is incomplete or mismatched")
    if not evidence.get("REVIEW_RESULT_KEY") or not evidence.get("PLAN_REF"):
        raise ControlError("canonical independent Pre-code evidence lacks review/plan binding")
    locator = evidence.get("CANONICAL_REF", "")
    match = re.fullmatch(
        r"https://github\.com/[^/]+/[^/]+/issues/\d+#issuecomment-(\d+)", locator
    )
    if match is None or not any(
        item.endswith("PRECODE_PASS_" + match.group(1))
        for item in state.completed_work
    ):
        raise ControlError("independent Pre-code PASS is not bound to canonical package state")


def validate_execution_admission(
    state: PackageState,
    *,
    requested_route: str,
    actor: str,
    stage: str,
    event_key: str,
    observed_head: str,
    authorized_identity: Mapping[str, str],
    actual_identity: Mapping[str, str],
    precode_evidence: Mapping[str, str] | None = None,
    codex_thread_id: str = "",
    worktree_identity: str = "",
    resume_verifiable: bool = False,
) -> None:
    """Pure guard for the *admitted* entrypoint, not a universal provider bypass guard.

    The caller supplies fresh canonical route/evidence and independently observed
    actual runtime identity. Matching caller strings alone is NOT runtime proof.
    """
    validate_state(state)
    family = route_family(state.route)
    if requested_route != state.route or route_family(requested_route) != family:
        raise ControlError("frozen execution route mismatch")
    if observed_head != state.exact_head:
        raise ControlError("STALE_REBIND: execution head mismatch")
    if stage != state.current_stage or stage in {
        Stage.PAUSED_CAPABILITY, Stage.PAUSED_QUOTA, Stage.PAUSED_TRANSPORT
    }:
        raise ControlError("execution stage is not current or is paused")
    if not event_key or event_key in state.completed_work:
        raise ControlError("duplicate or missing semantic execution event")

    required_identity_fields = ("executor", "provider", "surface", "model", "reasoning")
    if any(
        field not in authorized_identity
        or field not in actual_identity
        or authorized_identity[field] != actual_identity[field]
        for field in required_identity_fields
    ):
        raise ControlError("requested/actual/frozen executor identity mismatch")

    executor = authorized_identity["executor"]
    surface = authorized_identity["surface"]
    model = authorized_identity["model"]
    reasoning = authorized_identity["reasoning"]
    if family == "A":
        if (
            actor != "DETERMINISTIC_CONTROLLER"
            or executor != "NONE"
            or model not in {"", "NONE"}
            or stage not in {"LOCAL_VALIDATE", "PUBLISH", "CI_WAIT", "MECHANICAL_REPAIR"}
        ):
            raise ControlError("Route A admits mechanical no-model execution only")
    elif family == "B":
        if (
            actor != "WRITER"
            or executor != "FRESH_ORDINARY_CHATGPT_WRITER"
            or surface != "CHATGPT_ORDINARY_GITHUB_NATIVE"
            or not model
            or reasoning != "HIGH"
            or stage not in {"IMPLEMENT", "REPAIR_1", "REPAIR_2"}
        ):
            raise ControlError("Route B requires frozen fresh ordinary ChatGPT High Writer")
        _require_independent_precode(state, precode_evidence)
    elif family == "C":
        if (
            actor != "WRITER"
            or executor != "CODEX"
            or surface != "CODEX_CLI"
            or not model
            or reasoning not in {"medium", "high"}
            or stage not in {"PLAN", "IMPLEMENT", "REPAIR_1", "REPAIR_2"}
        ):
            raise ControlError("Route C requires frozen Codex primary executor")
        if stage != "PLAN":
            _require_independent_precode(state, precode_evidence)
            validate_resume_identity(
                state, codex_thread_id, worktree_identity, resume_verifiable
            )
    else:
        if (
            actor != "ENGINEERING_CONTROL"
            or executor != "NONE"
            or model not in {"", "NONE"}
            or stage not in {"CONTROL_FREEZE", "CONTROL_REPLAN", "STALE_REBIND"}
        ):
            raise ControlError("Route D is Engineering Control only")


def validate_independent_reviewer_admission(
    state: PackageState,
    *,
    observed_head: str,
    actor: str,
    surface: str,
    reasoning: str,
    read_only: bool,
) -> None:
    """Reviewers remain fresh ordinary ChatGPT High and code read-only."""
    if observed_head != state.exact_head:
        raise ControlError("STALE_REBIND: reviewer head mismatch")
    if state.current_stage not in {"PRECODE_REVIEW", "FINAL_INDEPENDENT_REVIEW"}:
        raise ControlError("reviewer invoked at wrong stage")
    if (
        actor != "FRESH_INDEPENDENT_REVIEWER"
        or surface != "CHATGPT_ORDINARY_GITHUB_NATIVE"
        or reasoning != "HIGH"
        or not read_only
    ):
        raise ControlError("reviewer must be independent ordinary ChatGPT High read-only")


def validate_test_surface_obligation(
    *,
    required_surface: str,
    expected_head: str,
    evidence: Mapping[str, Any],
    target_host_authorized: bool = False,
) -> str:
    """Validate a Control-frozen test surface without inventing substitute proof."""
    allowed = {"LOCAL_FOCUSED", "GITHUB_V0", "GITHUB_E4_NATIVE", "TARGET_HOST"}
    if required_surface not in allowed:
        raise ControlError("unknown or unfrozen validation surface")
    if evidence.get("head") != expected_head:
        raise ControlError("STALE_REBIND: validation evidence head mismatch")
    if evidence.get("qualified") is not True:
        raise ControlError("validation surface is not qualified")
    if evidence.get("executed") is not True or evidence.get("skipped") is True:
        raise ControlError("required validation was not actually executed")

    if required_surface == "GITHUB_V0":
        if evidence.get("os") != "Linux" or evidence.get("python") != "3.12":
            raise ControlError("V0 GitHub validation environment is not qualified")
        if evidence.get("whole_repo") is not True:
            raise ControlError("V0 whole-repository test proof is missing")
    elif required_surface == "GITHUB_E4_NATIVE":
        required_native = {
            "os": "Linux",
            "arch": "x86_64",
            "python": "3.12",
            "nautilus": "2.0.0rc5",
        }
        if any(evidence.get(key) != value for key, value in required_native.items()):
            raise ControlError("E4 native rc5 validation identity mismatch")
    elif required_surface == "TARGET_HOST":
        if not target_host_authorized:
            raise ControlError("HUMAN_GATE: target-host validation is not authorized")
        if evidence.get("target_host") is not True:
            raise ControlError("target-host proof is missing")

    return required_surface


@dataclass(frozen=True)
class ReviewReadiness:
    decision: str
    blockers: tuple[str, ...] = ()


def final_review_readiness(
    state: PackageState,
    *,
    observed_head: str,
    required_checks: list[str],
    checks: list[Mapping[str, Any]],
    mandatory_steps: Mapping[str, list[str]],
    job_evidence: Mapping[str, Mapping[str, Any]],
) -> ReviewReadiness:
    """Admit a final reviewer only after genuine executed exact-head CI proof.

    Required checks and mandatory step names are Control-frozen caller inputs,
    never inferred from green status alone. Jobs/steps require native readback.
    """
    if observed_head != state.exact_head:
        return ReviewReadiness("STALE_REBIND", ("PR head drift",))
    if state.ci_head != state.exact_head:
        return ReviewReadiness("CONTROL_REPLAN", ("unbound exact-head CI",))
    if state.current_stage not in {
        "CI_WAIT", "OPTIONAL_INTERNAL_REVIEW", "FINAL_REVIEW_READY"
    }:
        return ReviewReadiness("CONTROL_REPLAN", ("review gate stage mismatch",))
    if not required_checks or len(required_checks) != len(set(required_checks)):
        return ReviewReadiness("CONTROL_REPLAN", ("missing/duplicate frozen required CI",))
    if not mandatory_steps or any(
        not steps or name not in required_checks for name, steps in mandatory_steps.items()
    ):
        return ReviewReadiness("CONTROL_REPLAN", ("mandatory test inventory missing",))

    latest: dict[str, Mapping[str, Any]] = {}
    for check in checks:
        name = check.get("name")
        if name not in required_checks:
            continue
        if check.get("head_sha") != state.exact_head:
            return ReviewReadiness("STALE_REBIND", (f"{name}: check head mismatch",))
        check_id = check.get("id")
        if not isinstance(check_id, int) or check_id <= 0:
            return ReviewReadiness("CONTROL_REPLAN", (f"{name}: unbound check run",))
        if name not in latest or check_id > int(latest[name]["id"]):
            latest[name] = check
    if any(name not in latest for name in required_checks):
        return ReviewReadiness("WAIT", ("required CI check missing/pending",))
    if any(latest[name].get("status") != "completed" for name in required_checks):
        return ReviewReadiness("WAIT", ("required CI still running",))
    if any(latest[name].get("conclusion") != "success" for name in required_checks):
        return ReviewReadiness("CONTROL_REPLAN", ("required CI failed/skipped/cancelled",))

    for name, required in mandatory_steps.items():
        job = job_evidence.get(name)
        if not job or any(
            (
                job.get("head_sha") != state.exact_head,
                job.get("check_run_id") != latest[name]["id"],
                not isinstance(job.get("run_id"), int),
                not job.get("run_id"),
                job.get("status") != "completed",
                job.get("conclusion") != "success",
            )
        ):
            return ReviewReadiness("CONTROL_REPLAN", (f"{name}: job execution unproven",))
        steps = job.get("steps")
        if not isinstance(steps, list):
            return ReviewReadiness("CONTROL_REPLAN", (f"{name}: no executed steps",))
        for required_name in required:
            matches = [step for step in steps if step.get("name") == required_name]
            if len(matches) != 1 or any(
                (
                    matches[0].get("status") != "completed",
                    matches[0].get("conclusion") != "success",
                    not isinstance(matches[0].get("number"), int),
                    not matches[0].get("started_at"),
                    not matches[0].get("completed_at"),
                )
            ):
                return ReviewReadiness(
                    "CONTROL_REPLAN", (f"{name}: mandatory step {required_name} unproven",)
                )
    return ReviewReadiness("READY")


def transition(
    state: PackageState, target: Stage, *, event_key: str, exact_head: str | None = None
) -> PackageState:
    validate_state(state)
    current = Stage(state.current_stage)
    if exact_head is not None and exact_head != state.exact_head:
        raise ControlError("STALE_REBIND: old-head event rejected")
    if event_key in state.completed_work:
        return state
    if target in PAUSES:
        result = replace(
            state,
            current_stage=target,
            resume_stage=current,
            pause_class=target,
            revision=state.revision + 1,
        )
    elif current in PAUSES:
        if target != Stage(state.resume_stage):
            raise ControlError("pause may resume only its stored stage")
        result = replace(state, current_stage=target, pause_class=None, revision=state.revision + 1)
    else:
        allowed = NORMAL.get(current, set())
        if target not in allowed:
            raise ControlError(f"illegal transition {current}->{target}")
        repairs = state.semantic_repair_count + (target in {Stage.REPAIR_1, Stage.REPAIR_2})
        if repairs > 2:
            target, repairs = Stage.CONTROL_REPLAN, state.semantic_repair_count
        result = replace(
            state,
            current_stage=target,
            resume_stage=target,
            semantic_repair_count=repairs,
            revision=state.revision + 1,
        )
    return replace(
        result,
        completed_work=[*state.completed_work, event_key],
        next_allowed_transition="CONTROLLER_COMPUTED",
    )


def invalidate_old_head_evidence(
    state: PackageState, new_head: str, new_tree: str
) -> PackageState:
    if new_head == state.exact_head:
        if new_tree != state.exact_tree:
            raise ControlError("STALE_REBIND: same head has different tree")
        return state
    return replace(
        state,
        exact_head=new_head,
        exact_tree=new_tree,
        ci_head=None,
        ci_run_or_check_locators=[],
        last_canonical_evidence="STALE_HEAD_INVALIDATED",
        current_stage=Stage.STALE_REBIND,
        resume_stage=Stage.STALE_REBIND,
        next_allowed_transition=Stage.LOCAL_VALIDATE,
        revision=state.revision + 1,
    )


@dataclass(frozen=True)
class CiObservation:
    head: str
    conclusion: str
    classification: str
    rerun_count: int = 0
    locator: str = ""


def route_ci(state: PackageState, observation: CiObservation) -> Stage:
    """Route exact-head CI without model polling or unbounded retry."""
    if observation.head != state.exact_head:
        return Stage.STALE_REBIND
    if observation.conclusion == "success":
        return Stage.OPTIONAL_INTERNAL_REVIEW
    if observation.classification == "TRANSIENT_OR_KNOWN_FLAKE":
        return Stage.CI_WAIT if observation.rerun_count < 1 else Stage.PAUSED_TRANSPORT
    if observation.classification == "DETERMINISTIC_MECHANICAL":
        return Stage.MECHANICAL_REPAIR
    if observation.classification == "SEMANTIC":
        return (
            Stage.REPAIR_1
            if state.semantic_repair_count == 0
            else Stage.REPAIR_2
            if state.semantic_repair_count == 1
            else Stage.CONTROL_REPLAN
        )
    if observation.classification in {"INFRASTRUCTURE_OR_TRANSPORT", "UNRESOLVED"}:
        return (
            Stage.PAUSED_TRANSPORT
            if observation.classification == "INFRASTRUCTURE_OR_TRANSPORT"
            else Stage.CONTROL_REPLAN
        )
    return Stage.CONTROL_REPLAN


class CanonicalCommentStore:
    """CAS-like read/validate/write/readback adapter supplied by a gh caller."""

    def __init__(
        self, comment_id: str, read: Callable[[str], str], write: Callable[[str, str], None]
    ):
        self.comment_id, self.read, self.write = comment_id, read, write

    def update(
        self, expected_revision: int, expected_stage: Stage, event_key: str, target: Stage
    ) -> PackageState:
        current = parse_state(self.read(self.comment_id))
        # Delivery is at-least-once. A completed event is already canonical even
        # when its duplicate carries the original pre-transition preconditions.
        if event_key in current.completed_work:
            return current
        if current.revision != expected_revision or current.current_stage != expected_stage:
            raise ControlError("canonical state revision/stage precondition failed")
        desired = transition(current, target, event_key=event_key)
        if desired == current:
            return current
        rendered = serialize_state(desired)
        self.write(self.comment_id, rendered)
        if parse_state(self.read(self.comment_id)) != desired:
            raise ControlError("ambiguous canonical state write/readback")
        return desired


def reconcile_push(
    readback_head: str | None, expected_head: str, mutation_known_absent: bool
) -> str:
    if readback_head == expected_head:
        return "PUSH_CONFIRMED"
    if mutation_known_absent:
        return "SAFE_RETRY"
    raise ControlError("PAUSED_TRANSPORT: ambiguous mutation without canonical readback")


def validate_draft_pr(pr: Mapping[str, Any], state: PackageState) -> None:
    if pr.get("number") != state.pr_number or pr.get("headRefOid") != state.exact_head:
        raise ControlError("bound Draft PR identity/head mismatch")
    if pr.get("isDraft") is not True or pr.get("state") != "OPEN":
        raise ControlError("bound PR must remain open Draft")


def validate_review(
    result: Mapping[str, Any], state: PackageState, existing_keys: set[str]
) -> None:
    required = {"REVIEW_TYPE", "REVIEW_RESULT_KEY", "DECISION", "RESULT_EGRESS", "HEAD"}
    if not required <= set(result):
        raise ControlError("review egress is incomplete")
    if result["HEAD"] != state.exact_head:
        raise ControlError("stale review result")
    if result["REVIEW_RESULT_KEY"] in existing_keys:
        return
    if result["RESULT_EGRESS"] != "GITHUB_CANONICAL":
        raise ControlError("review is incomplete without canonical egress")
    if result.get("REVIEW_SUBMISSION_MODE", "COMMENT_ONLY") not in {
        "COMMENT_ONLY",
        "NATIVE_REVIEW",
    }:
        raise ControlError("invalid review submission mode")


def render_resume_command(thread: str, prompt: str, *, prompt_file: str | None = None) -> str:
    if prompt_file:
        return f"codex exec resume {thread!r} - < {prompt_file!r}"
    return f"codex exec resume {thread!r} {prompt!r} </dev/null"


def validate_workflow_publication(changed_paths: list[str], workflow_scope_verified: bool) -> None:
    if (
        any(path.startswith(".github/workflows/") for path in changed_paths)
        and not workflow_scope_verified
    ):
        raise ControlError(
            "PAUSED_CAPABILITY: GH_WORKFLOW_SCOPE_VERIFIED=YES is required "
            "before workflow publication"
        )


def render_handoff(values: Mapping[str, str]) -> str:
    if set(values) != set(HANDOFF_FIELDS) or any(not values[k] for k in HANDOFF_FIELDS):
        raise ControlError("handoff is incomplete")
    return "\n".join(f"{key}={values[key]}" for key in HANDOFF_FIELDS)
