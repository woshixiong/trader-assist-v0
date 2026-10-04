"""Synthetic metadata proves validators, never production mapping facts."""

import pytest
from pydantic import ValidationError
from test_research_data_contracts import H

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.research_data.contracts import CapabilityState, ControlReplan
from trader_assist_v0.research_data.mapping import (
    CoverageKey,
    InitialMappingCoverageManifest,
    MappingCoverageRecord,
    PitReferenceResolver,
    ReferenceMappingInterval,
    ReferenceMappingSnapshot,
)


def mapping(**updates):
    values = dict(
        version="synthetic-v1",
        provider="BINANCE",
        venue="BINANCE",
        source_role="EXTERNAL_REFERENCE",
        native_symbol="SYNTH",
        instrument_id="SYNTH",
        product="SYNTHETIC_SWAP",
        contract_specification=tuple(
            (k, "UNKNOWN: synthetic")
            for k in ("multiplier", "settlement", "expiry", "convention", "price_tick", "size_step")
        ),
        price_unit="USD",
        size_unit="CONTRACTS",
        currency="USD",
        reference_currency="USD",
        listing_state="LISTED",
        valid_from=10,
        valid_to=20,
        known_at=10,
        recorded_at=11,
        metadata_hash=H,
        source_locator="synthetic://metadata",
        source_locator_hash=sha256_hex(b"synthetic://metadata"),
        association="SYNTH",
        metadata_basis="SYNTHETIC",
        support_state="AVAILABLE_VERIFIED",
    )
    values.update(updates)
    return ReferenceMappingInterval.create(**values)


def snapshot(*records):
    return ReferenceMappingSnapshot.create(version="synthetic-v1", records=records)


def coverage():
    keys = [
        CoverageKey(category=category, provider=provider, expression=expression)
        for category, provider, expression in (
            ("HL_UNIVERSE", "HYPERLIQUID", "SYNTH"),
            ("COMMON_CRYPTO", "BINANCE", "SYNTH"),
            ("COMMON_CRYPTO", "OKX", "SYNTH"),
            ("BINANCE_LINKED", "BINANCE", "MU"),
            ("BINANCE_LINKED", "BINANCE", "SNDK"),
            ("BINANCE_LINKED", "BINANCE", "SK-HYNIX"),
            ("DIRECT_IMPORT", "DIRECT", "SYNTH"),
        )
    ]
    maps = [
        mapping(provider=k.provider, native_symbol=k.expression, instrument_id=k.expression)
        for k in keys
    ]
    # One Binance common expression and three distinct family expressions do not overlap identities.
    records = [
        MappingCoverageRecord.create(
            version="synthetic-v1",
            key=k,
            disposition="AVAILABLE_VERIFIED",
            source_exposes=True,
            evidence_locator="synthetic://coverage",
            evidence_hash=H,
            mapping_hash=m.record_hash,
            required=True,
            synthetic=True,
        )
        for k, m in zip(keys, maps, strict=True)
    ]
    return InitialMappingCoverageManifest.create(
        version="synthetic-v1",
        expected=tuple(keys),
        records=tuple(records),
        universe_manifest_hash=H,
    ), snapshot(*maps)


def test_half_open_symbol_reuse_and_contract_changes():
    first = mapping()
    second = mapping(
        valid_from=20,
        valid_to=30,
        known_at=20,
        recorded_at=20,
        instrument_id="RELISTED",
        version="synthetic-v2",
        contract_specification=tuple((k, "changed") for k, _ in first.contract_specification),
    )
    resolver = PitReferenceResolver(snapshot(first, second))
    assert resolver.resolve("BINANCE", "SYNTH", 19, 19, production=False) == first
    assert resolver.resolve("BINANCE", "RELISTED", 20, 20, production=False) == second
    with pytest.raises(ValueError):
        resolver.resolve("BINANCE", "SYNTH", 20, 30, production=False)
    with pytest.raises(ValueError):
        resolver.resolve("BINANCE", "SYNTH", 15, 10, production=False)
    with pytest.raises(PermissionError):
        resolver.resolve("BINANCE", "SYNTH", 15, 15)


@pytest.mark.parametrize(
    "changes",
    [
        dict(valid_to=10),
        dict(recorded_at=9),
        dict(metadata_basis="PROSPECTIVE", known_at=12, recorded_at=12),
        dict(source_locator_hash="b" * 64),
        dict(contract_specification=()),
    ],
)
def test_invalid_interval_or_provenance(changes):
    with pytest.raises(ValidationError):
        mapping(**changes)


def test_overlap_delisting_and_unproven_fail_closed():
    with pytest.raises(ValidationError):
        snapshot(mapping(), mapping(instrument_id="REUSED"))
    for state in (CapabilityState.ADAPTER_UNSUPPORTED, CapabilityState.CAPABILITY_UNPROVEN):
        with pytest.raises(ControlReplan):
            PitReferenceResolver(snapshot(mapping(support_state=state))).resolve(
                "BINANCE", "SYNTH", 15, 15, production=False
            )
    with pytest.raises(ValueError):
        PitReferenceResolver(snapshot(mapping(listing_state="DELISTED"))).resolve(
            "BINANCE", "SYNTH", 15, 15, production=False
        )


def test_all_four_categories_and_synthetic_production_refusal():
    manifest, maps = coverage()
    manifest.require_coverage(maps, production=False)
    with pytest.raises(PermissionError):
        manifest.require_coverage(maps, production=True)


def test_coverage_omission_duplicate_and_unresolved():
    manifest, maps = coverage()
    values = manifest.model_dump(exclude={"record_hash"})
    for records in (manifest.records[:-1], (*manifest.records, manifest.records[0])):
        with pytest.raises(ValidationError):
            InitialMappingCoverageManifest.create(**{**values, "records": records})
    record = manifest.records[0]
    changed = MappingCoverageRecord.create(
        **{**record.model_dump(exclude={"record_hash"}), "disposition": "CAPABILITY_UNPROVEN"}
    )
    unproven = InitialMappingCoverageManifest.create(
        **{**values, "records": (changed, *manifest.records[1:])}
    )
    with pytest.raises(ControlReplan):
        unproven.require_coverage(maps, production=False)
    absence = MappingCoverageRecord.create(
        **{**changed.model_dump(exclude={"record_hash"}), "disposition": "SOURCE_NOT_AVAILABLE"}
    )
    false_absence = InitialMappingCoverageManifest.create(
        **{**values, "records": (absence, *manifest.records[1:])}
    )
    with pytest.raises(ValueError):
        false_absence.require_coverage(maps, production=False)


def test_snapshot_hash_tamper_rejected():
    forged = snapshot(mapping()).model_copy(update={"records": (mapping(currency="EUR"),)})
    with pytest.raises(ValidationError):
        PitReferenceResolver(forged)
