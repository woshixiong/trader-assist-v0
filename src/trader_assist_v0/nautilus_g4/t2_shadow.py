# mypy: disable-error-code="import-not-found"
"""Immutable R3 composition over accepted R1/R2 evidence.

This module deliberately owns no execution economics.  It validates and binds
objects owned by E4, VNext, R1 and R2; the only values it derives are hashes and
claim-state projections.
"""

from __future__ import annotations

import dataclasses
import hmac
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import DecisionKind, StrategyDecision
from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
from trader_assist_v0.nautilus_g4.catalog_bridge import EvaluationAdmission, NativeReplayProjection
from trader_assist_v0.nautilus_g4.runner import ProviderExecutionEvidence
from trader_assist_v0.vnext_g4.contracts import (
    NAUTILUS_VERSION,
    CausalLineage,
    G4RunManifest,
    HypotheticalOrderIntent,
    ValidationReference,
)
from trader_assist_v0.vnext_g4.evaluator import EvaluationInputs
from trader_assist_v0.vnext_g4.reporting import CostComponent, CostProvenance, ThesisOutcome

_COST_NAMES = (
    "fee",
    "spread",
    "slippage",
    "impact_size_feasibility",
    "funding",
    "implementation_shortfall",
)
_STRUCTURAL_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/structural/v1\0"
_EVALUATION_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/evaluation/v1\0"
_OUTCOME_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/outcome/v1\0"
_RESTART_SOURCE_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/restart-source/v1\0"
_RESTART_IDENTITY_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/restart-identities/v1\0"
_ARTIFACT_DOMAIN = b"trader-assist-v0/nautilus-g4/t2/artifact/v1\0"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CostClaimState(StrEnum):
    PROVEN = "PROVEN"
    PROVEN_ZERO = "PROVEN_ZERO"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CostEvidence(_Frozen):
    name: Literal[
        "fee",
        "spread",
        "slippage",
        "impact_size_feasibility",
        "funding",
        "implementation_shortfall",
    ]
    claim_state: CostClaimState
    provenance: CostProvenance
    amount_bps: Decimal | None
    source_hash: Sha256Hex
    reason: str | None = None

    @model_validator(mode="after")
    def validate_claim(self) -> Self:
        expected = {
            CostProvenance.OBSERVED: CostClaimState.PROVEN,
            CostProvenance.MODELLED: CostClaimState.PROVEN,
            CostProvenance.PROVEN_ZERO: CostClaimState.PROVEN_ZERO,
            CostProvenance.NOT_APPLICABLE: CostClaimState.NOT_APPLICABLE,
        }.get(self.provenance)
        if expected is None or self.claim_state is not expected:
            raise ValueError("cost claim state conflicts with provenance")
        if self.provenance is CostProvenance.NOT_APPLICABLE:
            if self.amount_bps is not None:
                raise ValueError("not-applicable cost cannot carry a numeric amount")
        else:
            assert self.amount_bps is not None
            if not self.amount_bps.is_finite() or self.amount_bps < 0:
                raise ValueError("cost amount must be finite and non-negative")
            if self.provenance is CostProvenance.PROVEN_ZERO and self.amount_bps != 0:
                raise ValueError("PROVEN_ZERO must carry exact zero")
        return self


class RestartIdentitySet(_Frozen):
    structural_decision_hash: Sha256Hex
    causal_lineage_hash: Sha256Hex
    evaluation_inputs_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    provider_state_projection_hash: Sha256Hex
    outcome_report_hash: Sha256Hex
    identity_set_hash: Sha256Hex

    @classmethod
    def create(cls, **values: object) -> Self:
        digest = sha256_hex(_RESTART_IDENTITY_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "identity_set_hash": digest})

    @model_validator(mode="after")
    def validate_hash(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"identity_set_hash"})
        expected = sha256_hex(_RESTART_IDENTITY_DOMAIN + canonical_json_bytes(payload))
        if not hmac.compare_digest(self.identity_set_hash, expected):
            raise ValueError("restart identity set hash is invalid")
        return self


class ReplayEquivalence(_Frozen):
    source_bundle_hash: Sha256Hex
    original: RestartIdentitySet
    rebuilt: RestartIdentitySet
    child_pid: int = Field(gt=0)
    exact_match: Literal[True] = True

    @model_validator(mode="after")
    def exact_identity_match(self) -> Self:
        if self.child_pid == os.getpid():
            raise ValueError("restart evidence must come from a fresh process")
        if self.original != self.rebuilt:
            raise ValueError("fresh-process restart identities differ")
        return self


