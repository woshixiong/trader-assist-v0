"""Synthetic-only Binance-to-existing DEV sidecar and B1 rights/inventory guards."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest
from test_research_data_binance_archive import obj, receipt, rows, zipped
from test_research_data_contracts import H, rights
from test_research_replay_dev_access import authority, prereg

from trader_assist_v0.research_data.admission import AdmissionPolicy
from trader_assist_v0.research_data.binance_archive import (
    DAY_NS,
    MAX_ZIP_BYTES,
    HttpResponse,
    frozen_archive_objects,
)
from trader_assist_v0.research_data.contracts import ProviderCapability, SourceMode
from trader_assist_v0.research_data.mapping import (
    PitReferenceResolver,
    ReferenceMappingInterval,
    ReferenceMappingSnapshot,
)
from trader_assist_v0.research_inventory.builder import _binding, build_inventory_manifest
from trader_assist_v0.research_inventory.contracts import (
    AllocationItem,
    InventoryAllocationSpec,
    InventoryRole,
    InventoryState,
)
from trader_assist_v0.research_replay.dev_archive import (
    ENVELOPE_BYTES,
    G0_QUESTION,
    G0_STRATEGY,
    bind_archive_dataset,
    metadata_ledger,
    metadata_only_inventory,
    prepare_current_dev_sidecar,
)
from trader_assist_v0.research_replay.dev_evidence import (
    DevExternalAdmission,
    read_external_dev,
)
from trader_assist_v0.research_replay.dev_lifecycle import DevVisibilityPolicy


def visibility(*, max_bytes: int = 4_000_000, max_rows: int = 288):
    return DevVisibilityPolicy.create(
        version="DEV_VISIBILITY_V1",
        channel="DEV_LOCAL_AND_AGGREGATE",
        max_rows=max_rows,
        max_bytes=max_bytes,
        max_buckets=64,
        aggregate_allowed=True,
        attribution=(),
    )


def mapping(item):
    from trader_assist_v0.contracts.common import sha256_hex

    return ReferenceMappingInterval.create(
        version="synthetic-v1",
        provider="BINANCE",
        venue="BINANCE_UM",
        source_role="EXTERNAL_REFERENCE",
        native_symbol=item.symbol,
        instrument_id=item.symbol,
        product="USD_M_FUTURES",
        contract_specification=tuple(
            (key, "SYNTHETIC_UNVERIFIED")
            for key in ("multiplier", "settlement", "expiry", "convention", "price_tick", "size_step")
        ),
        price_unit="USD",
        size_unit="CONTRACTS",
        currency="USDT",
        reference_currency="USDT",
        listing_state="LISTED",
        valid_from=item.start_ns,
        valid_to=item.end_ns,
        known_at=item.start_ns,
        recorded_at=item.start_ns,
        metadata_hash=H,
        source_locator="synthetic://binance-um-contract",
        source_locator_hash=sha256_hex(b"synthetic://binance-um-contract"),
        association=item.symbol,
        metadata_basis="SYNTHETIC",
        support_state="AVAILABLE_VERIFIED",
    )


def inv(ds, *, role=InventoryRole.CURRENT_DEV, state=InventoryState.AVAILABLE):
    item = AllocationItem(
        binding=_binding(ds),
        role=role,
        block_id="G0_TEST_FROZEN_DEV",
        intended_use="STRATEGY_DEV_RESEARCH",
        inventory_state=state,
        limitations=("NOT_EXECUTABLE",) if state != InventoryState.AVAILABLE else (),
        reason="synthetic no-outcome scope",
    )
    spec = InventoryAllocationSpec.create(
        spec_id="G0_SYNTHETIC_R3",
        freeze_evidence_locator="synthetic://freeze-before-data",
        freeze_evidence_hash=H,
        strategy_version=G0_STRATEGY,
        primary_research_question=G0_QUESTION,
        items=(item,),
    )
    return build_inventory_manifest(datasets=(ds,), allocation=spec)


def fixture(*, csv_rows: list[str] | None = None, max_bytes: int = 4_000_000):
    item = obj()
    payload = zipped(item, csv_rows)
    proof = receipt(item, payload)
    snap = ReferenceMappingSnapshot.create(
        version="synthetic-v1", records=(mapping(item),)
    )
    r = rights(intended_use="STRATEGY_DEV_RESEARCH")
    ds = bind_archive_dataset(
        item, proof, mapping_hash=snap.record_hash, rights=r
    )
    vis = visibility(max_bytes=max_bytes)
    pre = prereg(
        ds, vis=vis, strategy_version=G0_STRATEGY, question=G0_QUESTION
    )
    auth = authority(ds, pre)
    cap = ProviderCapability.create(
        version="G0_BINANCE_SYNTHETIC_IMPORT_V1",
        provider="BINANCE",
        venue="BINANCE_UM",
        product="USD_M_FUTURES",
        source_mode=SourceMode.FREE_REFERENCE_IMPORT,
        datatype="BAR_5M",
        source_exposes=True,
        source_evidence="synthetic://official-schema-fixture",
        adapter_state="AVAILABLE_VERIFIED",
        adapter_owner="FREE_FILE",
        proof_locator="synthetic://offline-transport-only",
        enabled=True,
    )
    policy = AdmissionPolicy.create(
        version="G0_SYNTHETIC_ADMISSION_V1",
        stale_after_ns=DAY_NS,
        sequence_semantics="UNKNOWN",
        max_observations=288,
    )
    admission = DevExternalAdmission(
        ds, PitReferenceResolver(snap), (cap,), policy, auth, pre
    )
    allocation = inv(ds)
    calls: list[str] = []

    def opener(url: str, limit: int) -> HttpResponse:
        assert limit == MAX_ZIP_BYTES
        calls.append(url)
        return HttpResponse(
            url, 200, (("Content-Length", str(len(payload))),), payload
        )

    return item, proof, admission, allocation, vis, opener, calls


def test_metadata_ledger_exact_240_plus_8_plus_8_unknown_checksum_noninvented():
    all_rows = metadata_ledger()
    assert len(all_rows) == 256
    assert sum(x.intended_role == "CURRENT_DEV" for x in all_rows) == 240
    assert sum(x.intended_role == "FUTURE_DEV_RESERVE" for x in all_rows) == 8
    assert sum(x.intended_role == "CERTIFICATION_RESERVE" for x in all_rows) == 8
    assert {x.operative_role for x in all_rows} == {"METADATA_ONLY_EXCLUDED"}
    assert all(x.receipt is None for x in all_rows)
    assert metadata_only_inventory(
        (), mapping_hash=H, freeze_locator="synthetic://freeze", freeze_hash=H
    ) is None
    with pytest.raises(ValueError):
        metadata_ledger((replace(receipt(obj(), zipped(obj())), zip_url="https://bad.example"),))


def test_real_unknown_rights_are_only_metadata_excluded_and_intent_preserved():
    dev = obj()
    reserve = next(
        x for x in frozen_archive_objects() if x.role_intent == "CERTIFICATION_RESERVE"
    )
    proofs = (
        receipt(dev, zipped(dev)),
        receipt(reserve, b"synthetic-fake-reserve-checksum-only"),
    )
    ledger = metadata_ledger(proofs)
    assert len(ledger) == 256
    assert sum(x.receipt is not None for x in ledger) == 2
    manifest = metadata_only_inventory(
        proofs,
        mapping_hash=H,
        freeze_locator="synthetic://freeze",
        freeze_hash=H,
    )
    assert manifest is not None
    assert len(manifest.entries) == 2
    assert manifest.sufficiency_assessment == "NOT_ASSESSED"
    for entry in manifest.entries:
        assert entry.dataset.exposure_state == "UNSEEN_SEALED"
        assert entry.dataset.rights is None
        assert entry.allocation.role == InventoryRole.METADATA_ONLY_EXCLUDED
        assert entry.allocation.inventory_state == InventoryState.UNKNOWN
        assert entry.allocation.limitations
        assert entry.dataset.checksum in {p.archive_sha256 for p in proofs}
        for bad_role in (
            InventoryRole.CURRENT_DEV,
            InventoryRole.FUTURE_DEV_RESERVE,
            InventoryRole.CERTIFICATION_RESERVE,
        ):
            row = entry.allocation.model_copy(update={"role": bad_role})
            spec = InventoryAllocationSpec.create(
                **{
                    **manifest.allocation_spec.model_dump(
                        exclude={"record_hash", "items"}
                    ),
                    "items": (row,),
                }
            )
            with pytest.raises((ValueError, PermissionError)):
                build_inventory_manifest(
                    datasets=(entry.dataset,), allocation=spec
                )


def test_real_allowed_claim_does_not_authorize_this_package():
    item = obj()
    proof = receipt(item, zipped(item))
    for real in (
        rights(
            intended_use="STRATEGY_DEV_RESEARCH", synthetic=False, eligibility="ALLOWED"
        ),
        rights(
            intended_use="STRATEGY_DEV_RESEARCH", synthetic=True, eligibility="UNKNOWN"
        ),
    ):
        with pytest.raises(PermissionError):
            bind_archive_dataset(item, proof, mapping_hash=H, rights=real)
    for eligibility in ("UNKNOWN", "PROHIBITED"):
        real = rights(
            intended_use="STRATEGY_DEV_RESEARCH",
            synthetic=False,
            eligibility=eligibility,
        )
        ds = bind_archive_dataset(item, proof, mapping_hash=H, rights=real)
        assert ds.exposure_state == "UNSEEN_SEALED"
        assert ds.rights is not None
        assert ds.rights.eligibility == eligibility


def test_real_synthetic_fixture_roundtrip_and_causality(tmp_path):
    item, proof, bound, allocation, vis, opener, calls = fixture()
    prepared = prepare_current_dev_sidecar(
        item, proof, bound, allocation, vis, opener=opener, output_root=tmp_path
    )
    assert calls == [item.zip_url]
    assert prepared.observations == 288
    assert prepared.encoded_bytes <= ENVELOPE_BYTES < 4_000_000
    assert prepared.path.name == prepared.record_hash + ".reference.json"
    assert prepared.checksum == sha256(prepared.path.read_bytes()).hexdigest()
    observations = read_external_dev(
        tmp_path, prepared.path, prepared.checksum, H, bound
    )
    assert len(observations) == 288
    assert all(row.ts_receive is None and row.receive_provenance == "NOT_EXPOSED"
               for row in observations)
    assert all(row.known_at == proof.retrieved_at_ns for row in observations)
    assert observations[0].ts_event == item.start_ns
    assert observations[-1].bar_end == item.end_ns
    assert observations[0].evidence.source_tier == "R3"
    assert observations[0].evidence.exposure_state == "DEV_EXPOSED"
    assert observations[0].quality
    with pytest.raises(FileExistsError):
        prepare_current_dev_sidecar(
            item, proof, bound, allocation, vis, opener=opener, output_root=tmp_path
        )
    with pytest.raises(ValueError):
        read_external_dev(tmp_path, prepared.path, "a" * 64, H, bound)
    prepared.path.write_bytes(prepared.path.read_bytes() + b"x")
    with pytest.raises(ValueError):
        read_external_dev(tmp_path, prepared.path, prepared.checksum, H, bound)


def test_invalid_authority_inventory_and_visibility_fail_before_fixture_opener(tmp_path):
    item, proof, bound, inventory, vis, _, _ = fixture()

    def never(url: str, limit: int) -> HttpResponse:
        pytest.fail(f"unauthorized fake HTTP opener: {url} {limit}")

    for changed_inventory in (
        inv(bound.dataset, role=InventoryRole.METADATA_ONLY_EXCLUDED,
            state=InventoryState.UNKNOWN),
        inv(bound.dataset, role=InventoryRole.FUTURE_DEV_RESERVE),
    ):
        with pytest.raises((ValueError, PermissionError)):
            prepare_current_dev_sidecar(
                item, proof, bound, changed_inventory, vis,
                opener=never, output_root=tmp_path,
            )
    other_receipt = replace(proof, archive_sha256="b" * 64)
    with pytest.raises((ValueError, PermissionError)):
        prepare_current_dev_sidecar(
            item, other_receipt, bound, inventory, vis,
            opener=never, output_root=tmp_path,
        )
    # A non-matching visibility identity is rejected before path or opener I/O.
    with pytest.raises((ValueError, PermissionError)):
        prepare_current_dev_sidecar(
            item, proof, bound, inventory, visibility(max_rows=287),
            opener=never, output_root=tmp_path,
        )
    assert not list(tmp_path.iterdir())


def test_reserve_zip_opener_sentinel_and_noncurrent_role(tmp_path):
    item, proof, bound, inventory, vis, _, _ = fixture()
    reserve = next(
        x for x in frozen_archive_objects() if x.role_intent == "FUTURE_DEV_RESERVE"
    )
    forged_proof = receipt(reserve, b"synthetic-fake-reserve-no-archive")
    accessed: list[str] = []

    def never(url: str, limit: int) -> HttpResponse:
        accessed.append(url)
        pytest.fail("reserve ZIP opened")

    with pytest.raises(PermissionError):
        prepare_current_dev_sidecar(
            reserve, forged_proof, bound, inventory, vis,
            opener=never, output_root=tmp_path,
        )
    assert accessed == []
    assert item.role_intent == "CURRENT_DEV"
    assert proof.zip_url == item.zip_url


def test_wrong_strategy_and_prereg_hash_fail_before_io(tmp_path):
    item, proof, bound, inventory, vis, _, _ = fixture()
    bound.preregistration = prereg(
        bound.dataset,
        vis=vis,
        strategy_version="WRONG_VERSION",
        question=G0_QUESTION,
    )

    def never(url: str, limit: int) -> HttpResponse:
        pytest.fail("opener used before Strategy/prereg gate")

    with pytest.raises(PermissionError):
        prepare_current_dev_sidecar(
            item, proof, bound, inventory, vis,
            opener=never, output_root=tmp_path,
        )


def test_missing_real_rights_and_synthetic_kind_guard(tmp_path):
    item, proof, bound, inventory, vis, _, _ = fixture()
    no_rights = bound.dataset.model_copy(update={"rights": None})
    bound.dataset = no_rights

    def never(url: str, limit: int) -> HttpResponse:
        pytest.fail("opener used with missing rights")

    with pytest.raises((ValueError, PermissionError)):
        prepare_current_dev_sidecar(
            item, proof, bound, inventory, vis,
            opener=never, output_root=tmp_path,
        )


def test_small_visibility_bound_refuses_sidecar_before_file_write(tmp_path):
    item, proof, bound, inventory, vis, opener, calls = fixture(max_bytes=1500)
    with pytest.raises(ValueError, match="sidecar"):
        prepare_current_dev_sidecar(
            item, proof, bound, inventory, vis, opener=opener, output_root=tmp_path
        )
    assert calls == [item.zip_url]
    assert not list(tmp_path.iterdir())


def test_maximum_length_wire_fields_fit_existing_four_mb_sidecar(tmp_path):
    item = obj()
    dense = rows(item)
    start_ms = item.start_ns // 1_000_000
    maximum = "9" * 80
    dense = [
        f"{start_ms + index * 300000},{maximum},{maximum},{maximum},"
        f"{maximum},{maximum},{start_ms + index * 300000 + 299999},"
        f"{maximum},999999,{maximum},{maximum},5"
        for index in range(288)
    ]
    item, proof, bound, inventory, vis, opener, _ = fixture(csv_rows=dense)
    prepared = prepare_current_dev_sidecar(
        item, proof, bound, inventory, vis, opener=opener, output_root=tmp_path
    )
    assert prepared.observations == 288
    assert prepared.encoded_bytes <= ENVELOPE_BYTES
    assert prepared.encoded_bytes < 4_000_000
    assert len(read_external_dev(tmp_path, prepared.path, prepared.checksum, H, bound)) == 288


def test_transport_identity_and_sha_fail_without_sidecar_io(tmp_path):
    item, proof, bound, inventory, vis, opener, _ = fixture()

    def redirected(url: str, limit: int) -> HttpResponse:
        response = opener(url, limit)
        return replace(response, redirected=True)

    with pytest.raises(ValueError):
        prepare_current_dev_sidecar(
            item, proof, bound, inventory, vis, opener=redirected, output_root=tmp_path
        )
    with pytest.raises(PermissionError, match="binding mismatch"):
        prepare_current_dev_sidecar(
            item, replace(proof, archive_sha256="b" * 64), bound,
            # The receipt/dataset guard rejects changed checksum before raw I/O.
            inventory, vis, opener=opener, output_root=tmp_path,
        )
    assert not list(tmp_path.iterdir())
