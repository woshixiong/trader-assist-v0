from __future__ import annotations

from decimal import Decimal

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    SourceEvent,
)
from trader_assist_v0.nautilus_g4.catalog_bridge import bind_rebuildable_cache, build_replay_payload
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    OrderPrimitive,
    ReentryPolicy,
    WinnerConfirmation,
)

MARKET = "a" * 64
STRUCTURAL = "b" * 64


def admitted(ordinal: int) -> AdmittedEvent:
    source = SourceEvent.create(
        market_id=MARKET,
        expression_id="expr-ETH",
        provider_id="NAUTILUS_HYPERLIQUID",
        instrument_id="ETH-PERP.HYPERLIQUID",
        data_kind=DataKind.BAR,
        source_event_id=f"bar-{ordinal}",
        native_trade_id=None,
        provider_aggressor_side=None,
        event_context="FINALIZED_5M",
        ts_event=ordinal,
        ts_init=ordinal + 1,
        true_network_receive_ts=None,
        payload={"close": str(100 + ordinal)},
    )
    return AdmittedEvent.create(
        schema_version="E4_CAPTURE_V1",
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        admission_ordinal=ordinal,
        admission_ts=ordinal + 2,
        source_identity=source.replay_identity,
        out_of_order=False,
        continuity_state=EvidenceState.COMPLETE,
        source=source,
    )


def manifest() -> G4RunManifest:
    config = CandidateConfig(
        entry_activation="EA1",
        attempt_stop=AttemptStop.AP0,
        room_to_cost_k=Decimal("2"),
        reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
        winner_confirmation=WinnerConfirmation.WC0,
        winner_progress_bps=Decimal("3"),
        exit_policy=ExitPolicy.X1,
        comparison_role="REFERENCE",
    )
    candidate = CandidateManifest.create(
        candidate_id="reference",
        structural_component_manifest_hash=STRUCTURAL,
        config=config,
    )
    execution = ExecutionModelConfig(
        book_type="L1_MBP",
        order_primitive=OrderPrimitive.MARKETABLE,
        prob_fill_on_limit=Decimal("0"),
        prob_slippage=Decimal("0"),
        trade_execution=True,
        queue_position=False,
        liquidity_consumption=True,
        fill_limit_at_price=False,
        fill_stop_at_price=False,
        random_seed=7,
        execution_model_limited=True,
    )
    return G4RunManifest.create(
        run_id="run-1",
        git_sha="1" * 40,
        git_tree="2" * 40,
        source_e4_manifest_hash="c" * 64,
        source_pit_snapshot_hash="d" * 64,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(name="admissions", sha256="e" * 64),
        ),
        structural_component_manifest_hash=STRUCTURAL,
        execution_model=execution,
        candidates=(candidate,),
        trial_adaptivity_id="trial-v1",
        cutoff_id="cutoff-v1",
    )


def test_replay_payload_is_deterministic_and_source_bound() -> None:
    events = (admitted(1), admitted(2))
    payload = build_replay_payload(events)
    assert payload == build_replay_payload(events)
    identity = bind_rebuildable_cache(manifest=manifest(), payload=payload)
    assert identity.derived_payload_hash == sha256_hex(payload)
    assert identity.source_g4_manifest_hash == manifest().manifest_hash


def test_replay_bridge_rejects_noncausal_or_duplicate_order() -> None:
    with pytest.raises(ValueError, match="causal admission order"):
        build_replay_payload((admitted(2), admitted(1)))
    with pytest.raises(ValueError, match="duplicate admission ordinals"):
        build_replay_payload((admitted(1), admitted(1)))
