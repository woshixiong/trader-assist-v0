"""Provenance-bound reference identities; never an execution universe replacement."""

from typing import Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex, sha256_hex

from .contracts import BoundRecord, CapabilityState, ControlReplan, FrozenModel


class ReferenceMappingInterval(BoundRecord):
    provider: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    source_role: Literal["EXECUTION_UNIVERSE_METADATA", "EXTERNAL_REFERENCE", "RESEARCH_IMPORT"]
    native_symbol: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    product: str = Field(min_length=1)
    contract_specification: tuple[tuple[str, str], ...]
    price_unit: str = Field(min_length=1)
    size_unit: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    reference_currency: str = Field(min_length=1)
    listing_state: Literal["LISTED", "DELISTED", "HALTED"]
    valid_from: int = Field(gt=0)
    valid_to: int = Field(gt=0)
    known_at: int = Field(gt=0)
    recorded_at: int = Field(gt=0)
    metadata_hash: Sha256Hex
    source_locator: str = Field(min_length=1)
    source_locator_hash: Sha256Hex
    association: str | None
    metadata_basis: Literal["PROSPECTIVE", "HISTORICAL", "SYNTHETIC"]
    support_state: CapabilityState

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.valid_from >= self.valid_to or self.recorded_at < self.known_at:
            raise ValueError("invalid mapping interval/knowledge provenance")
        if self.metadata_basis == "PROSPECTIVE" and self.valid_from < self.known_at:
            raise ValueError("current metadata cannot establish historical truth")
        if sha256_hex(self.source_locator.encode()) != self.source_locator_hash:
            raise ValueError("mapping locator hash mismatch")
        keys = [k for k, _ in self.contract_specification]
        required = {"multiplier", "settlement", "expiry", "convention", "price_tick", "size_step"}
        if set(keys) != required or len(keys) != len(set(keys)):
            raise ValueError("complete unique contract specification required")
        if any(not value for _, value in self.contract_specification):
            raise ValueError("unknown/nonapplicable contract facts require explicit reasons")
        return self


class ReferenceMappingSnapshot(BoundRecord):
    records: tuple[ReferenceMappingInterval, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_intervals(self) -> Self:
        for i, left in enumerate(self.records):
            for right in self.records[i + 1 :]:
                if (left.provider, left.venue, left.native_symbol) == (
                    right.provider,
                    right.venue,
                    right.native_symbol,
                ) and max(left.valid_from, right.valid_from) < min(left.valid_to, right.valid_to):
                    raise ValueError("overlapping native-symbol mapping intervals")
        return self


class PitReferenceResolver:
    def __init__(self, snapshot: ReferenceMappingSnapshot) -> None:
        self.snapshot = ReferenceMappingSnapshot.model_validate_json(snapshot.model_dump_json())

    def resolve(
        self,
        provider: str,
        instrument_id: str,
        event_ns: int,
        knowledge_ns: int,
        *,
        production: bool = True,
    ) -> ReferenceMappingInterval:
        candidates = [
            r
            for r in self.snapshot.records
            if r.provider == provider
            and r.instrument_id == instrument_id
            and r.valid_from <= event_ns < r.valid_to
            and max(r.known_at, r.recorded_at) <= knowledge_ns
        ]
        if len(candidates) != 1:
            raise ValueError("missing or ambiguous PIT reference mapping")
        record = candidates[0]
        if production and record.metadata_basis == "SYNTHETIC":
            raise PermissionError("synthetic mappings are not production truth")
        if record.support_state != CapabilityState.AVAILABLE_VERIFIED:
            raise ControlReplan("source product mapping/support is not verified")
        if record.listing_state != "LISTED":
            raise ValueError("instrument is not listed at event time")
        return record


class CoverageKey(FrozenModel):
    category: Literal["HL_UNIVERSE", "COMMON_CRYPTO", "BINANCE_LINKED", "DIRECT_IMPORT"]
    provider: str = Field(min_length=1)
    expression: str = Field(min_length=1)


class MappingCoverageRecord(BoundRecord):
    key: CoverageKey
    disposition: CapabilityState
    source_exposes: bool | None
    evidence_locator: str = Field(min_length=1)
    evidence_hash: Sha256Hex
    mapping_hash: Sha256Hex | None
    required: bool
    synthetic: bool


class InitialMappingCoverageManifest(BoundRecord):
    expected: tuple[CoverageKey, ...]
    records: tuple[MappingCoverageRecord, ...]
    universe_manifest_hash: Sha256Hex

    @model_validator(mode="after")
    def complete_expected_set(self) -> Self:
        expected = [k.model_dump_json() for k in self.expected]
        actual = [r.key.model_dump_json() for r in self.records]
        if len(expected) != len(set(expected)) or len(actual) != len(set(actual)):
            raise ValueError("duplicate coverage member")
        if set(expected) != set(actual):
            raise ValueError("coverage omission or unexpected member")
        if {k.category for k in self.expected} != {
            "HL_UNIVERSE",
            "COMMON_CRYPTO",
            "BINANCE_LINKED",
            "DIRECT_IMPORT",
        }:
            raise ValueError("all four A7 categories required")
        if {k.provider for k in self.expected if k.category == "COMMON_CRYPTO"} != {
            "BINANCE",
            "OKX",
        }:
            raise ValueError("both common crypto providers required")
        linked = {
            k.expression
            for k in self.expected
            if k.category == "BINANCE_LINKED" and k.provider == "BINANCE"
        }
        if linked != {"MU", "SNDK", "SK-HYNIX"}:
            raise ValueError("all three linked Binance families required")
        return self

    def require_coverage(self, snapshot: ReferenceMappingSnapshot, *, production: bool) -> None:
        bound = InitialMappingCoverageManifest.model_validate_json(self.model_dump_json())
        snapshot = ReferenceMappingSnapshot.model_validate_json(snapshot.model_dump_json())
        mappings = {r.record_hash: r for r in snapshot.records}
        for record in bound.records:
            if production and record.synthetic:
                raise PermissionError("synthetic coverage is not production truth")
            if record.disposition == CapabilityState.SOURCE_NOT_AVAILABLE:
                if record.source_exposes is not False or record.mapping_hash is not None:
                    raise ValueError("source absence cannot mask adapter failure")
                continue
            if record.disposition != CapabilityState.AVAILABLE_VERIFIED:
                if record.required:
                    raise ControlReplan("unresolved required coverage")
                continue
            mapping = mappings.get(record.mapping_hash or "")
            if record.source_exposes is not True or mapping is None:
                raise ValueError("verified coverage requires bound source mapping")
            if mapping.provider != record.key.provider:
                raise ValueError("coverage provider substitution")
            if mapping.support_state != CapabilityState.AVAILABLE_VERIFIED:
                raise ControlReplan("coverage mapping support unproven")
            if production and mapping.metadata_basis == "SYNTHETIC":
                raise PermissionError("synthetic mapping cannot enable production coverage")