# Process-local capabilities deliberately are not part of the serialized claim.  Composition
# accepts only the exact object minted after this process has observed the trusted worker exit.
_MINTED_RESTART_CAPABILITIES: dict[int, tuple[ReplayEquivalence, str, str]] = {}


@dataclass(frozen=True, slots=True)
class T2SourceBundle:
    acquisition_plan_hash: str
    exact_git_head: str
    exact_git_tree: str
    source_e4_manifest_hash: str
    source_pit_snapshot_hash: str
    market_id: str
    expression_id: str
    instrument_id: str
    instrument_metadata_version: str
    instrument_metadata_hash: str
    formal_setup_id: str
    structural_decision: StrategyDecision
    lineage: CausalLineage
    evaluation_inputs: EvaluationInputs
    evaluation_admission: EvaluationAdmission
    validation: ValidationReference
    intent: HypotheticalOrderIntent
    run_manifest: G4RunManifest
    candidate_hash: str
    trigger_admission_hash: str
    admitted_events: tuple[AdmittedEvent, ...]
    projection: NativeReplayProjection
    provider_instrument: object
    provider_execution: ProviderExecutionEvidence
    outcome: ThesisOutcome
    evidence_tier: Literal["REAL_T2"] = "REAL_T2"
    source_kind: Literal["ACCEPTED_REAL_SOURCE"] = "ACCEPTED_REAL_SOURCE"


class RealT2Artifact(_Frozen):
    schema_version: Literal["REAL_T2_ARTIFACT_V1"] = "REAL_T2_ARTIFACT_V1"
    evidence_tier: Literal["REAL_T2"] = "REAL_T2"
    exact_git_head: str
    exact_git_tree: str
    nautilus_version: Literal["2.0.0rc5"] = NAUTILUS_VERSION
    acquisition_plan_hash: Sha256Hex
    source_e4_manifest_hash: Sha256Hex
    source_pit_snapshot_hash: Sha256Hex
    ordered_source_admission_hashes: tuple[Sha256Hex, ...]
    market_id: Sha256Hex
    expression_id: str
    instrument_id: str
    instrument_metadata_version: str
    instrument_metadata_hash: Sha256Hex
    strategy_version: str
    policy_version: str
    parameter_version: str
    derivation_version: str
    validation_reference_hash: Sha256Hex
    structural_decision_hash: Sha256Hex
    causal_lineage_hash: Sha256Hex
    evaluation_inputs_hash: Sha256Hex
    order_intent_hash: Sha256Hex
    projection_hash: Sha256Hex
    native_content_hash: Sha256Hex
    provider_execution_evidence_hash: Sha256Hex
    provider_state_hash: Sha256Hex
    outcome_report_hash: Sha256Hex
    costs: tuple[CostEvidence, ...] = Field(min_length=6, max_length=6)
    restart_equivalence: ReplayEquivalence
    simulation_only: Literal[True] = True
    private_api: Literal[False] = False
    signing: Literal[False] = False
    exchange_write: Literal[False] = False
    live_venue_submitted: Literal[False] = False
    proves_g4e8: Literal[False] = False
    proves_formal_g4: Literal[False] = False
    proves_strategy_edge: Literal[False] = False
    final_t2_artifact_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"final_t2_artifact_hash"})

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        if tuple(item.name for item in self.costs) != _COST_NAMES:
            raise ValueError("artifact must contain the six ordered cost components")
        expected = sha256_hex(_ARTIFACT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.final_t2_artifact_hash, expected):
            raise ValueError("final_t2_artifact_hash is invalid")
        return self


def _hash(domain: bytes, value: object) -> Sha256Hex:
    if isinstance(value, BaseModel):
        payload: object = value.model_dump(mode="json")
    elif dataclasses.is_dataclass(value):
        payload = dataclasses.asdict(cast(Any, value))
    else:
        payload = value
    return sha256_hex(domain + canonical_json_bytes(payload))


def project_cost_evidence(outcome: ThesisOutcome) -> tuple[CostEvidence, ...]:
    result: list[CostEvidence] = []
    states = {
        CostProvenance.OBSERVED: CostClaimState.PROVEN,
        CostProvenance.MODELLED: CostClaimState.PROVEN,
        CostProvenance.PROVEN_ZERO: CostClaimState.PROVEN_ZERO,
        CostProvenance.NOT_APPLICABLE: CostClaimState.NOT_APPLICABLE,
    }
    for name in _COST_NAMES:
        component: CostComponent = getattr(outcome, name)
        if component.provenance is CostProvenance.MISSING:
            raise ValueError(f"{name} cost provenance is MISSING")
        if component.source_hash is None:
            raise ValueError(f"{name} cost lacks source_hash")
        state = states.get(component.provenance)
        if state is None:
            raise ValueError(f"{name} cost has unknown provenance")
        result.append(
            CostEvidence(
                name=cast(
                    Literal[
                        "fee",
                        "spread",
                        "slippage",
                        "impact_size_feasibility",
                        "funding",
                        "implementation_shortfall",
                    ],
                    name,
                ),
                claim_state=state,
                provenance=component.provenance,
                amount_bps=component.amount_bps,
                source_hash=component.source_hash,
                reason=component.reason,
            )
        )
    return tuple(result)


