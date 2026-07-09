from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

import trader_assist_v0
import trader_assist_v0.data.bronze as bronze_module
from trader_assist_v0.contracts import (
    EnvironmentV0,
    RawCaptureModeV0,
    RawEventV0,
    RawManifestEntryV0,
    ReplayStatusV0,
)
from trader_assist_v0.data import BronzeStore, ManifestWriter, replay_segment
from trader_assist_v0.data.bronze import _test_open_anchor_fd

DAY = date(2026, 7, 7)
NOW = datetime(2026, 7, 7, 1, 0, tzinfo=UTC)
SEGMENT = "segment-001"


def event(store: BronzeStore, sequence: int = 1) -> RawEventV0:
    stored = store.write_payload(b'{"channel":"pong"}')
    return RawEventV0.bind_observation(
        endpoint_id="hl-ws-mainnet-public",
        operation_type="allMids",
        coin=None,
        candle_interval=None,
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id="conn-001",
        subscription_id="all-mids",
        receive_sequence=sequence,
        source_native_id=None,
        source_native_cursor=None,
        collector_version="collector.0.1",
        environment=EnvironmentV0.READ_ONLY,
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


def finalized(root: Path) -> BronzeStore:
    store = BronzeStore(root)
    anchor_fd = _test_open_anchor_fd(store)
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT,
                            authority_anchor_fd=anchor_fd)
    writer.append(event(store, 1))
    writer.append(event(store, 2))
    writer.finalize()
    os.close(anchor_fd)
    return store


def test_replay_pass_and_cross_process_determinism(tmp_path: Path) -> None:
    first_store, second_store = finalized(tmp_path / "a"), finalized(tmp_path / "b")
    first = replay_segment(first_store, manifest_date=DAY, segment_id=SEGMENT)
    second = replay_segment(second_store, manifest_date=DAY, segment_id=SEGMENT)
    assert first.status is ReplayStatusV0.PASS
    assert first.model_dump() == second.model_dump()
    script = (
        "from datetime import date\nfrom pathlib import Path\n"
        "from trader_assist_v0.data import BronzeStore,replay_segment\nimport sys\n"
        "print(replay_segment(BronzeStore(Path(sys.argv[1])),"
        "manifest_date=date(2026,7,7),segment_id='segment-001').report_hash)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(trader_assist_v0.__file__).resolve().parents[1])
    actual = subprocess.check_output(
        [sys.executable, "-c", script, str(first_store.root)], text=True, env=env
    ).strip()
    assert actual == first.report_hash


def test_missing_corrupt_orphan_partial_and_no_network_fail(tmp_path: Path) -> None:
    (tmp_path / "missing").mkdir(parents=True, exist_ok=True)
    missing = replay_segment(
        BronzeStore(tmp_path / "missing"), manifest_date=DAY, segment_id=SEGMENT
    )
    assert missing.status is ReplayStatusV0.FAIL
    assert {"MISSING_MANIFEST", "MISSING_CHECKPOINT"}.issubset(missing.reason_codes)

    store = finalized(tmp_path / "root")
    manifest = store.path(store.manifest_ref(DAY, SEGMENT))
    entry = RawManifestEntryV0.model_validate_json(
        manifest.read_bytes().splitlines()[0]
    )
    payload = store.path(entry.raw_event.payload_ref)
    original = payload.read_bytes()
    payload.unlink()
    assert (
        replay_segment(
            store, manifest_date=DAY, segment_id=SEGMENT
        ).missing_payload_count
        > 0
    )
    payload.write_bytes(b"bad")
    assert (
        replay_segment(
            store, manifest_date=DAY, segment_id=SEGMENT
        ).corrupt_payload_count
        > 0
    )
    payload.write_bytes(original)
    store.write_payload(b"orphan")
    assert (
        replay_segment(
            store, manifest_date=DAY, segment_id=SEGMENT
        ).orphan_payload_count
        > 0
    )

    partial = finalized(tmp_path / "partial")
    path = partial.path(partial.manifest_ref(DAY, SEGMENT))
    path.write_bytes(path.read_bytes()[:-1])
    assert (
        replay_segment(
            partial, manifest_date=DAY, segment_id=SEGMENT
        ).partial_manifest_count
        == 1
    )


def test_short_manifest_write_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = BronzeStore(tmp_path / "root")
    raw = event(store)
    original = bronze_module.os.write

    def short(fd: int, payload: bytes) -> int:
        return original(fd, payload[: max(1, len(payload) // 2)])

    anchor_fd = _test_open_anchor_fd(store)
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT,
                            authority_anchor_fd=anchor_fd)
    monkeypatch.setattr(bronze_module.os, "write", short)
    with pytest.raises(OSError, match="short manifest append"):
        writer.append(raw)
    writer.close()
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.FAIL
    assert report.partial_manifest_count == 1
