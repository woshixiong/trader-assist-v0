from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

STATE_SCHEMA_VERSION: Final = "STATE_SCHEMA_V0"
MODEL_DEADLINE_SECONDS: Final = 3.0
L2_MAX_AGE_SECONDS: Final = 2.0
SNAPSHOT_TO_PUBLICATION_MAX_SECONDS: Final = 5.0
SIGNAL_MAX_AGE_SECONDS: Final = 15.0
ONE_MINUTE_CLOSED_MAX_AGE_SECONDS: Final = 90.0
FIVE_MINUTE_CLOSED_MAX_AGE_SECONDS: Final = 390.0
ACTIVE_CONTEXT_MAX_AGE_SECONDS: Final = 15.0
METADATA_MAX_AGE_SECONDS: Final = 24.0 * 60.0 * 60.0


class EntryAction(StrEnum):
    LONG_ENTRY = "LONG_ENTRY"
    SHORT_ENTRY = "SHORT_ENTRY"
    WAIT = "WAIT"
    PASS = "PASS"


class SetupFamily(StrEnum):
    SWEEP_RECLAIM = "SWEEP_RECLAIM"
    BREAKOUT_RETEST = "BREAKOUT_RETEST"
    RANGE_EDGE_REJECTION = "RANGE_EDGE_REJECTION"
    NONE = "NONE"


