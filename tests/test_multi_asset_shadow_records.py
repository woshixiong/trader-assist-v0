from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.shadow_records import (
    SUBMISSION_STATUS,
    Candidate,
    CandidateTransition,
    CorrelationIdentifier,
    EvidenceStore,
    FormalSignal,
    HumanReview,
    HumanReviewAction,
    MarketEvent,
    NotificationOutboxReference,
    OutcomeEnvelope,
    PlanRecord,
    ProvenanceRecord,
    RecordConflictError,
    RecordError,
    ScannerEvidence,
    ShadowOrder,
)


def _lineage(
    *, family: str = "BREAKOUT_RETEST", mode: str = "MICRO_FAST", tier: str = "P0", tag: str = "a"
) -> tuple[object, ...]:
    provenance = ProvenanceRecord.create(
        identity={"release": "ed7ab1e", "strategy": "three-setup-r1"},
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        registry_version="registry-1",
        registry_hash="r" * 64,
        cost_model_version="cost-1",
        release_sha="ed7ab1e2a91265a31e60260502de8fd9d119517c",
        recorded_at="2026-08-12T00:00:00Z",
    )
    scan = ScannerEvidence.create(
        identity={"scan": "scan-1"},
        scan_id="scan-1",
        observed_at="2026-08-12T00:00:00Z",
        scanner_version="scanner-r3",
        parameter_version="2026-08-03-r1",
        registry_version="registry-1",
        registry_hash="r" * 64,
        release_sha="ed7ab1e2a91265a31e60260502de8fd9d119517c",
        universe_snapshot_hash="u" * 64,
        eligible_count=40,
        rejected_count=2,
    )
    candidate = Candidate.create(
        identity={"candidate": tag},
        scanner_evidence_id=scan.record_id,
        scan_id="scan-1",
        market_id=f"market-{tag}",
        state="FAILED_BREAKOUT_SWEEP_WATCH" if family == "BREAKOUT_RETEST" else "SETUP_READY",
        alert_level="WATCH",
        created_at="2026-08-12T00:01:00Z",
        scanner_rank=1,
        session_tag="US_CASH",
        htf_relation="ALIGNED",
        breakout_path="ACCEPTED_REENTRY" if family == "BREAKOUT_RETEST" else "NONE",
        invalidation_reason="ACCEPTED_REENTRY" if family == "BREAKOUT_RETEST" else None,
    )
    transition = CandidateTransition.create(
        identity={"candidate": tag, "transition": "ready"},
        candidate_id=candidate.record_id,
        from_state="WATCH",
        to_state="SETUP_READY",
        transitioned_at="2026-08-12T00:02:00Z",
        invalidation_reason="ACCEPTED_REENTRY" if family == "BREAKOUT_RETEST" else None,
    )
    event = MarketEvent.create(
        identity={"event": tag},
        candidate_id=candidate.record_id,
        market_id=f"market-{tag}",
        event_kind="BREAKOUT" if family == "BREAKOUT_RETEST" else family,
        event_time="2026-08-12T00:03:00Z",
        initial_breakout_candle_id=f"5m-{tag}",
        initial_breakout_time="2026-08-12T00:00:00Z",
        initial_breakout_open="100",
        initial_breakout_high="106",
        initial_breakout_low="99",
        initial_breakout_close="105",
        a5_event="A5_EVENT",
        m20_event="M20_EVENT",
        breakout_body_atr="1.1",
        breakout_volume_ratio="2.2",
        breakout_clv="0.9",
        breakout_distance_atr="0.7",
        zone_id="zone-1",
        zone_quality="ZQ2",
        htf_relation="ALIGNED",
        scanner_relative_strength_rank=1,
        session_tag="US_CASH",
    )
    signal = FormalSignal.create(
        identity={"signal": tag},
        candidate_id=candidate.record_id,
        market_event_id=event.record_id,
        market_id=f"market-{tag}",
        setup_family=family,
        setup_mode=mode,
        side="LONG",
        approval_status="APPROVED",
        tier=tier,
        confirmed_at="2026-08-12T00:04:00Z",
        provenance_id=provenance.record_id,
    )
    plan = PlanRecord.create(
        identity={"plan": tag},
        signal_id=signal.record_id,
        planned_entry="101",
        stop="99",
        tp1="104",
        tp2="106",
        risk_reference_sizing={"reference_equity": "200", "risk_pct": "1"},
        created_at="2026-08-12T00:05:00Z",
        provenance_id=provenance.record_id,
    )
    shadow = ShadowOrder.create(
        identity={"shadow": tag},
        signal_id=signal.record_id,
        plan_id=plan.record_id,
        market_event_id=event.record_id,
        market_id=f"market-{tag}",
        setup_family=family,
        setup_mode=mode,
        side="LONG",
        planned_entry="101",
        stop="99",
        tp1="104",
        tp2="106",
        risk_reference_sizing={"reference_equity": "200", "risk_pct": "1"},
        provenance_id=provenance.record_id,
        strategy_version="FL-MA-PRICE-ACTION-v0.1",
        parameter_version="2026-08-03-r1",
        registry_version="registry-1",
        registry_hash="r" * 64,
        cost_model_version="cost-1",
        created_at="2026-08-12T00:05:00Z",
        submission_status=SUBMISSION_STATUS,
    )
    review = HumanReview.create(
        identity={"review": tag},
        signal_id=signal.record_id,
        shadow_order_id=shadow.record_id,
        action=HumanReviewAction.SKIPPED,
        actor="operator-1",
        source="terminal",
        reviewed_at="2026-08-12T00:06:00Z",
        reason_code="MANUAL_SKIP",
    )
    outcome = OutcomeEnvelope.create(
        identity={"outcome": tag},
        signal_id=signal.record_id,
        shadow_order_id=shadow.record_id,
        observed_at="2026-08-12T00:07:00Z",
        path_maturity_status="PENDING_120M",
        outcome_source="ON_DEMAND_1M",
        mfe_mae_by_horizon={"30m": {"mfe": "1", "mae": "0.2"}},
        failed_breakout=family == "BREAKOUT_RETEST",
    )
    correlation = CorrelationIdentifier.create(
        identity={"correlation": tag},
        signal_id=signal.record_id,
        shadow_order_id=shadow.record_id,
        cluster_kind="SETUP_RESEARCH_CLUSTER",
        cluster_id=f"cluster-{tag}",
        correlation_version="r1",
        correlation_status="INSUFFICIENT_DATA",
    )
    notification = NotificationOutboxReference.create(
        identity={"publication": tag},
        signal_id=signal.record_id,
        publication_id=f"publication-{tag}",
        published_at="2026-08-12T00:08:00Z",
        outbox_reference=f"outbox-{tag}",
    )
    return (
        provenance,
        scan,
        candidate,
        transition,
        event,
        signal,
        plan,
        shadow,
        review,
        outcome,
        correlation,
        notification,
    )


