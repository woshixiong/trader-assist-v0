from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trader_assist_v0.first_launch.market_data import (
    Candle,
    DataQualityState,
    EthMarketData,
    StrategySnapshot,
    candle_from_websocket,
    context_from_websocket,
    evidence_from_raw,
    metadata_from_info,
)
from trader_assist_v0.first_launch.strategy import (
    AIExplanation,
    PlanError,
    PreparedSetup,
    SetupFamily,
    Side,
    Signal,
    SignalState,
    StrategyOutput,
    _round_price,
    _trade_digest,
    advance_prepare,
    apply_volatility_overlay,
    bounded_explanation,
    build_plan,
    evaluate_signal,
    lifecycle_state,
    risk_math,
    round_quantity,
    size_plan,
    wilder_atr14,
)

NOW = datetime(2026, 7, 14, tzinfo=UTC)


def _candle(
    open_time: int,
    *,
    open: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    volume: str = "10",
    interval: str = "5m",
) -> Candle:
    width = 300_000 if interval == "5m" else 900_000
    latest_index = 26 if interval == "5m" else 10
    if open_time < 10_000_000_000:
        actual_open_time = (
            int(NOW.timestamp() * 1000) - 1_000 - ((latest_index + 1) * width) + open_time
        )
    else:
        actual_open_time = open_time
    open_value, high_value, low_value, close_value = map(Decimal, (open, high, low, close))
    high_value = max(high_value, open_value, close_value)
    low_value = min(low_value, open_value, close_value)
    raw = json.dumps(
        {
            "channel": "candle",
            "data": {
                "s": "ETH",
                "i": interval,
                "t": actual_open_time,
                "T": actual_open_time + width,
                "o": str(open_value),
                "h": str(high_value),
                "l": str(low_value),
                "c": str(close_value),
                "v": volume,
                "n": 0,
            },
        },
        separators=(",", ":"),
    )
    evidence = evidence_from_raw(
        raw,
        operation="WebSocket",
        received_at=max(
            NOW,
            datetime.fromtimestamp((actual_open_time + width + 1_000) / 1_000, tz=UTC),
        ),
        receive_sequence=max(0, actual_open_time // width),
        connection_id="test",
    )
    return candle_from_websocket(raw, evidence)


def _snapshot(candles_5m: tuple[Candle, ...], candles_15m: tuple[Candle, ...]) -> StrategySnapshot:
    data = EthMarketData()
    data.begin_connection()
    for candle in (*candles_5m, *candles_15m):
        assert data.accept_candle(candle) == "ACCEPTED"
    evaluated_at = max(candle.evidence.received_at for candle in (*candles_5m, *candles_15m))
    context_raw = (
        '{"channel":"activeAssetCtx","data":{"coin":"ETH","ctx":'
        '{"markPx":"100","openInterest":"1","funding":"0"}}}'
    )
    data.accept_context(
        context_from_websocket(
            context_raw,
            evidence_from_raw(
                context_raw,
                operation="WebSocket",
                received_at=evaluated_at,
                receive_sequence=90,
                connection_id="test",
            ),
        )
    )
    metadata_raw = '{"universe":[{"name":"ETH","szDecimals":3}]}'
    data.accept_metadata(
        metadata_from_info(
            metadata_raw,
            evidence_from_raw(
                metadata_raw,
                operation="metaAndAssetCtxs",
                received_at=evaluated_at,
                receive_sequence=91,
                connection_id="test",
            ),
        )
    )
    snapshot = data.strategy_snapshot(evaluated_at)
    assert snapshot.quality.state is DataQualityState.READY
    return snapshot


def _history(
    family: SetupFamily, side: Side, fast: bool
) -> tuple[tuple[Candle, ...], tuple[Candle, ...]]:
    c5 = [_candle(i * 300_000) for i in range(-37, 26)]
    volume = "20" if fast else "13"
    if family is SetupFamily.SWEEP_RECLAIM:
        trigger = _candle(
            26 * 300_000,
            high="101" if side is Side.LONG else "102",
            low="98" if side is Side.LONG else "99",
            close="100",
            volume=volume,
        )
        c15 = tuple(
            _candle(
                i * 900_000, close=str(100 + i if side is Side.LONG else 100 - i), interval="15m"
            )
            for i in range(-9, 11)
        )
    elif side is Side.LONG:
        trigger = _candle(26 * 300_000, high="102", low="100", close="102", volume=volume)
        c15 = tuple(_candle(i * 900_000, close=str(90 + i), interval="15m") for i in range(-9, 11))
    else:
        trigger = _candle(26 * 300_000, high="100", low="98", close="98", volume=volume)
        c15 = tuple(_candle(i * 900_000, close=str(110 - i), interval="15m") for i in range(-9, 11))
    return tuple([*c5, trigger]), c15


def _confirmed(family: SetupFamily, side: Side, fast: bool) -> StrategyOutput:
    c5, c15 = _history(family, side, fast)
    value = evaluate_signal(_snapshot(c5, c15))
    if fast:
        assert type(value) is StrategyOutput
        return value
    assert type(value) is PreparedSetup
    boundary = value.provenance.boundary
    retest = _candle(
        27 * 300_000,
        open=str(boundary),
        high=str(boundary + Decimal("1")) if side is Side.LONG else str(boundary),
        low=str(boundary) if side is Side.LONG else str(boundary - Decimal("1")),
        close=str(boundary + Decimal("1")) if side is Side.LONG else str(boundary - Decimal("1")),
        volume="10",
    )
    result = advance_prepare(value, _snapshot((*c5, retest), c15))
    assert type(result) is StrategyOutput
    return result


@pytest.mark.parametrize("family", list(SetupFamily))
@pytest.mark.parametrize("side", list(Side))
@pytest.mark.parametrize("fast", [True, False])
def test_production_authority_matrix(family: SetupFamily, side: Side, fast: bool) -> None:
    output = _confirmed(family, side, fast)
    assert output.setup_id == output.provenance.setup_id
    assert output.family is family and output.side is side
    assert output.speed == ("FAST" if fast else "STANDARD")
    assert output.provenance.setup_trigger_open_time_ms == (
        _history(family, side, fast)[0][-1].open_time_ms
    )
    assert output.decision_trigger_open_time_ms == output.provenance.setup_trigger_open_time_ms + (
        0 if fast else 300_000
    )
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    assert plan.provenance == output.provenance and plan.raw_values() == (
        output.raw_entry_low,
        output.raw_entry_high,
        output.raw_chase_limit,
        output.raw_stop,
    )


def test_c1_f004_normal_overlay_serializes_five_minute_span() -> None:
    candles, _ = _history(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    overlay = apply_volatility_overlay(output, wilder_atr14(candles), candles, output.raw_entry_low)
    assert overlay.regime is not None
    if overlay.regime.value in {"NORMAL", "HIGH"}:
        assert overlay.selected_decision_span == 5


def test_plan_rejects_coherently_rehashed_strategy_substitution() -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_GEOMETRY_INVALID"):
        replace(output, material_extreme=output.material_extreme + Decimal("1"))
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    substituted_setup_id = "b" * 64
    rehashed = copy.copy(plan)
    object.__setattr__(rehashed, "setup_id", substituted_setup_id)
    digest = _trade_digest(rehashed.payload())
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_AUTHORITY_INVALID"):
        replace(plan, setup_id=substituted_setup_id, plan_id=digest, canonical_hash=digest)


def test_only_issued_outputs_are_planable_after_copy_or_mutation() -> None:
    for output in (
        _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True),
        _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, False),
    ):
        direct = StrategyOutput(*output.__dict__.values())
        copied = copy.copy(output)
        reconstructed = object.__new__(StrategyOutput)
        for field, value in output.__dict__.items():
            object.__setattr__(reconstructed, field, value)
        for forged in (direct, replace(output), copied, reconstructed):
            with pytest.raises(PlanError, match="STRATEGY_OUTPUT_AUTHORITY_INVALID"):
                build_plan(
                    strategy_output=forged,
                    reference=output.raw_entry_low,
                    equity=Decimal("1000"),
                    sz_decimals=3,
                )

    issued = _confirmed(SetupFamily.BREAKOUT_RETEST, Side.LONG, True)
    object.__setattr__(issued.provenance, "boundary", issued.provenance.boundary + Decimal("1"))
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_AUTHORITY_INVALID"):
        build_plan(
            strategy_output=issued,
            reference=issued.raw_entry_low,
            equity=Decimal("1000"),
            sz_decimals=3,
        )


