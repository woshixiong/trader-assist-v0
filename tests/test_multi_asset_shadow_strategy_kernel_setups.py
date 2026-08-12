from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfRelation,
    MarketEvent,
    SetupFamily,
    SetupMode,
    Side,
    StrategyEvaluationInput,
    TargetKind,
    TargetReference,
    ZoneBook,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
    evaluate_strategy,
    mark_unresolved_at_shutdown,
    market_event_id,
)

MARKET = "2" * 64
FIXTURE = Path(__file__).parent / "fixtures/multi_asset_shadow_strategy_kernel/frozen_cases.json"


def bar(
    index: int,
    *,
    interval: str = "5m",
    open_: str = "100",
    high: str = "102",
    low: str = "99",
    close: str = "101",
    volume: str = "10",
) -> Bar:
    width = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000}[interval]
    return Bar(
        MARKET,
        interval,
        index * width,
        (index + 1) * width,
        Decimal(open_),
        Decimal(high),
        Decimal(low),
        Decimal(close),
        Decimal(volume),
    )


def baseline(current: Bar) -> tuple[Bar, ...]:
    return (*tuple(bar(index) for index in range(current.open_time_ms // 300_000)), current)


def zone(zone_type: ZoneType, *, center: str, low: str, high: str) -> ZoneSnapshot:
    identity = ("a" if zone_type is ZoneType.LOW else "b") * 64
    return ZoneSnapshot(
        identity,
        MARKET,
        zone_type,
        Decimal(center),
        Decimal(low),
        Decimal(high),
        (Decimal(high) - Decimal(low)) / 2,
        ZoneQuality.ZQ3,
        3,
        20,
        ("r1", "r2", "r3"),
        True,
    )


SUPPORT = zone(ZoneType.LOW, center="100", low="99.5", high="100.5")
RESISTANCE = zone(ZoneType.HIGH, center="110", low="109.5", high="110.5")
BOOK = ZoneBook((SUPPORT, RESISTANCE), (), SUPPORT, RESISTANCE)


def event(
    *,
    family: SetupFamily,
    side: Side,
    source_zone: ZoneSnapshot,
    created: Bar,
    **changes: object,
) -> MarketEvent:
    event_id = market_event_id(
        market_id=MARKET,
        zone_id=source_zone.zone_id,
        side=side,
        first_attack_5m_candle_id=created.candle_id,
    )
    value = MarketEvent(
        event_id,
        MARKET,
        family,
        side,
        EventStatus.ACTIVE,
        "CREATED",
        source_zone,
        created,
        created,
        Decimal("2"),
        Decimal("10"),
        HtfRelation.NEUTRAL,
        previous_close=created.close,
        previous_high=created.high,
        previous_low=created.low,
    )
    return value.evolve(**changes)


def evaluate(
    current: Bar, ledger: EventLedger | None = None, *, book: ZoneBook = BOOK
):
    return evaluate_strategy(
        StrategyEvaluationInput(
            bars_5m=baseline(current),
            minimum_tick=Decimal("0.1"),
            bars_15m=tuple(bar(index, interval="15m") for index in range(20)),
            bars_1h=(),
            zone_book=book,
        ),
        EventLedger() if ledger is None else ledger,
    )


@pytest.mark.parametrize(
    ("side", "source_zone", "created", "confirmation", "expected_stop"),
    (
        (
            Side.LONG,
            SUPPORT,
            bar(20, open_="100", high="101", low="99", close="100"),
            bar(21, open_="100", high="102", low="99.2", close="101.2"),
            Decimal("98.8"),
        ),
        (
            Side.SHORT,
            RESISTANCE,
            bar(20, open_="110", high="111", low="109", close="110"),
            bar(21, open_="110", high="110.8", low="108", close="108.8"),
            Decimal("111.2"),
        ),
    ),
)
def test_sweep_long_and_short_exact_confirmation_and_terms(
    side: Side,
    source_zone: ZoneSnapshot,
    created: Bar,
    confirmation: Bar,
    expected_stop: Decimal,
) -> None:
    active = event(
        family=SetupFamily.SWEEP_RECLAIM,
        side=side,
        source_zone=source_zone,
        created=created,
        reclaim_candle_high=created.high,
        reclaim_candle_low=created.low,
        sweep_extreme=created.low if side is Side.LONG else created.high,
        structural_stop=expected_stop,
        ideal_entry_low=Decimal("99.6") if side is Side.LONG else Decimal("109.5"),
        ideal_entry_high=Decimal("100") if side is Side.LONG else Decimal("110.4"),
        chase_limit=Decimal("100.2") if side is Side.LONG else Decimal("109.8"),
        target_reference=TargetReference(
            TargetKind.SOURCE_ZONE_CENTER, source_zone.center, source_zone.zone_id
        ),
    )
    result = evaluate(confirmation, EventLedger((active,)))
    formal = next(
        item for item in result.decisions if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert formal.setup_family is SetupFamily.SWEEP_RECLAIM
    assert formal.setup_mode is SetupMode.SWEEP_RECLAIM
    assert formal.a5_event == Decimal("2")
    assert formal.m20_event == Decimal("10")
    assert formal.structural_stop == expected_stop
    assert formal.zone_snapshot is source_zone
    with pytest.raises(AttributeError):
        formal.reason = "MUTATION_PROHIBITED"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("side", "source_zone", "created", "invalidating"),
    (
        (
            Side.LONG,
            SUPPORT,
            bar(20, open_="100", high="101", low="99", close="100"),
            bar(21, open_="100", high="100.2", low="98", close="99.3"),
        ),
        (
            Side.SHORT,
            RESISTANCE,
            bar(20, open_="110", high="111", low="109", close="110"),
            bar(21, open_="110", high="112", low="109.8", close="110.7"),
        ),
    ),
)
def test_sweep_accepted_outside_invalidation(
    side: Side,
    source_zone: ZoneSnapshot,
    created: Bar,
    invalidating: Bar,
) -> None:
    active = event(
        family=SetupFamily.SWEEP_RECLAIM,
        side=side,
        source_zone=source_zone,
        created=created,
        reclaim_candle_high=created.high,
        reclaim_candle_low=created.low,
        sweep_extreme=created.low if side is Side.LONG else created.high,
    )
    result = evaluate(invalidating, EventLedger((active,)))
    assert result.ledger.events[0].status is EventStatus.INVALIDATED
    assert result.ledger.events[0].transition == "INVALIDATED_ACCEPTED_OUTSIDE"


@pytest.mark.parametrize(
    ("side", "source_zone", "created", "confirmation", "expected_stop"),
    (
        (
            Side.LONG,
            RESISTANCE,
            bar(20, open_="110", high="112", low="109.8", close="111.8", volume="15"),
            bar(21, open_="111.8", high="113", low="111", close="112.8"),
            Decimal("109.8"),
        ),
        (
            Side.SHORT,
            SUPPORT,
            bar(20, open_="100", high="100.2", low="98", close="98.2", volume="15"),
            bar(21, open_="98.2", high="99", low="97", close="97.2"),
            Decimal("100.2"),
        ),
    ),
)
def test_breakout_micro_long_and_short_mode_priority(
    side: Side,
    source_zone: ZoneSnapshot,
    created: Bar,
    confirmation: Bar,
    expected_stop: Decimal,
) -> None:
    active = event(
        family=SetupFamily.BREAKOUT_RETEST,
        side=side,
        source_zone=source_zone,
        created=created,
        breakout_linkage=BreakoutLinkage("u" * 64, created.candle_id),
        initial_breakout_open=created.open,
        initial_breakout_high=created.high,
        initial_breakout_low=created.low,
        initial_breakout_close=created.close,
        impulse_extreme=created.high if side is Side.LONG else created.low,
        target_reference=TargetReference(TargetKind.OPEN_SPACE_REFERENCE, None),
    )
    result = evaluate(confirmation, EventLedger((active,)))
    formal = next(
        item for item in result.decisions if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert formal.setup_mode is SetupMode.MICRO_FAST
    assert formal.structural_stop == expected_stop
    assert len([item for item in result.ledger.events if item.status is EventStatus.CONFIRMED]) == 1


@pytest.mark.parametrize(
    ("side", "mode", "source_zone", "pullback", "previous", "confirmation"),
    (
        (
            Side.LONG,
            SetupMode.STANDARD_DEEP,
            RESISTANCE,
            "110.8",
            bar(30, open_="111.2", high="111.4", low="110.8", close="111"),
            bar(31, open_="111", high="112.5", low="110.9", close="112"),
        ),
        (
            Side.LONG,
            SetupMode.STANDARD_SHALLOW,
            RESISTANCE,
            "111.5",
            bar(30, open_="111.9", high="112", low="111.5", close="111.7"),
            bar(31, open_="111.7", high="113", low="111.6", close="112.2"),
        ),
        (
            Side.SHORT,
            SetupMode.STANDARD_DEEP,
            SUPPORT,
            "99.2",
            bar(30, open_="99", high="99.2", low="98.5", close="98.8"),
            bar(31, open_="98.8", high="99", low="97", close="98"),
        ),
        (
            Side.SHORT,
            SetupMode.STANDARD_SHALLOW,
            SUPPORT,
            "98.5",
            bar(30, open_="98.4", high="98.5", low="98", close="98.3"),
            bar(31, open_="98.3", high="98.4", low="97", close="97.8"),
        ),
    ),
)
def test_breakout_standard_deep_shallow_long_short(
    side: Side,
    mode: SetupMode,
    source_zone: ZoneSnapshot,
    pullback: str,
    previous: Bar,
    confirmation: Bar,
) -> None:
    created = bar(
        20,
        open_="110" if side is Side.LONG else "100",
        high="113" if side is Side.LONG else "100.2",
        low="109.8" if side is Side.LONG else "97",
        close="112" if side is Side.LONG else "98",
        volume="15",
    )
    active = event(
        family=SetupFamily.BREAKOUT_RETEST,
        side=side,
        source_zone=source_zone,
        created=created,
        latest_bar=previous,
        breakout_linkage=BreakoutLinkage("v" * 64, created.candle_id),
        initial_breakout_open=created.open,
        initial_breakout_high=created.high,
        initial_breakout_low=created.low,
        initial_breakout_close=created.close,
        previous_close=previous.close,
        previous_high=previous.high,
        previous_low=previous.low,
        pullback_started=True,
        impulse_extreme=Decimal("113") if side is Side.LONG else Decimal("97"),
        pullback_extreme=Decimal(pullback),
        retest_mode=mode,
        retest_seen_bar_time_ms=previous.open_time_ms,
        target_reference=TargetReference(TargetKind.OPEN_SPACE_REFERENCE, None),
    )
    result = evaluate(confirmation, EventLedger((active,)))
    formal = next(
        item for item in result.decisions if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert formal.setup_mode is mode
    assert formal.breakout_linkage is not None


def test_accepted_reentry_invalidates_breakout_and_routes_new_opposite_sweep() -> None:
    created = bar(20, open_="110", high="112", low="109.8", close="111.8", volume="15")
    breakout = event(
        family=SetupFamily.BREAKOUT_RETEST,
        side=Side.LONG,
        source_zone=RESISTANCE,
        created=created,
        breakout_linkage=BreakoutLinkage("w" * 64, created.candle_id),
        initial_breakout_open=created.open,
        initial_breakout_high=created.high,
        initial_breakout_low=created.low,
        initial_breakout_close=created.close,
        impulse_extreme=created.high,
    )
    reentry = bar(21, open_="111", high="111.2", low="109.8", close="110.2")
    result = evaluate(reentry, EventLedger((breakout,)))
    assert result.ledger.events[0].transition == "INVALIDATED_ACCEPTED_REENTRY"
    routed = result.ledger.events[-1]
    assert routed.setup_family is SetupFamily.SWEEP_RECLAIM
    assert routed.side is Side.SHORT
    assert routed.breakout_linkage is not None
    assert routed.breakout_linkage.accepted_reentry_source_event_id == breakout.market_event_id


def _range_bars() -> tuple[Bar, ...]:
    return tuple(
        bar(index, interval="15m", open_="105", high="106", low="104", close="105")
        for index in range(20)
    )


@pytest.mark.parametrize(
    ("side", "current", "reason"),
    (
        (
            Side.LONG,
            bar(20, open_="101", high="102", low="99.8", close="101.5"),
            "RANGE_LONG_CONFIRMED",
        ),
        (
            Side.SHORT,
            bar(20, open_="109", high="110.2", low="108", close="108.5"),
            "RANGE_SHORT_CONFIRMED",
        ),
    ),
)
def test_range_long_and_short_exact_wick_true_range_formulas(
    side: Side, current: Bar, reason: str
) -> None:
    bars_5m = baseline(current)
    if side is Side.SHORT:
        previous = bar(19, open_="109", high="110", low="108", close="109")
        bars_5m = (*bars_5m[:-2], previous, current)
    result = evaluate_strategy(
        StrategyEvaluationInput(
            bars_5m,
            Decimal("0.1"),
            bars_15m=_range_bars(),
            bars_1h=(),
            zone_book=BOOK,
        )
    )
    formal = next(item for item in result.decisions if item.reason == reason)
    assert formal.side is side
    assert formal.setup_mode is SetupMode.RANGE_EDGE_REJECTION
    assert formal.target_reference is not None
    assert formal.target_reference.price == Decimal("105")
    rerun = evaluate_strategy(
        StrategyEvaluationInput(
            bars_5m,
            Decimal("0.1"),
            bars_15m=_range_bars(),
            bars_1h=(),
            zone_book=BOOK,
        ),
        result.ledger,
    )
    same_family = [
        item
        for item in rerun.ledger.events
        if item.setup_family is SetupFamily.RANGE_EDGE_REJECTION and item.side is side
    ]
    assert len(same_family) == 1


def test_same_event_dedup_new_deeper_sweep_supersession_and_no_timeout() -> None:
    first = bar(20, open_="100", high="101", low="99", close="100")
    created = evaluate(first)
    count = len(created.ledger.events)
    duplicate = evaluate_strategy(
        StrategyEvaluationInput(
            baseline(first),
            Decimal("0.1"),
            bars_15m=_range_bars(),
            bars_1h=(),
            zone_book=BOOK,
        ),
        created.ledger,
    )
    assert len(duplicate.ledger.events) == count

    old = next(
        item
        for item in created.ledger.events
        if item.setup_family is SetupFamily.SWEEP_RECLAIM
    )
    deeper = bar(21, open_="100", high="101", low="98.8", close="100")
    superseded = evaluate(deeper, EventLedger((old,)))
    assert superseded.ledger.events[0].status is EventStatus.SUPERSEDED
    assert superseded.ledger.events[-1].status is EventStatus.ACTIVE
    assert superseded.ledger.events[-1].market_event_id != old.market_event_id

    many_bars_later = replace(
        superseded.ledger.events[-1], latest_bar=bar(100), transition="STILL_ACTIVE"
    )
    assert not many_bars_later.status.terminal
    shutdown = mark_unresolved_at_shutdown(EventLedger((many_bars_later,)))
    assert shutdown.events[0].status is EventStatus.UNRESOLVED_AT_SHUTDOWN


def test_different_setup_same_direction_and_opposite_formal_invalidation() -> None:
    created = bar(20, open_="100", high="101", low="99", close="100")
    sweep_long = event(
        family=SetupFamily.SWEEP_RECLAIM,
        side=Side.LONG,
        source_zone=SUPPORT,
        created=created,
        reclaim_candle_high=Decimal("105"),
        reclaim_candle_low=created.low,
        sweep_extreme=created.low,
    )
    breakout_long = event(
        family=SetupFamily.BREAKOUT_RETEST,
        side=Side.LONG,
        source_zone=RESISTANCE,
        created=created,
        breakout_linkage=BreakoutLinkage("x" * 64, created.candle_id),
        initial_breakout_open=Decimal("110"),
        initial_breakout_high=Decimal("112"),
        initial_breakout_low=Decimal("109.8"),
        initial_breakout_close=Decimal("111.8"),
        impulse_extreme=Decimal("112"),
    )
    current = bar(21, open_="111.8", high="113", low="111", close="112.8")
    same_direction = evaluate(current, EventLedger((sweep_long, breakout_long)))
    assert same_direction.ledger.events[0].status is not EventStatus.SUPERSEDED
    assert same_direction.ledger.events[1].status is EventStatus.CONFIRMED

    opposite_active = event(
        family=SetupFamily.RANGE_EDGE_REJECTION,
        side=Side.SHORT,
        source_zone=RESISTANCE,
        created=created,
    )
    range_long_bar = bar(21, open_="101", high="102", low="99.8", close="101.5")
    opposite = evaluate_strategy(
        StrategyEvaluationInput(
            baseline(range_long_bar),
            Decimal("0.1"),
            bars_15m=_range_bars(),
            bars_1h=(),
            zone_book=BOOK,
        ),
        EventLedger((opposite_active,)),
    )
    assert opposite.ledger.events[0].transition == "INVALIDATED_BY_OPPOSITE_FORMAL_EVENT"


def test_frozen_fixture_and_formal_setup_count_exactly_three() -> None:
    payload = json.loads(FIXTURE.read_text())
    assert payload["formal_setups"] == [item.value for item in SetupFamily]
    assert len(SetupFamily) == 3
    assert set(SetupFamily) == {
        SetupFamily.SWEEP_RECLAIM,
        SetupFamily.BREAKOUT_RETEST,
        SetupFamily.RANGE_EDGE_REJECTION,
    }
    assert all("FAILED_ACCEPTED_BREAKOUT" not in item.value for item in SetupFamily)
