from __future__ import annotations

import gc
import json
import multiprocessing as mp
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)
    for index, payload in enumerate(payloads, start=1):
        writer.append(make_event(store, payload, sequence=index))
    checkpoint = writer.finalize()
    return store, checkpoint


def _try_manifest_writer(root: str, manifest_date: date, segment_id: str, queue) -> None:
    candidate_store = BronzeStore(Path(root))
    try:
        writer = ManifestWriter(
            candidate_store,
            manifest_date=manifest_date,
            segment_id=segment_id,
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)
    writer.append(make_event(store))
    assert (
        replay_segment(store, manifest_date=DAY, segment_id=SEGMENT).status
        is ReplayStatusV0.FAIL
    )
    writer.close()

    empty = ManifestWriter(store, manifest_date=DAY, segment_id="segment-empty")
    empty.close()
    report = replay_segment(store, manifest_date=DAY, segment_id="segment-empty")
    assert report.status is ReplayStatusV0.FAIL
    assert "MISSING_CHECKPOINT" in report.reason_codes


def test_zero_entry_finalized_segment_passes(tmp_path):
    store = BronzeStore(tmp_path / "root")
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-zero")
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
        ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)


def test_same_slot_same_event_cross_segment_global_idempotent(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    one = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")
    assert one.append(event).disposition is AppendDisposition.APPENDED
    one.finalize()
    two = ManifestWriter(store, manifest_date=DAY, segment_id="segment-two")
    result = two.append(event)
    assert result.disposition is AppendDisposition.IDEMPOTENT
    assert read_manifest_entries(store, DAY, "segment-two") == ()
    two.finalize()


def test_same_slot_different_event_cross_segment_conflict(tmp_path):
    store = BronzeStore(tmp_path / "root")
    one = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")
    one.append(make_event(store, b"one", sequence=1))
    one.close()
    two = ManifestWriter(store, manifest_date=DAY, segment_id="segment-two")
    with pytest.raises(ObservationConflictError):
        two.append(make_event(store, b"two", sequence=1))
    two.close()


def test_cross_date_same_source_event_id_idempotent(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    one = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")
    one.append(event)
    one.close()
    later = date(2026, 7, 8)
    two = ManifestWriter(store, manifest_date=later, segment_id="segment-two")
    assert two.append(event).disposition is AppendDisposition.IDEMPOTENT
    assert read_manifest_entries(store, later, "segment-two") == ()
    two.close()




def test_scan_append_critical_section_cannot_split_on_marker_replacement(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"one", sequence=1)
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")
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
        ManifestWriter(
            store,
            manifest_date=date(2026, 7, 8),
            segment_id="segment-two",
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")

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

    contender = ManifestWriter(
        store,
        manifest_date=date(2026, 7, 8),
        segment_id="segment-two",
    )
    with pytest.raises(ObservationConflictError):
        contender.append(make_event(store, b"two", sequence=1))
    contender.close()
    assert len(read_manifest_entries(store, DAY, "segment-one")) == 1
    assert read_manifest_entries(store, date(2026, 7, 8), "segment-two") == ()


def test_root_wide_authority_same_event_is_idempotent_after_waiting_writer(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")

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
    contender = ManifestWriter(
        store,
        manifest_date=date(2026, 7, 8),
        segment_id="segment-two",
    )
    assert contender.append(event).disposition is AppendDisposition.IDEMPOTENT
    contender.close()


def test_corrupt_other_manifest_blocks_new_append(tmp_path):
    store = BronzeStore(tmp_path / "root")
    first = ManifestWriter(store, manifest_date=DAY, segment_id="segment-one")
    first.append(make_event(store, b"one", sequence=1))
    first.close()
    path = store.path(store.manifest_ref(DAY, "segment-one"))
    path.write_bytes(path.read_bytes()[:-1])
    second = ManifestWriter(store, manifest_date=DAY, segment_id="segment-two")
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
    assert not store.path(store.global_authority_lock_ref()).exists()
    lock.release()




@pytest.mark.parametrize("failure_point", ["fstat", "stat", "constructor"])
def test_post_flock_acquire_failures_release_authority_without_path_cleanup(
    tmp_path, monkeypatch, failure_point
):
    store = BronzeStore(tmp_path / "root")
    legacy = store.path(store.global_authority_lock_ref())
    legacy.write_text("replacement-token\n", encoding="utf-8")
    real_fstat = bronze_module.os.fstat
    real_stat = bronze_module.os.stat
    real_init = OwnedLock.__init__

    if failure_point == "fstat":
        monkeypatch.setattr(
            bronze_module.os,
            "fstat",
            lambda fd: (_ for _ in ()).throw(OSError("injected fstat failure")),
        )
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

    with pytest.raises(OSError):
        OwnedLock.acquire(store, store.global_authority_lock_ref())

    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    monkeypatch.setattr(bronze_module.os, "stat", real_stat)
    monkeypatch.setattr(OwnedLock, "__init__", real_init)
    replacement = OwnedLock.acquire(store, store.global_authority_lock_ref())
    replacement.release()
    assert legacy.read_text(encoding="utf-8") == "replacement-token\n"


def test_descriptor_identity_mismatch_is_terminal_and_closes_fd(tmp_path, monkeypatch):
    store = BronzeStore(tmp_path / "root")
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    before = _fd_count()
    real_fstat = bronze_module.os.fstat
    failed = False

    def fail_once(fd):
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected post-flock identity failure")
        return real_fstat(fd)

    monkeypatch.setattr(bronze_module.os, "fstat", fail_once)
    with pytest.raises(OSError, match="injected post-flock identity failure"):
        OwnedLock.acquire(store, store.global_authority_lock_ref())
    monkeypatch.setattr(bronze_module.os, "fstat", real_fstat)
    replacement = OwnedLock.acquire(store, store.global_authority_lock_ref())
    replacement.release()
    gc.collect()
    assert _fd_count() <= before + 1


def test_release_verify_to_unlock_race_never_deletes_replacement_root(
    tmp_path, monkeypatch
):
    store = BronzeStore(tmp_path / "root")
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
    lock.release()
    with pytest.raises(LockOwnershipError, match="already released"):
        lock.release()
    assert legacy.read_text(encoding="utf-8") == "replacement-token\n"


def test_repeated_acquire_failures_do_not_leak_descriptors(tmp_path, monkeypatch):
    store = BronzeStore(tmp_path / "root")
    before = _fd_count()
    real_fstat = bronze_module.os.fstat

    def fail(fd):
        raise OSError("injected identity failure")

    monkeypatch.setattr(bronze_module.os, "fstat", fail)
    for _ in range(20):
        with pytest.raises(OSError, match="injected identity failure"):
            OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-fork")
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
    writer = ManifestWriter(store, manifest_date=DAY, segment_id="segment-fork2")
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
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
    lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
    read_pipe, write_pipe = _os.pipe()
    pid = _os.fork()
    if pid == 0:
        _os.close(read_pipe)
        import time as _time
        _time.sleep(0.3)
        try:
            lock.authority_fd
            _os.write(write_pipe, b"CHILD_GOT_FD")
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
        new_lock = OwnedLock.acquire(store, store.global_authority_lock_ref())
        new_lock.release()