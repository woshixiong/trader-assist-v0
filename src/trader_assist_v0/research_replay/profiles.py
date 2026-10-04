"""Trade-volume profiles and causal auction candidate state, not a Formal Setup."""

from decimal import ROUND_FLOOR, Decimal, localcontext
from typing import Literal

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import FiniteDecimal
from trader_assist_v0.research_data.contracts import BoundRecord

from .alignment import result
from .contracts import FeatureObservation, FeatureSpec, Observation
from .microstructure import window_rows


def volume_profile(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    previous: FeatureObservation | None = None,
) -> FeatureObservation:
    if spec.family != "BBO_TRADES" or spec.required_kinds != ("TRADE",):
        raise ValueError("profile must derive from retained trades")
    selected, status = window_rows(rows, spec, t, knowledge)
    if status != "AVAILABLE":
        return result(spec, t, knowledge, selected, {}, status)
    parameters = dict(spec.parameters)
    width, origin, fraction = (
        Decimal(parameters[k]) for k in ("bin_width", "origin", "value_fraction")
    )
    tick = Decimal(parameters["price_tick"])
    if width <= 0 or tick <= 0 or width % tick or not 0 < fraction <= 1:
        raise ValueError("tick-aligned width and bounded value fraction required")
    radius = int(parameters["node_radius"])
    if not 1 <= radius <= 100:
        raise ValueError("bounded node neighborhood required")
    bins: dict[int, Decimal] = {}
    facts: set[str] = set()
    with localcontext() as ctx:
        ctx.prec = 80
        for row in selected:
            if row.evidence.source_hash in facts:
                continue
            facts.add(row.evidence.source_hash)
            price, size = row.number("price"), row.number("size")
            if price <= 0 or size < 0:
                return result(spec, t, knowledge, selected, {}, "INVALID_EVIDENCE")
            index = int(((price - origin) / width).to_integral_value(rounding=ROUND_FLOOR))
            bins[index] = bins.get(index, Decimal(0)) + size
        total = sum(bins.values(), Decimal(0))
        if not total:
            return result(
                spec, t, knowledge, selected, {}, "MISSING_SOURCE", reasons=("ZERO_PROFILE_VOLUME",)
            )
        poc = min(bins, key=lambda i: (-bins[i], i))
        low = high = poc
        volume = bins[poc]
        # Only observed adjacent bins can extend a value area: do not invent gap volume.
        while volume < total * fraction:
            choices = [i for i in (low - 1, high + 1) if i in bins]
            if not choices:
                return result(
                    spec,
                    t,
                    knowledge,
                    selected,
                    {},
                    "GAPPED",
                    reasons=("NONCONTIGUOUS_VALUE_AREA",),
                )
            index = min(choices, key=lambda i: (-bins[i], i))
            volume += bins[index]
            low, high = min(low, index), max(high, index)
        hvn, lvn = [], []
        for i, v in sorted(bins.items()):
            neighbors = [bins[j] for j in range(i - radius, i + radius + 1) if j != i and j in bins]
            if neighbors and all(v > x for x in neighbors):
                hvn.append(i)
            if len(neighbors) == 2 * radius and all(v < x for x in neighbors):
                lvn.append(i)
        val, vah = origin + low * width, origin + (high + 1) * width
        values: dict[str, Decimal] = {
            "poc": origin + poc * width,
            "val": val,
            "vah": vah,
            "width": vah - val,
            "concentration": sum(((v / total) ** 2 for v in bins.values()), Decimal(0)),
            "hvn_count": Decimal(len(hvn)),
            "lvn_count": Decimal(len(lvn)),
            "outside_balance_volume": total - volume,
        }
        values.update({f"hvn_{i}": origin + b * width for i, b in enumerate(hvn)})
        values.update({f"lvn_{i}": origin + b * width for i, b in enumerate(lvn)})
        if previous:
            previous = FeatureObservation.model_validate_json(previous.model_dump_json())
            if previous.spec_hash != spec.record_hash or previous.event_cutoff >= t:
                raise ValueError("migration requires earlier same-version profile")
            if previous.status == "AVAILABLE":
                values["value_migration"] = values["poc"] - Decimal(dict(previous.values)["poc"])
        return result(
            spec,
            t,
            knowledge,
            selected,
            values,
            ancestors=(previous.record_hash,) if previous else (),
        )


class AuctionConfig(BoundRecord):
    balance_low: FiniteDecimal
    balance_high: FiniteDecimal
    frozen_at: int = Field(gt=0)
    boundary_source_hash: str = Field(min_length=64, max_length=64)
    max_response_bps: FiniteDecimal = Field(ge=0)
    acceptance_dwell_ns: int = Field(gt=0)
    require_second_attempt: bool

    @model_validator(mode="after")
    def ordered_balance(self) -> "AuctionConfig":
        if not 0 < self.balance_low < self.balance_high:
            raise ValueError("invalid frozen balance")
        return self


class AuctionState(BoundRecord):
    config_hash: str
    state: Literal[
        "BALANCE", "EDGE_TEST", "FAILED_AUCTION", "ACCEPTED_BREAK", "REBALANCE", "NEW_BALANCE"
    ]
    entered_at: int
    confirmed_at: int | None
    tests: int = Field(ge=0)
    last_ts: int


def auction_step(
    config: AuctionConfig,
    state: AuctionState | None,
    *,
    ts: int,
    price: Decimal,
    opposing_flow: bool,
    response_bps: Decimal,
) -> AuctionState:
    config = AuctionConfig.model_validate_json(config.model_dump_json())
    if ts < config.frozen_at or not price.is_finite() or price <= 0:
        raise ValueError("auction observation precedes frozen balance")
    if state:
        state = AuctionState.model_validate_json(state.model_dump_json())
        if state.config_hash != config.record_hash or ts <= state.last_ts:
            raise ValueError("auction boundary/order identity changed")
    current = state.state if state else "BALANCE"
    entered = state.entered_at if state else ts
    tests = state.tests if state else 0
    confirmed = state.confirmed_at if state else None
    outside = price < config.balance_low or price > config.balance_high
    if current in {"BALANCE", "REBALANCE"} and outside:
        current, entered, tests = "EDGE_TEST", ts, tests + 1
    elif current == "EDGE_TEST":
        if outside and ts - entered >= config.acceptance_dwell_ns:
            current, confirmed = "ACCEPTED_BREAK", ts
        elif not outside:
            failed = opposing_flow and abs(response_bps) <= config.max_response_bps
            if failed and (tests >= 2 or not config.require_second_attempt):
                current, confirmed = "FAILED_AUCTION", ts
            else:
                current = "BALANCE"
    elif current == "FAILED_AUCTION" and not outside:
        current = "REBALANCE"
    elif current == "ACCEPTED_BREAK":
        current = "NEW_BALANCE"
    return AuctionState.create(
        version="B_AUCTION_V1",
        config_hash=config.record_hash,
        state=current,
        entered_at=entered,
        confirmed_at=confirmed,
        tests=tests,
        last_ts=ts,
    )
