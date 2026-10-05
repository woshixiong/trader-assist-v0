"""Offline external mechanism identities; none confer native execution authority."""

from __future__ import annotations

import sys
from typing import Literal, Self, TypeVar

from pydantic import BaseModel, Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal, GitCommitOid, Sha256Hex
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest
from trader_assist_v0.research_data.admission import AdmissionPolicy
from trader_assist_v0.research_data.contracts import (
    BoundRecord,
    DatasetManifest,
    ProviderCapability,
)
from trader_assist_v0.research_data.mapping import ReferenceMappingSnapshot
from trader_assist_v0.research_inventory.contracts import DatasetInventoryManifest

from .contracts import CostModel, Decision, digest
from .dev_contracts import DevAccessAuthority, DevObservation
from .dev_lifecycle import DevTrialLedger, DevVisibilityPolicy
from .lifecycle import BlockPlan
from .policies import BASELINES, PolicySpec

CHAMPION = "CURRENT_THREE_SETUP_CHAMPION"
CODES = (CHAMPION, *BASELINES)
Family = Literal["SWEEP_RECLAIM", "BREAKOUT_RETEST", "RANGE_EDGE_REJECTION"]
Mode = Literal["MICRO_FAST", "STANDARD", "UNCONFIRMED", "NOT_APPLICABLE"]
Side = Literal["LONG", "SHORT"]
_T = TypeVar("_T", bound=BaseModel)


def checked(value: _T, cls: type[_T]) -> _T:
    """Reject concrete-type and construction/copy bypasses, including nested subclasses."""

    def walk(v: object) -> None:
        if isinstance(v, BaseModel):
            if (
                type(v).__name__ not in _MODEL_NAMES
                or getattr(sys.modules[type(v).__module__], type(v).__name__, None) is not type(v)
                or not type(v).__module__.startswith("trader_assist_v0.")
                or set(v.__dict__) != set(type(v).model_fields)
            ):
                raise TypeError("unrecognized concrete mechanism contract")
            if v.model_extra:
                raise ValueError("extra mechanism fields")
            for child in v.__dict__.values():
                walk(child)
        elif isinstance(v, tuple | list):
            for child in v:
                walk(child)

    if type(value) is not cls:
        raise TypeError("exact concrete contract required")
    walk(value)
    return cls.model_validate_json(value.model_dump_json())


class MechanismMarket(BoundRecord):
    instrument: str = Field(min_length=1)
    expression: str = Field(min_length=1)
    minimum_tick: FiniteDecimal = Field(gt=0)
    cluster: str = Field(min_length=1)
    regime: str = Field(min_length=1)


class MechanismConfig(BoundRecord):
    model: Literal["BAR_NEXT_OPEN_STOP_FIRST_V1"]
    cost: CostModel
    resolution_ns: Literal[300_000_000_000]
    horizon_ns: int = Field(gt=0)
    decision_start_ns: int = Field(gt=0)
    expiry_ns: int = Field(gt=0)
    spread_bps: FiniteDecimal = Field(ge=0, lt=10000)
    funding_applicable: bool
    funding_bps: FiniteDecimal | None
    funding_interval_ns: int = Field(gt=0)
    funding_anchor_ns: int = Field(ge=0)
    scanner_liquidity_healthy: bool
    scanner_assumption_ref: str = Field(min_length=1)
    donchian_bars: int = Field(ge=2, le=10000)
    baseline_stop: Literal["SIGNAL_EXTREME_PLUS_TICK"]
    baseline_target_r: FiniteDecimal = Field(gt=0)
    original_risk_cash: FiniteDecimal = Field(gt=0)
    capital_cash: FiniteDecimal = Field(gt=0)
    cluster_window_ns: int = Field(gt=0)
    episode_rule: Literal["CAUSAL_FAMILY_SIDE_BOUNDARY_NONOVERLAP_V1"]
    regime_method: str = Field(min_length=1)
    markets: tuple[MechanismMarket, ...] = Field(min_length=1)
    pit_qa_hash: Sha256Hex | None
    pit_qa_ref: str | None

    @model_validator(mode="after")
    def assumptions(self) -> Self:
        if self.cost.size != 1:
            raise ValueError("CostModel.size must be unit placeholder; original risk owns sizing")
        if (
            self.horizon_ns % self.resolution_ns
            or self.expiry_ns > self.horizon_ns
            or self.decision_start_ns % self.resolution_ns
        ):
            raise ValueError("whole-bar horizon and bounded expiry required")
        if self.original_risk_cash > self.capital_cash:
            raise ValueError("risk exceeds matched capital")
        if not self.funding_applicable and self.funding_bps is not None:
            raise ValueError("nonapplicable funding cannot carry a rate")
        if len({m.expression for m in self.markets}) != len(self.markets):
            raise ValueError("one declared source per external expression")
        if len({m.instrument for m in self.markets}) != len(self.markets):
            raise ValueError("duplicate universe instrument")
        return self

    @property
    def risk_hash(self) -> str:
        return digest("MECHANISM_ORIGINAL_RISK_V1", (self.original_risk_cash, self.capital_cash))


