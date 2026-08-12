from __future__ import annotations

from decimal import Decimal

from trader_assist_v0.multi_asset_shadow.planning import (
    CostModel,
    EntryQuality,
    LiquidityAssessment,
    PlanInputs,
    PlanRejection,
    PublicBbo,
    Side,
    assess_l2,
    make_plan,
    minimum_tick,
)


def liquidity(side: Side, *, slippage: str = "1") -> LiquidityAssessment:
    return LiquidityAssessment(
        market_id="market",
        coin="BTC",
        side=side,
        observed_at_ms=1_000,
        best_bid=Decimal("100.80"),
        best_ask=Decimal("101"),
        reference_notional_usd=Decimal("1000"),
        depth_consumed=((Decimal("101"), Decimal("9.91")),),
        executable_price=Decimal("101"),
        one_way_slippage_bps=Decimal(slippage),
        sufficient_depth=True,
        provenance_hash="a" * 64,
    )


def costs() -> CostModel:
    return CostModel("r1", Decimal("4.5"), Decimal("2"), Decimal("5"))


def test_long_plan_uses_current_ask_and_is_never_submitted() -> None:
    plan = make_plan(
        PlanInputs(
            market_id="market",
            side=Side.LONG,
            ideal_entry_low=Decimal("100"),
            ideal_entry_high=Decimal("101"),
            chase_limit=Decimal("102"),
            structural_stop=Decimal("98"),
            structural_target=Decimal("105"),
            liquidity=liquidity(Side.LONG),
            cost_model=costs(),
            now_ms=1_001,
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
        market_id="market",
        side=Side.SHORT,
        ideal_entry_low=Decimal("99"),
        ideal_entry_high=Decimal("100"),
        chase_limit=Decimal("98"),
        structural_stop=Decimal("102"),
        structural_target=Decimal("95"),
        liquidity=liquidity(Side.SHORT),
        cost_model=costs(),
        now_ms=1_001,
    )
    assert (
        make_plan(inputs, PublicBbo(Decimal("97.80"), Decimal("98"), Decimal("1")))
        is PlanRejection.CHASE_LIMIT_EXCEEDED
    )
    assert (
        make_plan(inputs, PublicBbo(Decimal("99.80"), Decimal("100"), Decimal("11")))
        is PlanRejection.BBO_INVALID_OR_STALE
    )


def test_l2_hard_gate_consumes_1000_and_does_not_use_cost_model_default() -> None:
    long = assess_l2(
        market_id="market",
        coin="BTC",
        side=Side.LONG,
        observed_at_ms=1_000,
        best_bid=Decimal("99"),
        best_ask=Decimal("100"),
        levels=((Decimal("100"), Decimal("5")), (Decimal("101"), Decimal("5"))),
        provenance_hash="b" * 64,
    )
    short = assess_l2(
        market_id="market",
        coin="BTC",
        side=Side.SHORT,
        observed_at_ms=1_000,
        best_bid=Decimal("100"),
        best_ask=Decimal("101"),
        levels=((Decimal("100"), Decimal("5")), (Decimal("99"), Decimal("6"))),
        provenance_hash="c" * 64,
    )
    assert long.sufficient_depth and long.executable_price == Decimal(
        "100.4975124378109452736318408"
    )
    assert short.sufficient_depth and short.one_way_slippage_bps is not None
    assert short.one_way_slippage_bps > 0
    insufficient = assess_l2(
        market_id="market",
        coin="BTC",
        side=Side.LONG,
        observed_at_ms=1_000,
        best_bid=Decimal("99"),
        best_ask=Decimal("100"),
        levels=((Decimal("100"), Decimal("1")),),
        provenance_hash="d" * 64,
    )
    assert not insufficient.sufficient_depth
    missing = PlanInputs(
        market_id="market",
        side=Side.LONG,
        ideal_entry_low=Decimal("99"),
        ideal_entry_high=Decimal("101"),
        chase_limit=Decimal("102"),
        structural_stop=Decimal("98"),
        structural_target=Decimal("105"),
        liquidity=None,
        cost_model=costs(),
        now_ms=1_001,
    )
    assert (
        make_plan(missing, PublicBbo(Decimal("99"), Decimal("100"), Decimal("1")))
        is PlanRejection.LIQUIDITY_HARD_LIMIT
    )


def test_price_precision_has_positive_variable_tick_and_never_improves_touch() -> None:
    assert minimum_tick(Decimal("0.001234"), max_decimals=4) > 0
    assert minimum_tick(Decimal("123456"), max_decimals=4) > minimum_tick(
        Decimal("12"), max_decimals=4
    )
