from __future__ import annotations

import json
from dataclasses import dataclass

from .contracts import (
    STATE_SCHEMA_VERSION,
    DecisionRequest,
    DecisionResult,
    ModelTarget,
    QuestionPack,
)
from .experiment import ExperimentRecordV0
from .model import DecisionBatch, DecisionBatchResult, build_batch_result
from .serialization import canonical_json, canonical_sha256
from .state import StateSchemaV0

REPLAY_ARTIFACT_SCHEMA_VERSION = "fdml.replay-artifact.v0"


@dataclass(frozen=True, slots=True, init=False)
class ReplayArtifactV0:
    """Immutable replay identity over recorded evidence and its exact input."""

    experiment_record: ExperimentRecordV0
    input_identity: str
    schema_version: str
    _evidence_payload_json: str

    def __init__(
        self,
        *,
        experiment_record: ExperimentRecordV0,
        evidence_payload: object,
        input_identity: str,
        schema_version: str = REPLAY_ARTIFACT_SCHEMA_VERSION,
    ) -> None:
        if not input_identity.strip():
            raise ValueError("input_identity must be non-empty")
        if schema_version != REPLAY_ARTIFACT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {REPLAY_ARTIFACT_SCHEMA_VERSION}")
        object.__setattr__(self, "experiment_record", experiment_record)
        object.__setattr__(self, "input_identity", input_identity)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "_evidence_payload_json", canonical_json(evidence_payload))

    @property
    def evidence_payload(self) -> object:
        return json.loads(self._evidence_payload_json)

    def identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "experiment_record_identity": self.experiment_record.record_identity,
            "evidence_payload": self.evidence_payload,
            "input_identity": self.input_identity,
        }

    @property
    def replay_identity(self) -> str:
        return canonical_sha256(self.identity_payload())

    @property
    def stable_identity(self) -> str:
        return self.replay_identity

    def canonical_json(self) -> str:
        return canonical_json(
            {**self.identity_payload(), "experiment_record": self.experiment_record.to_payload()}
        )


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
