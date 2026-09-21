from __future__ import annotations

from dataclasses import replace

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import (
    STATE_SCHEMA_VERSION,
    ChoiceDistribution,
    DecisionArm,
    DecisionRequest,
    DecisionResult,
    InputFitEvidence,
    ModelIdentity,
    ModelInvocationStatus,
    ModelTarget,
    NormalizedUsage,
)
from trader_assist_v0.fast_decision_model_lab.evidence import DecisionEvidenceKey
from trader_assist_v0.fast_decision_model_lab.questions import (
    ENTRY_ACTION_LABELS,
    ENTRY_ACTION_NOW,
    SETUP_DIRECTION,
    SETUP_DIRECTION_LABELS,
    SETUP_FAMILY,
    SETUP_FAMILY_LABELS,
    SETUP_STATE,
    SETUP_STATE_LABELS,
    model_native_question_pack,
    strategy_informed_question_pack,
)


def _target(name: str = "a", provider: str = "fake-a") -> ModelTarget:
    return ModelTarget(
        model_target_id=f"target-{name}",
        provider=provider,
        requested_model_id=f"model-{name}",
        requested_checkpoint_or_revision=f"rev-{name}",
        adapter_id=f"adapter-{provider}",
        adapter_version="1",
    )


def _request(*, informed: bool = False) -> DecisionRequest:
    pack = strategy_informed_question_pack() if informed else model_native_question_pack()
    return DecisionRequest(
        decision_event_id="event-1",
        invocation_id=f"inv-{pack.arm.value}",
        snapshot_id="sha256:snapshot",
        snapshot_hash="snapshot",
        data_cutoff_ns=123,
        state_schema_version=STATE_SCHEMA_VERSION,
        state_payload={"x": 1},
        arm=pack.arm,
        question_pack=pack,
        common_context_version="ctx-v1",
        experiment_config_id="exp-v1",
        model_target=_target(),
    )


def _success(request: DecisionRequest) -> DecisionResult:
    choices = []
    for question in request.question_pack.questions:
        p = 1.0 / len(question.allowed_labels)
        choices.append(
            (
                question.name,
                ChoiceDistribution(
                    selected=question.allowed_labels[-1],
                    probabilities=tuple((label, p) for label in question.allowed_labels),
                ),
            )
        )
    return DecisionResult(
        decision_event_id=request.decision_event_id,
        invocation_id=request.invocation_id,
        snapshot_id=request.snapshot_id,
        snapshot_hash=request.snapshot_hash,
        data_cutoff_ns=request.data_cutoff_ns,
        model_target=request.model_target,
        arm=request.arm,
        question_pack_id=request.question_pack.question_pack_id,
        question_pack_version=request.question_pack.version,
        experiment_config_id=request.experiment_config_id,
        status=ModelInvocationStatus.SUCCESS,
        model_identity=ModelIdentity(
            provider=request.model_target.provider,
            requested_model_id=request.model_target.requested_model_id,
            returned_model_or_checkpoint_id="returned-model",
        ),
        choices=tuple(choices),
        request_ts_ns=10,
        response_ts_ns=20,
        latency_ms=0.00001,
        usage=NormalizedUsage(input_tokens=10, output_tokens=2),
        input_fit=InputFitEvidence(state_truncated=False),
    )


def test_exact_frozen_ab_question_semantics_and_orthogonal_axes() -> None:
    native = model_native_question_pack()
    informed = strategy_informed_question_pack()
    assert native.arm is DecisionArm.MODEL_NATIVE
    assert tuple(q.name for q in native.questions) == (ENTRY_ACTION_NOW,)
    assert native.questions[0].allowed_labels == ENTRY_ACTION_LABELS
    assert informed.arm is DecisionArm.STRATEGY_INFORMED
    assert tuple(q.name for q in informed.questions) == (
        SETUP_FAMILY,
        SETUP_DIRECTION,
        SETUP_STATE,
        ENTRY_ACTION_NOW,
    )
    assert informed.questions[0].allowed_labels == SETUP_FAMILY_LABELS
    assert informed.questions[1].allowed_labels == SETUP_DIRECTION_LABELS
    assert informed.questions[2].allowed_labels == SETUP_STATE_LABELS
    assert informed.questions[3].allowed_labels == ENTRY_ACTION_LABELS
    assert _request().model_target == _request(informed=True).model_target


def test_success_rejects_state_truncation_and_failure_is_typed() -> None:
    request = _request()
    result = _success(request)
    with pytest.raises(ValueError, match="state_truncated"):
        replace(result, input_fit=InputFitEvidence(state_truncated=True))
    failed = DecisionResult.failure_for(
        request,
        status=ModelInvocationStatus.TIMEOUT,
        request_ts_ns=10,
        response_ts_ns=20,
        error_code="TIMEOUT",
        error_class="TimeoutError",
    )
    assert failed.status is ModelInvocationStatus.TIMEOUT
    assert not failed.choices


def test_required_status_vocabulary_and_evidence_identity() -> None:
    assert {item.value for item in ModelInvocationStatus} >= {
        "SUCCESS",
        "TIMEOUT",
        "PROVIDER_ERROR",
        "VALIDATION_ERROR",
        "INPUT_INVALID",
        "ADAPTER_ERROR",
    }
    native = _request()
    informed = _request(informed=True)
    native_key = DecisionEvidenceKey.from_request_result(native, _success(native))
    informed_key = DecisionEvidenceKey.from_request_result(informed, _success(informed))
    assert native_key.evidence_key_hash != informed_key.evidence_key_hash
    assert native_key.model_target_id == informed_key.model_target_id
