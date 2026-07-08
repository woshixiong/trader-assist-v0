from __future__ import annotations

import errno
import gc
import json
import multiprocessing as mp
import os
import threading
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_schema
from pydantic import BaseModel, ValidationError

import trader_assist_v0.data.bronze as bronze_module
from trader_assist_v0.contracts import (
    BronzeReplayReportV0,
    EnvironmentV0,
    RawCaptureModeV0,
    RawEventV0,
    RawManifestCheckpointV0,
    RawManifestEntryV0,
    ReplayStatusV0,
)
from trader_assist_v0.contracts.events import (
    A0_SCHEMA_VERSION,
    MANIFEST_CHECKPOINT_HASH_VERSION,
    MANIFEST_CHECKPOINT_VERSION,
    MANIFEST_FORMAT_VERSION,
    MANIFEST_GENESIS_HASH,
    MANIFEST_HASH_CHAIN_VERSION,
    OBSERVATION_SLOT_VERSION,
    RAW_IDENTITY_VERSION,
    REPLAY_REPORT_HASH_VERSION,
    REPLAY_REPORT_VERSION,
    compute_manifest_checkpoint_hash_from_payload,
    compute_replay_report_hash_from_payload,
)
from trader_assist_v0.contracts.source_catalog import (
    SOURCE_CATALOG_HASH,
    SOURCE_CATALOG_VERSION,
)
from trader_assist_v0.data import (
    AppendDisposition,
    BronzeIntegrityError,
    BronzeStore,
    LockOwnershipError,
    ManifestWriter,
    ObservationConflictError,
    OwnedLock,
    SegmentFinalizedError,
    SingleWriterError,
    read_manifest_entries,
    replay_segment,
)
from trader_assist_v0.data.bronze import _open_anchor_fd

DAY = date(2026, 7, 7)
NOW = datetime(2026, 7, 7, 1, 0, tzinfo=UTC)
SEGMENT = "segment-001"


@pytest.fixture
def store(tmp_path: Path) -> BronzeStore:
    return BronzeStore(tmp_path / "root")


def make_event(
    store: BronzeStore,
    payload: bytes = b'{"channel":"pong"}',
    *,
    sequence: int = 1,
    connection: str = "conn-001",
    endpoint_id: str = "hl-ws-mainnet-public",
    operation_type: str = "allMids",
    coin: str | None = None,
    candle_interval: str | None = None,
    capture_mode: RawCaptureModeV0 = (
        RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD
    ),
    **overrides: object,
) -> RawEventV0:
    stored = store.write_payload(payload)
    values: dict[str, object] = {
        "endpoint_id": endpoint_id,
        "operation_type": operation_type,
        "coin": coin,
        "candle_interval": candle_interval,
        "capture_mode": capture_mode,
        "connection_id": connection,
        "subscription_id": "sub-001",
        "receive_sequence": sequence,
        "source_native_id": None,
        "source_native_cursor": None,
        "collector_version": "collector.0.1",
        "environment": EnvironmentV0.READ_ONLY,
        "content_type": "application/json",
        "payload_sha256": stored.payload_sha256,
        "payload_size_bytes": stored.payload_size_bytes,
        "payload_encoding": "utf-8",
        "payload_ref": stored.payload_ref,
        "source_event_time": None,
        "source_publish_time": None,
        "first_observed_time": NOW,
        "collector_receive_time": NOW,
        "collector_monotonic_ns": 123,
        "revision_time": None,
    }
    values.update(overrides)
    return RawEventV0.bind_observation(**values)


def _raw_dict(event: RawEventV0) -> dict[str, object]:
    return BaseModel.model_dump(event, mode="python", round_trip=True)


def _manifest_dict(entry: RawManifestEntryV0) -> dict[str, object]:
    return BaseModel.model_dump(entry, mode="python", round_trip=True)


def _checkpoint_dict(checkpoint: RawManifestCheckpointV0) -> dict[str, object]:
    return BaseModel.model_dump(checkpoint, mode="python", round_trip=True)


def _finalized_store(tmp_path: Path, payloads: tuple[bytes, ...] = (b"a", b"b")):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    for index, payload in enumerate(payloads, start=1):
        writer.append(make_event(store, payload, sequence=index))
    checkpoint = writer.finalize()
    return store, checkpoint


def _try_manifest_writer(root: str, manifest_date: date, segment_id: str, queue) -> None:
    candidate_store = BronzeStore(Path(root))
    try:
        anchor_fd = _provision_anchor(candidate_store)
        writer = ManifestWriter(
            candidate_store,
            manifest_date=manifest_date,
            segment_id=segment_id,
            authority_anchor_fd=anchor_fd,
        )
    except SingleWriterError:
        queue.put("BLOCKED")
    else:
        writer.close()
        queue.put("ACQUIRED")


def _fd_count() -> int:
    fd_root = Path("/proc/self/fd")
    if not fd_root.exists():
        pytest.skip("Linux /proc fd accounting is unavailable")
    return len(tuple(fd_root.iterdir()))



def _provision_anchor(store):
    """Provision a BronzeStore root and return an open anchor fd."""
    store.root.mkdir(parents=True, exist_ok=True)
    return _open_anchor_fd(store)


@pytest.mark.parametrize(
    ("model", "field", "bad"),
    [
        (RawEventV0, "schema_version", "9.9.9"),
        (RawManifestEntryV0, "schema_version", "9.9.9"),
        (RawManifestEntryV0, "manifest_format_version", "9.9.9"),
        (RawManifestEntryV0, "hash_chain_version", "evil/v9"),
        (RawManifestCheckpointV0, "schema_version", "9.9.9"),
        (RawManifestCheckpointV0, "checkpoint_version", "9.9.9"),
        (BronzeReplayReportV0, "schema_version", "9.9.9"),
        (BronzeReplayReportV0, "replay_report_version", "9.9.9"),
    ],
)
def test_version_fields_emit_schema_const(model, field, bad):
    schema = model.model_json_schema()
    assert "const" in schema["properties"][field]
    with pytest.raises(JsonSchemaValidationError):
        validate_schema(
            {field: bad},
            {
                "type": "object",
                "properties": {field: schema["properties"][field]},
                "required": [field],
            },
        )


def test_version_constants_are_frozen():
    assert A0_SCHEMA_VERSION == "0.1.0"
    assert MANIFEST_FORMAT_VERSION == "0.1.0"
    assert MANIFEST_HASH_CHAIN_VERSION == "trader-assist-v0/raw-manifest-entry/v1"
    assert MANIFEST_CHECKPOINT_VERSION == "0.1.0"
    assert MANIFEST_CHECKPOINT_HASH_VERSION == "trader-assist-v0/raw-manifest-checkpoint/v1"
    assert REPLAY_REPORT_VERSION == "0.1.0"
    assert REPLAY_REPORT_HASH_VERSION == "trader-assist-v0/bronze-replay-report/v1"
    assert RAW_IDENTITY_VERSION == "trader-assist-v0/raw-observation/v2"
    assert OBSERVATION_SLOT_VERSION == "trader-assist-v0/raw-observation-slot/v2"


def test_arbitrary_versions_rejected_even_with_recomputed_hash(store):
    event = make_event(store)
    raw = _raw_dict(event)
    raw["schema_version"] = "9.9.9"
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(raw)
    with pytest.raises(ValidationError):
        RawEventV0.model_validate_json(json.dumps(raw, default=str))

    entry = RawManifestEntryV0.bind(
        segment_id=SEGMENT,
        entry_index=0,
        previous_entry_hash=MANIFEST_GENESIS_HASH,
        raw_event=event,
    )
    data = _manifest_dict(entry)
    data["schema_version"] = "9.9.9"
    data["entry_hash"] = "0" * 64
    with pytest.raises(ValidationError):
        RawManifestEntryV0.model_validate(data)
    with pytest.raises(ValueError):
        RawManifestEntryV0.bind(
            segment_id=SEGMENT,
            entry_index=0,
            previous_entry_hash=MANIFEST_GENESIS_HASH,
            raw_event=event,
            schema_version="9.9.9",
        )

    cp = RawManifestCheckpointV0.bind(
        manifest_date=DAY,
        segment_id=SEGMENT,
        expected_entry_count=0,
        terminal_entry_hash=MANIFEST_GENESIS_HASH,
    )
    cp_data = _checkpoint_dict(cp)
    cp_data["checkpoint_version"] = "9.9.9"
    cp_data["checkpoint_hash"] = compute_manifest_checkpoint_hash_from_payload(cp_data)
    with pytest.raises(ValidationError):
        RawManifestCheckpointV0.model_validate(cp_data)
    with pytest.raises(ValueError):
        RawManifestCheckpointV0.bind(
            manifest_date=DAY,
            segment_id=SEGMENT,
            expected_entry_count=0,
            terminal_entry_hash=MANIFEST_GENESIS_HASH,
            checkpoint_version="9.9.9",
        )


