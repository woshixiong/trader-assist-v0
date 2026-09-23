"""Versioned, Nautilus-independent contracts for the E4 capture prefix."""

from __future__ import annotations

import hmac
import platform
import sys
from enum import StrEnum
from typing import Any, Final, Literal

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

CAPTURE_SCHEMA_VERSION: Final[Literal["E4_CAPTURE_V1"]] = "E4_CAPTURE_V1"
STRATEGY_VERSION: Final[Literal["TA_VNEXT_E4_C1_2026-09-11"]] = (
    "TA_VNEXT_E4_C1_2026-09-11"
)
POLICY_VERSION: Final[Literal["TA_FRICTION_POSITION_POLICY_V0_1"]] = (
    "TA_FRICTION_POSITION_POLICY_V0_1"
)
PARAMETER_VERSION: Final[Literal["TA_PRE_E4_GRID_V0_1"]] = "TA_PRE_E4_GRID_V0_1"
DERIVATION_VERSION: Final[Literal["TA_MICROSTRUCTURE_DERIV_V0_1"]] = (
    "TA_MICROSTRUCTURE_DERIV_V0_1"
)
DATA_VERSION: Final[
    Literal["TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"]
] = "TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"
LEGACY_NAUTILUS_VERSION: Final[Literal["2.0.0rc4"]] = "2.0.0rc4"
NAUTILUS_VERSION: Final[Literal["2.0.0rc5"]] = "2.0.0rc5"
SUPPORTED_EVIDENCE_NAUTILUS_VERSIONS: Final[tuple[str, ...]] = (
    LEGACY_NAUTILUS_VERSION,
    NAUTILUS_VERSION,
)
EXECUTION_MODEL_VERSION: Final[Literal["E4_PHASE_A_MARKETABLE_L1_V1"]] = (
    "E4_PHASE_A_MARKETABLE_L1_V1"
)
WARMUP_5M_BARS = 2304
PRE_DECISION_RETENTION_NS = 60_000_000_000
POST_TERMINAL_MICRO_NS = 1_800_000_000_000
POST_TERMINAL_CONTEXT_NS = 21_600_000_000_000

_SNAPSHOT_DOMAIN = b"trader-assist-v0/e4/pit-snapshot/v1\0"
_MANIFEST_DOMAIN = b"trader-assist-v0/e4/run-manifest/v1\0"
_SOURCE_DOMAIN = b"trader-assist-v0/e4/source-event/v1\0"
_ADMISSION_DOMAIN = b"trader-assist-v0/e4/admission/v1\0"
_LIFECYCLE_DOMAIN = b"trader-assist-v0/e4/lifecycle/v1\0"


class CaptureTier(StrEnum):
    DISCOVERY = "DISCOVERY"
    WATCH = "WATCH"
    ACTIONABLE = "ACTIONABLE"


class DataKind(StrEnum):
    BBO = "BBO"
    DEPTH10 = "DEPTH10"
    TRADE = "TRADE"
    BAR = "BAR"
    CONTEXT = "CONTEXT"


