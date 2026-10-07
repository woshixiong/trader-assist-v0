"""Real-form DEV admission/local-ingress tests use generated local bytes only."""
from __future__ import annotations

import inspect
from dataclasses import replace
from hashlib import sha256

import pytest
from test_research_data_binance_archive import zipped
from test_research_data_binance_research_transport import (
    CONSTRAINTS,
    mock_rights,
    response,
)
from test_research_data_contracts import H
from test_research_replay_dev_access import authority, prereg

import trader_assist_v0.research_replay.binance_real_dev as binance_real_dev_module
from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.research_data.admission import AdmissionPolicy
from trader_assist_v0.research_data.binance_archive import (
    DAY_NS,
    MAX_CHECKSUM_BYTES,
    ChecksumReceipt,
    checksum_receipt,
    frozen_archive_objects,
)
from trader_assist_v0.research_data.binance_research_transport import (
    MockOnlyResearchTransport,
    PinnedHttpsResearchTransport,
)
from trader_assist_v0.research_data.contracts import CapabilityState, ProviderCapability, SourceMode
from trader_assist_v0.research_data.mapping import (
    PitReferenceResolver,
    ReferenceMappingInterval,
    ReferenceMappingSnapshot,
)
from trader_assist_v0.research_data.storage import EvidenceSidecar
from trader_assist_v0.research_inventory.builder import _binding, build_inventory_manifest
from trader_assist_v0.research_inventory.contracts import (
    AllocationItem,
    InventoryAllocationSpec,
    InventoryRole,
    InventoryState,
)
from trader_assist_v0.research_replay.binance_real_dev import (
    FrozenRealDevCandidate,
    _require_historical_bar_only,
    bind_candidate_real_dataset,
    prepare_local_real_dev_sidecar,
    prepare_mock_real_dev_sidecar,
    prepare_real_dev_sidecar,
    read_local_checksum_receipt,
    require_complete_frozen_receipts,
)
from trader_assist_v0.research_replay.dev_archive import G0_QUESTION, G0_STRATEGY
from trader_assist_v0.research_replay.dev_evidence import (
    DevExternalAdmission,
    read_external_dev,
)
from trader_assist_v0.research_replay.dev_lifecycle import DevVisibilityPolicy

RETRIEVED = 1790000000000000000
R0_REF = "https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560"
R1_REF = "https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017243748"
RUN_REF = "https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6032019360"


def visibility():
    return DevVisibilityPolicy.create(
        version="G0_REAL_DEV_MOCK_VIS_V1", channel="DEV_LOCAL_AND_AGGREGATE",
        max_rows=288, max_bytes=4_000_000, max_buckets=64,
        aggregate_allowed=True, attribution=("FAKE_TEST_ONLY",),
    )


def mapping():
    records = []
    objects = frozen_archive_objects()
    for symbol in sorted({obj.symbol for obj in objects}):
        first = next(obj for obj in objects if obj.symbol == symbol)
        locator = (
            f"https://data.binance.vision/data/futures/um/daily/klines/{symbol}/5m/"
        )
        records.append(ReferenceMappingInterval.create(
            version="G0_REAL_DEV_MOCK_HIST_MAPPING_V1",
            provider="BINANCE", venue="BINANCE_UM", source_role="RESEARCH_IMPORT",
            native_symbol=symbol, instrument_id=symbol, product="USD_M_FUTURES",
            contract_specification=tuple(
                (key, f"UNVERIFIED_OUTSIDE_BAR_SCOPE:{key}")
                for key in (
                    "multiplier", "settlement", "expiry", "convention",
                    "price_tick", "size_step",
                )
            ),
            price_unit="USD", size_unit="CONTRACTS", currency="USDT",
            reference_currency="USDT", listing_state="LISTED",
            valid_from=first.start_ns,
            valid_to=max(obj.end_ns for obj in objects
                         if obj.symbol == symbol and obj.role_intent == "CURRENT_DEV"),
            known_at=RETRIEVED, recorded_at=RETRIEVED,
            metadata_hash=H, source_locator=locator,
            source_locator_hash=sha256_hex(locator.encode()),
            association=symbol, metadata_basis="HISTORICAL",
            support_state="AVAILABLE_VERIFIED",
        ))
    return ReferenceMappingSnapshot.create(
        version="G0_REAL_DEV_MOCK_HIST_MAPPING_SNAPSHOT_V1", records=tuple(records)
    )


