# mypy: disable-error-code="import-not-found"
"""Rooted, non-authorizing Real-T2 candidate evidence.

This module deliberately separates deterministic evidence construction from the
GitHub/control-plane act which may accept that evidence.  All constructors in
this module produce *candidates*; none of them grant Real-T2 credit.
"""

from __future__ import annotations

import base64
import hmac
import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex

SOURCE_ROOT_SCHEMA_VERSION: Literal["ROOTED_T2_SOURCE_V1"] = "ROOTED_T2_SOURCE_V1"
ARTIFACT_CANDIDATE_SCHEMA_VERSION: Literal["ROOTED_T2_CANDIDATE_V1"] = "ROOTED_T2_CANDIDATE_V1"
ACCEPTANCE_RECEIPT_SCHEMA_VERSION: Literal["ROOTED_T2_ACCEPTANCE_V1"] = "ROOTED_T2_ACCEPTANCE_V1"
_ARTIFACT_DOMAIN = b"trader-assist-v0/rooted-t2/source-artifact/v1\0"
_ROOT_DOMAIN = b"trader-assist-v0/rooted-t2/source-root/v1\0"
_CANDIDATE_DOMAIN = b"trader-assist-v0/rooted-t2/artifact-candidate/v1\0"
_RECEIPT_DOMAIN = b"trader-assist-v0/rooted-t2/acceptance-receipt/v1\0"


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
    """Exact bytes assigned to one semantic role and stable name."""

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
    """Complete role-typed source closure; serializable evidence, never authority."""

    schema_version: Literal["ROOTED_T2_SOURCE_V1"] = SOURCE_ROOT_SCHEMA_VERSION
    task_id: str = Field(min_length=1)
    governance_epoch: Sha256Hex
    acquisition_plan_hash: Sha256Hex
    exact_source_git_head: Sha256Hex
    exact_source_git_tree: Sha256Hex
    e4_run_manifest_hash: Sha256Hex
    e4_pit_snapshot_hash: Sha256Hex
    g4_run_manifest_hash: Sha256Hex
    selected_candidate_hash: Sha256Hex
    strategy_package_identity: str = Field(min_length=1)
    validation_reference_hash: Sha256Hex
    artifacts: tuple[RoleBoundSourceArtifact, ...] = Field(min_length=1)
    accepted_t2_source_root_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"accepted_t2_source_root_hash"})

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
            (T2SourceRole.E4_RUN_MANIFEST, self.e4_run_manifest_hash),
            (T2SourceRole.E4_PIT_SNAPSHOT, self.e4_pit_snapshot_hash),
            (T2SourceRole.G4_RUN_MANIFEST, self.g4_run_manifest_hash),
            (T2SourceRole.SELECTED_CANDIDATE, self.selected_candidate_hash),
            (T2SourceRole.VALIDATION_REFERENCE, self.validation_reference_hash),
        }
        for role, digest in required:
            if not any(
                item.role is role and hmac.compare_digest(item.artifact_hash, digest)
                for item in self.artifacts
            ):
                raise ValueError(
                    f"declared {role.value} hash is not rooted under its required role"
                )
        expected = sha256_hex(_ROOT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.accepted_t2_source_root_hash, expected):
            raise ValueError("accepted_t2_source_root_hash does not bind the complete source graph")
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
        payload = {
            "schema_version": SOURCE_ROOT_SCHEMA_VERSION,
            **values,
            "artifacts": artifacts,
        }
        return cls.model_validate(
            {
                **payload,
                "accepted_t2_source_root_hash": sha256_hex(
                    _ROOT_DOMAIN + canonical_json_bytes(payload)
                ),
            }
        )


