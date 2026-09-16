"""Thin Nautilus-owned G4 replay/simulation integration seams."""

from .catalog_bridge import DerivedCatalogBinding, bind_e4_source, build_empty_provider_catalog
from .runner import (
    CandidateSimulationContext,
    assert_exact_rc5,
    build_candidate_simulation_context,
    build_isolated_candidate_contexts,
    dispose_candidate_contexts,
)

__all__ = [
    "CandidateSimulationContext",
    "DerivedCatalogBinding",
    "assert_exact_rc5",
    "bind_e4_source",
    "build_candidate_simulation_context",
    "build_empty_provider_catalog",
    "build_isolated_candidate_contexts",
    "dispose_candidate_contexts",
]
