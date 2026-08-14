from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfRelation,
    MarketEvent,
    RetestType,
    ScannerCandidate,
    ScannerChase,
    ScannerLinkage,
    ScannerMarketInput,
    ScannerState,
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
    advance_scanner_candidate,
    evaluate_strategy,
    market_event_id,
    scan_cross_section,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel.scanner import (
    ScannerCandidateClass,
    classify_scanner_state,
)


def market_bar(
    market_id: str,
    index: int,
    *,
    close: Decimal,
    half_range: Decimal = Decimal("2"),
) -> Bar:
    return Bar(
        market_id,
        "5m",
        index * 300_000,
        (index + 1) * 300_000,
        close - Decimal("0.2"),
        close + half_range,
        close - half_range,
        close,
        Decimal("10"),
    )


def history(
    market_id: str,
    *,
    slope: Decimal,
    count: int = 288,
    final_jump: Decimal = Decimal(),
) -> tuple[Bar, ...]:
    base_close = Decimal("100") if market_id == "scanner-market" else Decimal("1000")
    output = [
        market_bar(market_id, index, close=base_close + slope * index)
        for index in range(count)
    ]
    if final_jump:
        value = output[-1]
        close = value.close + final_jump
        output[-1] = market_bar(market_id, count - 1, close=close, half_range=Decimal("0.5"))
    return tuple(output)


def input_for(
    market_id: str,
    *,
    slope: str,
    count: int = 288,
    final_jump: str = "0",
) -> ScannerMarketInput:
    return ScannerMarketInput(
        market_id,
        history(
            market_id,
            slope=Decimal(slope),
            count=count,
            final_jump=Decimal(final_jump),
        ),
        Decimal("0.1"),
        Decimal("0.1"),
        True,
    )


def test_scanner_cross_section_cadence_ranks_and_watch_states() -> None:
    universe = tuple(
        input_for(f"market-{index}", slope=str(Decimal(index - 5) / Decimal(5)))
        for index in range(10)
    )
    observations = scan_cross_section(universe)
    candidates = tuple(item.candidate for item in observations if item.candidate is not None)
    assert candidates
    assert all(item.metrics is not None for item in observations)
    assert any(item.state is ScannerState.WATCH_MOMENTUM for item in candidates)
    assert all(
        item.metrics is None
        or (
            Decimal() <= item.metrics.er_15m <= Decimal(1)
            and Decimal() <= item.metrics.er_30m <= Decimal(1)
            and Decimal() <= item.metrics.er_60m <= Decimal(1)
        )
        for item in observations
    )
    assert all(item.scanner_version == "SESSION-MOMENTUM-R3" for item in candidates)

    new_market = scan_cross_section((input_for("new", slope="0.1", count=64),))[0]
    assert new_market.candidate is not None
    assert new_market.candidate.state is ScannerState.WATCH_NEW_MARKET
    assert new_market.candidate.side is None

    near_universe = (*universe[:-1], input_for("near-winner", slope="0.1", final_jump="1"))
    near = next(
        item.candidate
        for item in scan_cross_section(near_universe)
        if item.market_id == "near-winner"
    )
    assert near is not None and near.state is ScannerState.WATCH_NEAR_LEVEL

    breakout_universe = (*universe[:-1], input_for("winner", slope="0.2", final_jump="3"))
    breakout = next(
        item.candidate
        for item in scan_cross_section(breakout_universe)
        if item.market_id == "winner"
    )
    assert breakout is not None
    assert breakout.state is ScannerState.BREAKOUT_DETECTED
    assert breakout.breakout_buffer is not None
    assert breakout.breakout_level is not None


def breakout_candidate(*, side: Side = Side.LONG) -> ScannerCandidate:
    return ScannerCandidate(
        "c" * 64,
        "scanner-market",
        side,
        ScannerState.BREAKOUT_DETECTED,
        63 * 300_000,
        63 * 300_000,
        Decimal("100"),
        Decimal("0.2"),
        True,
        None,
        ScannerChase.EARLY,
        Decimal("0.2"),
        "BREAKOUT_DETECTED",
        ("NEW->BREAKOUT_DETECTED",),
    )


def test_scanner_lifecycle_classification_is_the_progression_source_of_truth() -> None:
    expected = {
        ScannerCandidateClass.DISCOVERY_ONLY: {
            ScannerState.WATCH_MOMENTUM,
            ScannerState.WATCH_NEAR_LEVEL,
            ScannerState.WATCH_NEW_MARKET,
        },
        ScannerCandidateClass.PROGRESSION_ELIGIBLE: {
            ScannerState.BREAKOUT_DETECTED,
            ScannerState.RETEST_PENDING,
            ScannerState.LATE_WATCH,
            ScannerState.REJECTED_CHASE_FOR_ACTION,
        },
        ScannerCandidateClass.TERMINAL: {
            ScannerState.BREAKOUT_RETEST_READY,
            ScannerState.FAILED_BREAKOUT_SWEEP_WATCH,
            ScannerState.FAILED_INVALIDATED_INSIDE_RANGE,
            ScannerState.EXPIRED_NO_RETEST,
        },
    }
    assert set().union(*expected.values()) == set(ScannerState)
    for classification, states in expected.items():
        assert all(classify_scanner_state(state) is classification for state in states)
    for state in expected[ScannerCandidateClass.TERMINAL]:
        terminal = replace(breakout_candidate(), state=state)
        assert (
            advance_scanner_candidate(
                terminal,
                bars_5m=scanner_path("100.1"),
                current_spread_price=Decimal("0.1"),
                liquidity_healthy=True,
            )
            is terminal
        )


