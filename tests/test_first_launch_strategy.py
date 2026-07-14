from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.first_launch.market_data import Candle, DataQualityState, RawEvidence
from trader_assist_v0.first_launch.strategy import (
    AIExplanation,
    PlanError,
    PreparedSetup,
    SetupFamily,
    Side,
    SignalState,
    _round_price,
    advance_prepare,
    bounded_explanation,
    build_plan,
    fallback_explanation,
    inward_zone,
    lifecycle_state,
    risk_math,
    round_quantity,
    size_plan,
    strategy_output,
)

NOW = datetime(2026, 7, 14, tzinfo=UTC)


def _plan(side: Side = Side.LONG):
    return build_plan(
        setup_id="a" * 64,
        side=side,
        speed="FAST",
        boundary=Decimal("100"),
        atr=Decimal("10"),
        sweep=Decimal("98") if side is Side.LONG else Decimal("102"),
        reference=Decimal("101") if side is Side.LONG else Decimal("99"),
        equity=Decimal("1000"),
        sz_decimals=3,
        created_at=NOW,
    )


def test_risk_is_decimal_capped_and_plan_is_immutable() -> None:
    result = size_plan(
        side=Side.LONG,
        entry=Decimal("100"),
        stop=Decimal("98"),
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    assert result.planned_risk <= result.risk_budget
    plan = _plan()
    assert plan.planned_entry <= plan.chase_limit
    with pytest.raises(AttributeError):
        plan.quantity = Decimal("1")  # type: ignore[misc]


def test_short_mirror_and_chase_rejection() -> None:
    short = _plan(Side.SHORT)
    assert short.stop > short.planned_entry > short.tp1 > short.tp2
    with pytest.raises(PlanError, match="CHASE"):
        build_plan(
            setup_id="b" * 64,
            side=Side.LONG,
            speed="FAST",
            boundary=Decimal("100"),
            atr=Decimal("10"),
            sweep=Decimal("98"),
            reference=Decimal("103"),
            equity=Decimal("1000"),
            sz_decimals=3,
            created_at=NOW,
        )


class _BadAI:
    def explain(self, summary: dict[str, str]) -> AIExplanation:
        del summary
        return AIExplanation((), (), (), (), ("x" * 241,), "AVAILABLE")


def test_ai_failure_is_non_authoritative_and_uses_fallback() -> None:
    plan = _plan()
    result = bounded_explanation(_BadAI(), plan, DataQualityState.READY)
    assert result.status == "UNAVAILABLE"
    assert "DO NOT CHASE" in result.risk_and_expiry_warnings


def test_ai_explanation_is_immutable() -> None:
    explanation = fallback_explanation(_plan(), DataQualityState.READY)
    with pytest.raises(AttributeError):
        explanation.status = "UNAVAILABLE"  # type: ignore[misc]


def test_ai_fallback_is_deterministic() -> None:
    plan = _plan()
    assert fallback_explanation(plan, DataQualityState.READY) == fallback_explanation(
        plan, DataQualityState.READY
    )


def test_ai_provider_receives_exact_summary_and_preserves_plan_identity() -> None:
    class CapturingAI:
        summary: dict[str, str] | None = None

        def explain(self, summary: dict[str, str]) -> AIExplanation:
            self.summary = summary
            return AIExplanation(("support",), (), (), (), ("check",), "AVAILABLE")

    plan = _plan()
    quality = DataQualityState.READY
    provider = CapturingAI()
    plan_id, canonical_hash = plan.plan_id, plan.canonical_hash
    result = bounded_explanation(provider, plan, quality)
    assert provider.summary == {
        "side": plan.side.value,
        "speed": plan.speed,
        "quality": quality.value,
    }
    assert result == AIExplanation(("support",), (), (), (), ("check",), "AVAILABLE")
    assert (plan.plan_id, plan.canonical_hash) == (plan_id, canonical_hash)


def test_ai_provider_exception_uses_deterministic_unavailable_fallback() -> None:
    class RaisingAI:
        def explain(self, summary: dict[str, str]) -> AIExplanation:
            del summary
            raise RuntimeError("unavailable")

    plan = _plan()
    first = bounded_explanation(RaisingAI(), plan, DataQualityState.READY)
    second = bounded_explanation(RaisingAI(), plan, DataQualityState.READY)
    assert first == second and first.status == "UNAVAILABLE"
    assert "DO NOT CHASE" in first.risk_and_expiry_warnings


def _trigger() -> Candle:
    evidence = RawEvidence("{}", "a" * 64, "test", "test", NOW, 1, "test")
    return Candle(
        "5m",
        1,
        300_001,
        Decimal("100"),
        Decimal("101"),
        Decimal("99"),
        Decimal("100"),
        Decimal("1"),
        evidence,
    )


@pytest.mark.parametrize(
    ("name", "family", "side", "speed", "zone", "chase", "stop"),
    [
        (
            "LONG_SWEEP_FAST",
            SetupFamily.SWEEP_RECLAIM,
            Side.LONG,
            "FAST",
            ("100", "101.5"),
            "102.5",
            "89",
        ),
        (
            "LONG_SWEEP_STANDARD",
            SetupFamily.SWEEP_RECLAIM,
            Side.LONG,
            "STANDARD",
            ("99.5", "101"),
            "102",
            "89",
        ),
        (
            "SHORT_SWEEP_FAST",
            SetupFamily.SWEEP_RECLAIM,
            Side.SHORT,
            "FAST",
            ("98.5", "100"),
            "97.5",
            "111",
        ),
        (
            "SHORT_SWEEP_STANDARD",
            SetupFamily.SWEEP_RECLAIM,
            Side.SHORT,
            "STANDARD",
            ("99", "100.5"),
            "98",
            "111",
        ),
        (
            "LONG_BREAKOUT_FAST",
            SetupFamily.BREAKOUT_RETEST,
            Side.LONG,
            "FAST",
            ("101", "102"),
            "103",
            "97.5",
        ),
        (
            "LONG_BREAKOUT_STANDARD",
            SetupFamily.BREAKOUT_RETEST,
            Side.LONG,
            "STANDARD",
            ("99.5", "101"),
            "102",
            "97.5",
        ),
        (
            "SHORT_BREAKOUT_FAST",
            SetupFamily.BREAKOUT_RETEST,
            Side.SHORT,
            "FAST",
            ("98", "99"),
            "97",
            "102.5",
        ),
        (
            "SHORT_BREAKOUT_STANDARD",
            SetupFamily.BREAKOUT_RETEST,
            Side.SHORT,
            "STANDARD",
            ("99", "100.5"),
            "98",
            "102.5",
        ),
    ],
)
def test_actionable_matrix_8_of_8(
    name: str,
    family: SetupFamily,
    side: Side,
    speed: Literal["FAST", "STANDARD"],
    zone: tuple[str, str],
    chase: str,
    stop: str,
) -> None:
    trigger = _trigger()
    setup = PreparedSetup(
        name,
        family,
        side,
        Decimal("100"),
        Decimal("10"),
        Decimal("90") if side is Side.LONG else Decimal("110"),
        1,
        900_001,
    )
    result = strategy_output(
        setup,
        speed=speed,
        trigger=trigger,
        retest_extreme=Decimal("98") if side is Side.LONG else Decimal("102"),
    )
    assert result.setup_id == name and result.family is family and result.side is side
    assert result.speed == speed and result.trigger_open_time_ms == trigger.open_time_ms
    assert (result.entry_low, result.entry_high) == tuple(map(Decimal, zone))
    assert result.chase_limit == Decimal(chase) and result.stop == Decimal(stop)
    assert result.expires_at == NOW + timedelta(seconds=180 if speed == "FAST" else 900)
    assert result.do_not_chase == "DO NOT CHASE"


def _output(side: Side, speed: Literal["FAST", "STANDARD"]):
    setup = PreparedSetup(
        "lifecycle-setup",
        SetupFamily.SWEEP_RECLAIM,
        side,
        Decimal("100"),
        Decimal("10"),
        Decimal("90") if side is Side.LONG else Decimal("110"),
        1,
        900_001,
    )
    return strategy_output(setup, speed=speed, trigger=_trigger())


def _prepare(side: Side, family: SetupFamily = SetupFamily.SWEEP_RECLAIM) -> PreparedSetup:
    return PreparedSetup(
        "prepare-" + side.value + family.value,
        family,
        side,
        Decimal("100"),
        Decimal("10"),
        Decimal("90") if side is Side.LONG else Decimal("110"),
        1,
        900_001,
    )


def _retest(side: Side, open_time: int) -> Candle:
    evidence = RawEvidence("{}", "b" * 64, "test", "test", NOW, 2, "test")
    if side is Side.LONG:
        return Candle(
            "5m",
            open_time,
            open_time + 300_000,
            Decimal("100"),
            Decimal("102"),
            Decimal("99"),
            Decimal("101"),
            Decimal("1"),
            evidence,
        )
    return Candle(
        "5m",
        open_time,
        open_time + 300_000,
        Decimal("100"),
        Decimal("101"),
        Decimal("101"),
        Decimal("99"),
        Decimal("1"),
        evidence,
    )


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("offset", [1, 2, 3])
def test_prepare_confirmation_offsets_permit_standard(side: Side, offset: int) -> None:
    result = advance_prepare(
        _prepare(side), _retest(side, 1 + offset * 300_000), quality=DataQualityState.READY
    )
    assert result.state.value == "TRIGGERED_STANDARD"


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_prepare_expiry_first_non_permitted_offset(side: Side) -> None:
    setup = _prepare(side)
    before = _retest(side, 900_001)
    after = _retest(side, 1_200_001)
    assert (
        advance_prepare(setup, before, quality=DataQualityState.READY).state.value
        == "TRIGGERED_STANDARD"
    )
    expired = advance_prepare(setup, after, quality=DataQualityState.READY)
    assert expired.state.value == "EXPIRED"
    assert advance_prepare(setup, after, quality=DataQualityState.READY) == expired


@pytest.mark.parametrize("mode", ["ACTIVE", "EXPIRED", "INVALIDATED"])
def test_lifecycle_idempotence(mode: str) -> None:
    output = _output(Side.LONG, "FAST")
    now = NOW if mode == "ACTIVE" else output.expires_at
    reference = Decimal("100") if mode != "INVALIDATED" else Decimal("89")
    first = lifecycle_state(output, now=now, reference=reference, quality=DataQualityState.READY)
    second = lifecycle_state(output, now=now, reference=reference, quality=DataQualityState.READY)
    assert first is second


@pytest.mark.parametrize("terminal", [SignalState.TAKEN, SignalState.SKIPPED, SignalState.REJECTED])
def test_decided_setup_non_reactivation(terminal: SignalState) -> None:
    output = _output(Side.SHORT, "STANDARD")
    assert (
        lifecycle_state(
            output,
            now=output.expires_at,
            reference=Decimal("111"),
            quality=DataQualityState.STALE,
            terminal=terminal,
        )
        is terminal
    )


@pytest.mark.parametrize("side, prohibited", [(Side.LONG, "97"), (Side.SHORT, "103")])
def test_breakout_intervening_close_lifecycle(side: Side, prohibited: str) -> None:
    setup = _prepare(side, SetupFamily.BREAKOUT_RETEST)
    retest = _retest(side, 300_001)
    result = advance_prepare(
        setup, retest, quality=DataQualityState.READY, intervening_closes=(Decimal(prohibited),)
    )
    assert result.state.value == "PREPARE"
    assert (
        advance_prepare(
            setup, retest, quality=DataQualityState.READY, intervening_closes=(Decimal(prohibited),)
        )
        == result
    )


@pytest.mark.parametrize(
    ("side", "entry", "stop", "adverse_entry", "adverse_stop"),
    [
        (Side.LONG, "100", "90", "100.0500", "89.9550"),
        (Side.SHORT, "100", "110", "99.9500", "110.0550"),
    ],
)
def test_risk_math_adverse_execution_and_fees(
    side: Side, entry: str, stop: str, adverse_entry: str, adverse_stop: str
) -> None:
    result = risk_math(
        side=side,
        planned_entry=Decimal(entry),
        stop=Decimal(stop),
        account_equity_usd=Decimal("1000"),
    )
    assert result.risk_budget_usd == Decimal("2.5000") and result.max_notional_usd == Decimal(
        "1000"
    )
    assert result.adverse_entry == Decimal(adverse_entry) and result.adverse_stop == Decimal(
        adverse_stop
    )
    assert result.entry_fee_per_unit == result.adverse_entry * Decimal("0.00045")
    assert result.exit_fee_per_unit == result.adverse_stop * Decimal("0.00045")
    assert all(type(value) is Decimal for value in result.__dict__.values())


@pytest.mark.parametrize(
    "equity,entry,stop",
    [("0", "100", "90"), ("-1", "100", "90"), ("100", "0", "90"), ("100", "100", "100")],
)
def test_risk_math_rejects_invalid_authority(equity: str, entry: str, stop: str) -> None:
    with pytest.raises(PlanError):
        risk_math(
            side=Side.LONG,
            planned_entry=Decimal(entry),
            stop=Decimal(stop),
            account_equity_usd=Decimal(equity),
        )


@pytest.mark.parametrize(
    ("name", "side", "entry", "stop", "limited"),
    [
        ("LONG_RISK_LIMITED", Side.LONG, "100", "90", "risk"),
        ("SHORT_RISK_LIMITED", Side.SHORT, "100", "110", "risk"),
        ("LONG_NOTIONAL_LIMITED", Side.LONG, "100", "99.999", "notional"),
        ("SHORT_NOTIONAL_LIMITED", Side.SHORT, "100", "100.001", "notional"),
    ],
)
def test_risk_math_remaining_limits(
    name: str, side: Side, entry: str, stop: str, limited: str
) -> None:
    result = risk_math(
        side=side,
        planned_entry=Decimal(entry),
        stop=Decimal(stop),
        account_equity_usd=Decimal("1000"),
    )
    assert name and result.quantity_raw == min(
        result.risk_limited_quantity_raw, result.notional_limited_quantity_raw
    )
    if limited == "risk":
        assert result.risk_limited_quantity_raw < result.notional_limited_quantity_raw
    else:
        assert result.notional_limited_quantity_raw < result.risk_limited_quantity_raw


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_risk_math_remaining_non_finite(value: str) -> None:
    with pytest.raises(PlanError):
        risk_math(
            side=Side.LONG,
            planned_entry=Decimal(value),
            stop=Decimal("90"),
            account_equity_usd=Decimal("100"),
        )


@pytest.mark.parametrize(
    ("side", "entry", "stop", "expected"),
    [
        (
            Side.LONG,
            "100",
            "90",
            (
                "100.0500",
                "89.9550",
                "10.0950",
                "0.045022500",
                "0.040479750",
                "10.180502250",
                "0.2455674522344906902800399656",
                "9.995002498750624687656171914",
            ),
        ),
        (
            Side.SHORT,
            "100",
            "110",
            (
                "99.9500",
                "110.0550",
                "10.1050",
                "0.044977500",
                "0.049524750",
                "10.199502250",
                "0.2451100003433991104811021538",
                "10.00500250125062531265632816",
            ),
        ),
        (
            Side.LONG,
            "100",
            "99.999",
            (
                "100.0500",
                "99.9490005",
                "0.1009995",
                "0.045022500",
                "0.044977050225",
                "0.190999050225",
                "13.08907032288882681536905009",
                "9.995002498750624687656171914",
            ),
        ),
        (
            Side.SHORT,
            "100",
            "100.001",
            (
                "99.9500",
                "100.0510005",
                "0.1010005",
                "0.044977500",
                "0.045022950225",
                "0.191000950225",
                "13.08894011812500656893001591",
                "10.00500250125062531265632816",
            ),
        ),
    ],
)
def test_risk_math_remaining_literal_outputs(
    side: Side, entry: str, stop: str, expected: tuple[str, ...]
) -> None:
    result = risk_math(
        side=side,
        planned_entry=Decimal(entry),
        stop=Decimal(stop),
        account_equity_usd=Decimal("1000"),
    )
    actual = (
        result.adverse_entry,
        result.adverse_stop,
        result.price_loss_per_unit,
        result.entry_fee_per_unit,
        result.exit_fee_per_unit,
        result.worst_case_loss_per_unit,
        result.risk_limited_quantity_raw,
        result.notional_limited_quantity_raw,
    )
    assert actual == tuple(Decimal(value) for value in expected)
    assert result.risk_budget_usd == Decimal("2.5000") and result.max_notional_usd == Decimal(
        "1000"
    )


@pytest.mark.parametrize("field", ["account_equity_usd", "planned_entry", "stop"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_risk_math_remaining_non_finite_every_input(field: str, value: str) -> None:
    values = {
        "account_equity_usd": Decimal("100"),
        "planned_entry": Decimal("100"),
        "stop": Decimal("90"),
    }
    values[field] = Decimal(value)
    with pytest.raises(PlanError):
        risk_math(side=Side.LONG, **values)


@pytest.mark.parametrize(
    "sz,raw,expected", [(0, "1.9", "1"), (18, "1.1234567891234567899", "1.123456789123456789")]
)
def test_precision_slice_quantity(sz: int, raw: str, expected: str) -> None:
    assert round_quantity(Decimal(raw), sz) == Decimal(expected)


def test_precision_slice_price_and_zone() -> None:
    assert _round_price(Decimal("12345.67"), 3, "down") == Decimal("12345")
    assert _round_price(Decimal("1.23456"), 3, "up") == Decimal("1.235")
    assert inward_zone(Decimal("1.2341"), Decimal("1.2359"), 3) == (
        Decimal("1.235"),
        Decimal("1.235"),
    )
    with pytest.raises(PlanError):
        inward_zone(Decimal("1.2359"), Decimal("1.2341"), 3)


@pytest.mark.parametrize(
    ("field", "side", "direction", "expected"),
    [
        ("entry", Side.LONG, "up", "1.235"),
        ("chase", Side.LONG, "down", "1.234"),
        ("stop", Side.LONG, "down", "1.234"),
        ("target", Side.LONG, "down", "1.234"),
        ("entry", Side.SHORT, "down", "1.234"),
        ("chase", Side.SHORT, "up", "1.235"),
        ("stop", Side.SHORT, "up", "1.235"),
        ("target", Side.SHORT, "up", "1.235"),
    ],
)
def test_precision_direction_matrix(field: str, side: Side, direction: str, expected: str) -> None:
    del field, side
    assert _round_price(Decimal("1.2345"), 3, direction) == Decimal(expected)


@pytest.mark.parametrize("raw,sz,expected", [("1.2349", 3, "1.234"), ("1.2", 3, "1.200")])
def test_precision_risk_cap(raw: str, sz: int, expected: str) -> None:
    quantity = round_quantity(Decimal(raw), sz)
    assert quantity == Decimal(expected) and quantity <= Decimal(raw)
    assert round_quantity(Decimal(raw), sz) == quantity
    with pytest.raises(PlanError):
        round_quantity(Decimal("0.0009"), 3)


@pytest.mark.parametrize("sz", [-1, 7, 19])
def test_precision_invalid_matrix_metadata(sz: int) -> None:
    with pytest.raises(PlanError):
        _round_price(Decimal("1"), sz, "up")


@pytest.mark.parametrize("value", ["0", "-1", "0.0009", "NaN", "Infinity", "-Infinity"])
def test_precision_invalid_matrix_quantity(value: str) -> None:
    with pytest.raises(PlanError):
        round_quantity(Decimal(value), 3)


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_precision_invalid_matrix_price(value: str) -> None:
    with pytest.raises(PlanError):
        _round_price(Decimal(value), 3, "up")


@pytest.mark.parametrize("speed,seconds", [("FAST", 180), ("STANDARD", 900)])
def test_actionable_expiry_boundaries(speed: Literal["FAST", "STANDARD"], seconds: int) -> None:
    output = _output(Side.LONG, speed)
    assert (
        lifecycle_state(
            output,
            now=NOW + timedelta(seconds=seconds - 1),
            reference=Decimal("100"),
            quality=DataQualityState.READY,
        )
        is output.state
    )
    for offset in (0, 1):
        assert (
            lifecycle_state(
                output,
                now=NOW + timedelta(seconds=seconds + offset),
                reference=Decimal("100"),
                quality=DataQualityState.READY,
            ).value
            == "EXPIRED"
        )


@pytest.mark.parametrize("side,reference", [(Side.LONG, "89"), (Side.SHORT, "111")])
def test_stop_data_and_terminal_lifecycle_are_fail_closed(side: Side, reference: str) -> None:
    output = _output(side, "FAST")
    assert (
        lifecycle_state(
            output, now=NOW, reference=Decimal(reference), quality=DataQualityState.READY
        ).value
        == "INVALIDATED"
    )
    assert (
        lifecycle_state(
            output, now=NOW, reference=Decimal("100"), quality=DataQualityState.STALE
        ).value
        == "INVALIDATED"
    )
    for terminal in (SignalState.TAKEN, SignalState.SKIPPED, SignalState.REJECTED):
        assert (
            lifecycle_state(
                output,
                now=NOW,
                reference=Decimal(reference),
                quality=DataQualityState.STALE,
                terminal=terminal,
            )
            is terminal
        )


@pytest.mark.parametrize(
    ("side", "setup_id", "sweep", "expected", "expected_digest"),
    [
        (
            Side.LONG,
            "a" * 64,
            Decimal("98"),
            {
                "entry_low": Decimal("100"),
                "entry_high": Decimal("101.5"),
                "planned_entry": Decimal("100"),
                "chase_limit": Decimal("102.5"),
                "stop": Decimal("97"),
                "tp1": Decimal("103"),
                "tp2": Decimal("106"),
                "quantity": Decimal(".784"),
                "notional": Decimal("78.4392"),
                "account_equity": Decimal("1000"),
                "risk_budget": Decimal("2.5"),
                "planned_risk": Decimal("2.4987261292"),
                "expires_at": datetime(2026, 7, 14, 0, 3, tzinfo=UTC),
            },
            "76bd3281bdbcff867e59402e34ea77387e406f50a615908322db86f059b26552",
        ),
        (
            Side.SHORT,
            "b" * 64,
            Decimal("102"),
            {
                "entry_low": Decimal("98.5"),
                "entry_high": Decimal("100"),
                "planned_entry": Decimal("100"),
                "chase_limit": Decimal("97.5"),
                "stop": Decimal("103"),
                "tp1": Decimal("97"),
                "tp2": Decimal("94"),
                "quantity": Decimal(".782"),
                "notional": Decimal("78.1609"),
                "account_equity": Decimal("1000"),
                "risk_budget": Decimal("2.5"),
                "planned_risk": Decimal("2.49680922785"),
                "expires_at": datetime(2026, 7, 14, 0, 3, tzinfo=UTC),
            },
            "dacee4b41b47b22332fa7f9041fd7e29879dd27bb1a465612254a0699c8c7942",
        ),
    ],
)
def test_tradeplan_hash_core_fixed_vectors(
    side: Side,
    setup_id: str,
    sweep: Decimal,
    expected: dict[str, object],
    expected_digest: str,
) -> None:
    plan = build_plan(
        setup_id=setup_id,
        side=side,
        speed="FAST",
        boundary=Decimal("100"),
        atr=Decimal("10"),
        sweep=sweep,
        reference=Decimal("100"),
        equity=Decimal("1000"),
        sz_decimals=3,
        created_at=NOW,
    )
    for field, value in expected.items():
        assert getattr(plan, field) == value
    assert plan.plan_id == plan.canonical_hash == expected_digest
    expected_payload = {
        "trade_plan_version": "1",
        "strategy_version": "ETH-LDAR-v0.1",
        "configuration_version": "1",
        "setup_id": setup_id,
        "supersedes_plan_id": None,
        "created_at": "2026-07-14T00:00:00+00:00",
        "expires_at": "2026-07-14T00:03:00+00:00",
        "symbol": "ETH",
        "side": side.value,
        "speed": "FAST",
        "entry_low": expected["entry_low"],
        "entry_high": expected["entry_high"],
        "planned_entry": expected["planned_entry"],
        "chase_limit": expected["chase_limit"],
        "stop": expected["stop"],
        "tp1": expected["tp1"],
        "tp2": expected["tp2"],
        "quantity": expected["quantity"],
        "notional": expected["notional"],
        "account_equity": expected["account_equity"],
        "risk_budget": expected["risk_budget"],
        "planned_risk": expected["planned_risk"],
        "sz_decimals": 3,
        "do_not_chase": "DO NOT CHASE",
    }
    digest = hashlib.sha256(
        b"trader-assist-v0/first-launch/trade-plan/v1\0" + canonical_json_bytes(expected_payload)
    ).hexdigest()
    assert digest == expected_digest
    assert "plan_id" not in expected_payload and "canonical_hash" not in expected_payload


def test_tradeplan_hash_core_is_deterministic_for_decimal_spellings() -> None:
    arguments = dict(
        setup_id="a" * 64,
        side=Side.LONG,
        speed="FAST",
        boundary=Decimal("100"),
        atr=Decimal("10"),
        sweep=Decimal("98"),
        reference=Decimal("100"),
        equity=Decimal("1000"),
        sz_decimals=3,
        created_at=NOW,
    )
    first = build_plan(**arguments)
    repeated = build_plan(**arguments)
    equivalent = build_plan(
        **{
            **arguments,
            "boundary": Decimal("100.0"),
            "atr": Decimal("10.00"),
            "sweep": Decimal("98.000"),
            "reference": Decimal("100.0000"),
            "equity": Decimal("1000.00"),
        }
    )
    assert first.plan_id == repeated.plan_id == equivalent.plan_id


def _self_validating_plan(side: Side = Side.LONG, speed: Literal["FAST", "STANDARD"] = "FAST"):
    return build_plan(
        setup_id="a" * 64 if side is Side.LONG else "b" * 64,
        side=side,
        speed=speed,
        boundary=Decimal("100"),
        atr=Decimal("10"),
        sweep=Decimal("98") if side is Side.LONG else Decimal("102"),
        reference=Decimal("100"),
        equity=Decimal("1000"),
        sz_decimals=3,
        created_at=NOW,
    )


def _independently_rehashed_plan(plan, **updates):
    fields = (
        "trade_plan_version",
        "strategy_version",
        "configuration_version",
        "setup_id",
        "supersedes_plan_id",
        "created_at",
        "expires_at",
        "symbol",
        "side",
        "speed",
        "entry_low",
        "entry_high",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
        "account_equity",
        "risk_budget",
        "planned_risk",
        "sz_decimals",
        "do_not_chase",
    )
    values = {field: updates.get(field, getattr(plan, field)) for field in fields}
    payload = {
        **values,
        "created_at": values["created_at"].isoformat(),
        "expires_at": values["expires_at"].isoformat(),
        "side": values["side"].value,
    }
    digest = hashlib.sha256(
        b"trader-assist-v0/first-launch/trade-plan/v1\0" + canonical_json_bytes(payload)
    ).hexdigest()
    return replace(plan, plan_id=digest, canonical_hash=digest, **updates)


@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_tradeplan_self_validation_fixed_vectors_still_construct(side: Side) -> None:
    plan = _self_validating_plan(side)
    assert plan.plan_id == plan.canonical_hash
    with pytest.raises(AttributeError):
        plan.quantity = Decimal("1")  # type: ignore[misc]
    assert replace(plan) == plan


def test_tradeplan_self_validation_rejects_naive_build_timestamp() -> None:
    with pytest.raises(PlanError, match="CREATED_AT_TIMEZONE_REQUIRED"):
        build_plan(
            setup_id="a" * 64,
            side=Side.LONG,
            speed="FAST",
            boundary=Decimal("100"),
            atr=Decimal("10"),
            sweep=Decimal("98"),
            reference=Decimal("100"),
            equity=Decimal("1000"),
            sz_decimals=3,
            created_at=datetime(2026, 7, 14),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("created_at", datetime(2026, 7, 14)),
        ("created_at", NOW.astimezone(timezone(timedelta(hours=1)))),
        ("expires_at", datetime(2026, 7, 14, 0, 3)),
        ("expires_at", datetime(2026, 7, 14, 1, 3, tzinfo=timezone(timedelta(hours=1)))),
    ],
)
def test_tradeplan_self_validation_rejects_non_utc_timestamps(field: str, value: datetime) -> None:
    with pytest.raises(PlanError):
        replace(_self_validating_plan(), **{field: value})


def test_tradeplan_self_validation_rejects_wrong_fast_and_standard_expiry() -> None:
    fast = _self_validating_plan(speed="FAST")
    standard = _self_validating_plan(speed="STANDARD")
    for plan in (fast, standard):
        with pytest.raises(PlanError, match="TRADE_PLAN_EXPIRY_INVALID"):
            replace(plan, expires_at=plan.expires_at + timedelta(seconds=1))


@pytest.mark.parametrize(
    "field,value",
    [
        ("setup_id", "A" * 64),
        ("plan_id", "not-a-digest"),
        ("canonical_hash", "f" * 63),
        ("supersedes_plan_id", "Z" * 64),
        ("plan_id", "b" * 64),
    ],
)
def test_tradeplan_self_validation_rejects_bad_identity(field: str, value: str) -> None:
    with pytest.raises(PlanError):
        replace(_self_validating_plan(), **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("trade_plan_version", "2"),
        ("strategy_version", "other"),
        ("configuration_version", "2"),
        ("symbol", "BTC"),
        ("do_not_chase", "CHASE"),
        ("side", Side.LONG.value),
        ("speed", "SLOW"),
        ("sz_decimals", 7),
    ],
)
def test_tradeplan_self_validation_rejects_fixed_authority_and_types(
    field: str, value: object
) -> None:
    with pytest.raises(PlanError):
        replace(_self_validating_plan(), **{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "entry_low",
        "entry_high",
        "planned_entry",
        "chase_limit",
        "stop",
        "tp1",
        "tp2",
        "quantity",
        "notional",
        "account_equity",
        "risk_budget",
        "planned_risk",
    ],
)
@pytest.mark.parametrize(
    "value",
    [
        "not-decimal",
        Decimal(0),
        Decimal(-1),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_tradeplan_self_validation_rejects_invalid_financial_fields(
    field: str, value: object
) -> None:
    with pytest.raises(PlanError):
        replace(_self_validating_plan(), **{field: value})


@pytest.mark.parametrize(
    "side,updates",
    [
        (Side.LONG, {"entry_low": Decimal("101")}),
        (Side.LONG, {"stop": Decimal("100")}),
        (Side.SHORT, {"tp2": Decimal("98")}),
        (Side.LONG, {"planned_risk": Decimal("2.6")}),
    ],
)
def test_tradeplan_self_validation_rejects_structure_and_risk_budget(
    side: Side, updates: dict[str, Decimal]
) -> None:
    with pytest.raises(PlanError):
        replace(_self_validating_plan(side), **updates)


@pytest.mark.parametrize(
    "field,value",
    [
        ("quantity", Decimal(".783")),
        ("notional", Decimal("79")),
        ("risk_budget", Decimal("2.6")),
        ("planned_risk", Decimal("2.4")),
    ],
)
def test_tradeplan_self_validation_rejects_coherently_rehashed_risk_mutations(
    field: str, value: Decimal
) -> None:
    with pytest.raises(PlanError, match="TRADE_PLAN_RISK_INCONSISTENT"):
        _independently_rehashed_plan(_self_validating_plan(), **{field: value})


def test_tradeplan_self_validation_rejects_stale_digest_for_canonical_mutation() -> None:
    with pytest.raises(PlanError, match="TRADE_PLAN_HASH_INVALID"):
        replace(_self_validating_plan(), entry_low=Decimal("99"))
