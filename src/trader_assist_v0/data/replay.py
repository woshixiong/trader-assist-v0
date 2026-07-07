from __future__ import annotations

from datetime import date, datetime

from trader_assist_v0.contracts.events import (
    MANIFEST_GENESIS_HASH,
    BronzeReplayReportV0,
    RawEventV0,
    RawManifestCheckpointV0,
    RawManifestEntryV0,
    ReplayStatusV0,
)
from trader_assist_v0.contracts.source_catalog import SOURCE_CATALOG_VERSION
from trader_assist_v0.data.bronze import (
    BronzeIntegrityError,
    BronzeStore,
    PathConfinementError,
    parse_checkpoint_bytes,
    parse_manifest_bytes,
    read_manifest_checkpoint,
    read_manifest_entries,
    scan_global_observation_authority,
    verify_checkpoint_against_entries,
)


def _all_referenced_payloads(store: BronzeStore) -> tuple[set[str], set[str]]:
    references: set[str] = set()
    reasons: set[str] = set()
    try:
        manifests = store.manifest_files()
    except (OSError, ValueError, BronzeIntegrityError, PathConfinementError):
        return references, {"MANIFEST_TREE_INVALID"}
    for manifest_date, segment_id in manifests:
        try:
            entries = read_manifest_entries(store, manifest_date, segment_id)
            checkpoint: RawManifestCheckpointV0 | None
            try:
                checkpoint = read_manifest_checkpoint(store, manifest_date, segment_id)
            except FileNotFoundError:
                checkpoint = None
            if checkpoint is not None:
                verify_checkpoint_against_entries(checkpoint, entries)
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
    if source_catalog_version != SOURCE_CATALOG_VERSION:
        raise ValueError("A0 replay supports only the frozen source catalog version")

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

    checkpoint: RawManifestCheckpointV0 | None = None
    try:
        raw_checkpoint = store.read_checkpoint_bytes(manifest_date, segment_id)
    except FileNotFoundError:
        reasons.add("MISSING_CHECKPOINT")
    except (PathConfinementError, OSError):
        reasons.add("CHECKPOINT_PATH_OR_READ_FAILURE")
    else:
        try:
            checkpoint = parse_checkpoint_bytes(
                raw_checkpoint,
                manifest_date=manifest_date,
                segment_id=segment_id,
            )
        except BronzeIntegrityError:
            reasons.add("INVALID_CHECKPOINT")

    if checkpoint is not None:
        try:
            verify_checkpoint_against_entries(checkpoint, entries)
        except BronzeIntegrityError:
            reasons.add("CHECKPOINT_MANIFEST_MISMATCH")

    payload_hashes: set[str] = set()
    slot_map: dict[str, tuple[str, str]] = {}
    event_id_map: dict[str, RawManifestEntryV0] = {}
    receive_times: list[datetime] = []

    for entry in entries:
        event = entry.raw_event
        try:
            exact_event = RawEventV0.model_validate(event)
        except (ValueError, TypeError):
            reasons.add("RAW_EVENT_CATALOG_AUTHORITY_INVALID")
            continue
        previous = slot_map.get(exact_event.observation_slot_id)
        current = (exact_event.source_event_id, exact_event.payload_sha256)
        if previous is not None:
            if previous == current:
                idempotent_event_observations += 1
                reasons.add("DUPLICATE_AUTHORITATIVE_OBSERVATION")
            else:
                conflicting_event_identities += 1
                reasons.add("CONFLICTING_EVENT_IDENTITY")
        else:
            slot_map[exact_event.observation_slot_id] = current
        previous_event_id = event_id_map.get(exact_event.source_event_id)
        if previous_event_id is not None:
            idempotent_event_observations += 1
            reasons.add("DUPLICATE_SOURCE_EVENT_ID")
        else:
            event_id_map[exact_event.source_event_id] = entry

        payload_hashes.add(exact_event.payload_sha256)
        receive_times.append(exact_event.collector_receive_time)
        try:
            store.verify_payload(exact_event)
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

    terminal_hash = entries[-1].entry_hash if entries else MANIFEST_GENESIS_HASH
    if expected_terminal_hash is not None and terminal_hash != expected_terminal_hash:
        reasons.add("EXTRA_EXPECTED_TERMINAL_HASH_MISMATCH")

    try:
        scan_global_observation_authority(store)
    except (BronzeIntegrityError, OSError, PathConfinementError, ValueError):
        reasons.add("GLOBAL_OBSERVATION_AUTHORITY_INVALID")
        conflicting_event_identities += 1

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
        manifest_segment_id=segment_id,
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
