from __future__ import annotations

import json
import threading
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_schema
from pydantic import BaseModel, ValidationError
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
        validate_schema({field: bad}, {
            "type": "object",
            "properties": {field: schema["properties"][field]},
            "required": [field],
        })


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
    assert replay_segment(
        store, manifest_date=DAY, segment_id="segment-zero"
    ).status is ReplayStatusV0.PASS


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


def test_concurrent_same_slot_at_most_one_authority(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = make_event(store, b"same", sequence=1)
    writers = [
        ManifestWriter(store, manifest_date=DAY, segment_id="segment-one"),
        ManifestWriter(store, manifest_date=DAY, segment_id="segment-two"),
    ]
    barrier = threading.Barrier(2)
    results = []
    errors = []

    def run(writer):
        try:
            barrier.wait()
            results.append(writer.append(event).disposition)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(writer,)) for writer in writers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for writer in writers:
        writer.close()
    assert not errors
    assert results.count(AppendDisposition.APPENDED) == 1
    assert results.count(AppendDisposition.IDEMPOTENT) == 1
    total = sum(
        len(read_manifest_entries(store, DAY, segment))
        for segment in ("segment-one", "segment-two")
    )
    assert total == 1


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


def test_segment_lock_delete_replace_token_inode_and_symlink_fail_closed(tmp_path):
    store = BronzeStore(tmp_path / "root")
    writer = ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)
    path = store.path(store.lock_ref(DAY, SEGMENT))

    path.unlink()
    with pytest.raises(LockOwnershipError):
        writer.close()

    store2 = BronzeStore(tmp_path / "root2")
    writer2 = ManifestWriter(store2, manifest_date=DAY, segment_id=SEGMENT)
    path2 = store2.path(store2.lock_ref(DAY, SEGMENT))
    path2.unlink()
    path2.write_text("replacement-token\n")
    with pytest.raises(LockOwnershipError):
        writer2.close()
    assert path2.read_text() == "replacement-token\n"

    store3 = BronzeStore(tmp_path / "root3")
    writer3 = ManifestWriter(store3, manifest_date=DAY, segment_id=SEGMENT)
    path3 = store3.path(store3.lock_ref(DAY, SEGMENT))
    path3.write_text("mutated-token\n")
    with pytest.raises(LockOwnershipError):
        writer3.close()
    assert path3.exists()

    store4 = BronzeStore(tmp_path / "root4")
    writer4 = ManifestWriter(store4, manifest_date=DAY, segment_id=SEGMENT)
    path4 = store4.path(store4.lock_ref(DAY, SEGMENT))
    path4.unlink()
    target = tmp_path / "target-lock"
    target.write_text("target")
    path4.symlink_to(target)
    with pytest.raises(LockOwnershipError):
        writer4.close()
    assert path4.is_symlink()


def test_old_lock_does_not_delete_new_owner_lock(tmp_path):
    store = BronzeStore(tmp_path / "root")
    relative = store.global_authority_lock_ref()
    old = OwnedLock.acquire(store, relative)
    path = store.path(relative)
    path.unlink()
    new = OwnedLock.acquire(store, relative)
    with pytest.raises(LockOwnershipError):
        old.release()
    assert path.exists()
    new.release()


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
