"""Immutable Ordinary VNext G4 identities and execution assumptions."""

from __future__ import annotations

import hmac
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import (
    GitCommitOid,
    OpaqueId,
    Sha256Hex,
    VersionId,
    canonical_json_bytes,
    sha256_hex,
)

VNEXT_STRATEGY_VERSION: Literal["TA_VNEXT_E4_C1_2026-09-11"] = "TA_VNEXT_E4_C1_2026-09-11"
VNEXT_POLICY_VERSION: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = (
    "TA_FRICTION_POSITION_POLICY_V0_1"
)
VNEXT_PARAMETER_VERSION: Literal["TA_PRE_E4_GRID_V0_1"] = "TA_PRE_E4_GRID_V0_1"
VNEXT_DERIVATION_VERSION: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = (
    "TA_MICROSTRUCTURE_DERIV_V0_1"
)
VNEXT_DATA_VERSION: Literal["TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"] = (
    "TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"
)
NAUTILUS_VERSION: Literal["2.0.0rc5"] = "2.0.0rc5"
G4_SCHEMA_VERSION: Literal["VNEXT_G4_V1"] = "VNEXT_G4_V1"
G4_EXECUTION_MODEL_VERSION: Literal["VNEXT_G4_EXPLICIT_NAUTILUS_RC5_V1"] = (
    "VNEXT_G4_EXPLICIT_NAUTILUS_RC5_V1"
)
REPRESENTATIVE_MARKET_FLOOR = 20

_CANDIDATE_DOMAIN = b"trader-assist-v0/vnext-g4/candidate/v1\0"
_MANIFEST_DOMAIN = b"trader-assist-v0/vnext-g4/run-manifest/v1\0"
_DERIVED_DOMAIN = b"trader-assist-v0/vnext-g4/derived-cache/v1\0"

_ROOM_TO_COST_GRID = frozenset({Decimal("2"), Decimal("3"), Decimal("4")})
_FIXED_STOP_GRID = frozenset(
    Decimal(value) for value in ("4", "6", "8", "10", "12", "15", "20")
)
_RV_MULTIPLIER_GRID = frozenset(Decimal(value) for value in ("0.5", "1.0", "1.5"))
_TIME_STOP_GRID = frozenset({30, 60, 90, 120, 180, 300})
_WINNER_PROGRESS_GRID = frozenset(
    Decimal(value) for value in ("3", "5", "8", "10", "15", "20")
)
_PERSISTENCE_GRID = frozenset({30, 60})
_GIVEBACK_GRID = frozenset(
    {Decimal(1) / Decimal(3), Decimal(1) / Decimal(2), Decimal(2) / Decimal(3)}
)


class EntryActivation(StrEnum):
    EA0 = "EA0"
    EA1 = "EA1"
    EA2 = "EA2"
    EA3 = "EA3"


class Ea3Base(StrEnum):
    EA1 = "EA1"
    EA2 = "EA2"


class AttemptStop(StrEnum):
    AP0 = "AP0"
    AP1 = "AP1"
    AP2 = "AP2"
    AP3 = "AP3"
    AP4 = "AP4"


class ReentryPolicy(StrEnum):
    NO_REENTRY_REFERENCE = "NO_REENTRY_REFERENCE"
    ONE_FRESH_CAUSAL_ACTIVATION_REENTRY = "ONE_FRESH_CAUSAL_ACTIVATION_REENTRY"
    BLIND_IMMEDIATE_REENTRY_NEGATIVE_CONTROL = "BLIND_IMMEDIATE_REENTRY_NEGATIVE_CONTROL"


class WinnerConfirmation(StrEnum):
    WC0 = "WC0"
    WC1 = "WC1"
    WC2 = "WC2"
    WC3 = "WC3"


class WinnerAdd(StrEnum):
    A0_NO_ADD = "A0_NO_ADD"


class ExitPolicy(StrEnum):
    X0 = "X0"
    X1 = "X1"
    X2 = "X2"
    X3 = "X3"


