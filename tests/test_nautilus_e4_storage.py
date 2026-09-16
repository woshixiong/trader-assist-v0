from __future__ import annotations

import json
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_e4.capture import (
    CaptureSession,
    SubscriptionPolicy,
    recover_capture_session,
)
from trader_assist_v0.nautilus_e4.contracts import (
    POST_TERMINAL_MICRO_NS,
    DataKind,
    DecisionState,
    EvidenceState,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    SourceEvent,
    StreamHealth,
    TailPhase,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore, InMemoryCatalogSink

BASE = 2_000_000_000_000
MARKET = sha256_hex(b"HYPERLIQUID|MAIN|ETH")


def _identity() -> tuple[PitUniverseSnapshot, RunManifest]:
    expression = MarketExpression(
        market_id=MARKET,
        dex="MAIN",
        provider_coin="ETH",
        instrument_id="ETH-PERP.HYPERLIQUID",
        expression_id="expr-ETH",
        listing_state="LISTED",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash=sha256_hex(b"metadata"),
        fee_state_version="fee-v1",
        fee_state_hash=sha256_hex(b"fee"),
    )
    snapshot = PitUniverseSnapshot.create(observed_at_ns=BASE, expressions=(expression,))
    manifest = RunManifest.create(
        run_id="run-storage",
        git_sha="2" * 40,
        git_tree="3" * 40,
        snapshot=snapshot,
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        capture_configuration={
            "expressions": [expression.model_dump(mode="json")],
            "raw_storage": "NAUTILUS_PARQUET_DATA_CATALOG",
            "semantic_storage": "VERSIONED_PORTABLE_COLUMN_BATCHES",
        },
        subscription_policy={
            "discovery": [MARKET], "watch": [MARKET], "actionable": [MARKET]
        },
        trial_ledger_id="trial-v1",
    )
    return snapshot, manifest


def _event(index: int) -> SourceEvent:
    ts = BASE + index * 1_000_000_000
    return SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-PERP.HYPERLIQUID",
        data_kind=DataKind.TRADE,
        source_event_id=f"trade-{index}",
        native_trade_id=f"tid-{index}",
        provider_aggressor_side="BUYER",
        event_context=f"block-{index}",
        ts_event=ts,
        ts_init=ts + 1,
        true_network_receive_ts=None,
        payload={"price": str(100 + index), "size": "1"},
    )


def _low_rate_event(index: int, kind: DataKind) -> SourceEvent:
    ts = BASE + index * 1_000_000_000
    return SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-PERP.HYPERLIQUID",
        data_kind=kind,
        source_event_id=f"{kind.value.lower()}-{index}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context=f"finalized-{kind.value.lower()}-{index}",
        ts_event=ts,
        ts_init=ts + 1,
        true_network_receive_ts=None,
        payload={"finalized": True, "value": str(index)},
    )


def _policy() -> SubscriptionPolicy:
    return SubscriptionPolicy(
        discovery=frozenset({MARKET}),
        watch=frozenset({MARKET}),
        actionable=frozenset({MARKET}),
    )


def test_catalog_and_semantic_round_trip_preserves_causal_identity(tmp_path: Path) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    sink = InMemoryCatalogSink()
    session = CaptureSession(
        manifest=manifest,
        policy=SubscriptionPolicy(
            discovery=frozenset({MARKET}),
            watch=frozenset({MARKET}),
            actionable=frozenset({MARKET}),
        ),
        raw_sink=sink,
        evidence_store=store,
        batch_size=2,
    )
    for index in range(3):
        event = _event(index)
        session.ingest(event, admission_ts=event.ts_init)
    session.open_actionable(
        package_id="pkg-001",
        opportunity_id="opp-001",
        thesis_id="thesis-001",
        market_id=MARKET,
        expression_id="expr-ETH",
        decision_ts=BASE + 4_000_000_000,
        decision_state=DecisionState.WAIT,
    )
    session.terminal(
        package_id="pkg-001",
        terminal_ts=BASE + 5_000_000_000,
        decision_state=DecisionState.WAIT,
    )
    session.close()
    session.write_operational_artifacts()

    assert store.load_manifest() == manifest
    assert store.load_snapshot() == snapshot
    assert [item.record_hash for item in store.load_lifecycle()] == [
        item.record_hash for item in session.lifecycle_records
    ]
    stored = store.load_admissions()
    assert [item.source_identity for item in stored] == [
        item.source_identity for item in sink.events
    ]
    assert [item.admission_ordinal for item in stored] == sorted(
        item.admission_ordinal for item in stored
    )
    assert store.artifact_hashes().keys() == {
        "run-manifest.json",
        "pit-universe-snapshot.json",
        "lifecycle.jsonl",
        "causal-admission-columns.jsonl",
        "runtime-checkpoint.json",
    }
    expected_artifacts = {
        "capture-source-counts.json",
        "causal-order-replay-proof.json",
        "duplicate-gap-reconnect-prebuffer.json",
        "missingness-not-evaluable-counts.json",
        "catalog-semantic-round-trip.json",
        "capture-health-resource-freshness.json",
        "credential-negative-zero-write.json",
    }
    assert expected_artifacts <= {path.name for path in tmp_path.iterdir()}
    proof = json.loads((tmp_path / "catalog-semantic-round-trip.json").read_text())
    assert proof["readable"] is proof["deterministic"] is True


