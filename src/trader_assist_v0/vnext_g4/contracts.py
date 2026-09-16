"""Immutable Ordinary VNext G4 contracts.

These contracts bind the publication-clean VNext candidate to accepted E4 source
evidence without granting transport, account, order-submission, or real-capital authority.
"""

from __future__ import annotations

import hmac
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self, cast

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
from trader_assist_v0.nautilus_e4.contracts import (
    DATA_VERSION,
    DERIVATION_VERSION,
    NAUTILUS_VERSION,
    PARAMETER_VERSION,
    POLICY_VERSION,
    STRATEGY_VERSION,
)

G4_SCHEMA_VERSION: Literal["VNEXT_G4_V1"] = "VNEXT_G4_V1"
G4_EXECUTION_MODEL_VERSION: Literal["VNEXT_G4_MARKETABLE_L1_V1"] = (
    "VNEXT_G4_MARKETABLE_L1_V1"
)
G4_STAGE_ROLE: Literal["DEVELOPMENT_CALIBRATION_ONLY"] = "DEVELOPMENT_CALIBRATION_ONLY"

_EXECUTION_DOMAIN = b"trader-assist-v0/vnext-g4/execution-model/v1\0"
_CANDIDATE_DOMAIN = b"trader-assist-v0/vnext-g4/candidate/v1\0"
_RUN_DOMAIN = b"trader-assist-v0/vnext-g4/run/v1\0"
_FEATURE_DOMAIN = b"trader-assist-v0/vnext-g4/features/v1\0"
_EVALUATION_DOMAIN = b"trader-assist-v0/vnext-g4/evaluation/v1\0"
_EXECUTION_RESULT_DOMAIN = b"trader-assist-v0/vnext-g4/execution-result/v1\0"


class EntryActivation(StrEnum):
    EA0_FORMAL_TIME_CONTROL = "EA0_FORMAL_TIME_CONTROL"
    EA1_DIRECT_REACCEL_PRICE = "EA1_DIRECT_REACCEL_PRICE"
    EA2_RETEST_REACCEL_PRICE = "EA2_RETEST_REACCEL_PRICE"
    EA3_SIMPLE_FLOW_PRICE_RESPONSE = "EA3_SIMPLE_FLOW_PRICE_RESPONSE"


class AttemptPolicy(StrEnum):
    AP0_STRUCTURAL_REFERENCE = "AP0_STRUCTURAL_REFERENCE"
    AP1_FIXED_BPS = "AP1_FIXED_BPS"
    AP2_VOL_NORMALIZED = "AP2_VOL_NORMALIZED"
    AP3_TIME_NO_FOLLOWTHROUGH = "AP3_TIME_NO_FOLLOWTHROUGH"
    AP4_SIMPLE_PRICE_PLUS_TIME = "AP4_SIMPLE_PRICE_PLUS_TIME"


class ReentryPolicy(StrEnum):
    R0_NO_REENTRY = "R0_NO_REENTRY"
    R1_ONE_FRESH_CAUSAL_ACTIVATION = "R1_ONE_FRESH_CAUSAL_ACTIVATION"
    BLIND_IMMEDIATE_NEGATIVE_CONTROL = "BLIND_IMMEDIATE_NEGATIVE_CONTROL"


class WinnerConfirmation(StrEnum):
    WC0_PROGRESS = "WC0_PROGRESS"
    WC1_PROGRESS_PERSISTENCE = "WC1_PROGRESS_PERSISTENCE"
    WC2_PROGRESS_FRESH_STRUCTURE = "WC2_PROGRESS_FRESH_STRUCTURE"
    WC3_PROGRESS_FLOW_RESPONSE = "WC3_PROGRESS_FLOW_RESPONSE"


class WinnerAdd(StrEnum):
    A0_NO_ADD = "A0_NO_ADD"


class ExitPolicy(StrEnum):
    X0_FIXED_R_CONTROL = "X0_FIXED_R_CONTROL"
    X1_STRUCTURAL_FULL_EXIT = "X1_STRUCTURAL_FULL_EXIT"
    X2_MFE_GIVEBACK = "X2_MFE_GIVEBACK"
    X3_STRUCTURAL_RATCHET_GIVEBACK = "X3_STRUCTURAL_RATCHET_GIVEBACK"


