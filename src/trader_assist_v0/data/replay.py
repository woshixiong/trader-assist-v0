from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

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
    read_manifest_entries,
)
from trader_assist_v0.data.source_catalog import SOURCE_CATALOG_VERSION


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _all_referenced_payloads(store: BronzeStore) -> tuple[set[str], set[str]]:
    references: set[str] = set()
    reasons: set[str] = set()
    manifests_root = store.path("manifests")
    if not manifests_root.exists():
        return references, reasons
    for manifest_path in manifests_root.rglob("*.jsonl"):
        try:
            resolved = manifest_path.resolve(strict=True)
            resolved.relative_to(store.root)
            entries = read_manifest_entries(manifest_path)
        except (OSError, ValueError, BronzeIntegrityError) as exc:
            reasons.add(f"INVALID_MANIFEST:{type(exc).__name__}")
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
        manifest_path = store.manifest_path(manifest_date, segment_id)
    except (ValueError, PathConfinementError):
        reasons.add("MANIFEST_PATH_ESCAPE")
        manifest_path = store.root / "invalid-manifest-path"

    if not manifest_path.exists():
        reasons.add("MISSING_MANIFEST")
    else:
        try:
            raw_manifest = manifest_path.read_bytes()
            if raw_manifest and not raw_manifest.endswith(b"\n"):
                partial_manifest_count = 1
                reasons.add("PARTIAL_MANIFEST")
            else:
                entries = read_manifest_entries(manifest_path)
        except PathConfinementError:
            reasons.add("MANIFEST_PATH_ESCAPE")
        except BronzeIntegrityError:
            reasons.add("INVALID_MANIFEST")
        except OSError:
            reasons.add("MANIFEST_READ_ERROR")

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
            payload_path = store.path(event.payload_ref)
        except PathConfinementError:
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_PATH_ESCAPE")
            continue
        if payload_path.is_symlink():
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_SYMLINK")
            continue
        if not payload_path.exists():
            missing_payload_count += 1
            reasons.add("MISSING_PAYLOAD")
            continue
        if not payload_path.is_file():
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_NOT_REGULAR_FILE")
            continue
        if payload_path.stat().st_size != event.payload_size_bytes:
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_SIZE_MISMATCH")
            continue
        if _file_sha256(payload_path) != event.payload_sha256:
            corrupt_payload_count += 1
            reasons.add("PAYLOAD_HASH_MISMATCH")

    terminal_hash = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
    if expected_terminal_hash is not None and terminal_hash != expected_terminal_hash:
        reasons.add("TERMINAL_HASH_MISMATCH")

    referenced_payloads, global_manifest_reasons = _all_referenced_payloads(store)
    reasons.update(global_manifest_reasons)
    try:
        all_payloads = store.payload_refs()
    except (PathConfinementError, BronzeIntegrityError):
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
