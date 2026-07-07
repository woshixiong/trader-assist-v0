from __future__ import annotations

import os
from datetime import UTC, date, datetime

import pytest
from pydantic import BaseModel, ValidationError

from trader_assist_v0.contracts import (
    EnvironmentV0,
    RawCaptureModeV0,
    RawEventV0,
    RawManifestEntryV0,
)
from trader_assist_v0.data import (
    SOURCE_CATALOG_VERSION,
    AppendDisposition,
    BronzeIntegrityError,
    BronzeStore,
    ManifestWriter,
    ObservationConflictError,
    PathConfinementError,
    SingleWriterError,
    payload_sha256,
    read_manifest_entries,
)

DAY = date(2026, 7, 7)
NOW = datetime(2026, 7, 7, 1, 0, tzinfo=UTC)
SEGMENT = "segment-001"


def _event(
    store: BronzeStore,
    payload: bytes,
    *,
    sequence: int = 1,
    connection: str = "conn-001",
) -> RawEventV0:
    stored = store.write_payload(payload)
    return RawEventV0.bind_observation(
        schema_version="0.1.0",
        source_id="hyperliquid-public-mainnet",
        source_catalog_version=SOURCE_CATALOG_VERSION,
        endpoint_id="hl-ws-mainnet-public",
        connection_id=connection,
        subscription_id="trades-ETH",
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
        source_event_time=NOW,
        source_publish_time=None,
        first_observed_time=NOW,
        collector_receive_time=NOW,
        collector_monotonic_ns=123,
        revision_time=None,
    )


def test_exact_bytes_and_payload_observation_identity(tmp_path):
    store = BronzeStore(tmp_path / "root")
    compact = b'{"x":1}'
    spaced = b'{ "x": 1 }'
    assert payload_sha256(compact) != payload_sha256(spaced)
    first = _event(store, compact, sequence=1)
    assert first == _event(store, compact, sequence=1)
    second = _event(store, compact, sequence=2)
    assert first.payload_sha256 == second.payload_sha256
    assert first.source_event_id != second.source_event_id
    assert first.observation_slot_id != second.observation_slot_id
    assert store.write_payload(compact).created is False


def test_caller_cannot_forge_authority_ids(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = _event(store, b"x")
    data = event.model_dump(mode="python")
    data["source_event_id"] = "0" * 64
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(data)
    with pytest.raises(ValueError):
        RawEventV0.bind_observation(**data)


def test_manifest_idempotency_conflict_and_single_writer(tmp_path):
    store = BronzeStore(tmp_path / "root")
    first = _event(store, b"one", sequence=1)
    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT) as writer:
        assert writer.append(first).disposition is AppendDisposition.APPENDED
        assert writer.append(first).disposition is AppendDisposition.IDEMPOTENT
        with pytest.raises(SingleWriterError):
            ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)
        with pytest.raises(ObservationConflictError):
            writer.append(_event(store, b"different", sequence=1))
    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT):
        pass


def test_stale_lock_fails_closed(tmp_path):
    store = BronzeStore(tmp_path / "root")
    lock = store.path(store.lock_ref(DAY, SEGMENT))
    lock.parent.mkdir(parents=True)
    lock.write_bytes(b"")
    with pytest.raises(SingleWriterError):
        ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT)


def test_manifest_chain_detects_reorder_deletion_and_insertion(tmp_path):
    store = BronzeStore(tmp_path / "root")
    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT) as writer:
        writer.append(_event(store, b"one", sequence=1))
        writer.append(_event(store, b"two", sequence=2))
    path = store.path(store.manifest_ref(DAY, SEGMENT))
    lines = path.read_bytes().splitlines()
    for mutated in (lines[::-1], lines[1:], [lines[0], lines[0], lines[1]]):
        path.write_bytes(b"\n".join(mutated) + b"\n")
        with pytest.raises(BronzeIntegrityError):
            read_manifest_entries(store, DAY, SEGMENT)
        path.write_bytes(b"\n".join(lines) + b"\n")


def test_partial_and_corrupt_manifest_fail(tmp_path):
    store = BronzeStore(tmp_path / "root")
    with ManifestWriter(store, manifest_date=DAY, segment_id=SEGMENT) as writer:
        writer.append(_event(store, b"one"))
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
def test_path_traversal_rejected(tmp_path, bad):
    with pytest.raises(PathConfinementError):
        BronzeStore(tmp_path / "root").path(bad)


def test_root_and_intermediate_symlink_rejected(tmp_path):
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


def test_payload_and_manifest_symlink_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink unsupported")
    store = BronzeStore(tmp_path / "root")
    event = _event(store, b"x")
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


def test_authority_models_revalidate_copy_construct_and_subclass(tmp_path):
    store = BronzeStore(tmp_path / "root")
    event = _event(store, b"x")
    with pytest.raises(TypeError):
        event.model_copy(update={"receive_sequence": 99})
    stale = BaseModel.model_copy(event, update={"receive_sequence": 99})
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(stale)
    built = BaseModel.model_construct.__func__(
        RawEventV0, **event.model_dump(mode="python")
    )
    object.__setattr__(built, "receive_sequence", 99)
    with pytest.raises(ValidationError):
        RawEventV0.model_validate(built)

    class Evil(RawEventV0):
        pass

    evil = BaseModel.model_construct.__func__(Evil, **event.model_dump(mode="python"))
    with pytest.raises((ValueError, ValidationError)):
        RawEventV0.model_validate(evil)

    entry = RawManifestEntryV0.bind(
        schema_version="0.1.0",
        segment_id=SEGMENT,
        entry_index=0,
        previous_entry_hash="0" * 64,
        raw_event=event,
    )
    stale_entry = BaseModel.model_copy(entry, update={"entry_index": 1})
    with pytest.raises(ValidationError):
        RawManifestEntryV0.model_validate(stale_entry)
