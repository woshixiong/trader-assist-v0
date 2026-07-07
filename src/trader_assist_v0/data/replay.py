from __future__ import annotations

import hashlib
import os
from datetime import date

from trader_assist_v0.contracts.events import (
    MANIFEST_GENESIS_HASH,
    BronzeReplayReportV0,
    RawManifestEntryV0,
    ReplayStatusV0,
)
from trader_assist_v0.data.bronze import (
    BronzeIntegrityError,
    BronzeStore,
    PathConfinementError,
    SingleWriterError,
    _open_verified_at,
    parse_manifest_bytes,
    read_manifest_entries,
)
from trader_assist_v0.data.source_catalog import SOURCE_CATALOG_VERSION


def _payload_file_hash(store: BronzeStore, relative_path: str) -> str:
    parent_fd, filename = store._open_parent(relative_path, create=False)
    try:
        fd = _open_verified_at(parent_fd, filename, os.O_RDONLY, kind="regular")
        try:
            hasher = hashlib.sha256()
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    return hasher.hexdigest()
                hasher.update(chunk)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _all_referenced_payloads(store: BronzeStore) -> tuple[set[str], set[str]]:
    references: set[str] = set()
    reasons: set[str] = set()
    try:
        manifests = store.manifest_files()
    except SingleWriterError:
        return references, {"ACTIVE_OR_STALE_WRITER_LOCK"}
    except (OSError, ValueError, BronzeIntegrityError, PathConfinementError):
        return references, {"MANIFEST_TREE_INVALID"}
    for manifest_date, segment_id in manifests:
        try:
            entries = read_manifest_entries(store, manifest_date, segment_id)
        except (OSError, ValueError, BronzeIntegrityError, PathConfinementError):
            reasons.add("GLOBAL_MANIFEST_INVALID")
            continue
        references.update(entry.raw_event.payload_ref for entry in entries)
    return references, reasons


def replay_segment(
    store: BronzeStore,
    *,
    manifest_date: date,
    segment_id: str,
    source_catalog_version: str = SOURCE_CATALOG_VERSION,
    expected_terminal_hash: str | None = None,
) -> BronzeReplayReportV0:
    reasons: set[str] = set()
    entries: tuple[RawManifestEntryV0, ...] = ()
    partial_manifest_count = 0
    missing_payload_count = 0
    corrupt_payload_count = 0
    conflicting_event_identities = 0
    idempotent_event_observations = 0

    try:
        raw_manifest = store.read_manifest_bytes(manifest_date, segment_id)
    except FileNotFoundError:
        reasons.add("MISSING_MANIFEST")
    except (PathConfinementError, OSError):
        reasons.add("MANIFEST_PATH_OR_READ_FAILURE")
    else:
        if raw_manifest and not raw_manifest.endswith(b"\n"):
            partial_manifest_count = 1
            reasons.add("PARTIAL_MANIFEST")
        else:
            try:
                entries = parse_manifest_bytes(raw_manifest, expected_segment_id=segment_id)
            except BronzeIntegrityError:
                reasons.add("INVALID_MANIFEST")

    payload_hashes: set[str] = set()
    slot_map: dict[str, tuple[str, str]] = {}
    receive_times = []

    for entry in entries:
        event = entry.raw_event
        if event.source_catalog_version != source_catalog_version:
            reasons.add("SOURCE_CATALOG_VERSION_MISMATCH")
        previous = slot_map.get(event.observation_slot_id)
        current = (event.source_event_id, event.payload_sha256)
        if previous is not None:
            if previous == current:
                idempotent_event_observations += 1
                reasons.add("DUPLICATE_AUTHORITATIVE_OBSERVATION")
            else:
                conflicting_event_identities += 1
                reasons.add("CONFLICTING_EVENT_IDENTITY")
        else:
            slot_map[event.observation_slot_id] = current

        payload_hashes.add(event.payload_sha256)
        receive_times.append(event.collector_receive_time)
        try:
            store.verify_payload(event)
        except BronzeIntegrityError as exc:
            if "missing payload" in str(exc):
                missing_payload_count += 1
                reasons.add("MISSING_PAYLOAD")
            else:
                corrupt_payload_count += 1
                reasons.add("CORRUPT_PAYLOAD")
        except (PathConfinementError, OSError):
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_PATH_OR_READ_FAILURE")
        else:
            try:
                if _payload_file_hash(store, event.payload_ref) != event.payload_sha256:
                    corrupt_payload_count += 1
                    reasons.add("PAYLOAD_HASH_MISMATCH")
            except (OSError, PathConfinementError):
                corrupt_payload_count += 1
                reasons.add("PAYLOAD_PATH_OR_READ_FAILURE")

    terminal_hash = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
    if expected_terminal_hash is not None and terminal_hash != expected_terminal_hash:
        reasons.add("TERMINAL_HASH_MISMATCH")

    referenced_payloads, global_manifest_reasons = _all_referenced_payloads(store)
    reasons.update(global_manifest_reasons)
    try:
        all_payloads = store.payload_refs()
    except (PathConfinementError, BronzeIntegrityError, OSError):
        all_payloads = set()
        reasons.add("PAYLOAD_TREE_INVALID")
    orphan_payload_count = len(all_payloads - referenced_payloads)
    if orphan_payload_count:
        reasons.add("ORPHAN_PAYLOAD")

    entries_checked = len(entries)
    duplicate_payload_observations = entries_checked - len(payload_hashes)
    status = ReplayStatusV0.FAIL if reasons else ReplayStatusV0.PASS
    return BronzeReplayReportV0.bind(
        schema_version="0.1.0",
        manifest_segment_id=segment_id,
        source_catalog_version=source_catalog_version,
        entries_checked=entries_checked,
        unique_payload_blobs=len(payload_hashes),
        duplicate_payload_observations=duplicate_payload_observations,
        idempotent_event_observations=idempotent_event_observations,
        conflicting_event_identities=conflicting_event_identities,
        missing_payload_count=missing_payload_count,
        corrupt_payload_count=corrupt_payload_count,
        orphan_payload_count=orphan_payload_count,
        partial_manifest_count=partial_manifest_count,
        first_receive_time=min(receive_times) if receive_times else None,
        last_receive_time=max(receive_times) if receive_times else None,
        manifest_terminal_hash=terminal_hash,
        status=status,
        reason_codes=tuple(sorted(reasons)),
    )
