"""Deterministic Thesis-level G4 reporting over development evidence."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import ParticipationDecision


class ThesisOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_id: str = Field(min_length=1, max_length=160)
    market_id: str = Field(min_length=1, max_length=160)
    decision: ParticipationDecision
    attempt_count: int = Field(ge=0, le=2)
    net_r_after_cost: Decimal | None = None
    fee_bps: Decimal = Field(ge=0)
    spread_slippage_bps: Decimal = Field(ge=0)
    funding_bps: Decimal = Decimal("0")
    market_mfe_bps: Decimal | None = None
    market_mae_bps: Decimal | None = None
    executable_mfe_bps: Decimal | None = None
    executable_mae_bps: Decimal | None = None
    missed_winner_bps: Decimal | None = None
    not_evaluable_reason: str | None = None


class G4DevelopmentReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_count: int = Field(ge=0)
    denominator_counts: dict[str, int]
    evaluated_theses: int = Field(ge=0)
    not_evaluable_theses: int = Field(ge=0)
    net_r_sum_after_cost: Decimal
    attempt_count_sum: int = Field(ge=0)
    total_explicit_friction_bps: Decimal = Field(ge=0)
    confirmatory_e5: bool = False


def build_development_report(outcomes: tuple[ThesisOutcome, ...]) -> G4DevelopmentReport:
    """Retain the full denominator and never relabel G4 as confirmatory E5."""
    counts = Counter(item.decision.value for item in outcomes)
    not_evaluable = sum(
        item.decision is ParticipationDecision.NOT_EVALUABLE for item in outcomes
    )
    evaluated = sum(item.net_r_after_cost is not None for item in outcomes)
    net_r_sum = sum(
        (item.net_r_after_cost for item in outcomes if item.net_r_after_cost is not None),
        start=Decimal("0"),
    )
    friction = sum(
        (item.fee_bps + item.spread_slippage_bps + item.funding_bps for item in outcomes),
        start=Decimal("0"),
    )
    return G4DevelopmentReport(
        thesis_count=len(outcomes),
        denominator_counts=dict(sorted(counts.items())),
        evaluated_theses=evaluated,
        not_evaluable_theses=not_evaluable,
        net_r_sum_after_cost=net_r_sum,
        attempt_count_sum=sum(item.attempt_count for item in outcomes),
        total_explicit_friction_bps=friction,
        confirmatory_e5=False,
    )
