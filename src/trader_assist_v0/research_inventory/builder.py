"""Pure metadata validation and serialization; source locators stay opaque."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.research_data.contracts import (
    DatasetManifest,
    IntendedUseEligibility,
    SourceRightsProvenance,
)

from .contracts import (
    AllocationItem,
    CountState,
    CutIdentity,
    DatasetBinding,
    DatasetInventoryManifest,
    InventoryAllocationSpec,
    InventoryCountKind,
    InventoryEntry,
    InventoryRole,
    InventoryState,
    NonOutcomeInventoryFact,
)

_MODELS = frozenset({
    DatasetManifest, SourceRightsProvenance, CutIdentity, DatasetBinding,
    NonOutcomeInventoryFact, AllocationItem, InventoryAllocationSpec,
    InventoryEntry, DatasetInventoryManifest,
})
_ENUMS = frozenset({
    IntendedUseEligibility, CountState, InventoryCountKind, InventoryRole, InventoryState,
})
_T = TypeVar("_T", bound=BaseModel)


def _check_tree(value: object) -> None:
    """Refuse subclasses, hidden copied fields and mutable/non-metadata values."""
    if isinstance(value, BaseModel):
        if type(value) not in _MODELS:
            raise TypeError("unrecognized concrete metadata model")
        fields = type(value).model_fields
        if set(value.__dict__) != set(fields) or value.model_extra:
            raise ValueError("invalid model fields")
        for name in fields:
            _check_tree(value.__dict__[name])
    elif type(value) is tuple:
        for child in value:
            _check_tree(child)
    elif isinstance(value, StrEnum):
        if type(value) not in _ENUMS:
            raise TypeError("unrecognized metadata enum")
    elif value is not None and type(value) not in {str, int, bool}:
        raise TypeError("non-metadata value")


def _snapshot(value: _T, cls: type[_T]) -> _T:
    if type(value) is not cls:
        raise TypeError("exact concrete model required")
    _check_tree(value)
    # JSON mode permits wire enum strings/arrays while strict validation refuses coercion.
    return cls.model_validate_json(BaseModel.model_dump_json(value), strict=True)


def _known(value: str) -> bool:
    token = value.strip().upper()
    return bool(token) and not token.startswith((
        "UNKNOWN", "UNAVAILABLE", "MISSING", "REQUIRES_SEPARATE_INVENTORY",
    )) and token not in {"N/A", "NA", "NONE", "*"}


def _binding(dataset: DatasetManifest) -> DatasetBinding:
    metadata = dict(dataset.metadata)
    return DatasetBinding(
        dataset_id=dataset.dataset_id,
        dataset_manifest_hash=dataset.record_hash,
        checksum=dataset.checksum,
        cut=CutIdentity(**{
            name: getattr(dataset, name) for name in CutIdentity.model_fields
        }),
        source_tier=dataset.source_tier,
        exposure_state=dataset.exposure_state,
        current_evidence_role=metadata["current_evidence_role"],
        rights_hash=dataset.rights.record_hash if dataset.rights else None,
        rights_state="PRESENT" if dataset.rights else "MISSING",
        strategy_version=metadata["strategy_version_allowed"],
        primary_research_question=metadata["primary_research_question"],
    )


def _unique(values: tuple[str, ...], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")


def _role(dataset: DatasetManifest, item: AllocationItem, spec: InventoryAllocationSpec) -> None:
    role = item.role
    exposure = dataset.exposure_state
    allowed = {
        InventoryRole.CURRENT_DEV: {"DEV_EXPOSED"},
        InventoryRole.FUTURE_DEV_RESERVE: {"DEV_EXPOSED", "UNSEEN_SEALED"},
        InventoryRole.CERTIFICATION_RESERVE: {"UNSEEN_SEALED", "VALIDATION_SEALED"},
        InventoryRole.SEALED_VALIDATION: {"VALIDATION_SEALED"},
        InventoryRole.FINAL_LOCKBOX: {"FINAL_LOCKBOX_SEALED"},
    }
    if role != InventoryRole.METADATA_ONLY_EXCLUDED and exposure not in allowed[role]:
        raise ValueError("exposure incompatible with allocation role")
    if role == InventoryRole.METADATA_ONLY_EXCLUDED:
        return
    if dataset.rights is None or dataset.rights.eligibility != IntendedUseEligibility.ALLOWED:
        raise PermissionError("non-ALLOWED rights require metadata-only exclusion")
    if role in {
        InventoryRole.CURRENT_DEV, InventoryRole.FUTURE_DEV_RESERVE,
        InventoryRole.CERTIFICATION_RESERVE,
    }:
        if not _known(item.intended_use):
            raise PermissionError("unknown intended use")
        dataset.rights.require_allowed(item.intended_use, frozenset(item.satisfied_constraints))
    if role == InventoryRole.CURRENT_DEV:
        if item.intended_use != "STRATEGY_DEV_RESEARCH":
            raise PermissionError("current DEV requires STRATEGY_DEV_RESEARCH")
        if dataset.source_tier in {"R0", "R6"}:
            raise ValueError("infrastructure/Forward evidence is not current DEV")
        if item.inventory_state in {
            InventoryState.MISSING, InventoryState.UNAVAILABLE, InventoryState.UNKNOWN,
        }:
            raise ValueError("current DEV inventory unavailable or unknown")
        b = item.binding
        critical = (
            b.strategy_version, b.primary_research_question, b.current_evidence_role,
            b.cut.source, b.cut.venue, b.cut.asset_class, b.cut.resolution,
            b.cut.timezone, b.cut.session_semantics, *b.cut.instruments, *b.cut.datatypes,
        )
        if not b.cut.datatypes or not all(_known(x) for x in critical):
            raise ValueError("unknown critical DEV metadata")
        if (b.strategy_version, b.primary_research_question) != (
            spec.strategy_version, spec.primary_research_question,
        ):
            raise ValueError("Strategy/question mismatch")


def _overlaps(left: AllocationItem, right: AllocationItem) -> bool:
    a, b = left.binding.cut, right.binding.cut
    # Unknown venue identity cannot establish disjointness.
    venue_overlap = a.venue == b.venue or not _known(a.venue) or not _known(b.venue)
    instrument_overlap = bool(set(a.instruments) & set(b.instruments)) or not all(
        _known(x) for x in (*a.instruments, *b.instruments)
    )
    return venue_overlap and instrument_overlap and max(a.start_ns, b.start_ns) < min(
        a.end_ns, b.end_ns,
    )


def _fact_key(fact: NonOutcomeInventoryFact) -> tuple[str, str, str]:
    return fact.binding.dataset_id, fact.kind.value, fact.cell_id or ""


def build_inventory_manifest(
    *,
    datasets: tuple[DatasetManifest, ...],
    allocation: InventoryAllocationSpec,
    facts: tuple[NonOutcomeInventoryFact, ...] = (),
) -> DatasetInventoryManifest:
    """Validate caller-frozen allocation; never access or classify dataset contents."""
    if type(datasets) is not tuple or type(facts) is not tuple:
        raise TypeError("immutable input tuples required")
    rows = tuple(_snapshot(d, DatasetManifest) for d in datasets)
    spec = _snapshot(allocation, InventoryAllocationSpec)
    inventory_facts = tuple(_snapshot(f, NonOutcomeInventoryFact) for f in facts)
    _unique(tuple(d.dataset_id for d in rows), "dataset IDs")
    _unique(tuple(d.record_hash for d in rows), "dataset hashes")
    _unique(tuple(i.binding.dataset_id for i in spec.items), "allocation rows")
    by_id = {d.dataset_id: d for d in rows}
    if set(by_id) != {i.binding.dataset_id for i in spec.items}:
        raise ValueError("allocation must exhaustively cover input datasets")
    for item in spec.items:
        dataset = by_id[item.binding.dataset_id]
        if item.binding != _binding(dataset):
            raise ValueError("exact dataset binding mismatch")
        _unique(item.satisfied_constraints, "satisfied constraints")
        _unique(item.limitations, "limitations")
        if item.inventory_state != InventoryState.AVAILABLE and not item.limitations:
            raise ValueError("non-available inventory requires explicit limitations")
        _role(dataset, item, spec)
    for index, left in enumerate(spec.items):
        for right in spec.items[index + 1:]:
            if _overlaps(left, right) and (left.role, left.block_id) != (
                right.role, right.block_id,
            ):
                raise ValueError("incompatible overlapping roles/blocks")
    keys = tuple(_fact_key(f) for f in inventory_facts)
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate inventory facts/cells")
    for fact in inventory_facts:
        if fact.binding.dataset_id not in by_id or fact.binding != _binding(
            by_id[fact.binding.dataset_id],
        ):
            raise ValueError("orphan/mismatched inventory fact")
        if fact.state == CountState.KNOWN and not all(_known(x) for x in (
            fact.method_version, fact.evidence_locator,
        )):
            raise ValueError("known fact requires explicit non-outcome provenance")
    items = tuple(sorted((i.model_copy(update={
        "satisfied_constraints": tuple(sorted(i.satisfied_constraints)),
        "limitations": tuple(sorted(i.limitations)),
    }) for i in spec.items), key=lambda i: i.binding.dataset_id))
    # Bind normalized allocation, not the incidental caller ordering.
    normalized_spec = InventoryAllocationSpec.create(**{
        **spec.model_dump(exclude={"record_hash", "items"}), "items": items,
    })
    entries = tuple(InventoryEntry(
        dataset=by_id[item.binding.dataset_id], allocation=item,
        inventory_state=item.inventory_state, limitations=item.limitations,
        facts=tuple(sorted((f for f in inventory_facts if f.binding.dataset_id ==
                            item.binding.dataset_id), key=_fact_key)),
    ) for item in items)
    return DatasetInventoryManifest.create(allocation_spec=normalized_spec, entries=entries)


def validate_inventory_manifest(manifest: DatasetInventoryManifest) -> DatasetInventoryManifest:
    """Check both integrity and allocation semantics, including normalized ordering."""
    value = _snapshot(manifest, DatasetInventoryManifest)
    expected = build_inventory_manifest(
        datasets=tuple(e.dataset for e in value.entries), allocation=value.allocation_spec,
        facts=tuple(f for e in value.entries for f in e.facts),
    )
    if value != expected:
        raise ValueError("noncanonical or inconsistent inventory manifest")
    return value


def inventory_manifest_bytes(manifest: DatasetInventoryManifest) -> bytes:
    return canonical_json_bytes(validate_inventory_manifest(manifest).model_dump(mode="json"))


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_number(value: str) -> None:
    raise ValueError(f"invalid JSON number: {value}")


def inventory_manifest_from_bytes(payload: bytes) -> DatasetInventoryManifest:
    if type(payload) is not bytes:
        raise TypeError("in-memory bytes required")
    json.loads(payload, object_pairs_hook=_object_pairs, parse_constant=_invalid_number)
    return validate_inventory_manifest(DatasetInventoryManifest.model_validate_json(
        payload, strict=True,
    ))