class ParticipationDecision(StrEnum):
    BLOCKED = "BLOCKED"
    TAKE = "TAKE"
    WAIT = "WAIT"
    PASS = "PASS"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class OrderPrimitive(StrEnum):
    MARKETABLE = "MARKETABLE"
    PASSIVE = "PASSIVE"


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceArtifactHash(StrictFrozenModel):
    name: str = Field(min_length=1, max_length=160)
    sha256: Sha256Hex


class ExecutionModelConfig(StrictFrozenModel):
    version: Literal["VNEXT_G4_EXPLICIT_NAUTILUS_RC5_V1"] = G4_EXECUTION_MODEL_VERSION
    book_type: Literal["L1_MBP", "L2_MBP"]
    order_primitive: OrderPrimitive
    prob_fill_on_limit: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    prob_slippage: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    trade_execution: bool
    queue_position: bool
    liquidity_consumption: bool
    fill_limit_at_price: bool
    fill_stop_at_price: bool
    random_seed: int | None
    l1_size_feasibility_required: Literal[True] = True
    passive_touch_equals_fill: Literal[False] = False
    trigger_price_equals_fill: Literal[False] = False
    execution_model_limited: bool

    @model_validator(mode="after")
    def validate_explicit_realism(self) -> Self:
        stochastic = self.prob_fill_on_limit not in {Decimal("0"), Decimal("1")} or (
            self.prob_slippage not in {Decimal("0"), Decimal("1")}
        )
        if stochastic and self.random_seed is None:
            raise ValueError("stochastic execution model requires an explicit reproducible seed")
        if self.queue_position and (not self.trade_execution or self.book_type != "L2_MBP"):
            raise ValueError("queue_position requires trade_execution and L2_MBP")
        if (
            self.order_primitive is OrderPrimitive.PASSIVE
            and not self.queue_position
            and not self.execution_model_limited
        ):
            raise ValueError("passive execution without queue evidence must remain limited")
        return self


class CandidateConfig(StrictFrozenModel):
    entry_activation: EntryActivation
    ea3_base: Ea3Base | None = None
    attempt_stop: AttemptStop
    room_to_cost_k: Decimal
    fixed_stop_bps: Decimal | None = None
    rv_multiplier: Decimal | None = None
    time_stop_seconds: int | None = None
    reentry_policy: ReentryPolicy
    winner_confirmation: WinnerConfirmation
    winner_progress_bps: Decimal
    persistence_seconds: int | None = None
    winner_add: Literal[WinnerAdd.A0_NO_ADD] = WinnerAdd.A0_NO_ADD
    exit_policy: ExitPolicy
    giveback_ratio: Decimal | None = None
    comparison_role: Literal["REFERENCE", "CHALLENGER", "NEGATIVE_CONTROL"]

    @model_validator(mode="after")
    def validate_frozen_grid(self) -> Self:
        if self.room_to_cost_k not in _ROOM_TO_COST_GRID:
            raise ValueError("room_to_cost_k is outside the frozen C1 grid")
        if self.winner_progress_bps not in _WINNER_PROGRESS_GRID:
            raise ValueError("winner_progress_bps is outside the frozen C1 grid")
        if self.entry_activation is EntryActivation.EA3 and self.ea3_base is None:
            raise ValueError("EA3 must declare whether it overlays EA1 or EA2")
        if self.entry_activation is not EntryActivation.EA3 and self.ea3_base is not None:
            raise ValueError("ea3_base is only valid for EA3")

        if self.attempt_stop in {AttemptStop.AP1, AttemptStop.AP4}:
            if self.fixed_stop_bps not in _FIXED_STOP_GRID:
                raise ValueError("AP1/AP4 fixed_stop_bps is outside the frozen C1 grid")
        elif self.fixed_stop_bps is not None:
            raise ValueError("fixed_stop_bps is only valid for AP1/AP4")

        if self.attempt_stop is AttemptStop.AP2:
            if self.rv_multiplier not in _RV_MULTIPLIER_GRID:
                raise ValueError("AP2 rv_multiplier is outside the frozen C1 grid")
        elif self.rv_multiplier is not None:
            raise ValueError("rv_multiplier is only valid for AP2")

        if self.attempt_stop in {AttemptStop.AP3, AttemptStop.AP4}:
            if self.time_stop_seconds not in _TIME_STOP_GRID:
                raise ValueError("AP3/AP4 time_stop_seconds is outside the frozen C1 grid")
        elif self.time_stop_seconds is not None:
            raise ValueError("time_stop_seconds is only valid for AP3/AP4")

        if self.winner_confirmation is WinnerConfirmation.WC1:
            if self.persistence_seconds not in _PERSISTENCE_GRID:
                raise ValueError("WC1 persistence_seconds is outside the frozen C1 grid")
        elif self.persistence_seconds is not None:
            raise ValueError("persistence_seconds is only valid for WC1")

        if self.exit_policy in {ExitPolicy.X2, ExitPolicy.X3}:
            if self.giveback_ratio not in _GIVEBACK_GRID:
                raise ValueError("X2/X3 giveback_ratio is outside the frozen C1 grid")
        elif self.giveback_ratio is not None:
            raise ValueError("giveback_ratio is only valid for X2/X3")

        if (
            self.reentry_policy is ReentryPolicy.BLIND_IMMEDIATE_REENTRY_NEGATIVE_CONTROL
            and self.comparison_role != "NEGATIVE_CONTROL"
        ):
            raise ValueError("blind immediate re-entry is negative-control only")
        return self