class EvidenceState(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    GAPPED = "GAPPED"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    PRE_DECISION_WINDOW_INCOMPLETE = "PRE_DECISION_WINDOW_INCOMPLETE"
    INTERRUPTED = "INTERRUPTED"
    EXECUTION_MODEL_LIMITED = "EXECUTION_MODEL_LIMITED"


class StreamHealth(StrEnum):
    HEALTHY = "HEALTHY"
    DISCONNECTED = "DISCONNECTED"
    REESTABLISHING = "REESTABLISHING"


class DecisionState(StrEnum):
    BLOCKED = "BLOCKED"
    TAKE = "TAKE"
    WAIT = "WAIT"
    PASS = "PASS"
    NONACTIVATION = "NONACTIVATION"
    NO_SUBMIT = "NO_SUBMIT"
    NONFILL = "NONFILL"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class LifecycleKind(StrEnum):
    OPPORTUNITY = "OPPORTUNITY"
    ELIGIBILITY = "ELIGIBILITY"
    ARMED = "ARMED"
    ACTIVATION = "ACTIVATION"
    THESIS = "THESIS"
    ATTEMPT = "ATTEMPT"
    WINNER = "WINNER"
    EXIT = "EXIT"


class LifecycleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TERMINAL = "TERMINAL"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class ApprovalTimingMode(StrEnum):
    POST_ACTIVATION = "POST_ACTIVATION"
    PREAUTHORIZED_ARMED = "PREAUTHORIZED_ARMED"


class ApprovalProvenance(StrEnum):
    SIMULATED = "SIMULATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    OBSERVED = "OBSERVED"


class GuardDecision(StrEnum):
    PASS = "PASS"
    NO_SUBMIT = "NO_SUBMIT"


class FailureClass(StrEnum):
    APPLICATION_FAILURE = "APPLICATION_FAILURE"
    DATA_INCOMPLETENESS = "DATA_INCOMPLETENESS"
    STRATEGY_NOT_EVALUABLE = "STRATEGY_NOT_EVALUABLE"
    HARNESS_INFRASTRUCTURE_FAILURE = "HARNESS_INFRASTRUCTURE_FAILURE"


class TailPhase(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class MarketExpression(BaseModel):
    """Immutable prospective venue-expression identity and public state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: Sha256Hex
    venue: Literal["HYPERLIQUID"] = "HYPERLIQUID"
    dex: str = Field(min_length=1, max_length=80)
    provider_coin: str = Field(min_length=1, max_length=80)
    instrument_id: str = Field(min_length=3, max_length=160)
    provider_id: Literal["NAUTILUS_HYPERLIQUID"] = "NAUTILUS_HYPERLIQUID"
    expression_id: OpaqueId
    listing_state: str | None = Field(default=None, max_length=80)
    instrument_metadata_version: VersionId
    instrument_metadata_hash: Sha256Hex
    fee_state_version: VersionId | None = None
    fee_state_hash: Sha256Hex | None = None
    growth_mode: str | None = Field(default=None, max_length=80)
    deployer_fee_state: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_market_identity(self) -> MarketExpression:
        expected = sha256_hex(
            f"HYPERLIQUID|{self.dex}|{self.provider_coin}".encode()
        )
        if not hmac.compare_digest(self.market_id, expected):
            raise ValueError("market_id does not bind venue/DEX/provider coin identity")
        return self


class PitUniverseSnapshot(BaseModel):
    """Hash-bound current-state snapshot; it makes no historical reconstruction claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["E4_CAPTURE_V1"] = CAPTURE_SCHEMA_VERSION
    observed_at_ns: int = Field(ge=1)
    history_provenance: Literal["PROSPECTIVE_CURRENT_STATE"] = "PROSPECTIVE_CURRENT_STATE"
    expressions: tuple[MarketExpression, ...] = Field(min_length=1)
    snapshot_id: Sha256Hex
    snapshot_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"snapshot_id", "snapshot_hash"})

    @model_validator(mode="after")
    def validate_snapshot(self) -> PitUniverseSnapshot:
        ids = [(item.market_id, item.expression_id) for item in self.expressions]
        if len(ids) != len(set(ids)):
            raise ValueError("PIT snapshot contains duplicate market/expression identity")
        expected = sha256_hex(_SNAPSHOT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.snapshot_hash, expected) or not hmac.compare_digest(
            self.snapshot_id, expected
        ):
            raise ValueError("PIT snapshot hash does not bind current public state")
        return self

    @classmethod
    def create(
        cls, *, observed_at_ns: int, expressions: tuple[MarketExpression, ...]
    ) -> PitUniverseSnapshot:
        payload: dict[str, object] = {
            "schema_version": CAPTURE_SCHEMA_VERSION,
            "observed_at_ns": observed_at_ns,
            "history_provenance": "PROSPECTIVE_CURRENT_STATE",
            "expressions": [item.model_dump(mode="json") for item in expressions],
        }
        digest = sha256_hex(_SNAPSHOT_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "snapshot_id": digest, "snapshot_hash": digest})


