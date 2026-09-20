# mypy: disable-error-code="import-not-found"
"""Rooted Real-T2 mechanical evidence with no local formal-credit authority.

The local plane can rebuild and compare an exact mechanical candidate.  Formal
Real-T2 acceptance belongs to the canonical GitHub control plane and is not
represented by any authority-bearing object or positive path in this module.
"""

from __future__ import annotations

import argparse
import base64
import hmac
import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from trader_assist_v0.contracts.common import (
    GitCommitOid,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)

SOURCE_ROOT_SCHEMA_VERSION: Literal["ROOTED_T2_SOURCE_V1"] = "ROOTED_T2_SOURCE_V1"
ARTIFACT_CANDIDATE_SCHEMA_VERSION: Literal["ROOTED_T2_CANDIDATE_V2"] = (
    "ROOTED_T2_CANDIDATE_V2"
)
ACCEPTANCE_EVIDENCE_SCHEMA_VERSION: Literal["ROOTED_T2_ACCEPTANCE_EVIDENCE_V1"] = (
    "ROOTED_T2_ACCEPTANCE_EVIDENCE_V1"
)
_ARTIFACT_DOMAIN = b"trader-assist-v0/rooted-t2/source-artifact/v1\0"
_ROOT_DOMAIN = b"trader-assist-v0/rooted-t2/source-root/v1\0"
_CANDIDATE_DOMAIN = b"trader-assist-v0/rooted-t2/artifact-candidate/v2\0"
_RECEIPT_EVIDENCE_DOMAIN = b"trader-assist-v0/rooted-t2/receipt-evidence/v1\0"


class T2SourceRole(StrEnum):
    E4_RUN_MANIFEST = "E4_RUN_MANIFEST"
    E4_PIT_SNAPSHOT = "E4_PIT_SNAPSHOT"
    E4_ADMISSION = "E4_ADMISSION"
    E4_LIFECYCLE = "E4_LIFECYCLE"
    E4_CONTINUITY = "E4_CONTINUITY_CHECKPOINT_PROCESS_SEGMENT_EVIDENCE"
    STRUCTURAL_SOURCE = "STRUCTURAL_SOURCE_ARTIFACT"
    CAUSAL_LINEAGE = "CAUSAL_LINEAGE"
    RESTART_REFERENCE = "RESTART_REFERENCE_EVIDENCE"
    RESTART_REFERENCE_SOURCE = "RESTART_REFERENCE_SOURCE"
    EVALUATOR_SUPPLEMENT = "EVALUATOR_SUPPLEMENT"
    EVALUATOR_SUPPLEMENT_SOURCE = "EVALUATOR_SUPPLEMENT_SOURCE"
    MARKET_EXPRESSION = "MARKET_EXPRESSION_AUTHORITY"
    REGISTRY_MARKET = "REGISTRY_MARKET_METADATA_AUTHORITY"
    VALIDATION_REFERENCE = "VALIDATION_REFERENCE"
    VALIDATION_SOURCE = "VALIDATION_SOURCE"
    G4_RUN_MANIFEST = "G4_RUN_MANIFEST"
    SELECTED_CANDIDATE = "SELECTED_CANDIDATE_MANIFEST"
    PROVIDER_INSTRUMENT_WIRE = "PROVIDER_INSTRUMENT_LOSSLESS_PUBLIC_WIRE"
    INSTRUMENT_METADATA = "INSTRUMENT_METADATA_SOURCE"
    THESIS_OUTCOME = "SOURCE_THESIS_OUTCOME"
    COST_SOURCE = "COST_COMPONENT_ROLE_APPROPRIATE_SOURCE"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceReference(_FrozenModel):
    """A role-sensitive edge in the transitive evidence graph."""

    role: T2SourceRole
    name: str = Field(min_length=1, max_length=200)
    artifact_hash: Sha256Hex


