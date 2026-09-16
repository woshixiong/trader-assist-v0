# mypy: disable-error-code="import-not-found"
"""Exact-rc5 provider-native simulation configuration for Ordinary VNext G4."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING, Any

from trader_assist_v0.nautilus_e4.contracts import NAUTILUS_VERSION
from trader_assist_v0.vnext_g4.contracts import ExecutionModelConfig, VNextCandidateConfig

if TYPE_CHECKING:
    class BacktestNode:
        def __init__(self, configs: list[object]) -> None: ...
        def dispose(self) -> None: ...

    class BacktestRunConfig:
        id: object

    class BacktestVenueConfig: ...

    class DefaultFillModel: ...


@dataclass(frozen=True)
class CandidateSimulationContext:
    """One candidate gets one isolated Nautilus run/node/matching state."""

    candidate_hash: str
    execution_model_hash: str
    venue_config: Any
    run_config: Any
    node: Any


def assert_exact_rc5() -> str:
    actual = version("nautilus-trader")
    if actual != NAUTILUS_VERSION:
        raise RuntimeError(f"exact Nautilus {NAUTILUS_VERSION} required; found {actual}")
    return actual


def build_candidate_simulation_context(
    *,
    candidate: VNextCandidateConfig,
    execution: ExecutionModelConfig,
) -> CandidateSimulationContext:
    """Build a fresh provider-native simulation owner for one candidate.

    The node is intentionally empty until deterministic E4-derived market data and
    a candidate Strategy shell are attached. No project-owned matching code exists.
    """
    assert_exact_rc5()
    from nautilus_trader.backtest import (
        BacktestEngineConfig as RuntimeBacktestEngineConfig,
        BacktestNode as RuntimeBacktestNode,
        BacktestRunConfig as RuntimeBacktestRunConfig,
        BacktestVenueConfig as RuntimeBacktestVenueConfig,
    )
    from nautilus_trader.execution import DefaultFillModel as RuntimeDefaultFillModel
    from nautilus_trader.model import AccountType, BookType, OmsType

    fill_model = RuntimeDefaultFillModel(
        prob_fill_on_limit=float(execution.prob_fill_on_limit),
        prob_slippage=float(execution.prob_slippage),
        random_seed=execution.random_seed,
    )
    venue = RuntimeBacktestVenueConfig(
        name=f"G4{candidate.candidate_hash[:10].upper()}",
        oms_type=OmsType.HEDGING,
        account_type=AccountType.MARGIN,
        book_type=BookType.L1_MBP,
        starting_balances=["1_000_000 USD"],
        bar_execution=execution.bar_execution,
        trade_execution=execution.trade_execution,
        liquidity_consumption=execution.liquidity_consumption,
        queue_position=execution.queue_position,
        fill_model=fill_model,
        use_random_ids=False,
        use_position_ids=True,
        use_reduce_only=True,
    )
    run_config = RuntimeBacktestRunConfig(
        venues=[venue],
        data=[],
        engine=RuntimeBacktestEngineConfig(
            bypass_logging=True,
            run_analysis=False,
            load_state=False,
            save_state=False,
            shutdown_on_error=True,
        ),
        dispose_on_completion=False,
    )
    node = RuntimeBacktestNode([run_config])
    return CandidateSimulationContext(
        candidate_hash=candidate.candidate_hash,
        execution_model_hash=execution.config_hash,
        venue_config=venue,
        run_config=run_config,
        node=node,
    )


def build_isolated_candidate_contexts(
    *,
    candidates: tuple[VNextCandidateConfig, ...],
    execution: ExecutionModelConfig,
) -> tuple[CandidateSimulationContext, ...]:
    if len({item.candidate_hash for item in candidates}) != len(candidates):
        raise ValueError("candidate identities must be unique")
    contexts = tuple(
        build_candidate_simulation_context(candidate=item, execution=execution)
        for item in candidates
    )
    if len({id(item.node) for item in contexts}) != len(contexts):
        raise RuntimeError("candidate simulations unexpectedly share a Nautilus node")
    if len({id(item.venue_config.fill_model) for item in contexts}) != len(contexts):
        raise RuntimeError("candidate simulations unexpectedly share a fill model")
    return contexts


def dispose_candidate_contexts(contexts: tuple[CandidateSimulationContext, ...]) -> None:
    for context in contexts:
        context.node.dispose()