def test_record_round_trip_and_signal_plan_shadow_linkage(tmp_path: Path) -> None:
    records = _lineage()
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        assert all(store.write(records))
        signal = records[5]
        shadow = records[7]
        assert isinstance(signal, FormalSignal) and isinstance(shadow, ShadowOrder)
        assert store.get(shadow.record_id) == shadow
        assert shadow.payload["signal_id"] == signal.record_id
        assert shadow.payload["submission_status"] == "NOT_SUBMITTED"
        assert store.count() == len(records)


def test_hashes_are_deterministic_and_payload_copies_cannot_mutate_record() -> None:
    first = ScannerEvidence.create(
        identity={"scan": "same", "market": "btc"},
        scan_id="same",
        observed_at="2026-08-12T00:00:00Z",
        scanner_version="r3",
        parameter_version="p1",
        registry_version="r1",
        registry_hash="r" * 64,
        release_sha="s" * 40,
        universe_snapshot_hash="u" * 64,
    )
    second = ScannerEvidence.create(
        identity={"market": "btc", "scan": "same"},
        universe_snapshot_hash="u" * 64,
        release_sha="s" * 40,
        registry_hash="r" * 64,
        registry_version="r1",
        parameter_version="p1",
        scanner_version="r3",
        observed_at="2026-08-12T00:00:00Z",
        scan_id="same",
    )
    assert first == second
    copy = first.payload
    copy["scan_id"] = "rewritten"
    assert first.payload["scan_id"] == "same"


