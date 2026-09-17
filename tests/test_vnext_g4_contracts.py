from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    Ea3Base,
    EntryActivation,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    OrderPrimitive,
    ReentryPolicy,
    WinnerConfirmation,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def candidate_config(**updates: object) -> CandidateConfig:
    values: dict[str, object] = {
        "entry_activation": EntryActivation.EA1,
        "attempt_stop": AttemptStop.AP0,
        "room_to_cost_k": Decimal("2"),
        "reentry_policy": ReentryPolicy.NO_REENTRY_REFERENCE,
        "winner_confirmation": WinnerConfirmation.WC0,
        "winner_progress_bps": Decimal("3"),
        "exit_policy": ExitPolicy.X1,
        "comparison_role": "REFERENCE",
    }
    values.update(updates)
    return CandidateConfig.model_validate(values)


def execution_model(**updates: object) -> ExecutionModelConfig:
    values: dict[str, object] = {
        "book_type": "L1_MBP",
        "order_primitive": OrderPrimitive.MARKETABLE,
        "prob_fill_on_limit": Decimal("0"),
        "prob_slippage": Decimal("0"),
        "trade_execution": True,
        "queue_position": False,
        "liquidity_consumption": True,
        "fill_limit_at_price": False,
        "fill_stop_at_price": False,
        "random_seed": 7,
        "execution_model_limited": True,
    }
    values.update(updates)
    return ExecutionModelConfig.model_validate(values)


def test_candidate_identity_binds_vnext_and_structural_component() -> None:
    candidate = CandidateManifest.create(
        candidate_id="ordinary-reference",
        structural_component_manifest_hash=HASH_A,
        config=candidate_config(),
    )
    assert candidate.strategy_version == "TA_VNEXT_E4_C1_2026-09-11"
    assert candidate.structural_component_manifest_hash == HASH_A
    raw = candidate.model_dump(mode="json")
    raw["candidate_id"] = "tampered"
    with pytest.raises(ValidationError, match="candidate_hash"):
        CandidateManifest.model_validate(raw)


def test_frozen_family_grid_fails_closed() -> None:
    with pytest.raises(ValidationError, match="room_to_cost_k"):
        candidate_config(room_to_cost_k=Decimal("5"))
    with pytest.raises(ValidationError, match="EA3"):
        candidate_config(entry_activation=EntryActivation.EA3)
    ea3 = candidate_config(entry_activation=EntryActivation.EA3, ea3_base=Ea3Base.EA1)
    assert ea3.ea3_base is Ea3Base.EA1
    with pytest.raises(ValidationError, match="negative-control"):
        candidate_config(
            reentry_policy=ReentryPolicy.BLIND_IMMEDIATE_REENTRY_NEGATIVE_CONTROL,
            comparison_role="CHALLENGER",
        )


def test_execution_model_is_explicit_and_passive_claims_fail_closed() -> None:
    config = execution_model()
    assert config.passive_touch_equals_fill is False
    assert config.trigger_price_equals_fill is False
    assert config.l1_size_feasibility_required is True
    with pytest.raises(ValidationError, match="queue evidence"):
        execution_model(
            order_primitive=OrderPrimitive.PASSIVE,
            execution_model_limited=False,
        )
    with pytest.raises(ValidationError, match="reproducible seed"):
        execution_model(prob_slippage=Decimal("0.5"), random_seed=None)


def test_g4_manifest_binds_immutable_e4_source_and_never_opens_e5() -> None:
    candidate = CandidateManifest.create(
        candidate_id="ordinary-reference",
        structural_component_manifest_hash=HASH_A,
        config=candidate_config(),
    )
    manifest = G4RunManifest.create(
        run_id="g4-run-001",
        git_sha="1" * 40,
        git_tree="2" * 40,
        source_e4_manifest_hash=HASH_B,
        source_pit_snapshot_hash=HASH_C,
        source_evidence_artifact_hashes=(
            EvidenceArtifactHash(name="admissions", sha256="d" * 64),
            EvidenceArtifactHash(name="lifecycle", sha256="e" * 64),
        ),
        structural_component_manifest_hash=HASH_A,
        execution_model=execution_model(),
        candidates=(candidate,),
        trial_adaptivity_id="trial-v1",
        cutoff_id="cutoff-v1",
    )
    assert manifest.confirmatory_e5 is False
    assert manifest.private_api is manifest.signing is manifest.exchange_write is False
    assert manifest.venue_submitted is False
    assert [item.name for item in manifest.source_evidence_artifact_hashes] == [
        "admissions",
        "lifecycle",
    ]
