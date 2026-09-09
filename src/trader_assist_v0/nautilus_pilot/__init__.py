"""Trade OS-owned contracts and Strategy package for the Nautilus E3 pilot.

The optional Nautilus host is deliberately not imported here. Normal project
imports therefore remain independent of the pilot dependency.
"""

from .contracts import (
    E3_AUTHORITY_MARKER,
    PilotEvaluationEnvelope,
    StrategyInputEvent,
    close_boundary_ns,
)
from .strategy_package import (
    STRATEGY_PACKAGE_VERSION,
    PilotStrategyEvaluator,
    StrategyPackageManifest,
    select_strategy_package,
)

__all__ = [
    "E3_AUTHORITY_MARKER",
    "STRATEGY_PACKAGE_VERSION",
    "PilotEvaluationEnvelope",
    "PilotStrategyEvaluator",
    "StrategyInputEvent",
    "StrategyPackageManifest",
    "close_boundary_ns",
    "select_strategy_package",
]
