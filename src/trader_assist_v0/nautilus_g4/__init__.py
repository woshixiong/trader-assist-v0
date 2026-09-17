"""Thin Nautilus-owned execution/replay integration for Ordinary VNext G4."""

from .catalog_bridge import TRANSFORM_VERSION, bind_rebuildable_cache, build_replay_payload
from .runner import (
    assert_exact_nautilus_rc5,
    assert_representative_scale,
    build_fill_model,
    candidate_state_isolation_plan,
    new_isolated_backtest_engine,
)

__all__ = [
    "TRANSFORM_VERSION",
    "assert_exact_nautilus_rc5",
    "assert_representative_scale",
    "bind_rebuildable_cache",
    "build_fill_model",
    "build_replay_payload",
    "candidate_state_isolation_plan",
    "new_isolated_backtest_engine",
]