def test_exact_duplicate_is_idempotent_and_conflicting_identity_fails(tmp_path: Path) -> None:
    records = _lineage()
    candidate = records[2]
    assert isinstance(candidate, Candidate)
    changed = Candidate.create(
        identity={"candidate": "a"},
        **{**candidate.payload, "state": "REJECTED"},
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        store.write(records[:3])
        assert store.write((candidate,)) == (False,)
        with pytest.raises(RecordConflictError):
            store.write((changed,))


def test_batch_rolls_back_when_a_later_link_is_invalid(tmp_path: Path) -> None:
    records = _lineage()
    candidate = records[2]
    assert isinstance(candidate, Candidate)
    broken = CandidateTransition.create(
        identity={"candidate": "missing", "transition": "broken"},
        candidate_id="f" * 64,
        from_state="WATCH",
        to_state="SETUP_READY",
        transitioned_at="2026-08-12T00:02:00Z",
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        store.write(records[:2])
        with pytest.raises(RecordError):
            store.write((candidate, broken))
        assert store.count() == 2


def test_tsr_is_append_only_and_uses_live_authority_terms(tmp_path: Path) -> None:
    records = _lineage()
    signal, shadow = records[5], records[7]
    assert isinstance(signal, FormalSignal) and isinstance(shadow, ShadowOrder)
    reviews = tuple(
        HumanReview.create(
            identity={"review": action.value},
            signal_id=signal.record_id,
            shadow_order_id=shadow.record_id,
            action=action,
            actor="operator-1",
            source="terminal",
            reviewed_at=f"2026-08-12T00:0{index}:00Z",
        )
        for index, action in enumerate(HumanReviewAction, start=7)
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        store.write(records[:8])
        assert all(store.write(reviews))
        assert [review.payload["action"] for review in reviews] == [
            "TAKEN",
            "SKIPPED",
            "REJECTED",
        ]
        with pytest.raises(sqlite3.DatabaseError, match="append-only evidence"):
            store._connection.execute("DELETE FROM human_reviews")


def test_outcome_placeholder_and_failed_breakout_research_linkage(tmp_path: Path) -> None:
    records = _lineage()
    candidate, transition, event, signal, outcome = (
        records[2],
        records[3],
        records[4],
        records[5],
        records[9],
    )
    assert isinstance(candidate, Candidate)
    assert isinstance(transition, CandidateTransition)
    assert isinstance(event, MarketEvent)
    assert isinstance(signal, FormalSignal)
    assert isinstance(outcome, OutcomeEnvelope)
    opposite = MarketEvent.create(
        identity={"event": "opposite"},
        candidate_id=candidate.record_id,
        market_id=event.payload["market_id"],
        event_kind="OPPOSITE_SWEEP",
        event_time="2026-08-12T00:09:00Z",
        linked_market_event_id=event.record_id,
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        store.write(records)
        store.write((opposite,))
        assert candidate.payload["state"] == "FAILED_BREAKOUT_SWEEP_WATCH"
        assert transition.payload["invalidation_reason"] == "ACCEPTED_REENTRY"
        assert event.payload["a5_event"] == "A5_EVENT"
        assert event.payload["breakout_clv"] == "0.9"
        assert outcome.payload["path_maturity_status"] == "PENDING_120M"
        assert opposite.payload["linked_market_event_id"] == event.record_id


def test_breakout_micro_fast_standard_and_successful_control_are_retained(tmp_path: Path) -> None:
    micro = _lineage(tag="micro")
    standard = _lineage(mode="STANDARD", tag="standard")
    signal, shadow = standard[5], standard[7]
    assert isinstance(signal, FormalSignal) and isinstance(shadow, ShadowOrder)
    successful_control = OutcomeEnvelope.create(
        identity={"outcome": "successful-standard-120m"},
        signal_id=signal.record_id,
        shadow_order_id=shadow.record_id,
        observed_at="2026-08-12T02:05:00Z",
        path_maturity_status="MATURE_120M",
        outcome_source="ON_DEMAND_1M",
        research_classification="SUCCESSFUL_BREAKOUT",
        failed_breakout=False,
        mfe_mae_by_horizon={"120m": {"mfe": "2.1", "mae": "0.3"}},
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        store.write(micro)
        store.write(standard)
        store.write((successful_control,))
        assert micro[5].payload["setup_mode"] == "MICRO_FAST"
        assert standard[5].payload["setup_mode"] == "STANDARD"
        assert successful_control.payload["research_classification"] == "SUCCESSFUL_BREAKOUT"


def test_all_families_all_tiers_and_versioned_provenance_are_retained(tmp_path: Path) -> None:
    groups = (
        _lineage(family="SWEEP_RECLAIM", mode="STANDARD", tier="P0", tag="sweep"),
        _lineage(family="BREAKOUT_RETEST", mode="MICRO_FAST", tier="P1", tag="breakout"),
        _lineage(family="RANGE_EDGE_REJECTION", mode="STANDARD", tier="P2", tag="range"),
    )
    with EvidenceStore(tmp_path / "shadow-evidence.sqlite") as store:
        for group in groups:
            store.write(group)
        signals = [group[5] for group in groups]
        families = {
            signal.payload["setup_family"]
            for signal in signals
            if isinstance(signal, FormalSignal)
        }
        assert families == {
            "SWEEP_RECLAIM",
            "BREAKOUT_RETEST",
            "RANGE_EDGE_REJECTION",
        }
        tiers = {
            signal.payload["tier"] for signal in signals if isinstance(signal, FormalSignal)
        }
        assert tiers == {
            "P0",
            "P1",
            "P2",
        }
        provenance = groups[0][0]
        assert isinstance(provenance, ProvenanceRecord)
        assert provenance.payload["cost_model_version"] == "cost-1"
        assert provenance.payload["registry_hash"] == "r" * 64


def test_reopen_and_deterministic_research_export(tmp_path: Path) -> None:
    database = tmp_path / "shadow-evidence.sqlite"
    records = _lineage()
    with EvidenceStore(database) as store:
        store.write(records)
        first = store.export_jsonl()
        first_hash = store.export_hash()
    with EvidenceStore(database) as reopened:
        assert reopened.count() == len(records)
        assert reopened.export_jsonl() == first
        assert reopened.export_hash() == first_hash


def test_shadow_store_has_no_exchange_write_or_account_surface() -> None:
    public_methods = {name for name in dir(EvidenceStore) if not name.startswith("_")}
    assert public_methods == {"close", "count", "export_hash", "export_jsonl", "get", "write"}
    assert SUBMISSION_STATUS == "NOT_SUBMITTED"
