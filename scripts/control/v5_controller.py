#!/usr/bin/env python3
"""Small deterministic V5 package-state controller; GitHub remains canonical."""

from __future__ import annotations

import json
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
        Stage.REPAIR_1,
        Stage.REPAIR_2,
        Stage.CONTROL_REPLAN,
        Stage.STALE_REBIND,
    },
    Stage.OPTIONAL_INTERNAL_REVIEW: {Stage.FINAL_REVIEW_READY},
    Stage.FINAL_REVIEW_READY: {Stage.FINAL_INDEPENDENT_REVIEW},
    Stage.FINAL_INDEPENDENT_REVIEW: {Stage.HUMAN_CLOSEOUT_GATE, Stage.STALE_REBIND},
    Stage.HUMAN_CLOSEOUT_GATE: {Stage.DONE},
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


def invalidate_old_head_evidence(state: PackageState, new_head: str) -> PackageState:
    if new_head == state.exact_head:
        return state
    return replace(
        state,
        exact_head=new_head,
        ci_head=None,
        ci_run_or_check_locators=[],
        last_canonical_evidence="STALE_HEAD_INVALIDATED",
        current_stage=Stage.STALE_REBIND,
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
