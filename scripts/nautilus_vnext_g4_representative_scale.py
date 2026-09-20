#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Build a bounded representative-scale candidate from persisted public E4 evidence.

The output is a candidate artifact only.  It cannot grant G4E8 credit until an
owner-authored canonical GitHub acceptance readback independently binds it.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    EvidenceState,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.nautilus_g4.runner import (
    RepresentativeMarketEvidence,
    assert_actual_representative_scale,
)

ARTIFACT_SCHEMA = "G4_REPRESENTATIVE_SCALE_CANDIDATE_V1"
CANONICAL_REPOSITORY = "woshixiong/trader-assist-v0"


def build_representative_scale_candidate(
    *,
    manifest: RunManifest,
    snapshot: PitUniverseSnapshot,
    admissions: tuple[AdmittedEvent, ...],
    source_artifact_hashes: dict[str, str],
) -> dict[str, object]:
    """Derive a hash-bound candidate from actual retained E4 source identities."""
    if manifest.pit_snapshot_hash != snapshot.snapshot_hash:
        raise ValueError("E4 manifest and PIT snapshot identity conflict")
    if manifest.private_api or manifest.exchange_write or manifest.real_exec_client_registered:
        raise ValueError("representative acquisition must remain public-data-only")

    expressions = {item.market_id: item for item in snapshot.expressions}
    if len(expressions) != len(snapshot.expressions):
        raise ValueError("representative PIT snapshot contains duplicate market identity")

    retained: dict[str, list[AdmittedEvent]] = defaultdict(list)
    seen_source_identities: set[str] = set()
    for event in admissions:
        expression = expressions.get(event.source.market_id)
        if expression is None:
            raise ValueError("retained E4 event is outside the bound PIT snapshot")
        if event.process_epoch != manifest.process_epoch:
            raise ValueError("retained E4 event process epoch contradicts the manifest")
        if event.continuity_epoch != manifest.continuity_epoch:
            raise ValueError("retained E4 event continuity epoch contradicts the manifest")
        if event.admission_epoch != manifest.admission_epoch:
            raise ValueError("retained E4 event admission epoch contradicts the manifest")
        if event.source.expression_id != expression.expression_id:
            raise ValueError("retained E4 event expression contradicts the PIT snapshot")
        if event.source.instrument_id != expression.instrument_id:
            raise ValueError("retained E4 event instrument contradicts the PIT snapshot")
        if event.continuity_state is not EvidenceState.COMPLETE:
            continue
        if event.source_identity in seen_source_identities:
            raise ValueError("retained E4 source identities must be globally unique")
        seen_source_identities.add(event.source_identity)
        retained[event.source.market_id].append(event)

    markets = tuple(
        RepresentativeMarketEvidence(
            market_id=market_id,
            instrument_id=expressions[market_id].instrument_id,
            source_e4_manifest_hash=manifest.manifest_hash,
            source_event_hashes=tuple(
                sorted(event.source_identity for event in market_events)
            ),
            event_count=len(market_events),
        )
        for market_id, market_events in sorted(retained.items())
        if market_events
    )
    market_ids = assert_actual_representative_scale(markets)
    market_set_hash = sha256_hex(canonical_json_bytes(list(market_ids)))
    identity: dict[str, object] = {
        "schema_version": ARTIFACT_SCHEMA,
        "repository": CANONICAL_REPOSITORY,
        "candidate_only": True,
        "canonical_acceptance_required": True,
        "evidence_tier": "E4_PUBLIC_PROVIDER_REPRESENTATIVE_SCALE_CANDIDATE",
        "synthetic": False,
        "manual_substitution": False,
        "public_data_only": True,
        "zero_credentials": True,
        "zero_execution_client": True,
        "zero_signing": True,
        "zero_exchange_write": True,
        "source_e4_manifest_hash": manifest.manifest_hash,
        "source_e4_snapshot_hash": snapshot.snapshot_hash,
        "source_e4_exact_head": manifest.git_sha,
        "source_e4_exact_tree": manifest.git_tree,
        "source_artifact_hashes": dict(sorted(source_artifact_hashes.items())),
        "representative_market_set_hash": market_set_hash,
        "representative_market_count": len(markets),
        "unique_retained_event_identity_count": len(seen_source_identities),
        "markets": [item.model_dump(mode="json") for item in markets],
    }
    return {
        **identity,
        "artifact_hash": sha256_hex(canonical_json_bytes(identity)),
    }


def build_from_evidence_root(root: Path) -> dict[str, object]:
    store = EvidenceStore(root)
    return build_representative_scale_candidate(
        manifest=store.load_manifest(),
        snapshot=store.load_snapshot(),
        admissions=store.load_admissions(),
        source_artifact_hashes=store.artifact_hashes(),
    )


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    encoded = canonical_json_bytes(payload) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    print(encoded.decode().strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    args = parser.parse_args()
    _write_result(args.result_path, build_from_evidence_root(args.evidence_root))


if __name__ == "__main__":
    main()
