from __future__ import annotations

from dataclasses import dataclass

from .contracts import DecisionArm, DecisionRequest, DecisionResult
from .serialization import canonical_sha256


@dataclass(frozen=True, slots=True)
class DecisionEvidenceKey:
    decision_event_id: str
    snapshot_id: str
    snapshot_hash: str
    data_cutoff_ns: int
    model_target_id: str
    provider: str
    requested_model_id: str
    returned_model_or_checkpoint_id: str | None
    arm: DecisionArm
    invocation_id: str
    question_pack_id: str
    question_pack_version: str
    state_schema_version: str
    experiment_config_id: str

    @property
    def evidence_key_hash(self) -> str:
        return canonical_sha256(self)

    @classmethod
    def from_request_result(
        cls, request: DecisionRequest, result: DecisionResult
    ) -> "DecisionEvidenceKey":
        if result.invocation_id != request.invocation_id:
            raise ValueError("request/result invocation identity mismatch")
        return cls(
            decision_event_id=request.decision_event_id,
            snapshot_id=request.snapshot_id,
            snapshot_hash=request.snapshot_hash,
            data_cutoff_ns=request.data_cutoff_ns,
            model_target_id=request.model_target.model_target_id,
            provider=request.model_target.provider,
            requested_model_id=request.model_target.requested_model_id,
            returned_model_or_checkpoint_id=result.model_identity.returned_model_or_checkpoint_id,
            arm=request.arm,
            invocation_id=request.invocation_id,
            question_pack_id=request.question_pack.question_pack_id,
            question_pack_version=request.question_pack.version,
            state_schema_version=request.state_schema_version,
            experiment_config_id=request.experiment_config_id,
        )
