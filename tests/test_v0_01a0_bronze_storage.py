from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from trader_assist_v0.contracts import (
    EnvironmentV0,
    RawCaptureModeV0,
    RawEventV0,
    RawManifestEntryV0,
)
from trader_assist_v0.contracts.events import MANIFEST_GENESIS_HASH
from trader_assist_v0.data import (
    AppendDisposition,
    BronzeIntegrityError,
    BronzeStore,
    ManifestWriter,
    ObservationConflictError,
    PathConfinementError,
    SegmentFinalizedError,
    SingleWriterError,
    read_manifest_entries,
)
from trader_assist_v0.data.bronze import _open_anchor_fd

DAY = date(2026, 7, 7)
NOW = datetime(2026, 7, 7, 1, 0, tzinfo=UTC)
SEGMENT = "segment-001"


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


@pytest.fixture
def store(tmp_path: Path) -> BronzeStore:
    return BronzeStore(tmp_path / "root")


def test_exact_bytes_and_payload_observation_identity(store: BronzeStore) -> None:
    compact = b'{"x":1}'
    spaced = b'{ "x": 1 }'
    first = make_event(store, compact, sequence=1)
    duplicate = make_event(store, compact, sequence=1)
    second_observation = make_event(store, compact, sequence=2)
    different_bytes = make_event(store, spaced, sequence=3)

    assert first == duplicate
    assert first.payload_sha256 == second_observation.payload_sha256
    assert first.source_event_id != second_observation.source_event_id
    assert first.observation_slot_id != second_observation.observation_slot_id
    assert first.payload_sha256 != different_bytes.payload_sha256
    assert store.write_payload(compact).created is False


def test_caller_cannot_forge_authority_ids(store: BronzeStore) -> None:
    event = make_event(store)
    data = event.model_dump(mode="python")
    data["source_event_id"] = "0" * 64
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(data)
    with pytest.raises(ValueError):
        RawEventV0.bind_observation(**data)


def test_manifest_idempotency_conflict_and_finalization(store: BronzeStore) -> None:
    first = make_event(store, b"one", sequence=1)
    anchor_fd = _open_anchor_fd(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    assert writer.append(first).disposition is AppendDisposition.APPENDED
    assert writer.append(first).disposition is AppendDisposition.IDEMPOTENT
    anchor_fd2 = _open_anchor_fd(store)
    try:
        with pytest.raises(SingleWriterError):
            ManifestWriter(
                store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd2
            )
    finally:
        os.close(anchor_fd2)
    with pytest.raises(ObservationConflictError):
        writer.append(make_event(store, b"different", sequence=1))
    writer.finalize()
    with pytest.raises((SingleWriterError, SegmentFinalizedError)):
        writer.append(make_event(store, b"later", sequence=2))
    anchor_fd3 = _open_anchor_fd(store)
    try:
        with pytest.raises(SegmentFinalizedError):
            ManifestWriter(
                store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd3
            )
    finally:
        os.close(anchor_fd3)
    os.close(anchor_fd)


def test_root_wide_single_writer_blocks_different_segments(store: BronzeStore) -> None:
    anchor_fd = _open_anchor_fd(store)
    first = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-one", authority_anchor_fd=anchor_fd
    )
    anchor_fd2 = _open_anchor_fd(store)
    try:
        with pytest.raises(SingleWriterError):
            ManifestWriter(
                store, manifest_date=DAY, segment_id="segment-two", authority_anchor_fd=anchor_fd2
            )
    finally:
        os.close(anchor_fd2)
    first.close()
    os.close(anchor_fd)
    anchor_fd3 = _open_anchor_fd(store)
    second = ManifestWriter(
        store, manifest_date=DAY, segment_id="segment-two", authority_anchor_fd=anchor_fd3
    )
    second.close()
    os.close(anchor_fd3)


