from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.vnext_g4.contracts import ParticipationDecision
from trader_assist_v0.vnext_g4.reporting import (
    CostComponent,
    CostProvenance,
    ThesisOutcome,
    build_development_report,
)

SOURCE = "a" * 64


def cost(value: str, provenance: CostProvenance = CostProvenance.MODELLED) -> CostComponent:
    return CostComponent(
        amount_bps=Decimal(value),
        provenance=provenance,
        source_hash=SOURCE,
    )


def not_applicable() -> CostComponent:
    return CostComponent(
        provenance=CostProvenance.NOT_APPLICABLE,
        source_hash=SOURCE,
        reason="SOURCE_CONTRACT_PROVES_NOT_APPLICABLE",
    )


def outcome(**updates: object) -> ThesisOutcome:
    values: dict[str, object] = {
        "thesis_id": "thesis-1",
        "market_id": "market-1",
        "provider_state_source_hash": SOURCE,
        "order_intent_hash": "b" * 64,
        "decision": ParticipationDecision.TAKE,
        "attempt_count": 1,
        "net_r_after_cost": Decimal("0.5"),
        "fee": cost("1"),
        "spread": cost("1"),
        "slippage": cost("1"),
        "impact_size_feasibility": cost("0", CostProvenance.PROVEN_ZERO),
        "funding": not_applicable(),
        "implementation_shortfall": cost("3"),
    }
    values.update(updates)
    return ThesisOutcome.model_validate(values)


def test_full_denominator_and_after_cost_totals_are_retained() -> None:
    no_trade = {
        "order_intent_hash": None,
        "attempt_count": 0,
        "net_r_after_cost": None,
        "fee": not_applicable(),
        "spread": not_applicable(),
        "slippage": not_applicable(),
        "impact_size_feasibility": not_applicable(),
        "funding": not_applicable(),
        "implementation_shortfall": not_applicable(),
    }
    outcomes = (
        outcome(),
        outcome(
            thesis_id="thesis-2",
            market_id="market-2",
            decision=ParticipationDecision.PASS,
            **no_trade,
        ),
        outcome(
            thesis_id="thesis-3",
            market_id="market-3",
            decision=ParticipationDecision.NOT_EVALUABLE,
            not_evaluable_reason="GAPPED",
            **no_trade,
        ),
    )
    report = build_development_report(outcomes)
    assert report.thesis_count == 3
    assert report.denominator_counts == {"NOT_EVALUABLE": 1, "PASS": 1, "TAKE": 1}
    assert report.evaluated_theses == 1
    assert report.not_evaluable_theses == 1
    assert report.net_r_sum_after_cost == Decimal("0.5")
    assert report.total_explicit_friction_bps == Decimal("3")
    assert report.cost_complete_theses == 3
    assert report.confirmatory_e5 is False


def test_missing_cost_is_not_silently_zero() -> None:
    missing = CostComponent(
        provenance=CostProvenance.MISSING,
        reason="NO_SOURCE_BOUND_IMPACT_EVIDENCE",
    )
    report = build_development_report((outcome(impact_size_feasibility=missing),))
    assert report.total_explicit_friction_bps is None
    assert report.cost_complete_theses == 0
    assert report.cost_incomplete_theses == 1
