"""Deterministic Thesis-level G4 reporting over typed evaluation/execution evidence."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trader_assist_v0.contracts.common import (
    FiniteDecimal,
    NonNegativeFiniteDecimal,
    OpaqueId,
    Sha256Hex,
    canonical_json_bytes,
    sha256_hex,
)

from .contracts import ParticipationState, SimulatedExecutionResult, VNextEvaluationRecord

_REPORT_DOMAIN = b"trader-assist-v0/vnext-g4/report/v1\0"
_OUTCOME_DOMAIN = b"trader-assist-v0/vnext-g4/outcome/v1\0"


class ThesisOutcome(BaseModel):
    """One Thesis economic record; unsupported values remain absent, never fabricated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis_id: OpaqueId
    package_id: OpaqueId
    candidate_hash: Sha256Hex
    evaluation_hash: Sha256Hex
    execution_result_hash: Sha256Hex | None = None
    attempt_count: int = Field(default=1, ge=1, le=2)
    gross_r: FiniteDecimal | None = None
    net_r_after_cost: FiniteDecimal | None = None
    fee_bps: NonNegativeFiniteDecimal = Decimal("0")
    spread_slippage_bps: NonNegativeFiniteDecimal = Decimal("0")
    funding_bps: FiniteDecimal = Decimal("0")
    market_mfe_bps: NonNegativeFiniteDecimal | None = None
    market_mae_bps: NonNegativeFiniteDecimal | None = None
    executable_mfe_bps: NonNegativeFiniteDecimal | None = None
    executable_mae_bps: NonNegativeFiniteDecimal | None = None
    missed_winner_bps: NonNegativeFiniteDecimal | None = None
    not_evaluable_reason: str | None = Field(default=None, max_length=160)
    outcome_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"outcome_hash"})

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        expected = sha256_hex(_OUTCOME_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if self.outcome_hash != expected:
            raise ValueError("outcome_hash mismatch")
        return self

    @classmethod
    def create(cls, **values: object) -> Self:
        payload = dict(values)
        digest = sha256_hex(_OUTCOME_DOMAIN + canonical_json_bytes(payload))
        return cls.model_validate({**payload, "outcome_hash": digest})


class G4Report(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_hash: Sha256Hex
    evaluation_count: int = Field(ge=0)
    denominator: dict[str, int]
    not_evaluable_reasons: dict[str, int]
    completed_outcomes: int = Field(ge=0)
    total_net_r_after_cost: FiniteDecimal | None
    mean_net_r_after_cost: FiniteDecimal | None
    total_fee_bps: NonNegativeFiniteDecimal
    total_spread_slippage_bps: NonNegativeFiniteDecimal
    winner_count: int = Field(ge=0)
    top1_winner_contribution_ratio: NonNegativeFiniteDecimal | None
    report_hash: Sha256Hex

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"report_hash"})

    @model_validator(mode="after")
    def validate_report(self) -> Self:
        if sum(self.denominator.values()) != self.evaluation_count:
            raise ValueError("denominator must retain every evaluation")
        expected = sha256_hex(_REPORT_DOMAIN + canonical_json_bytes(self.identity_payload()))
        if self.report_hash != expected:
            raise ValueError("report_hash mismatch")
        return self


def build_report(
    *,
    candidate_hash: str,
    evaluations: tuple[VNextEvaluationRecord, ...],
    outcomes: tuple[ThesisOutcome, ...],
) -> G4Report:
    if any(item.candidate_hash != candidate_hash for item in evaluations):
        raise ValueError("evaluation candidate mismatch")
    if any(item.candidate_hash != candidate_hash for item in outcomes):
        raise ValueError("outcome candidate mismatch")

    denominator = Counter(item.participation.value for item in evaluations)
    for state in ParticipationState:
        denominator.setdefault(state.value, 0)
    ne_reasons: Counter[str] = Counter()
    evaluation_by_hash = {item.record_hash: item for item in evaluations}
    for item in evaluations:
        if item.participation is ParticipationState.NOT_EVALUABLE:
            for reason in item.reason_codes:
                ne_reasons[reason] += 1

    net_values: list[Decimal] = []
    winner_values: list[Decimal] = []
    fee_total = Decimal("0")
    slippage_total = Decimal("0")
    for outcome in outcomes:
        if outcome.evaluation_hash not in evaluation_by_hash:
            raise ValueError("outcome references an unknown evaluation")
        fee_total += Decimal(outcome.fee_bps)
        slippage_total += Decimal(outcome.spread_slippage_bps)
        if outcome.net_r_after_cost is not None:
            value = Decimal(outcome.net_r_after_cost)
            net_values.append(value)
            if value > 0:
                winner_values.append(value)

    total_net = sum(net_values, Decimal("0")) if net_values else None
    mean_net = (
        total_net / Decimal(len(net_values))
        if total_net is not None and net_values
        else None
    )
    top1_ratio: Decimal | None = None
    winner_total = sum(winner_values, Decimal("0"))
    if winner_values and winner_total > 0:
        top1_ratio = max(winner_values) / winner_total

    payload: dict[str, object] = {
        "candidate_hash": candidate_hash,
        "evaluation_count": len(evaluations),
        "denominator": dict(sorted(denominator.items())),
        "not_evaluable_reasons": dict(sorted(ne_reasons.items())),
        "completed_outcomes": len(net_values),
        "total_net_r_after_cost": total_net,
        "mean_net_r_after_cost": mean_net,
        "total_fee_bps": fee_total,
        "total_spread_slippage_bps": slippage_total,
        "winner_count": len(winner_values),
        "top1_winner_contribution_ratio": top1_ratio,
    }
    digest = sha256_hex(_REPORT_DOMAIN + canonical_json_bytes(payload))
    return G4Report.model_validate({**payload, "report_hash": digest})


def bind_execution_outcome(
    *,
    thesis_id: str,
    evaluation: VNextEvaluationRecord,
    execution: SimulatedExecutionResult | None,
    attempt_count: int,
    gross_r: Decimal | None = None,
    net_r_after_cost: Decimal | None = None,
    fee_bps: Decimal = Decimal("0"),
    spread_slippage_bps: Decimal = Decimal("0"),
    funding_bps: Decimal = Decimal("0"),
    not_evaluable_reason: str | None = None,
) -> ThesisOutcome:
    if execution is not None and execution.candidate_hash != evaluation.candidate_hash:
        raise ValueError("execution candidate mismatch")
    return ThesisOutcome.create(
        thesis_id=thesis_id,
        package_id=evaluation.package_id,
        candidate_hash=evaluation.candidate_hash,
        evaluation_hash=evaluation.record_hash,
        execution_result_hash=None if execution is None else execution.result_hash,
        attempt_count=attempt_count,
        gross_r=gross_r,
        net_r_after_cost=net_r_after_cost,
        fee_bps=fee_bps,
        spread_slippage_bps=spread_slippage_bps,
        funding_bps=funding_bps,
        market_mfe_bps=None,
        market_mae_bps=None,
        executable_mfe_bps=None,
        executable_mae_bps=None,
        missed_winner_bps=None,
        not_evaluable_reason=not_evaluable_reason,
    )
