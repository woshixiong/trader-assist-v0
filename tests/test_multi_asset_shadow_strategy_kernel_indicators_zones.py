from __future__ import annotations

from decimal import Decimal

import pytest

from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    HtfMomentum,
    HtfRelation,
    HtfStructure,
    KernelInputError,
    Reaction,
    Side,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
    aggregate_closed_5m_causally,
    build_zone_book,
    causal_pivot_high_indices,
    causal_pivot_low_indices,
    clv_long,
    clv_short,
    directional_efficiency_8,
    htf_context,
    htf_relation,
    median_previous_20_volume,
    wilder_atr14,
    wilder_atr14_series,
)

MARKET = "1" * 64


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
        market_id=MARKET,
        interval=interval,
        open_time_ms=index * width,
        close_time_ms=(index + 1) * width,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def test_wilder_atr_seed_recursion_m20_clv_and_er8_are_exact() -> None:
    bars = tuple(bar(index, volume=str(index + 1)) for index in range(21))
    series = wilder_atr14_series(bars)
    assert series[:14] == (None,) * 14
    assert series[14] == Decimal("3")
    assert wilder_atr14(bars) == Decimal("3")
    assert median_previous_20_volume(bars) == Decimal("10.5")
    assert clv_long(bar(0)) == Decimal(2) / Decimal(3)
    assert clv_short(bar(0)) == Decimal(1) / Decimal(3)
    flat = tuple(bar(index, close="100") for index in range(9))
    assert directional_efficiency_8(flat) == 0


def test_local_15m_and_1h_aggregation_is_complete_utc_aligned_and_no_lookahead() -> None:
    bars = tuple(
        bar(
            index,
            open_=str(100 + index),
            high=str(101 + index),
            low=str(99 + index),
            close=str(100 + index),
        )
        for index in range(13)
    )
    fifteen = aggregate_closed_5m_causally(bars, minutes=15)
    hourly = aggregate_closed_5m_causally(bars, minutes=60)
    assert len(fifteen) == 4
    assert fifteen[-1].close == Decimal("111")
    assert len(hourly) == 1
    assert hourly[0].close == Decimal("111")
    assert bars[-1].close == Decimal("112")  # incomplete future buckets stay invisible
    with pytest.raises(KernelInputError, match="gap"):
        aggregate_closed_5m_causally((*bars[:2], *bars[3:]), minutes=15)


def test_causal_pivots_require_the_right_bar_and_htf_states_are_mirrored() -> None:
    partial = (
        bar(0, interval="1h", high="101", low="99"),
        bar(1, interval="1h", high="105", low="100", close="104"),
    )
    assert causal_pivot_high_indices(partial) == ()
    closed_right = (*partial, bar(2, interval="1h", high="104", low="98", close="99"))
    assert causal_pivot_high_indices(closed_right) == (1,)
    assert causal_pivot_low_indices(closed_right) == ()

    rising = tuple(
        bar(
            index,
            interval="1h",
            open_=str(100 + index),
            high=str(102 + index),
            low=str(99 + index),
            close=str(101 + index),
        )
        for index in range(20)
    )
    context = htf_context(rising)
    assert context.momentum is HtfMomentum.UP
    assert context.structure is HtfStructure.INSUFFICIENT
    assert htf_relation(context, Side.LONG) is HtfRelation.ALIGNED_PARTIAL
    assert htf_relation(context, Side.SHORT) is HtfRelation.COUNTERTREND_PARTIAL
    unavailable = htf_context(rising[:8])
    assert unavailable.momentum is HtfMomentum.UNAVAILABLE
    assert unavailable.structure is HtfStructure.UNAVAILABLE


def _htf_pattern(values: tuple[tuple[str, str, str], ...]) -> tuple[Bar, ...]:
    return tuple(
        bar(
            index,
            interval="1h",
            open_=close,
            high=high,
            low=low,
            close=close,
        )
        for index, (close, high, low) in enumerate(values)
    )


def test_htf_momentum_down_neutral_and_structure_range_transition() -> None:
    rising_values = tuple(
        (str(value), str(value + 2), str(value - 2))
        for value in (
            100,
            105,
            100,
            95,
            100,
            110,
            103,
            98,
            101,
            106,
            115,
            110,
            104,
            108,
            112,
            114,
            116,
            118,
            120,
            122,
        )
    )
    upward = htf_context(_htf_pattern(rising_values))
    downward = htf_context(
        _htf_pattern(
            tuple(
                (str(300 - int(close)), str(304 - int(low)), str(296 - int(high)))
                for close, high, low in rising_values
            )
        )
    )
    assert upward.momentum is HtfMomentum.UP
    assert upward.structure is HtfStructure.UP
    assert downward.momentum is HtfMomentum.DOWN
    assert downward.structure is HtfStructure.DOWN

    range_values = tuple(
        (str(close), str(high), str(low))
        for close, high, low in (
            (100, 102, 98),
            (105, 107, 103),
            (100, 102, 98),
            (95, 97, 93),
            (100, 102, 98),
            (104, 106, 102),
            (100, 102, 98),
            (96, 98, 94),
            *((100, 102, 98),) * 12,
        )
    )
    transition_values = tuple(
        (str(close), str(high), str(low))
        for close, high, low in (
            (100, 102, 98),
            (105, 107, 103),
            (100, 102, 98),
            (95, 97, 93),
            (100, 102, 98),
            (110, 112, 108),
            (100, 102, 98),
            (90, 92, 88),
            (111, 113, 98),
            *((100, 102, 98),) * 11,
        )
    )
    ranged = htf_context(_htf_pattern(range_values))
    transitioning = htf_context(_htf_pattern(transition_values))
    assert ranged.momentum is HtfMomentum.NEUTRAL
    assert ranged.structure is HtfStructure.RANGE
    assert transitioning.structure is HtfStructure.TRANSITION