class MechanismCandidate(BoundRecord):
    participation: PolicySpec
    config_hash: Sha256Hex
    risk_hash: Sha256Hex
    role: Literal["REFERENCE", "BASELINE"]

    @model_validator(mode="after")
    def g0_only(self) -> Self:
        p = self.participation
        if p.code not in CODES or p.family != ("CHAMPION" if p.code == CHAMPION else "BASELINE"):
            raise ValueError("frozen G0 participation only")
        if p.parameters or p.prerequisite is not None:
            raise ValueError("G0 has no participation optimization")
        if self.role != ("REFERENCE" if p.code == CHAMPION else "BASELINE"):
            raise ValueError("candidate role mismatch")
        return self


class MechanismSource(BoundRecord):
    dataset: DatasetManifest
    authority: DevAccessAuthority
    mapping: ReferenceMappingSnapshot
    capabilities: tuple[ProviderCapability, ...]
    policy: AdmissionPolicy
    registry_hash: Sha256Hex
    root: str = Field(min_length=1)
    path: str = Field(min_length=1)
    checksum: Sha256Hex


class MechanismRunSpec(BoundRecord):
    package: Literal["C_G0_EXTERNAL_MECHANISM_REPLAY_1"]
    stage: Literal["S1"]
    group: Literal["G0"]
    base: GitCommitOid
    code_commit: GitCommitOid
    code_tree: GitCommitOid
    manifest: StrategyPackageManifest
    strategy_hash: Sha256Hex
    dataset_hashes: tuple[Sha256Hex, ...]
    source_hashes: tuple[Sha256Hex, ...]
    candidate_hashes: tuple[Sha256Hex, ...]
    inventory_hash: Sha256Hex
    preregistration_hash: Sha256Hex
    ledger_hash: Sha256Hex
    block_hash: Sha256Hex
    visibility_hash: Sha256Hex
    config_hash: Sha256Hex
    registry_hash: Sha256Hex
    taxonomy_hash: Sha256Hex
    s0_preparation_hash: Sha256Hex
    dependency_lock_hash: Sha256Hex
    module_hashes: tuple[tuple[str, Sha256Hex], ...]
    runtime: str = Field(min_length=1)
    python_version: str = Field(min_length=1)
    os_arch: str = Field(min_length=1)
    max_observations: int = Field(gt=0, le=100000)
    max_events: int = Field(gt=0, le=10000)
    evidence_kind: Literal["SYNTHETIC_ENGINEERING", "RIGHTS_AUTHORIZED_DEV"]
    claim: Literal["MECHANISM_VALIDATION"] = "MECHANISM_VALIDATION"
    economics: Literal["SYNTHETIC_VENUE_OVERLAY"] = "SYNTHETIC_VENUE_OVERLAY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def source_code_identity(self) -> Self:
        expected = ("mechanism.py", "mechanism_contracts.py", "mechanism_harness.py")
        if tuple(k for k, _ in self.module_hashes) != expected:
            raise ValueError("exact sorted implementation source hashes required")
        if self.strategy_hash != self.manifest.manifest_hash:
            raise ValueError("Strategy hash must bind current package manifest")
        return self


class MechanismDecision(BoundRecord):
    code: str
    at: int = Field(gt=0)
    prefix_hashes: tuple[Sha256Hex, ...]
    participation: Decision
    reason: str
    mode: Mode
    entry_low: FiniteDecimal | None
    entry_high: FiniteDecimal | None
    chase: FiniteDecimal | None
    stop: FiniteDecimal | None
    target: FiniteDecimal | None
    owner_hash: Sha256Hex