class T2ArtifactCandidate(_FrozenModel):
    """Deterministic mechanical result.  This object always has zero formal credit."""

    schema_version: Literal["ROOTED_T2_CANDIDATE_V1"] = ARTIFACT_CANDIDATE_SCHEMA_VERSION
    task_id: str
    governance_epoch: Sha256Hex
    source_root_hash: Sha256Hex
    evaluation_inputs_hash: Sha256Hex
    participation_result_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    replay_projection_hash: Sha256Hex
    provider_execution_record_hash: Sha256Hex
    provider_instrument_wire_hash: Sha256Hex
    thesis_outcome_hash: Sha256Hex
    transitive_cost_source_hashes: tuple[Sha256Hex, ...]
    fresh_process_source_root_hash: Sha256Hex
    formal_real_t2_credit: Literal[False] = False
    real_t2_credit: Literal[False] = False
    g4_promotion: Literal[False] = False
    deployment_ready: Literal[False] = False
    trading_ready: Literal[False] = False
    candidate_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"candidate_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        if not hmac.compare_digest(self.source_root_hash, self.fresh_process_source_root_hash):
            raise ValueError("fresh process did not rederive the exact received source root")
        if self.transitive_cost_source_hashes != tuple(
            sorted(set(self.transitive_cost_source_hashes))
        ):
            raise ValueError("cost source hashes must be unique and sorted")
        expected = sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.candidate_hash, expected):
            raise ValueError("candidate_hash does not bind the complete mechanical result")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        supplied_costs = cast(tuple[Sha256Hex, ...], values["transitive_cost_source_hashes"])
        payload = {
            "schema_version": ARTIFACT_CANDIDATE_SCHEMA_VERSION,
            **values,
            "transitive_cost_source_hashes": tuple(sorted(set(supplied_costs))),
            "formal_real_t2_credit": False,
            "real_t2_credit": False,
            "g4_promotion": False,
            "deployment_ready": False,
            "trading_ready": False,
        }
        return cls.model_validate(
            {
                **payload,
                "candidate_hash": sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(payload)),
            }
        )


class AcceptedRealT2Receipt(_FrozenModel):
    """Representation of an external receipt; model validity is not acceptance."""

    schema_version: Literal["ROOTED_T2_ACCEPTANCE_V1"] = ACCEPTANCE_RECEIPT_SCHEMA_VERSION
    accepted_t2_source_root_hash: Sha256Hex
    t2_artifact_candidate_hash: Sha256Hex
    task_id: str
    governance_epoch: Sha256Hex
    exact_implementation_head: Sha256Hex
    exact_implementation_tree: Sha256Hex
    independent_review_locator: str = Field(min_length=1)
    receipt_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"receipt_hash"})

    @model_validator(mode="after")
    def verify_integrity_only(self) -> Self:
        expected = sha256_hex(_RECEIPT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.receipt_hash, expected):
            raise ValueError("receipt_hash does not bind the receipt fields")
        return self


class CanonicalAcceptanceExpectation(_FrozenModel):
    """Precommitted control-plane facts supplied by the external verifier."""

    task_id: str
    governance_epoch: Sha256Hex
    source_root_hash: Sha256Hex
    candidate_hash: Sha256Hex
    implementation_head: Sha256Hex
    implementation_tree: Sha256Hex
    independent_review_locator: str
    canonical_receipt_hash: Sha256Hex


class RealT2AcceptanceDecision(_FrozenModel):
    accepted: bool
    real_t2_credit: bool
    reason: str


class RootedT2Rederivation(_FrozenModel):
    """Typed identities produced only by existing semantic owners."""

    source_root_hash: Sha256Hex
    evaluation_inputs_hash: Sha256Hex
    participation_result_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    replay_projection_hash: Sha256Hex
    provider_execution_record_hash: Sha256Hex
    provider_instrument_wire_hash: Sha256Hex
    thesis_outcome_hash: Sha256Hex
    cost_source_hashes: tuple[Sha256Hex, ...]


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