def fake_receipts(first_payload: bytes) -> tuple[ChecksumReceipt, ...]:
    result = []
    objects = frozen_archive_objects()
    for index, obj in enumerate(objects):
        archive_hash = sha256(
            first_payload if index == 0 else ("FAKE:" + obj.zip_url).encode()
        ).hexdigest()
        raw = (archive_hash + "  " + obj.zip_name + "\n").encode()
        result.append(checksum_receipt(
            obj, raw, retrieved_at_ns=RETRIEVED,
            retrieval_identity="synthetic://fake-provider-checksum-fixture",
        ))
    return tuple(result)


def inventory(datasets, satisfied):
    objects = frozen_archive_objects()
    by_url = {d.source_locator: d for d in datasets}
    items = []
    for obj in objects:
        ds = by_url[obj.zip_url]
        if obj.role_intent == "CURRENT_DEV":
            role, state, limitations = (
                InventoryRole.CURRENT_DEV, InventoryState.AVAILABLE, (),
            )
        elif obj.role_intent == "FUTURE_DEV_RESERVE":
            role, state, limitations = (
                InventoryRole.FUTURE_DEV_RESERVE, InventoryState.UNKNOWN,
                ("SEALED_FAKE_CHECKSUM_IDENTITY_ONLY",),
            )
        else:
            role, state, limitations = (
                InventoryRole.CERTIFICATION_RESERVE, InventoryState.UNKNOWN,
                ("SEALED_FAKE_CHECKSUM_IDENTITY_ONLY",),
            )
        items.append(AllocationItem(
            binding=_binding(ds), role=role,
            block_id=f"G0_{obj.role_intent}_{obj.symbol}",
            intended_use="STRATEGY_DEV_RESEARCH",
            satisfied_constraints=tuple(sorted(satisfied)),
            inventory_state=state, limitations=limitations,
            reason="FAKE_TEST_ONLY: exercise frozen real-form allocation contract",
        ))
    spec = InventoryAllocationSpec.create(
        spec_id="G0_R3_REAL_DEV_FAKE_ROSTER_V1",
        freeze_evidence_locator=RUN_REF, freeze_evidence_hash=H,
        strategy_version=G0_STRATEGY, primary_research_question=G0_QUESTION,
        items=tuple(items),
    )
    return build_inventory_manifest(datasets=datasets, allocation=spec)