class RoleBoundSourceArtifact(_FrozenModel):
    """Exact bytes assigned to one semantic role and stable serialization name."""

    role: T2SourceRole
    name: str = Field(min_length=1, max_length=200)
    exact_bytes_b64: str = Field(min_length=1)
    references: tuple[SourceReference, ...] = ()
    artifact_hash: Sha256Hex

    def exact_bytes(self) -> bytes:
        try:
            return base64.b64decode(self.exact_bytes_b64, validate=True)
        except ValueError as exc:
            raise ValueError("exact_bytes_b64 is not canonical base64") from exc

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"artifact_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        raw = self.exact_bytes()
        if base64.b64encode(raw).decode("ascii") != self.exact_bytes_b64:
            raise ValueError("exact_bytes_b64 is not canonical base64")
        ordered = tuple(sorted(self.references, key=lambda item: (item.role, item.name)))
        if self.references != ordered or len({(x.role, x.name) for x in ordered}) != len(ordered):
            raise ValueError("source references must be unique and sorted by role/name")
        expected = sha256_hex(_ARTIFACT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.artifact_hash, expected):
            raise ValueError("artifact_hash does not bind role, name, exact bytes and references")
        return self

    @classmethod
    def create(
        cls,
        *,
        role: T2SourceRole,
        name: str,
        exact_bytes: bytes,
        references: tuple[SourceReference, ...] = (),
    ) -> Self:
        values: dict[str, object] = {
            "role": role,
            "name": name,
            "exact_bytes_b64": base64.b64encode(exact_bytes).decode("ascii"),
            "references": tuple(sorted(references, key=lambda item: (item.role, item.name))),
        }
        return cls.model_validate(
            {**values, "artifact_hash": sha256_hex(_ARTIFACT_DOMAIN + canonical_json_bytes(values))}
        )


class T2SourceRootSnapshot(_FrozenModel):
    """Complete role-typed source closure; valid construction grants no authority."""

    schema_version: Literal["ROOTED_T2_SOURCE_V1"] = SOURCE_ROOT_SCHEMA_VERSION
    task_id: str = Field(min_length=1)
    governance_epoch: Sha256Hex
    acquisition_plan_hash: Sha256Hex
    exact_source_git_head: GitCommitOid
    exact_source_git_tree: GitCommitOid
    e4_run_manifest_hash: Sha256Hex
    e4_pit_snapshot_hash: Sha256Hex
    g4_run_manifest_hash: Sha256Hex
    selected_candidate_hash: Sha256Hex
    strategy_package_identity: str = Field(min_length=1)
    validation_reference_hash: Sha256Hex
    artifacts: tuple[RoleBoundSourceArtifact, ...] = Field(min_length=1)
    source_root_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"source_root_hash"})

    def artifact(self, role: T2SourceRole, name: str) -> RoleBoundSourceArtifact:
        matches = tuple(item for item in self.artifacts if item.role is role and item.name == name)
        if len(matches) != 1:
            raise ValueError(f"source root has no unique {role.value}:{name}")
        return matches[0]

    @model_validator(mode="after")
    def verify_closure(self) -> Self:
        ordered = tuple(sorted(self.artifacts, key=lambda item: (item.role, item.name)))
        keys = tuple((item.role, item.name) for item in self.artifacts)
        if self.artifacts != ordered or len(keys) != len(set(keys)):
            raise ValueError("source artifacts must be unique and sorted by role/name")
        by_key = {(item.role, item.name): item for item in self.artifacts}
        for owner in self.artifacts:
            for reference in owner.references:
                target = by_key.get((reference.role, reference.name))
                if target is None:
                    raise ValueError("transitive source reference is unresolved")
                if not hmac.compare_digest(target.artifact_hash, reference.artifact_hash):
                    raise ValueError("transitive source reference has wrong role or exact hash")
        required = {
            T2SourceRole.E4_RUN_MANIFEST: self.e4_run_manifest_hash,
            T2SourceRole.E4_PIT_SNAPSHOT: self.e4_pit_snapshot_hash,
            T2SourceRole.G4_RUN_MANIFEST: self.g4_run_manifest_hash,
            T2SourceRole.SELECTED_CANDIDATE: self.selected_candidate_hash,
            T2SourceRole.VALIDATION_REFERENCE: self.validation_reference_hash,
        }
        for role, digest in required.items():
            if not any(
                item.role is role and hmac.compare_digest(item.artifact_hash, digest)
                for item in self.artifacts
            ):
                raise ValueError(
                    f"declared {role.value} hash is not rooted under its required role"
                )
        expected = sha256_hex(_ROOT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.source_root_hash, expected):
            raise ValueError("source_root_hash does not bind the complete source graph")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        raw_artifacts = cast(tuple[object, ...], values["artifacts"])
        supplied = tuple(
            item
            if isinstance(item, RoleBoundSourceArtifact)
            else RoleBoundSourceArtifact.model_validate(item)
            for item in raw_artifacts
        )
        artifacts = tuple(sorted(supplied, key=lambda item: (item.role, item.name)))
        payload = {"schema_version": SOURCE_ROOT_SCHEMA_VERSION, **values, "artifacts": artifacts}
        return cls.model_validate(
            {
                **payload,
                "source_root_hash": sha256_hex(
                    _ROOT_DOMAIN + canonical_json_bytes(payload)
                ),
            }
        )