def test_discovery_bar_and_context_are_durable_without_memory_catalog(
    tmp_path: Path,
) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    session = CaptureSession(
        manifest=manifest,
        policy=SubscriptionPolicy(
            discovery=frozenset({MARKET}),
            watch=frozenset(),
            actionable=frozenset(),
        ),
        raw_sink=None,
        evidence_store=store,
        batch_size=2,
    )
    bar = _low_rate_event(1, DataKind.BAR)
    context = _low_rate_event(2, DataKind.CONTEXT)
    session.ingest(bar, admission_ts=bar.ts_init)
    session.ingest(context, admission_ts=context.ts_init)
    session.close()

    stored = store.load_admissions()
    assert [item.source.data_kind for item in stored] == [DataKind.BAR, DataKind.CONTEXT]
    assert [item.source.payload["finalized"] for item in stored] == [True, True]


def test_missing_or_corrupt_manifest_hash_fails_closed_for_replay(tmp_path: Path) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    store.verify_manifest_hash(manifest.manifest_hash)
    raw = json.loads(store.manifest_path.read_text(encoding="utf-8"))
    raw["capture_configuration"]["raw_storage"] = "MUTATED"
    store.manifest_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest_hash"):
        store.load_manifest()


def test_tail_round_trip_preserves_completeness_and_provenance(tmp_path: Path) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    session = CaptureSession(
        manifest=manifest,
        policy=SubscriptionPolicy(
            discovery=frozenset({MARKET}),
            watch=frozenset({MARKET}),
            actionable=frozenset({MARKET}),
        ),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    event = _event(1)
    session.ingest(event, admission_ts=event.ts_init)
    session.open_actionable(
        package_id="pkg-001",
        opportunity_id="opp-001",
        thesis_id="thesis-001",
        market_id=MARKET,
        expression_id="expr-ETH",
        decision_ts=BASE + 2_000_000_000,
        decision_state=DecisionState.PASS,
    )
    session.terminal(
        package_id="pkg-001",
        terminal_ts=BASE + 3_000_000_000,
        decision_state=DecisionState.PASS,
    )
    tail_before = session.tail_statuses["pkg-001"]
    checkpoint = session.checkpoint()
    restored = CaptureSession.restart_from(
        checkpoint,
        manifest=RunManifest.create(
            run_id="run-storage",
            git_sha="2" * 40,
            git_tree="3" * 40,
            snapshot=snapshot,
            process_epoch="process-2",
            continuity_epoch="continuity-2",
            admission_epoch="admission-2",
            capture_configuration=manifest.capture_configuration,
            subscription_policy=manifest.subscription_policy,
            trial_ledger_id="trial-v1",
        ),
        policy=session.policy,
        raw_sink=InMemoryCatalogSink(),
    )
    tail_after = restored.tail_statuses["pkg-001"]
    assert tail_after.package_id == tail_before.package_id
    assert tail_after.terminal_ts == tail_before.terminal_ts
    assert "PROCESS_RESTART" in tail_after.reason_codes


def test_durable_host_recovery_preserves_authority_and_creates_new_epochs(
    tmp_path: Path,
) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    first = recover_capture_session(
        manifest=manifest,
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    event = _event(1)
    first.ingest(event, admission_ts=event.ts_init)
    first.open_actionable(
        package_id="pkg-001",
        opportunity_id="opp-001",
        thesis_id="thesis-001",
        market_id=MARKET,
        expression_id="expr-ETH",
        decision_ts=BASE + 2_000_000_000,
        decision_state=DecisionState.WAIT,
    )
    commitment = first.decision_commitment("pkg-001")

    restarted = recover_capture_session(
        manifest=manifest,
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    assert restarted.manifest == manifest
    assert restarted.ledger.process_epoch == "process-1.p1"
    assert restarted.ledger.admission_epoch == "admission-1.p1"
    assert restarted.ledger.continuity_epoch == "continuity-1.p1"
    assert restarted.ledger.health is StreamHealth.REESTABLISHING
    assert restarted.tail_statuses["pkg-001"].evidence_state is EvidenceState.INTERRUPTED
    assert restarted.decision_commitment("pkg-001") == commitment
    assert restarted.ingest(event, admission_ts=event.ts_init + 10).duplicate is True
    with pytest.raises(ValueError, match="duplicate"):
        restarted.open_actionable(
            package_id="pkg-001",
            opportunity_id="opp-001",
            thesis_id="thesis-001",
            market_id=MARKET,
            expression_id="expr-ETH",
            decision_ts=BASE + 3_000_000_000,
            decision_state=DecisionState.TAKE,
        )
    assert len(store.load_lifecycle()) == 2
    segments = [json.loads(line) for line in store.process_segments_path.read_text().splitlines()]
    assert [item["segment_index"] for item in segments] == [0, 1]
    assert segments[1]["predecessor_checkpoint_hash"] is not None


@pytest.mark.parametrize("micro_complete", (False, True))
def test_durable_restart_types_mid_30m_and_mid_6h_tails(
    tmp_path: Path, micro_complete: bool
) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    first = recover_capture_session(
        manifest=manifest,
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    event = _event(1)
    first.ingest(event, admission_ts=event.ts_init)
    first.open_actionable(
        package_id="pkg-tail",
        opportunity_id="opp-tail",
        thesis_id="thesis-tail",
        market_id=MARKET,
        expression_id="expr-ETH",
        decision_ts=BASE + 2_000_000_000,
        decision_state=DecisionState.PASS,
    )
    terminal_ts = BASE + 3_000_000_000
    first.terminal(
        package_id="pkg-tail",
        terminal_ts=terminal_ts,
        decision_state=DecisionState.PASS,
    )
    if micro_complete:
        first.advance(now_ns=terminal_ts + POST_TERMINAL_MICRO_NS)

    restarted = recover_capture_session(
        manifest=manifest,
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    tail = restarted.tail_statuses["pkg-tail"]
    assert tail.terminal_ts == terminal_ts
    assert tail.evidence_state is EvidenceState.INTERRUPTED
    assert tail.context_phase is TailPhase.INCOMPLETE
    assert tail.micro_phase is (
        TailPhase.COMPLETE if micro_complete else TailPhase.INCOMPLETE
    )
    assert "PROCESS_RESTART" in tail.reason_codes


def test_runtime_checkpoint_is_atomic_hash_bound_and_identity_bound(tmp_path: Path) -> None:
    snapshot, manifest = _identity()
    store = EvidenceStore(tmp_path)
    store.initialize(manifest, snapshot)
    recover_capture_session(
        manifest=manifest,
        policy=_policy(),
        raw_sink=InMemoryCatalogSink(),
        evidence_store=store,
    )
    checkpoint = store.load_runtime_checkpoint(manifest)
    assert checkpoint is not None
    assert not list(tmp_path.glob(".runtime-checkpoint.json.*"))

    other_manifest = RunManifest.create(
        run_id="other-run",
        git_sha="2" * 40,
        git_tree="3" * 40,
        snapshot=snapshot,
        process_epoch="process-other",
        continuity_epoch="continuity-other",
        admission_epoch="admission-other",
        capture_configuration=manifest.capture_configuration,
        subscription_policy=manifest.subscription_policy,
        trial_ledger_id="trial-v1",
    )
    with pytest.raises(ValueError, match="immutable run/PIT identity"):
        store.load_runtime_checkpoint(other_manifest)

    raw = json.loads(store.runtime_checkpoint_path.read_text())
    raw["state"]["ledger"]["ordinal"] = 999
    store.runtime_checkpoint_path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="checkpoint hash"):
        store.load_runtime_checkpoint(manifest)