def fixture(first_payload: bytes | None = None):
    objects = frozen_archive_objects()
    payload = zipped(objects[0]) if first_payload is None else first_payload
    rights = mock_rights()
    snap = mapping()
    proofs = fake_receipts(payload)
    datasets = tuple(
        bind_candidate_real_dataset(
            obj, proof, mapping_hash=snap.record_hash, rights=rights,
            satisfied=CONSTRAINTS,
        )
        for obj, proof in zip(objects, proofs, strict=True)
    )
    vis = visibility()
    dev_hashes = tuple(
        ds.record_hash for obj, ds in zip(objects, datasets, strict=True)
        if obj.role_intent == "CURRENT_DEV"
    )
    reserve_hashes = tuple(
        ds.record_hash for obj, ds in zip(objects, datasets, strict=True)
        if obj.role_intent != "CURRENT_DEV"
    )
    pre = prereg(
        datasets[0], vis=vis, strategy_version=G0_STRATEGY, question=G0_QUESTION,
        r0_ref=R0_REF, r1_ref=R1_REF, run_authority_ref=RUN_REF,
        evidence_kind="RIGHTS_AUTHORIZED_DEV", dataset_hashes=dev_hashes,
        reserve_hashes=reserve_hashes,
    )
    auth = authority(
        datasets[0], pre, satisfied_constraints=tuple(sorted(CONSTRAINTS)),
    )
    cap = ProviderCapability.create(
        version="G0_REAL_DEV_MOCK_CAP_V1",
        provider="BINANCE", venue="BINANCE_UM", product="USD_M_FUTURES",
        source_mode=SourceMode.FREE_REFERENCE_IMPORT, datatype="BAR_5M",
        source_exposes=True,
        source_evidence=(
            "https://github.com/binance/binance-public-data/"
            "blob/master/README.md"
        ),
        adapter_state="AVAILABLE_VERIFIED", adapter_owner="FREE_FILE",
        proof_locator=objects[0].checksum_url, enabled=True,
    )
    policy = AdmissionPolicy.create(
        version="G0_REAL_DEV_MOCK_ADMISSION_V1",
        stale_after_ns=DAY_NS, sequence_semantics="CONTIGUOUS", max_observations=288,
    )
    admission = DevExternalAdmission(
        datasets[0], PitReferenceResolver(snap), (cap,), policy, auth, pre,
    )
    candidate = FrozenRealDevCandidate(
        proofs, datasets, inventory(datasets, CONSTRAINTS), pre, vis, CONSTRAINTS,
    )
    mock = MockOnlyResearchTransport((response(objects[0].zip_url, payload),))
    return objects, payload, rights, proofs, datasets, candidate, admission, mock


def test_local_checksum_rights_fail_before_filesystem_access(tmp_path, monkeypatch):
    obj = frozen_archive_objects()[0]

    def no_resolve(self, *args, **kwargs):
        pytest.fail("filesystem touched before rights rejection")

    monkeypatch.setattr("pathlib.Path.resolve", no_resolve)
    with pytest.raises(TypeError, match="rights contract"):
        read_local_checksum_receipt(
            obj,
            input_root=tmp_path,
            checksum_path=tmp_path / (obj.zip_name + ".CHECKSUM"),
            rights=object(),
            satisfied=CONSTRAINTS,
            retrieved_at_ns=RETRIEVED,
            retrieval_identity="file://generated-invalid-rights",
        )


def test_local_checksum_identity_reserve_and_path_bounds(tmp_path):
    objects, _, rights, proofs, _, _, _, _ = fixture()
    root = tmp_path / "input"
    root.mkdir()
    obj = objects[0]
    path = root / (obj.zip_name + ".CHECKSUM")
    raw = (proofs[0].archive_sha256 + "  " + obj.zip_name + "\n").encode()
    path.write_bytes(raw)
    identity = "file://generated-current-checksum"
    got = read_local_checksum_receipt(
        obj,
        input_root=root,
        checksum_path=path,
        rights=rights,
        satisfied=CONSTRAINTS,
        retrieved_at_ns=RETRIEVED,
        retrieval_identity=identity,
    )
    expected = checksum_receipt(
        obj, raw, retrieved_at_ns=RETRIEVED, retrieval_identity=identity,
    )
    assert got == expected

    reserve_index = next(
        i for i, item in enumerate(objects) if item.role_intent == "FUTURE_DEV_RESERVE"
    )
    reserve = objects[reserve_index]
    reserve_path = root / (reserve.zip_name + ".CHECKSUM")
    reserve_raw = (
        proofs[reserve_index].archive_sha256 + "  " + reserve.zip_name + "\n"
    ).encode()
    reserve_path.write_bytes(reserve_raw)
    reserve_receipt = read_local_checksum_receipt(
        reserve,
        input_root=root,
        checksum_path=reserve_path,
        rights=rights,
        satisfied=CONSTRAINTS,
        retrieved_at_ns=RETRIEVED,
        retrieval_identity="file://generated-reserve-checksum",
    )
    assert reserve_receipt.zip_url == reserve.zip_url

    wrong = root / "wrong.CHECKSUM"
    wrong.write_bytes(raw)
    with pytest.raises(ValueError, match="basename"):
        read_local_checksum_receipt(
            obj,
            input_root=root,
            checksum_path=wrong,
            rights=rights,
            satisfied=CONSTRAINTS,
            retrieved_at_ns=RETRIEVED,
            retrieval_identity=identity,
        )

    outside_root = tmp_path / "outside"
    outside_root.mkdir()
    escaped = outside_root / (obj.zip_name + ".CHECKSUM")
    escaped.write_bytes(raw)
    with pytest.raises(PermissionError, match="escapes"):
        read_local_checksum_receipt(
            obj,
            input_root=root,
            checksum_path=escaped,
            rights=rights,
            satisfied=CONSTRAINTS,
            retrieved_at_ns=RETRIEVED,
            retrieval_identity=identity,
        )

    path.write_bytes(b"x" * (MAX_CHECKSUM_BYTES + 1))
    with pytest.raises(ValueError, match="bounded local file"):
        read_local_checksum_receipt(
            obj,
            input_root=root,
            checksum_path=path,
            rights=rights,
            satisfied=CONSTRAINTS,
            retrieved_at_ns=RETRIEVED,
            retrieval_identity=identity,
        )

    path.write_bytes(b"malformed\n")
    with pytest.raises(ValueError, match="single exact .CHECKSUM"):
        read_local_checksum_receipt(
            obj,
            input_root=root,
            checksum_path=path,
            rights=rights,
            satisfied=CONSTRAINTS,
            retrieved_at_ns=RETRIEVED,
            retrieval_identity=identity,
        )