class MechanismOpportunity(BoundRecord):
    market_event_id: str
    thesis_id: str
    expression: str
    dataset_hash: Sha256Hex
    family: Family
    mode: Mode
    side: Side
    cluster_id: str
    regime: str
    start_ns: int = Field(gt=0)
    expiry_ns: int = Field(gt=0)
    horizon_end: int = Field(gt=0)
    kernel_event: bool
    availability: Literal["AVAILABLE", "NOT_EVALUABLE"]
    reasons: tuple[str, ...]
    original_risk_cash: FiniteDecimal = Field(gt=0)
    risk_hash: Sha256Hex
    config_hash: Sha256Hex
    scan_hashes: tuple[Sha256Hex, ...]
    decisions: tuple[MechanismDecision, ...]

    @model_validator(mode="after")
    def prefix_timing(self) -> Self:
        if not self.start_ns < self.expiry_ns <= self.horizon_end:
            raise ValueError("invalid episode horizon")
        if self.family != "BREAKOUT_RETEST" and self.mode != "NOT_APPLICABLE":
            raise ValueError("non-breakout mode forbidden")
        if self.family == "BREAKOUT_RETEST" and self.mode == "NOT_APPLICABLE":
            raise ValueError("breakout stratum required")
        if any(d.at < self.start_ns or d.at >= self.expiry_ns for d in self.decisions):
            raise ValueError("decision outside causal episode")
        return self


class ModeledFill(BoundRecord):
    ts: int = Field(gt=0)
    price: FiniteDecimal = Field(gt=0)
    size: FiniteDecimal = Field(gt=0)
    direction: Literal["BUY", "SELL"]
    fee: FiniteDecimal = Field(ge=0)
    friction_cash: FiniteDecimal = Field(ge=0)
    source_hash: Sha256Hex
    model_hash: Sha256Hex
    mode: Literal["SYNTHETIC_VENUE_OVERLAY"] = "SYNTHETIC_VENUE_OVERLAY"


class MechanismPath(BoundRecord):
    status: Literal["COMPLETE", "INCOMPLETE"]
    input_hashes: tuple[Sha256Hex, ...]
    mfe: FiniteDecimal | None
    mae: FiniteDecimal | None
    first_stop_ns: int | None
    first_target_ns: int | None
    time_to_mfe_ns: int | None
    time_to_mae_ns: int | None
    recovery_ns: int | None
    ambiguous: bool
    reasons: tuple[str, ...]
    bounds_only: Literal[True] = True


class MechanismResult(BoundRecord):
    opportunity_hash: Sha256Hex
    candidate_hash: Sha256Hex
    code: str
    thesis_id: str
    cluster_id: str
    config_hash: Sha256Hex
    risk_hash: Sha256Hex
    original_risk_cash: FiniteDecimal
    decisions: tuple[MechanismDecision, ...]
    entry: ModeledFill | None
    exit: ModeledFill | None
    path: MechanismPath
    counterfactual_r: FiniteDecimal | None
    net_cash: FiniteDecimal | None
    net_r: FiniteDecimal | None
    funding_cash: FiniteDecimal | None
    additional_cash: FiniteDecimal
    terminal: Literal[
        "COMPLETE",
        "SUPPRESSED",
        "NO_SUBMIT",
        "NONFILL",
        "NOT_EVALUABLE",
        "UNFINISHED",
        "NOT_APPLICABLE",
    ]
    reasons: tuple[str, ...]
    economics: Literal["SYNTHETIC_VENUE_OVERLAY"] = "SYNTHETIC_VENUE_OVERLAY"

    @model_validator(mode="after")
    def economics_binding(self) -> Self:
        if self.original_risk_cash <= 0:
            raise ValueError("original risk must be positive")
        if (self.net_cash is None) != (self.net_r is None):
            raise ValueError("incomplete economics cannot acquire R")
        if self.net_cash is not None:
            from .contracts import wire

            if wire(self.net_cash / self.original_risk_cash) != wire(self.net_r):  # type: ignore[arg-type]
                raise ValueError("original risk denominator mismatch")
        if self.terminal in {"NOT_EVALUABLE", "UNFINISHED", "NOT_APPLICABLE"}:
            if self.net_cash is not None:
                raise ValueError("unknown/inapplicable economics must stay null")
        if self.entry and self.entry.model_hash != self.config_hash:
            raise ValueError("modeled fill config mismatch")
        if self.exit and (not self.entry or self.exit.ts < self.entry.ts):
            raise ValueError("exit predates modeled entry")
        return self


class MechanismPair(BoundRecord):
    opportunity_hash: Sha256Hex
    left_hash: Sha256Hex
    right_hash: Sha256Hex
    comparable: bool
    reason: str
    delta_r: FiniteDecimal | None
    delta_cash: FiniteDecimal | None


