"""Supplied synthetic files only; no provider acquisition."""

import pytest
from test_research_data_admission import admission
from test_research_data_contracts import rights

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.research_data.contracts import SourceMode
from trader_assist_v0.research_data.free_import import (
    FreeReferenceImportSpec,
    import_free_reference,
)

CSV = (
    b"instrument_id,native_id,source_ts_ns,interval_minutes,start_ns,end_ns,timestamp_meaning,"
    b"open,high,low,close,volume\n"
    b"SYNTH,row-1,60000000010,1,10,60000000010,CLOSE,10,11,9,10,2\n"
)


def setup_import(tmp_path, raw=CSV, **changes):
    path = tmp_path / "supplied.csv"
    path.write_bytes(raw)
    bound = admission(
        mode=SourceMode.FREE_REFERENCE_IMPORT,
        datatype="BAR_1M",
        ds_changes={"checksum": sha256_hex(raw), **changes},
    )
    spec = FreeReferenceImportSpec.create(
        version="synthetic-v1",
        format="BAR_CSV_V1",
        checksum=sha256_hex(raw),
        max_bytes=2000,
        max_rows=2,
        timezone="UTC",
        session="24x7",
        adjustment_policy="UNADJUSTED_EXPLICIT",
        adjustment_provenance="synthetic://unadjusted",
    )
    return path, bound, spec


def test_free_csv_preserves_source_mode_units_and_missing_receive(tmp_path):
    path, bound, spec = setup_import(tmp_path)
    ledger = import_free_reference(path, spec, bound, observed_at_ns=70_000_000_000)
    value = ledger.observations[0].event
    assert value.payload.volume == "2" and value.payload.interval_minutes == 1
    assert value.source_mode == SourceMode.FREE_REFERENCE_IMPORT
    assert value.timestamps.true_network_receive_ts is None and value.timestamps.ts_init is None


@pytest.mark.parametrize(
    "raw",
    [
        CSV.replace(b"60000000010,1", b"ambiguous-DST,1"),
        CSV.replace(b"CLOSE,10", b"UNKNOWN,10"),
        CSV.replace(b"open,high", b"open,unknown"),
        CSV.replace(b"10,11,9,10,2", b"10,NaN,9,10,2"),
        CSV + CSV.splitlines()[1] + b"\n" * 2,
    ],
)
def test_malformed_or_ambiguous_import_rejected(tmp_path, raw):
    path, bound, spec = setup_import(tmp_path, raw)
    with pytest.raises((ValueError, TypeError)):
        import_free_reference(path, spec, bound, observed_at_ns=70_000_000_000)


def test_checksum_byte_row_and_session_limits(tmp_path):
    path, bound, spec = setup_import(tmp_path)
    path.write_bytes(CSV + b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        import_free_reference(path, spec, bound, observed_at_ns=70_000_000_000)
    path.write_bytes(CSV)
    for changes in ({"max_bytes": 10}, {"session": "unknown"}, {"timezone": "America/New_York"}):
        altered = FreeReferenceImportSpec.create(
            **{**spec.model_dump(exclude={"record_hash"}), **changes}
        )
        with pytest.raises(ValueError):
            import_free_reference(path, altered, bound, observed_at_ns=70_000_000_000)


@pytest.mark.parametrize(
    "rights_record",
    [
        None,
        rights(eligibility="UNKNOWN"),
        rights(eligibility="PROHIBITED"),
        rights(intended_use="OTHER"),
        rights(attribution_constraints=("REQUIRED",)),
    ],
)
def test_rights_reject_before_file_read(tmp_path, monkeypatch, rights_record):
    path, bound, spec = setup_import(tmp_path)
    from test_research_data_contracts import dataset

    bound.dataset = dataset(
        venue="BINANCE",
        instruments=("SYNTH",),
        datatypes=("BAR_1M",),
        checksum=spec.checksum,
        mapping_hash=bound.resolver.snapshot.record_hash,
        rights=rights_record,
    )

    def never(*args, **kwargs):
        raise AssertionError("read before rights gate")

    monkeypatch.setattr(type(path), "open", never)
    with pytest.raises(PermissionError):
        import_free_reference(path, spec, bound, observed_at_ns=70_000_000_000)
