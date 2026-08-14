"""Deterministic causal 15m reaction-zone engine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256
from statistics import median

from .indicators import (
    causal_pivot_high_indices,
    causal_pivot_low_indices,
    validate_series,
    wilder_atr14_series,
)
from .types import (
    PARAMETER_VERSION,
    Bar,
    KernelInputError,
    Reaction,
    ZoneQuality,
    ZoneSnapshot,
    ZoneType,
)

ZONE_LOOKBACK_15M = 96


@dataclass(frozen=True)
class ZoneBook:
    zones: tuple[ZoneSnapshot, ...]
    reactions: tuple[Reaction, ...]
    active_support: ZoneSnapshot | None
    active_resistance: ZoneSnapshot | None


@dataclass
class _Cluster:
    zone_type: ZoneType
    members: list[Reaction]
    created_bar_index: int

    @property
    def center(self) -> Decimal:
        return median(item.price for item in self.members)

    @property
    def identity(self) -> str:
        return _zone_id(
            self.members[0].market_id,
            self.zone_type,
            tuple(item.reaction_id for item in self.members),
        )


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _reaction_id(
    *, market_id: str, zone_type: ZoneType, pivot: Bar, confirmed_bar_index: int
) -> str:
    return _digest(
        market_id
        + zone_type.value
        + pivot.candle_id
        + str(confirmed_bar_index)
        + PARAMETER_VERSION
    )


def _zone_id(market_id: str, zone_type: ZoneType, reaction_ids: tuple[str, ...]) -> str:
    return _digest(
        market_id + zone_type.value + "".join(sorted(reaction_ids)) + PARAMETER_VERSION
    )


def _qualified_reactions(bars: tuple[Bar, ...]) -> tuple[Reaction, ...]:
    atr_values = wilder_atr14_series(bars)
    lookback_start = max(1, len(bars) - ZONE_LOOKBACK_15M)
    candidates: list[Reaction] = []
    pivot_groups = (
        (ZoneType.HIGH, causal_pivot_high_indices(bars)),
        (ZoneType.LOW, causal_pivot_low_indices(bars)),
    )
    for zone_type, pivot_indices in pivot_groups:
        typed: list[Reaction] = []
        for pivot_index in pivot_indices:
            if pivot_index < lookback_start:
                continue
            confirmation_index = pivot_index + 1
            a15_reaction = atr_values[confirmation_index]
            if a15_reaction is None:
                continue
            pivot = bars[pivot_index]
            qualifying_index: int | None = None
            subsequent = range(pivot_index + 1, min(pivot_index + 5, len(bars)))
            for index in subsequent:
                if zone_type is ZoneType.HIGH:
                    move_away = pivot.high - min(
                        item.low for item in bars[pivot_index + 1 : index + 1]
                    )
                else:
                    move_away = max(
                        item.high for item in bars[pivot_index + 1 : index + 1]
                    ) - pivot.low
                if move_away >= Decimal("0.50") * a15_reaction:
                    qualifying_index = index
                    break
            if qualifying_index is None:
                continue
            price = pivot.high if zone_type is ZoneType.HIGH else pivot.low
            reaction = Reaction(
                reaction_id=_reaction_id(
                    market_id=pivot.market_id,
                    zone_type=zone_type,
                    pivot=pivot,
                    confirmed_bar_index=qualifying_index,
                ),
                market_id=pivot.market_id,
                zone_type=zone_type,
                pivot_bar_index=pivot_index,
                confirmed_bar_index=qualifying_index,
                price=price,
                a15_reaction=a15_reaction,
            )
            if typed and pivot_index - typed[-1].pivot_bar_index < 2:
                current = typed[-1]
                better_price = (
                    price > current.price
                    if zone_type is ZoneType.HIGH
                    else price < current.price
                )
                if better_price:
                    typed[-1] = reaction
                # Equal price retains the earlier confirmed reaction.
                continue
            typed.append(reaction)
        candidates.extend(typed)
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.confirmed_bar_index,
                item.zone_type.value,
                item.pivot_bar_index,
                item.reaction_id,
            ),
        )
    )


def _clusters(reactions: tuple[Reaction, ...], minimum_tick: Decimal) -> tuple[_Cluster, ...]:
    clusters: list[_Cluster] = []
    for reaction in reactions:
        eligible: list[tuple[Decimal, int, str, _Cluster]] = []
        for cluster in clusters:
            if cluster.zone_type is not reaction.zone_type:
                continue
            distance = abs(reaction.price - cluster.center)
            threshold = max(Decimal("0.20") * reaction.a15_reaction, 2 * minimum_tick)
            if distance <= threshold:
                eligible.append(
                    (distance, cluster.created_bar_index, cluster.identity, cluster)
                )
        if eligible:
            eligible.sort(key=lambda item: (item[0], item[1], item[2]))
            eligible[0][3].members.append(reaction)
        else:
            clusters.append(
                _Cluster(reaction.zone_type, [reaction], reaction.confirmed_bar_index)
            )
    return tuple(clusters)


def _distance_to_zone(value: Decimal, zone: ZoneSnapshot) -> Decimal:
    if zone.contains(value):
        return Decimal()
    return min(abs(value - zone.low), abs(value - zone.high))


def _overlap_reaches_threshold(left: ZoneSnapshot, right: ZoneSnapshot) -> bool:
    overlap = min(left.high, right.high) - max(left.low, right.low)
    if overlap <= 0:
        return False
    return overlap >= Decimal("0.50") * min(left.width, right.width)


def _suppress_overlaps(
    zones: tuple[ZoneSnapshot, ...], current_close: Decimal
) -> tuple[ZoneSnapshot, ...]:
    output = list(zones)
    for zone_type in (ZoneType.HIGH, ZoneType.LOW):
        candidates = [
            item
            for item in output
            if item.zone_type is zone_type
            and item.active_for_new_event
            and item.quality.rank >= ZoneQuality.ZQ2.rank
        ]
        ordered = sorted(
            candidates,
            key=lambda item: (
                -item.quality.rank,
                -item.reaction_count,
                -item.latest_reaction_bar_index,
                _distance_to_zone(current_close, item),
                item.zone_id,
            ),
        )
        winners: list[ZoneSnapshot] = []
        suppressed_ids: set[str] = set()
        for candidate in ordered:
            if any(_overlap_reaches_threshold(candidate, winner) for winner in winners):
                suppressed_ids.add(candidate.zone_id)
            else:
                winners.append(candidate)
        output = [
            replace(item, suppressed=True) if item.zone_id in suppressed_ids else item
            for item in output
        ]
    return tuple(sorted(output, key=lambda item: (item.zone_type.value, item.center, item.zone_id)))


def build_zone_book(bars_15m: tuple[Bar, ...], *, minimum_tick: Decimal) -> ZoneBook:
    validate_series(bars_15m, interval="15m")
    if not minimum_tick.is_finite() or minimum_tick <= 0:
        raise KernelInputError("minimum tick must be positive and finite")
    atr_values = wilder_atr14_series(bars_15m)
    a15_current = atr_values[-1]
    if a15_current is None:
        raise KernelInputError("zone engine requires current A15")
    reactions = _qualified_reactions(bars_15m)
    clusters = _clusters(reactions, minimum_tick)
    evaluation_index = len(bars_15m) - 1
    zones: list[ZoneSnapshot] = []
    for cluster in clusters:
        prices = tuple(item.price for item in cluster.members)
        center = median(prices)
        mad = median(abs(item - center) for item in prices)
        minimum_width = Decimal("0.15") * a15_current
        maximum_width = Decimal("0.40") * a15_current
        raw_half_width = max(Decimal("1.5") * mad, minimum_width)
        half_width = min(max(raw_half_width, minimum_width), maximum_width)
        latest = max(item.confirmed_bar_index for item in cluster.members)
        count = len(cluster.members)
        quality = (
            ZoneQuality.ZQ3
            if count >= 3
            else ZoneQuality.ZQ2
            if count >= 2
            else ZoneQuality.ZQ1
        )
        age = evaluation_index - latest
        active = quality.rank >= ZoneQuality.ZQ2.rank and age <= 24
        ids = tuple(item.reaction_id for item in cluster.members)
        zones.append(
            ZoneSnapshot(
                zone_id=_zone_id(bars_15m[0].market_id, cluster.zone_type, ids),
                market_id=bars_15m[0].market_id,
                zone_type=cluster.zone_type,
                center=center,
                low=center - half_width,
                high=center + half_width,
                half_width=half_width,
                quality=quality,
                reaction_count=count,
                latest_reaction_bar_index=latest,
                member_reaction_ids=ids,
                active_for_new_event=active,
            )
        )
    selected = _suppress_overlaps(tuple(zones), bars_15m[-1].close)
    eligible = [
        item
        for item in selected
        if item.active_for_new_event
        and not item.suppressed
        and item.quality.rank >= ZoneQuality.ZQ2.rank
    ]
    supports = [
        item
        for item in eligible
        if item.zone_type is ZoneType.LOW and item.low <= bars_15m[-1].close
    ]
    resistances = [
        item
        for item in eligible
        if item.zone_type is ZoneType.HIGH and item.high >= bars_15m[-1].close
    ]
    active_support = min(
        supports,
        key=lambda item: (_distance_to_zone(bars_15m[-1].close, item), item.zone_id),
        default=None,
    )
    active_resistance = min(
        resistances,
        key=lambda item: (_distance_to_zone(bars_15m[-1].close, item), item.zone_id),
        default=None,
    )
    return ZoneBook(selected, reactions, active_support, active_resistance)