class MechanismMetrics(BoundRecord):
    cell: str
    code: str
    roster_count: int
    event_count: int
    thesis_count: int
    cluster_count: int
    incomplete_count: int
    participation: tuple[tuple[str, int], ...]
    after_cost_thesis_r: FiniteDecimal | None
    paired_delta_r: FiniteDecimal | None
    median_delta_r: FiniteDecimal | None
    drawdown_r: FiniteDecimal | None
    tail_loss_r: FiniteDecimal | None
    tail_mae_r: FiniteDecimal | None
    longest_losing_streak: int
    winner_concentration: FiniteDecimal | None
    cluster_concentration: FiniteDecimal | None
    coverage: FiniteDecimal
    unavailable_rate: FiniteDecimal
    cost_r: FiniteDecimal
    turnover_cash: FiniteDecimal
    fee_cash: FiniteDecimal
    friction_cash: FiniteDecimal
    funding_cash: FiniteDecimal | None
    additional_cash: FiniteDecimal
    per_leg_cost_cash: FiniteDecimal | None
    reentry_tax: Literal["NOT_APPLICABLE"] = "NOT_APPLICABLE"
    missed_count: int
    false_positive_count: int
    false_negative_count: int
    ambiguous_count: int
    comparable_count: int
    unmatched_count: int
    cluster_delta_lower: FiniteDecimal | None
    cluster_delta_upper: FiniteDecimal | None
    sufficient: bool
    coherent: bool
    uncertainty: Literal["DESCRIPTIVE_CLUSTER_RANGE_NO_INFERENTIAL_CLAIM"] = (
        "DESCRIPTIVE_CLUSTER_RANGE_NO_INFERENTIAL_CLAIM"
    )


class MechanismSummary(BoundRecord):
    metrics: tuple[MechanismMetrics, ...]
    missing_cells: tuple[str, ...]
    cohort_count: int
    unavailable_cohort_count: int
    event_count: int
    disposition: Literal[
        "KEEP_CURRENT", "RESEARCH_LEADER", "REJECT", "INSUFFICIENT", "MORE_EVIDENCE_REQUIRED"
    ]
    stop_broad_optimization: bool
    next_action: str
    performance_evidence: bool
    claim: Literal["MECHANISM_VALIDATION"] = "MECHANISM_VALIDATION"
    economics: Literal["SYNTHETIC_VENUE_OVERLAY"] = "SYNTHETIC_VENUE_OVERLAY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"


class MechanismBundle(BoundRecord):
    run: MechanismRunSpec
    config: MechanismConfig
    sources: tuple[MechanismSource, ...]
    inventory: DatasetInventoryManifest
    ledger: DevTrialLedger
    blocks: BlockPlan
    visibility: DevVisibilityPolicy
    candidates: tuple[MechanismCandidate, ...]
    observations: tuple[DevObservation, ...]
    roster: tuple[MechanismOpportunity, ...]
    results: tuple[MechanismResult, ...]
    pairs: tuple[MechanismPair, ...]
    summary: MechanismSummary
    as_of_ns: int
    artifacts: tuple[tuple[str, Sha256Hex], ...]
    fingerprint: Sha256Hex
    claim: Literal["MECHANISM_VALIDATION"] = "MECHANISM_VALIDATION"
    economics: Literal["SYNTHETIC_VENUE_OVERLAY"] = "SYNTHETIC_VENUE_OVERLAY"
    promotion: Literal["PROHIBITED"] = "PROHIBITED"

    @model_validator(mode="after")
    def complete_evidence(self) -> Self:
        from .mechanism_harness import authenticate_bundle

        authenticate_bundle(self)
        return self


def mechanism_fingerprint(payload: object) -> str:
    return digest("MECHANISM_EVIDENCE_BUNDLE_V1", payload)


# Closed input graph; nested upstream owners keep their concrete identities.
_MODEL_NAMES = {
    "MechanismMarket",
    "MechanismConfig",
    "MechanismCandidate",
    "MechanismSource",
    "MechanismRunSpec",
    "MechanismDecision",
    "MechanismOpportunity",
    "ModeledFill",
    "MechanismPath",
    "MechanismResult",
    "MechanismPair",
    "MechanismMetrics",
    "MechanismSummary",
    "MechanismBundle",
    "CostModel",
    "PolicySpec",
    "StrategyPackageManifest",
    "DatasetManifest",
    "SourceRightsProvenance",
    "DevAccessAuthority",
    "ReferenceMappingSnapshot",
    "ReferenceMappingInterval",
    "ProviderCapability",
    "AdmissionPolicy",
    "DatasetInventoryManifest",
    "InventoryAllocationSpec",
    "InventoryEntry",
    "AllocationItem",
    "DatasetBinding",
    "CutIdentity",
    "NonOutcomeInventoryFact",
    "DevPreregistration",
    "DevGates",
    "DevTrialLedger",
    "DevTrial",
    "DevCompletion",
    "DevReproduction",
    "BlockPlan",
    "Block",
    "DevVisibilityPolicy",
    "DevObservation",
    "EvidenceRef",
}