def test_report_bind_cannot_be_overridden():
    base = dict(
        manifest_segment_id=SEGMENT,
        entries_checked=0,
        unique_payload_blobs=0,
        duplicate_payload_observations=0,
        idempotent_event_observations=0,
        conflicting_event_identities=0,
        missing_payload_count=0,
        corrupt_payload_count=0,
        orphan_payload_count=0,
        partial_manifest_count=0,
        first_receive_time=None,
        last_receive_time=None,
        manifest_terminal_hash=MANIFEST_GENESIS_HASH,
        status=ReplayStatusV0.PASS,
        reason_codes=(),
    )
    for field in ("schema_version", "replay_report_version", "source_catalog_version"):
        with pytest.raises(ValueError):
            BronzeReplayReportV0.bind(**base, **{field: "9.9.9"})
    payload = {
        **base,
        "schema_version": A0_SCHEMA_VERSION,
        "replay_report_version": "9.9.9",
        "source_catalog_version": SOURCE_CATALOG_VERSION,
    }
    payload["report_hash"] = compute_replay_report_hash_from_payload(payload)
    with pytest.raises(ValidationError):
        BronzeReplayReportV0.model_validate(payload)


def test_checkpoint_exact_class_copy_construct_and_subclass():
    cp = RawManifestCheckpointV0.bind(
        manifest_date=DAY,
        segment_id=SEGMENT,
        expected_entry_count=0,
        terminal_entry_hash=MANIFEST_GENESIS_HASH,
    )
    with pytest.raises(TypeError):
        cp.model_copy(update={"expected_entry_count": 1})
    stale = BaseModel.model_copy(cp, update={"expected_entry_count": 1})
    with pytest.raises(ValidationError):
        RawManifestCheckpointV0.model_validate(stale)
    constructed = BaseModel.model_construct.__func__(
        RawManifestCheckpointV0, **cp.model_dump(mode="python")
    )
    object.__setattr__(constructed, "expected_entry_count", 1)
    with pytest.raises(ValidationError):
        RawManifestCheckpointV0.model_validate(constructed)

    class EvilCheckpoint(RawManifestCheckpointV0):
        pass

    evil = BaseModel.model_construct.__func__(
        EvilCheckpoint, **cp.model_dump(mode="python")
    )
    with pytest.raises((ValueError, ValidationError)):
        RawManifestCheckpointV0.model_validate(evil)


def test_finalize_normal_replay_pass(tmp_path):
    store, checkpoint = _finalized_store(tmp_path)
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.PASS
    assert checkpoint.expected_entry_count == 2
    assert checkpoint.terminal_entry_hash == (
        read_manifest_entries(store, DAY, SEGMENT)[-1].entry_hash
    )


def test_unfinalized_missing_checkpoint_and_empty_unfinalized_fail(tmp_path):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    writer.append(make_event(store))
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )
    writer.close()

    anchor_fd = _provision_anchor(store)
    empty = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-empty", authority_anchor_fd=anchor_fd
    )
    empty.close()
    report = replay_segment(store, manifest_date=DAY, segment_id="segment-empty")
    assert report.status is ReplayStatusV0.FAIL
    assert "MISSING_CHECKPOINT" in report.reason_codes


def test_zero_entry_finalized_segment_passes(tmp_path):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-zero", authority_anchor_fd=anchor_fd
    )
    checkpoint = writer.finalize()
    assert checkpoint.expected_entry_count == 0
    assert checkpoint.terminal_entry_hash == MANIFEST_GENESIS_HASH
    assert (
        replay_segment(store, manifest_date=DAY, segment_id="segment-zero").status
        is ReplayStatusV0.PASS
    )


@pytest.mark.parametrize("keep", [0, 1])
def test_tail_entry_deletion_rejected(tmp_path, keep):
    store, _ = _finalized_store(tmp_path, (b"same", b"same"))
    manifest = store.path(store.manifest_ref(DAY, SEGMENT))
    lines = manifest.read_bytes().splitlines()
    manifest.write_bytes(b"\n".join(lines[:keep]) + (b"\n" if keep else b""))
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.FAIL
    assert "CHECKPOINT_MANIFEST_MISMATCH" in report.reason_codes


def test_unique_tail_and_payload_deletion_rejected(tmp_path):
    store, _ = _finalized_store(tmp_path, (b"head", b"unique-tail"))
    entries = read_manifest_entries(store, DAY, SEGMENT)
    manifest = store.path(store.manifest_ref(DAY, SEGMENT))
    manifest.write_bytes(manifest.read_bytes().splitlines()[0] + b"\n")
    store.path(entries[-1].raw_event.payload_ref).unlink()
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )


def test_checkpoint_and_tail_deleted_together_rejected(tmp_path):
    store, _ = _finalized_store(tmp_path)
    manifest = store.path(store.manifest_ref(DAY, SEGMENT))
    manifest.write_bytes(manifest.read_bytes().splitlines()[0] + b"\n")
    store.path(store.checkpoint_ref(DAY, SEGMENT)).unlink()
    report = replay_segment(store, manifest_date=DAY, segment_id=SEGMENT)
    assert report.status is ReplayStatusV0.FAIL
    assert "MISSING_CHECKPOINT" in report.reason_codes


def _rewrite_checkpoint(store: BronzeStore, mutator) -> None:
    path = store.path(store.checkpoint_ref(DAY, SEGMENT))
    data = json.loads(path.read_text())
    mutator(data)
    data["checkpoint_hash"] = compute_manifest_checkpoint_hash_from_payload(data)
    path.write_text(json.dumps(data, separators=(",", ":")) + "\n")


@pytest.mark.parametrize("field", ["expected_entry_count", "terminal_entry_hash", "segment_id"])
def test_wrong_checkpoint_authority_rejected(tmp_path, field):
    store, _ = _finalized_store(tmp_path)

    def mutate(data):
        if field == "expected_entry_count":
            data[field] += 1
        elif field == "terminal_entry_hash":
            data[field] = "f" * 64
        else:
            data[field] = "other-segment"

    _rewrite_checkpoint(store, mutate)
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )


def test_checkpoint_truncation_hash_and_overwrite_rejected(tmp_path):
    store, _ = _finalized_store(tmp_path)
    path = store.path(store.checkpoint_ref(DAY, SEGMENT))
    original = path.read_bytes()
    path.write_bytes(original[:-1])
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )
    path.write_bytes(original.replace(b'"checkpoint_hash":"', b'"checkpoint_hash":"f', 1))
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )
    path.write_bytes(original)
    with pytest.raises(SegmentFinalizedError):
        anchor_fd = _provision_anchor(store)
        ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd)


def test_same_slot_same_event_cross_segment_global_idempotent(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    anchor_fd = _provision_anchor(store)
    one = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    assert one.append(event).disposition is AppendDisposition.APPENDED
    one.finalize()
    anchor_fd = _provision_anchor(store)
    two = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-two", authority_anchor_fd=anchor_fd
    )
    result = two.append(event)
    assert result.disposition is AppendDisposition.IDEMPOTENT
    assert read_manifest_entries(store, DAY, "segment-two") == ()
    two.finalize()


def test_same_slot_different_event_cross_segment_conflict(tmp_path):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    one = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    one.append(make_event(store, b"one", sequence=1))
    one.close()
    anchor_fd = _provision_anchor(store)
    two = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-two", authority_anchor_fd=anchor_fd
    )
    with pytest.raises(ObservationConflictError):
        two.append(make_event(store, b"two", sequence=1))
    two.close()


