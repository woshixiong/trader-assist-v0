from __future__ import annotations

from decimal import Decimal

import pytest

pytest.importorskip("nautilus_trader")

from trader_assist_v0.nautilus_g4.runner import (
    assert_exact_rc5,
    build_isolated_candidate_contexts,
    dispose_candidate_contexts,
)
from trader_assist_v0.vnext_g4.contracts import (
    AttemptPolicy,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    ReentryPolicy,
    VNextCandidateConfig,
    WinnerConfirmation,
)


def candidate(candidate_id: str, hurdle: int) -> VNextCandidateConfig:
    return VNextCandidateConfig.create(
        candidate_id=candidate_id,
        entry_activation=EntryActivation.EA0_FORMAL_TIME_CONTROL,
        attempt_policy=AttemptPolicy.AP1_FIXED_BPS,
        reentry_policy=ReentryPolicy.R0_NO_REENTRY,
        winner_confirmation=WinnerConfirmation.WC0_PROGRESS,
        exit_policy=ExitPolicy.X1_STRUCTURAL_FULL_EXIT,
        room_to_cost_hurdle=hurdle,
        fixed_stop_bps=8,
        rv_multiplier=None,
        no_followthrough_seconds=None,
        winner_progress_bps=5,
        winner_persistence_seconds=None,
        giveback_numerator=None,
        giveback_denominator=None,
    )


def test_exact_rc5_provider_native_configs_are_explicit_and_candidate_isolated() -> None:
    assert assert_exact_rc5() == "2.0.0rc5"
    execution = ExecutionModelConfig.create(
        prob_fill_on_limit=Decimal("1"),
        prob_slippage=Decimal("0"),
    )
    contexts = build_isolated_candidate_contexts(
        candidates=(candidate("candidate-one", 3), candidate("candidate-two", 4)),
        execution=execution,
    )
    try:
        assert len(contexts) == 2
        assert contexts[0].node is not contexts[1].node
        assert contexts[0].venue_config.fill_model is not contexts[1].venue_config.fill_model
        for context in contexts:
            venue = context.venue_config
            assert str(venue.book_type).endswith("L1_MBP")
            assert venue.bar_execution is False
            assert venue.trade_execution is False
            assert venue.liquidity_consumption is True
            assert venue.queue_position is False
            assert context.execution_model_hash == execution.config_hash
    finally:
        dispose_candidate_contexts(contexts)


def test_provider_native_default_fill_model_is_not_implicit() -> None:
    from nautilus_trader.execution import DefaultFillModel

    model = DefaultFillModel(prob_fill_on_limit=1.0, prob_slippage=0.0, random_seed=None)
    assert model is not None