def source_bundle_hash(bundle: T2SourceBundle) -> Sha256Hex:
    payload = {
        "acquisition_plan_hash": bundle.acquisition_plan_hash,
        "exact_git_head": bundle.exact_git_head,
        "exact_git_tree": bundle.exact_git_tree,
        "events": [item.model_dump(mode="json") for item in bundle.admitted_events],
        "decision": dataclasses.asdict(bundle.structural_decision),
        "lineage": bundle.lineage.model_dump(mode="json"),
        "evaluation": bundle.evaluation_inputs.model_dump(mode="json"),
        "evaluation_admission": bundle.evaluation_admission.model_dump(mode="json"),
        "validation": bundle.validation.model_dump(mode="json"),
        "intent": bundle.intent.model_dump(mode="json"),
        "outcome": bundle.outcome.model_dump(mode="json"),
    }
    return sha256_hex(_RESTART_SOURCE_DOMAIN + canonical_json_bytes(payload))


def identity_set(
    bundle: T2SourceBundle, *, provider_state_hash: str | None = None
) -> RestartIdentitySet:
    return RestartIdentitySet.create(
        structural_decision_hash=_hash(_STRUCTURAL_DOMAIN, bundle.structural_decision),
        causal_lineage_hash=bundle.lineage.lineage_hash,
        evaluation_inputs_hash=_hash(_EVALUATION_DOMAIN, bundle.evaluation_inputs),
        order_intent_hash=bundle.intent.order_intent_hash,
        provider_state_projection_hash=provider_state_hash
        or bundle.provider_execution.record.provider_state.state_hash,
        outcome_report_hash=_hash(_OUTCOME_DOMAIN, bundle.outcome),
    )


