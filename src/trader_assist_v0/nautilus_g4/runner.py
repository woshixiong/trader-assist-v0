"""Thin Nautilus rc5 execution seam for Ordinary VNext G4 development replay."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from trader_assist_v0.vnext_g4.contracts import (
    NAUTILUS_VERSION,
    REPRESENTATIVE_MARKET_FLOOR,
    CandidateManifest,
    ExecutionModelConfig,
)

if TYPE_CHECKING:
    from nautilus_trader.backtest import BacktestEngine
    from nautilus_trader.execution import ProbabilisticFillModel


def assert_exact_nautilus_rc5() -> None:
    from importlib.metadata import version

    installed = version("nautilus-trader")
    if installed != NAUTILUS_VERSION:
        raise RuntimeError(f"expected Nautilus {NAUTILUS_VERSION}, installed {installed}")


def build_fill_model(config: ExecutionModelConfig) -> ProbabilisticFillModel:
    """Map explicit project assumptions onto Nautilus' provider-owned fill model."""
    from nautilus_trader.execution import ProbabilisticFillModel

    assert_exact_nautilus_rc5()
    return ProbabilisticFillModel(
        prob_fill_on_limit=float(config.prob_fill_on_limit),
        prob_slippage=float(config.prob_slippage),
        random_seed=config.random_seed,
    )


def new_isolated_backtest_engine(candidate: CandidateManifest) -> BacktestEngine:
    """Create one fresh Nautilus engine per candidate; simulated state is never shared."""
    from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.model import TraderId

    assert_exact_nautilus_rc5()
    config = BacktestEngineConfig(
        trader_id=TraderId(f"VNEXT-G4-{candidate.candidate_hash[:16]}"),
        bypass_logging=True,
    )
    return BacktestEngine(config)


def assert_backtest_node_catalog_surface() -> None:
    """Fail closed unless the exact rc5 high-level catalog replay surface is available."""
    from nautilus_trader.backtest import BacktestNode
    from nautilus_trader.config import (
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
    )
    from nautilus_trader.persistence import ParquetDataCatalog

    assert_exact_nautilus_rc5()
    public_types = (
        BacktestNode,
        BacktestDataConfig,
        BacktestEngineConfig,
        BacktestRunConfig,
        BacktestVenueConfig,
        ParquetDataCatalog,
    )
    if not all(callable(item) for item in public_types):
        raise RuntimeError("exact rc5 high-level catalog replay surface is incomplete")
    required_methods = (
        "build",
        "run",
        "dispose",
        "generate_order_fills_report",
        "generate_positions_report",
        "generate_account_report",
    )
    missing = tuple(
        name
        for name in required_methods
        if not callable(getattr(BacktestNode, name, None))
    )
    if missing:
        raise RuntimeError(f"exact rc5 BacktestNode is missing public methods: {missing}")


def assert_representative_scale(market_ids: tuple[str, ...]) -> None:
    unique = set(market_ids)
    if len(unique) != len(market_ids):
        raise ValueError("representative-scale market identities must be unique")
    if len(unique) < REPRESENTATIVE_MARKET_FLOOR:
        raise ValueError(
            f"formal G4 scale requires at least {REPRESENTATIVE_MARKET_FLOOR} markets"
        )


def assert_actual_representative_scale(
    market_event_counts: Mapping[str, int],
    *,
    source_evidence_hashes: tuple[str, ...],
) -> tuple[str, ...]:
    """Accept G4E8 only for source-bound markets with actual retained events."""
    if not source_evidence_hashes:
        raise ValueError("actual representative scale requires source-bound E4 evidence")
    if any(len(value) != 64 for value in source_evidence_hashes):
        raise ValueError("representative-scale source evidence hashes must be SHA-256 hex")
    markets = tuple(sorted(market_event_counts))
    if not markets:
        raise ValueError("actual representative scale requires retained market evidence")
    if any(market_event_counts[market_id] <= 0 for market_id in markets):
        raise ValueError("each representative market must retain at least one causal event")
    assert_representative_scale(markets)
    return markets


def candidate_state_isolation_plan(
    candidates: tuple[CandidateManifest, ...],
) -> tuple[str, ...]:
    """Return exact candidate hashes requiring independent engine/context state."""
    hashes = tuple(candidate.candidate_hash for candidate in candidates)
    if len(hashes) != len(set(hashes)):
        raise ValueError("duplicate candidate identity would violate comparison isolation")
    return hashes
