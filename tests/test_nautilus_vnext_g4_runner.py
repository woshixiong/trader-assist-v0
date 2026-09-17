from __future__ import annotations

import importlib.util
import os
from decimal import Decimal

import pytest

from trader_assist_v0.nautilus_g4.runner import (
    assert_exact_nautilus_rc5,
    assert_representative_scale,
    build_fill_model,
    candidate_state_isolation_plan,
    new_isolated_backtest_engine,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptStop,
    CandidateConfig,
    CandidateManifest,
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
        entry_activation="EA1",
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
        assert callable(engine.generate_order_fills_report)
        assert callable(engine.generate_positions_report)
    finally:
        engine.dispose()


def test_formal_representative_scale_boundary_is_twenty_unique_markets() -> None:
    assert_representative_scale(tuple(f"market-{index:02d}" for index in range(20)))
    with pytest.raises(ValueError, match="at least 20"):
        assert_representative_scale(tuple(f"market-{index:02d}" for index in range(19)))
