from __future__ import annotations

from .contracts import (
    STATE_SCHEMA_VERSION,
    DecisionRequest,
    DecisionResult,
    ModelTarget,
    QuestionPack,
)
from .model import DecisionBatch, DecisionBatchResult, build_batch_result
from .serialization import canonical_sha256
from .state import StateSchemaV0


def build_requests(
    *,
    decision_event_id: str,
    snapshot: StateSchemaV0,
    question_packs: tuple[QuestionPack, ...],
    model_targets: tuple[ModelTarget, ...],
    common_context_version: str,
    experiment_config_id: str,
    deadline_seconds: float,
) -> tuple[DecisionRequest, ...]:
    requests: list[DecisionRequest] = []
    for target in model_targets:
        for question_pack in question_packs:
            invocation_seed = {
                "decision_event_id": decision_event_id,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_hash": snapshot.snapshot_hash,
                "model_target_id": target.model_target_id,
                "arm": question_pack.arm.value,
                "question_pack_id": question_pack.question_pack_id,
                "question_pack_version": question_pack.version,
                "experiment_config_id": experiment_config_id,
            }
            invocation_id = f"sha256:{canonical_sha256(invocation_seed)}"
            requests.append(
                DecisionRequest(
                    decision_event_id=decision_event_id,
                    invocation_id=invocation_id,
                    snapshot_id=snapshot.snapshot_id,
                    snapshot_hash=snapshot.snapshot_hash,
                    data_cutoff_ns=snapshot.data_cutoff_ns,
                    state_schema_version=STATE_SCHEMA_VERSION,
                    state_payload=snapshot.compact_payload(),
                    arm=question_pack.arm,
                    question_pack=question_pack,
                    common_context_version=common_context_version,
                    experiment_config_id=experiment_config_id,
                    model_target=target,
                    deadline_seconds=deadline_seconds,
                )
            )
    return tuple(requests)


def replay_recorded_results(
    requests: tuple[DecisionRequest, ...], recorded_results: tuple[DecisionResult, ...]
) -> DecisionBatchResult:
    if not requests:
        raise ValueError("replay requires requests")
    first = requests[0]
    batch = DecisionBatch(
        decision_event_id=first.decision_event_id,
        snapshot_id=first.snapshot_id,
        snapshot_hash=first.snapshot_hash,
        data_cutoff_ns=first.data_cutoff_ns,
        requests=requests,
    )
    return build_batch_result(batch, recorded_results)
