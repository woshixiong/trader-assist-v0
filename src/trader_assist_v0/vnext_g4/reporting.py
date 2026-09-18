"""Deterministic Thesis-level G4 evidence projection over provider-owned state."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex

from .contracts import ParticipationDecision


class CostProvenance(StrEnum):
    OBSERVED = "OBSERVED"
    MODELLED = "MODELLED"
    PROVEN_ZERO = "PROVEN_ZERO"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"


class CostComponent(BaseModel):
    """One explicit cost component; missing and zero are disjoint states."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    amount_bps: Decimal | None = Field(default=None, ge=0)
    provenance: CostProvenance
    source_hash: Sha256Hex | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        if self.provenance is CostProvenance.MISSING:
            if self.amount_bps is not None or self.source_hash is not None or self.reason is None:
                raise ValueError("missing cost requires a reason and cannot carry zero/source")
            return self
        if self.source_hash is None:
            raise ValueError("non-missing cost provenance requires a source hash")
        if self.provenance is CostProvenance.NOT_APPLICABLE:
            if self.amount_bps is not None:
                raise ValueError("not-applicable cost cannot carry a numeric amount")
            return self
        if self.amount_bps is None:
            raise ValueError("observed/modelled/proven-zero cost requires an exact amount")
        if self.provenance is CostProvenance.PROVEN_ZERO and self.amount_bps != 0:
            raise ValueError("PROVEN_ZERO must carry exact zero")
        return self

    @property
    def complete_amount(self) -> Decimal | None:
        if self.provenance is CostProvenance.MISSING:
            return None
        if self.provenance is CostProvenance.NOT_APPLICABLE:
            return Decimal("0")
        assert self.amount_bps is not None
        return self.amount_bps


class ThesisOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_id: str = Field(min_length=1, max_length=160)
    market_id: str = Field(min_length=1, max_length=160)
    provider_state_source_hash: Sha256Hex
    order_intent_hash: Sha256Hex | None = None
    decision: ParticipationDecision
    attempt_count: int = Field(ge=0, le=2)
    net_r_after_cost: Decimal | None = None
    fee: CostComponent
    spread: CostComponent
    slippage: CostComponent
    impact_size_feasibility: CostComponent
    funding: CostComponent
    implementation_shortfall: CostComponent
    market_mfe_bps: Decimal | None = None
    market_mae_bps: Decimal | None = None
    executable_mfe_bps: Decimal | None = None
    executable_mae_bps: Decimal | None = None
    missed_winner_bps: Decimal | None = None
    not_evaluable_reason: str | None = None

    @model_validator(mode="after")
    def validate_outcome_binding(self) -> Self:
        if self.decision is ParticipationDecision.TAKE and self.order_intent_hash is None:
            raise ValueError("TAKE outcome requires its canonical OrderIntent hash")
        if (
            self.decision is ParticipationDecision.NOT_EVALUABLE
            and self.not_evaluable_reason is None
        ):
            raise ValueError("NOT_EVALUABLE outcome requires a typed reason")
        return self

    @property
    def explicit_friction_bps(self) -> Decimal | None:
        components = (
            self.fee,
            self.spread,
            self.slippage,
            self.impact_size_feasibility,
            self.funding,
        )
        amounts = tuple(item.complete_amount for item in components)
        if any(item is None for item in amounts):
            return None
        return sum((item for item in amounts if item is not None), start=Decimal("0"))


class G4DevelopmentReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_count: int = Field(ge=0)
    denominator_counts: dict[str, int]
    evaluated_theses: int = Field(ge=0)
    not_evaluable_theses: int = Field(ge=0)
    cost_complete_theses: int = Field(ge=0)
    cost_incomplete_theses: int = Field(ge=0)
    net_r_sum_after_cost: Decimal
    attempt_count_sum: int = Field(ge=0)
    total_explicit_friction_bps: Decimal | None
    confirmatory_e5: bool = False


def build_development_report(outcomes: tuple[ThesisOutcome, ...]) -> G4DevelopmentReport:
    """Retain the full denominator and never coerce missing cost to numeric zero."""
    counts = Counter(item.decision.value for item in outcomes)
    not_evaluable = sum(
        item.decision is ParticipationDecision.NOT_EVALUABLE for item in outcomes
    )
    evaluated = sum(item.net_r_after_cost is not None for item in outcomes)
    net_r_sum = sum(
        (item.net_r_after_cost for item in outcomes if item.net_r_after_cost is not None),
        start=Decimal("0"),
    )
    friction_values = tuple(item.explicit_friction_bps for item in outcomes)
    cost_incomplete = sum(item is None for item in friction_values)
    total_friction = (
        None
        if cost_incomplete
        else sum(
            (item for item in friction_values if item is not None),
            start=Decimal("0"),
        )
    )
    return G4DevelopmentReport(
        thesis_count=len(outcomes),
        denominator_counts=dict(sorted(counts.items())),
        evaluated_theses=evaluated,
        not_evaluable_theses=not_evaluable,
        cost_complete_theses=len(outcomes) - cost_incomplete,
        cost_incomplete_theses=cost_incomplete,
        net_r_sum_after_cost=net_r_sum,
        attempt_count_sum=sum(item.attempt_count for item in outcomes),
        total_explicit_friction_bps=total_friction,
        confirmatory_e5=False,
    )