class SetupDirection(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class SetupState(StrEnum):
    READY_NOW = "READY_NOW"
    DEVELOPING = "DEVELOPING"
    FAILED_OR_INVALID = "FAILED_OR_INVALID"
    NONE = "NONE"


class BlockReason(StrEnum):
    L2_STALE = "L2_STALE"
    ONE_MINUTE_CANDLE_STALE = "ONE_MINUTE_CANDLE_STALE"
    GAP = "GAP"
    CONFLICT = "CONFLICT"
    DISCONNECTED = "DISCONNECTED"
    INVALID_FRAME = "INVALID_FRAME"
    NOT_READY = "NOT_READY"


class AggressorSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


def _finite_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _non_negative_ns(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True, slots=True)
class MarketIdentity:
    market: str
    provider: str
    instrument_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("market", self.market),
            ("provider", self.provider),
            ("instrument_id", self.instrument_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class BBO:
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    source_ts_ns: int
    admitted_ts_ns: int
    continuity_valid: bool

    def __post_init__(self) -> None:
        _finite_positive("bid_price", self.bid_price)
        _finite_positive("bid_size", self.bid_size)
        _finite_positive("ask_price", self.ask_price)
        _finite_positive("ask_size", self.ask_size)
        _non_negative_ns("source_ts_ns", self.source_ts_ns)
        _non_negative_ns("admitted_ts_ns", self.admitted_ts_ns)
        if self.bid_price >= self.ask_price:
            raise ValueError("BBO must be uncrossed: bid_price < ask_price")
        if self.admitted_ts_ns < self.source_ts_ns:
            raise ValueError("BBO admitted_ts_ns must be at or after source_ts_ns")

    @property
    def mid(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0

    @property
    def spread_bps(self) -> float:
        return (self.ask_price - self.bid_price) / self.mid * 10_000.0


@dataclass(frozen=True, slots=True)
class L2Level:
    price: float
    size: float

    def __post_init__(self) -> None:
        _finite_positive("price", self.price)
        _finite_positive("size", self.size)


@dataclass(frozen=True, slots=True)
class L2Snapshot:
    bids: tuple[L2Level, ...]
    asks: tuple[L2Level, ...]
    source_ts_ns: int
    admitted_ts_ns: int
    provenance: str

    def __post_init__(self) -> None:
        _non_negative_ns("source_ts_ns", self.source_ts_ns)
        _non_negative_ns("admitted_ts_ns", self.admitted_ts_ns)
        if self.admitted_ts_ns < self.source_ts_ns:
            raise ValueError("L2 admitted_ts_ns must be at or after source_ts_ns")
        if len(self.bids) != 5 or len(self.asks) != 5:
            raise ValueError("L2 snapshot must contain exactly five bid and five ask levels")
        if not self.provenance.strip():
            raise ValueError("L2 provenance must be non-empty")
        if any(self.bids[index].price <= self.bids[index + 1].price for index in range(4)):
            raise ValueError("L2 bids must be strictly descending")
        if any(self.asks[index].price >= self.asks[index + 1].price for index in range(4)):
            raise ValueError("L2 asks must be strictly ascending")
        if self.bids[0].price >= self.asks[0].price:
            raise ValueError("L2 snapshot must be uncrossed")


@dataclass(frozen=True, slots=True)
class PublicTrade:
    ts_ns: int
    price: float
    size: float
    aggressor_side: AggressorSide

    def __post_init__(self) -> None:
        _non_negative_ns("ts_ns", self.ts_ns)
        _finite_positive("price", self.price)
        _finite_positive("size", self.size)

    @property
    def notional(self) -> float:
        return self.price * self.size


@dataclass(frozen=True, slots=True)
class CompletedBar:
    interval_seconds: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_ts_ns: int
    completed: bool = True

    def __post_init__(self) -> None:
        if not self.completed:
            raise ValueError("bar must be completed")
        if self.interval_seconds not in (60, 300):
            raise ValueError("only completed 1m/5m bars are accepted by STATE_SCHEMA_V0")
        for name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _finite_positive(name, value)
        if not math.isfinite(self.volume) or self.volume < 0:
            raise ValueError("volume must be finite and non-negative")
        _non_negative_ns("close_ts_ns", self.close_ts_ns)
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("bar OHLC is internally inconsistent")
        if self.low > self.high:
            raise ValueError("bar low must be <= high")


@dataclass(frozen=True, slots=True)
class PublicationFreshnessResult:
    valid: bool
    age_seconds: float


def evaluate_snapshot_publication_freshness(
    *, snapshot_ready_ts_ns: int, publication_ts_ns: int
) -> PublicationFreshnessResult:
    _non_negative_ns("snapshot_ready_ts_ns", snapshot_ready_ts_ns)
    _non_negative_ns("publication_ts_ns", publication_ts_ns)
    age = (publication_ts_ns - snapshot_ready_ts_ns) / 1_000_000_000.0
    return PublicationFreshnessResult(
        valid=0.0 <= age <= SNAPSHOT_TO_PUBLICATION_MAX_SECONDS, age_seconds=age
    )


def signal_is_fresh(
    *, signal_publication_ts_ns: int, at_ts_ns: int, next_evaluation_ts_ns: int | None = None
) -> bool:
    _non_negative_ns("signal_publication_ts_ns", signal_publication_ts_ns)
    _non_negative_ns("at_ts_ns", at_ts_ns)
    if next_evaluation_ts_ns is not None:
        _non_negative_ns("next_evaluation_ts_ns", next_evaluation_ts_ns)
    if at_ts_ns < signal_publication_ts_ns:
        return False
    expiry_ns = signal_publication_ts_ns + int(SIGNAL_MAX_AGE_SECONDS * 1_000_000_000)
    if next_evaluation_ts_ns is not None:
        expiry_ns = min(expiry_ns, next_evaluation_ts_ns)
    return at_ts_ns <= expiry_ns


@dataclass(frozen=True, slots=True)
class FreshnessInputs:
    l2_source_ts_ns: int | None
    latest_1m_close_ts_ns: int | None
    latest_5m_close_ts_ns: int | None
    optional_active_context_ts_ns: int | None
    metadata_ts_ns: int | None
    bbo_value_ts_ns: int | None = None
    latest_trade_ts_ns: int | None = None
    connected: bool = True
    gap: bool = False
    conflict: bool = False
    invalid_frame: bool = False
    ready: bool = True


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    valid: bool
    reasons: tuple[BlockReason, ...]
    l2_age_seconds: float | None
    one_minute_age_seconds: float | None
    five_minute_age_seconds: float | None
    active_context_age_seconds: float | None
    metadata_age_seconds: float | None
    bbo_value_age_seconds: float | None
    latest_trade_age_seconds: float | None


def _age_seconds(now_ns: int, ts_ns: int | None) -> float | None:
    if ts_ns is None:
        return None
    return (now_ns - ts_ns) / 1_000_000_000.0


def evaluate_freshness(now_ns: int, inputs: FreshnessInputs) -> FreshnessResult:
    """Evaluate frozen P1 freshness budgets without transport/runtime side effects."""
    _non_negative_ns("now_ns", now_ns)
    ages = {
        "l2": _age_seconds(now_ns, inputs.l2_source_ts_ns),
        "one": _age_seconds(now_ns, inputs.latest_1m_close_ts_ns),
        "five": _age_seconds(now_ns, inputs.latest_5m_close_ts_ns),
        "active": _age_seconds(now_ns, inputs.optional_active_context_ts_ns),
        "metadata": _age_seconds(now_ns, inputs.metadata_ts_ns),
        "bbo": _age_seconds(now_ns, inputs.bbo_value_ts_ns),
        "trade": _age_seconds(now_ns, inputs.latest_trade_ts_ns),
    }
    reasons: list[BlockReason] = []
    if not inputs.connected:
        reasons.append(BlockReason.DISCONNECTED)
    if inputs.gap:
        reasons.append(BlockReason.GAP)
    if inputs.conflict:
        reasons.append(BlockReason.CONFLICT)
    if inputs.invalid_frame or any(age is not None and age < 0 for age in ages.values()):
        reasons.append(BlockReason.INVALID_FRAME)
    if not inputs.ready:
        reasons.append(BlockReason.NOT_READY)
    if ages["l2"] is None or ages["l2"] > L2_MAX_AGE_SECONDS:
        reasons.append(BlockReason.L2_STALE)
    if ages["one"] is None or ages["one"] > ONE_MINUTE_CLOSED_MAX_AGE_SECONDS:
        reasons.append(BlockReason.ONE_MINUTE_CANDLE_STALE)
    # The frozen reason vocabulary has no dedicated 5m/context/metadata stale code.
    if ages["five"] is None or ages["five"] > FIVE_MINUTE_CLOSED_MAX_AGE_SECONDS:
        reasons.append(BlockReason.NOT_READY)
    if ages["active"] is not None and ages["active"] > ACTIVE_CONTEXT_MAX_AGE_SECONDS:
        reasons.append(BlockReason.NOT_READY)
    if ages["metadata"] is None or ages["metadata"] > METADATA_MAX_AGE_SECONDS:
        reasons.append(BlockReason.NOT_READY)

    deduped = tuple(dict.fromkeys(reasons))
    return FreshnessResult(
        valid=not deduped,
        reasons=deduped,
        l2_age_seconds=ages["l2"],
        one_minute_age_seconds=ages["one"],
        five_minute_age_seconds=ages["five"],
        active_context_age_seconds=ages["active"],
        metadata_age_seconds=ages["metadata"],
        bbo_value_age_seconds=ages["bbo"],
        latest_trade_age_seconds=ages["trade"],
    )

class DecisionArm(StrEnum):
    MODEL_NATIVE = "MODEL_NATIVE"
    STRATEGY_INFORMED = "STRATEGY_INFORMED"


class ModelInvocationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INPUT_INVALID = "INPUT_INVALID"
    ADAPTER_ERROR = "ADAPTER_ERROR"


def _non_empty(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class ModelTarget:
    model_target_id: str
    provider: str
    requested_model_id: str
    requested_checkpoint_or_revision: str | None
    adapter_id: str
    adapter_version: str

    def __post_init__(self) -> None:
        for name, value in (
            ("model_target_id", self.model_target_id),
            ("provider", self.provider),
            ("requested_model_id", self.requested_model_id),
            ("adapter_id", self.adapter_id),
            ("adapter_version", self.adapter_version),
        ):
            _non_empty(name, value)
        if self.requested_checkpoint_or_revision is not None:
            _non_empty("requested_checkpoint_or_revision", self.requested_checkpoint_or_revision)


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider: str
    requested_model_id: str
    returned_model_or_checkpoint_id: str | None = None
    checkpoint_revision_or_digest: str | None = None
    sdk_package: str | None = None
    sdk_version: str | None = None
    inference_runtime: str | None = None
    inference_runtime_version: str | None = None
    calibration_config_id: str | None = None
    inference_device: str | None = None

    def __post_init__(self) -> None:
        _non_empty("provider", self.provider)
        _non_empty("requested_model_id", self.requested_model_id)
        for name in (
            "returned_model_or_checkpoint_id",
            "checkpoint_revision_or_digest",
            "sdk_package",
            "sdk_version",
            "inference_runtime",
            "inference_runtime_version",
            "calibration_config_id",
            "inference_device",
        ):
            value = getattr(self, name)
            if value is not None:
                _non_empty(name, value)


@dataclass(frozen=True, slots=True)
class InputFitEvidence:
    state_truncated: bool
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.metadata]
        if len(keys) != len(set(keys)):
            raise ValueError("input-fit metadata keys must be unique")
        for key, value in self.metadata:
            _non_empty("input-fit metadata key", key)
            _non_empty("input-fit metadata value", value)


@dataclass(frozen=True, slots=True)
class DecisionQuestion:
    name: str
    instructions: str
    allowed_labels: tuple[str, ...]

    def __post_init__(self) -> None:
        _non_empty("question name", self.name)
        _non_empty("question instructions", self.instructions)
        if len(self.allowed_labels) < 2:
            raise ValueError("a Choice question requires at least two allowed labels")
        if len(self.allowed_labels) != len(set(self.allowed_labels)):
            raise ValueError("question labels must be unique")
        for label in self.allowed_labels:
            _non_empty("question label", label)


@dataclass(frozen=True, slots=True)
class QuestionPack:
    question_pack_id: str
    version: str
    arm: DecisionArm
    questions: tuple[DecisionQuestion, ...]

    def __post_init__(self) -> None:
        _non_empty("question_pack_id", self.question_pack_id)
        _non_empty("question pack version", self.version)
        if not self.questions:
            raise ValueError("question pack must contain at least one question")
        names = [question.name for question in self.questions]
        if len(names) != len(set(names)):
            raise ValueError("question names must be unique within a question pack")


@dataclass(frozen=True, slots=True)
class ChoiceDistribution:
    selected: str
    probabilities: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        _non_empty("selected choice", self.selected)
        labels = [label for label, _ in self.probabilities]
        if len(labels) != len(set(labels)):
            raise ValueError("choice probability labels must be unique")
        if self.selected not in labels:
            raise ValueError("selected choice is missing from the probability distribution")
        total = 0.0
        for label, probability in self.probabilities:
            _non_empty("choice probability label", label)
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("choice probabilities must be finite values in [0, 1]")
            total += probability
        if not math.isclose(total, 1.0, abs_tol=1e-3):
            raise ValueError("choice probabilities must sum approximately to 1")


@dataclass(frozen=True, slots=True)
class NormalizedUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative when present")
        if self.cost_usd is not None and (
            not math.isfinite(self.cost_usd) or self.cost_usd < 0
        ):
            raise ValueError("cost_usd must be finite and non-negative when present")


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    decision_event_id: str
    invocation_id: str
    snapshot_id: str
    snapshot_hash: str
    data_cutoff_ns: int
    state_schema_version: str
    state_payload: object
    arm: DecisionArm
    question_pack: QuestionPack
    common_context_version: str
    experiment_config_id: str
    model_target: ModelTarget
    deadline_seconds: float = MODEL_DEADLINE_SECONDS

    def __post_init__(self) -> None:
        for name, value in (
            ("decision_event_id", self.decision_event_id),
            ("invocation_id", self.invocation_id),
            ("snapshot_id", self.snapshot_id),
            ("snapshot_hash", self.snapshot_hash),
            ("state_schema_version", self.state_schema_version),
            ("common_context_version", self.common_context_version),
            ("experiment_config_id", self.experiment_config_id),
        ):
            _non_empty(name, value)
        _non_negative_ns("data_cutoff_ns", self.data_cutoff_ns)
        if self.state_schema_version != STATE_SCHEMA_VERSION:
            raise ValueError(f"state_schema_version must be {STATE_SCHEMA_VERSION}")
        if self.question_pack.arm is not self.arm:
            raise ValueError("question pack arm must equal request arm")
        if not math.isfinite(self.deadline_seconds) or self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be finite and positive")


@dataclass(frozen=True, slots=True)
class DecisionResult:
    decision_event_id: str
    invocation_id: str
    snapshot_id: str
    snapshot_hash: str
    data_cutoff_ns: int
    model_target: ModelTarget
    arm: DecisionArm
    question_pack_id: str
    question_pack_version: str
    experiment_config_id: str
    status: ModelInvocationStatus
    model_identity: ModelIdentity
    choices: tuple[tuple[str, ChoiceDistribution], ...]
    request_ts_ns: int
    response_ts_ns: int
    latency_ms: float
    usage: NormalizedUsage
    input_fit: InputFitEvidence
    error_code: str | None = None
    error_class: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("decision_event_id", self.decision_event_id),
            ("invocation_id", self.invocation_id),
            ("snapshot_id", self.snapshot_id),
            ("snapshot_hash", self.snapshot_hash),
            ("question_pack_id", self.question_pack_id),
            ("question_pack_version", self.question_pack_version),
            ("experiment_config_id", self.experiment_config_id),
        ):
            _non_empty(name, value)
        _non_negative_ns("data_cutoff_ns", self.data_cutoff_ns)
        _non_negative_ns("request_ts_ns", self.request_ts_ns)
        _non_negative_ns("response_ts_ns", self.response_ts_ns)
        if self.response_ts_ns < self.request_ts_ns:
            raise ValueError("response_ts_ns must be at or after request_ts_ns")
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError("latency_ms must be finite and non-negative")
        names = [name for name, _ in self.choices]
        if len(names) != len(set(names)):
            raise ValueError("result question names must be unique")
        if self.status is ModelInvocationStatus.SUCCESS:
            if self.input_fit.state_truncated:
                raise ValueError("SUCCESS requires state_truncated=false")
            if not self.choices:
                raise ValueError("SUCCESS requires normalized choices")
            if self.error_code is not None or self.error_class is not None:
                raise ValueError("SUCCESS may not carry an error code/class")
        elif self.error_code is None or self.error_class is None:
            raise ValueError("non-success results require deterministic error code/class")

    @classmethod
    def failure_for(
        cls,
        request: DecisionRequest,
        *,
        status: ModelInvocationStatus,
        request_ts_ns: int,
        response_ts_ns: int,
        error_code: str,
        error_class: str,
        model_identity: ModelIdentity | None = None,
        input_fit: InputFitEvidence | None = None,
    ) -> "DecisionResult":
        if status is ModelInvocationStatus.SUCCESS:
            raise ValueError("failure_for cannot construct SUCCESS")
        identity = model_identity or ModelIdentity(
            provider=request.model_target.provider,
            requested_model_id=request.model_target.requested_model_id,
            checkpoint_revision_or_digest=request.model_target.requested_checkpoint_or_revision,
        )
        return cls(
            decision_event_id=request.decision_event_id,
            invocation_id=request.invocation_id,
            snapshot_id=request.snapshot_id,
            snapshot_hash=request.snapshot_hash,
            data_cutoff_ns=request.data_cutoff_ns,
            model_target=request.model_target,
            arm=request.arm,
            question_pack_id=request.question_pack.question_pack_id,
            question_pack_version=request.question_pack.version,
            experiment_config_id=request.experiment_config_id,
            status=status,
            model_identity=identity,
            choices=(),
            request_ts_ns=request_ts_ns,
            response_ts_ns=response_ts_ns,
            latency_ms=max(0.0, (response_ts_ns - request_ts_ns) / 1_000_000.0),
            usage=NormalizedUsage(),
            input_fit=input_fit or InputFitEvidence(state_truncated=False),
            error_code=error_code,
            error_class=error_class,
        )


@runtime_checkable
class DecisionModelAdapter(Protocol):
    async def invoke(self, request: DecisionRequest) -> DecisionResult: ...
