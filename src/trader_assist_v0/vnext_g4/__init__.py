"""Ordinary VNext G4 project-owned Strategy/evidence semantics."""

from .contracts import (
    AttemptPolicy,
    EntryActivation,
    ExecutionModelConfig,
    ExitPolicy,
    G4RunManifest,
    ParticipationState,
    ReentryPolicy,
    SimulatedExecutionResult,
    VNextCandidateConfig,
    VNextEvaluationRecord,
    VNextFeatureSnapshot,
    WinnerAdd,
    WinnerConfirmation,
)
from .evaluator import evaluate_vnext
from .reporting import G4Report, ThesisOutcome, bind_execution_outcome, build_report

__all__ = [
    "AttemptPolicy",
    "EntryActivation",
    "ExecutionModelConfig",
    "ExitPolicy",
    "G4Report",
    "G4RunManifest",
    "ParticipationState",
    "ReentryPolicy",
    "SimulatedExecutionResult",
    "ThesisOutcome",
    "VNextCandidateConfig",
    "VNextEvaluationRecord",
    "VNextFeatureSnapshot",
    "WinnerAdd",
    "WinnerConfirmation",
    "bind_execution_outcome",
    "build_report",
    "evaluate_vnext",
]