def scanner_path(*closes: str) -> tuple[Bar, ...]:
    base = list(history("scanner-market", slope=Decimal("0.01"), count=64))
    for close in closes:
        index = len(base)
        base.append(
            market_bar(
                "scanner-market",
                index,
                close=Decimal(close),
                half_range=Decimal("0.3"),
            )
        )
    return tuple(base)


def test_scanner_retest_ready_failed_late_rejected_and_expired_states() -> None:
    candidate = breakout_candidate()
    pending = advance_scanner_candidate(
        candidate,
        bars_5m=scanner_path("100.1"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert pending.state is ScannerState.RETEST_PENDING
    ready = advance_scanner_candidate(
        pending,
        bars_5m=scanner_path("100.1", "100.4"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert ready.state is ScannerState.BREAKOUT_RETEST_READY

    failed = advance_scanner_candidate(
        candidate,
        bars_5m=scanner_path("98"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert failed.state is ScannerState.FAILED_BREAKOUT_SWEEP_WATCH

    invalidated = advance_scanner_candidate(
        candidate,
        bars_5m=scanner_path("102", "102", "102", "102", "102", "102", "98"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert invalidated.state is ScannerState.FAILED_INVALIDATED_INSIDE_RANGE

    late = advance_scanner_candidate(
        candidate,
        bars_5m=scanner_path("103.5"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    rejected = advance_scanner_candidate(
        candidate,
        bars_5m=scanner_path("108"),
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert late.state is ScannerState.LATE_WATCH
    assert rejected.state is ScannerState.REJECTED_CHASE_FOR_ACTION

    expired_path = scanner_path(*(f"{102 + index / 100}" for index in range(13)))
    expired = advance_scanner_candidate(
        candidate,
        bars_5m=expired_path,
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    assert expired.state is ScannerState.EXPIRED_NO_RETEST


def _support() -> ZoneSnapshot:
    return ZoneSnapshot(
        "d" * 64,
        "scanner-market",
        ZoneType.LOW,
        Decimal("100"),
        Decimal("99.5"),
        Decimal("100.5"),
        Decimal("0.5"),
        ZoneQuality.ZQ3,
        3,
        20,
        ("a", "b", "c"),
        True,
    )


def test_scanner_expiry_does_not_economically_expire_formal_standard() -> None:
    scanner = replace(breakout_candidate(side=Side.SHORT), state=ScannerState.EXPIRED_NO_RETEST)
    source = _support()
    created = market_bar("scanner-market", 20, close=Decimal("98"))
    event_id = market_event_id(
        market_id="scanner-market",
        zone_id=source.zone_id,
        side=Side.SHORT,
        first_attack_5m_candle_id=created.candle_id,
    )
    previous = market_bar("scanner-market", 75, close=Decimal("98.8"), half_range=Decimal("0.2"))
    formal = MarketEvent(
        event_id,
        "scanner-market",
        SetupFamily.BREAKOUT_RETEST,
        Side.SHORT,
        EventStatus.ACTIVE,
        "STANDARD_WAIT_NO_ECONOMIC_TIMEOUT",
        source,
        created,
        previous,
        Decimal("2"),
        Decimal("10"),
        HtfRelation.NEUTRAL,
        scanner_linkage=ScannerLinkage(scanner.candidate_id, scanner.state),
        breakout_linkage=BreakoutLinkage(event_id, created.candle_id),
        initial_breakout_open=Decimal("100"),
        initial_breakout_high=Decimal("100.2"),
        initial_breakout_low=Decimal("97"),
        initial_breakout_close=Decimal("98"),
        previous_close=previous.close,
        previous_high=previous.high,
        previous_low=previous.low,
        pullback_started=True,
        impulse_extreme=Decimal("97"),
        pullback_extreme=Decimal("99.2"),
        retest_type=RetestType.DEEP,
        retest_seen_bar_time_ms=previous.open_time_ms,
        target_reference=TargetReference(TargetKind.OPEN_SPACE_REFERENCE, None),
    )
    current = market_bar("scanner-market", 76, close=Decimal("98"), half_range=Decimal("0.3"))
    bars = (*history("scanner-market", slope=Decimal("0.01"), count=76), current)
    book = ZoneBook((source,), (), source, None)
    result = evaluate_strategy(
        StrategyEvaluationInput(
            bars,
            Decimal("0.1"),
            bars_15m=tuple(
                Bar(
                    "scanner-market",
                    "15m",
                    index * 900_000,
                    (index + 1) * 900_000,
                    Decimal("100"),
                    Decimal("102"),
                    Decimal("99"),
                    Decimal("101"),
                    Decimal("10"),
                )
                for index in range(20)
            ),
            bars_1h=(),
            zone_book=book,
            scanner_linkage=scanner.linkage,
        ),
        EventLedger((formal,)),
    )
    decision = next(
        item for item in result.decisions if item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED
    )
    assert decision.setup_mode is SetupMode.STANDARD
    assert decision.retest_type is RetestType.DEEP
    assert decision.scanner_linkage is not None
    assert decision.scanner_linkage.state is ScannerState.EXPIRED_NO_RETEST