def test_legacy_lock_marker_is_inert_and_never_removed(store: BronzeStore) -> None:
    legacy = store.path(store.lock_ref(DAY, SEGMENT))
    legacy.parent.mkdir(parents=True)
    legacy.write_text("stale-or-replacement\n", encoding="utf-8")
    anchor_fd = _open_anchor_fd(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    writer.close()
    os.close(anchor_fd)
    assert legacy.read_text(encoding="utf-8") == "stale-or-replacement\n"


def test_manifest_chain_detects_reorder_deletion_and_insertion(store: BronzeStore) -> None:
    anchor_fd = _open_anchor_fd(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    writer.append(make_event(store, b"one", sequence=1))
    writer.append(make_event(store, b"two", sequence=2))
    writer.close()
    os.close(anchor_fd)

    path = store.path(store.manifest_ref(DAY, SEGMENT))
    lines = path.read_bytes().splitlines()
    mutations = (lines[::-1], lines[1:], [lines[0], lines[0], lines[1]])
    for mutated in mutations:
        path.write_bytes(b"\n".join(mutated) + b"\n")
        with pytest.raises(BronzeIntegrityError):
            read_manifest_entries(store, DAY, SEGMENT)
        path.write_bytes(b"\n".join(lines) + b"\n")


def test_partial_and_corrupt_manifest_fail(store: BronzeStore) -> None:
    anchor_fd = _open_anchor_fd(store)
    writer = ManifestWriter(
        store, manifest_date=DAY, segment_id=SEGMENT, authority_anchor_fd=anchor_fd
    )
    writer.append(make_event(store, b"one"))
    writer.close()
    os.close(anchor_fd)
    path = store.path(store.manifest_ref(DAY, SEGMENT))
    original = path.read_bytes()

    path.write_bytes(original[:-1])
    with pytest.raises(BronzeIntegrityError):
        read_manifest_entries(store, DAY, SEGMENT)
    path.write_bytes(b"{bad}\n")
    with pytest.raises(BronzeIntegrityError):
        read_manifest_entries(store, DAY, SEGMENT)


@pytest.mark.parametrize(
    "bad",
    ["/abs", "../x", "a/../x", "a//x", "a/./x", "C:/x", "a\\x", "a\x00x"],
)
def test_path_traversal_rejected(store: BronzeStore, bad: str) -> None:
    with pytest.raises(PathConfinementError):
        store.path(bad)


def test_root_and_intermediate_symlink_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root_link = tmp_path / "root-link"
    root_link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(PathConfinementError):
        BronzeStore(root_link)

    root = tmp_path / "root"
    root.mkdir()
    (root / "payloads").symlink_to(outside, target_is_directory=True)
    with pytest.raises(PathConfinementError):
        BronzeStore(root).write_payload(b"x")


def test_payload_and_manifest_symlink_rejected(store: BronzeStore, tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlink unsupported")
    event = make_event(store, b"x")
    payload_path = store.path(event.payload_ref)
    payload_path.unlink()
    payload_path.symlink_to(tmp_path / "missing")
    with pytest.raises((PathConfinementError, BronzeIntegrityError)):
        store.verify_payload(event)

    manifest = store.path(store.manifest_ref(DAY, SEGMENT))
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.symlink_to(tmp_path / "missing")
    with pytest.raises((PathConfinementError, BronzeIntegrityError)):
        read_manifest_entries(store, DAY, SEGMENT)


def test_authority_models_revalidate_copy_construct_and_subclass(
    store: BronzeStore,
) -> None:
    event = make_event(store, b"x")
    with pytest.raises(TypeError):
        event.model_copy(update={"receive_sequence": 99})
    stale = BaseModel.model_copy(event, update={"receive_sequence": 99})
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(stale)
    constructed = BaseModel.model_construct.__func__(
        RawEventV0,
        **event.model_dump(mode="python"),
    )
    object.__setattr__(constructed, "receive_sequence", 99)
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(constructed)

    class EvilRawEvent(RawEventV0):
        pass

    evil = BaseModel.model_construct.__func__(
        EvilRawEvent,
        **event.model_dump(mode="python"),
    )
    with pytest.raises((ValueError, ValidationError)):
        RawEventV0.model_validate(evil)

    entry = RawManifestEntryV0.bind(
        segment_id=SEGMENT,
        entry_index=0,
        previous_entry_hash=MANIFEST_GENESIS_HASH,
        raw_event=event,
    )
    stale_entry = BaseModel.model_copy(entry, update={"entry_index": 1})
    with pytest.raises(ValidationError):
        RawManifestEntryV0.model_validate(stale_entry)