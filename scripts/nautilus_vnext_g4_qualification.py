#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""Bounded exact-rc5 Ordinary VNext G4 engineering qualification."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from trader_assist_v0.nautilus_g4.runner import (
    assert_exact_nautilus_rc5,
    assert_representative_scale,
    build_fill_model,
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


def _candidate() -> CandidateManifest:
    return CandidateManifest.create(
        candidate_id="qualification-reference",
        structural_component_manifest_hash="a" * 64,
        config=CandidateConfig(
            entry_activation="EA1",
            attempt_stop=AttemptStop.AP0,
            room_to_cost_k=Decimal("2"),
            reentry_policy=ReentryPolicy.NO_REENTRY_REFERENCE,
            winner_confirmation=WinnerConfirmation.WC0,
            winner_progress_bps=Decimal("3"),
            exit_policy=ExitPolicy.X1,
            comparison_role="REFERENCE",
        ),
    )


def _execution() -> ExecutionModelConfig:
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


def qualify() -> dict[str, object]:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    fill_model = build_fill_model(_execution())
    assert isinstance(fill_model, ProbabilisticFillModel)
    engine = new_isolated_backtest_engine(_candidate())
    try:
        assert isinstance(engine, BacktestEngine)
        required = (
            engine.add_venue,
            engine.add_instrument,
            engine.add_data,
            engine.add_strategy,
            engine.run,
            engine.generate_order_fills_report,
            engine.generate_positions_report,
        )
        assert all(callable(item) for item in required)
    finally:
        engine.dispose()

    markets = tuple(f"representative-market-{index:02d}" for index in range(20))
    assert_representative_scale(markets)
    return {
        "schema_version": "VNEXT_G4_QUALIFICATION_RESULT_V1",
        "status": "PASS",
        "nautilus_version": version("nautilus-trader"),
        "provider_native_backtest_engine": True,
        "provider_native_fill_model": True,
        "explicit_fill_model_config": True,
        "candidate_state_isolation_by_fresh_engine": True,
        "representative_scale_boundary": len(markets),
        "derived_cache_is_authoritative_market_truth": False,
        "confirmatory_e5_open": False,
        "private_api": False,
        "signing": False,
        "exchange_write": False,
        "venue_submitted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", type=Path, required=True)
    args = parser.parse_args()
    result = qualify()
    args.result_path.parent.mkdir(parents=True, exist_ok=True)
    args.result_path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
