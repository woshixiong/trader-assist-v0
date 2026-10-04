"""Complete bounded evidence must validate before replay exposes any fact."""

import pytest
from test_research_data_admission import admission, event

from trader_assist_v0.research_data.admission import ExternalReferenceLedger
from trader_assist_v0.research_data.storage import ReferenceDatasetStore, ReferenceReplayReader


def test_restart_replay_identity_quality_order_and_raw_fidelity(tmp_path):
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    for value in (
        event(bound),
        event(bound),
        event(bound, ts=1050, seq=3, native_id="three"),
        event(bound, ts=1020, seq=2, native_id="two"),
    ):
        ledger.observe(value, evaluated_at_ns=1100)
    store = ReferenceDatasetStore(tmp_path)
    path, checksum = store.write(
        ledger,
        source_bytes=(b'{"source": "exact spaces"}\n',),
        raw_semantics="SUPPLIED_SOURCE_BYTES",
    )
    result = ReferenceReplayReader(store, admission()).read(path, checksum)
    assert result == tuple(ledger.observations)
    assert ReferenceReplayReader(store, admission()).read(path, checksum) == result
    with pytest.raises(FileExistsError):
        store.write(
            ledger,
            source_bytes=(b'{"source": "exact spaces"}\n',),
            raw_semantics="SUPPLIED_SOURCE_BYTES",
        )


def test_checksum_partial_corrupt_binding_and_catalog_tamper(tmp_path):
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    ledger.observe(event(bound), evaluated_at_ns=1001)
    store = ReferenceDatasetStore(tmp_path)
    native_file = tmp_path / "native.parquet"
    native_file.write_bytes(b"synthetic-catalog")
    path, checksum = store.write(ledger, catalog_files=(native_file,))
    with pytest.raises(ValueError, match="checksum"):
        ReferenceReplayReader(store, bound).read(path, "b" * 64)
    native_file.write_bytes(b"tamper")
    with pytest.raises(ValueError, match="catalog"):
        ReferenceReplayReader(store, bound).read(path, checksum)
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError):
        ReferenceReplayReader(store, bound).read(path, checksum)


def test_replay_rights_refusal_before_file_open(tmp_path, monkeypatch):
    bound = admission()
    ledger = ExternalReferenceLedger(bound)
    ledger.observe(event(bound), evaluated_at_ns=1001)
    store = ReferenceDatasetStore(tmp_path)
    path, checksum = store.write(ledger)
    from test_research_data_contracts import dataset, rights

    bound.dataset = dataset(
        venue="BINANCE",
        source="BINANCE",
        instruments=("SYNTH",),
        datatypes=("TRADE",),
        mapping_hash=bound.resolver.snapshot.record_hash,
        rights=rights(eligibility="PROHIBITED"),
    )

    def never(*args, **kwargs):
        raise AssertionError("file was opened before rights")

    monkeypatch.setattr(type(path), "open", never)
    with pytest.raises(PermissionError):
        ReferenceReplayReader(store, bound).read(path, checksum)


def test_native_catalog_owns_serialization_and_bounds(tmp_path):
    calls = []

    class Catalog:
        def write_trade_ticks(self, records):
            calls.append(records)
            return "native.parquet"

    store = ReferenceDatasetStore(tmp_path, catalog=Catalog(), max_bytes=100)
    assert store.write_native("TRADE", [object()], admission()) == "native.parquet"
    assert len(calls) == 1
    with pytest.raises(ValueError):
        store.write_native("OI", [object()], admission())
    with pytest.raises(ValueError):
        store.write(ExternalReferenceLedger(admission()), source_bytes=(b"x" * 101,))
