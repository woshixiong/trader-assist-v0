"""Immutable Ordinary VNext G4 identities and execution assumptions."""

from __future__ import annotations

import hmac
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import (
    GitCommitOid,
    NonNegativeFiniteDecimal,
    OpaqueId,
    PositiveFiniteDecimal,
    Sha256Hex,
    VersionId,
    canonical_json_bytes,
    sha256_hex,
)

VNEXT_STRATEGY_VERSION: Literal["TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"] = (
    "TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"
)
VNEXT_POLICY_VERSION: Literal["TA_FRICTION_POSITION_POLICY_V0_2R2"] = (
    "TA_FRICTION_POSITION_POLICY_V0_2R2"
)
VNEXT_PARAMETER_VERSION: Literal["TA_PRE_E4_GRID_V0_1"] = "TA_PRE_E4_GRID_V0_1"
VNEXT_DERIVATION_VERSION: Literal[
    "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
] = (
    "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
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
_LINEAGE_DOMAIN = b"trader-assist-v0/vnext-g4/causal-lineage/v2r2\0"
_RESTART_REFERENCE_DOMAIN = b"trader-assist-v0/vnext-g4/restart-reference/v2r2\0"
_VALIDATION_REFERENCE_DOMAIN = b"trader-assist-v0/vnext-g4/validation-reference/v1\0"
_ORDER_INTENT_DOMAIN = b"trader-assist-v0/vnext-g4/order-intent/v1\0"

SOURCE_E4_STRATEGY_VERSION: Literal["TA_VNEXT_E4_C1_2026-09-11"] = (
    "TA_VNEXT_E4_C1_2026-09-11"
)
SOURCE_E4_POLICY_VERSION: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = (
    "TA_FRICTION_POSITION_POLICY_V0_1"
)
SOURCE_E4_PARAMETER_VERSION: Literal["TA_PRE_E4_GRID_V0_1"] = "TA_PRE_E4_GRID_V0_1"
SOURCE_E4_DERIVATION_VERSION: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = (
    "TA_MICROSTRUCTURE_DERIV_V0_1"
)

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


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class DerivationStatus(StrEnum):
    EVALUABLE = "EVALUABLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class RestartReferenceKind(StrEnum):
    PIVOT_HIGH = "PIVOT_HIGH"
    PIVOT_LOW = "PIVOT_LOW"


class LatencyEvidenceRole(StrEnum):
    CONTROL_ONLY = "CONTROL_ONLY"
    MODELLED = "MODELLED"
    OBSERVED = "OBSERVED"


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceArtifactHash(StrictFrozenModel):
    name: str = Field(min_length=1, max_length=160)
    sha256: Sha256Hex


class CausalLineage(StrictFrozenModel):
    """Exact source/semantic lineage for one Formal G4 derivation instance."""

    source_e4_manifest_hash: Sha256Hex
    source_pit_snapshot_hash: Sha256Hex
    source_structural_artifact_hash: Sha256Hex
    structural_component_manifest_hash: Sha256Hex
    market_id: Sha256Hex
    instrument_id: str = Field(min_length=3, max_length=160)
    formal_setup_id: OpaqueId
    formal_setup_admission_ordinal: int = Field(ge=1)
    formal_setup_admission_ts: int = Field(ge=1)
    thesis_id: OpaqueId
    activation_sequence_id: OpaqueId
    attempt_lineage_id: OpaqueId
    restart_reference_id: OpaqueId
    continuity_epoch: OpaqueId
    admission_epoch: OpaqueId
    instrument_metadata_version: VersionId
    instrument_metadata_hash: Sha256Hex
    validation_reference_id: VersionId
    validation_reference_hash: Sha256Hex
    strategy_version: Literal[
        "TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"
    ] = VNEXT_STRATEGY_VERSION
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_2R2"] = (
        VNEXT_POLICY_VERSION
    )
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = VNEXT_PARAMETER_VERSION
    derivation_version: Literal[
        "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
    ] = VNEXT_DERIVATION_VERSION
    lineage_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"lineage_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        expected = sha256_hex(_LINEAGE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.lineage_hash, expected):
            raise ValueError("lineage_hash does not bind exact causal source identities")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload = {
            **values,
            "strategy_version": VNEXT_STRATEGY_VERSION,
            "policy_version": VNEXT_POLICY_VERSION,
            "parameter_version": VNEXT_PARAMETER_VERSION,
            "derivation_version": VNEXT_DERIVATION_VERSION,
        }
        digest = sha256_hex(_LINEAGE_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "lineage_hash": digest})


