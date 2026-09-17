"""Source-bound, rebuildable replay payload bridge over accepted E4 evidence."""

from __future__ import annotations

from collections.abc import Sequence

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
from trader_assist_v0.vnext_g4.contracts import (
    DerivedReplayCacheIdentity,
    EvidenceArtifactHash,
    G4RunManifest,
)

TRANSFORM_VERSION = "E4_ADMITTED_TO_G4_REPLAY_V1"


def build_replay_payload(events: Sequence[AdmittedEvent]) -> bytes:
    """Serialize immutable admitted evidence in its accepted causal order."""
    ordinals = [event.admission_ordinal for event in events]
    if ordinals != sorted(ordinals):
        raise ValueError("G4 replay input is not in accepted causal admission order")
    if len(ordinals) != len(set(ordinals)):
        raise ValueError("G4 replay input contains duplicate admission ordinals")
    payload = {
        "schema_version": "VNEXT_G4_REPLAY_INPUT_V1",
        "transform_version": TRANSFORM_VERSION,
        "events": [event.model_dump(mode="json") for event in events],
    }
    return canonical_json_bytes(payload)


def bind_rebuildable_cache(
    *,
    manifest: G4RunManifest,
    payload: bytes,
) -> DerivedReplayCacheIdentity:
    """Bind a derived cache to immutable E4/G4 source hashes; it is never market truth."""
    artifacts = tuple(
        EvidenceArtifactHash(name=item.name, sha256=item.sha256)
        for item in manifest.source_evidence_artifact_hashes
    )
    return DerivedReplayCacheIdentity.create(
        source_g4_manifest_hash=manifest.manifest_hash,
        source_artifact_hashes=artifacts,
        transform_version=TRANSFORM_VERSION,
        derived_payload_hash=sha256_hex(payload),
    )
