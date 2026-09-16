from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.vnext_g4.contracts import (
    AttemptPolicy,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    ReentryPolicy,
    SimulatedExecutionResult,
    VNextCandidateConfig,
    WinnerConfirmation,
)


def candidate(**updates: object) -> VNextCandidateConfig:
    values: dict[str, object] = {
        "candidate_id": "candidate-g4-001",
        "entry_activation": EntryActivation.EA1_DIRECT_REACCEL_PRICE,
        "attempt_policy": AttemptPolicy.AP1_FIXED_BPS,
        "reentry_policy": ReentryPolicy.R1_ONE_FRESH_CAUSAL_ACTIVATION,
        "winner_confirmation": WinnerConfirmation.WC0_PROGRESS,
        "exit_policy": ExitPolicy.X1_STRUCTURAL_FULL_EXIT,
        "room_to_cost_hurdle": 3,
        "fixed_stop_bps": 8,
        "rv_multiplier": None,
        "no_followthrough_seconds": None,
        "winner_progress_bps": 5,
        "winner_persistence_seconds": None,
        "giveback_numerator": None,
        "giveback_denominator": None,
    }
    values.update(updates)
    return VNextCandidateConfig.create(**values)


def test_execution_model_is_explicit_hash_bound_and_zero_optimism_is_not_implicit() -> None:
    model = ExecutionModelConfig.create()
    assert model.prob_fill_on_limit == Decimal("1")
    assert model.prob_slippage == Decimal("0")
    assert model.queue_position is False
    assert model.passive_touch_is_fill is False
    assert model.trigger_price_is_fill is False
    assert model.execution_model_limited is True
    raw = model.model_dump(mode="json")
    raw["trade_execution"] = True
    with pytest.raises(ValidationError, match="config_hash"):
        ExecutionModelConfig.model_validate(raw)


def test_stochastic_execution_requires_explicit_seed() -> None:
    with pytest.raises(ValidationError, match="explicit seed"):
        ExecutionModelConfig.create(prob_slippage=Decimal("0.1"))
    seeded = ExecutionModelConfig.create(
        prob_slippage=Decimal("0.1"),
        random_seed=17,
    )
    assert seeded.random_seed == 17


def test_candidate_rejects_unfrozen_or_incomplete_family_configuration() -> None:
    with pytest.raises(ValidationError, match="AP1"):
        candidate(fixed_stop_bps=None)
    with pytest.raises(ValidationError, match="AP4"):
        candidate(
            attempt_policy=AttemptPolicy.AP4_SIMPLE_PRICE_PLUS_TIME,
            fixed_stop_bps=8,
            no_followthrough_seconds=None,
        )
    x3 = candidate(
        exit_policy=ExitPolicy.X3_STRUCTURAL_RATCHET_GIVEBACK,
        giveback_numerator=1,
        giveback_denominator=2,
    )
    assert (x3.giveback_numerator, x3.giveback_denominator) == (1, 2)


def test_g4_manifest_binds_immutable_e4_source_and_hard_zero_write() -> None:
    execution = ExecutionModelConfig.create()
    c = candidate()
    artifacts = {
        "causal-admission-columns.jsonl": "a" * 64,
        "run-manifest.json": "b" * 64,
    }
    manifest = G4RunManifest.create(
        run_id="g4-run-001",
        git_sha="1" * 40,
        git_tree="2" * 40,
        source_e4_manifest_hash="3" * 64,
        source_pit_snapshot_hash="4" * 64,
        source_artifact_hashes=artifacts,
        structural_component_manifest_hash="5" * 64,
        candidate_hash=c.candidate_hash,
        execution_model_hash=execution.config_hash,
        trial_ledger_id="trial-v1",
        evidence_cutoff_id="cutoff-v1",
    )
    assert manifest.source_e4_authority_immutable is True
    assert manifest.derived_catalog_rebuildable is True
    assert manifest.pre_e5_confirmatory_evidence_open is False
    assert manifest.exchange_write is manifest.private_api is manifest.signing is False
    assert manifest.real_capital is False


def test_simulated_result_enforces_order_active_l1_and_passive_queue_boundaries() -> None:
    c = candidate()
    execution = ExecutionModelConfig.create()
    result = SimulatedExecutionResult.create(
        package_id="pkg-001",
        candidate_hash=c.candidate_hash,
        execution_model_hash=execution.config_hash,
        order_active_ts=100,
        first_executable_state_ts=101,
        l1_capacity_sufficient=True,
        passive_order=False,
        queue_evidence_supported=False,
        modeled_fill=True,
        fill_ts=101,
        fill_price=Decimal("100"),
        fill_qty=Decimal("1"),
        fee_bps=Decimal("1"),
        slippage_bps=Decimal("0"),
        execution_model_limited=True,
        venue_submitted=False,
        private_api=False,
        signing=False,
        exchange_write=False,
    )
    assert result.fill_ts == 101
    with pytest.raises(ValidationError, match="passive touch"):
        SimulatedExecutionResult.create(
            package_id="pkg-002",
            candidate_hash=c.candidate_hash,
            execution_model_hash=execution.config_hash,
            order_active_ts=100,
            first_executable_state_ts=101,
            l1_capacity_sufficient=True,
            passive_order=True,
            queue_evidence_supported=False,
            modeled_fill=True,
            fill_ts=101,
            fill_price=Decimal("100"),
            fill_qty=Decimal("1"),
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            execution_model_limited=True,
            venue_submitted=False,
            private_api=False,
            signing=False,
            exchange_write=False,
        )
    with pytest.raises(ValidationError, match="L1 capacity"):
        SimulatedExecutionResult.create(
            package_id="pkg-003",
            candidate_hash=c.candidate_hash,
            execution_model_hash=execution.config_hash,
            order_active_ts=100,
            first_executable_state_ts=None,
            l1_capacity_sufficient=False,
            passive_order=False,
            queue_evidence_supported=False,
            modeled_fill=False,
            fill_ts=None,
            fill_price=None,
            fill_qty=None,
            fee_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            execution_model_limited=False,
            venue_submitted=False,
            private_api=False,
            signing=False,
            exchange_write=False,
        )


def test_candidate_hash_changes_when_candidate_economics_identity_changes() -> None:
    first = candidate(candidate_id="candidate-a", room_to_cost_hurdle=2)
    second = candidate(candidate_id="candidate-b", room_to_cost_hurdle=4)
    assert first.candidate_hash != second.candidate_hash
    assert len(sha256_hex(first.model_dump_json().encode())) == 64
