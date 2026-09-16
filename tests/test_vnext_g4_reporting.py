from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.vnext_g4.contracts import ParticipationDecision
from trader_assist_v0.vnext_g4.reporting import ThesisOutcome, build_development_report


def test_full_denominator_and_after_cost_totals_are_retained() -> None:
    outcomes = (
        ThesisOutcome(
            thesis_id="thesis-1",
            market_id="market-1",
            decision=ParticipationDecision.TAKE,
            attempt_count=1,
            net_r_after_cost=Decimal("0.5"),
            fee_bps=Decimal("1"),
            spread_slippage_bps=Decimal("2"),
        ),
        ThesisOutcome(
            thesis_id="thesis-2",
            market_id="market-2",
            decision=ParticipationDecision.PASS,
            attempt_count=0,
            net_r_after_cost=None,
            fee_bps=Decimal("0"),
            spread_slippage_bps=Decimal("0"),
        ),
        ThesisOutcome(
            thesis_id="thesis-3",
            market_id="market-3",
            decision=ParticipationDecision.NOT_EVALUABLE,
            attempt_count=0,
            net_r_after_cost=None,
            fee_bps=Decimal("0"),
            spread_slippage_bps=Decimal("0"),
            not_evaluable_reason="GAPPED",
        ),
    )
    report = build_development_report(outcomes)
    assert report.thesis_count == 3
    assert report.denominator_counts == {"NOT_EVALUABLE": 1, "PASS": 1, "TAKE": 1}
    assert report.evaluated_theses == 1
    assert report.not_evaluable_theses == 1
    assert report.net_r_sum_after_cost == Decimal("0.5")
    assert report.total_explicit_friction_bps == Decimal("3")
    assert report.confirmatory_e5 is False