def test_local_current_dev_full_gate_parser_and_existing_reader_roundtrip(tmp_path):
    objects, payload, _, proofs, _, candidate, admission, _ = fixture()
    root = tmp_path / "input"
    root.mkdir()
    zip_path = root / objects[0].zip_name
    zip_path.write_bytes(payload)
    observed = RETRIEVED + 1
    prepared = prepare_local_real_dev_sidecar(
        objects[0], proofs[0], admission, candidate,
        input_root=root, zip_path=zip_path,
        output_root=tmp_path / "output", registry_hash=H,
        observed_at_ns=observed,
    )
    replay = read_external_dev(
        prepared.path.parent, prepared.path, prepared.checksum, H, admission,
    )
    assert prepared.observations == 288
    assert len(replay) == 288
    assert all(row.ts_receive is None for row in replay)
    assert all(row.receive_provenance == "NOT_EXPOSED" for row in replay)
    assert all(row.known_at == observed for row in replay)
    sidecar = EvidenceSidecar.model_validate_json(prepared.path.read_text())
    assert tuple(observation.event.sequence for observation in sidecar.observations) == tuple(
        range(1, 289)
    )
    assert all(
        observation.quality.states == (CapabilityState.AVAILABLE_VERIFIED,)
        for observation in sidecar.observations
    )
    assert all(row.quality == ("AVAILABLE_VERIFIED",) for row in replay)
    encoded = prepared.path.read_bytes()
    assert b'"source_bytes_hex":[]' in encoded
    assert payload not in encoded


def test_reserve_and_incomplete_candidate_fail_before_local_payload_filesystem(
    tmp_path, monkeypatch,
):
    objects, _, _, proofs, _, candidate, admission, _ = fixture()
    reserve_index = next(
        i for i, item in enumerate(objects) if item.role_intent == "FUTURE_DEV_RESERVE"
    )
    partial = replace(candidate, receipts=proofs[:-1])

    def no_resolve(self, *args, **kwargs):
        pytest.fail("payload filesystem touched before pre-I/O gate")

    monkeypatch.setattr("pathlib.Path.resolve", no_resolve)
    with pytest.raises(PermissionError, match="reserve"):
        prepare_local_real_dev_sidecar(
            objects[reserve_index], proofs[reserve_index], admission, candidate,
            input_root=tmp_path, zip_path=tmp_path / objects[reserve_index].zip_name,
            output_root=tmp_path, registry_hash=H, observed_at_ns=RETRIEVED + 1,
        )
    with pytest.raises(Exception, match="missing 1 exact checksum"):
        prepare_local_real_dev_sidecar(
            objects[0], proofs[0], admission, partial,
            input_root=tmp_path, zip_path=tmp_path / objects[0].zip_name,
            output_root=tmp_path, registry_hash=H, observed_at_ns=RETRIEVED + 1,
        )