class RunManifest(BaseModel):
    """Exact version/run identity for one public-only Capture process."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["E4_CAPTURE_V1"] = CAPTURE_SCHEMA_VERSION
    run_id: OpaqueId
    git_sha: GitCommitOid
    git_tree: GitCommitOid
    strategy_version: Literal["TA_VNEXT_E4_C1_2026-09-11"] = STRATEGY_VERSION
    policy_version: Literal["TA_FRICTION_POSITION_POLICY_V0_1"] = POLICY_VERSION
    parameter_version: Literal["TA_PRE_E4_GRID_V0_1"] = PARAMETER_VERSION
    derivation_version: Literal["TA_MICROSTRUCTURE_DERIV_V0_1"] = DERIVATION_VERSION
    data_version: Literal[
        "TA_VNEXT_RESEARCH_DATA_CONTRACT_V1_2026-09-11_REPAIR1"
    ] = DATA_VERSION
    nautilus_version: Literal["2.0.0rc4", "2.0.0rc5"] = NAUTILUS_VERSION
    runtime_python: str
    runtime_platform: str
    pit_snapshot_id: Sha256Hex
    pit_snapshot_hash: Sha256Hex
    provider_instrument_ids: tuple[str, ...]
    fee_state_ids: tuple[str, ...] = ()
    process_epoch: OpaqueId
    continuity_epoch: OpaqueId
    admission_epoch: OpaqueId
    execution_model_version: Literal["E4_PHASE_A_MARKETABLE_L1_V1"] = (
        EXECUTION_MODEL_VERSION
    )
    execution_model_limited: bool = True
    random_seed: int | None = None
    stochastic_config_hash: Sha256Hex | None = None
    input_catalog_hash: Sha256Hex | None = None
    semantic_evidence_hash: Sha256Hex | None = None
    capture_configuration: dict[str, object]
    subscription_policy: dict[str, object]
    trial_ledger_id: VersionId
    adaptivity_state: Literal["LEGACY_INCOMPLETE_CONSERVATIVE"] = (
        "LEGACY_INCOMPLETE_CONSERVATIVE"
    )
    private_api: Literal[False] = False
    exchange_write: Literal[False] = False
    real_exec_client_registered: Literal[False] = False
    manifest_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"manifest_hash"})

    @model_validator(mode="after")
    def validate_manifest(self) -> RunManifest:
        if self.nautilus_version not in SUPPORTED_EVIDENCE_NAUTILUS_VERSIONS:
            raise ValueError("unsupported Nautilus evidence version")
        if tuple(sorted(self.provider_instrument_ids)) != self.provider_instrument_ids:
            raise ValueError("provider instrument identities must be sorted")
        if self.random_seed is None and self.stochastic_config_hash is not None:
            raise ValueError("stochastic config cannot exist without an explicit seed")
        expected = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.manifest_hash, expected):
            raise ValueError("manifest_hash does not bind the Capture run")
        return self

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        git_sha: str,
        git_tree: str,
        snapshot: PitUniverseSnapshot,
        process_epoch: str,
        continuity_epoch: str,
        admission_epoch: str,
        capture_configuration: dict[str, object],
        subscription_policy: dict[str, object],
        trial_ledger_id: str,
    ) -> RunManifest:
        payload: dict[str, object] = {
            "schema_version": CAPTURE_SCHEMA_VERSION,
            "run_id": run_id,
            "git_sha": git_sha,
            "git_tree": git_tree,
            "strategy_version": STRATEGY_VERSION,
            "policy_version": POLICY_VERSION,
            "parameter_version": PARAMETER_VERSION,
            "derivation_version": DERIVATION_VERSION,
            "data_version": DATA_VERSION,
            "nautilus_version": NAUTILUS_VERSION,
            "runtime_python": platform.python_version(),
            "runtime_platform": f"{platform.system()}-{platform.machine()}",
            "pit_snapshot_id": snapshot.snapshot_id,
            "pit_snapshot_hash": snapshot.snapshot_hash,
            "provider_instrument_ids": tuple(
                sorted(item.instrument_id for item in snapshot.expressions)
            ),
            "fee_state_ids": tuple(
                sorted(
                    item.fee_state_hash
                    for item in snapshot.expressions
                    if item.fee_state_hash is not None
                )
            ),
            "process_epoch": process_epoch,
            "continuity_epoch": continuity_epoch,
            "admission_epoch": admission_epoch,
            "execution_model_version": EXECUTION_MODEL_VERSION,
            "execution_model_limited": True,
            "random_seed": None,
            "stochastic_config_hash": None,
            "input_catalog_hash": None,
            "semantic_evidence_hash": None,
            "capture_configuration": capture_configuration,
            "subscription_policy": subscription_policy,
            "trial_ledger_id": trial_ledger_id,
            "adaptivity_state": "LEGACY_INCOMPLETE_CONSERVATIVE",
            "private_api": False,
            "exchange_write": False,
            "real_exec_client_registered": False,
        }
        digest = sha256_hex(_MANIFEST_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "manifest_hash": digest})


class SourceEvent(BaseModel):
    """Provider-normalized event before project causal admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: Sha256Hex
    expression_id: OpaqueId
    provider_id: Literal["NAUTILUS_HYPERLIQUID"] = "NAUTILUS_HYPERLIQUID"
    instrument_id: str = Field(min_length=3, max_length=160)
    data_kind: DataKind
    source_event_id: str = Field(min_length=1, max_length=200)
    native_trade_id: str | None = Field(default=None, max_length=200)
    provider_aggressor_side: str | None = Field(default=None, max_length=40)
    event_context: str = Field(min_length=1, max_length=200)
    ts_event: int = Field(ge=1)
    ts_init: int = Field(ge=1)
    true_network_receive_ts: int | None = Field(default=None, ge=1)
    payload: dict[str, object]
    payload_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"payload_hash"})

    @model_validator(mode="after")
    def validate_source(self) -> SourceEvent:
        if self.data_kind is DataKind.TRADE and (
            self.native_trade_id is None or self.provider_aggressor_side is None
        ):
            raise ValueError("TradeTick identity requires native trade_id and aggressor side")
        if self.data_kind is not DataKind.TRADE and (
            self.native_trade_id is not None or self.provider_aggressor_side is not None
        ):
            raise ValueError("non-trade evidence cannot carry TradeTick identity")
        expected = sha256_hex(_SOURCE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.payload_hash, expected):
            raise ValueError("payload_hash does not bind the source event")
        return self

    @classmethod
    def create(cls, **values: Any) -> SourceEvent:
        digest = sha256_hex(_SOURCE_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "payload_hash": digest})

    @property
    def replay_identity(self) -> str:
        if self.data_kind is DataKind.TRADE:
            identity = {
                "market_id": self.market_id,
                "expression_id": self.expression_id,
                "instrument_id": self.instrument_id,
                "native_trade_id": self.native_trade_id,
                "provider_aggressor_side": self.provider_aggressor_side,
                "event_context": self.event_context,
            }
        else:
            identity = {
                "market_id": self.market_id,
                "expression_id": self.expression_id,
                "instrument_id": self.instrument_id,
                "data_kind": self.data_kind,
                "source_event_id": self.source_event_id,
                "event_context": self.event_context,
            }
        return sha256_hex(_SOURCE_DOMAIN + canonical_json_bytes(identity))


