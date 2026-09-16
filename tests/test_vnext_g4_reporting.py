from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.vnext_g4.contracts import ParticipationState, VNextEvaluationRecord
from trader_assist_v0.vnext_g4.reporting import ThesisOutcome, build_report

CANDIDATE = "a" * 64


def evaluation(package: str, state: ParticipationState, reason: str) -> VNextEvaluationRecord:
    return VNextEvaluationRecord.create(
        package_id=package,
        candidate_hash=CANDIDATE,
        feature_hash="b" * 64,
        participation=state,
        activation=state is ParticipationState.TAKE,
        stop_triggered=False,
        winner_confirmed=False,
        exit_triggered=False,
        can_reenter=False,
        order_intent="MARKETABLE_ENTRY" if state is ParticipationState.TAKE else "NONE",
        reason_codes=(reason,),
    )


def outcome(item: VNextEvaluationRecord, thesis: str, net_r: Decimal) -> ThesisOutcome:
    return ThesisOutcome.create(
        thesis_id=thesis,
        package_id=item.package_id,
        candidate_hash=CANDIDATE,
        evaluation_hash=item.record_hash,
        execution_result_hash=None,
        attempt_count=1,
        gross_r=net_r + Decimal("0.1"),
        net_r_after_cost=net_r,
        fee_bps=Decimal("1"),
        spread_slippage_bps=Decimal("2"),
        funding_bps=Decimal("0"),
        market_mfe_bps=None,
        market_mae_bps=None,
        executable_mfe_bps=None,
        executable_mae_bps=None,
        missed_winner_bps=None,
        not_evaluable_reason=None,
    )


def test_report_retains_full_denominator_and_no_composite_score() -> None:
    take_a = evaluation("pkg-a", ParticipationState.TAKE, "TAKE")
    take_b = evaluation("pkg-b", ParticipationState.TAKE, "TAKE")
    not_eval = evaluation("pkg-c", ParticipationState.NOT_EVALUABLE, "DATA_GAP")
    passed = evaluation("pkg-d", ParticipationState.PASS, "FRICTION")
    report = build_report(
        candidate_hash=CANDIDATE,
        evaluations=(take_a, take_b, not_eval, passed),
        outcomes=(
            outcome(take_a, "thesis-a", Decimal("2")),
            outcome(take_b, "thesis-b", Decimal("1")),
        ),
    )
    assert report.evaluation_count == 4
    assert sum(report.denominator.values()) == 4
    assert report.denominator["TAKE"] == 2
    assert report.denominator["NOT_EVALUABLE"] == 1
    assert report.not_evaluable_reasons["DATA_GAP"] == 1
    assert report.total_net_r_after_cost == Decimal("3")
    assert report.mean_net_r_after_cost == Decimal("1.5")
    assert report.top1_winner_contribution_ratio == Decimal("2") / Decimal("3")
    assert "score" not in report.model_dump()


def test_report_is_deterministic_for_same_evidence() -> None:
    item = evaluation("pkg-a", ParticipationState.TAKE, "TAKE")
    first = build_report(
        candidate_hash=CANDIDATE,
        evaluations=(item,),
        outcomes=(outcome(item, "thesis-a", Decimal("1")),),
    )
    second = build_report(
        candidate_hash=CANDIDATE,
        evaluations=(item,),
        outcomes=(outcome(item, "thesis-a", Decimal("1")),),
    )
    assert first.report_hash == second.report_hash