class ParticipationState(StrEnum):
    BLOCKED = "BLOCKED"
    TAKE = "TAKE"
    WAIT = "WAIT"
    PASS = "PASS"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class ExecutionModelConfig(BaseModel):
    """Explicit claim-limited provider-native simulation assumptions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    execution_model_version: Literal["VNEXT_G4_MARKETABLE_L1_V1"] = (
        G4_EXECUTION_MODEL_VERSION
    )
    order_primitive: Literal["MARKETABLE"] = "MARKETABLE"
    book_type: Literal["L1_MBP"] = "L1_MBP"
    bar_execution: Literal[False] = False
    trade_execution: Literal[False] = False
    liquidity_consumption: Literal[True] = True
    queue_position: Literal[False] = False
    prob_fill_on_limit: NonNegativeFiniteDecimal
    prob_slippage: NonNegativeFiniteDecimal
    random_seed: int | None = None
    l1_size_feasibility_required: Literal[True] = True
    passive_touch_is_fill: Literal[False] = False
    trigger_price_is_fill: Literal[False] = False
    execution_model_limited: Literal[True] = True
    config_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"config_hash"})

    @model_validator(mode="after")
    def validate_config(self) -> Self:
        one = Decimal("1")
        if Decimal(self.prob_fill_on_limit) > one or Decimal(self.prob_slippage) > one:
            raise ValueError("fill probabilities must be within [0, 1]")
        stochastic = any(
            Decimal(value) not in {Decimal("0"), Decimal("1")}
            for value in (self.prob_fill_on_limit, self.prob_slippage)
        )
        if stochastic and self.random_seed is None:
            raise ValueError("stochastic execution assumptions require an explicit seed")
        expected = sha256_hex(
            _EXECUTION_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.config_hash, expected):
            raise ValueError("config_hash does not bind explicit execution assumptions")
        return self

    @classmethod
    def create(
        cls,
        *,
        prob_fill_on_limit: Decimal = Decimal("1"),
        prob_slippage: Decimal = Decimal("0"),
        random_seed: int | None = None,
    ) -> Self:
        payload: dict[str, object] = {
            "schema_version": G4_SCHEMA_VERSION,
            "execution_model_version": G4_EXECUTION_MODEL_VERSION,
            "order_primitive": "MARKETABLE",
            "book_type": "L1_MBP",
            "bar_execution": False,
            "trade_execution": False,
            "liquidity_consumption": True,
            "queue_position": False,
            "prob_fill_on_limit": prob_fill_on_limit,
            "prob_slippage": prob_slippage,
            "random_seed": random_seed,
            "l1_size_feasibility_required": True,
            "passive_touch_is_fill": False,
            "trigger_price_is_fill": False,
            "execution_model_limited": True,
        }
        digest = sha256_hex(_EXECUTION_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "config_hash": digest})


class VNextCandidateConfig(BaseModel):
    """One immutable bounded C1 candidate; no unrestricted Cartesian search."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    candidate_id: OpaqueId
    strategy_version: Literal["TA_VNEXT_E4_C1_2026-09-11"] = STRATEGY_VERSION
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = PARAMETER_VERSION
    derivation_version: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = DERIVATION_VERSION
    data_version: Literal["TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"] = (
        DATA_VERSION
    )
    entry_activation: EntryActivation
    attempt_policy: AttemptPolicy
    reentry_policy: ReentryPolicy
    winner_confirmation: WinnerConfirmation
    winner_add: Literal[WinnerAdd.A0_NO_ADD] = WinnerAdd.A0_NO_ADD
    exit_policy: ExitPolicy
    room_to_cost_hurdle: Literal[2, 3, 4]
    fixed_stop_bps: Literal[4, 6, 8, 10, 12, 15, 20] | None = None
    rv_multiplier: Literal["0.5", "1.0", "1.5"] | None = None
    no_followthrough_seconds: Literal[30, 60, 90, 120, 180, 300] | None = None
    winner_progress_bps: Literal[3, 5, 8, 10, 15, 20]
    winner_persistence_seconds: Literal[30, 60] | None = None
    giveback_numerator: Literal[1, 2] | None = None
    giveback_denominator: Literal[2, 3] | None = None
    candidate_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"candidate_hash"})

    @model_validator(mode="after")
    def validate_candidate(self) -> Self:
        if self.attempt_policy is AttemptPolicy.AP1_FIXED_BPS and self.fixed_stop_bps is None:
            raise ValueError("AP1 requires a frozen fixed_stop_bps")
        if self.attempt_policy is AttemptPolicy.AP2_VOL_NORMALIZED and self.rv_multiplier is None:
            raise ValueError("AP2 requires a frozen rv_multiplier")
        if (
            self.attempt_policy is AttemptPolicy.AP3_TIME_NO_FOLLOWTHROUGH
            and self.no_followthrough_seconds is None
        ):
            raise ValueError("AP3 requires a frozen no_followthrough_seconds")
        if self.attempt_policy is AttemptPolicy.AP4_SIMPLE_PRICE_PLUS_TIME and (
            self.fixed_stop_bps is None or self.no_followthrough_seconds is None
        ):
            raise ValueError("AP4 identity requires frozen price and time components")
        if (
            self.winner_confirmation is WinnerConfirmation.WC1_PROGRESS_PERSISTENCE
            and self.winner_persistence_seconds is None
        ):
            raise ValueError("WC1 requires a frozen persistence window")
        if self.exit_policy in {
            ExitPolicy.X2_MFE_GIVEBACK,
            ExitPolicy.X3_STRUCTURAL_RATCHET_GIVEBACK,
        }:
            pair = (self.giveback_numerator, self.giveback_denominator)
            if pair not in {(1, 3), (1, 2), (2, 3)}:
                raise ValueError("X2/X3 giveback must use the frozen {1/3, 1/2, 2/3} grid")
        expected = sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.candidate_hash, expected):
            raise ValueError("candidate_hash does not bind VNext candidate identity")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload: dict[str, object] = {
            "schema_version": G4_SCHEMA_VERSION,
            "strategy_version": STRATEGY_VERSION,
            "policy_version": POLICY_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "derivation_version": DERIVATION_VERSION,
            "data_version": DATA_VERSION,
            "winner_add": WinnerAdd.A0_NO_ADD,
            **values,
        }
        digest = sha256_hex(_CANDIDATE_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "candidate_hash": digest})