class RootedT2Rederivation(_FrozenModel):
    """Mechanical identities emitted by existing semantic owners."""

    source_root_hash: Sha256Hex
    thesis_id: str = Field(min_length=1)
    market_id: Sha256Hex
    decision: Literal["TAKE"]
    evaluation_inputs_hash: Sha256Hex
    participation_result_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    replay_projection_hash: Sha256Hex
    provider_execution_record_hash: Sha256Hex
    provider_state_source_hash: Sha256Hex
    provider_instrument_wire_hash: Sha256Hex
    thesis_outcome_hash: Sha256Hex
    cost_source_hashes: tuple[Sha256Hex, ...]

    @model_validator(mode="after")
    def verify_cost_order(self) -> Self:
        if self.cost_source_hashes != tuple(sorted(set(self.cost_source_hashes))):
            raise ValueError("cost source hashes must be unique and sorted")
        return self

    def owner_payload(self) -> dict[str, object]:
        """Semantic-owner result, excluding the serialization-root wrapper identity."""
        return self.model_dump(mode="json", exclude={"source_root_hash"})


class T2ArtifactCandidate(_FrozenModel):
    """Mechanical candidate constructible only from a root/rederivation pair.

    The object is deliberately not deserializable through public Pydantic model
    helpers.  It is still non-authoritative: only ``verify_mechanical_t2`` can
    accept it mechanically, and that function always launches a fresh child.
    """

    schema_version: Literal["ROOTED_T2_CANDIDATE_V2"] = ARTIFACT_CANDIDATE_SCHEMA_VERSION
    task_id: str
    governance_epoch: Sha256Hex
    source_root_hash: Sha256Hex
    thesis_id: str
    market_id: Sha256Hex
    decision: Literal["TAKE"]
    evaluation_inputs_hash: Sha256Hex
    participation_result_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    replay_projection_hash: Sha256Hex
    provider_execution_record_hash: Sha256Hex
    provider_state_source_hash: Sha256Hex
    provider_instrument_wire_hash: Sha256Hex
    thesis_outcome_hash: Sha256Hex
    transitive_cost_source_hashes: tuple[Sha256Hex, ...]
    formal_real_t2_credit: Literal[False] = False
    real_t2_credit: Literal[False] = False
    g4_promotion: Literal[False] = False
    deployment_ready: Literal[False] = False
    trading_ready: Literal[False] = False
    candidate_hash: Sha256Hex

    _DESERIALIZATION_ERROR: ClassVar[str] = (
        "T2ArtifactCandidate requires exact root and RootedT2Rederivation inputs"
    )

    def __init__(
        self,
        *,
        root: T2SourceRootSnapshot,
        rederivation: RootedT2Rederivation,
    ) -> None:
        if not hmac.compare_digest(root.source_root_hash, rederivation.source_root_hash):
            raise ValueError("rederivation does not bind the exact source root")
        payload: dict[str, object] = {
            "schema_version": ARTIFACT_CANDIDATE_SCHEMA_VERSION,
            "task_id": root.task_id,
            "governance_epoch": root.governance_epoch,
            "source_root_hash": root.source_root_hash,
            "thesis_id": rederivation.thesis_id,
            "market_id": rederivation.market_id,
            "decision": rederivation.decision,
            "evaluation_inputs_hash": rederivation.evaluation_inputs_hash,
            "participation_result_hash": rederivation.participation_result_hash,
            "order_intent_hash": rederivation.order_intent_hash,
            "replay_projection_hash": rederivation.replay_projection_hash,
            "provider_execution_record_hash": rederivation.provider_execution_record_hash,
            "provider_state_source_hash": rederivation.provider_state_source_hash,
            "provider_instrument_wire_hash": rederivation.provider_instrument_wire_hash,
            "thesis_outcome_hash": rederivation.thesis_outcome_hash,
            "transitive_cost_source_hashes": rederivation.cost_source_hashes,
            "formal_real_t2_credit": False,
            "real_t2_credit": False,
            "g4_promotion": False,
            "deployment_ready": False,
            "trading_ready": False,
        }
        candidate_values = {
            **payload,
            "candidate_hash": sha256_hex(
                _CANDIDATE_DOMAIN + canonical_json_bytes(payload)
            ),
        }
        BaseModel.__init__(self, **candidate_values)

    @classmethod
    def model_validate(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError(cls._DESERIALIZATION_ERROR)

    @classmethod
    def model_validate_json(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError(cls._DESERIALIZATION_ERROR)

    @classmethod
    def model_construct(cls, *_args: object, **_kwargs: object) -> Self:
        raise TypeError(cls._DESERIALIZATION_ERROR)


class AcceptedRealT2Receipt(_FrozenModel):
    """Locally serializable copy of receipt evidence; never an acceptance token."""

    schema_version: Literal["ROOTED_T2_ACCEPTANCE_EVIDENCE_V1"] = (
        ACCEPTANCE_EVIDENCE_SCHEMA_VERSION
    )
    acceptance_claim: Literal["ACCEPTED"]
    task_id: str
    governance_epoch: Sha256Hex
    accepted_t2_source_root_hash: Sha256Hex
    t2_artifact_candidate_hash: Sha256Hex
    exact_implementation_head: GitCommitOid
    exact_implementation_tree: GitCommitOid
    required_ci_run_ids_and_conclusions: tuple[str, ...] = Field(min_length=1)
    fresh_independent_review_result_key: str = Field(min_length=1)
    fresh_independent_review_locator: str = Field(min_length=1)
    fresh_independent_review_verdict: Literal["PASS"]
    exact_reviewed_head: GitCommitOid
    canonical_acceptance_receipt_key: str = Field(min_length=1)
    evidence_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_hash"})

    @model_validator(mode="after")
    def verify_integrity_only(self) -> Self:
        expected = sha256_hex(
            _RECEIPT_EVIDENCE_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.evidence_hash, expected):
            raise ValueError("evidence_hash does not bind the copied receipt evidence")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload = {"schema_version": ACCEPTANCE_EVIDENCE_SCHEMA_VERSION, **values}
        return cls.model_validate(
            {
                **payload,
                "evidence_hash": sha256_hex(
                    _RECEIPT_EVIDENCE_DOMAIN + canonical_json_bytes(payload)
                ),
            }
        )


class CanonicalAcceptanceExpectation(_FrozenModel):
    """Copied canonical-looking fields; local construction has zero authority."""

    task_id: str
    governance_epoch: Sha256Hex
    source_root_hash: Sha256Hex
    candidate_hash: Sha256Hex
    implementation_head: GitCommitOid
    implementation_tree: GitCommitOid
    required_ci_run_ids_and_conclusions: tuple[str, ...] = Field(min_length=1)
    independent_review_result_key: str = Field(min_length=1)
    independent_review_locator: str = Field(min_length=1)
    exact_reviewed_head: GitCommitOid
    canonical_receipt_key: str = Field(min_length=1)
    copied_receipt_evidence_hash: Sha256Hex


class RealT2AcceptanceDecision(_FrozenModel):
    """Non-authoritative local comparison result; formal credit is impossible."""

    evidence_consistent: bool
    claimed_accepted: bool
    formal_real_t2_credit: Literal[False] = False
    real_t2_credit: Literal[False] = False
    reason: Literal["LOCAL_ACCEPTANCE_EVIDENCE_IS_NON_AUTHORITATIVE"] = (
        "LOCAL_ACCEPTANCE_EVIDENCE_IS_NON_AUTHORITATIVE"
    )


class MechanicalT2Verification(_FrozenModel):
    mechanically_verified: Literal[True] = True
    source_root_hash: Sha256Hex
    candidate_hash: Sha256Hex
    fresh_child_candidate_hash: Sha256Hex
    formal_real_t2_credit: Literal[False] = False
    real_t2_credit: Literal[False] = False
    g4_promotion: Literal[False] = False


def assess_local_acceptance_evidence(
    *,
    receipt: AcceptedRealT2Receipt,
    canonical: CanonicalAcceptanceExpectation,
) -> RealT2AcceptanceDecision:
    """Compare copied evidence without representing or granting formal authority."""
    pairs = (
        (receipt.task_id, canonical.task_id),
        (receipt.governance_epoch, canonical.governance_epoch),
        (receipt.accepted_t2_source_root_hash, canonical.source_root_hash),
        (receipt.t2_artifact_candidate_hash, canonical.candidate_hash),
        (receipt.exact_implementation_head, canonical.implementation_head),
        (receipt.exact_implementation_tree, canonical.implementation_tree),
        (
            receipt.required_ci_run_ids_and_conclusions,
            canonical.required_ci_run_ids_and_conclusions,
        ),
        (receipt.fresh_independent_review_result_key, canonical.independent_review_result_key),
        (receipt.fresh_independent_review_locator, canonical.independent_review_locator),
        (receipt.exact_reviewed_head, canonical.exact_reviewed_head),
        (receipt.canonical_acceptance_receipt_key, canonical.canonical_receipt_key),
        (receipt.evidence_hash, canonical.copied_receipt_evidence_hash),
    )
    return RealT2AcceptanceDecision(
        evidence_consistent=all(left == right for left, right in pairs),
        claimed_accepted=receipt.acceptance_claim == "ACCEPTED",
    )


def _one(root: T2SourceRootSnapshot, role: T2SourceRole) -> RoleBoundSourceArtifact:
    matches = tuple(item for item in root.artifacts if item.role is role)
    if len(matches) != 1:
        raise ValueError(f"source root requires exactly one {role.value} artifact")
    return matches[0]


def _many(root: T2SourceRootSnapshot, role: T2SourceRole) -> tuple[RoleBoundSourceArtifact, ...]:
    matches = tuple(item for item in root.artifacts if item.role is role)
    if not matches:
        raise ValueError(f"source root requires at least one {role.value} artifact")
    return matches


def _parse(artifact: RoleBoundSourceArtifact, target: Any) -> Any:
    return TypeAdapter(target).validate_json(artifact.exact_bytes())


def rederive_rooted_t2(
    *, root: T2SourceRootSnapshot, catalog_path: str | Path
) -> RootedT2Rederivation:
    """Rederive the complete mechanical T2 result from rooted bytes only."""
    from trader_assist_v0.multi_asset_shadow.models import RegistryMarket
    from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import StrategyDecision
    from trader_assist_v0.nautilus_e4.contracts import (
        AdmittedEvent,
        DataKind,
        EvidenceState,
        LifecycleRecord,
        MarketExpression,
    )
    from trader_assist_v0.nautilus_g4.catalog_bridge import (
        EvaluatorSupplementEvidence,
        admit_hypothetical_order_intent,
        derive_evaluation_admission,
        project_native_replay,
    )
    from trader_assist_v0.nautilus_g4.runner import execute_provider_native_state
    from trader_assist_v0.vnext_g4.contracts import (
        CandidateManifest,
        CausalLineage,
        DerivationStatus,
        G4RunManifest,
        ParticipationDecision,
        PositionSide,
        RestartReferenceEvidence,
        ValidationReference,
    )
    from trader_assist_v0.vnext_g4.evaluator import evaluate_participation
    from trader_assist_v0.vnext_g4.reporting import CostProvenance, ThesisOutcome

    structural_artifact = _one(root, T2SourceRole.STRUCTURAL_SOURCE)
    structural = cast(StrategyDecision, _parse(structural_artifact, StrategyDecision))
    lineage = cast(CausalLineage, _parse(_one(root, T2SourceRole.CAUSAL_LINEAGE), CausalLineage))
    candidate = cast(
        CandidateManifest, _parse(_one(root, T2SourceRole.SELECTED_CANDIDATE), CandidateManifest)
    )
    g4 = cast(G4RunManifest, _parse(_one(root, T2SourceRole.G4_RUN_MANIFEST), G4RunManifest))
    if candidate.candidate_hash not in g4.candidate_hashes:
        raise ValueError("rooted selected candidate is not a member of the rooted G4 run")
    if candidate.structural_component_manifest_hash != structural_artifact.artifact_hash:
        raise ValueError("selected candidate does not bind the exact structural source bytes")
    if (
        structural.market_id != lineage.market_id
        or structural.market_event_id != lineage.formal_setup_id
    ):
        raise ValueError("structural decision and lineage do not form one causal unit")

    expression = cast(
        MarketExpression, _parse(_one(root, T2SourceRole.MARKET_EXPRESSION), MarketExpression)
    )
    admissions = tuple(
        sorted(
            (
                cast(AdmittedEvent, _parse(item, AdmittedEvent))
                for item in _many(root, T2SourceRole.E4_ADMISSION)
            ),
            key=lambda item: (item.admission_ordinal, item.admission_ts, item.admission_hash),
        )
    )
    bbo = tuple(
        item
        for item in admissions
        if item.source.data_kind is DataKind.BBO
        and item.source.market_id == lineage.market_id
        and item.source.expression_id == expression.expression_id
        and item.source.instrument_id == lineage.instrument_id
        and item.continuity_state is EvidenceState.COMPLETE
        and not item.out_of_order
    )
    if not bbo:
        raise ValueError("complete rooted evidence has no causally eligible BBO")
    current_bbo = max(
        bbo, key=lambda item: (item.admission_ordinal, item.admission_ts, item.admission_hash)
    )
    lifecycle = tuple(
        sorted(
            (
                cast(LifecycleRecord, _parse(item, LifecycleRecord))
                for item in _many(root, T2SourceRole.E4_LIFECYCLE)
            ),
            key=lambda item: (item.state_ts, item.last_admission_ordinal, item.record_hash),
        )
    )
    restarts = tuple(
        sorted(
            (
                cast(RestartReferenceEvidence, _parse(item, RestartReferenceEvidence))
                for item in _many(root, T2SourceRole.RESTART_REFERENCE)
            ),
            key=lambda item: (
                item.confirmed_admission_ordinal,
                item.confirmed_admission_ts,
                item.reference_hash,
            ),
        )
    )
    validation = cast(
        ValidationReference,
        _parse(_one(root, T2SourceRole.VALIDATION_REFERENCE), ValidationReference),
    )
    supplement = cast(
        EvaluatorSupplementEvidence,
        _parse(_one(root, T2SourceRole.EVALUATOR_SUPPLEMENT), EvaluatorSupplementEvidence),
    )
    registry = cast(
        RegistryMarket, _parse(_one(root, T2SourceRole.REGISTRY_MARKET), RegistryMarket)
    )
    admission = derive_evaluation_admission(
        candidate_room_to_cost_k=candidate.config.room_to_cost_k,
        lineage=lineage,
        formal_decision=structural,
        lifecycle_records=lifecycle,
        bbo_events=bbo,
        restart_references=restarts,
        market_expression=expression,
        registry_market=registry,
        validation=validation,
        supplement=supplement,
    )
    if admission.status is not DerivationStatus.EVALUABLE or admission.inputs is None:
        raise ValueError(f"rooted evaluation is not evaluable: {admission.reason_codes}")
    participation = evaluate_participation(candidate.config, admission.inputs)
    if participation.decision is not ParticipationDecision.TAKE:
        raise ValueError("rooted selected candidate does not produce TAKE")

    wire_artifact = _one(root, T2SourceRole.PROVIDER_INSTRUMENT_WIRE)
    wire = json.loads(wire_artifact.exact_bytes())
    from nautilus_trader.model import CryptoPerpetual

    provider_instrument = CryptoPerpetual.from_dict(wire)
    child_wire = provider_instrument.to_dict()
    if canonical_json_bytes(wire) != canonical_json_bytes(child_wire):
        raise ValueError("provider instrument public wire does not round-trip exactly")
    wire_hash = sha256_hex(canonical_json_bytes(wire))
    metadata_artifact = _one(root, T2SourceRole.INSTRUMENT_METADATA)
    metadata = json.loads(metadata_artifact.exact_bytes())
    if metadata.get("provider_wire_hash") != wire_hash:
        raise ValueError("instrument metadata does not bind the rooted provider wire")
    quantity = Decimal(str(provider_instrument.size_increment))
    size_decimals = int(provider_instrument.size_precision)
    side = PositionSide.LONG if structural.side.value == "LONG" else PositionSide.SHORT
    payload = current_bbo.source.payload
    opposite = Decimal(
        str(payload["ask_size"] if side is PositionSide.LONG else payload["bid_size"])
    )
    if quantity <= 0 or quantity > opposite:
        raise ValueError("one public size increment is not executable at the same causal BBO")
    restart = next(
        (item for item in restarts if item.reference_hash == lineage.restart_reference_id), None
    )
    if restart is None:
        restart = next(
            (
                item
                for item in restarts
                if item.restart_reference_id == lineage.restart_reference_id
            ),
            None,
        )
    if restart is None:
        raise ValueError("exact accepted restart reference is absent")
    intent_admission = admit_hypothetical_order_intent(
        strategy_decision_id=structural_artifact.artifact_hash,
        candidate_hash=candidate.candidate_hash,
        side=side,
        lineage=lineage,
        current_bbo=current_bbo,
        technical_quantity=quantity,
        size_decimals=size_decimals,
        activation_reference_hash=restart.reference_hash,
        validation=validation,
    )
    if intent_admission.intent is None:
        raise ValueError(f"canonical OrderIntent is not evaluable: {intent_admission.reason_codes}")
    intent = intent_admission.intent
    projection = project_native_replay(
        events=admissions,
        market_id=lineage.market_id,
        expression_id=expression.expression_id,
        instrument_id=lineage.instrument_id,
    )
    execution = execute_provider_native_state(
        projection=projection,
        intent=intent,
        trigger_admission_hash=current_bbo.admission_hash,
        provider_instrument=provider_instrument,
        catalog_path=catalog_path,
    )
    record = execution.record
    expected_side = "BUY" if side is PositionSide.LONG else "SELL"
    if (
        record.projection_hash != projection.identity.projection_hash
        or record.order_intent_hash != intent.order_intent_hash
        or record.trigger_admission_hash != current_bbo.admission_hash
        or record.submitted_side != expected_side
        or Decimal(record.submitted_technical_quantity) != quantity
    ):
        raise ValueError("provider execution does not cross-bind the canonical causal unit")
    outcome_artifact = _one(root, T2SourceRole.THESIS_OUTCOME)
    outcome = cast(ThesisOutcome, _parse(outcome_artifact, ThesisOutcome))
    if outcome.thesis_id != lineage.thesis_id:
        raise ValueError("rooted outcome belongs to another thesis")
    if outcome.market_id != lineage.market_id:
        raise ValueError("rooted outcome belongs to another market")
    if outcome.decision is not ParticipationDecision.TAKE:
        raise ValueError("rooted outcome decision is not TAKE")
    if outcome.order_intent_hash != intent.order_intent_hash:
        raise ValueError("rooted outcome does not bind the canonical OrderIntent")
    if outcome.provider_state_source_hash != record.evidence_hash:
        raise ValueError("rooted outcome does not bind the fresh provider state")
    rooted_costs = {item.artifact_hash for item in _many(root, T2SourceRole.COST_SOURCE)}
    costs = (
        outcome.fee,
        outcome.spread,
        outcome.slippage,
        outcome.impact_size_feasibility,
        outcome.funding,
        outcome.implementation_shortfall,
    )
    if any(item.provenance is CostProvenance.MISSING for item in costs):
        raise ValueError("rooted outcome has missing cost provenance")
    cost_hashes = tuple(sorted(cast(str, item.source_hash) for item in costs))
    if any(item not in rooted_costs for item in cost_hashes):
        raise ValueError("outcome cost source is absent or rooted under the wrong role")
    return RootedT2Rederivation(
        source_root_hash=root.source_root_hash,
        thesis_id=lineage.thesis_id,
        market_id=lineage.market_id,
        decision="TAKE",
        evaluation_inputs_hash=sha256_hex(
            canonical_json_bytes(admission.inputs.model_dump(mode="json"))
        ),
        participation_result_hash=sha256_hex(
            canonical_json_bytes(participation.model_dump(mode="json"))
        ),
        order_intent_hash=intent.order_intent_hash,
        replay_projection_hash=projection.identity.projection_hash,
        provider_execution_record_hash=record.evidence_hash,
        provider_state_source_hash=record.evidence_hash,
        provider_instrument_wire_hash=wire_hash,
        thesis_outcome_hash=outcome_artifact.artifact_hash,
        cost_source_hashes=tuple(sorted(set(cost_hashes))),
    )


def fresh_process_rederive(
    *, root: T2SourceRootSnapshot, catalog_path: str | Path
) -> RootedT2Rederivation:
    """Rederive through the installed module from an unrelated temporary CWD."""
    resolved_catalog = Path(catalog_path).resolve()
    with tempfile.TemporaryDirectory(prefix="rooted-t2-child-") as directory:
        child_cwd = Path(directory)
        snapshot = child_cwd / "source-root.json"
        output = child_cwd / "result.json"
        snapshot.write_text(root.model_dump_json(), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "trader_assist_v0.nautilus_g4.t2_shadow",
                "--source-root",
                str(snapshot),
                "--rederive",
                "--catalog-path",
                str(resolved_catalog),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            cwd=child_cwd,
            text=True,
            timeout=300,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "fresh installed-module rederivation failed: "
                f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
            )
        return RootedT2Rederivation.model_validate_json(output.read_bytes())


def verify_mechanical_t2(
    *,
    root: T2SourceRootSnapshot,
    candidate: T2ArtifactCandidate,
    catalog_path: str | Path,
) -> MechanicalT2Verification:
    """Freshly rederive and exact-compare the complete non-authoritative candidate."""
    fresh = fresh_process_rederive(root=root, catalog_path=catalog_path)
    expected = T2ArtifactCandidate(root=root, rederivation=fresh)
    if candidate != expected:
        raise ValueError("candidate differs from genuine fresh-process rederivation")
    return MechanicalT2Verification(
        source_root_hash=root.source_root_hash,
        candidate_hash=candidate.candidate_hash,
        fresh_child_candidate_hash=expected.candidate_hash,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--catalog-path", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.source_root is None:
        result: dict[str, object] = {
            "R3_RUNTIME_T2_STATUS": "NONDECISIVE_REAL_INPUT_ABSENT",
            "CURRENT_REAL_SOURCE_ROOT": "ABSENT",
            "CURRENT_REAL_T2_SOURCE_BUNDLE": "ABSENT",
            "FORMAL_REAL_T2_CREDIT": "NO",
            "REAL_T2_CREDIT": "NO",
            "G4_PROMOTION": "NO",
            "DEPLOYMENT_READY": "NO",
            "TRADING_READY": "NO",
        }
    else:
        root = T2SourceRootSnapshot.model_validate_json(args.source_root.read_bytes())
        if args.rederive:
            if args.catalog_path is None or args.output is None:
                parser.error("--rederive requires --catalog-path and --output")
            rederived = rederive_rooted_t2(root=root, catalog_path=args.catalog_path)
            args.output.write_text(rederived.model_dump_json(), encoding="utf-8")
            return 0
        result = {
            "R3_RUNTIME_T2_STATUS": "ROOT_SNAPSHOT_VALID_MECHANICAL_ONLY",
            "SOURCE_ROOT_HASH": root.source_root_hash,
            "FORMAL_REAL_T2_CREDIT": "NO",
            "REAL_T2_CREDIT": "NO",
            "G4_PROMOTION": "NO",
            "DEPLOYMENT_READY": "NO",
            "TRADING_READY": "NO",
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
