from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from importlib.metadata import version

import pytest

pytest.importorskip("nautilus_trader")

from n0_bridge import close_boundary_ns, dispatch_offline, kernel_bar_from_event, project_closed_bar
from trader_assist_v0.multi_asset_shadow.models import ClosedBar
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    BreakoutLinkage,
    DecisionKind,
    EventLedger,
    EventStatus,
    HtfRelation,
    MarketEvent,
    SetupFamily,
    StrategyEvaluationInput,
    TargetKind,
    TargetReference,
    ZoneBook,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
    evaluate_strategy,
    market_event_id,
)

MARKET = "2" * 64
PROVENANCE = "3" * 64
RECEIVED_AT = datetime(2026, 9, 8, tzinfo=UTC)


def _bar(index: int, interval: str = "5m", **values: str) -> Bar:
    width = {"5m": 300_000, "15m": 900_000}[interval]
    return Bar(
        MARKET, interval, index * width, (index + 1) * width,
        *(Decimal(values.get(name, value)) for name, value in (
            ("open", "100"), ("high", "102"), ("low", "99"), ("close", "101"), ("volume", "10")
        )),
    )


def _closed(bar: Bar) -> ClosedBar:
    return ClosedBar.create(
        market_id=bar.market_id, interval=bar.interval,
        open_time_ms=bar.open_time_ms, close_time_ms=bar.close_time_ms,
        open=bar.open, high=bar.high, low=bar.low, close=bar.close, volume=bar.volume,
        source_id="n0-current-project-fixture", provenance_hash=PROVENANCE, received_at=RECEIVED_AT,
    )


SUPPORT = ZoneSnapshot("a" * 64, MARKET, ZoneType.LOW, Decimal("100"), Decimal("99.5"), Decimal("100.5"), Decimal("0.5"), ZoneQuality.ZQ3, 3, 20, ("r1", "r2", "r3"), True)
RESISTANCE = ZoneSnapshot("b" * 64, MARKET, ZoneType.HIGH, Decimal("110"), Decimal("109.5"), Decimal("110.5"), Decimal("0.5"), ZoneQuality.ZQ3, 3, 20, ("r1", "r2", "r3"), True)
BOOK = ZoneBook((SUPPORT, RESISTANCE), (), SUPPORT, RESISTANCE)


def _event(family: SetupFamily, source: ZoneSnapshot, created: Bar, **changes: object) -> MarketEvent:
    side = {SetupFamily.SWEEP_RECLAIM: "LONG", SetupFamily.BREAKOUT_RETEST: "LONG"}[family]
    from trader_assist_v0.multi_asset_shadow.strategy_kernel import Side

    typed_side = Side(side)
    value = MarketEvent(
        market_event_id(market_id=MARKET, zone_id=source.zone_id, side=typed_side, first_attack_5m_candle_id=created.candle_id),
        MARKET, family, typed_side, EventStatus.ACTIVE, "CREATED", source, created, created,
        Decimal("2"), Decimal("10"), HtfRelation.NEUTRAL,
        previous_close=created.close, previous_high=created.high, previous_low=created.low,
    )
    return value.evolve(**changes)


def _fixture(family: SetupFamily) -> tuple[tuple[Bar, ...], EventLedger]:
    fives = [_bar(index) for index in range(61)]
    fifteens = [_bar(index, "15m", **({"open": "105", "high": "106", "low": "104", "close": "105"} if family is SetupFamily.RANGE_EDGE_REJECTION else {})) for index in range(20)]
    if family is SetupFamily.SWEEP_RECLAIM:
        fives[-2] = _bar(59, open="100", high="101", low="99", close="100")
        fives[-1] = _bar(60, open="100", high="102", low="99.2", close="101.2")
        active = _event(family, SUPPORT, fives[-2], reclaim_candle_high=fives[-2].high, reclaim_candle_low=fives[-2].low, sweep_extreme=fives[-2].low, structural_stop=Decimal("98.8"), ideal_entry_low=Decimal("99.6"), ideal_entry_high=Decimal("100"), chase_limit=Decimal("100.2"), target_reference=TargetReference(TargetKind.SOURCE_ZONE_CENTER, SUPPORT.center, SUPPORT.zone_id))
        ledger = EventLedger((active,))
    elif family is SetupFamily.BREAKOUT_RETEST:
        fives[-2] = _bar(59, open="110", high="112", low="109.8", close="111.8", volume="15")
        fives[-1] = _bar(60, open="111.8", high="113", low="111", close="112.8")
        active = _event(family, RESISTANCE, fives[-2], breakout_linkage=BreakoutLinkage("u" * 64, fives[-2].candle_id), initial_breakout_open=fives[-2].open, initial_breakout_high=fives[-2].high, initial_breakout_low=fives[-2].low, initial_breakout_close=fives[-2].close, impulse_extreme=fives[-2].high, target_reference=TargetReference(TargetKind.OPEN_SPACE_REFERENCE, None))
        ledger = EventLedger((active,))
    else:
        fives[-1] = _bar(60, open="101", high="102", low="99.8", close="101.5")
        ledger = EventLedger()
    return tuple(fives + fifteens), ledger


@pytest.mark.parametrize("family", tuple(SetupFamily))
def test_exact_rc4_official_dispatch_is_lossless_and_kernel_identical(family: SetupFamily) -> None:
    assert version("nautilus_trader") == "2.0.0rc4"
    direct, ledger = _fixture(family)
    projected = tuple(_closed(bar) for bar in direct)
    event = project_closed_bar(projected[-1])
    restored = kernel_bar_from_event(event)
    assert restored.market_id == projected[-1].market_id
    assert restored.interval == projected[-1].interval
    assert (restored.open_time_ms, restored.close_time_ms) == (projected[-1].open_time_ms, projected[-1].close_time_ms)
    assert (restored.open, restored.high, restored.low, restored.close, restored.volume) == (projected[-1].open, projected[-1].high, projected[-1].low, projected[-1].close, projected[-1].volume)
    assert restored.source_identity == projected[-1].canonical_hash
    assert event.ts_event == event.ts_init == close_boundary_ns(projected[-1])

    def exact_current_kernel(received: tuple[Bar, ...]):
        fives = tuple(bar for bar in received if bar.interval == "5m")
        fifteens = tuple(bar for bar in received if bar.interval == "15m")
        if len(fives) != 61 or len(fifteens) != 20:
            return None
        return evaluate_strategy(StrategyEvaluationInput(fives, Decimal("0.1"), fifteens, (), BOOK), ledger)

    direct_result = exact_current_kernel(tuple(kernel_bar_from_event(project_closed_bar(bar)) for bar in projected))
    mediated = dispatch_offline(projected, exact_current_kernel)
    expected_delivery = tuple(sorted(projected, key=close_boundary_ns))
    assert mediated.bars == tuple(kernel_bar_from_event(project_closed_bar(bar)) for bar in expected_delivery)
    assert mediated.delivery_times == tuple(sorted(mediated.delivery_times))
    assert mediated.outputs[-1] == direct_result
    assert direct_result is not None
    assert any(item.setup_family is family for item in direct_result.ledger.events)
    if family is not SetupFamily.RANGE_EDGE_REJECTION:
        assert any(item.decision is DecisionKind.FORMAL_SETUP_CONFIRMED for item in direct_result.decisions)
