"""Frozen metadata inventory identities; these contracts never grant data access."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex
from trader_assist_v0.research_data.contracts import BoundRecord, DatasetManifest, FrozenModel

Text = Annotated[str, Field(min_length=1)]
Count = Annotated[int, Field(strict=True, ge=0)]
Timestamp = Annotated[int, Field(strict=True, gt=0)]


class InventoryRole(StrEnum):
    CURRENT_DEV = "CURRENT_DEV"
    FUTURE_DEV_RESERVE = "FUTURE_DEV_RESERVE"
    CERTIFICATION_RESERVE = "CERTIFICATION_RESERVE"
    SEALED_VALIDATION = "SEALED_VALIDATION"
    FINAL_LOCKBOX = "FINAL_LOCKBOX"
    METADATA_ONLY_EXCLUDED = "METADATA_ONLY_EXCLUDED"


class InventoryState(StrEnum):
    AVAILABLE = "AVAILABLE"
    INCOMPLETE = "INCOMPLETE"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class CountState(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    REQUIRES_SEPARATE_INVENTORY = "REQUIRES_SEPARATE_INVENTORY"


class InventoryCountKind(StrEnum):
    INDEPENDENT_EVENT = "INDEPENDENT_EVENT"
    CORRELATION_CLUSTER = "CORRELATION_CLUSTER"
    REQUIRED_CELL = "REQUIRED_CELL"


class CutIdentity(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source: Text
    venue: Text
    asset_class: Text
    instruments: tuple[Text, ...] = Field(min_length=1)
    start_ns: Timestamp
    end_ns: Timestamp
    resolution: Text
    datatypes: tuple[Text, ...]
    timezone: Text
    session_semantics: Text
    mapping_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_cut(self) -> Self:
        if self.start_ns >= self.end_ns:
            raise ValueError("invalid half-open cut")
        if len(set(self.instruments)) != len(self.instruments):
            raise ValueError("duplicate instruments")
        if len(set(self.datatypes)) != len(self.datatypes):
            raise ValueError("duplicate datatypes")
        return self


class DatasetBinding(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset_id: Text
    dataset_manifest_hash: Sha256Hex
    checksum: Sha256Hex
    cut: CutIdentity
    source_tier: Literal["R0", "R1", "R2", "R3", "R4", "R5", "R6"]
    exposure_state: Literal[
        "UNSEEN_SEALED", "SACRIFICIAL", "DEV_EXPOSED", "VALIDATION_SEALED",
        "VALIDATION_USED", "FINAL_LOCKBOX_SEALED", "FINAL_LOCKBOX_USED",
        "CONTAMINATED", "RETIRED",
    ]
    current_evidence_role: Text
    rights_hash: Sha256Hex | None
    rights_state: Literal["PRESENT", "MISSING"]
    strategy_version: Text
    primary_research_question: Text

    @model_validator(mode="after")
    def validate_rights_identity(self) -> Self:
        if (self.rights_hash is None) != (self.rights_state == "MISSING"):
            raise ValueError("rights identity/state mismatch")
        return self


class NonOutcomeInventoryFact(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_type: Literal["NON_OUTCOME"] = "NON_OUTCOME"
    kind: InventoryCountKind
    state: CountState
    value: Count | None = None
    cell_id: Text | None = None
    binding: DatasetBinding
    method_version: Text
    evidence_locator: Text
    evidence_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_count(self) -> Self:
        if (self.state == CountState.KNOWN) != (self.value is not None):
            raise ValueError("unknown counts must have no value; known counts require a value")
        if (self.kind == InventoryCountKind.REQUIRED_CELL) != (self.cell_id is not None):
            raise ValueError("required-cell facts require an exact cell identity")
        return self


class AllocationItem(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    binding: DatasetBinding
    role: InventoryRole
    block_id: Text
    intended_use: Text
    satisfied_constraints: tuple[Text, ...] = ()
    inventory_state: InventoryState
    limitations: tuple[Text, ...] = ()
    reason: Text


class InventoryAllocationSpec(BoundRecord):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: Literal["R2B_ALLOCATION_V1"] = "R2B_ALLOCATION_V1"
    spec_id: Text
    freeze_evidence_locator: Text
    freeze_evidence_hash: Sha256Hex
    strategy_version: Text
    primary_research_question: Text
    items: tuple[AllocationItem, ...] = Field(min_length=1)


class InventoryEntry(FrozenModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    dataset: DatasetManifest
    allocation: AllocationItem
    inventory_state: InventoryState
    limitations: tuple[Text, ...]
    facts: tuple[NonOutcomeInventoryFact, ...] = ()


class DatasetInventoryManifest(BoundRecord):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: Literal["R2B_INVENTORY_V1"] = "R2B_INVENTORY_V1"
    allocation_spec: InventoryAllocationSpec
    entries: tuple[InventoryEntry, ...] = Field(min_length=1)
    sufficiency_assessment: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