def test_only_market_issued_snapshot_can_drive_strategy_or_prepare() -> None:
    candles_5m, candles_15m = _history(SetupFamily.SWEEP_RECLAIM, Side.LONG, False)
    snapshot = _snapshot(candles_5m, candles_15m)
    direct = StrategySnapshot(*snapshot.__dict__.values())
    reconstructed = object.__new__(StrategySnapshot)
    for field, value in snapshot.__dict__.items():
        object.__setattr__(reconstructed, field, value)
    for forged in (direct, replace(snapshot), copy.copy(snapshot), reconstructed):
        with pytest.raises(PlanError, match="STRATEGY_SNAPSHOT_AUTHORITY_INVALID"):
            evaluate_signal(forged)
    with pytest.raises(PlanError, match="STRATEGY_SNAPSHOT_AUTHORITY_INVALID"):
        evaluate_signal(candles_5m)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        evaluate_signal(snapshot, quality=DataQualityState.READY)  # type: ignore[call-arg]

    prepared = evaluate_signal(snapshot)
    assert type(prepared) is PreparedSetup
    with pytest.raises(PlanError, match="PREPARED_SETUP_AUTHORITY_INVALID"):
        advance_prepare(replace(prepared), snapshot)


def test_build_plan_has_no_caller_strategy_authority() -> None:
    output = _confirmed(SetupFamily.BREAKOUT_RETEST, Side.LONG, True)
    with pytest.raises(TypeError):
        build_plan(
            strategy_output=output,
            reference=output.raw_entry_low,
            equity=Decimal("1000"),
            sz_decimals=3,
            boundary=Decimal("1"),
        )  # type: ignore[call-arg]
    assert not hasattr(
        __import__("trader_assist_v0.first_launch.strategy", fromlist=["x"]),
        "evaluate_closed_candles",
    )


