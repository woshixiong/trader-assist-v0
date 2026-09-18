from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    CausalLineage,
    Ea3Base,
    EntryActivation,
    EvidenceArtifactHash,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    HypotheticalOrderIntent,
    LatencyEvidenceRole,
    OrderPrimitive,
    PositionSide,
    ReentryPolicy,
    TechnicalOrderQuantity,
    ValidationReference,
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
    assert candidate.strategy_version == "TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"
    assert candidate.policy_version == "TA_FRICTION_POSITION_POLICY_V0_2R2"
    assert (
        candidate.derivation_version
        == "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
    )
    assert candidate.structural_component_manifest_hash == HASH_A
    raw = candidate.model_dump(mode="json")
    raw["candidate_id"] = "tampered"
    with pytest.raises(ValidationError, match="candidate_hash"):
        CandidateManifest.model_validate(raw)
    old = candidate.model_dump(mode="json")
    old["strategy_version"] = "TA_VNEXT_E4_C1_2026-09-11"
    old["policy_version"] = "TA_FRICTION_POSITION_POLICY_V0_1"
    old["derivation_version"] = "TA_MICROSTRUCTURE_DERIV_V0_1"
    with pytest.raises(ValidationError):
        CandidateManifest.model_validate(old)


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
    assert manifest.source_e4_strategy_version == "TA_VNEXT_E4_C1_2026-09-11"
    assert manifest.strategy_version == "TA_VNEXT_E4_C1_SEMANTIC_V2R2_2026-09-17"
    assert manifest.source_e4_derivation_version == "TA_MICROSTRUCTURE_DERIV_V0_1"
    assert (
        manifest.derivation_version
        == "TA_VNEXT_CAUSAL_SEMANTIC_DERIV_V0_1R2_2026-09-17"
    )


def validation_reference(**updates: object) -> ValidationReference:
    values: dict[str, object] = {
        "validation_reference_id": "validation-v1",
        "source_artifact_hash": "1" * 64,
        "fee_profile_id": "fee-v1",
        "fee_profile_source_hash": "2" * 64,
        "fee_effective_at_ns": 1,
        "fee_bps": Decimal("1"),
        "all_in_friction_state_id": "friction-v1",
        "all_in_friction_source_hash": "3" * 64,
        "all_in_friction_bps": Decimal("2"),
        "execution_model_id": "execution-v1",
        "execution_model_source_hash": "4" * 64,
        "technical_quantity_rule_id": "quantity-v1",
        "technical_quantity_rule_source_hash": "5" * 64,
        "latency_control_id": "latency-v1",
        "latency_control_source_hash": "6" * 64,
        "latency_ms": Decimal("0"),
        "latency_evidence_role": LatencyEvidenceRole.CONTROL_ONLY,
    }
    values.update(updates)
    return ValidationReference.create(**values)


def test_validation_materialization_and_canonical_order_intent_fail_closed() -> None:
    complete = validation_reference()
    assert complete.fully_materialized
    missing = ValidationReference.create(
        validation_reference_id="validation-missing",
        source_artifact_hash="7" * 64,
    )
    assert not missing.fully_materialized
    with pytest.raises(ValidationError, match="complete or absent"):
        validation_reference(fee_profile_source_hash=None)
    with pytest.raises(ValidationError, match="CONTROL_ONLY"):
        validation_reference(latency_evidence_role=LatencyEvidenceRole.OBSERVED)

    quantity = TechnicalOrderQuantity(
        quantity=Decimal("1.20"),
        displayed_opposite_l1_size=Decimal("2.00"),
        size_decimals=2,
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash="8" * 64,
        bbo_admission_hash="9" * 64,
    )
    lineage = CausalLineage.create(
        source_e4_manifest_hash="d" * 64,
        source_pit_snapshot_hash="e" * 64,
        source_structural_artifact_hash="f" * 64,
        structural_component_manifest_hash=HASH_A,
        market_id="1" * 64,
        instrument_id="ETH-PERP.HYPERLIQUID",
        formal_setup_id="setup-v1",
        formal_setup_admission_ordinal=1,
        formal_setup_admission_ts=1,
        thesis_id="thesis-v1",
        activation_sequence_id="activation-v1",
        attempt_lineage_id="attempt-v1",
        restart_reference_id="restart-v1",
        continuity_epoch="continuity-v1",
        admission_epoch="admission-v1",
        instrument_metadata_version="meta-v1",
        instrument_metadata_hash="8" * 64,
        validation_reference_id=complete.validation_reference_id,
        validation_reference_hash=complete.reference_hash,
    )
    intent = HypotheticalOrderIntent.create(
        strategy_decision_id="decision-v1",
        candidate_hash="a" * 64,
        side=PositionSide.LONG,
        technical_quantity=quantity,
        executable_price=Decimal("100"),
        activation_reference_hash="b" * 64,
        validation=complete,
        lineage=lineage,
    )
    assert intent.not_submitted is True
    assert intent.venue_submitted is False
    assert intent.technical_notional == Decimal("120")
    with pytest.raises(ValidationError, match="grid-aligned"):
        quantity.model_copy(update={"quantity": Decimal("1.201")}).model_validate(
            quantity.model_copy(update={"quantity": Decimal("1.201")})
        )
    with pytest.raises(ValidationError, match="displayed L1"):
        TechnicalOrderQuantity(
            quantity=Decimal("2.01"),
            displayed_opposite_l1_size=Decimal("2.00"),
            size_decimals=2,
            instrument_metadata_version="meta-v1",
            instrument_metadata_hash="8" * 64,
            bbo_admission_hash="9" * 64,
        )
