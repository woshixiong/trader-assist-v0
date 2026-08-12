"""Pure formal-Setup and Market Event state machine.

The engine has no clocks, network clients, persistence, account state, sizing,
orders, or notifications.  Every call consumes immutable closed-bar evidence and
returns a new immutable ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256

from .indicators import (
    aggregate_closed_5m_causally,
    clv_long,
    clv_short,
    directional_efficiency_8,
    htf_context,
    htf_relation,
    median_previous_20_volume,
    true_range,
    validate_series,
    wilder_atr14,
)
from .types import (
    PARAMETER_VERSION,
    STRATEGY_VERSION,
    Bar,
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfRelation,
    KernelInputError,
    KernelResult,
    MarketEvent,
    RetestType,
    ScannerLinkage,
    SetupFamily,
    SetupMode,
    Side,
    StrategyDecision,
    TargetKind,
    TargetReference,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
)
from .zones import ZoneBook, build_zone_book


@dataclass(frozen=True)
class StrategyEvaluationInput:
    bars_5m: tuple[Bar, ...]
    minimum_tick: Decimal
    bars_15m: tuple[Bar, ...] | None = None
    bars_1h: tuple[Bar, ...] | None = None
    zone_book: ZoneBook | None = None
    scanner_linkage: ScannerLinkage | None = None
    mandatory_data_valid: bool = True


def market_event_id(
    *, market_id: str, zone_id: str, side: Side, first_attack_5m_candle_id: str
) -> str:
    return sha256(
        (
            market_id
            + zone_id
            + side.value
            + first_attack_5m_candle_id
            + STRATEGY_VERSION
            + PARAMETER_VERSION
        ).encode("utf-8")
    ).hexdigest()


def _decision(
    event: MarketEvent,
    *,
    kind: DecisionKind,
    reason: str,
    transition: str,
) -> StrategyDecision:
    return StrategyDecision(
        market_id=event.market_id,
        setup_family=event.setup_family,
        setup_mode=event.formal_mode,
        retest_type=(
            event.retest_type if event.formal_mode is SetupMode.STANDARD else None
        ),
        side=event.side,
        decision=kind,
        reason=reason,
        market_event_id=event.market_event_id,
        zone_id=event.zone.zone_id,
        zone_snapshot=event.zone,
        a5_event=event.a5_event,
        m20_event=event.m20_event,
        htf_relation=event.htf_relation,
        breakout_linkage=event.breakout_linkage,
        ideal_entry_low=event.ideal_entry_low,
        ideal_entry_high=event.ideal_entry_high,
        chase_limit=event.chase_limit,
        structural_stop=event.structural_stop,
        target_reference=event.target_reference,
        transition=transition,
        scanner_linkage=event.scanner_linkage,
    )


def _eligible(zone: ZoneSnapshot, zone_type: ZoneType) -> bool:
    return (
        zone.zone_type is zone_type
        and zone.quality.rank >= ZoneQuality.ZQ2.rank
        and zone.active_for_new_event
        and not zone.suppressed
    )


def _sweep_candidate(bar: Bar, zone: ZoneSnapshot, side: Side, a5: Decimal) -> bool:
    if side is Side.LONG:
        excursion = zone.low - bar.low
        return (
            Decimal("0.10") * a5 <= excursion <= Decimal("0.75") * a5
            and bar.close >= zone.low + Decimal("0.05") * a5
        )
    excursion = bar.high - zone.high
    return (
        Decimal("0.10") * a5 <= excursion <= Decimal("0.75") * a5
        and bar.close <= zone.high - Decimal("0.05") * a5
    )


def _sweep_terms(
    bar: Bar, zone: ZoneSnapshot, side: Side, a5: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal, TargetReference]:
    if side is Side.LONG:
        ideal_low = zone.low + Decimal("0.05") * a5
        ideal_high = min(zone.center, zone.low + Decimal("0.25") * a5)
        chase = zone.low + Decimal("0.35") * a5
        stop = bar.low - Decimal("0.10") * a5
    else:
        ideal_low = max(zone.center, zone.high - Decimal("0.25") * a5)
        ideal_high = zone.high - Decimal("0.05") * a5
        chase = zone.high - Decimal("0.35") * a5
        stop = bar.high + Decimal("0.10") * a5
    return (
        ideal_low,
        ideal_high,
        chase,
        stop,
        TargetReference(TargetKind.SOURCE_ZONE_CENTER, zone.center, zone.zone_id),
    )


def _new_sweep(
    *,
    bar: Bar,
    zone: ZoneSnapshot,
    side: Side,
    a5: Decimal,
    m20: Decimal,
    relation: HtfRelation,
    scanner_linkage: ScannerLinkage | None,
    breakout_linkage: BreakoutLinkage | None = None,
) -> MarketEvent:
    ideal_low, ideal_high, chase, stop, target = _sweep_terms(bar, zone, side, a5)
    return MarketEvent(
        market_event_id=market_event_id(
            market_id=bar.market_id,
            zone_id=zone.zone_id,
            side=side,
            first_attack_5m_candle_id=bar.candle_id,
        ),
        market_id=bar.market_id,
        setup_family=SetupFamily.SWEEP_RECLAIM,
        side=side,
        status=EventStatus.ACTIVE,
        transition="SWEEP_CANDIDATE_CREATED",
        zone=zone,
        created_bar=bar,
        latest_bar=bar,
        a5_event=a5,
        m20_event=m20,
        htf_relation=relation,
        scanner_linkage=scanner_linkage,
        breakout_linkage=breakout_linkage,
        reclaim_candle_high=bar.high,
        reclaim_candle_low=bar.low,
        sweep_extreme=bar.low if side is Side.LONG else bar.high,
        previous_close=bar.close,
        previous_high=bar.high,
        previous_low=bar.low,
        ideal_entry_low=ideal_low,
        ideal_entry_high=ideal_high,
        chase_limit=chase,
        structural_stop=stop,
        target_reference=target,
    )


def _progress_sweep(event: MarketEvent, bar: Bar) -> tuple[MarketEvent, StrategyDecision | None]:
    if (
        event.sweep_extreme is None
        or event.reclaim_candle_high is None
        or event.reclaim_candle_low is None
    ):
        raise KernelInputError("sweep event is incomplete")
    a5 = event.a5_event
    is_new_extreme = (
        bar.low < event.sweep_extreme
        if event.side is Side.LONG
        else bar.high > event.sweep_extreme
    )
    if is_new_extreme and _sweep_candidate(bar, event.zone, event.side, a5):
        updated = event.evolve(
            status=EventStatus.SUPERSEDED,
            transition="SUPERSEDED_BY_NEW_INDEPENDENT_EVENT",
            latest_bar=bar,
        )
        return updated, _decision(
            updated,
            kind=DecisionKind.SUPERSEDED,
            reason="SUPERSEDED_BY_NEW_INDEPENDENT_EVENT",
            transition=updated.transition,
        )
    invalidated = (
        bar.close <= event.zone.low - Decimal("0.05") * a5
        if event.side is Side.LONG
        else bar.close >= event.zone.high + Decimal("0.05") * a5
    )
    if invalidated:
        updated = event.evolve(
            status=EventStatus.INVALIDATED,
            transition="INVALIDATED_ACCEPTED_OUTSIDE",
            latest_bar=bar,
        )
        return updated, _decision(
            updated,
            kind=DecisionKind.INVALIDATED,
            reason="INVALIDATED_ACCEPTED_OUTSIDE",
            transition=updated.transition,
        )
    confirmed = (
        bar.close > event.reclaim_candle_high
        and bar.low > event.sweep_extreme
        and bar.close >= event.zone.low + Decimal("0.05") * a5
        if event.side is Side.LONG
        else bar.close < event.reclaim_candle_low
        and bar.high < event.sweep_extreme
        and bar.close <= event.zone.high - Decimal("0.05") * a5
    )
    if confirmed:
        updated = event.evolve(
            status=EventStatus.CONFIRMED,
            transition="FORMAL_SETUP_CONFIRMED",
            latest_bar=bar,
        )
        return updated, _decision(
            updated,
            kind=DecisionKind.FORMAL_SETUP_CONFIRMED,
            reason="SWEEP_RECLAIM_CONFIRMED",
            transition=updated.transition,
        )
    return event.evolve(latest_bar=bar, transition="SWEEP_WAIT_CONFIRMATION"), None


def _initial_breakout(bar: Bar, zone: ZoneSnapshot, side: Side, a5: Decimal, m20: Decimal) -> bool:
    body = abs(bar.close - bar.open)
    if side is Side.LONG:
        return (
            bar.close >= zone.high + Decimal("0.15") * a5
            and body >= Decimal("0.50") * a5
            and clv_long(bar) >= Decimal("0.70")
            and bar.volume >= Decimal("1.20") * m20
        )
    return (
        bar.close <= zone.low - Decimal("0.15") * a5
        and body >= Decimal("0.50") * a5
        and clv_short(bar) >= Decimal("0.70")
        and bar.volume >= Decimal("1.20") * m20
    )


def _breakout_target(
    *, source: ZoneSnapshot, side: Side, zones: tuple[ZoneSnapshot, ...]
) -> TargetReference:
    if side is Side.LONG:
        directional = tuple(
            sorted(
                (
                    item
                    for item in zones
                    if _eligible(item, ZoneType.HIGH) and item.low > source.high
                ),
                key=lambda item: (item.low, item.zone_id),
            )
        )
    else:
        directional = tuple(
            sorted(
                (
                    item
                    for item in zones
                    if _eligible(item, ZoneType.LOW) and item.high < source.low
                ),
                key=lambda item: (-item.high, item.zone_id),
            )
        )
    if directional:
        return TargetReference(
            TargetKind.DIRECTIONAL_ZONE_SET_FROZEN,
            None,
            frozen_directional_zones=directional,
        )
    return TargetReference(TargetKind.OPEN_SPACE_REFERENCE, None)


def _new_breakout(
    *,
    bar: Bar,
    zone: ZoneSnapshot,
    side: Side,
    a5: Decimal,
    m20: Decimal,
    relation: HtfRelation,
    scanner_linkage: ScannerLinkage | None,
    zones: tuple[ZoneSnapshot, ...],
) -> MarketEvent:
    event_id = market_event_id(
        market_id=bar.market_id,
        zone_id=zone.zone_id,
        side=side,
        first_attack_5m_candle_id=bar.candle_id,
    )
    linkage = BreakoutLinkage(event_id, bar.candle_id)
    return MarketEvent(
        market_event_id=event_id,
        market_id=bar.market_id,
        setup_family=SetupFamily.BREAKOUT_RETEST,
        side=side,
        status=EventStatus.ACTIVE,
        transition="INITIAL_BREAKOUT_EVENT_CREATED",
        zone=zone,
        created_bar=bar,
        latest_bar=bar,
        a5_event=a5,
        m20_event=m20,
        htf_relation=relation,
        scanner_linkage=scanner_linkage,
        breakout_linkage=linkage,
        initial_breakout_open=bar.open,
        initial_breakout_high=bar.high,
        initial_breakout_low=bar.low,
        initial_breakout_close=bar.close,
        previous_close=bar.close,
        previous_high=bar.high,
        previous_low=bar.low,
        impulse_extreme=bar.high if side is Side.LONG else bar.low,
        target_reference=_breakout_target(source=zone, side=side, zones=zones),
    )


def _accepted_reentry(event: MarketEvent, bar: Bar) -> bool:
    return (
        bar.close <= event.zone.high - Decimal("0.05") * event.a5_event
        if event.side is Side.LONG
        else bar.close >= event.zone.low + Decimal("0.05") * event.a5_event
    )


def _micro_confirmation(event: MarketEvent, bar: Bar) -> bool:
    if (
        event.initial_breakout_close is None
        or event.initial_breakout_high is None
        or event.initial_breakout_low is None
    ):
        raise KernelInputError("breakout event is incomplete")
    a5 = event.a5_event
    if event.side is Side.LONG:
        return (
            bar.close >= event.zone.high + Decimal("0.10") * a5
            and bar.low >= event.zone.high - Decimal("0.10") * a5
            and (
                bar.close > event.initial_breakout_close
                or (bar.low > event.initial_breakout_low and bar.close > bar.open)
            )
        )
    return (
        bar.close <= event.zone.low - Decimal("0.10") * a5
        and bar.high <= event.zone.low + Decimal("0.10") * a5
        and (
            bar.close < event.initial_breakout_close
            or (bar.high < event.initial_breakout_high and bar.close < bar.open)
        )
    )


def _micro_terms(event: MarketEvent) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if event.initial_breakout_high is None or event.initial_breakout_low is None:
        raise KernelInputError("breakout event is incomplete")
    a5 = event.a5_event
    if event.side is Side.LONG:
        return (
            event.zone.high + Decimal("0.10") * a5,
            event.zone.high + Decimal("0.40") * a5,
            event.zone.high + Decimal("0.75") * a5,
            min(event.initial_breakout_low, event.zone.high - Decimal("0.25") * a5),
        )
    return (
        event.zone.low - Decimal("0.40") * a5,
        event.zone.low - Decimal("0.10") * a5,
        event.zone.low - Decimal("0.75") * a5,
        max(event.initial_breakout_high, event.zone.low + Decimal("0.25") * a5),
    )


def _standard_terms(
    event: MarketEvent, pullback_extreme: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    a5 = event.a5_event
    if event.side is Side.LONG:
        return (
            event.zone.high - Decimal("0.05") * a5,
            event.zone.high + Decimal("0.20") * a5,
            event.zone.high + Decimal("0.35") * a5,
            min(pullback_extreme, event.zone.high - Decimal("0.10") * a5),
        )
    return (
        event.zone.low - Decimal("0.20") * a5,
        event.zone.low + Decimal("0.05") * a5,
        event.zone.low - Decimal("0.35") * a5,
        max(pullback_extreme, event.zone.low + Decimal("0.10") * a5),
    )


def _qualify_retest(
    event: MarketEvent, bar: Bar, pullback_extreme: Decimal
) -> RetestType | None:
    if event.impulse_extreme is None:
        raise KernelInputError("breakout impulse extreme is missing")
    a5 = event.a5_event
    if event.side is Side.LONG:
        deep = (
            bar.low <= event.zone.high + Decimal("0.25") * a5
            and bar.close >= event.zone.high + Decimal("0.05") * a5
        )
        denominator = event.impulse_extreme - event.zone.high
        ratio = (
            (event.impulse_extreme - pullback_extreme) / denominator
            if denominator > 0
            else Decimal("-1")
        )
        shallow = (
            pullback_extreme > event.zone.high + Decimal("0.25") * a5
            and Decimal("0.25") <= ratio <= Decimal("0.60")
        )
    else:
        deep = (
            bar.high >= event.zone.low - Decimal("0.25") * a5
            and bar.close <= event.zone.low - Decimal("0.05") * a5
        )
        denominator = event.zone.low - event.impulse_extreme
        ratio = (
            (pullback_extreme - event.impulse_extreme) / denominator
            if denominator > 0
            else Decimal("-1")
        )
        shallow = (
            pullback_extreme < event.zone.low - Decimal("0.25") * a5
            and Decimal("0.25") <= ratio <= Decimal("0.60")
        )
    if deep:
        return RetestType.DEEP
    if shallow:
        return RetestType.SHALLOW
    return None


def _progress_breakout(
    event: MarketEvent, bar: Bar
) -> tuple[MarketEvent, StrategyDecision | None]:
    if event.previous_close is None or event.previous_high is None or event.previous_low is None:
        raise KernelInputError("breakout event previous-bar state is missing")
    if _accepted_reentry(event, bar):
        updated = event.evolve(
            status=EventStatus.INVALIDATED,
            transition="INVALIDATED_ACCEPTED_REENTRY",
            latest_bar=bar,
        )
        return updated, _decision(
            updated,
            kind=DecisionKind.INVALIDATED,
            reason="INVALIDATED_ACCEPTED_REENTRY",
            transition=updated.transition,
        )

    if not event.pullback_started:
        pullback_start = (
            bar.close < event.previous_close
            if event.side is Side.LONG
            else bar.close > event.previous_close
        )
        if pullback_start:
            pullback_extreme = bar.low if event.side is Side.LONG else bar.high
            retest_type = _qualify_retest(event, bar, pullback_extreme)
            return (
                event.evolve(
                    latest_bar=bar,
                    transition="PULLBACK_STARTED_STANDARD_ONLY",
                    previous_close=bar.close,
                    previous_high=bar.high,
                    previous_low=bar.low,
                    pullback_started=True,
                    pullback_extreme=pullback_extreme,
                    retest_type=retest_type,
                    retest_seen_bar_time_ms=(
                        bar.open_time_ms if retest_type is not None else None
                    ),
                ),
                None,
            )
        if _micro_confirmation(event, bar):
            ideal_low, ideal_high, chase, stop = _micro_terms(event)
            updated = event.evolve(
                status=EventStatus.CONFIRMED,
                transition="FORMAL_SETUP_CONFIRMED",
                latest_bar=bar,
                formal_mode=SetupMode.MICRO_FAST,
                ideal_entry_low=ideal_low,
                ideal_entry_high=ideal_high,
                chase_limit=chase,
                structural_stop=stop,
            )
            return updated, _decision(
                updated,
                kind=DecisionKind.FORMAL_SETUP_CONFIRMED,
                reason="BREAKOUT_MICRO_FAST_CONFIRMED",
                transition=updated.transition,
            )
        if event.impulse_extreme is None:
            raise KernelInputError("breakout impulse extreme is missing")
        impulse = (
            max(event.impulse_extreme, bar.high)
            if event.side is Side.LONG
            else min(event.impulse_extreme, bar.low)
        )
        return (
            event.evolve(
                latest_bar=bar,
                transition="MICRO_FAST_WAIT",
                previous_close=bar.close,
                previous_high=bar.high,
                previous_low=bar.low,
                impulse_extreme=impulse,
            ),
            None,
        )

    if event.pullback_extreme is None:
        raise KernelInputError("standard pullback extreme is missing")
    pullback_extreme = (
        min(event.pullback_extreme, bar.low)
        if event.side is Side.LONG
        else max(event.pullback_extreme, bar.high)
    )
    qualified = _qualify_retest(event, bar, pullback_extreme)
    retest_type = event.retest_type
    seen_time = event.retest_seen_bar_time_ms
    if qualified is RetestType.DEEP:
        retest_type = qualified
        seen_time = seen_time if event.retest_type is qualified else bar.open_time_ms
    elif retest_type is None and qualified is RetestType.SHALLOW:
        retest_type = qualified
        seen_time = bar.open_time_ms
    after_retest = seen_time is not None and bar.open_time_ms > seen_time
    confirms = (
        bar.close > event.previous_high
        if event.side is Side.LONG
        else bar.close < event.previous_low
    )
    if retest_type is not None and after_retest and confirms:
        ideal_low, ideal_high, chase, stop = _standard_terms(event, pullback_extreme)
        updated = event.evolve(
            status=EventStatus.CONFIRMED,
            transition="FORMAL_SETUP_CONFIRMED",
            latest_bar=bar,
            formal_mode=SetupMode.STANDARD,
            pullback_extreme=pullback_extreme,
            retest_type=retest_type,
            retest_seen_bar_time_ms=seen_time,
            ideal_entry_low=ideal_low,
            ideal_entry_high=ideal_high,
            chase_limit=chase,
            structural_stop=stop,
        )
        reason = (
            "BREAKOUT_STANDARD_CONFIRMED_DEEP_RETEST"
            if retest_type is RetestType.DEEP
            else "BREAKOUT_STANDARD_CONFIRMED_SHALLOW_RETEST"
        )
        return updated, _decision(
            updated,
            kind=DecisionKind.FORMAL_SETUP_CONFIRMED,
            reason=reason,
            transition=updated.transition,
        )
    return (
        event.evolve(
            latest_bar=bar,
            transition="STANDARD_WAIT_NO_ECONOMIC_TIMEOUT",
            previous_close=bar.close,
            previous_high=bar.high,
            previous_low=bar.low,
            pullback_extreme=pullback_extreme,
            retest_type=retest_type,
            retest_seen_bar_time_ms=seen_time,
        ),
        None,
    )


def _range_valid(
    *, support: ZoneSnapshot | None, resistance: ZoneSnapshot | None, bars_15m: tuple[Bar, ...]
) -> bool:
    if support is None or resistance is None or len(bars_15m) < 15:
        return False
    if not _eligible(support, ZoneType.LOW) or not _eligible(resistance, ZoneType.HIGH):
        return False
    a15 = wilder_atr14(bars_15m)
    width = resistance.center - support.center
    if not Decimal("1.5") * a15 <= width <= Decimal("5.0") * a15:
        return False
    if len(bars_15m) < 9:
        return False
    if directional_efficiency_8(bars_15m) > Decimal("0.35"):
        return False
    if abs(bars_15m[-1].close - bars_15m[-9].close) > a15:
        return False
    return all(
        support.low - Decimal("0.10") * a15
        <= item.close
        <= resistance.high + Decimal("0.10") * a15
        for item in bars_15m[-8:]
    )


def _range_candidate(
    *, bar: Bar, previous_close: Decimal, zone: ZoneSnapshot, side: Side, a5: Decimal, m20: Decimal
) -> bool:
    tr = true_range(bar, previous_close)
    if tr <= 0:
        return False
    if side is Side.LONG:
        lower_wick = min(bar.open, bar.close) - bar.low
        return (
            bar.low <= zone.high + Decimal("0.10") * a5
            and bar.close >= zone.low + Decimal("0.05") * a5
            and clv_long(bar) >= Decimal("0.70")
            and lower_wick / tr >= Decimal("0.35")
            and bar.volume >= m20
        )
    upper_wick = bar.high - max(bar.open, bar.close)
    return (
        bar.high >= zone.low - Decimal("0.10") * a5
        and bar.close <= zone.high - Decimal("0.05") * a5
        and clv_short(bar) >= Decimal("0.70")
        and upper_wick / tr >= Decimal("0.35")
        and bar.volume >= m20
    )


def _new_range(
    *,
    bar: Bar,
    zone: ZoneSnapshot,
    other_zone: ZoneSnapshot,
    side: Side,
    a5: Decimal,
    m20: Decimal,
    relation: HtfRelation,
    scanner_linkage: ScannerLinkage | None,
) -> MarketEvent:
    range_center = (zone.center + other_zone.center) / Decimal(2)
    if side is Side.LONG:
        ideal_low = zone.low
        ideal_high = zone.high + Decimal("0.10") * a5
        chase = zone.high + Decimal("0.35") * a5
        stop = bar.low - Decimal("0.10") * a5
    else:
        ideal_low = zone.low - Decimal("0.10") * a5
        ideal_high = zone.high
        chase = zone.low - Decimal("0.35") * a5
        stop = bar.high + Decimal("0.10") * a5
    return MarketEvent(
        market_event_id=market_event_id(
            market_id=bar.market_id,
            zone_id=zone.zone_id,
            side=side,
            first_attack_5m_candle_id=bar.candle_id,
        ),
        market_id=bar.market_id,
        setup_family=SetupFamily.RANGE_EDGE_REJECTION,
        side=side,
        status=EventStatus.CONFIRMED,
        transition="FORMAL_SETUP_CONFIRMED",
        zone=zone,
        created_bar=bar,
        latest_bar=bar,
        a5_event=a5,
        m20_event=m20,
        htf_relation=relation,
        scanner_linkage=scanner_linkage,
        ideal_entry_low=ideal_low,
        ideal_entry_high=ideal_high,
        chase_limit=chase,
        structural_stop=stop,
        target_reference=TargetReference(TargetKind.RANGE_CENTER, range_center),
    )


def _replace(ledger: EventLedger, original: MarketEvent, updated: MarketEvent) -> EventLedger:
    events = tuple(updated if item is original else item for item in ledger.events)
    if events == ledger.events and original is not updated:
        raise KernelInputError("event ledger replacement failed")
    return EventLedger(events)


def _invalidate_opposite_active(
    ledger: EventLedger, confirmed: tuple[MarketEvent, ...]
) -> tuple[EventLedger, tuple[StrategyDecision, ...]]:
    decisions: list[StrategyDecision] = []
    current = ledger
    for formal in confirmed:
        for event in current.events:
            if (
                event.market_id == formal.market_id
                and event.side is formal.side.opposite
                and event.status is EventStatus.ACTIVE
                and event.created_bar.open_time_ms < formal.latest_bar.open_time_ms
            ):
                updated = event.evolve(
                    status=EventStatus.INVALIDATED,
                    transition="INVALIDATED_BY_OPPOSITE_FORMAL_EVENT",
                    latest_bar=formal.latest_bar,
                )
                current = _replace(current, event, updated)
                decisions.append(
                    _decision(
                        updated,
                        kind=DecisionKind.INVALIDATED,
                        reason="OPPOSITE_FORMAL_EVENT",
                        transition=updated.transition,
                    )
                )
    return current, tuple(decisions)


def _active_zones(book: ZoneBook) -> tuple[ZoneSnapshot, ...]:
    return tuple(
        item
        for item in book.zones
        if item.active_for_new_event and not item.suppressed and item.quality.rank >= 2
    )


def _contains_event_id(
    ledger: EventLedger, event_id: str, family: SetupFamily
) -> bool:
    return any(
        item.market_event_id == event_id and item.setup_family is family
        for item in ledger.events
    )


def _supersede_for_new_zone(
    ledger: EventLedger,
    active: MarketEvent,
    bar: Bar,
) -> tuple[EventLedger, StrategyDecision]:
    updated = active.evolve(
        status=EventStatus.SUPERSEDED,
        transition="SUPERSEDED_BY_NEW_INDEPENDENT_EVENT",
        latest_bar=bar,
    )
    return _replace(ledger, active, updated), _decision(
        updated,
        kind=DecisionKind.SUPERSEDED,
        reason="SUPERSEDED_BY_NEW_INDEPENDENT_EVENT",
        transition=updated.transition,
    )


def evaluate_strategy(
    inputs: StrategyEvaluationInput, ledger: EventLedger | None = None
) -> KernelResult:
    """Evaluate the latest closed 5m bar and return a new immutable state."""
    validate_series(inputs.bars_5m, interval="5m")
    current_bar = inputs.bars_5m[-1]
    if inputs.bars_15m is None:
        bars_15m = aggregate_closed_5m_causally(inputs.bars_5m, minutes=15)
    else:
        bars_15m = inputs.bars_15m
        validate_series(bars_15m, interval="15m")
    if inputs.bars_1h is None:
        bars_1h = aggregate_closed_5m_causally(inputs.bars_5m, minutes=60)
    else:
        bars_1h = inputs.bars_1h
        if bars_1h:
            validate_series(bars_1h, interval="1h")
    context = htf_context(bars_1h)
    if inputs.zone_book is None:
        if not bars_15m:
            raise KernelInputError("strategy evaluation requires causal 15m history")
        book = build_zone_book(bars_15m, minimum_tick=inputs.minimum_tick)
    else:
        book = inputs.zone_book

    decisions: list[StrategyDecision] = []
    current_ledger = EventLedger() if ledger is None else ledger
    if not inputs.mandatory_data_valid:
        for event in current_ledger.events:
            if event.status is EventStatus.ACTIVE:
                updated = event.evolve(
                    status=EventStatus.DATA_INVALID,
                    transition="CORE_DATA_INVALID",
                    latest_bar=current_bar,
                )
                current_ledger = _replace(current_ledger, event, updated)
                decisions.append(
                    _decision(
                        updated,
                        kind=DecisionKind.DATA_INVALID,
                        reason="MULTITIMEFRAME_DATA_INVALID",
                        transition=updated.transition,
                    )
                )
        return KernelResult(
            current_ledger,
            tuple(decisions),
            book.zones,
            book.active_support,
            book.active_resistance,
            context,
        )

    a5 = wilder_atr14(inputs.bars_5m)
    m20 = median_previous_20_volume(inputs.bars_5m)
    accepted_reentries: dict[tuple[str, Side, str], BreakoutLinkage] = {}
    confirmed_events: list[MarketEvent] = []
    creation_blocked: set[tuple[SetupFamily, Side]] = set()

    # Progress only events created before this candle.  Re-evaluation of the
    # same closed candle is an idempotent read and cannot confirm itself.
    for event in tuple(current_ledger.events):
        if event.status is not EventStatus.ACTIVE or event.market_id != current_bar.market_id:
            continue
        if event.latest_bar.open_time_ms >= current_bar.open_time_ms:
            continue
        if event.setup_family is SetupFamily.SWEEP_RECLAIM:
            updated, decision = _progress_sweep(event, current_bar)
        elif event.setup_family is SetupFamily.BREAKOUT_RETEST:
            updated, decision = _progress_breakout(event, current_bar)
        else:
            continue
        current_ledger = _replace(current_ledger, event, updated)
        if updated.status.terminal and updated.status is not EventStatus.SUPERSEDED:
            creation_blocked.add((event.setup_family, event.side))
        if decision is not None:
            decisions.append(decision)
            if decision.decision is DecisionKind.FORMAL_SETUP_CONFIRMED:
                confirmed_events.append(updated)
            if decision.reason == "INVALIDATED_ACCEPTED_REENTRY" and updated.breakout_linkage:
                reentry_key = (
                    updated.zone.zone_id,
                    updated.side.opposite,
                    updated.market_id,
                )
                accepted_reentries[reentry_key] = (
                    BreakoutLinkage(
                        updated.breakout_linkage.underlying_breakout_event_id,
                        updated.breakout_linkage.initial_breakout_candle_id,
                        updated.market_event_id,
                    )
                )

    # Candidate creation uses the current Event-zone winners, while every
    # created event freezes its complete ZoneSnapshot.
    sweep_specs = (
        (Side.LONG, book.active_support, ZoneType.LOW),
        (Side.SHORT, book.active_resistance, ZoneType.HIGH),
    )
    for side, zone, required_type in sweep_specs:
        if zone is None or not _eligible(zone, required_type):
            continue
        if (SetupFamily.SWEEP_RECLAIM, side) in creation_blocked:
            continue
        active = current_ledger.active(
            market_id=current_bar.market_id,
            family=SetupFamily.SWEEP_RECLAIM,
            side=side,
        )
        candidate_matches = _sweep_candidate(current_bar, zone, side, a5)
        if active is not None:
            if active.zone.zone_id == zone.zone_id or not candidate_matches:
                continue
            current_ledger, supersession = _supersede_for_new_zone(
                current_ledger, active, current_bar
            )
            decisions.append(supersession)
        if candidate_matches:
            linkage = accepted_reentries.get((zone.zone_id, side, current_bar.market_id))
            event = _new_sweep(
                bar=current_bar,
                zone=zone,
                side=side,
                a5=a5,
                m20=m20,
                relation=htf_relation(context, side),
                scanner_linkage=inputs.scanner_linkage,
                breakout_linkage=linkage,
            )
            if _contains_event_id(
                current_ledger, event.market_event_id, event.setup_family
            ):
                continue
            current_ledger = current_ledger.append(event)
            decisions.append(
                _decision(
                    event,
                    kind=DecisionKind.WAIT,
                    reason="SWEEP_CANDIDATE_CREATED",
                    transition=event.transition,
                )
            )

    breakout_specs = (
        (Side.LONG, book.active_resistance, ZoneType.HIGH),
        (Side.SHORT, book.active_support, ZoneType.LOW),
    )
    all_active_zones = _active_zones(book)
    for side, zone, required_type in breakout_specs:
        if zone is None or not _eligible(zone, required_type):
            continue
        if (SetupFamily.BREAKOUT_RETEST, side) in creation_blocked:
            continue
        active = current_ledger.active(
            market_id=current_bar.market_id,
            family=SetupFamily.BREAKOUT_RETEST,
            side=side,
        )
        candidate_matches = _initial_breakout(current_bar, zone, side, a5, m20)
        if active is not None:
            if active.zone.zone_id == zone.zone_id or not candidate_matches:
                continue
            current_ledger, supersession = _supersede_for_new_zone(
                current_ledger, active, current_bar
            )
            decisions.append(supersession)
        if candidate_matches:
            event = _new_breakout(
                bar=current_bar,
                zone=zone,
                side=side,
                a5=a5,
                m20=m20,
                relation=htf_relation(context, side),
                scanner_linkage=inputs.scanner_linkage,
                zones=all_active_zones,
            )
            if _contains_event_id(
                current_ledger, event.market_event_id, event.setup_family
            ):
                continue
            current_ledger = current_ledger.append(event)
            decisions.append(
                _decision(
                    event,
                    kind=DecisionKind.WAIT,
                    reason="INITIAL_BREAKOUT_EVENT_CREATED",
                    transition=event.transition,
                )
            )

    if _range_valid(
        support=book.active_support,
        resistance=book.active_resistance,
        bars_15m=bars_15m,
    ) and len(inputs.bars_5m) >= 2:
        range_specs = (
            (Side.LONG, book.active_support, book.active_resistance),
            (Side.SHORT, book.active_resistance, book.active_support),
        )
        for side, zone, other in range_specs:
            if zone is None or other is None:
                continue
            if _range_candidate(
                bar=current_bar,
                previous_close=inputs.bars_5m[-2].close,
                zone=zone,
                side=side,
                a5=a5,
                m20=m20,
            ):
                event = _new_range(
                    bar=current_bar,
                    zone=zone,
                    other_zone=other,
                    side=side,
                    a5=a5,
                    m20=m20,
                    relation=htf_relation(context, side),
                    scanner_linkage=inputs.scanner_linkage,
                )
                if _contains_event_id(
                    current_ledger, event.market_event_id, event.setup_family
                ):
                    continue
                current_ledger = current_ledger.append(event)
                confirmed_events.append(event)
                decisions.append(
                    _decision(
                        event,
                        kind=DecisionKind.FORMAL_SETUP_CONFIRMED,
                        reason=(
                            "RANGE_LONG_CONFIRMED"
                            if side is Side.LONG
                            else "RANGE_SHORT_CONFIRMED"
                        ),
                        transition=event.transition,
                    )
                )

    current_ledger, opposite_decisions = _invalidate_opposite_active(
        current_ledger, tuple(confirmed_events)
    )
    decisions.extend(opposite_decisions)
    return KernelResult(
        current_ledger,
        tuple(decisions),
        book.zones,
        book.active_support,
        book.active_resistance,
        context,
    )


def mark_unresolved_at_shutdown(ledger: EventLedger) -> EventLedger:
    """Explicit shutdown transition; never a time-based economic expiry."""
    return EventLedger(
        tuple(
            event.evolve(
                status=EventStatus.UNRESOLVED_AT_SHUTDOWN,
                transition="UNRESOLVED_AT_SHUTDOWN",
            )
            if event.status is EventStatus.ACTIVE
            else event
            for event in ledger.events
        )
    )
