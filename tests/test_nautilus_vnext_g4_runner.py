from __future__ import annotations

import importlib.util
import os
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.nautilus_g4.runner import (
    RepresentativeMarketEvidence,
    assert_actual_representative_scale,
    assert_backtest_node_catalog_surface,
    assert_exact_nautilus_rc5,
    assert_representative_scale,
    build_fill_model,
    candidate_state_isolation_plan,
    causal_claim_gate_states,
    formal_g4_acceptance,
    new_isolated_backtest_engine,
    project_provider_native_state,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    OrderPrimitive,
    ReentryPolicy,
    WinnerConfirmation,
)

STRUCTURAL = "a" * 64
NAUTILUS_AVAILABLE = importlib.util.find_spec("nautilus_trader") is not None
NAUTILUS_REQUIRED = os.environ.get("NAUTILUS_G4_REQUIRED") == "1"
REQUIRES_NAUTILUS = pytest.mark.skipif(
    not NAUTILUS_AVAILABLE and not NAUTILUS_REQUIRED,
    reason="optional Nautilus distribution is absent",
)


def _assert_required_nautilus_available() -> None:
    if not NAUTILUS_AVAILABLE:
        raise AssertionError("authoritative G4 CI requires the exact Nautilus distribution")


def candidate(candidate_id: str) -> CandidateManifest:
    config = CandidateConfig(
        entry_activation=EntryActivation.EA1,
        attempt_stop=AttemptStop.AP0,
        room_to_cost_k=Decimal("2"),
        reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
        winner_confirmation=WinnerConfirmation.WC0,
        winner_progress_bps=Decimal("3"),
        exit_policy=ExitPolicy.X1,
        comparison_role="REFERENCE" if candidate_id == "reference" else "CHALLENGER",
    )
    return CandidateManifest.create(
        candidate_id=candidate_id,
        structural_component_manifest_hash=STRUCTURAL,
        config=config,
    )


def execution_model() -> ExecutionModelConfig:
    return ExecutionModelConfig(
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


@REQUIRES_NAUTILUS
def test_installed_rc5_and_provider_owned_fill_model_are_consumed() -> None:
    _assert_required_nautilus_available()
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    model = build_fill_model(execution_model())
    assert isinstance(model, ProbabilisticFillModel)


@REQUIRES_NAUTILUS
def test_exact_rc5_exposes_high_level_backtest_node_catalog_surface() -> None:
    _assert_required_nautilus_available()
    assert_backtest_node_catalog_surface()


def test_candidate_execution_contexts_are_identity_isolated() -> None:
    reference = candidate("reference")
    challenger = candidate("challenger")
    assert candidate_state_isolation_plan((reference, challenger)) == (
        reference.candidate_hash,
        challenger.candidate_hash,
    )
    with pytest.raises(ValueError, match="duplicate candidate"):
        candidate_state_isolation_plan((reference, reference))


@REQUIRES_NAUTILUS
def test_new_engine_is_provider_native_and_disposable() -> None:
    _assert_required_nautilus_available()
    from nautilus_trader.backtest import BacktestEngine

    engine = new_isolated_backtest_engine(candidate("reference"))
    try:
        assert isinstance(engine, BacktestEngine)
        assert callable(engine.add_venue)
        assert callable(engine.add_instrument)
        assert callable(engine.add_data)
        assert callable(engine.add_strategy)
        assert callable(engine.run)
        assert engine.cache is not None
        assert engine.portfolio is not None
    finally:
        engine.dispose()


def test_formal_representative_scale_boundary_is_twenty_unique_markets() -> None:
    assert_representative_scale(tuple(f"market-{index:02d}" for index in range(20)))
    with pytest.raises(ValueError, match="at least 20"):
        assert_representative_scale(tuple(f"market-{index:02d}" for index in range(19)))


def test_actual_representative_scale_requires_source_bound_positive_events() -> None:
    evidence = tuple(
        RepresentativeMarketEvidence(
            market_id=sha256_hex(f"actual-market-{index}".encode()),
            instrument_id=f"ACTUAL-{index}.HYPERLIQUID",
            source_e4_manifest_hash="f" * 64,
            source_event_hashes=(sha256_hex(f"actual-event-{index}".encode()),),
            event_count=index + 1,
        )
        for index in range(20)
    )
    with pytest.raises(ValueError, match="retained market evidence"):
        assert_actual_representative_scale(())
    markets = assert_actual_representative_scale(evidence)
    assert len(markets) == 20
    with pytest.raises(ValidationError):
        RepresentativeMarketEvidence(
            market_id="generated-market-01",
            instrument_id="GENERATED.HYPERLIQUID",
            source_e4_manifest_hash="f" * 64,
            source_event_hashes=("e" * 64,),
            event_count=1,
        )


def test_provider_state_projection_uses_cache_portfolio_without_report_generation() -> None:
    class Value:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class Cache:
        def orders(self) -> tuple[object, ...]:
            return (
                Value(client_order_id="order-1", status="FILLED", filled_qty="1", avg_px="100"),
            )

        def positions(self) -> tuple[object, ...]:
            return (
                Value(id="position-1", instrument_id="ETH", side="LONG", quantity="1"),
            )

        def accounts(self) -> tuple[object, ...]:
            return (Value(id="account-1", type="MARGIN", base_currency="USD"),)

    class Engine:
        cache = Cache()
        portfolio = Value()

        def generate_order_fills_report(self) -> None:
            raise AssertionError("pandas report generation must not be called")

    first = project_provider_native_state(Engine())
    second = project_provider_native_state(Engine())
    assert first == second
    assert first.source_api == "NAUTILUS_CACHE_PORTFOLIO"
    assert first.filled_order_count == 1


def test_synthetic_or_manual_controls_cannot_pass_causal_gates() -> None:
    synthetic = causal_claim_gate_states(
        evidence_tier="T0_SYNTHETIC_CONTROL",
        synthetic=True,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    manual = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=True,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert set(synthetic.values()) == {"NOT_PROVEN"}
    assert set(manual.values()) == {"NOT_PROVEN"}

    validation_missing = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=False,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert validation_missing["G4E2"] == "NOT_PROVEN"
    assert validation_missing["G4E5"] == "NOT_PROVEN"

    no_intent = causal_claim_gate_states(
        evidence_tier="T2_REAL_CAUSAL_G4_ARTIFACT",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=False,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert no_intent["G4E2"] == "NOT_PROVEN"
    assert no_intent["G4E5"] == "NOT_PROVEN"


def test_formal_acceptance_requires_every_g4_gate_to_genuinely_pass() -> None:
    gates = {f"G4E{index}": "PASS" for index in range(9)}
    assert formal_g4_acceptance(gates)
    gates["G4E5"] = "NOT_PROVEN"
    assert not formal_g4_acceptance(gates)
    gates["G4E5"] = "PASS"
    del gates["G4E8"]
    assert not formal_g4_acceptance(gates)