def _validate_bundle(bundle: T2SourceBundle) -> None:
    if bundle.source_kind != "ACCEPTED_REAL_SOURCE" or bundle.evidence_tier != "REAL_T2":
        raise ValueError("synthetic/manual/T0/T1 source substitution is forbidden")
    if bundle.structural_decision.decision is not DecisionKind.FORMAL_SETUP_CONFIRMED:
        raise ValueError("structural decision is not FORMAL_SETUP_CONFIRMED")
    if (
        bundle.structural_decision.market_id != bundle.market_id
        or bundle.structural_decision.market_event_id != bundle.lineage.formal_setup_id
    ):
        raise ValueError("structural decision source identity mismatch")
    if (
        bundle.evaluation_admission.status.value != "EVALUABLE"
        or bundle.evaluation_admission.inputs != bundle.evaluation_inputs
    ):
        raise ValueError("EvaluationInputs do not match accepted derivation evidence")
    if not bundle.validation.fully_materialized:
        raise ValueError("ValidationReference is not fully materialized")
    lineage, intent, manifest, projection, record, outcome = (
        bundle.lineage,
        bundle.intent,
        bundle.run_manifest,
        bundle.projection.identity,
        bundle.provider_execution.record,
        bundle.outcome,
    )
    admissions = tuple(event.admission_hash for event in bundle.admitted_events)
    if not admissions or len(admissions) != len(set(admissions)):
        raise ValueError("source admissions are absent or duplicated")
    if tuple(event.admission_ordinal for event in bundle.admitted_events) != tuple(
        sorted(event.admission_ordinal for event in bundle.admitted_events)
    ):
        raise ValueError("source admissions are out of order")
    epochs = {
        (e.process_epoch, e.continuity_epoch, e.admission_epoch) for e in bundle.admitted_events
    }
    if len(epochs) != 1:
        raise ValueError("source admissions cross epochs")
    expected = (bundle.market_id, bundle.expression_id, bundle.instrument_id)
    if any(
        (e.source.market_id, e.source.expression_id, e.source.instrument_id) != expected
        for e in bundle.admitted_events
    ):
        raise ValueError("source admission identity mismatch")
    if (
        projection.market_id,
        projection.expression_id,
        projection.instrument_id,
    ) != expected or projection.ordered_source_admission_hashes != admissions:
        raise ValueError("R1 projection source binding mismatch")
    if (
        lineage.market_id,
        lineage.instrument_id,
        lineage.source_e4_manifest_hash,
        lineage.source_pit_snapshot_hash,
    ) != (
        bundle.market_id,
        bundle.instrument_id,
        bundle.source_e4_manifest_hash,
        bundle.source_pit_snapshot_hash,
    ):
        raise ValueError("causal lineage mismatch")
    if (
        lineage.formal_setup_id,
        lineage.instrument_metadata_version,
        lineage.instrument_metadata_hash,
    ) != (
        bundle.formal_setup_id,
        bundle.instrument_metadata_version,
        bundle.instrument_metadata_hash,
    ):
        raise ValueError("formal setup or instrument metadata mismatch")
    if (
        manifest.git_sha,
        manifest.git_tree,
        manifest.source_e4_manifest_hash,
        manifest.source_pit_snapshot_hash,
    ) != (
        bundle.exact_git_head,
        bundle.exact_git_tree,
        bundle.source_e4_manifest_hash,
        bundle.source_pit_snapshot_hash,
    ):
        raise ValueError("G4 manifest source identity mismatch")
    if manifest.structural_component_manifest_hash != lineage.structural_component_manifest_hash:
        raise ValueError("G4 manifest structural component mismatch")
    if (
        lineage.validation_reference_id != bundle.validation.validation_reference_id
        or lineage.validation_reference_hash != bundle.validation.reference_hash
    ):
        raise ValueError("causal lineage ValidationReference mismatch")
    if (
        bundle.candidate_hash not in manifest.candidate_hashes
        or intent.candidate_hash != bundle.candidate_hash
    ):
        raise ValueError("candidate identity mismatch")
    if (
        intent.causal_lineage_hash != lineage.lineage_hash
        or intent.validation_reference_hash != bundle.validation.reference_hash
        or intent.validation_reference_id != bundle.validation.validation_reference_id
    ):
        raise ValueError("OrderIntent lineage/Validation mismatch")
    if (
        intent.technical_quantity.instrument_metadata_hash != bundle.instrument_metadata_hash
        or intent.technical_quantity.instrument_metadata_version
        != bundle.instrument_metadata_version
    ):
        raise ValueError("OrderIntent instrument metadata mismatch")
    if not intent.not_submitted or intent.venue_submitted:
        raise ValueError("OrderIntent was submitted")
    if not isinstance(bundle.provider_execution, ProviderExecutionEvidence):
        raise TypeError("accepted ProviderExecutionEvidence capability is required")
    if (
        record.projection_hash,
        record.ordered_source_admission_hashes,
        record.order_intent_hash,
        record.trigger_admission_hash,
    ) != (
        projection.projection_hash,
        admissions,
        intent.order_intent_hash,
        bundle.trigger_admission_hash,
    ):
        raise ValueError("provider execution cross-binding mismatch")
    if record.provider_instrument_id != bundle.instrument_id or record.provider_instrument_type != (
        f"{type(bundle.provider_instrument).__module__}."
        f"{type(bundle.provider_instrument).__qualname__}"
    ):
        raise ValueError("provider instrument mismatch")
    if (
        outcome.market_id,
        outcome.thesis_id,
        outcome.order_intent_hash,
        outcome.provider_state_source_hash,
    ) != (
        lineage.market_id,
        lineage.thesis_id,
        intent.order_intent_hash,
        record.provider_state.state_hash,
    ):
        raise ValueError("ThesisOutcome source binding mismatch")
    if outcome.decision.value != "TAKE" or outcome.attempt_count < 1:
        raise ValueError("ThesisOutcome is not an executed technical TAKE")
    project_cost_evidence(outcome)