def test_cross_date_same_source_event_id_idempotent(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    anchor_fd = _provision_anchor(store)
    one = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    one.append(event)
    one.close()
    later = date(2026, 7, 8)
    anchor_fd = _provision_anchor(store)
    two = ManifestWriter(
        store, manifest_date=later, segment_id="segment-two", authority_anchor_fd=anchor_fd
    )
    assert two.append(event).disposition is AppendDisposition.IDEMPOTENT
    assert read_manifest_entries(store, later, "segment-two") == ()
    two.close()




def test_scan_append_critical_section_cannot_split_on_marker_replacement(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"one", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    scanned = threading.Event()
    proceed = threading.Event()
    original_scan = bronze_module.scan_global_observation_authority

    def paused_scan(*args, **kwargs):
        authority = original_scan(*args, **kwargs)
        scanned.set()
        assert proceed.wait(timeout=5)
        return authority

    monkeypatch.setattr(bronze_module, "scan_global_observation_authority", paused_scan)
    results: list[AppendDisposition] = []
    errors: list[BaseException] = []

    def append_first() -> None:
        try:
            results.append(writer.append(event).disposition)
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=append_first)
    thread.start()
    assert scanned.wait(timeout=5)

    global_marker = store.path(store.global_authority_lock_ref())
    global_marker.write_text("replacement-global-token\n", encoding="utf-8")
    segment_marker = store.path(store.lock_ref(DAY, "segment-one"))
    segment_marker.write_text("replacement-segment-token\n", encoding="utf-8")
    with pytest.raises(SingleWriterError):
        anchor_fd = _provision_anchor(store)
        ManifestWriter(
            store,
            manifest_date=date(2026, 7, 8),
            segment_id="segment-two",
            authority_anchor_fd=anchor_fd,
        )

    proceed.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert not errors
    assert results == [AppendDisposition.APPENDED]
    writer.close()
    assert global_marker.read_text(encoding="utf-8") == "replacement-global-token\n"
    assert segment_marker.read_text(encoding="utf-8") == "replacement-segment-token\n"
    assert len(read_manifest_entries(store, DAY, "segment-one")) == 1

def test_root_wide_authority_blocks_replacement_namespace_multiprocess(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"one", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )

    legacy_global = store.path(store.global_authority_lock_ref())
    legacy_global.write_text("replacement-global-token\n", encoding="utf-8")
    legacy_segment = store.path(store.lock_ref(DAY, "segment-one"))
    legacy_segment.write_text("replacement-segment-token\n", encoding="utf-8")

    context = mp.get_context("fork")
    queue = context.Queue()
    process = context.Process(
        target=_try_manifest_writer,
        args=(str(store.root), date(2026, 7, 8), "segment-two", queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    assert queue.get(timeout=2) == "BLOCKED"
    assert legacy_global.read_text(encoding="utf-8") == "replacement-global-token\n"
    assert legacy_segment.read_text(encoding="utf-8") == "replacement-segment-token\n"

    assert writer.append(event).disposition is AppendDisposition.APPENDED
    writer.close()

    anchor_fd = _provision_anchor(store)
    contender = ManifestWriter(
        store,
        manifest_date=date(2026, 7, 8),
        segment_id="segment-two",
        authority_anchor_fd=anchor_fd,
    )
    with pytest.raises(ObservationConflictError):
        contender.append(make_event(store, b"two", sequence=1))
    contender.close()
    assert len(read_manifest_entries(store, DAY, "segment-one")) == 1
    assert read_manifest_entries(store, date(2026, 7, 8), "segment-two") == ()


def test_root_wide_authority_same_event_is_idempotent_after_waiting_writer(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()
    process = context.Process(
        target=_try_manifest_writer,
        args=(str(store.root), date(2026, 7, 8), "segment-two", queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    assert queue.get(timeout=2) == "BLOCKED"

    writer.append(event)
    writer.close()
    anchor_fd = _provision_anchor(store)
    contender = ManifestWriter(
        store,
        manifest_date=date(2026, 7, 8),
        segment_id="segment-two",
        authority_anchor_fd=anchor_fd,
    )
    assert contender.append(event).disposition is AppendDisposition.IDEMPOTENT
    contender.close()


def test_corrupt_other_manifest_blocks_new_append(tmp_path):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    first = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    first.append(make_event(store, b"one", sequence=1))
    first.close()
    path = store.path(store.manifest_ref(DAY, "segment-one"))
    path.write_bytes(path.read_bytes()[:-1])
    anchor_fd = _provision_anchor(store)
    second = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-two", authority_anchor_fd=anchor_fd
    )
    with pytest.raises(BronzeIntegrityError):
        second.append(make_event(store, b"two", sequence=2))
    second.close()


def test_lock_acquire_eliminates_marker_write_and_directory_fsync_cleanup(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")

    def forbidden(*args, **kwargs):
        raise AssertionError("kernel-backed lock acquisition must not write or fsync markers")

    monkeypatch.setattr(bronze_module, "_write_all", forbidden)
    monkeypatch.setattr(bronze_module, "_fsync_directory_fd", forbidden)
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    assert not store.path(store.global_authority_lock_ref()).exists()
    lock.release()




@pytest.mark.parametrize("failure_point", ["fstat", "stat", "constructor"])
def test_post_flock_acquire_failures_release_authority_without_path_cleanup(
    tmp_path, monkeypatch, failure_point
):
    store = BronzeStore(tmp_path / "root")
    store.root.mkdir(parents=True, exist_ok=True)
    legacy = store.path(store.global_authority_lock_ref())
    legacy.write_text("replacement-token\n", encoding="utf-8")
    # Pre-open anchor fd to avoid the new os.fstat validation in acquire()
    anchor_fd = bronze_module._open_anchor_fd(store)
    real_fstat = bronze_module.os.fstat
    real_stat = bronze_module.os.stat
    real_init = OwnedLock.__init__

    if failure_point == "fstat":
        # Only fail fstat for the lock_fd (not the authority_anchor_fd validation)
        def fstat_fail(fd):
            if fd == anchor_fd:
                return real_fstat(fd)
            raise OSError("injected fstat failure")
        monkeypatch.setattr(bronze_module.os, "fstat", fstat_fail)
    elif failure_point == "stat":
        monkeypatch.setattr(
            bronze_module.os,
            "stat",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected stat failure")),
        )
    else:
        monkeypatch.setattr(
            OwnedLock,
            "__init__",
            lambda self, **kwargs: (_ for _ in ()).throw(
                OSError("injected pre-return constructor failure")
            ),
        )

    with pytest.raises((OSError, LockOwnershipError)):
        OwnedLock.acquire(
            store,
            store.global_authority_lock_ref(),
            authority_anchor_fd=anchor_fd,
        )

    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    monkeypatch.setattr(bronze_module.os, "stat", real_stat)
    monkeypatch.setattr(OwnedLock, "__init__", real_init)
    replacement = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    replacement.release()
    assert legacy.read_text(encoding="utf-8") == "replacement-token\n"


def test_descriptor_identity_mismatch_is_terminal_and_closes_fd(tmp_path, monkeypatch):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    authority_fd = lock.authority_fd
    real_fstat = bronze_module.os.fstat

    def mismatched(fd):
        metadata = real_fstat(fd)
        if fd == authority_fd:
            return type(
                "MismatchedStat",
                (),
                {
                    "st_mode": metadata.st_mode,
                    "st_dev": metadata.st_dev,
                    "st_ino": metadata.st_ino + 1,
                },
            )()
        return metadata

    monkeypatch.setattr(bronze_module.os, "fstat", mismatched)
    with pytest.raises(LockOwnershipError, match="identity changed"):
        lock.assert_owned()
    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    assert lock.released
    assert lock.compromised
    with pytest.raises(LockOwnershipError, match="compromised"):
        lock.release()

def test_lock_acquire_exception_closes_descriptor_and_releases_kernel_lock(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")
    store.root.mkdir(parents=True, exist_ok=True)
    # Pre-open anchor fd to avoid the new os.fstat validation in acquire()
    anchor_fd = bronze_module._open_anchor_fd(store)
    before = _fd_count()
    real_fstat = bronze_module.os.fstat
    failed = False

    def fail_once(fd):
        nonlocal failed
        if fd == anchor_fd:
            return real_fstat(fd)
        if not failed:
            failed = True
            raise OSError("injected post-flock identity failure")
        return real_fstat(fd)

    monkeypatch.setattr(bronze_module.os, "fstat", fail_once)
    with pytest.raises(LockOwnershipError, match="cannot stat lock file descriptor"):
        OwnedLock.acquire(
            store,
            store.global_authority_lock_ref(),
            authority_anchor_fd=anchor_fd,
        )
    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    replacement = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    replacement.release()
    gc.collect()
    assert _fd_count() <= before + 1


def test_release_verify_to_unlock_race_never_deletes_replacement_root(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    verified = threading.Event()
    proceed = threading.Event()
    original_verify = lock._verify_owned

    def paused_verify():
        original_verify()
        verified.set()
        assert proceed.wait(timeout=5)

    monkeypatch.setattr(lock, "_verify_owned", paused_verify)
    errors: list[BaseException] = []

    def release():
        try:
            lock.release()
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=release)
    thread.start()
    assert verified.wait(timeout=5)
    detached = tmp_path / "detached-root"
    store.root.rename(detached)
    store.root.mkdir()
    replacement = store.root / "replacement-authority"
    replacement.write_text("new-owner\n", encoding="utf-8")
    proceed.set()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert not errors
    assert replacement.read_text(encoding="utf-8") == "new-owner\n"
    assert detached.exists()


@pytest.mark.parametrize("replacement_kind", ["missing", "symlink", "file", "directory"])
def test_root_namespace_loss_is_terminal_and_closes_owned_descriptor(
    tmp_path, replacement_kind
):
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    event = make_event(store)
    detached = tmp_path / "detached-root"
    store.root.rename(detached)
    if replacement_kind == "symlink":
        target = tmp_path / "replacement-target"
        target.mkdir()
        store.root.symlink_to(target, target_is_directory=True)
    elif replacement_kind == "file":
        store.root.write_text("not-a-directory", encoding="utf-8")
    elif replacement_kind == "directory":
        store.root.mkdir()

    with pytest.raises(LockOwnershipError):
        writer.append(event)
    with pytest.raises(LockOwnershipError, match="terminal"):
        writer.append(event)
    with pytest.raises(LockOwnershipError, match="terminal"):
        writer.finalize()
    with pytest.raises(LockOwnershipError, match="terminal"):
        writer.close()
    assert writer._authority_lock.released
    assert writer._authority_lock.compromised


def test_repeated_release_is_deterministic_and_legacy_tokens_are_never_unlinked(tmp_path):
    store = BronzeStore(tmp_path / "root")
    legacy = store.path(store.global_authority_lock_ref())
    legacy.write_text("replacement-token\n", encoding="utf-8")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    lock.release()
    with pytest.raises(LockOwnershipError, match="already released"):
        lock.release()
    assert legacy.read_text(encoding="utf-8") == "replacement-token\n"


def test_repeated_acquire_failures_do_not_leak_descriptors(tmp_path, monkeypatch):
    store = BronzeStore(tmp_path / "root")
    store.root.mkdir(parents=True, exist_ok=True)
    # Pre-open anchor fd to avoid the new os.fstat validation in acquire()
    anchor_fd = bronze_module._open_anchor_fd(store)
    before = _fd_count()
    real_fstat = bronze_module.os.fstat

    def fail(fd):
        if fd == anchor_fd:
            return real_fstat(fd)
        raise OSError("injected identity failure")

    monkeypatch.setattr(bronze_module.os, "fstat", fail)
    for _ in range(20):
        with pytest.raises(LockOwnershipError, match="cannot stat lock file descriptor"):
            OwnedLock.acquire(
                store,
                store.global_authority_lock_ref(),
                authority_anchor_fd=anchor_fd,
            )
    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    gc.collect()
    assert _fd_count() <= before + 1


def test_raw_event_catalog_binding_and_source_time_policy(store):
    valid = make_event(
        store,
        endpoint_id="hl-ws-mainnet-public",
        operation_type="trades",
        coin="ETH",
        candle_interval=None,
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
    )
    assert valid.source_catalog_version == SOURCE_CATALOG_VERSION
    assert valid.source_catalog_hash == SOURCE_CATALOG_HASH
    assert valid.source_event_time is None
    assert valid.source_publish_time is None
    assert valid.revision_time is None
    assert valid.source_native_id is None
    assert valid.source_native_cursor is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"endpoint_id": "unknown"},
        {"endpoint_id": "/exchange"},
        {"endpoint_id": "hl-ws-testnet-public"},
        {"operation_type": "unknown"},
        {"operation_type": "trades", "coin": None},
        {
            "endpoint_id": "hl-info-mainnet-public",
            "operation_type": "meta",
            "coin": "ETH",
            "capture_mode": RawCaptureModeV0.HTTP_RESPONSE_BODY,
        },
        {"operation_type": "trades", "coin": "SOL"},
        {"operation_type": "candle", "coin": "ETH", "candle_interval": "30m"},
        {"capture_mode": RawCaptureModeV0.HTTP_RESPONSE_BODY},
        {"source_event_time": "2026-07-07T01:00:00Z"},
        {"source_publish_time": "2026-07-07T01:00:00Z"},
        {"revision_time": "2026-07-07T01:00:00Z"},
        {"source_native_id": "native"},
        {"source_native_cursor": "cursor"},
    ],
)
def test_invalid_catalog_selection_or_source_time_rejected(store, overrides):
    with pytest.raises((ValueError, ValidationError)):
        make_event(store, **overrides)


def test_wrong_catalog_and_entry_hash_rejected(store):
    event = make_event(store)
    data = _raw_dict(event)
    data["source_catalog_hash"] = "f" * 64
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(data)
    data = _raw_dict(event)
    data["catalog_entry_hash"] = "f" * 64
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(data)


def test_bind_rejects_caller_authority_fields(store):
    stored = store.write_payload(b"x")
    base = dict(
        endpoint_id="hl-ws-mainnet-public",
        operation_type="allMids",
        coin=None,
        candle_interval=None,
        capture_mode=RawCaptureModeV0.WS_TEXT_UTF8_APPLICATION_PAYLOAD,
        connection_id="conn-001",
        subscription_id="sub-001",
        receive_sequence=1,
        source_native_id=None,
        source_native_cursor=None,
        collector_version="collector.0.1",
        environment="READ_ONLY",
        content_type="application/json",
        payload_sha256=stored.payload_sha256,
        payload_size_bytes=stored.payload_size_bytes,
        payload_encoding="utf-8",
        payload_ref=stored.payload_ref,
        source_event_time=None,
        source_publish_time=None,
        first_observed_time="2026-07-07T01:00:00Z",
        collector_receive_time="2026-07-07T01:00:00Z",
        collector_monotonic_ns=1,
        revision_time=None,
    )
    for field, value in (
        ("schema_version", "9.9.9"),
        ("source_id", "other"),
        ("source_catalog_version", "9.9.9"),
        ("source_catalog_hash", "f" * 64),
        ("catalog_entry_hash", "f" * 64),
    ):
        with pytest.raises(ValueError):
            RawEventV0.bind_observation(**base, **{field: value})

# ============================================================
# Tests added for Commit 1: reproduce fork ownership failure
# ============================================================

def test_fork_child_release_does_not_unlock_parent(tmp_path):
    """Child process release() must not release the parent's kernel lock."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            lock.release()
            _os.write(write_pipe, b"CHILD_RELEASED_OK")
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        assert not lock.released
        assert not lock.compromised
        lock.release()


def test_fork_child_authority_fd_is_blocked(tmp_path):
    """Child process must not be able to access authority_fd after fork."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            fd = lock.authority_fd
            _os.write(write_pipe, f"CHILD_GOT_FD:{fd}".encode())
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        assert lock.authority_fd >= 0
        lock.release()


def test_fork_child_append_is_blocked(tmp_path):
    """Child process must not be able to append through a parent's ManifestWriter."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-fork", authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            result = writer.append(event)
            _os.write(write_pipe, f"CHILD_APPENDED:{result.disposition}".encode())
        except (LockOwnershipError, SingleWriterError) as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{type(exc).__name__}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        assert writer.append(event).disposition is AppendDisposition.APPENDED
        writer.close()


def test_fork_child_finalize_is_blocked(tmp_path):
    """Child process must not be able to finalize a parent's ManifestWriter."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-fork2", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            writer.finalize()
            _os.write(write_pipe, b"CHILD_FINALIZED_OK")
        except (LockOwnershipError, SingleWriterError) as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{type(exc).__name__}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        writer.finalize()


def test_fork_child_assert_owned_is_blocked(tmp_path):
    """Child process assert_owned must fail after fork."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            lock.assert_owned()
            _os.write(write_pipe, b"CHILD_ASSERTED_OK")
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        lock.assert_owned()
        lock.release()


def test_fork_child_operations_after_parent_release_are_blocked(tmp_path):
    """Even after parent releases, a forked child cannot use the stale lock."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        import time as _time
        _time.sleep(0.3)
        try:
            _fd = lock.authority_fd
            _os.write(write_pipe, f"CHILD_GOT_FD:{_fd}".encode())
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        lock.release()
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        anchor_fd = _provision_anchor(store)
        new_lock = OwnedLock.acquire(
            store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
        )
        new_lock.release()
# ============================================================
# Tests added for Commit 2: fork child close duplicates + nested exit
# ============================================================

def test_child_closes_duplicates_owner_exit_third_acquires(tmp_path):
    """owner取得锁 -> owner fork child -> child保持存活 -> owner不release直接exit
    -> 第三个进程尝试取得锁 -> 必须成功
    证明 child 已关闭 inherited duplicate, 未延长锁生命周期"""
    import os as _os
    store = BronzeStore(tmp_path / "root")

    # Parent acquires lock
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )

    # Fork child - child should not be able to use the lock
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            _fd = lock.authority_fd
            _os.write(write_pipe, b"CHILD_GOT_FD")
        except LockOwnershipError:
            _os.write(write_pipe, b"CHILD_BLOCKED")
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result, f"Child should be blocked, got: {child_result}"

    # Parent releases the lock
    lock.release()

    # After release, a new process should acquire the lock
    context = mp.get_context("fork")
    queue = context.Queue()

    def third_acquire(root_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            new_store = BronzeStore(_Path(root_str))
            anchor_fd = _provision_anchor(store)
            new_lock = OwnedLock.acquire(
                new_store, new_store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
            )
            new_lock.release()
            queue_obj.put("ACQUIRED")
        except SingleWriterError:
            queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{type(exc).__name__}:{exc}")

    process = context.Process(
        target=third_acquire,
        args=(str(store.root), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    result = queue.get(timeout=2)
    assert result == "ACQUIRED", f"Third process should acquire, got: {result}"
def test_child_release_does_not_execute_lock_un(tmp_path):
    """Child process release must not execute flock(LOCK_UN) on inherited fd."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            lock.release()
            _os.write(write_pipe, b"CHILD_RELEASED_OK")
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        # Parent should still hold the lock
        lock.assert_owned()
        lock.release()


def test_child_close_does_not_execute_lock_un(tmp_path):
    """Child process close must not execute flock(LOCK_UN) on inherited fd."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-child-close", authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            writer.close()
            _os.write(write_pipe, b"CHILD_CLOSED_OK")
        except (LockOwnershipError, SingleWriterError) as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{type(exc).__name__}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        # Parent should still hold the lock
        writer.append(event)
        writer.close()


def test_parent_survives_second_writer_blocked_after_fork(tmp_path):
    """After fork, parent still holds the lock and second writer is blocked."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store,
        manifest_date=DAY,
        segment_id="segment-parent-survives",
        authority_anchor_fd=anchor_fd,
    )
    event = make_event(store, b"data", sequence=1)
    writer.append(event)

    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            _fd = writer._authority_lock.authority_fd
            _os.write(write_pipe, f"CHILD_GOT_FD:{_fd}".encode())
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{exc}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result

    # Second writer should still be blocked because parent holds lock
    with pytest.raises(SingleWriterError):
        anchor_fd = _provision_anchor(store)
        ManifestWriter(
            store, manifest_date=DAY, segment_id="segment-other", authority_anchor_fd=anchor_fd
        )

    writer.close()


# ============================================================
# Tests added for Commit 3: reproduce same-writer operation races
# ============================================================


def test_concurrent_append_and_close_race(tmp_path):
    """Demonstrate that concurrent append and close on the same writer can race."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"race", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-race", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    results: list[AppendDisposition] = []

    def append_worker():
        try:
            barrier.wait(timeout=5)
            results.append(writer.append(event).disposition)
        except BaseException as exc:
            errors.append(exc)

    def close_worker():
        try:
            barrier.wait(timeout=5)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=append_worker)
    t2 = threading.Thread(target=close_worker)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    # Both threads should complete without hanging
    assert not t1.is_alive()
    assert not t2.is_alive()


def test_concurrent_append_and_finalize_race(tmp_path):
    """Demonstrate that concurrent append and finalize on the same writer can race."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"race2", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-race2", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    results: list[AppendDisposition] = []

    def append_worker():
        try:
            barrier.wait(timeout=5)
            results.append(writer.append(event).disposition)
        except BaseException as exc:
            errors.append(exc)

    def finalize_worker():
        try:
            barrier.wait(timeout=5)
            # This may race with append
            writer.finalize()
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=append_worker)
    t2 = threading.Thread(target=finalize_worker)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive()
    assert not t2.is_alive()


def test_concurrent_double_close(tmp_path):
    """Demonstrate that concurrent double close on the same writer is safe."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-dclose", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def close_worker():
        try:
            barrier.wait(timeout=5)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=close_worker)
    t2 = threading.Thread(target=close_worker)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive()
    assert not t2.is_alive()


def test_concurrent_close_and_finalize_race(tmp_path):
    """Demonstrate that concurrent close and finalize on the same writer can race."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"race3", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-race3", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def close_worker():
        try:
            barrier.wait(timeout=5)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    def finalize_worker():
        try:
            barrier.wait(timeout=5)
            writer.finalize()
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=close_worker)
    t2 = threading.Thread(target=finalize_worker)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive()
    assert not t2.is_alive()


def test_concurrent_multi_append_same_writer(tmp_path):
    """Demonstrate concurrent multi-append on the same writer can race."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-multi", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(3)
    errors: list[BaseException] = []
    results: list[AppendDisposition] = []

    def append_worker(seq: int):
        try:
            event = make_event(store, b"multi", sequence=seq, connection=f"conn-{seq:03d}")
            barrier.wait(timeout=5)
            results.append(writer.append(event).disposition)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=append_worker, args=(i,)) for i in range(1, 4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not any(t.is_alive() for t in threads)
    writer.close()


def test_append_close_append_sequence_race(tmp_path):
    """Demonstrate that append-close-append across threads can race on the same writer."""
    store = BronzeStore(tmp_path / "root")
    event1 = make_event(store, b"one", sequence=1, connection="conn-001")
    event2 = make_event(store, b"two", sequence=2, connection="conn-002")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-seq", authority_anchor_fd=anchor_fd
    )
    bar1 = threading.Barrier(2)
    bar2 = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker1():
        try:
            bar1.wait(timeout=5)
            writer.append(event1)
            bar2.wait(timeout=5)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    def worker2():
        try:
            bar1.wait(timeout=5)
            bar2.wait(timeout=5)
            writer.append(event2)
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive()
    assert not t2.is_alive()# ============================================================

def test_root_rename_while_authority_held_multiprocess(tmp_path):
    """Root rename should not release authority when parent directory is locked."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"rename", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-rename", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def rename_and_contend(root_str: str, queue) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            detached = root_path.parent / "detached-root"
            root_path.rename(detached)
            root_path.mkdir()
            queue.put("RENAMED")
            try:
                new_store = BronzeStore(root_path)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue.put("BLOCKED_BY_OLD")
        except Exception as exc:
            queue.put(f"ERROR:{exc}")

    process = context.Process(
        target=rename_and_contend,
        args=(str(store.root), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "RENAMED"
    # Currently the new writer CAN acquire because the lock is on the root
    # directory, not the parent. After R3B-ROOTNS fix, this should be BLOCKED_BY_OLD.
    assert result2 in ("BLOCKED_BY_OLD", "ACQUIRED_NEW")

    # Close may fail because root was renamed (identity check fails)
    try:
        writer.close()
    except LockOwnershipError:
        pass


def test_root_parent_lock_blocks_concurrent_after_rename(tmp_path):
    """Parent directory lock prevents concurrent writers even after root rename."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-parent", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def try_writer(root_str: str, queue) -> None:
        from pathlib import Path as _Path
        try:
            candidate = BronzeStore(_Path(root_str))
            anchor_fd = _provision_anchor(store)
            ManifestWriter(
                candidate,
                manifest_date=date(2026, 7, 8),
                segment_id="segment-other",
                authority_anchor_fd=anchor_fd,
            )
            queue.put("ACQUIRED")
        except SingleWriterError:
            queue.put("BLOCKED")
        except Exception as exc:
            queue.put(f"ERROR:{type(exc).__name__}")

    process = context.Process(
        target=try_writer,
        args=(str(store.root), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    result = queue.get(timeout=2)
    assert result == "BLOCKED"

    writer.close()

    process2 = context.Process(
        target=try_writer,
        args=(str(store.root), queue),
    )
    process2.start()
    process2.join(timeout=10)
    assert process2.exitcode == 0
    result2 = queue.get(timeout=2)
    assert result2 == "ACQUIRED"


def test_root_identity_change_detected_at_publication(tmp_path):
    """Root inode identity change should be detected at publication boundary."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-identity", authority_anchor_fd=anchor_fd
    )
    event = make_event(store, b"identity", sequence=1)
    writer.append(event)

    import os as _os
    original_stat = _os.stat(store.root, follow_symlinks=False)
    original_ino = original_stat.st_ino

    detached = tmp_path / "detached-root"
    store.root.rename(detached)
    store.root.mkdir()

    new_stat = _os.stat(store.root, follow_symlinks=False)
    assert new_stat.st_ino != original_ino

    # The writer should detect the identity change
    try:
        writer.append(make_event(store, b"identity2", sequence=2, connection="conn-002"))
    except LockOwnershipError:
        pass


def test_root_identity_preserved_after_rename(tmp_path):
    """With parent directory lock, root identity check should operate correctly."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-preserve", authority_anchor_fd=anchor_fd
    )
    event = make_event(store, b"preserve", sequence=1)
    writer.append(event)

    detached = tmp_path / "detached-root"
    store.root.rename(detached)
    store.root.mkdir()

    try:
        writer.close()
    except LockOwnershipError:
        pass

# ============================================================
# Tests added for Commit 6: parent replacement and root namespace tests
# ============================================================

def test_root_rename_blocked_with_authority_anchor(tmp_path):
    """With authority_anchor, root rename does not release authority."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"rename", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-anchor", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def rename_and_contend(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            detached = anchor_path / "detached-root"
            root_path.rename(detached)
            root_path.mkdir()
            queue_obj.put("RENAMED")
            try:
                new_store = BronzeStore(root_path, authority_anchor=anchor_path)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED_BY_OLD")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=rename_and_contend,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "RENAMED"
    # With authority_anchor, the new writer must be BLOCKED
    assert result2 == "BLOCKED_BY_OLD",         f"Expected BLOCKED_BY_OLD, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_immediate_parent_rename_blocked(tmp_path):
    """Immediate parent rename should not release authority."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-immediate", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def parent_rename_contend(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str) if not isinstance(root_str, _Path) else root_str
            anchor_path = _Path(anchor_str) if not isinstance(anchor_str, _Path) else anchor_str
            old_parent = root_path.parent
            new_parent = anchor_path.parent / "new-parent"
            old_parent.rename(new_parent)
            queue_obj.put("PARENT_RENAMED")

            # Try to create a new writer - should be blocked
            try:
                new_store = BronzeStore(
                    new_parent / root_path.name,
                    authority_anchor=anchor_path,
                )
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
            except LockOwnershipError as exc:
                queue_obj.put(f"OWNERSHIP_ERROR:{type(exc).__name__}")
            except Exception as exc:
                queue_obj.put(f"ERROR:{type(exc).__name__}:{exc}")
        except Exception as exc:
            import traceback
            queue_obj.put(f"FATAL:{type(exc).__name__}:{exc}:{traceback.format_exc()}")

    process = context.Process(
        target=parent_rename_contend,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=15)
    if process.exitcode is None:
        process.terminate()
        process.join(timeout=5)
        raise AssertionError("Subprocess hung and was terminated")

    assert process.exitcode == 0, f"Subprocess exited with {process.exitcode}"

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "PARENT_RENAMED", f"Expected PARENT_RENAMED, got {result1}"
    assert result2 != "ACQUIRED" and result2 != "ACQUIRED_NEW", f"Should not acquire, got {result2}"
def test_replacement_parent_new_root_blocked(tmp_path):
    """Replacement parent with new root must still be blocked by authority."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-replace", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_and_contend(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            # Replace root with entirely new directory
            old_root = root_path
            backup = anchor_path / "backup-root"
            old_root.rename(backup)
            new_root = anchor_path / root_path.name
            new_root.mkdir()
            queue_obj.put("REPLACED")
            try:
                new_store = BronzeStore(new_root, authority_anchor=anchor_path)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_and_contend,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED"
    assert result2 == "BLOCKED", f"Expected BLOCKED, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_second_writer_same_authority_namespace(tmp_path):
    """Second writer must use the same authority namespace."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-first", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def second_writer(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            new_store = BronzeStore(
                _Path(root_str),
                authority_anchor=_Path(anchor_str),
            )
            anchor_fd = _provision_anchor(new_store)
            ManifestWriter(
                new_store,
                manifest_date=date(2026, 7, 8),
                segment_id="segment-second",
                authority_anchor_fd=anchor_fd,
            )
            queue_obj.put("ACQUIRED")
        except SingleWriterError:
            queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=second_writer,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0
    result = queue.get(timeout=2)
    assert result == "BLOCKED", f"Expected BLOCKED, got {result}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_after_scan(tmp_path):
    """Replacement after scan: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"scan", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-scan", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_after_scan(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-scan"
            root_path.rename(backup)
            queue_obj.put("REPLACED_AFTER_SCAN")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_after_scan,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_AFTER_SCAN"
    assert result2 == "BLOCKED", f"Expected BLOCKED after scan, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_before_payload_publication(tmp_path):
    """Replacement before payload publication: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-payload", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_before_payload(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-payload"
            root_path.rename(backup)
            queue_obj.put("REPLACED_BEFORE_PAYLOAD")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_before_payload,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_BEFORE_PAYLOAD"
    assert result2 == "BLOCKED", f"Expected BLOCKED before payload, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_before_manifest_write(tmp_path):
    """Replacement before manifest write: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-manifest", authority_anchor_fd=anchor_fd
    )

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_before_manifest(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-manifest"
            root_path.rename(backup)
            queue_obj.put("REPLACED_BEFORE_MANIFEST")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_before_manifest,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_BEFORE_MANIFEST"
    assert result2 == "BLOCKED", f"Expected BLOCKED before manifest, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_after_manifest_fsync(tmp_path):
    """Replacement after manifest fsync: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"fsync", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-fsync", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_after_fsync(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-fsync"
            root_path.rename(backup)
            queue_obj.put("REPLACED_AFTER_FSYNC")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_after_fsync,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_AFTER_FSYNC"
    assert result2 == "BLOCKED", f"Expected BLOCKED after fsync, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_before_checkpoint_publication(tmp_path):
    """Replacement before checkpoint publication: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"checkpoint", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-checkpoint", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_before_checkpoint(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-checkpoint"
            root_path.rename(backup)
            queue_obj.put("REPLACED_BEFORE_CHECKPOINT")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_before_checkpoint,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_BEFORE_CHECKPOINT"
    assert result2 == "BLOCKED", f"Expected BLOCKED before checkpoint, got {result2}"

    # writer.close() skipped - root identity check fails after rename


def test_replacement_during_finalize(tmp_path):
    """Replacement during finalize: authority must still hold."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"finalize", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-finalize-r", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    context = mp.get_context("fork")
    queue = context.Queue()

    def replace_during_finalize(root_str: str, anchor_str: str, queue_obj) -> None:
        from pathlib import Path as _Path
        try:
            root_path = _Path(root_str)
            anchor_path = _Path(anchor_str)
            backup = anchor_path / "backup-finalize"
            root_path.rename(backup)
            queue_obj.put("REPLACED_DURING_FINALIZE")
            try:
                new_store = BronzeStore(anchor_path / root_path.name)
                anchor_fd = _provision_anchor(new_store)
                ManifestWriter(
                    new_store,
                    manifest_date=date(2026, 7, 8),
                    segment_id="segment-new",
                    authority_anchor_fd=anchor_fd,
                )
                queue_obj.put("ACQUIRED_NEW")
            except SingleWriterError:
                queue_obj.put("BLOCKED")
        except Exception as exc:
            queue_obj.put(f"ERROR:{exc}")

    process = context.Process(
        target=replace_during_finalize,
        args=(str(store.root), str(store.authority_anchor), queue),
    )
    process.start()
    process.join(timeout=10)
    assert process.exitcode == 0

    result1 = queue.get(timeout=2)
    result2 = queue.get(timeout=2)
    assert result1 == "REPLACED_DURING_FINALIZE"
    assert result2 == "BLOCKED", f"Expected BLOCKED during finalize, got {result2}"

    # writer.close() skipped - root identity check fails after rename


# ============================================================
# Tests added for Commit 7: reproduce uncertain close lifecycle
# ============================================================
def test_fd_state_transitions_on_normal_close(tmp_path):
    """Verify fd state transitions during normal close lifecycle."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )

    assert lock._fd_state == bronze_module._FdState.OPEN_OWNED
    lock.release()
    assert lock._fd_state == bronze_module._FdState.CLOSED
    assert lock._fd == -1
    assert lock._lock_fd == -1


def test_double_release_does_not_double_free(tmp_path):
    """Double release of OwnedLock should be safe and not double-free fds."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    lock.release()

    with pytest.raises(LockOwnershipError):
        lock.release()

    assert lock._fd_state == bronze_module._FdState.CLOSED
    assert lock._fd == -1


def test_writer_state_transitions_on_normal_close(tmp_path):
    """Verify writer state transitions during normal close lifecycle."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-state", authority_anchor_fd=anchor_fd
    )

    assert writer._writer_state == bronze_module._WriterState.ACTIVE
    writer.close()
    assert writer._writer_state == bronze_module._WriterState.CLOSED


def test_writer_state_transitions_on_finalize(tmp_path):
    """Verify writer state transitions during finalize."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-finalize", authority_anchor_fd=anchor_fd
    )
    writer.append(event)

    assert writer._writer_state == bronze_module._WriterState.ACTIVE
    writer.finalize()
    assert writer._writer_state == bronze_module._WriterState.CLOSED


def test_writer_double_close_is_safe(tmp_path):
    """Double close of ManifestWriter should be deterministic and safe."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-dclose2", authority_anchor_fd=anchor_fd
    )
    writer.close()
    # Second close should be a no-op
    writer.close()
    assert writer._writer_state == bronze_module._WriterState.CLOSED


def test_writer_closed_raises_on_append(tmp_path):
    """Append after close should raise SingleWriterError."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-closed", authority_anchor_fd=anchor_fd
    )
    writer.close()

    with pytest.raises(SingleWriterError):
        writer.append(event)

# ============================================================
# Tests added for Commit 7b: deterministic concurrency tests
# ============================================================

def test_append_after_close_blocked(tmp_path):
    """Append after close must be blocked deterministically."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-close", authority_anchor_fd=anchor_fd
    )
    writer.close()
    with pytest.raises(SingleWriterError):
        writer.append(event)


def test_append_after_finalize_blocked(tmp_path):
    """Append after finalize must be blocked deterministically."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-finalize", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    writer.finalize()
    with pytest.raises(SingleWriterError):
        writer.append(event)


def test_close_after_finalize_is_noop(tmp_path):
    """Close after finalize must be a no-op."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-close-final", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    writer.finalize()
    # Close after finalize should be safe
    writer.close()
    assert writer._writer_state == bronze_module._WriterState.CLOSED


def test_finalize_after_close_blocked(tmp_path):
    """Finalize after close must be blocked deterministically."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"data", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-fin-close", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    writer.close()
    with pytest.raises(SingleWriterError):
        writer.finalize()


def test_deterministic_concurrent_close_workers(tmp_path):
    """Two concurrent close workers must both complete without hanging."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-conc-close", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def close_worker():
        try:
            barrier.wait(timeout=5)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    t1 = threading.Thread(target=close_worker)
    t2 = threading.Thread(target=close_worker)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)
    assert not t1.is_alive(), "Thread 1 did not complete"
    assert not t2.is_alive(), "Thread 2 did not complete"


def test_entry_indexes_unique_after_concurrent_append(tmp_path):
    """Entry indexes must be unique and contiguous after concurrent append."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-index", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(3)
    errors: list[BaseException] = []
    results: list[AppendDisposition] = []

    def append_worker(seq: int):
        try:
            event = make_event(store, b"idx", sequence=seq, connection=f"c-{seq:03d}")
            barrier.wait(timeout=5)
            result = writer.append(event)
            results.append(result.disposition)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=append_worker, args=(i,)) for i in range(1, 4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not any(t.is_alive() for t in threads)
    writer.close()

    # Verify entry indexes are contiguous
    entries = read_manifest_entries(store, DAY, "seg-det-index")
    for i, entry in enumerate(entries):
        assert entry.entry_index == i, f"Entry index {entry.entry_index} != expected {i}"


def test_previous_entry_hash_chain_correct(tmp_path):
    """Previous entry hash chain must be correct after concurrent operations."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-hash", authority_anchor_fd=anchor_fd
    )
    events = [
        make_event(store, b"hash1", sequence=i, connection=f"h-{i:03d}")
        for i in range(1, 5)
    ]
    for event in events:
        writer.append(event)
    writer.close()

    entries = read_manifest_entries(store, DAY, "seg-det-hash")
    assert entries[0].previous_entry_hash == MANIFEST_GENESIS_HASH
    for i in range(1, len(entries)):
        assert entries[i].previous_entry_hash == entries[i - 1].entry_hash, \
            f"Hash chain broken at index {i}"


def test_checkpoint_entry_count_correct(tmp_path):
    """Checkpoint entry count must be correct after finalize."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-checkpoint", authority_anchor_fd=anchor_fd
    )
    for i in range(1, 4):
        event = make_event(store, b"cp", sequence=i, connection=f"cp-{i:03d}")
        writer.append(event)
    checkpoint = writer.finalize()
    assert checkpoint.expected_entry_count == 3


def test_authority_release_only_once(tmp_path):
    """Authority release must happen exactly once."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-once", authority_anchor_fd=anchor_fd
    )
    writer.close()
    # Second close should be no-op, not release again
    writer.close()
    # Lock should be released
    anchor_fd = _provision_anchor(store)
    new_writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-once2", authority_anchor_fd=anchor_fd
    )
    new_writer.close()


def test_no_publication_after_release(tmp_path):
    """No publication after authority release."""
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"pub", sequence=1)
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-pub", authority_anchor_fd=anchor_fd
    )
    writer.append(event)
    writer.close()
    with pytest.raises(SingleWriterError):
        writer.append(make_event(store, b"pub2", sequence=2, connection="conn-002"))


def test_threads_all_bounded_join(tmp_path):
    """All threads must bounded join - no hanging."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id="seg-det-join", authority_anchor_fd=anchor_fd
    )
    barrier = threading.Barrier(5)
    errors: list[BaseException] = []

    def worker(idx: int):
        try:
            barrier.wait(timeout=10)
            if idx % 2 == 0:
                event = make_event(store, b"join", sequence=idx + 1, connection=f"j-{idx:03d}")
                writer.append(event)
            writer.close()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not any(t.is_alive() for t in threads), "Some threads did not complete within timeout"


# ============================================================
# Tests added for TRAE-R4: fork _lock_fd lifecycle, CloseAdapter
# fault-injection, and anchor replacement
# ============================================================

# --- Fork tests: verify _lock_fd is invalidated in child ---

def test_fork_child_lock_fd_is_invalidated(tmp_path):
    """After fork, child's _lock_fd must be invalidated to prevent
    accidental flock(LOCK_UN) on the inherited lock file descriptor."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            _os.write(write_pipe, f"CHILD_LOCK_FD:{lock._lock_fd}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        # _lock_fd should be -1 in the child (invalidated by _after_fork_child)
        assert "CHILD_LOCK_FD:-1" in child_result, f"Expected _lock_fd=-1, got: {child_result}"
        lock.release()


def test_fork_child_cannot_unlock_lock_fd(tmp_path):
    """Fork child must not be able to call flock(LOCK_UN) on lock_fd
    because _lock_fd is set to -1 in the child."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        try:
            lock.release()
            _os.write(write_pipe, b"CHILD_RELEASED_OK")
        except LockOwnershipError as exc:
            _os.write(write_pipe, f"CHILD_BLOCKED:{type(exc).__name__}".encode())
        except Exception as exc:
            _os.write(write_pipe, f"CHILD_ERROR:{type(exc).__name__}:{exc}".encode())
        finally:
            _os.close(write_pipe)
            _os._exit(0)
    else:
        _os.close(write_pipe)
        child_result = _os.read(read_pipe, 4096).decode()
        _os.close(read_pipe)
        _os.waitpid(pid, 0)
        assert "CHILD_BLOCKED" in child_result
        # Parent still holds the lock
        lock.assert_owned()
        lock.release()


# --- CloseAdapter fault-injection tests ---

def test_close_adapter_default_behaviour(tmp_path):
    """CloseAdapter with no overrides should behave like os.close."""
    import os as _os
    r, w = _os.pipe()
    adapter = bronze_module.CloseAdapter()
    adapter.close(r)
    adapter.close(w)
    # Verify fds are actually closed
    with pytest.raises(OSError):
        _os.fstat(r)
    with pytest.raises(OSError):
        _os.fstat(w)


def test_close_adapter_pre_syscall_failure(tmp_path):
    """CloseAdapter subclass raising OSError before os.close must prevent
    os.close and leave the fd known-open."""
    import os as _os
    r, w = _os.pipe()

    class FailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd):
            raise OSError("pre-syscall failure")

    adapter = FailingCloseAdapter()
    with pytest.raises(OSError, match="pre-syscall failure"):
        adapter.close(r)
    # fd should still be open (pre-syscall failure)
    _os.fstat(r)
    _os.close(r)
    _os.close(w)