def test_local_zip_sha_mismatch_and_malformed_archive_remain_parser_owned(tmp_path):
    objects, _, _, proofs, _, candidate, admission, _ = fixture()
    root = tmp_path / "mismatch"
    root.mkdir()
    zip_path = root / objects[0].zip_name
    zip_path.write_bytes(b"not-the-frozen-zip")
    with pytest.raises(ValueError, match="ZIP SHA256 mismatch before ZIP parsing"):
        prepare_local_real_dev_sidecar(
            objects[0], proofs[0], admission, candidate,
            input_root=root, zip_path=zip_path, output_root=tmp_path / "out-a",
            registry_hash=H, observed_at_ns=RETRIEVED + 1,
        )

    malformed = b"not-a-zip"
    objects2, _, _, proofs2, _, candidate2, admission2, _ = fixture(malformed)
    root2 = tmp_path / "malformed"
    root2.mkdir()
    zip_path2 = root2 / objects2[0].zip_name
    zip_path2.write_bytes(malformed)
    with pytest.raises(ValueError, match="invalid ZIP/CRC archive"):
        prepare_local_real_dev_sidecar(
            objects2[0], proofs2[0], admission2, candidate2,
            input_root=root2, zip_path=zip_path2, output_root=tmp_path / "out-b",
            registry_hash=H, observed_at_ns=RETRIEVED + 1,
        )


def test_local_ingress_adds_no_network_subprocess_or_downloader_capability():
    source = inspect.getsource(binance_real_dev_module)
    forbidden = (
        "import subprocess", "from subprocess", "import socket", "from socket",
        "urllib.request", "import requests", "from requests", "import aiohttp",
        "from aiohttp", "curl ", "wget ",
    )
    assert not [token for token in forbidden if token in source]


def test_complete_256_roster_is_required_without_hash_fabrication():
    _, _, _, proofs, _, _, _, _ = fixture()
    assert len(require_complete_frozen_receipts(proofs)) == 256
    with pytest.raises(Exception, match="missing 1 exact checksum"):
        require_complete_frozen_receipts(proofs[:-1])
    with pytest.raises(ValueError, match="duplicate"):
        require_complete_frozen_receipts((*proofs[:-1], proofs[0]))


def test_mock_real_form_full_gate_and_existing_reader_roundtrip(tmp_path):
    objects, _, rights, proofs, _, candidate, admission, mock = fixture()
    candidate.require_frozen(rights)
    prepared = prepare_mock_real_dev_sidecar(
        objects[0], proofs[0], admission, candidate,
        mock=mock, output_root=tmp_path, registry_hash=H,
    )
    assert prepared.observations == 288
    assert prepared.encoded_bytes < 4_000_000
    assert prepared.path.exists()
    replay = read_external_dev(
        tmp_path, prepared.path, prepared.checksum, H, admission,
    )
    assert len(replay) == 288
    assert all(row.ts_receive is None for row in replay)
    assert all(row.receive_provenance == "NOT_EXPOSED" for row in replay)
    assert all(row.known_at == RETRIEVED for row in replay)
    with pytest.raises(FileExistsError):
        prepare_mock_real_dev_sidecar(
            objects[0], proofs[0], admission, candidate,
            mock=mock, output_root=tmp_path, registry_hash=H,
        )


def test_partial_or_revised_roster_fails_before_mock_zip_or_write(tmp_path):
    objects, _, rights, proofs, _, candidate, admission, mock = fixture()
    partial = replace(candidate, receipts=proofs[:-1])
    with pytest.raises(Exception, match="missing 1 exact checksum"):
        prepare_mock_real_dev_sidecar(
            objects[0], proofs[0], admission, partial,
            mock=mock, output_root=tmp_path, registry_hash=H,
        )
    changed = replace(proofs[1], archive_sha256="b" * 64)
    revised = replace(candidate, receipts=(proofs[0], changed, *proofs[2:]))
    with pytest.raises(PermissionError, match="immutable binding"):
        revised.require_frozen(rights)
    assert not list(tmp_path.iterdir())


