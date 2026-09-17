from __future__ import annotations

import importlib.util
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.nautilus_vnext_g4_qualification import _representative_scale_probe
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_g4.runner import (
    BACKTEST_NODE_PUBLIC_METHODS,
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


def test_backtest_node_contract_requires_only_public_cache_portfolio_route() -> None:
    assert BACKTEST_NODE_PUBLIC_METHODS == (
        "build",
        "run",
        "dispose",
        "get_engine_cache",
        "get_engine_portfolio",
    )
    assert "get_engine" not in BACKTEST_NODE_PUBLIC_METHODS


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
        def __init__(self, *, reverse: bool = False) -> None:
            self.reverse = reverse

        def orders(self) -> tuple[object, ...]:
            values = (
                Value(client_order_id="order-1", status="FILLED", filled_qty="1", avg_px="100"),
                Value(client_order_id="order-2", status="ACCEPTED", filled_qty="0", avg_px=None),
            )
            return tuple(reversed(values)) if self.reverse else values

        def positions(self) -> tuple[object, ...]:
            return (
                Value(id="position-1", instrument_id="ETH", side="LONG", quantity="1"),
            )

        def accounts(self) -> tuple[object, ...]:
            raise AssertionError("unsupported Cache.accounts must not be called")

        def account_for_venue(self, venue: object) -> object:
            assert venue == "SIM"
            return Value(
                id="account-1",
                account_type="MARGIN",
                base_currency="USD",
            )

        def generate_order_fills_report(self) -> None:
            raise AssertionError("pandas report generation must not be called")

    class Portfolio:
        def account(self, venue: object) -> object:
            raise AssertionError("resolved Cache account should be used")

        def generate_order_fills_report(self) -> None:
            raise AssertionError("pandas report generation must not be called")

    first = project_provider_native_state(Cache(), Portfolio(), venue="SIM")
    second = project_provider_native_state(Cache(reverse=True), Portfolio(), venue="SIM")
    assert first == second
    assert first.source_api == "NAUTILUS_CACHE_PORTFOLIO"
    assert first.filled_order_count == 1
    assert first.account_count == 1


def test_provider_state_projection_uses_account_type_and_public_lookup_fallbacks() -> None:
    class Account:
        id = "account-1"
        account_type = "MARGIN"
        base_currency = "USD"

        @property
        def type(self) -> object:
            raise AssertionError("legacy account type field must not be read")

    class CacheById:
        def orders(self) -> tuple[object, ...]:
            return ()

        def positions(self) -> tuple[object, ...]:
            return ()

        def account(self, account_id: object) -> object:
            assert account_id == "account-1"
            return Account()

    class CacheByPortfolio:
        def orders(self) -> tuple[object, ...]:
            return ()

        def positions(self) -> tuple[object, ...]:
            return ()

        def account(self, account_id: object) -> None:
            return None

        def account_for_venue(self, venue: object) -> None:
            return None

    class Portfolio:
        def account(self, venue: object) -> object:
            assert venue == "SIM"
            return Account()

    by_id = project_provider_native_state(
        CacheById(),
        Portfolio(),
        account_id="account-1",
    )
    by_portfolio = project_provider_native_state(
        CacheByPortfolio(),
        Portfolio(),
        venue="SIM",
    )
    assert by_id.account_count == 1
    assert by_portfolio.account_count == 1


def test_t0_t1_or_manual_controls_cannot_pass_causal_gates() -> None:
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
    public_probe = causal_claim_gate_states(
        evidence_tier="T1_SAME_JOB_90S_PUBLIC_E4_PROBE",
        synthetic=False,
        manual_substitution=False,
        deterministic_replay_proven=True,
        semantic_derivation_proven=True,
        validation_materialized=True,
        canonical_order_intent_proven=True,
        provider_outcome_cost_provenance_complete=True,
        restart_equivalence_proven=True,
    )
    assert set(synthetic.values()) == {"NOT_PROVEN"}
    assert set(public_probe.values()) == {"NOT_PROVEN"}
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


def test_t2_absence_and_synthetic_markets_remain_truthfully_not_proven(
    tmp_path: Path,
) -> None:
    absent = _representative_scale_probe(None)
    assert absent == {
        "status": "NOT_PROVEN",
        "representative_evidence_supplied": False,
        "actual_representative_market_count": 0,
        "reason": "NO_ACCEPTED_T2_REPRESENTATIVE_EVIDENCE_SUPPLIED",
    }

    identity: dict[str, object] = {
        "evidence_tier": "T2_REAL_CAUSAL_G4_ARTIFACT",
        "synthetic": True,
        "manual_substitution": False,
        "markets": [],
    }
    artifact = {
        **identity,
        "artifact_hash": sha256_hex(canonical_json_bytes(identity)),
    }
    path = tmp_path / "synthetic-representative-evidence.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic/manual evidence cannot count"):
        _representative_scale_probe(path)


def test_formal_acceptance_requires_every_g4_gate_to_genuinely_pass() -> None:
    gates = {f"G4E{index}": "PASS" for index in range(9)}
    assert formal_g4_acceptance(gates)
    gates["G4E5"] = "NOT_PROVEN"
    assert not formal_g4_acceptance(gates)
    gates["G4E5"] = "PASS"
    del gates["G4E8"]
    assert not formal_g4_acceptance(gates)