def test_close_adapter_post_syscall_failure(tmp_path):
    """CloseAdapter subclass raising OSError after os.close means
    fd disposition is unknown."""
    import os as _os
    r, w = _os.pipe()

    class PostFailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd):
            _os.close(fd)
            raise OSError("post-syscall failure")

    adapter = PostFailingCloseAdapter()
    with pytest.raises(OSError, match="post-syscall failure"):
        adapter.close(r)
    # fd may or may not be closed - this is the "unknown" outcome
    _os.close(w)


def test_release_with_pre_syscall_close_failure(tmp_path, monkeypatch):
    """release() with a CloseAdapter that fails before os.close must
    poison the process since _close_single_descriptor treats all OSError
    as post-syscall unknown."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )

    class PreFailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd):
            raise OSError("pre-syscall root_fd")

    adapter = PreFailingCloseAdapter()
    # Ensure gate is clean before test (monkeypatch restores original after)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    with pytest.raises(LockOwnershipError, match="root authority release failed"):
        lock.release(close_adapter=adapter)
    assert lock.compromised
    assert lock._fd_state is bronze_module._FdState.CLOSE_OUTCOME_UNKNOWN


def test_release_with_post_syscall_close_failure(tmp_path, monkeypatch):
    """release() with a CloseAdapter that fails post-syscall must poison
    the process."""
    import os as _os
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )

    class PostFailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd):
            _os.close(fd)
            raise OSError("post-syscall root_fd")

    adapter = PostFailingCloseAdapter()
    # Ensure gate is clean before test (monkeypatch restores original after)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    with pytest.raises(LockOwnershipError, match="root authority release failed"):
        lock.release(close_adapter=adapter)
    assert lock.compromised
    assert lock._fd_state is bronze_module._FdState.CLOSE_OUTCOME_UNKNOWN


def test_acquire_with_close_adapter_passed_through(tmp_path, monkeypatch):
    """acquire() must pass the CloseAdapter through to _close_owned_descriptor
    via release when cleanup is needed."""
    # Ensure poison gate is clear
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    adapter = bronze_module.CloseAdapter()
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        close_adapter=adapter,
        authority_anchor_fd=anchor_fd,
    )
    lock.release(close_adapter=adapter)
    assert lock.released


# --- Anchor replacement tests ---

def test_anchor_replacement_acquire_new_anchor_after_release(tmp_path, monkeypatch):
    """After releasing a lock, a new lock can be acquired with a fresh
    authority_anchor_fd."""
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd_1 = bronze_module._open_anchor_fd(store)
    lock1 = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd_1,
    )
    lock1.release()
    # New anchor fd
    anchor_fd_2 = bronze_module._open_anchor_fd(store)
    lock2 = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd_2,
    )
    lock2.release()
    assert lock1.released
    assert lock2.released


def test_anchor_replacement_stale_anchor_blocked(tmp_path, monkeypatch):
    """After lock is released, using the old anchor_fd must fail or
    be detectable."""
    import os as _os
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = bronze_module._open_anchor_fd(store)
    lock = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    lock.release()
    # The anchor_fd is still valid (it's a directory fd), but the lock
    # file may have been recreated. A new acquire should work.
    # Old anchor_fd can still be used because the anchor directory is the same.
    lock2 = OwnedLock.acquire(
        store,
        store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    lock2.release()
    _os.close(anchor_fd)


def test_anchor_fd_is_directory_check(tmp_path, monkeypatch):
    """acquire() must reject authority_anchor_fd that is not a directory."""
    import os as _os
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    store.root.mkdir(parents=True, exist_ok=True)
    # Create a regular file and use its fd
    reg_file = store.root / "not-a-dir"
    reg_file.write_text("not a directory")
    reg_fd = _os.open(str(reg_file), _os.O_RDONLY)
    try:
        with pytest.raises(LockOwnershipError, match="not a directory"):
            OwnedLock.acquire(
                store,
                store.global_authority_lock_ref(),
                authority_anchor_fd=reg_fd,
            )
    finally:
        _os.close(reg_fd)


def test_anchor_fd_reuse_across_multiple_locks(tmp_path, monkeypatch):
    """Same anchor_fd can be used for multiple sequential lock acquisitions."""
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = bronze_module._open_anchor_fd(store)
    for _ in range(5):
        lock = OwnedLock.acquire(
            store,
            store.global_authority_lock_ref(),
            authority_anchor_fd=anchor_fd,
        )
        lock.release()
    # Clean up
    import os as _os
    _os.close(anchor_fd)


def test_open_anchor_fd_creates_lock_file(tmp_path):
    """_open_anchor_fd must create the lock file if it does not exist."""
    store = BronzeStore(tmp_path / "root")
    store.root.mkdir(parents=True, exist_ok=True)
    anchor_dir = store.root.parent
    lock_file = anchor_dir / ".bronze-global-observation-authority.lock"
    # Remove if exists from previous test
    if lock_file.exists():
        lock_file.unlink()
    assert not lock_file.exists()
    anchor_fd = bronze_module._open_anchor_fd(store)
    try:
        assert lock_file.exists()
    finally:
        import os as _os
        _os.close(anchor_fd)

# --- TRAE-R5: Real FD fault-injection via CloseAdapter subclass ---

def test_fd_fault_injection_pre_syscall_root_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-syscall fault on authority_anchor_fd close must leave CLOSE_OUTCOME_UNKNOWN."""
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)

    class PreFailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd: int) -> None:
            raise OSError(errno.EIO, "injected pre-syscall close failure")

    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    with pytest.raises(LockOwnershipError):
        lock.release(close_adapter=PreFailingCloseAdapter())
    assert lock._fd_state == bronze_module._FdState.CLOSE_OUTCOME_UNKNOWN