def test_reserve_zip_never_reaches_mock_transport_or_output(tmp_path):
    objects, _, _, proofs, _, candidate, admission, _ = fixture()
    reserve_index = next(
        i for i, obj in enumerate(objects) if obj.role_intent == "FUTURE_DEV_RESERVE"
    )
    reserve = objects[reserve_index]
    trap = MockOnlyResearchTransport((
        response(reserve.zip_url, b"FAKE-RESERVE-BYTES-NEVER-READ"),
    ))
    with pytest.raises(PermissionError, match="reserve"):
        prepare_mock_real_dev_sidecar(
            reserve, proofs[reserve_index], admission, candidate,
            mock=trap, output_root=tmp_path, registry_hash=H,
        )
    assert not list(tmp_path.iterdir())


def test_real_transport_is_still_denied_after_all_mock_readiness(tmp_path, monkeypatch):
    objects, _, _, proofs, _, candidate, admission, _ = fixture()

    def no_resolve(self):
        pytest.fail("filesystem touched after provider gate should have denied")

    monkeypatch.setattr("pathlib.Path.resolve", no_resolve)
    with pytest.raises(PermissionError, match="REAL_PROVIDER_IO_NOT_AUTHORIZED"):
        prepare_real_dev_sidecar(
            objects[0], proofs[0], admission, candidate,
            transport=PinnedHttpsResearchTransport(),
            output_root=tmp_path, registry_hash=H,
        )


def test_backdated_or_synthetic_mapping_is_not_historical_proof():
    objects, _, _, proofs, datasets, _, _, _ = fixture()
    obj, _, proof = objects[0], datasets[0], proofs[0]
    good = mapping().records[0]
    bad_record = ReferenceMappingInterval.create(**{
        **good.model_dump(exclude={"record_hash", "known_at", "recorded_at"}),
        "known_at": obj.start_ns, "recorded_at": obj.start_ns,
    })
    bad_snap = ReferenceMappingSnapshot.create(
        version="BAD_BACKDATED_MOCK", records=(bad_record,),
    )
    bad_ds = bind_candidate_real_dataset(
        obj, proof, mapping_hash=bad_snap.record_hash, rights=mock_rights(),
        satisfied=CONSTRAINTS,
    )
    vis = visibility()
    pre = prereg(
        bad_ds, vis=vis, strategy_version=G0_STRATEGY, question=G0_QUESTION,
        r0_ref=R0_REF, r1_ref=R1_REF, run_authority_ref=RUN_REF,
        evidence_kind="RIGHTS_AUTHORIZED_DEV", dataset_hashes=(bad_ds.record_hash,),
    )
    auth = authority(
        bad_ds, pre, satisfied_constraints=tuple(sorted(CONSTRAINTS)),
    )
    cap = ProviderCapability.create(
        version="BAD_MAPPING_MOCK_CAP", provider="BINANCE", venue="BINANCE_UM",
        product="USD_M_FUTURES", source_mode=SourceMode.FREE_REFERENCE_IMPORT,
        datatype="BAR_5M", source_exposes=True,
        source_evidence="https://data.binance.vision/fake-proof",
        adapter_state="AVAILABLE_VERIFIED", adapter_owner="FREE_FILE",
        proof_locator=obj.checksum_url, enabled=True,
    )
    admission = DevExternalAdmission(
        bad_ds, PitReferenceResolver(bad_snap), (cap,),
        AdmissionPolicy.create(
            version="BAD_MAPPING_POLICY", stale_after_ns=DAY_NS,
            sequence_semantics="UNKNOWN", max_observations=288,
        ),
        auth, pre,
    )
    with pytest.raises(Exception, match="historical mapping"):
        _require_historical_bar_only(obj, proof, admission)
