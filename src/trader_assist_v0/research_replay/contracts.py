"""Versioned research identities; raw evidence and execution authority stay upstream."""

from __future__ import annotations

from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from functools import wraps
from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    GitCommitOid,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)
from trader_assist_v0.research_data.contracts import BoundRecord, FrozenModel, SourceMode

Clock = Literal["EVENT", "RECEIVE", "OBSERVED", "INIT"]
Availability = Literal[
    "AVAILABLE",
    "WARMUP_INCOMPLETE",
    "MISSING_SOURCE",
    "STALE",
    "GAPPED",
    "CONTINUITY_UNKNOWN",
    "CLOCK_SKEW",
    "MAPPING_UNAVAILABLE",
    "INVALID_EVIDENCE",
    "NOT_APPLICABLE",
    "DEPTH_UNAVAILABLE",
    "AMBIGUOUS",
]
Family = Literal["BBO_TRADES", "DEPTH10_OR_L2", "CROSS_VENUE", "PATH"]
Decision = Literal[
    "TAKE",
    "WAIT",
    "PASS",
    "BLOCKED",
    "NOT_EVALUABLE",
    "NONACTIVATION",
    "NO_SUBMIT",
    "NONFILL",
]


def decimal80[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    @wraps(function)
    def bound(*args: P.args, **kwargs: P.kwargs) -> R:
        with localcontext() as context:
            context.prec = 80
            context.rounding = ROUND_HALF_EVEN
            return function(*args, **kwargs)

    return bound


def digest(domain: str, payload: object) -> str:
    return sha256_hex(domain.encode() + b"\0" + canonical_json_bytes(payload))


def wire(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("nonfinite research value")
    with localcontext() as context:
        context.prec = 80
        return format(value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN), "f")


class EvidenceRef(BoundRecord):
    owner: Literal["HL_E4", "EXTERNAL_REFERENCE"]
    source_hash: Sha256Hex
    dataset_hash: Sha256Hex
    mapping_hash: Sha256Hex
    interval_hash: Sha256Hex
    registry_hash: Sha256Hex
    provider: str = Field(min_length=1)
    instrument: str = Field(min_length=1)
    expression: str = Field(min_length=1)
    price_unit: str = Field(min_length=1)
    size_unit: str = Field(min_length=1)
    source_mode: SourceMode
    source_tier: Literal["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
    exposure_state: str
    capability_hash: Sha256Hex | None = None
    rights_hash: Sha256Hex | None = None
    source_locator: str = Field(min_length=1)
    valid_from: int = Field(gt=0)
    valid_to: int = Field(gt=0)
    mapping_known_at: int = Field(gt=0)
    mapping_recorded_at: int = Field(gt=0)
    coverage_start: int = Field(gt=0)
    coverage_end: int = Field(gt=0)

    @model_validator(mode="after")
    def authority(self) -> Self:
        if (self.owner == "HL_E4") != (self.provider == "NAUTILUS_HYPERLIQUID"):
            raise ValueError("external reference cannot acquire Hyperliquid E4 ownership")
        if self.valid_from >= self.valid_to or self.coverage_start >= self.coverage_end:
            raise ValueError("invalid evidence validity/coverage interval")
        return self


class Observation(BoundRecord):
    """Disposable research projection, never accepted as an E4 market event."""

    evidence: EvidenceRef
    kind: Literal["BBO", "TRADE", "BAR", "CONTEXT", "DEPTH"]
    ts_event: int = Field(gt=0)
    known_at: int = Field(gt=0)
    ts_init: int | None = Field(default=None, gt=0)
    ts_receive: int | None = Field(default=None, gt=0)
    ordinal: int = Field(ge=0)
    continuity_epoch: str = Field(min_length=1)
    quality: tuple[str, ...]
    values: tuple[tuple[str, str], ...]
    bar_end: int | None = Field(default=None, gt=0)
    receive_provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if self.evidence.exposure_state not in {"SACRIFICIAL", "CONTAMINATED"}:
            raise PermissionError("non-pipeline evidence forbidden in research projection")
        if len(dict(self.values)) != len(self.values):
            raise ValueError("duplicate observation value")
        if self.kind == "BAR" and self.bar_end is None:
            raise ValueError("bar end/finality required")
        if self.ts_receive is None and self.receive_provenance != "NOT_EXPOSED":
            raise ValueError("receive provenance cannot invent a timestamp")
        return self

    def number(self, key: str) -> Decimal:
        result = Decimal(dict(self.values)[key])
        if not result.is_finite():
            raise ValueError("nonfinite raw projection")
        return result

    def clock(self, variant: Clock) -> int | None:
        return {
            "EVENT": self.ts_event,
            "RECEIVE": self.ts_receive,
            "OBSERVED": self.known_at,
            "INIT": self.ts_init,
        }[variant]


class FeatureSpec(BoundRecord):
    name: str = Field(min_length=1)
    family: Family
    algorithm: str = Field(min_length=1)
    implementation: str = Field(min_length=1)
    parameters: tuple[tuple[str, str], ...]
    required_kinds: tuple[str, ...] = Field(min_length=1)
    clock: Clock
    window_ns: int = Field(gt=0)
    warmup_ns: int = Field(ge=0)
    stale_ns: int = Field(gt=0)
    skew_ns: int = Field(ge=0)
    unit: str = Field(min_length=1)
    rounding: Literal["DECIMAL80_HALF_EVEN_12"] = "DECIMAL80_HALF_EVEN_12"
    mapping_policy: Literal["ACCEPTED_PIT_NO_BACKFILL"] = "ACCEPTED_PIT_NO_BACKFILL"
    availability_claim: Literal["ORIGINAL_RETAINED", "RETROSPECTIVE_EVENT_TIME"] = (
        "ORIGINAL_RETAINED"
    )

    @model_validator(mode="after")
    def unique_parameters(self) -> Self:
        if tuple(sorted(self.parameters)) != self.parameters or len(dict(self.parameters)) != len(
            self.parameters
        ):
            raise ValueError("parameters must be sorted and unique")
        return self


class FeatureObservation(BoundRecord):
    spec_hash: Sha256Hex
    event_cutoff: int = Field(gt=0)
    knowledge_cutoff: int = Field(gt=0)
    input_hashes: tuple[Sha256Hex, ...]
    mapping_hashes: tuple[Sha256Hex, ...]
    source_modes: tuple[SourceMode, ...]
    values: tuple[tuple[str, str], ...]
    status: Availability
    reasons: tuple[str, ...]
    claim: Literal["ORIGINAL_AVAILABILITY", "RETROSPECTIVE_EVENT_TIME"]
    family: Family
    expression: str
    unit: str
    clock: Clock
    coverage: tuple[int, int] | None
    ancestor_features: tuple[Sha256Hex, ...] = ()

    @model_validator(mode="after")
    def explicit_state(self) -> Self:
        if self.status != "AVAILABLE" and (self.values or not self.reasons):
            raise ValueError("unavailable feature requires reasons and no numeric values")
        if len(dict(self.values)) != len(self.values):
            raise ValueError("duplicate feature value")
        return self


class Opportunity(BoundRecord):
    opportunity_id: Sha256Hex
    market_event_id: str = Field(min_length=1)
    thesis_id: str = Field(min_length=1)
    market_id: str = Field(min_length=1)
    setup: Literal["SWEEP_RECLAIM", "BREAKOUT_RETEST", "RANGE_EDGE_REJECTION"]
    mode: str
    side: Literal["LONG", "SHORT"]
    decision_ns: int = Field(gt=0)
    knowledge_ns: int = Field(gt=0)
    invalidation_ns: int | None = None
    expiry_ns: int = Field(gt=0)
    entry: FiniteDecimal
    stop: FiniteDecimal
    target: FiniteDecimal
    registry_hash: Sha256Hex
    strategy_hash: Sha256Hex
    parameter_hash: Sha256Hex
    prefix_hashes: tuple[Sha256Hex, ...]
    scanner_id: str | None = None
    evaluation_id: str | None = None
    formal_signal_id: str | None = None
    disposition_id: str | None = None
    absence_reason: str | None = None
    cluster_id: str = Field(min_length=1)
    regime: str = Field(min_length=1)
    domain_hashes: tuple[Sha256Hex, ...] = ()

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.expiry_ns <= self.decision_ns or self.entry <= 0:
            raise ValueError("invalid opportunity window/entry")
        if self.setup == "BREAKOUT_RETEST" and self.mode not in {"MICRO_FAST", "STANDARD"}:
            raise ValueError("unauthorized breakout mode")
        if self.formal_signal_id is None and not self.absence_reason:
            raise ValueError("missing FormalSignal must be explained")
        if self.side == "LONG" and not self.stop < self.entry < self.target:
            raise ValueError("invalid long barriers")
        if self.side == "SHORT" and not self.target < self.entry < self.stop:
            raise ValueError("invalid short barriers")
        return self


class CostModel(BoundRecord):
    maker_bps: FiniteDecimal = Field(ge=0)
    taker_bps: FiniteDecimal = Field(ge=0)
    slippage_bps: FiniteDecimal = Field(ge=0)
    additional_cost_bps: FiniteDecimal = Field(default=Decimal(0), ge=0)
    delay_ns: int = Field(ge=0)
    quote_age_ns: int = Field(gt=0)
    size: FiniteDecimal = Field(gt=0)
    fill_model_hash: Sha256Hex
    fee_profile: str = Field(min_length=1)
    funding_profile: str = Field(min_length=1)
    passive_touch_equals_fill: Literal[False] = False
    trigger_equals_fill: Literal[False] = False


class ResearchRunSpec(BoundRecord):
    package: Literal["CAUSAL_RESEARCH_DERIVATION_STRATEGY_REPLAY_FOUNDATION_1"]
    base: GitCommitOid
    release: GitCommitOid
    runtime: str = Field(min_length=1)
    strategy_hash: Sha256Hex
    dataset_hashes: tuple[Sha256Hex, ...] = Field(min_length=1)
    feature_hashes: tuple[Sha256Hex, ...]
    policy_hashes: tuple[Sha256Hex, ...] = Field(min_length=1, max_length=64)
    roster_hash: Sha256Hex
    cost: CostModel
    horizon_ns: int = Field(gt=0)
    max_observations: int = Field(gt=0, le=100_000)
    max_candidates: int = Field(gt=0, le=64)
    trial_ledger_hash: Sha256Hex
    block_plan_hash: Sha256Hex
    visibility_hash: Sha256Hex
    correlation_method: str = Field(min_length=1)
    seed: int
    claim: Literal["PIPELINE_CORRECTNESS_ONLY"] = "PIPELINE_CORRECTNESS_ONLY"
    ambiguity: Literal["CONSERVATIVE_STOP_FIRST"] = "CONSERVATIVE_STOP_FIRST"
    consumption: Literal["REPLAY"] = "REPLAY"


class DecisionSnapshot(BoundRecord):
    opportunity_hash: Sha256Hex
    policy_hash: Sha256Hex
    decision: Decision
    reasons: tuple[str, ...] = Field(min_length=1)
    decision_ns: int = Field(gt=0)
    prefix_hashes: tuple[Sha256Hex, ...]
    feature_hashes: tuple[Sha256Hex, ...]
    cost_hash: Sha256Hex
    horizon_end: int = Field(gt=0)


class Fill(FrozenModel):
    """Only native simulated fill evidence; never a private/account import."""

    ts: int = Field(gt=0)
    price: FiniteDecimal = Field(gt=0)
    size: FiniteDecimal = Field(gt=0)
    direction: Literal["BUY", "SELL"]
    fee: FiniteDecimal = Field(ge=0)
    source_hash: Sha256Hex
    mode: Literal["NATIVE_SIMULATED"] = "NATIVE_SIMULATED"


class CashFlow(FrozenModel):
    ts: int = Field(gt=0)
    amount: FiniteDecimal
    source_hash: Sha256Hex
    kind: Literal["FUNDING", "ADDITIONAL_COST"]
    input_hashes: tuple[Sha256Hex, ...] = ()


class Attempt(BoundRecord):
    thesis_id: str
    policy_hash: Sha256Hex
    index: int = Field(ge=1)
    trigger_ns: int = Field(gt=0)
    fill: Fill | None
    exit_fill: Fill | None
    state: Literal["PROBE_OPEN", "SCRATCHED", "WINNER_CONFIRMED", "COMPLETE", "NONFILL"]
    fresh_condition_hash: Sha256Hex | None
    reason: str = Field(min_length=1)
    winner_confirmed_ns: int | None = None

    @model_validator(mode="after")
    def timing(self) -> Self:
        if self.fill and self.fill.ts < self.trigger_ns:
            raise ValueError("fill predates trigger")
        if self.exit_fill and (not self.fill or self.exit_fill.ts < self.fill.ts):
            raise ValueError("exit predates fill")
        if self.state == "NONFILL" and self.fill is not None:
            raise ValueError("nonfill carries no fill")
        return self


class PathResult(BoundRecord):
    snapshot_hash: Sha256Hex
    status: Literal["RECONSTRUCTABLE", "PARTIAL", "NOT_RECONSTRUCTABLE"]
    reasons: tuple[str, ...]
    input_hashes: tuple[Sha256Hex, ...]
    market_mfe: FiniteDecimal | None
    market_mae: FiniteDecimal | None
    exec_mfe: FiniteDecimal | None
    exec_mae: FiniteDecimal | None
    first_favorable_ns: int | None
    first_adverse_ns: int | None
    time_to_mfe_ns: int | None
    time_to_mae_ns: int | None
    recovery_ns: int | None
    same_bar_ambiguous: bool
    primary: Literal["STOP_FIRST", "TARGET_FIRST", "NO_HIT", "UNKNOWN"]
    censored: bool
    basis: Literal["TRIGGER", "FILL"]
    bounds_only: bool
    first_stop_ns: int | None
    first_target_ns: int | None


class PropagationLabel(BoundRecord):
    """Matured outcome; deliberately not a FeatureObservation or decision input."""

    spec_hash: Sha256Hex
    impulse_hash: Sha256Hex
    baseline_hash: Sha256Hex | None
    response_hash: Sha256Hex | None
    impulse_ns: int
    horizon_end: int
    response_ns: int | None
    elapsed_ns: int | None
    source_impulse: FiniteDecimal | None
    response_bps: FiniteDecimal | None
    clock: Clock
    state: Literal["RESPONSE", "NO_RESPONSE", "CENSORED", "AMBIGUOUS", "UNAVAILABLE"]
    reason: str