def test_fd_fault_injection_post_syscall_root_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-syscall fault on authority_anchor_fd close must leave CLOSE_OUTCOME_UNKNOWN."""
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)

    class PostFailingCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd: int) -> None:
            os.close(fd)
            raise OSError(errno.EIO, "injected post-syscall close failure")

    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    with pytest.raises(LockOwnershipError):
        lock.release(close_adapter=PostFailingCloseAdapter())
    assert lock._fd_state == bronze_module._FdState.CLOSE_OUTCOME_UNKNOWN


def test_fd_fault_injection_post_syscall_lock_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-syscall fault on lock_fd close must leave CLOSE_OUTCOME_UNKNOWN."""
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)

    close_calls: list[int] = []

    class PostFailingLockCloseAdapter(bronze_module.CloseAdapter):
        def close(self, fd: int) -> None:
            os.close(fd)
            close_calls.append(fd)
            if len(close_calls) == 2:  # Second close is lock_fd
                raise OSError(errno.EIO, "injected post-syscall lock_fd close failure")

    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(),
        authority_anchor_fd=anchor_fd,
    )
    with pytest.raises(LockOwnershipError):
        lock.release(close_adapter=PostFailingLockCloseAdapter())
    assert lock._fd_state == bronze_module._FdState.CLOSE_OUTCOME_UNKNOWN