class RestartReferenceEvidence(StrictFrozenModel):
    """Accepted C1 causal one-minute pivot identity; never inferred from a gap."""

    lineage_hash: Sha256Hex
    restart_reference_id: OpaqueId
    side: PositionSide
    kind: RestartReferenceKind
    price: PositiveFiniteDecimal
    reset_admission_ordinal: int = Field(ge=1)
    confirmed_admission_ordinal: int = Field(ge=1)
    confirmed_admission_ts: int = Field(ge=1)
    source_artifact_hash: Sha256Hex
    reference_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"reference_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        expected_kind = (
            RestartReferenceKind.PIVOT_HIGH
            if self.side is PositionSide.LONG
            else RestartReferenceKind.PIVOT_LOW
        )
        if self.kind is not expected_kind:
            raise ValueError("restart reference kind conflicts with side")
        if self.confirmed_admission_ordinal < self.reset_admission_ordinal:
            raise ValueError("restart reference confirmation precedes its reset")
        expected = sha256_hex(
            _RESTART_REFERENCE_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.reference_hash, expected):
            raise ValueError("reference_hash does not bind the causal restart reference")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        digest = sha256_hex(
            _RESTART_REFERENCE_DOMAIN + canonical_json_bytes(values)
        )
        return cls.model_validate({**values, "reference_hash": digest})


class ValidationReference(StrictFrozenModel):
    """Accepted Validation authority; absence remains explicit, never a default zero."""

    validation_reference_id: VersionId
    source_artifact_hash: Sha256Hex
    accepted_source_bound: Literal[True] = True
    validation_reference_only: Literal[True] = True
    production_account_fee_authority: Literal[False] = False
    actual_user_fee_rate_claim: Literal[False] = False
    fee_profile_id: VersionId | None = None
    fee_profile_source_hash: Sha256Hex | None = None
    fee_effective_at_ns: int | None = Field(default=None, ge=1)
    fee_bps: NonNegativeFiniteDecimal | None = None
    all_in_friction_state_id: VersionId | None = None
    all_in_friction_source_hash: Sha256Hex | None = None
    all_in_friction_bps: PositiveFiniteDecimal | None = None
    execution_model_id: VersionId | None = None
    execution_model_source_hash: Sha256Hex | None = None
    technical_quantity_rule_id: VersionId | None = None
    technical_quantity_rule_source_hash: Sha256Hex | None = None
    latency_control_id: VersionId | None = None
    latency_control_source_hash: Sha256Hex | None = None
    latency_ms: NonNegativeFiniteDecimal | None = None
    latency_evidence_role: LatencyEvidenceRole | None = None
    reference_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"reference_hash"})

    @property
    def fully_materialized(self) -> bool:
        return all(
            item is not None
            for item in (
                self.fee_profile_id,
                self.fee_profile_source_hash,
                self.fee_effective_at_ns,
                self.fee_bps,
                self.all_in_friction_state_id,
                self.all_in_friction_source_hash,
                self.all_in_friction_bps,
                self.execution_model_id,
                self.execution_model_source_hash,
                self.technical_quantity_rule_id,
                self.technical_quantity_rule_source_hash,
                self.latency_control_id,
                self.latency_control_source_hash,
                self.latency_ms,
                self.latency_evidence_role,
            )
        )

    @model_validator(mode="after")
    def verify_materialization_and_hash(self) -> Self:
        groups = (
            (
                self.fee_profile_id,
                self.fee_profile_source_hash,
                self.fee_effective_at_ns,
                self.fee_bps,
            ),
            (
                self.all_in_friction_state_id,
                self.all_in_friction_source_hash,
                self.all_in_friction_bps,
            ),
            (self.execution_model_id, self.execution_model_source_hash),
            (
                self.technical_quantity_rule_id,
                self.technical_quantity_rule_source_hash,
            ),
            (
                self.latency_control_id,
                self.latency_control_source_hash,
                self.latency_ms,
                self.latency_evidence_role,
            ),
        )
        if any(
            any(item is not None for item in group)
            and any(item is None for item in group)
            for group in groups
        ):
            raise ValueError("Validation materialization groups must be complete or absent")
        if (
            self.latency_ms == 0
            and self.latency_evidence_role is not LatencyEvidenceRole.CONTROL_ONLY
        ):
            raise ValueError("0ms latency may be represented only as CONTROL_ONLY")
        expected = sha256_hex(
            _VALIDATION_REFERENCE_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.reference_hash, expected):
            raise ValueError("reference_hash does not bind accepted Validation authority")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload = {
            "accepted_source_bound": True,
            "validation_reference_only": True,
            "production_account_fee_authority": False,
            "actual_user_fee_rate_claim": False,
            "fee_profile_id": None,
            "fee_profile_source_hash": None,
            "fee_effective_at_ns": None,
            "fee_bps": None,
            "all_in_friction_state_id": None,
            "all_in_friction_source_hash": None,
            "all_in_friction_bps": None,
            "execution_model_id": None,
            "execution_model_source_hash": None,
            "technical_quantity_rule_id": None,
            "technical_quantity_rule_source_hash": None,
            "latency_control_id": None,
            "latency_control_source_hash": None,
            "latency_ms": None,
            "latency_evidence_role": None,
            **values,
        }
        digest = sha256_hex(
            _VALIDATION_REFERENCE_DOMAIN + canonical_json_bytes(payload)
        )
        return cls.model_validate({**payload, "reference_hash": digest})


