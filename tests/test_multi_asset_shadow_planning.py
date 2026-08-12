from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.multi_asset_shadow.planning import (
    EntryQuality,
    PlanInputs,
    PlanRejection,
    PublicBbo,
    Side,
    make_plan,
)


def test_long_plan_uses_current_ask_and_is_never_submitted() -> None:
    plan = make_plan(
        PlanInputs(
            side=Side.LONG,
            ideal_entry_low=Decimal("100"),
            ideal_entry_high=Decimal("101"),
            chase_limit=Decimal("102"),
            structural_stop=Decimal("98"),
            structural_target=Decimal("105"),
        ),
        PublicBbo(Decimal("100.80"), Decimal("101"), Decimal("1")),
    )
    assert not isinstance(plan, PlanRejection)
    assert plan.planned_entry == Decimal("101")
    assert plan.entry_quality is EntryQuality.IDEAL
    assert plan.tp1 == Decimal("104")
    assert plan.submission_status == "NOT_SUBMITTED"


def test_short_chase_and_liquidity_gates_fail_closed() -> None:
    inputs = PlanInputs(
        side=Side.SHORT,
        ideal_entry_low=Decimal("99"),
        ideal_entry_high=Decimal("100"),
        chase_limit=Decimal("98"),
        structural_stop=Decimal("102"),
        structural_target=Decimal("95"),
    )
    assert (
        make_plan(inputs, PublicBbo(Decimal("97.80"), Decimal("98"), Decimal("1")))
        is PlanRejection.CHASE_LIMIT_EXCEEDED
    )
    assert (
        make_plan(inputs, PublicBbo(Decimal("99.80"), Decimal("100"), Decimal("11")))
        is PlanRejection.BBO_STALE
    )