def test_ai_accepts_only_materialized_exact_value_without_side_effects() -> None:
    plan = build_plan(
        strategy_output=_confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True),
        reference=Decimal("99"),
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    explanation = AIExplanation(("x",), (), (), (), (), "AVAILABLE")
    assert bounded_explanation(explanation, plan, DataQualityState.READY) is explanation

    class Malicious:
        touched = 0

        def __getattr__(self, _name: str) -> object:
            self.touched += 1
            raise AssertionError

        def explain(self) -> None:
            self.touched += 1

    bad = Malicious()
    result = bounded_explanation(bad, plan, DataQualityState.READY)
    assert result.status == "UNAVAILABLE" and bad.touched == 0 and result is not plan


def test_precision_quantity_and_ten_dollar_gate() -> None:
    assert _round_price(Decimal("123456789"), 6, "up") == Decimal("123456789")
    assert _round_price(Decimal("1.234567"), 3, "up") == Decimal("1.235")
    assert _round_price(Decimal("1.234567"), 3, "down") == Decimal("1.234")
    assert round_quantity(Decimal("1.2399"), 2) == Decimal("1.23")
    for value in (Decimal("0"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(PlanError):
            _round_price(value, 3, "up")
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    with pytest.raises(PlanError, match="MINIMUM"):
        build_plan(
            strategy_output=output,
            reference=output.raw_entry_low,
            equity=Decimal("1"),
            sz_decimals=3,
        )


def test_lifecycle_and_risk_contracts_remain_fail_closed() -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    assert (
        lifecycle_state(
            output,
            now=NOW,
            reference=output.raw_entry_low,
            quality=DataQualityState.READY,
        )
        is output.state
    )
    assert (
        lifecycle_state(
            output,
            now=NOW,
            reference=output.raw_stop,
            quality=DataQualityState.READY,
        )
        is SignalState.INVALIDATED
    )
    assert (
        lifecycle_state(
            output,
            now=NOW,
            reference=output.raw_entry_low,
            quality=DataQualityState.STALE,
            terminal=SignalState.TAKEN,
        )
        is SignalState.TAKEN
    )
    raw = risk_math(
        side=Side.LONG,
        planned_entry=Decimal("100"),
        stop=Decimal("98"),
        account_equity_usd=Decimal("1000"),
    )
    sized = size_plan(
        side=Side.LONG,
        entry=Decimal("100"),
        stop=Decimal("98"),
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    assert raw.adverse_entry > Decimal("100")
    assert sized.notional == sized.quantity * Decimal("100")
    assert sized.planned_risk <= sized.risk_budget


def test_plan_is_immutable_and_fixed_authority_is_enforced() -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    assert plan.__dataclass_params__.frozen is True
    with pytest.raises(PlanError, match="FIXED_AUTHORITY"):
        replace(plan, symbol="BTC")


GEOMETRY_VECTORS: dict[
    tuple[SetupFamily, Side, bool],
    tuple[str, str, str, str],
] = {
    (SetupFamily.SWEEP_RECLAIM, Side.LONG, True): (
        "99",
        "99.31071428571428571428571429",
        "99.51785714285714285714285714",
        "97.79285714285714285714285714",
    ),
    (SetupFamily.SWEEP_RECLAIM, Side.LONG, False): (
        "98.89642857142857142857142857",
        "99.20714285714285714285714286",
        "99.41428571428571428571428571",
        "97.79285714285714285714285714",
    ),
    (SetupFamily.SWEEP_RECLAIM, Side.SHORT, True): (
        "100.6892857142857142857142857",
        "101",
        "100.4821428571428571428571429",
        "102.2071428571428571428571429",
    ),
    (SetupFamily.SWEEP_RECLAIM, Side.SHORT, False): (
        "100.7928571428571428571428571",
        "101.1035714285714285714285714",
        "100.5857142857142857142857143",
        "102.2071428571428571428571429",
    ),
    (SetupFamily.BREAKOUT_RETEST, Side.LONG, True): (
        "101.20",
        "101.40",
        "101.60",
        "100.50",
    ),
    (SetupFamily.BREAKOUT_RETEST, Side.LONG, False): (
        "100.90",
        "101.20",
        "101.40",
        "100.50",
    ),
    (SetupFamily.BREAKOUT_RETEST, Side.SHORT, True): (
        "98.60",
        "98.80",
        "98.40",
        "99.50",
    ),
    (SetupFamily.BREAKOUT_RETEST, Side.SHORT, False): (
        "98.80",
        "99.10",
        "98.60",
        "99.50",
    ),
}


@pytest.mark.parametrize("family", list(SetupFamily))
@pytest.mark.parametrize("side", list(Side))
@pytest.mark.parametrize("fast", [True, False])
def test_production_geometry_literal_vectors(
    family: SetupFamily,
    side: Side,
    fast: bool,
) -> None:
    output = _confirmed(family, side, fast)
    assert (
        output.raw_entry_low,
        output.raw_entry_high,
        output.raw_chase_limit,
        output.raw_stop,
    ) == tuple(Decimal(value) for value in GEOMETRY_VECTORS[(family, side, fast)])


def _prepared(family: SetupFamily, side: Side) -> PreparedSetup:
    candles_5m, candles_15m = _history(family, side, False)
    result = evaluate_signal(_snapshot(candles_5m, candles_15m))
    assert type(result) is PreparedSetup
    return result


def _retest(setup: PreparedSetup, offset: int) -> Candle:
    boundary = setup.provenance.boundary
    side = setup.provenance.side
    return _candle(
        setup.provenance.setup_trigger_open_time_ms + offset * 300_000,
        open=str(boundary),
        high=str(boundary + Decimal("1")) if side is Side.LONG else str(boundary),
        low=str(boundary) if side is Side.LONG else str(boundary - Decimal("1")),
        close=(str(boundary + Decimal("1")) if side is Side.LONG else str(boundary - Decimal("1"))),
    )


def _advance(setup: PreparedSetup, candle: Candle) -> Signal | StrategyOutput:
    candles_5m, candles_15m = _history(setup.provenance.family, setup.provenance.side, False)
    fillers = tuple(
        _candle(setup.provenance.setup_trigger_open_time_ms + offset * 300_000)
        for offset in range(
            1,
            (candle.open_time_ms - setup.provenance.setup_trigger_open_time_ms) // 300_000,
        )
    )
    fresh_15m = (
        (_candle(candles_15m[-1].open_time_ms + 900_000, interval="15m"),)
        if candle.close_time_ms - candles_15m[-1].close_time_ms > 990_000
        else ()
    )
    return advance_prepare(
        setup,
        _snapshot((*candles_5m, *fillers, candle), (*candles_15m, *fresh_15m)),
    )


@pytest.mark.parametrize("side", list(Side))
@pytest.mark.parametrize("offset", [1, 2, 3])
def test_prepare_confirmation_offsets_remain_permitted(
    side: Side,
    offset: int,
) -> None:
    setup = _prepared(SetupFamily.SWEEP_RECLAIM, side)
    result = _advance(setup, _retest(setup, offset))
    assert type(result) is StrategyOutput
    assert result.state is SignalState.TRIGGERED_STANDARD


@pytest.mark.parametrize("side", list(Side))
def test_prepare_first_non_permitted_offset_expires(side: Side) -> None:
    setup = _prepared(SetupFamily.SWEEP_RECLAIM, side)
    result = _advance(setup, _retest(setup, 4))
    assert result.state is SignalState.EXPIRED


@pytest.mark.parametrize("side", list(Side))
def test_intervening_closes_apply_only_to_breakout(side: Side) -> None:
    breakout = _prepared(SetupFamily.BREAKOUT_RETEST, side)
    sweep = _prepared(SetupFamily.SWEEP_RECLAIM, side)
    prohibited = (
        breakout.provenance.boundary - Decimal(".21") * breakout.provenance.atr
        if side is Side.LONG
        else breakout.provenance.boundary + Decimal(".21") * breakout.provenance.atr
    )
    breakout_retest = _retest(breakout, 2)
    breakout_candles, breakout_15m = _history(SetupFamily.BREAKOUT_RETEST, side, False)
    intervening = _candle(
        breakout.provenance.setup_trigger_open_time_ms + 300_000,
        close=str(prohibited),
    )
    breakout_result = advance_prepare(
        breakout,
        _snapshot((*breakout_candles, intervening, breakout_retest), breakout_15m),
    )
    sweep_result = _advance(sweep, _retest(sweep, 1))
    assert breakout_result.state is SignalState.PREPARE
    assert type(sweep_result) is StrategyOutput


@pytest.mark.parametrize("side", list(Side))
@pytest.mark.parametrize("fast", [True, False])
def test_lifecycle_expiry_stop_quality_and_terminal_boundaries(
    side: Side,
    fast: bool,
) -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, side, fast)
    assert (
        lifecycle_state(
            output,
            now=output.expires_at - timedelta(microseconds=1),
            reference=output.raw_entry_low,
            quality=DataQualityState.READY,
        )
        is output.state
    )
    assert (
        lifecycle_state(
            output,
            now=output.expires_at,
            reference=output.raw_entry_low,
            quality=DataQualityState.READY,
        )
        is SignalState.EXPIRED
    )
    stop_reference = output.raw_stop
    assert (
        lifecycle_state(
            output,
            now=output.created_at,
            reference=stop_reference,
            quality=DataQualityState.READY,
        )
        is SignalState.INVALIDATED
    )
    assert (
        lifecycle_state(
            output,
            now=output.created_at,
            reference=output.raw_entry_low,
            quality=DataQualityState.STALE,
        )
        is SignalState.INVALIDATED
    )
    for terminal in (SignalState.TAKEN, SignalState.SKIPPED, SignalState.REJECTED):
        assert (
            lifecycle_state(
                output,
                now=output.expires_at,
                reference=stop_reference,
                quality=DataQualityState.STALE,
                terminal=terminal,
            )
            is terminal
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
    ],
)
def test_risk_math_literal_vectors(
    side: Side,
    entry: str,
    stop: str,
    expected: tuple[str, ...],
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
    assert result.quantity_raw == min(
        result.risk_limited_quantity_raw,
        result.notional_limited_quantity_raw,
    )


@pytest.mark.parametrize("field", ["planned_entry", "stop", "account_equity_usd"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_risk_math_rejects_nonfinite_inputs(field: str, value: str) -> None:
    inputs = {
        "planned_entry": Decimal("100"),
        "stop": Decimal("90"),
        "account_equity_usd": Decimal("1000"),
    }
    inputs[field] = Decimal(value)
    with pytest.raises(PlanError):
        risk_math(side=Side.LONG, **inputs)


@pytest.mark.parametrize(
    ("side", "direction", "expected"),
    [
        (Side.LONG, "up", "1.235"),
        (Side.LONG, "down", "1.234"),
        (Side.SHORT, "down", "1.234"),
        (Side.SHORT, "up", "1.235"),
    ],
)
def test_precision_direction_matrix(
    side: Side,
    direction: str,
    expected: str,
) -> None:
    del side
    assert _round_price(Decimal("1.2345"), 3, direction) == Decimal(expected)


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1E+101"),
        Decimal("1E-101"),
    ],
)
def test_precision_rejects_abnormal_price_exponents(value: Decimal) -> None:
    with pytest.raises(PlanError, match="PRICE_PRECISION_INPUT_INVALID"):
        _round_price(value, 3, "up")


@pytest.mark.parametrize(
    "value",
    [
        Decimal("1E+101"),
        Decimal("1E-101"),
    ],
)
def test_precision_rejects_abnormal_quantity_exponents(value: Decimal) -> None:
    with pytest.raises(PlanError, match="QUANTITY_PRECISION_INPUT_INVALID"):
        round_quantity(value, 3)


def _ten_dollar_output() -> StrategyOutput:
    candles_5m = tuple(
        _candle(
            index * 300_000,
            open="11",
            high="12",
            low="10",
            close="11",
        )
        for index in range(-37, 26)
    )
    trigger = _candle(
        26 * 300_000,
        open="11",
        high="12",
        low="9.5",
        close="11.2",
        volume="20",
    )
    candles_15m = tuple(
        _candle(
            index * 900_000,
            open=str(max(1, 10 + index)),
            high=str(max(2, 11 + index)),
            low=str(max(1, 9 + index)),
            close=str(max(1, 10 + index)),
            interval="15m",
        )
        for index in range(-9, 11)
    )
    output = evaluate_signal(_snapshot((*candles_5m, trigger), candles_15m))
    assert type(output) is StrategyOutput
    assert output.raw_entry_low == Decimal("10")
    return output


def test_exact_ten_dollar_notional_is_accepted_and_below_is_rejected() -> None:
    output = _ten_dollar_output()
    entry = _round_price(output.raw_entry_low, 3, "up")
    stop = _round_price(output.raw_stop, 3, "down")
    unit = risk_math(
        side=output.side,
        planned_entry=entry,
        stop=stop,
        account_equity_usd=Decimal("1"),
    )
    exact_equity = Decimal("1") / unit.quantity_raw
    accepted = build_plan(
        strategy_output=output,
        reference=entry,
        equity=exact_equity,
        sz_decimals=3,
    )
    assert accepted.quantity == Decimal("1.000")
    assert accepted.notional == Decimal("10.000")
    with pytest.raises(PlanError, match="MINIMUM_NOTIONAL_NOT_MET"):
        build_plan(
            strategy_output=output,
            reference=entry,
            equity=exact_equity * Decimal(".9999"),
            sz_decimals=3,
        )


def _coherently_rehashed_plan(plan: object, **updates: object) -> object:
    candidate = copy.copy(plan)
    for field, value in updates.items():
        object.__setattr__(candidate, field, value)
    digest = _trade_digest(candidate.payload())
    return replace(
        plan,
        plan_id=digest,
        canonical_hash=digest,
        **updates,
    )


def test_strategy_output_time_and_trigger_authority_is_fail_closed() -> None:
    fast = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_EXPIRY_INVALID"):
        replace(
            fast,
            decision_trigger_received_at=fast.created_at + timedelta(seconds=1),
        )
    offset = timezone(timedelta(hours=1))
    with pytest.raises(PlanError, match="TRIGGER_RECEIVED_AT_INVALID"):
        replace(
            fast,
            decision_trigger_received_at=fast.decision_trigger_received_at.astimezone(offset),
            created_at=fast.created_at.astimezone(offset),
            expires_at=fast.expires_at.astimezone(offset),
        )
    with pytest.raises(PlanError, match="PROVENANCE_TRIGGER_INVALID"):
        replace(
            fast.provenance,
            setup_trigger_identity=("ETH", "5m", -1),
            setup_trigger_open_time_ms=-1,
        )
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_TRIGGER_INVALID"):
        replace(
            fast,
            decision_trigger_identity=("ETH", "5m", -1),
            decision_trigger_open_time_ms=-1,
        )


def test_trade_plan_rejects_coherently_rehashed_bound_field_mutations() -> None:
    output = _confirmed(SetupFamily.BREAKOUT_RETEST, Side.LONG, False)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    mutations: tuple[tuple[str, object], ...] = (
        (
            "provenance",
            replace(plan.provenance, boundary=plan.provenance.boundary + Decimal("1")),
        ),
        ("decision_trigger_canonical_hash", "f" * 64),
        ("material_extreme", plan.material_extreme + Decimal("1")),
        ("raw_entry_low", plan.raw_entry_low + Decimal(".1")),
        ("entry_low", plan.entry_low + Decimal(".1")),
        ("quantity", plan.quantity + Decimal(".001")),
        ("notional", plan.notional + Decimal(".01")),
        ("planned_risk", plan.planned_risk + Decimal(".01")),
    )
    for field, value in mutations:
        with pytest.raises(PlanError):
            _coherently_rehashed_plan(plan, **{field: value})


def test_trade_plan_rejects_embedded_strategy_authority_substitution() -> None:
    output = _confirmed(SetupFamily.BREAKOUT_RETEST, Side.LONG, False)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    substituted_output = replace(
        output,
        decision_trigger_canonical_hash="f" * 64,
    )
    with pytest.raises(PlanError, match="STRATEGY_OUTPUT_AUTHORITY_INVALID"):
        _coherently_rehashed_plan(
            plan,
            strategy_output=substituted_output,
        )


def test_trade_plan_v2_hash_is_deterministic_and_binds_received_time() -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.SHORT, True)
    first = build_plan(
        strategy_output=output,
        reference=output.raw_entry_high,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    repeated = build_plan(
        strategy_output=output,
        reference=output.raw_entry_high,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    assert first.plan_id == first.canonical_hash == repeated.plan_id
    assert first.trade_plan_version == "2"
    changed_received = first.decision_trigger_received_at + timedelta(seconds=1)
    with pytest.raises(PlanError):
        _coherently_rehashed_plan(
            first,
            decision_trigger_received_at=changed_received,
        )


def test_trade_plan_payload_rejects_invalid_provenance_without_assert() -> None:
    output = _confirmed(SetupFamily.SWEEP_RECLAIM, Side.LONG, True)
    plan = build_plan(
        strategy_output=output,
        reference=output.raw_entry_low,
        equity=Decimal("1000"),
        sz_decimals=3,
    )
    candidate = copy.copy(plan)
    object.__setattr__(candidate, "provenance", object())
    with pytest.raises(PlanError, match="TRADE_PLAN_PROVENANCE_INVALID"):
        candidate.payload()