class CandidateManifest(StrictFrozenModel):
    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    strategy_version: Literal["TA_VNEXT_E4_C1_2026-09-11"] = VNEXT_STRATEGY_VERSION
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = VNEXT_POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = VNEXT_PARAMETER_VERSION
    derivation_version: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = VNEXT_DERIVATION_VERSION
    data_version: Literal["TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"] = (
        VNEXT_DATA_VERSION
    )
    structural_component_manifest_hash: Sha256Hex
    candidate_id: OpaqueId
    config: CandidateConfig
    candidate_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"candidate_hash"})

    @model_validator(mode="after")
    def verify_hash(self) -> Self:
        expected = sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.candidate_hash, expected):
            raise ValueError("candidate_hash does not bind the exact frozen candidate")
        return self

    @classmethod
    def create(
        cls,
        *,
        candidate_id: str,
        structural_component_manifest_hash: str,
        config: CandidateConfig,
    ) -> Self:
        payload: dict[str, object] = {
            "schema_version": G4_SCHEMA_VERSION,
            "strategy_version": VNEXT_STRATEGY_VERSION,
            "policy_version": VNEXT_POLICY_VERSION,
            "parameter_version": VNEXT_PARAMETER_VERSION,
            "derivation_version": VNEXT_DERIVATION_VERSION,
            "data_version": VNEXT_DATA_VERSION,
            "structural_component_manifest_hash": structural_component_manifest_hash,
            "candidate_id": candidate_id,
            "config": config.model_dump(mode="json"),
        }
        digest = sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "candidate_hash": digest})


