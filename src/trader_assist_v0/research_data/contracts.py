"""Immutable external evidence contracts, independent of execution-venue truth."""

from __future__ import annotations

import hmac
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator

from trader_assist_v0.contracts.common import (
    FiniteDecimalString,
    NonNegativeFiniteDecimalString,
    PositiveFiniteDecimalString,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BoundRecord(FrozenModel):
    """Hash the complete versioned contract, including its concrete type."""

    version: str = Field(min_length=1)
    record_hash: str = ""

    @model_validator(mode="after")
    def verify_hash(self, info: ValidationInfo) -> Self:
        digest = sha256_hex(
            type(self).__name__.encode()
            + b"\0"
            + canonical_json_bytes(self.model_dump(mode="json", exclude={"record_hash"}))
        )
        if info.context and info.context.get("create") and not self.record_hash:
            object.__setattr__(self, "record_hash", digest)
        elif not hmac.compare_digest(self.record_hash, digest):
            raise ValueError("record hash mismatch")
        return self

    @classmethod
    def create(cls, **values: Any) -> Self:
        return cls.model_validate(values, context={"create": True})


class SourceMode(StrEnum):
    LIVE = "LIVE"
    HISTORY = "HISTORY"
    FREE_REFERENCE_IMPORT = "FREE_REFERENCE_IMPORT"


class CapabilityState(StrEnum):
    AVAILABLE_VERIFIED = "AVAILABLE_VERIFIED"
    SOURCE_NOT_AVAILABLE = "SOURCE_NOT_AVAILABLE"
    ADAPTER_UNSUPPORTED = "ADAPTER_UNSUPPORTED"
    CAPABILITY_UNPROVEN = "CAPABILITY_UNPROVEN"
    CONFIG_DISABLED = "CONFIG_DISABLED"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"
    GAP = "GAP"
    INVALID_EVIDENCE = "INVALID_EVIDENCE"
    CONTINUITY_UNKNOWN = "CONTINUITY_UNKNOWN"


class ControlReplan(RuntimeError):
    """A frozen required capability cannot be proven through its authorized owner."""


class ProviderCapability(BoundRecord):
    provider: str
    venue: str
    product: str
    source_mode: SourceMode
    datatype: str
    source_exposes: bool | None
    source_evidence: str
    adapter_state: CapabilityState
    adapter_owner: Literal["NAUTILUS_RC5", "OKX_PUBLIC_STDLIB", "FREE_FILE"]
    proof_locator: str | None
    enabled: bool

    @property
    def requirement(self) -> str:
        if self.datatype in {"BAR_1M", "BAR_5M", "TRADE", "BBO"}:
            return "CORE"
        if self.datatype in {"MARK", "INDEX", "FUNDING", "OI"}:
            return "CORE_WHERE_SOURCE_PRODUCT_EXPOSES"
        return "SUPPORTED_OPTIONAL_NOT_ALWAYS_ON"

    def require_core_proof(self) -> None:
        required = self.requirement != "SUPPORTED_OPTIONAL_NOT_ALWAYS_ON"
        if self.source_exposes is False:
            if (
                not self.source_evidence
                or self.adapter_state != CapabilityState.SOURCE_NOT_AVAILABLE
            ):
                raise ControlReplan("source absence requires independent evidence")
            return
        verified = (
            self.source_exposes is True
            and bool(self.source_evidence)
            and self.adapter_state == CapabilityState.AVAILABLE_VERIFIED
            and bool(self.proof_locator)
            and self.enabled
        )
        if required and not verified:
            raise ControlReplan("source-supported/unknown required core capability unproven")


class IntendedUseEligibility(StrEnum):
    ALLOWED = "ALLOWED"
    PROHIBITED = "PROHIBITED"
    UNKNOWN = "UNKNOWN"


class SourceRightsProvenance(BoundRecord):
    terms_locator: str = Field(min_length=1)
    observed_version: str = Field(min_length=1)
    observed_date: str = Field(min_length=1)
    terms_hash: Sha256Hex
    intended_use: str = Field(min_length=1)
    eligibility: IntendedUseEligibility
    decision_locator: str = Field(min_length=1)
    attribution_constraints: tuple[str, ...]
    retention_constraints: tuple[str, ...]
    synthetic: bool

    def require_allowed(self, use: str, satisfied: frozenset[str]) -> None:
        if self.eligibility != IntendedUseEligibility.ALLOWED or self.intended_use != use:
            raise PermissionError("intended-use rights are not ALLOWED")
        required = set(self.attribution_constraints + self.retention_constraints)
        if not required <= satisfied:
            raise PermissionError("rights constraints unsatisfied")


REQUIRED_DATASET_METADATA = frozenset(
    {
        "known_gaps",
        "survivorship_limits",
        "regime_tag_method",
        "strategy_version_allowed",
        "primary_research_question",
        "permitted_output_visibility",
        "fee_profile_version",
        "friction_profile_version",
        "oracle_basis_model_version",
        "first_opened_at",
        "open_reason",
        "current_evidence_role",
        "result_visibility_state",
        "correlation_cluster_method",
        "point_in_time_universe",
        "symbol_mapping",
        "corporate_action_policy",
        "split_adjustment_policy",
        "dividend_policy",
        "delisting_status",
        "trading_halt_status",
        "session_calendar_version",
        "timezone_dst_policy",
        "missing_bar_policy",
        "bad_tick_policy",
        "duplicate_policy",
        "provider_disagreement_policy",
        "data_revision_status",
    }
)


class DatasetManifest(BoundRecord):
    dataset_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_tier: Literal["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
    exposure_state: Literal[
        "UNSEEN_SEALED",
        "SACRIFICIAL",
        "DEV_EXPOSED",
        "VALIDATION_SEALED",
        "VALIDATION_USED",
        "FINAL_LOCKBOX_SEALED",
        "FINAL_LOCKBOX_USED",
        "CONTAMINATED",
        "RETIRED",
    ]
    venue: str
    asset_class: str
    instruments: tuple[str, ...] = Field(min_length=1)
    start_ns: int = Field(gt=0)
    end_ns: int = Field(gt=0)
    resolution: str
    datatypes: tuple[str, ...]
    timezone: str = Field(min_length=1)
    session_semantics: str = Field(min_length=1)
    checksum: Sha256Hex
    source_locator: str = Field(min_length=1)
    mapping_hash: Sha256Hex
    metadata: tuple[tuple[str, str], ...]
    rights: SourceRightsProvenance | None

    @model_validator(mode="after")
    def validate_cut(self) -> Self:
        keys = [k for k, _ in self.metadata]
        if self.start_ns >= self.end_ns or len(keys) != len(set(keys)):
            raise ValueError("invalid cut or duplicate metadata")
        if set(keys) != REQUIRED_DATASET_METADATA or any(not v for _, v in self.metadata):
            raise ValueError("complete #280 metadata required; unknown/N/A must be explicit")
        return self

    def require_access(self, use: str, satisfied: frozenset[str] = frozenset()) -> None:
        # Package A has no authority to expose performance data, even if rights allow it.
        if self.exposure_state not in {"SACRIFICIAL", "CONTAMINATED"}:
            raise PermissionError("sealed/non-sacrificial evidence access prohibited")
        if use != "PIPELINE_CORRECTNESS_ONLY":
            raise PermissionError("strategy-performance use not authorized")
        if self.rights is None:
            raise PermissionError("usage rights UNKNOWN")
        self.rights.require_allowed(use, satisfied)


class TimestampProvenance(FrozenModel):
    source_ts: str = Field(min_length=1)
    source_unit: Literal["ns", "ms"]
    ts_event: int = Field(gt=0)
    ts_init: int | None = Field(default=None, gt=0)
    true_network_receive_ts: int | None = Field(default=None, gt=0)
    receive_provenance: str = Field(min_length=1)
    observed_at_ns: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_time(self) -> Self:
        if not self.source_ts.isascii() or not self.source_ts.isdecimal():
            raise ValueError("source timestamp must be an integer string")
        factor = 1 if self.source_unit == "ns" else 1_000_000
        if int(self.source_ts) * factor != self.ts_event:
            raise ValueError("source timestamp conversion mismatch")
        if self.true_network_receive_ts is None and self.receive_provenance != "NOT_EXPOSED":
            raise ValueError("missing receive time must remain explicit")
        return self


class BarPayload(FrozenModel):
    kind: Literal["BAR"] = "BAR"
    interval_minutes: Literal[1, 5]
    start_ns: int
    end_ns: int
    timestamp_meaning: Literal["OPEN", "CLOSE"]
    aggregation_origin: str
    finalized: Literal[True]
    open: PositiveFiniteDecimalString
    high: PositiveFiniteDecimalString
    low: PositiveFiniteDecimalString
    close: PositiveFiniteDecimalString
    volume: NonNegativeFiniteDecimalString

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if (
            self.start_ns < 0
            or self.end_ns - self.start_ns != self.interval_minutes * 60_000_000_000
        ):
            raise ValueError("bar interval boundaries mismatch")
        low, high = Decimal(self.low), Decimal(self.high)
        if not low <= Decimal(self.open) <= high or not low <= Decimal(self.close) <= high:
            raise ValueError("invalid OHLC range")
        return self


class TradePayload(FrozenModel):
    kind: Literal["TRADE"] = "TRADE"
    price: PositiveFiniteDecimalString
    size: NonNegativeFiniteDecimalString
    native_id: str = Field(min_length=1)
    aggressor: str
    trade_semantics: Literal["TRADE", "AGGREGATED_TRADE"]


class BboPayload(FrozenModel):
    kind: Literal["BBO"] = "BBO"
    bid: PositiveFiniteDecimalString
    ask: PositiveFiniteDecimalString
    bid_size: NonNegativeFiniteDecimalString
    ask_size: NonNegativeFiniteDecimalString

    @model_validator(mode="after")
    def validate_quote(self) -> Self:
        if Decimal(self.bid) > Decimal(self.ask):
            raise ValueError("crossed BBO evidence")
        return self


class ContextPayload(FrozenModel):
    kind: Literal["CONTEXT"] = "CONTEXT"
    field: Literal["MARK", "INDEX", "ORACLE", "PREMIUM", "FUNDING"]
    value: FiniteDecimalString
    unit: str = Field(min_length=1)
    period: str = Field(min_length=1)
    settlement_ns: int | None = None


class OpenInterestPayload(FrozenModel):
    kind: Literal["OI"] = "OI"
    oi: NonNegativeFiniteDecimalString
    oi_ccy: NonNegativeFiniteDecimalString | None
    oi_usd: NonNegativeFiniteDecimalString | None
    oi_unit: str = Field(default="CONTRACTS", min_length=1)
    oi_ccy_unit: str = Field(min_length=1)
    oi_usd_unit: Literal["USD"] = "USD"


class DepthPayload(FrozenModel):
    kind: Literal["DEPTH"] = "DEPTH"
    shape: Literal["DEPTH10", "L2"]
    semantics: Literal["SNAPSHOT", "DELTA"]
    levels: tuple[tuple[str, PositiveFiniteDecimalString, NonNegativeFiniteDecimalString], ...]
    native_flags: tuple[str, ...]


ExternalReferencePayload = Annotated[
    BarPayload | TradePayload | BboPayload | ContextPayload | OpenInterestPayload | DepthPayload,
    Field(discriminator="kind"),
]


class ExternalReferenceEvent(BoundRecord):
    authority: Literal["EXTERNAL_REFERENCE"] = "EXTERNAL_REFERENCE"
    provider: str
    venue: str
    product: str
    instrument_id: str
    mapping_hash: Sha256Hex
    dataset_hash: Sha256Hex
    capability_hash: Sha256Hex
    rights_hash: Sha256Hex
    source_mode: SourceMode
    native_id: str = Field(min_length=1)
    sequence: int | None = Field(default=None, ge=0)
    timestamps: TimestampProvenance
    payload: ExternalReferencePayload


class ReferenceQuality(FrozenModel):
    states: tuple[CapabilityState, ...]
    reason: str
