from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import (
    STATE_SCHEMA_VERSION,
    ChoiceDistribution,
    DecisionRequest,
    DecisionResult,
    InputFitEvidence,
    ModelIdentity,
    ModelInvocationStatus,
    ModelTarget,
    NormalizedUsage,
)
from trader_assist_v0.fast_decision_model_lab.experiment import ExperimentRecordV0
from trader_assist_v0.fast_decision_model_lab.model import DecisionBatch, build_batch_result
from trader_assist_v0.fast_decision_model_lab.questions import model_native_question_pack
from trader_assist_v0.fast_decision_model_lab.replay import (
    ReplayArtifactV0,
    replay_recorded_results,
)


def _request(name: str) -> DecisionRequest:
    pack = model_native_question_pack()
    return DecisionRequest(
        "event-1",
        f"inv-{name}",
        "sha256:snapshot",
        "snapshot",
        123,
        STATE_SCHEMA_VERSION,
        {"x": 1},
        pack.arm,
        pack,
        "ctx-v1",
        "exp-v1",
        ModelTarget(
            f"target-{name}",
            f"fake-{name}",
            f"model-{name}",
            f"rev-{name}",
            f"adapter-{name}",
            "1",
        ),
    )


def _result(request: DecisionRequest, response_ts: int) -> DecisionResult:
    labels = request.question_pack.questions[0].allowed_labels
    p = 1.0 / len(labels)
    return DecisionResult(
        request.decision_event_id,
        request.invocation_id,
        request.snapshot_id,
        request.snapshot_hash,
        request.data_cutoff_ns,
        request.model_target,
        request.arm,
        request.question_pack.question_pack_id,
        request.question_pack.version,
        request.experiment_config_id,
        ModelInvocationStatus.SUCCESS,
        ModelIdentity(
            request.model_target.provider,
            request.model_target.requested_model_id,
            "returned",
        ),
        (
            (
                request.question_pack.questions[0].name,
                ChoiceDistribution(labels[-1], tuple((x, p) for x in labels)),
            ),
        ),
        10,
        response_ts,
        (response_ts - 10) / 1_000_000,
        NormalizedUsage(),
        InputFitEvidence(False),
    )


def test_completion_order_and_replay_are_canonical() -> None:
    a, b = _request("a"), _request("b")
    batch = DecisionBatch("event-1", a.snapshot_id, a.snapshot_hash, a.data_cutoff_ns, (a, b))
    ra, rb = _result(a, 20), _result(b, 30)
    first = build_batch_result(batch, (ra, rb))
    second = build_batch_result(batch, (rb, ra))
    assert first == second
    assert first.batch_hash == second.batch_hash
    replayed = replay_recorded_results((a, b), (rb, ra))
    assert replayed.batch_hash == first.batch_hash


def test_replay_artifact_identity_is_stable_and_snapshots_evidence() -> None:
    evidence = {"b": [2, 3], "a": 1}
    experiment = ExperimentRecordV0(
        experiment_id="experiment-1",
        timestamp=datetime(2026, 9, 22, tzinfo=UTC),
        state_hash="sha256:state",
        model_identity=ModelIdentity("provider", "requested", "returned"),
        decision_event_id="event-1",
        request_identity="sha256:request",
        result_identity="sha256:result",
    )
    first = ReplayArtifactV0(
        experiment_record=experiment,
        evidence_payload=evidence,
        input_identity="sha256:input",
    )
    second = ReplayArtifactV0(
        experiment_record=experiment,
        evidence_payload={"a": 1, "b": [2, 3]},
        input_identity="sha256:input",
    )

    evidence["a"] = 99
    assert first.replay_identity == second.replay_identity
    assert first.evidence_payload == {"a": 1, "b": [2, 3]}


def test_experiment_factory_reuses_full_model_output_identity_contract() -> None:
    request = _request("a")
    result = _result(request, 20)
    ExperimentRecordV0.from_request_result(
        experiment_id="experiment-1",
        timestamp=datetime(2026, 9, 22, tzinfo=UTC),
        request=request,
        result=result,
    )

    with pytest.raises(ValueError, match="identity mismatch"):
        ExperimentRecordV0.from_request_result(
            experiment_id="experiment-1",
            timestamp=datetime(2026, 9, 22, tzinfo=UTC),
            request=request,
            result=replace(result, data_cutoff_ns=result.data_cutoff_ns + 1),
        )