def compose_real_t2_artifact(bundle: T2SourceBundle, restart: ReplayEquivalence) -> RealT2Artifact:
    _validate_bundle(bundle)
    original = identity_set(bundle)
    if restart.source_bundle_hash != source_bundle_hash(bundle) or restart.original != original:
        raise ValueError("restart evidence does not bind this source bundle")
    _require_minted_restart(restart)
    lineage, projection, record = (
        bundle.lineage,
        bundle.projection.identity,
        bundle.provider_execution.record,
    )
    values: dict[str, object] = {
        "exact_git_head": bundle.exact_git_head,
        "exact_git_tree": bundle.exact_git_tree,
        "acquisition_plan_hash": bundle.acquisition_plan_hash,
        "source_e4_manifest_hash": bundle.source_e4_manifest_hash,
        "source_pit_snapshot_hash": bundle.source_pit_snapshot_hash,
        "ordered_source_admission_hashes": projection.ordered_source_admission_hashes,
        "market_id": bundle.market_id,
        "expression_id": bundle.expression_id,
        "instrument_id": bundle.instrument_id,
        "instrument_metadata_version": bundle.instrument_metadata_version,
        "instrument_metadata_hash": bundle.instrument_metadata_hash,
        "strategy_version": lineage.strategy_version,
        "policy_version": lineage.policy_version,
        "parameter_version": lineage.parameter_version,
        "derivation_version": lineage.derivation_version,
        "validation_reference_hash": bundle.validation.reference_hash,
        "structural_decision_hash": original.structural_decision_hash,
        "causal_lineage_hash": lineage.lineage_hash,
        "evaluation_inputs_hash": original.evaluation_inputs_hash,
        "order_intent_hash": bundle.intent.order_intent_hash,
        "projection_hash": projection.projection_hash,
        "native_content_hash": projection.native_content_hash,
        "provider_execution_evidence_hash": record.evidence_hash,
        "provider_state_hash": record.provider_state.state_hash,
        "outcome_report_hash": original.outcome_report_hash,
        "costs": project_cost_evidence(bundle.outcome),
        "restart_equivalence": restart,
    }
    digest = sha256_hex(
        _ARTIFACT_DOMAIN
        + canonical_json_bytes(
            RealT2Artifact.model_construct(**values).model_dump(  # type: ignore[arg-type]
                mode="json", exclude={"final_t2_artifact_hash"}
            )
        )
    )
    return RealT2Artifact.model_validate({**values, "final_t2_artifact_hash": digest})


def _require_minted_restart(restart: ReplayEquivalence) -> None:
    capability = _MINTED_RESTART_CAPABILITIES.get(id(restart))
    if (
        capability is None
        or capability[0] is not restart
        or capability[1:] != (restart.source_bundle_hash, restart.rebuilt.identity_set_hash)
    ):
        raise ValueError("restart evidence was not minted by the fresh-process worker path")


def fresh_process_equivalence(bundle: T2SourceBundle, worker: str | Path) -> ReplayEquivalence:
    """Serialize only immutable sources and require an independent child rebuild."""
    trusted_worker = (
        Path(__file__).resolve().parents[3] / "scripts" / "nautilus_vnext_g4_t2_shadow.py"
    )
    if Path(worker).resolve() != trusted_worker:
        raise ValueError("restart equivalence requires the repository-owned R3 worker")
    instrument_type = type(bundle.provider_instrument)
    to_dict = getattr(instrument_type, "to_dict", None)
    if not callable(to_dict):
        to_dict = getattr(bundle.provider_instrument, "to_dict", None)
    if not callable(to_dict):
        raise RuntimeError("provider instrument lacks exact public to_dict surface")
    instrument_wire = (
        to_dict(bundle.provider_instrument)
        if getattr(to_dict, "__self__", None) is instrument_type
        else to_dict()
    )
    source = {
        "events": [event.model_dump(mode="json") for event in bundle.admitted_events],
        "market_id": bundle.market_id,
        "expression_id": bundle.expression_id,
        "instrument_id": bundle.instrument_id,
        "structural_decision": dataclasses.asdict(bundle.structural_decision),
        "lineage": bundle.lineage.model_dump(mode="json"),
        "evaluation_inputs": bundle.evaluation_inputs.model_dump(mode="json"),
        "evaluation_admission": bundle.evaluation_admission.model_dump(mode="json"),
        "validation": bundle.validation.model_dump(mode="json"),
        "intent": bundle.intent.model_dump(mode="json"),
        "outcome": bundle.outcome.model_dump(mode="json"),
        "trigger_admission_hash": bundle.trigger_admission_hash,
        "provider_instrument": instrument_wire,
    }
    original = identity_set(bundle)
    payload = {"source_bundle_hash": source_bundle_hash(bundle), "source": source}
    completed = subprocess.run(
        [sys.executable, str(worker), "--rebuild-identities"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    response = json.loads(completed.stdout)
    rebuilt = RestartIdentitySet.model_validate(response["identity_set"])
    result = ReplayEquivalence(
        source_bundle_hash=cast(str, payload["source_bundle_hash"]),
        original=original,
        rebuilt=rebuilt,
        child_pid=response["pid"],
        exact_match=True,
    )
    _MINTED_RESTART_CAPABILITIES[id(result)] = (
        result,
        result.source_bundle_hash,
        result.rebuilt.identity_set_hash,
    )
    return result