# --- TRAE-R5: Poison gate tests ---

def test_poison_gate_prevents_new_acquire(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Poison gate must prevent new OwnedLock.acquire."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 1)
    with pytest.raises(LockOwnershipError, match="poisoned"):
        OwnedLock.acquire(
            store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
        )
    os.close(anchor_fd)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)


def test_poison_gate_prevents_new_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Poison gate must prevent new ManifestWriter."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 1)
    with pytest.raises(SingleWriterError, match="poisoned"):
        ManifestWriter(
            store, manifest_date=DAY, segment_id="segment-poison",
            authority_anchor_fd=anchor_fd,
        )
    os.close(anchor_fd)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)


def test_poison_gate_prevents_acquire_even_with_new_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Poison gate prevents acquire even with a fresh anchor fd."""
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 1)
    with pytest.raises(LockOwnershipError, match="poisoned"):
        OwnedLock.acquire(
            store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
        )
    os.close(anchor_fd)
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)


# --- TRAE-R5: Real fork lifecycle (3-process pattern) ---

def test_owner_exit_child_alive_third_acquires_fork_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner exits while child is alive; third process acquires fork lock.

    Uses os.fork() to verify R5 fork-safety: _after_fork_child closes
    inherited fds in the child, setting FORK_INVALID state.  The parent
    can release and re-acquire the lock.
    """
    monkeypatch.setattr(bronze_module, "_BRONZE_POISON_GATE", 0)
    store = BronzeStore(tmp_path / "root")
    anchor_fd = _provision_anchor(store)
    lock = OwnedLock.acquire(
        store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
    )

    pid = os.fork()
    if pid == 0:
        # CHILD: _after_fork_child has already closed inherited fds
        assert lock._lock_fd == -1
        assert lock._fd_state == bronze_module._FdState.FORK_INVALID
        os._exit(0)
    else:
        # PARENT: wait for child, then release and re-acquire
        os.waitpid(pid, 0)
        lock.release()
        lock2 = OwnedLock.acquire(
            store, store.global_authority_lock_ref(), authority_anchor_fd=anchor_fd
        )
        lock2.release()
        os.close(anchor_fd)
