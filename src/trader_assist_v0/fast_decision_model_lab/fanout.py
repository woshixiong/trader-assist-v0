from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .contracts import (
    DecisionModelAdapter,
    DecisionRequest,
    DecisionResult,
    ModelInvocationStatus,
)
from .model import DecisionBatch, DecisionBatchResult, build_batch_result


@dataclass(frozen=True, slots=True)
class InvocationPlan:
    adapter: DecisionModelAdapter
    request: DecisionRequest


async def _invoke_one(plan: InvocationPlan) -> DecisionResult:
    started = time.time_ns()
    try:
        result = await plan.adapter.invoke(plan.request)
    except Exception as error:  # noqa: BLE001
        finished = time.time_ns()
        return DecisionResult.failure_for(
            plan.request,
            status=ModelInvocationStatus.ADAPTER_ERROR,
            request_ts_ns=started,
            response_ts_ns=finished,
            error_code="UNEXPECTED_ADAPTER_EXCEPTION",
            error_class=type(error).__name__,
        )
    request = plan.request
    if (
        result.decision_event_id != request.decision_event_id
        or result.invocation_id != request.invocation_id
        or result.snapshot_id != request.snapshot_id
        or result.snapshot_hash != request.snapshot_hash
        or result.data_cutoff_ns != request.data_cutoff_ns
        or result.model_target != request.model_target
        or result.arm is not request.arm
        or result.question_pack_id != request.question_pack.question_pack_id
        or result.question_pack_version != request.question_pack.version
        or result.experiment_config_id != request.experiment_config_id
    ):
        finished = time.time_ns()
        return DecisionResult.failure_for(
            request,
            status=ModelInvocationStatus.VALIDATION_ERROR,
            request_ts_ns=started,
            response_ts_ns=finished,
            error_code="ADAPTER_IDENTITY_MISMATCH",
            error_class="AdapterIdentityMismatch",
        )
    return result


async def run_fanout(plans: tuple[InvocationPlan, ...]) -> DecisionBatchResult:
    if not plans:
        raise ValueError("fan-out requires at least one invocation plan")
    requests = tuple(plan.request for plan in plans)
    first = requests[0]
    batch = DecisionBatch(
        decision_event_id=first.decision_event_id,
        snapshot_id=first.snapshot_id,
        snapshot_hash=first.snapshot_hash,
        data_cutoff_ns=first.data_cutoff_ns,
        requests=requests,
    )
    results = tuple(await asyncio.gather(*(_invoke_one(plan) for plan in plans)))
    return build_batch_result(batch, results)