class AdmittedEvent(BaseModel):
    """Stable admission identity/order; ordering never changes after admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["E4_CAPTURE_V1"] = CAPTURE_SCHEMA_VERSION
    process_epoch: OpaqueId
    continuity_epoch: OpaqueId
    admission_epoch: OpaqueId
    admission_ordinal: int = Field(ge=1)
    admission_ts: int = Field(ge=1)
    source_identity: Sha256Hex
    out_of_order: bool
    continuity_state: EvidenceState
    source: SourceEvent
    admission_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"admission_hash"})

    @model_validator(mode="after")
    def validate_admission(self) -> AdmittedEvent:
        if self.source_identity != self.source.replay_identity:
            raise ValueError("source identity does not bind replay context")
        if self.admission_ts < self.source.ts_init:
            raise ValueError("admission cannot precede adapter initialization")
        expected = sha256_hex(_ADMISSION_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.admission_hash, expected):
            raise ValueError("admission_hash does not bind causal order")
        return self

    @classmethod
    def create(cls, **values: Any) -> AdmittedEvent:
        digest = sha256_hex(_ADMISSION_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "admission_hash": digest})


class LifecycleRecord(BaseModel):
    """Portable state fact for Opportunity through terminal Exit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["E4_CAPTURE_V1"] = CAPTURE_SCHEMA_VERSION
    run_id: OpaqueId
    object_id: OpaqueId
    parent_id: OpaqueId | None = None
    package_id: OpaqueId
    market_id: Sha256Hex
    expression_id: OpaqueId
    kind: LifecycleKind
    status: LifecycleStatus
    state_ts: int = Field(ge=1)
    reason_codes: tuple[str, ...]
    decision_state: DecisionState | None = None
    approval_timing_mode: ApprovalTimingMode | None = None
    approval_provenance: ApprovalProvenance = ApprovalProvenance.NOT_APPLICABLE
    expiry_ts: int | None = Field(default=None, ge=1)
    supersedes_id: OpaqueId | None = None
    last_admission_ordinal: int = Field(ge=0)
    evidence_state: EvidenceState
    record_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"record_hash"})

    @model_validator(mode="after")
    def validate_record(self) -> LifecycleRecord:
        if self.approval_provenance is ApprovalProvenance.OBSERVED:
            raise ValueError("E4 Capture cannot claim observed Human approval")
        if self.kind is LifecycleKind.ARMED and self.approval_timing_mode is None:
            raise ValueError("ARMED identity requires approval timing mode")
        expected = sha256_hex(_LIFECYCLE_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if not hmac.compare_digest(self.record_hash, expected):
            raise ValueError("record_hash does not bind lifecycle fact")
        return self

    @classmethod
    def create(cls, **values: Any) -> LifecycleRecord:
        digest = sha256_hex(_LIFECYCLE_DOMAIN + canonical_json_bytes(values))
        return cls.model_validate({**values, "record_hash": digest})


class TailStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package_id: OpaqueId
    terminal_ts: int | None = Field(default=None, ge=1)
    micro_deadline_ts: int | None = Field(default=None, ge=1)
    context_deadline_ts: int | None = Field(default=None, ge=1)
    micro_phase: TailPhase = TailPhase.NOT_STARTED
    context_phase: TailPhase = TailPhase.NOT_STARTED
    evidence_state: EvidenceState = EvidenceState.INCOMPLETE
    reason_codes: tuple[str, ...] = ()


class GuardInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spread_bps: NonNegativeFiniteDecimal
    all_in_friction_bps: NonNegativeFiniteDecimal
    remaining_room_bps: PositiveFiniteDecimal
    minimum_room_to_cost: PositiveFiniteDecimal
    bbo_state_valid: bool
    data_evaluable: bool
    intended_notional: PositiveFiniteDecimal
    top_level_notional: NonNegativeFiniteDecimal
    guard_config_version: VersionId


class GuardResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: GuardDecision
    reason_codes: tuple[str, ...]
    inputs: GuardInputs
    venue_submitted: Literal[False] = False
    not_submitted: Literal[True] = True


class ExecutionChain(BaseModel):
    """Raw D1 causal chain; it deliberately makes no promotion-grade fill claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    package_id: OpaqueId
    armed_ts: int | None = Field(default=None, ge=1)
    activation_ts: int = Field(ge=1)
    activation_market_state_id: Sha256Hex
    human_approval_ts: int | None = Field(default=None, ge=1)
    approval_provenance: ApprovalProvenance
    guard_eval_ts: int = Field(ge=1)
    guard_result: GuardResult
    order_submit_intent_ts: int | None = Field(default=None, ge=1)
    hypothetical_order_active_ts: int | None = Field(default=None, ge=1)
    active_market_state_id: Sha256Hex | None = None
    fill_market_state_ts: int | None = Field(default=None, ge=1)
    order_primitive: Literal["MARKETABLE", "PASSIVE", "NOT_APPLICABLE"]
    queue_model_supported: bool = False
    modeled_fill_state: Literal["FILLED", "NONFILL", "NOT_MODELED"]
    modeled_fill_ts: int | None = Field(default=None, ge=1)
    modeled_fill_price: PositiveFiniteDecimal | None = None
    modeled_fill_vwap: PositiveFiniteDecimal | None = None
    modeled_fill_qty: PositiveFiniteDecimal | None = None
    fee_state_id: str | None = None
    funding_state_id: str | None = None
    execution_model_version: Literal["E4_PHASE_A_MARKETABLE_L1_V1"]
    execution_model_limited: bool
    venue_submitted: Literal[False] = False
    not_submitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_chain(self) -> ExecutionChain:
        if self.approval_provenance is ApprovalProvenance.OBSERVED:
            raise ValueError("E4 Capture cannot claim observed Human approval")
        if self.guard_result.decision is GuardDecision.NO_SUBMIT:
            if any(
                item is not None
                for item in (
                    self.order_submit_intent_ts,
                    self.hypothetical_order_active_ts,
                    self.fill_market_state_ts,
                    self.modeled_fill_ts,
                )
            ) or self.modeled_fill_state != "NOT_MODELED":
                raise ValueError("NO_SUBMIT is terminal and cannot become an Attempt/fill")
            return self
        if (
            self.order_primitive == "PASSIVE"
            and self.modeled_fill_state == "FILLED"
            and not self.queue_model_supported
        ):
            raise ValueError("passive touch cannot imply fill without queue evidence")
        timeline = (
            self.activation_ts,
            self.guard_eval_ts,
            self.order_submit_intent_ts,
            self.hypothetical_order_active_ts,
            self.fill_market_state_ts,
            self.modeled_fill_ts,
        )
        present = tuple(item for item in timeline if item is not None)
        if present != tuple(sorted(present)):
            raise ValueError("execution timestamps are not causal")
        if self.modeled_fill_state == "FILLED" and any(
            item is None
            for item in (
                self.hypothetical_order_active_ts,
                self.active_market_state_id,
                self.fill_market_state_ts,
                self.modeled_fill_ts,
                self.modeled_fill_price,
                self.modeled_fill_vwap,
                self.modeled_fill_qty,
            )
        ):
            raise ValueError("modeled fill is missing its raw causal chain")
        return self


class StopChain(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    package_id: OpaqueId
    stop_decision_id: OpaqueId
    stop_reference_id: Sha256Hex
    trigger_id: Sha256Hex
    trigger_ts: int = Field(ge=1)
    hypothetical_active_ts: int = Field(ge=1)
    executable_market_state_id: Sha256Hex
    fill_market_state_ts: int | None = Field(default=None, ge=1)
    modeled_fill_state: Literal["FILLED", "NONFILL", "NOT_MODELED"]
    modeled_fill_ts: int | None = Field(default=None, ge=1)
    modeled_fill_price: PositiveFiniteDecimal | None = None
    modeled_fill_vwap: PositiveFiniteDecimal | None = None
    execution_model_version: Literal["E4_PHASE_A_MARKETABLE_L1_V1"]
    collar_config_version: VersionId
    execution_model_limited: bool
    venue_submitted: Literal[False] = False
    not_submitted: Literal[True] = True

    @model_validator(mode="after")
    def validate_stop(self) -> StopChain:
        if self.hypothetical_active_ts < self.trigger_ts:
            raise ValueError("stop cannot become active before its causal trigger")
        if self.fill_market_state_ts is not None and (
            self.fill_market_state_ts < self.hypothetical_active_ts
        ):
            raise ValueError("stop fill state cannot precede order-active time")
        return self


class ZeroWriteProof(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    real_exec_client_registered: Literal[False] = False
    signing: Literal[False] = False
    private_api: Literal[False] = False
    exchange_write: Literal[False] = False
    venue_submitted: Literal[False] = False
    not_submitted: Literal[True] = True


def runtime_identity() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": f"{platform.system()}-{platform.machine()}",
    }


def strategy_history_state(finalized_5m_bars: int) -> EvidenceState:
    """Raw capture is allowed early; current Strategy evidence is not."""
    if finalized_5m_bars < 0:
        raise ValueError("finalized bar count cannot be negative")
    return (
        EvidenceState.COMPLETE
        if finalized_5m_bars >= WARMUP_5M_BARS
        else EvidenceState.NOT_EVALUABLE
    )


def historical_pit_claim_state(snapshot: PitUniverseSnapshot) -> EvidenceState:
    """Unknown prospective metadata never becomes fabricated historical state."""
    return (
        EvidenceState.COMPLETE
        if all(item.listing_state is not None for item in snapshot.expressions)
        else EvidenceState.NOT_EVALUABLE
    )