def _zone_bars(
    *, high_reaction_indices: frozenset[int] = frozenset({16, 20, 24})
) -> tuple[Bar, ...]:
    values: list[Bar] = []
    # Alternating, separated reactions near two centers.  Their one-bar
    # move-away is large enough for qualification at the causal confirmation.
    for index in range(40):
        high = Decimal("106") if index in high_reaction_indices else Decimal("103")
        low = Decimal("94") if index in {18, 22, 26} else Decimal("97")
        close = Decimal("100")
        values.append(
            bar(
                index,
                interval="15m",
                open_=str(close),
                high=str(high),
                low=str(low),
                close=str(close),
            )
        )
    return tuple(values)


def test_zone_engine_qualifies_reactions_clusters_geometry_quality_and_snapshot_age() -> None:
    book = build_zone_book(_zone_bars(), minimum_tick=Decimal("0.1"))
    assert any(zone.quality is ZoneQuality.ZQ3 for zone in book.zones)
    for zone in book.zones:
        assert zone.half_width >= Decimal("0.15") * wilder_atr14(_zone_bars())
        assert zone.half_width <= Decimal("0.40") * wilder_atr14(_zone_bars())
        assert zone.center == Decimal("106") or zone.center == Decimal("94")
        assert zone.zone_id == zone.zone_id.lower() and len(zone.zone_id) == 64
    assert book.active_support is not None
    assert book.active_resistance is not None

    aged = (*_zone_bars(), *(bar(40 + index, interval="15m") for index in range(25)))
    stale_book = build_zone_book(aged, minimum_tick=Decimal("0.1"))
    assert all(not zone.active_for_new_event for zone in stale_book.zones)


@pytest.mark.parametrize(
    ("expected_quality", "high_reaction_indices"),
    (
        (ZoneQuality.ZQ2, frozenset({20, 24})),
        (ZoneQuality.ZQ3, frozenset({16, 20, 24})),
    ),
)
@pytest.mark.parametrize(
    ("extra_bars", "age", "eligible"),
    ((9, 23, True), (10, 24, True), (11, 25, False)),
)
def test_zone_latest_reaction_age_boundary_retains_evidence_but_gates_new_events(
    extra_bars: int,
    age: int,
    eligible: bool,
    expected_quality: ZoneQuality,
    high_reaction_indices: frozenset[int],
) -> None:
    source = _zone_bars(high_reaction_indices=high_reaction_indices)
    bars = (*source, *(bar(40 + index, interval="15m") for index in range(extra_bars)))
    book = build_zone_book(bars, minimum_tick=Decimal("0.1"))
    high_zone = next(zone for zone in book.zones if zone.zone_type is ZoneType.HIGH)

    assert len(bars) - 1 - high_zone.latest_reaction_bar_index == age
    assert high_zone.quality is expected_quality
    assert high_zone.reaction_count == expected_quality.rank
    assert high_zone.active_for_new_event is eligible
    assert high_zone.member_reaction_ids
    assert all(
        any(reaction.reaction_id == reaction_id for reaction in book.reactions)
        for reaction_id in high_zone.member_reaction_ids
    )
    assert (book.active_resistance is high_zone) is eligible


def test_zone_lookback_excludes_old_reactions_without_changing_past_output() -> None:
    original = build_zone_book(_zone_bars(), minimum_tick=Decimal("0.1"))
    extended = (*_zone_bars(), *(bar(40 + index, interval="15m") for index in range(100)))
    later = build_zone_book(extended, minimum_tick=Decimal("0.1"))
    assert original.reactions
    assert not later.reactions  # all original pivots fell outside the frozen 96/effective window


def test_zone_cluster_and_overlap_tie_breaks_are_deterministic() -> None:
    from trader_assist_v0.multi_asset_shadow.strategy_kernel.zones import (
        _clusters,
        _suppress_overlaps,
    )

    reactions = (
        Reaction("r1", MARKET, ZoneType.HIGH, 1, 2, Decimal("100"), Decimal("1")),
        Reaction("r2", MARKET, ZoneType.HIGH, 3, 4, Decimal("100.4"), Decimal("1")),
        Reaction("r3", MARKET, ZoneType.HIGH, 5, 6, Decimal("100.2"), Decimal("1")),
    )
    clustered = _clusters(reactions, Decimal("0.01"))
    assert [item.reaction_id for item in clustered[0].members] == ["r1", "r3"]
    assert [item.reaction_id for item in clustered[1].members] == ["r2"]

    winner = ZoneSnapshot(
        "a" * 64,
        MARKET,
        ZoneType.HIGH,
        Decimal("100"),
        Decimal("99"),
        Decimal("101"),
        Decimal("1"),
        ZoneQuality.ZQ3,
        3,
        10,
        ("a", "b", "c"),
        True,
    )
    loser = ZoneSnapshot(
        "b" * 64,
        MARKET,
        ZoneType.HIGH,
        Decimal("100.5"),
        Decimal("99.5"),
        Decimal("101.5"),
        Decimal("1"),
        ZoneQuality.ZQ2,
        2,
        11,
        ("d", "e"),
        True,
    )
    suppressed = _suppress_overlaps((loser, winner), Decimal("100"))
    assert next(item for item in suppressed if item.zone_id == winner.zone_id).suppressed is False
    assert next(item for item in suppressed if item.zone_id == loser.zone_id).suppressed is True
