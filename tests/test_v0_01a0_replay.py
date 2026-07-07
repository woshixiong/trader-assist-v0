from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

import trader_assist_v0.data.bronze as bronze_module
from trader_assist_v0.contracts import (
    BronzeReplayReportV0,
    EnvironmentV0,
    RawCaptureModeV0,
    RawEventV0,
    RawManifestEntryV0,
    ReplayStatusV0,
)
from trader_assist_v0.data import (
    SOURCE_CATALOG_VERSION,
    BronzeStore,
    ManifestWriter,
    replay_segment,
)

DAY = date(2026, 7, 7)
NOW = datetime(2026, 7, 7, 1, 0, tzinfo=UTC)
SEGMENT = "segment-001"


def _event(store: BronzeStore, payload: bytes, sequence: int) -> RawEventV0:
    stored = store.write_payload(payload)
    return RawEventV0.bind_observation(
        schema_version="0.1.0",
        source_id="hyperliquid-public-mainnet",
        source_catalog_version=SOURCE_CATALOG_VERSION,
        endpoint_id="hl-ws-mainnet-public",
        connection_id="conn-001",
        subscription_id="pong-control",
        receive_sequence=sequence,
        source_native_id=None,
        source_native_cursor=None,
        collector_version="collector.0.1",
        environment=EnvironmentV0.READ_ONLY,
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        content_type="application/json",
        payload_sha256=stored.payload_sha256,
        payload_size_bytes=stored.payload_size_bytes,
        payload_encoding="utf-8",
        payload_ref=stored.payload_ref,
        source_event_time=None,
        source_publish_time=None,
        first_observed_time=NOW,
        collector_receive_time=NOW,
        collector_monotonic_ns=123,
        revision_time=None,
    )


def _create_evidence(root: Path) -> BronzeStore:
    store = BronzeStore(root)
    payload = b'{"channel":"pong"}'
    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT) as writer:
        writer.append(_event(store, payload, 1))
        writer.append(_event(store, payload, 2))
    return store


def test_replay_pass_dedup_and_deterministic(tmp_path):
    store = _create_evidence(tmp_path / "a")
    first = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    second = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert first.status is ReplayStatusV0.PASS
    assert first.unique_payload_blobs == 1
    assert first.duplicate_payload_observations == 1
    assert first == second
    assert first.report_hash == second.report_hash


def test_missing_corrupt_orphan_and_partial_fail(tmp_path):
    store = _create_evidence(tmp_path / "root")
    manifest_path = store.path(store.manifest_ref(DAY, SEGMENT))
    original = manifest_path.read_bytes()
    first = json.loads(original.splitlines()[0])
    payload = store.path(first["raw_event"]["payload_ref"])
    payload.unlink()
    assert replay_segment(
        store, manifest_date=DAY, segment_id=SEGMENT
    ).missing_payload_count > 0

    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(b"bad")
    assert replay_segment(
        store, manifest_date=DAY, segment_id=SEGMENT
    ).corrupt_payload_count > 0

    store.write_payload(b"orphan")
    assert replay_segment(
        store, manifest_date=DAY, segment_id=SEGMENT
    ).orphan_payload_count > 0

    manifest_path.write_bytes(original[:-1])
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).partial_manifest_count
        == 1
    )


def test_report_tamper_fails_closed(tmp_path):
    report = replay_segment(
        _create_evidence(tmp_path / "root"),
        manifest_date=DAY,
        segment_id=SEGMENT,
    )
    stale = BaseModel.model_copy(report, update={"entries_checked": 99})
    with pytest.raises(ValidationError):
        BronzeReplayReportV0.model_validate(stale)
    with pytest.raises(TypeError):
        report.model_copy(update={"entries_checked": 99})
    payload = report.model_dump(mode="python")
    payload["entries_checked"] = 99
    constructed = BaseModel.model_construct.__func__(BronzeReplayReportV0, **payload)
    with pytest.raises(ValidationError):
        BronzeReplayReportV0.model_validate(constructed)

    class EvilReport(BronzeReplayReportV0):
        pass

    evil = BaseModel.model_construct.__func__(EvilReport, **report.model_dump(mode="python"))
    with pytest.raises((ValueError, ValidationError)):
        BronzeReplayReportV0.model_validate(evil)


def test_cross_root_and_cross_process_determinism(tmp_path):
    first_store = _create_evidence(tmp_path / "a")
    second_store = _create_evidence(tmp_path / "b")
    first = replay_segment(first_store, manifest_date=DAY, segment_id=SEGMENT)
    second = replay_segment(second_store, manifest_date=DAY, segment_id=SEGMENT)
    assert first.model_dump() == second.model_dump()

    script = (
        "from datetime import date\n"
        "from pathlib import Path\n"
        "from trader_assist_v0.data import BronzeStore,replay_segment\n"
        "import sys\n"
        "report=replay_segment(BronzeStore(Path(sys.argv[1])),"
        "manifest_date=date(2026,7,7),segment_id='segment-001')\n"
        "print(report.report_hash)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    output = subprocess.check_output(
        [sys.executable, "-c", script, str(first_store.root)],
        text=True,
        env=env,
    ).strip()
    assert output == first.report_hash


def test_replay_has_no_network_fallback(tmp_path):
    report = replay_segment(
        BronzeStore(tmp_path / "root"),
        manifest_date=DAY,
        segment_id=SEGMENT,
    )
    assert report.status is ReplayStatusV0.FAIL
    assert "MISSING_MANIFEST" in report.reason_codes


def test_short_manifest_write_leaves_detectable_partial_line(tmp_path, monkeypatch):
    store = BronzeStore(tmp_path / "root")
    event = _event(store, b'{"channel":"pong"}', 1)
    original_write = bronze_module.os.write

    def short_write(descriptor: int, payload: bytes) -> int:
        prefix = payload[: max(1, len(payload) // 2)]
        return original_write(descriptor, prefix)

    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT) as writer:
        monkeypatch.setattr(bronze_module.os, "write", short_write)
        with pytest.raises(OSError, match="short manifest append"):
            writer.append(event)
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.FAIL
    assert report.partial_manifest_count == 1


def test_unexpected_payload_tree_entry_fails_closed(tmp_path):
    store = _create_evidence(tmp_path / "root")
    unexpected = store.root / "payloads" / "sha256" / "unexpected"
    unexpected.mkdir()
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.FAIL
    assert "PAYLOAD_TREE_INVALID" in report.reason_codes


def test_nested_raw_event_subclass_is_rejected(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = _event(store, b"payload", 1)

    class EvilRaw(RawEventV0):
        pass

    evil = BaseModel.model_construct.__func__(EvilRaw, **event.model_dump(mode="python"))
    with pytest.raises((ValueError, ValidationError)):
        RawManifestEntryV0.bind(
            schema_version="0.1.0",
            segment_id=SEGMENT,
            entry_index=0,
            previous_entry_hash="0" * 64,
            raw_event=evil,
        )
