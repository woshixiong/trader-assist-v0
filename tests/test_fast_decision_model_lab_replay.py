from __future__ import annotations

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
from trader_assist_v0.fast_decision_model_lab.model import DecisionBatch, build_batch_result
from trader_assist_v0.fast_decision_model_lab.questions import model_native_question_pack
from trader_assist_v0.fast_decision_model_lab.replay import replay_recorded_results


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
