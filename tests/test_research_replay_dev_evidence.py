"""Shared external sidecar and original E4/PIT projection seams, all synthetic."""

from pathlib import Path

import pytest
from test_research_data_admission import admission as pipeline_admission
from test_research_data_admission import event
from test_research_replay_contracts import H, changed
from test_research_replay_dev_access import authority, dev_dataset, prereg

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.research_data.admission import ExternalReferenceLedger
from trader_assist_v0.research_data.storage import (
    EvidenceSidecar,
    ReferenceDatasetStore,
    ReferenceReplayReader,
)
from trader_assist_v0.research_replay.contracts import Observation, checked_observation
from trader_assist_v0.research_replay.dev_evidence import (
    DevExternalAdmission,
    read_e4_dev,
    read_external_dev,
)
from trader_assist_v0.research_replay.evidence import project_external, read_e4


def external_admission():
    old = pipeline_admission()
    ds = dev_dataset(
        source="BINANCE",
        venue="BINANCE",
        datatypes=("TRADE",),
        mapping_hash=old.dataset.mapping_hash,
    )
    pre = prereg(ds)
    return DevExternalAdmission(
        ds, old.resolver, old.capabilities, old.policy, authority(ds, pre), pre
    )


def sidecar(tmp_path, bound, *, catalog_files=()):
    log = ExternalReferenceLedger(bound)
    for ev in (event(bound), event(bound), event(bound, ts=1050, seq=3, native_id="three")):
        log.observe(ev, evaluated_at_ns=1100)
    item = EvidenceSidecar.create(
        version="1",
        dataset_hash=bound.dataset.record_hash,
        mapping_hash=bound.resolver.snapshot.record_hash,
        capability_hashes=tuple(c.record_hash for c in bound.capabilities),
        policy_hash=bound.policy.record_hash,
        observations=tuple(log.observations),
        source_bytes_hex=(b"synthetic raw".hex(),),
        raw_semantics="SYNTHETIC",
        catalog_files=catalog_files,
    )
    path = tmp_path / "fixture.reference.json"
    data = canonical_json_bytes(item.model_dump(mode="json"))
    path.write_bytes(data)
    return path, sha256_hex(data), log


def test_external_composes_single_admission_quality_pit_clock_and_checksum(tmp_path):
    bound = external_admission()
    path, check, log = sidecar(tmp_path, bound)
    rows = read_external_dev(tmp_path, path, check, H, bound)
    assert len(rows) == 2 and rows[-1].quality == ("GAP",)
    assert rows[0].clock("RECEIVE") is None
    assert rows[0].evidence.source_hash == log.observations[0].event.record_hash
    old = pipeline_admission()
    original = ExternalReferenceLedger(old).observe(event(old), evaluated_at_ns=1100)
    twin = project_external(
        ReferenceReplayReader(ReferenceDatasetStore(tmp_path), old), original, H
    )
    assert (
        rows[0].values,
        rows[0].quality,
        rows[0].known_at,
        rows[0].ts_event,
        rows[0].evidence.interval_hash,
    ) == (twin.values, twin.quality, twin.known_at, twin.ts_event, twin.evidence.interval_hash)
    with pytest.raises(ValueError, match="checksum"):
        read_external_dev(tmp_path, path, "b" * 64, H, bound)
    with pytest.raises(ValueError):
        read_external_dev(tmp_path, path, check, H, bound, max_bytes=1)
    with pytest.raises(PermissionError):
        ReferenceReplayReader(ReferenceDatasetStore(tmp_path), bound).read(path, check)
    with pytest.raises(PermissionError):
        project_external(
            ReferenceReplayReader(ReferenceDatasetStore(tmp_path), bound), log.observations[0], H
        )
    with pytest.raises(PermissionError):
        Observation.create(**rows[0].model_dump(exclude={"record_hash", "authority"}))
    with pytest.raises(TypeError):
        checked_observation(rows[0].model_dump())
    with pytest.raises(ValueError):
        checked_observation(rows[0].model_copy(update={"known_at": 999}))


def test_refusal_before_root_resolution_and_catalog_tamper(tmp_path, monkeypatch):
    bound = external_admission()
    path, check, _ = sidecar(tmp_path, bound)
    bound.dataset = changed(bound.dataset, exposure_state="FINAL_LOCKBOX_SEALED")
    monkeypatch.setattr(Path, "resolve", lambda *a, **k: pytest.fail("resolve before gate"))
    with pytest.raises(PermissionError):
        read_external_dev(tmp_path, path, check, H, bound)
    monkeypatch.undo()
    bound = external_admission()
    catalog = tmp_path / "catalog.parquet"
    catalog.write_bytes(b"fixture")
    path, check, _ = sidecar(
        tmp_path, bound, catalog_files=((catalog.name, sha256_hex(b"fixture")),)
    )
    catalog.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="catalog"):
        read_external_dev(tmp_path, path, check, H, bound)
    with pytest.raises(ValueError):
        bound.validate(changed(event(bound), mapping_hash=H), 1100)
    with pytest.raises(ValueError):
        bound.validate(event(bound, ts=20000), 20001)
    with pytest.raises(ValueError):
        DevExternalAdmission(
            bound.dataset, bound.resolver, (), bound.policy, bound.authority, bound.preregistration
        ).validate(event(bound), 1100)


def test_original_e4_reader_pit_clocks_and_namespace(tmp_path):
    from test_nautilus_e4_storage import BASE, _open_durable_session
    from test_research_data_contracts import dataset

    manifest, store, session = _open_durable_session(tmp_path)
    session.close()
    snapshot = store.load_snapshot()
    original = dataset(
        source="NAUTILUS_HYPERLIQUID",
        venue="HYPERLIQUID",
        instruments=("ETH-PERP.HYPERLIQUID",),
        start_ns=BASE,
        end_ns=BASE + 10_000_000_000,
        datatypes=("TRADE",),
        mapping_hash=snapshot.snapshot_hash,
    )
    ds = dev_dataset(
        source=original.source,
        venue=original.venue,
        instruments=original.instruments,
        start_ns=original.start_ns,
        end_ns=original.end_ns,
        datatypes=original.datatypes,
        mapping_hash=original.mapping_hash,
    )
    pre = prereg(ds)
    a = authority(ds, pre)
    rows = read_e4_dev(store, ds, manifest.manifest_hash, snapshot.snapshot_hash, H, a, pre)
    twins = read_e4(store, original, manifest.manifest_hash, snapshot.snapshot_hash, H)
    assert len(rows) == len(twins) == 1
    assert rows[0].values == twins[0].values and rows[0].quality == twins[0].quality
    assert rows[0].ts_event == twins[0].ts_event and rows[0].known_at == twins[0].known_at
    assert rows[0].clock("RECEIVE") is None and rows[0].evidence.owner == "HL_E4"
    with pytest.raises(ValueError):
        read_e4_dev(store, ds, H, H, H, a, pre)
    with pytest.raises(PermissionError):
        read_e4(store, ds, manifest.manifest_hash, snapshot.snapshot_hash, H)
    bad = changed(ds, instruments=("other",))
    p = prereg(bad)
    with pytest.raises(ValueError):
        read_e4_dev(
            store, bad, manifest.manifest_hash, snapshot.snapshot_hash, H, authority(bad, p), p
        )