class TechnicalOrderQuantity(StrictFrozenModel):
    quantity: PositiveFiniteDecimal
    displayed_opposite_l1_size: PositiveFiniteDecimal
    size_decimals: int = Field(ge=0, le=18)
    instrument_metadata_version: VersionId
    instrument_metadata_hash: Sha256Hex
    bbo_admission_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_venue_quantity(self) -> Self:
        quantum = Decimal(1).scaleb(-self.size_decimals)
        if self.quantity != self.quantity.quantize(quantum):
            raise ValueError("technical quantity is not venue grid-aligned")
        if self.quantity > self.displayed_opposite_l1_size:
            raise ValueError("technical quantity exceeds causal opposite-side displayed L1")
        return self


class HypotheticalOrderIntent(StrictFrozenModel):
    strategy_decision_id: OpaqueId
    candidate_hash: Sha256Hex
    side: PositionSide
    technical_quantity: TechnicalOrderQuantity
    executable_price: PositiveFiniteDecimal
    technical_notional: PositiveFiniteDecimal
    activation_sequence_id: OpaqueId
    activation_reference_hash: Sha256Hex
    validation_reference_id: VersionId
    validation_reference_hash: Sha256Hex
    causal_lineage_hash: Sha256Hex
    not_submitted: Literal[True] = True
    venue_submitted: Literal[False] = False
    order_intent_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"order_intent_hash"})

    @model_validator(mode="after")
    def verify_identity(self) -> Self:
        if self.technical_notional != self.technical_quantity.quantity * self.executable_price:
            raise ValueError("technical notional does not bind quantity and executable price")
        expected = sha256_hex(
            _ORDER_INTENT_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.order_intent_hash, expected):
            raise ValueError("order_intent_hash does not bind the canonical hypothetical intent")
        return self

    @classmethod
    def create(
        cls,
        *,
        strategy_decision_id: str,
        candidate_hash: str,
        side: PositionSide,
        technical_quantity: TechnicalOrderQuantity,
        executable_price: Decimal,
        activation_reference_hash: str,
        validation: ValidationReference,
        lineage: CausalLineage,
    ) -> Self:
        if not validation.fully_materialized:
            raise ValueError("canonical OrderIntent requires fully materialized Validation")
        if (
            validation.validation_reference_id != lineage.validation_reference_id
            or validation.reference_hash != lineage.validation_reference_hash
        ):
            raise ValueError("canonical OrderIntent Validation lineage conflicts")
        if (
            technical_quantity.instrument_metadata_version
            != lineage.instrument_metadata_version
            or technical_quantity.instrument_metadata_hash
            != lineage.instrument_metadata_hash
        ):
            raise ValueError("canonical OrderIntent quantity metadata conflicts")
        payload = {
            "strategy_decision_id": strategy_decision_id,
            "candidate_hash": candidate_hash,
            "side": side,
            "technical_quantity": technical_quantity.model_dump(mode="json"),
            "executable_price": executable_price,
            "technical_notional": technical_quantity.quantity * executable_price,
            "activation_sequence_id": lineage.activation_sequence_id,
            "activation_reference_hash": activation_reference_hash,
            "validation_reference_id": validation.validation_reference_id,
            "validation_reference_hash": validation.reference_hash,
            "causal_lineage_hash": lineage.lineage_hash,
            "not_submitted": True,
            "venue_submitted": False,
        }
        digest = sha256_hex(_ORDER_INTENT_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "order_intent_hash": digest})


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
    strategy_version: Literal["TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"] = (
        VNEXT_STRATEGY_VERSION
    )
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_2R2"] = VNEXT_POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = VNEXT_PARAMETER_VERSION
    derivation_version: Literal[
        "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
    ] = VNEXT_DERIVATION_VERSION
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
    source_e4_strategy_version: Literal["TA_VNEXT_E4_C1_2026-09-11"] = (
        SOURCE_E4_STRATEGY_VERSION
    )
    source_e4_policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = (
        SOURCE_E4_POLICY_VERSION
    )
    source_e4_parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = (
        SOURCE_E4_PARAMETER_VERSION
    )
    source_e4_derivation_version: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = (
        SOURCE_E4_DERIVATION_VERSION
    )
    source_pit_snapshot_hash: Sha256Hex
    source_evidence_artifact_hashes: tuple[EvidenceArtifactHash, ...]
    structural_component_manifest_hash: Sha256Hex
    strategy_version: Literal["TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"] = (
        VNEXT_STRATEGY_VERSION
    )
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_2R2"] = VNEXT_POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = VNEXT_PARAMETER_VERSION
    derivation_version: Literal[
        "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
    ] = VNEXT_DERIVATION_VERSION
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
            "source_e4_strategy_version": SOURCE_E4_STRATEGY_VERSION,
            "source_e4_policy_version": SOURCE_E4_POLICY_VERSION,
            "source_e4_parameter_version": SOURCE_E4_PARAMETER_VERSION,
            "source_e4_derivation_version": SOURCE_E4_DERIVATION_VERSION,
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