class G4RunManifest(BaseModel):
    """Derived run identity. Accepted E4 evidence remains immutable source authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    run_id: OpaqueId
    git_sha: GitCommitOid
    git_tree: GitCommitOid
    source_e4_manifest_hash: Sha256Hex
    source_pit_snapshot_hash: Sha256Hex
    source_artifact_hashes: dict[str, Sha256Hex]
    source_artifact_set_hash: Sha256Hex
    structural_component_manifest_hash: Sha256Hex
    candidate_hash: Sha256Hex
    execution_model_hash: Sha256Hex
    nautilus_version: Literal["2.0.0rc5"] = NAUTILUS_VERSION
    trial_ledger_id: VersionId
    evidence_cutoff_id: VersionId
    stage_role: Literal["DEVELOPMENT_CALIBRATION_ONLY"] = G4_STAGE_ROLE
    derived_catalog_rebuildable: Literal[True] = True
    source_e4_authority_immutable: Literal[True] = True
    pre_e5_confirmatory_evidence_open: Literal[False] = False
    private_api: Literal[False] = False
    signing: Literal[False] = False
    exchange_write: Literal[False] = False
    real_capital: Literal[False] = False
    manifest_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"manifest_hash"})

    @model_validator(mode="after")
    def validate_manifest(self) -> Self:
        sorted_hashes = dict(sorted(self.source_artifact_hashes.items()))
        if sorted_hashes != self.source_artifact_hashes:
            raise ValueError("source artifact hashes must be sorted by path")
        expected_set = sha256_hex(canonical_json_bytes(sorted_hashes))
        if not hmac.compare_digest(self.source_artifact_set_hash, expected_set):
            raise ValueError("source artifact set hash mismatch")
        expected = sha256_hex(_RUN_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.manifest_hash, expected):
            raise ValueError("manifest_hash does not bind the G4 run")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        raw_hashes = cast(dict[str, Sha256Hex], values.pop("source_artifact_hashes"))
        source_hashes = dict(sorted(raw_hashes.items()))
        payload: dict[str, object] = {
            "schema_version": G4_SCHEMA_VERSION,
            **values,
            "source_artifact_hashes": source_hashes,
            "source_artifact_set_hash": sha256_hex(canonical_json_bytes(source_hashes)),
            "nautilus_version": NAUTILUS_VERSION,
            "stage_role": G4_STAGE_ROLE,
            "derived_catalog_rebuildable": True,
            "source_e4_authority_immutable": True,
            "pre_e5_confirmatory_evidence_open": False,
            "private_api": False,
            "signing": False,
            "exchange_write": False,
            "real_capital": False,
        }
        digest = sha256_hex(_RUN_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "manifest_hash": digest})


class VNextFeatureSnapshot(BaseModel):
    """Causal, already-admitted feature state consumed by the pure VNext policy layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    market_id: Sha256Hex
    expression_id: OpaqueId
    package_id: OpaqueId
    candidate_hash: Sha256Hex
    source_e4_manifest_hash: Sha256Hex
    admission_ordinal: int = Field(ge=1)
    decision_ts: int = Field(ge=1)
    side: Literal["LONG", "SHORT"]
    structural_setup_confirmed: bool
    thesis_valid: bool
    data_evaluable: bool
    bbo_state_valid: bool
    predecision_window_complete: bool
    ea1_direct_reaccel: bool
    ea2_retest_reaccel: bool
    flow_imbalance_side_adjusted: Decimal | None = None
    flow_price_response_bps: Decimal | None = None
    remaining_room_bps: PositiveFiniteDecimal
    all_in_friction_bps: NonNegativeFiniteDecimal
    intended_notional: PositiveFiniteDecimal
    top_level_notional: NonNegativeFiniteDecimal
    attempt_number: Literal[1, 2] = 1
    adverse_progress_bps: NonNegativeFiniteDecimal
    micro_rv_60s_bps: NonNegativeFiniteDecimal | None = None
    elapsed_attempt_seconds: int = Field(ge=0)
    no_followthrough_state: bool | None = None
    fresh_reentry_activation: bool = False
    favorable_progress_bps: NonNegativeFiniteDecimal
    favorable_persistence_seconds: int = Field(ge=0)
    fresh_favorable_structure: bool = False
    structural_stop_reached: bool = False
    structural_exit_reached: bool = False
    fixed_r_exit_reached: bool | None = None
    current_net_progress_bps: Decimal = Decimal("0")
    net_mfe_bps: NonNegativeFiniteDecimal = Decimal("0")
    feature_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"feature_hash"})

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        for name in (
            "flow_imbalance_side_adjusted",
            "flow_price_response_bps",
            "current_net_progress_bps",
        ):
            value = getattr(self, name)
            if value is not None and not Decimal(value).is_finite():
                raise ValueError(f"{name} must be finite")
        expected = sha256_hex(_FEATURE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.feature_hash, expected):
            raise ValueError("feature_hash does not bind causal feature state")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload: dict[str, object] = {"schema_version": G4_SCHEMA_VERSION, **values}
        digest = sha256_hex(_FEATURE_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "feature_hash": digest})


class VNextEvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    package_id: OpaqueId
    candidate_hash: Sha256Hex
    feature_hash: Sha256Hex
    participation: ParticipationState
    activation: bool
    stop_triggered: bool
    winner_confirmed: bool
    exit_triggered: bool
    can_reenter: bool
    order_intent: Literal["MARKETABLE_ENTRY", "NONE"] = "NONE"
    reason_codes: tuple[str, ...]
    record_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"record_hash"})

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        if self.participation is not ParticipationState.TAKE and self.order_intent != "NONE":
            raise ValueError("only TAKE can emit a hypothetical entry intent")
        expected = sha256_hex(_EVALUATION_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.record_hash, expected):
            raise ValueError("record_hash mismatch")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload: dict[str, object] = {"schema_version": G4_SCHEMA_VERSION, **values}
        digest = sha256_hex(_EVALUATION_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "record_hash": digest})


class SimulatedExecutionResult(BaseModel):
    """Claim-limited execution observation; never venue-submitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["VNEXT_G4_V1"] = G4_SCHEMA_VERSION
    package_id: OpaqueId
    candidate_hash: Sha256Hex
    execution_model_hash: Sha256Hex
    order_active_ts: int = Field(ge=1)
    first_executable_state_ts: int | None = Field(default=None, ge=1)
    l1_capacity_sufficient: bool
    passive_order: bool = False
    queue_evidence_supported: bool = False
    modeled_fill: bool
    fill_ts: int | None = Field(default=None, ge=1)
    fill_price: PositiveFiniteDecimal | None = None
    fill_qty: PositiveFiniteDecimal | None = None
    fee_bps: NonNegativeFiniteDecimal = Decimal("0")
    slippage_bps: NonNegativeFiniteDecimal = Decimal("0")
    execution_model_limited: bool
    venue_submitted: Literal[False] = False
    private_api: Literal[False] = False
    signing: Literal[False] = False
    exchange_write: Literal[False] = False
    result_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"result_hash"})

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        if not self.l1_capacity_sufficient and not self.execution_model_limited:
            raise ValueError("insufficient L1 capacity must be typed execution-model-limited")
        if self.passive_order and self.modeled_fill and not self.queue_evidence_supported:
            raise ValueError("passive touch cannot become a fill without queue evidence")
        if (
            self.first_executable_state_ts is not None
            and self.first_executable_state_ts < self.order_active_ts
        ):
            raise ValueError("executable state cannot precede order-active time")
        if self.modeled_fill:
            if any(
                value is None
                for value in (
                    self.first_executable_state_ts,
                    self.fill_ts,
                    self.fill_price,
                    self.fill_qty,
                )
            ):
                raise ValueError("modeled fill requires full causal executable-state evidence")
            assert self.fill_ts is not None
            if self.fill_ts < self.order_active_ts:
                raise ValueError("fill cannot precede order-active time")
        elif any(value is not None for value in (self.fill_ts, self.fill_price, self.fill_qty)):
            raise ValueError("nonfill cannot carry fill values")
        expected = sha256_hex(
            _EXECUTION_RESULT_DOMAIN + canonical_json_bytes(self.identity_payload())
        )
        if not hmac.compare_digest(self.result_hash, expected):
            raise ValueError("result_hash mismatch")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload: dict[str, object] = {"schema_version": G4_SCHEMA_VERSION, **values}
        digest = sha256_hex(_EXECUTION_RESULT_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "result_hash": digest})
