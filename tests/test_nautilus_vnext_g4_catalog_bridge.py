from __future__ import annotations

from pathlib import Path

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore
from trader_assist_v0.nautilus_g4.catalog_bridge import bind_e4_source


def e4_store(root: Path) -> tuple[EvidenceStore, RunManifest]:
    expression = MarketExpression(
        market_id=sha256_hex(b"HYPERLIQUID|MAIN|ETH"),
        dex="MAIN",
        provider_coin="ETH",
        instrument_id="ETH-USD-PERP.HYPERLIQUID",
        expression_id="expr-eth",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=sha256_hex(b"meta"),
    )
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=1,
        expressions=(expression,),
    )
    manifest = RunManifest.create(
        run_id="e4-g4-source",
        git_sha="1" * 40,
        git_tree="2" * 40,
        snapshot=snapshot,
        process_epoch="process-e4",
        continuity_epoch="continuity-e4",
        admission_epoch="admission-e4",
        capture_configuration={
            "expressions": [expression.model_dump(mode="json")],
            "prebuffer_seconds": 60,
        },
        subscription_policy={"discovery": [expression.market_id], "watch": [expression.market_id]},
        trial_ledger_id="trial-e4",
    )
    store = EvidenceStore(root)
    store.initialize(manifest, snapshot)
    return store, manifest


def test_derived_catalog_binding_is_hash_bound_rebuildable_and_never_second_truth(
    tmp_path: Path,
) -> None:
    store, manifest = e4_store(tmp_path / "e4")
    before = store.artifact_hashes()
    binding = bind_e4_source(
        evidence_root=tmp_path / "e4",
        cache_root=tmp_path / "derived",
        expected_manifest_hash=manifest.manifest_hash,
    )
    after = store.artifact_hashes()
    assert before == after
    assert binding.source_e4_manifest_hash == manifest.manifest_hash
    assert binding.rebuildable is True
    assert binding.authoritative_market_truth is False
    assert binding.source_artifact_hashes == dict(sorted(before.items()))


def test_binding_rejects_wrong_source_authority(tmp_path: Path) -> None:
    _store, _manifest = e4_store(tmp_path / "e4")
    try:
        bind_e4_source(
            evidence_root=tmp_path / "e4",
            cache_root=tmp_path / "derived",
            expected_manifest_hash="f" * 64,
        )
    except ValueError as exc:
        assert "manifest" in str(exc)
    else:
        raise AssertionError("wrong E4 authority must fail closed")
