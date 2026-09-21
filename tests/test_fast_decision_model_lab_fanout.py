from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from trader_assist_v0.fast_decision_model_lab.contracts import (
    ChoiceDistribution,
    DecisionRequest,
    DecisionResult,
    InputFitEvidence,
    ModelIdentity,
    ModelInvocationStatus,
    ModelTarget,
    NormalizedUsage,
    STATE_SCHEMA_VERSION,
)
from trader_assist_v0.fast_decision_model_lab.fanout import InvocationPlan, run_fanout
from trader_assist_v0.fast_decision_model_lab.model import DecisionBatch
from trader_assist_v0.fast_decision_model_lab.questions import (
    model_native_question_pack,
    strategy_informed_question_pack,
)


def _request(name: str, provider: str, *, informed: bool = False) -> DecisionRequest:
    pack = strategy_informed_question_pack() if informed else model_native_question_pack()
    return DecisionRequest(
        "event-1",
        f"inv-{name}-{pack.arm.value}",
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
            provider,
            f"model-{name}",
            f"rev-{name}",
            f"adapter-{name}",
            "1",
        ),
    )


def _success(request: DecisionRequest) -> DecisionResult:
    choices = []
    for question in request.question_pack.questions:
        p = 1.0 / len(question.allowed_labels)
        choices.append(
            (
                question.name,
                ChoiceDistribution(
                    question.allowed_labels[-1],
                    tuple((x, p) for x in question.allowed_labels),
                ),
            )
        )
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
        tuple(choices),
        10,
        20,
        0.00001,
        NormalizedUsage(),
        InputFitEvidence(False),
    )


class FakeAdapter:
    def __init__(self, *, delay: float = 0.0, failure: str | None = None) -> None:
        self.delay = delay
        self.failure = failure

    async def invoke(self, request: DecisionRequest) -> DecisionResult:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.failure == "raise":
            raise RuntimeError("boom")
        if self.failure == "timeout":
            return DecisionResult.failure_for(
                request,
                status=ModelInvocationStatus.TIMEOUT,
                request_ts_ns=1,
                response_ts_ns=2,
                error_code="TIMEOUT",
                error_class="TimeoutError",
            )
        return _success(request)


def test_single_swap_concurrent_and_arm_axis_use_same_coordinator() -> None:
    async def run() -> None:
        a = _request("a", "fake-a")
        b = _request("b", "fake-b")
        informed = _request("a", "fake-a", informed=True)
        assert len((await run_fanout((InvocationPlan(FakeAdapter(), a),))).cells) == 1
        swapped = await run_fanout((InvocationPlan(FakeAdapter(), b),))
        assert swapped.cells[0].model_target_id == "target-b"
        both = await run_fanout(
            (InvocationPlan(FakeAdapter(delay=0.01), a), InvocationPlan(FakeAdapter(), b))
        )
        assert tuple(cell.model_target_id for cell in both.cells) == ("target-a", "target-b")
        arms = await run_fanout(
            (InvocationPlan(FakeAdapter(), a), InvocationPlan(FakeAdapter(), informed))
        )
        assert len(arms.cells) == 2

    asyncio.run(run())


def test_failure_isolation_and_adapter_error_normalization() -> None:
    async def run() -> None:
        a = _request("a", "fake-a")
        b = _request("b", "fake-b")
        timed = await run_fanout(
            (
                InvocationPlan(FakeAdapter(failure="timeout"), a),
                InvocationPlan(FakeAdapter(), b),
            )
        )
        assert [cell.result.status for cell in timed.cells] == [
            ModelInvocationStatus.TIMEOUT,
            ModelInvocationStatus.SUCCESS,
        ]
        raised = await run_fanout(
            (
                InvocationPlan(FakeAdapter(failure="raise"), a),
                InvocationPlan(FakeAdapter(), b),
            )
        )
        assert [cell.result.status for cell in raised.cells] == [
            ModelInvocationStatus.ADAPTER_ERROR,
            ModelInvocationStatus.SUCCESS,
        ]

    asyncio.run(run())


def test_duplicate_cell_and_snapshot_mismatch_rejected_before_invocation() -> None:
    a = _request("a", "fake-a")
    with pytest.raises(ValueError, match="duplicate model_target x arm"):
        DecisionBatch(
            "event-1",
            a.snapshot_id,
            a.snapshot_hash,
            a.data_cutoff_ns,
            (a, replace(a, invocation_id="other")),
        )
    b = replace(_request("b", "fake-b"), snapshot_hash="other")
    with pytest.raises(ValueError, match="share event/snapshot/hash/cutoff"):
        DecisionBatch("event-1", a.snapshot_id, a.snapshot_hash, a.data_cutoff_ns, (a, b))