class G4RunManifest(StrictFrozenModel):
    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    run_id: OpaqueId
    git_sha: GitCommitOid
    git_tree: GitCommitOid
    source_e4_manifest_hash: Sha256Hex
    source_pit_snapshot_hash: Sha256Hex
    source_evidence_artifact_hashes: tuple[EvidenceArtifactHash, ...]
    structural_component_manifest_hash: Sha256Hex
    strategy_version: Literal["TA_VNEXT_E4_C1_2026-09-11"] = VNEXT_STRATEGY_VERSION
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = VNEXT_POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = VNEXT_PARAMETER_VERSION
    derivation_version: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = VNEXT_DERIVATION_VERSION
    data_version: Literal["TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"] = (
        VNEXT_DATA_VERSION
    )
    nautilus_version: Literal["2.0.0rc5"] = NAUTILUS_VERSION
    execution_model: ExecutionModelConfig
    candidate_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    trial_adaptivity_id: VersionId
    cutoff_id: VersionId
    confirmatory_e5: Literal[False] = False
    private_api: Literal[False] = False
    signing: Literal[False] = False
    exchange_write: Literal[False] = False
    venue_submitted: Literal[False] = False
    manifest_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"manifest_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        names = tuple(item.name for item in self.source_evidence_artifact_hashes)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise ValueError("source evidence hashes must be unique and sorted by name")
        if self.candidate_hashes != tuple(sorted(self.candidate_hashes)):
            raise ValueError("candidate hashes must be sorted")
        expected = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.manifest_hash, expected):
            raise ValueError("manifest_hash does not bind exact G4 source/candidate identities")
        return self

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        git_sha: str,
        git_tree: str,
        source_e4_manifest_hash: str,
        source_pit_snapshot_hash: str,
        source_evidence_artifact_hashes: tuple[EvidenceArtifactHash, ...],
        structural_component_manifest_hash: str,
        execution_model: ExecutionModelConfig,
        candidates: tuple[CandidateManifest, ...],
        trial_adaptivity_id: str,
        cutoff_id: str,
    ) -> Self:
        if not candidates:
            raise ValueError("G4 run requires at least one frozen candidate")
        for candidate in candidates:
            if candidate.structural_component_manifest_hash != structural_component_manifest_hash:
                raise ValueError("candidate structural authority conflicts with G4 run")
        artifacts = tuple(sorted(source_evidence_artifact_hashes, key=lambda item: item.name))
        candidate_hashes = tuple(sorted(item.candidate_hash for item in candidates))
        payload: dict[str, object] = {
            "schema_version": G4_SCHEMA_VERSION,
            "run_id": run_id,
            "git_sha": git_sha,
            "git_tree": git_tree,
            "source_e4_manifest_hash": source_e4_manifest_hash,
            "source_pit_snapshot_hash": source_pit_snapshot_hash,
            "source_evidence_artifact_hashes": [item.model_dump(mode="json") for item in artifacts],
            "structural_component_manifest_hash": structural_component_manifest_hash,
            "strategy_version": VNEXT_STRATEGY_VERSION,
            "policy_version": VNEXT_POLICY_VERSION,
            "parameter_version": VNEXT_PARAMETER_VERSION,
            "derivation_version": VNEXT_DERIVATION_VERSION,
            "data_version": VNEXT_DATA_VERSION,
            "nautilus_version": NAUTILUS_VERSION,
            "execution_model": execution_model.model_dump(mode="json"),
            "candidate_hashes": candidate_hashes,
            "trial_adaptivity_id": trial_adaptivity_id,
            "cutoff_id": cutoff_id,
            "confirmatory_e5": False,
            "private_api": False,
            "signing": False,
            "exchange_write": False,
            "venue_submitted": False,
        }
        digest = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "manifest_hash": digest})


class DerivedReplayCacheIdentity(StrictFrozenModel):
    source_g4_manifest_hash: Sha256Hex
    source_artifact_hashes: tuple[EvidenceArtifactHash, ...]
    transform_version: VersionId
    derived_payload_hash: Sha256Hex
    cache_identity_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"cache_identity_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        expected = sha256_hex(_DERIVED_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.cache_identity_hash, expected):
            raise ValueError("derived replay cache identity is not source-bound")
        return self

    @classmethod
    def create(
        cls,
        *,
        source_g4_manifest_hash: str,
        source_artifact_hashes: tuple[EvidenceArtifactHash, ...],
        transform_version: str,
        derived_payload_hash: str,
    ) -> Self:
        artifacts = tuple(sorted(source_artifact_hashes, key=lambda item: item.name))
        payload: dict[str, object] = {
            "source_g4_manifest_hash": source_g4_manifest_hash,
            "source_artifact_hashes": [item.model_dump(mode="json") for item in artifacts],
            "transform_version": transform_version,
            "derived_payload_hash": derived_payload_hash,
        }
        digest = sha256_hex(_DERIVED_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "cache_identity_hash": digest})
