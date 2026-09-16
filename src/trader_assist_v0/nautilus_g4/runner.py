"""Thin Nautilus rc5 execution seam for Ordinary VNext G4 development replay."""

from __future__ import annotations

from typing import TYPE_CHECKING

from trader_assist_v0.vnext_g4.contracts import (
    NAUTILUS_VERSION,
    REPRESENTATIVE_MARKET_FLOOR,
    CandidateManifest,
    ExecutionModelConfig,
)

if TYPE_CHECKING:
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.backtest.models import FillModel


def assert_exact_nautilus_rc5() -> None:
    from importlib.metadata import version

    installed = version("nautilus-trader")
    if installed != NAUTILUS_VERSION:
        raise RuntimeError(f"expected Nautilus {NAUTILUS_VERSION}, installed {installed}")


def build_fill_model(config: ExecutionModelConfig) -> FillModel:
    """Map explicit project assumptions onto Nautilus' provider-owned FillModel."""
    from nautilus_trader.backtest.models import FillModel

    assert_exact_nautilus_rc5()
    return FillModel(
        prob_fill_on_limit=float(config.prob_fill_on_limit),
        prob_slippage=float(config.prob_slippage),
        random_seed=config.random_seed,
    )


def new_isolated_backtest_engine(candidate: CandidateManifest) -> BacktestEngine:
    """Create one fresh Nautilus engine per candidate; simulated state is never shared."""
    from nautilus_trader.backtest.config import BacktestEngineConfig
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.config import LoggingConfig
    from nautilus_trader.model import TraderId

    assert_exact_nautilus_rc5()
    config = BacktestEngineConfig(
        trader_id=TraderId(f"VNEXT-G4-{candidate.candidate_hash[:16]}"),
        logging=LoggingConfig(log_level="ERROR"),
    )
    return BacktestEngine(config=config)


def assert_representative_scale(market_ids: tuple[str, ...]) -> None:
    unique = set(market_ids)
    if len(unique) != len(market_ids):
        raise ValueError("representative-scale market identities must be unique")
    if len(unique) < REPRESENTATIVE_MARKET_FLOOR:
        raise ValueError(
            f"formal G4 scale requires at least {REPRESENTATIVE_MARKET_FLOOR} markets"
        )


def candidate_state_isolation_plan(candidates: tuple[CandidateManifest, ...]) -> tuple[str, ...]:
    """Return the exact candidate hashes that each require an independent engine/context."""
    hashes = tuple(candidate.candidate_hash for candidate in candidates)
    if len(hashes) != len(set(hashes)):
        raise ValueError("duplicate candidate identity would violate comparison isolation")
    return hashes