def _parse(artifact: RoleBoundSourceArtifact, target: type[object]) -> object:
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
        cast(AdmittedEvent, _parse(item, AdmittedEvent))
        for item in _many(root, T2SourceRole.E4_ADMISSION)
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
    current_bbo = max(bbo, key=lambda item: (item.admission_ordinal, item.admission_ts))
    lifecycle = tuple(
        cast(LifecycleRecord, _parse(item, LifecycleRecord))
        for item in _many(root, T2SourceRole.E4_LIFECYCLE)
    )
    restarts = tuple(
        cast(RestartReferenceEvidence, _parse(item, RestartReferenceEvidence))
        for item in _many(root, T2SourceRole.RESTART_REFERENCE)
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
        bbo_events=tuple(sorted(bbo, key=lambda item: item.admission_ordinal)),
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
        source_root_hash=root.accepted_t2_source_root_hash,
        evaluation_inputs_hash=sha256_hex(
            canonical_json_bytes(admission.inputs.model_dump(mode="json"))
        ),
        participation_result_hash=sha256_hex(
            canonical_json_bytes(participation.model_dump(mode="json"))
        ),
        order_intent_hash=intent.order_intent_hash,
        replay_projection_hash=projection.identity.projection_hash,
        provider_execution_record_hash=record.evidence_hash,
        provider_instrument_wire_hash=wire_hash,
        thesis_outcome_hash=outcome_artifact.artifact_hash,
        cost_source_hashes=tuple(sorted(set(cost_hashes))),
    )


def fresh_process_rederive(
    *, root: T2SourceRootSnapshot, catalog_path: str | Path
) -> RootedT2Rederivation:
    """Give a child only the source snapshot; never transmit derived authority."""
    with tempfile.TemporaryDirectory(prefix="rooted-t2-child-") as directory:
        snapshot = Path(directory) / "source-root.json"
        output = Path(directory) / "result.json"
        snapshot.write_text(root.model_dump_json(), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "scripts/nautilus_vnext_g4_t2_shadow.py",
                "--source-root",
                str(snapshot),
                "--rederive",
                "--catalog-path",
                str(catalog_path),
                "--output",
                str(output),
            ],
            check=True,
        )
        return RootedT2Rederivation.model_validate_json(output.read_bytes())


def verify_external_acceptance(
    *,
    root: T2SourceRootSnapshot,
    candidate: T2ArtifactCandidate,
    receipt: AcceptedRealT2Receipt | None,
    canonical: CanonicalAcceptanceExpectation | None,
) -> RealT2AcceptanceDecision:
    """Fail closed unless every candidate/receipt/precommit edge matches exactly."""
    if receipt is None or canonical is None:
        return RealT2AcceptanceDecision(
            accepted=False,
            real_t2_credit=False,
            reason="NO_CANONICAL_PRECOMMITTED_ACCEPTED_ROOT_OR_RECEIPT",
        )
    pairs = (
        (root.task_id, candidate.task_id, receipt.task_id, canonical.task_id),
        (
            root.governance_epoch,
            candidate.governance_epoch,
            receipt.governance_epoch,
            canonical.governance_epoch,
        ),
        (
            root.accepted_t2_source_root_hash,
            candidate.source_root_hash,
            receipt.accepted_t2_source_root_hash,
            canonical.source_root_hash,
        ),
        (candidate.candidate_hash, receipt.t2_artifact_candidate_hash, canonical.candidate_hash),
        (receipt.exact_implementation_head, canonical.implementation_head),
        (receipt.exact_implementation_tree, canonical.implementation_tree),
        (receipt.independent_review_locator, canonical.independent_review_locator),
        (receipt.receipt_hash, canonical.canonical_receipt_hash),
    )
    if any(len(set(values)) != 1 for values in pairs):
        return RealT2AcceptanceDecision(
            accepted=False, real_t2_credit=False, reason="CANONICAL_ACCEPTANCE_BINDING_MISMATCH"
        )
    return RealT2AcceptanceDecision(
        accepted=True, real_t2_credit=True, reason="CANONICAL_EXTERNAL_ACCEPTANCE_MATCHED"
    )
