"""Bounded L1/flow measurements; depth is a distinct, optional native snapshot family."""

import json
from decimal import Decimal, localcontext

from .alignment import eligible, mid, result
from .contracts import Availability, FeatureObservation, FeatureSpec, Observation


def window_rows(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
) -> tuple[tuple[Observation, ...], Availability]:
    spec = FeatureSpec.model_validate_json(spec.model_dump_json())
    prefix = tuple(
        r
        for r in rows
        if r.ts_event <= t and r.known_at <= knowledge and r.kind in spec.required_kinds
    )
    if not prefix:
        return (), "MISSING_SOURCE"
    if len({(r.evidence.provider, r.evidence.instrument) for r in prefix}) != 1:
        raise ValueError("feature window must be one instrument/stream")
    if any(r.evidence.coverage_start > t - max(spec.window_ns, spec.warmup_ns) for r in prefix):
        return (), "WARMUP_INCOMPLETE"
    selected = tuple(
        sorted(
            (r for r in prefix if t - spec.window_ns <= r.ts_event <= t),
            key=lambda r: (r.ts_event, r.ordinal),
        )
    )
    if not selected:
        return (), "MISSING_SOURCE"
    if len({r.continuity_epoch for r in selected}) != 1:
        return selected, "GAPPED"
    for row in selected:
        state = eligible(row, spec, row.ts_event, knowledge)
        if state != "AVAILABLE":
            return selected, state
    # A late unhealthy observation cannot be bypassed by ordering it earlier by event time.
    if (
        eligible(max(prefix, key=lambda r: (r.known_at, r.ordinal)), spec, t, knowledge)
        != "AVAILABLE"
    ):
        return selected, eligible(
            max(prefix, key=lambda r: (r.known_at, r.ordinal)), spec, t, knowledge
        )
    return selected, "AVAILABLE"


def bbo_features(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
) -> FeatureObservation:
    if spec.family != "BBO_TRADES" or spec.required_kinds != ("BBO",):
        raise ValueError("L1 feature identity mismatch")
    selected, state = window_rows(rows, spec, t, knowledge)
    if state != "AVAILABLE":
        return result(spec, t, knowledge, selected, {}, state)
    if len(selected) < 2:
        return result(spec, t, knowledge, selected, {}, "WARMUP_INCOMPLETE")
    with localcontext() as ctx:
        ctx.prec = 80
        ofi = Decimal(0)
        previous = selected[0]
        for row in selected[1:]:
            b, a, qb, qa = (row.number(k) for k in ("bid", "ask", "bid_size", "ask_size"))
            pb, pa, pqb, pqa = (previous.number(k) for k in ("bid", "ask", "bid_size", "ask_size"))
            if min(qb, qa, pqb, pqa) < 0 or not 0 < b <= a or not 0 < pb <= pa:
                return result(spec, t, knowledge, selected, {}, "INVALID_EVIDENCE")
            ofi += int(b >= pb) * qb - int(b <= pb) * pqb
            ofi += -int(a <= pa) * qa + int(a >= pa) * pqa
            previous = row
        b, a, qb, qa = (previous.number(k) for k in ("bid", "ask", "bid_size", "ask_size"))
        if qb + qa == 0:
            return result(
                spec, t, knowledge, selected, {}, "MISSING_SOURCE", reasons=("ZERO_BBO_SIZE",)
            )
        m = mid(previous)
        microprice = (a * qb + b * qa) / (qb + qa)
        return result(
            spec,
            t,
            knowledge,
            selected,
            {
                "imbalance": (qb - qa) / (qb + qa),
                "microprice": microprice,
                "microprice_minus_mid": microprice - m,
                "ofi": ofi,
                "ofi_normalized": ofi / (qb + qa),
                "spread": a - b,
                "spread_bps": (a - b) / m * 10_000,
                "quote_age_ns": Decimal(t - previous.ts_event),
            },
        )


def trade_features(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
) -> FeatureObservation:
    selected, state = window_rows(rows, spec, t, knowledge)
    if spec.family != "BBO_TRADES" or spec.required_kinds != ("TRADE",):
        raise ValueError("trade feature identity mismatch")
    if state != "AVAILABLE":
        return result(spec, t, knowledge, selected, {}, state)
    seen: set[str] = set()
    signed = total = Decimal(0)
    with localcontext() as ctx:
        ctx.prec = 80
        for row in selected:
            identity = row.evidence.source_hash
            if identity in seen:
                continue
            seen.add(identity)
            side = dict(row.values).get("aggressor")
            if side not in {"BUY", "SELL", "BUYER", "SELLER"}:
                return result(
                    spec,
                    t,
                    knowledge,
                    selected,
                    {},
                    "MISSING_SOURCE",
                    reasons=("AGGRESSOR_UNKNOWN",),
                )
            size = row.number("size")
            if size < 0:
                return result(spec, t, knowledge, selected, {}, "INVALID_EVIDENCE")
            signed += size if side in {"BUY", "BUYER"} else -size
            total += size
        if total == 0:
            return result(
                spec, t, knowledge, selected, {}, "MISSING_SOURCE", reasons=("ZERO_TRADE_VOLUME",)
            )
        response = (selected[-1].number("price") / selected[0].number("price") - 1) * 10_000
        return result(
            spec,
            t,
            knowledge,
            selected,
            {
                "signed_flow": signed,
                "aggressor_imbalance": signed / total,
                "price_response_bps": response,
            },
        )


def depth_features(
    row: Observation | None,
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    size: Decimal,
) -> FeatureObservation:
    if spec.family != "DEPTH10_OR_L2" or size <= 0:
        raise ValueError("distinct depth identity/positive size required")
    if row is None or row.kind != "DEPTH":
        return result(spec, t, knowledge, (), {}, "DEPTH_UNAVAILABLE")
    state = eligible(row, spec, t, knowledge)
    if state != "AVAILABLE":
        return result(spec, t, knowledge, (row,), {}, state)
    raw = json.loads(dict(row.values)["native_depth"])
    if raw.get("semantics", "SNAPSHOT") != "SNAPSHOT":
        return result(
            spec,
            t,
            knowledge,
            (row,),
            {},
            "DEPTH_UNAVAILABLE",
            reasons=("DELTA_RECONSTRUCTION_NOT_OWNED_HERE",),
        )
    levels = raw.get("levels")
    if levels is None:
        levels = [
            (side, p, q)
            for side, key in (("BUY", "bids"), ("SELL", "asks"))
            for p, q in raw.get(key, [])
        ]
    n = int(dict(spec.parameters)["top_n"])
    if not 1 <= n <= 10:
        raise ValueError("bounded top-N depth required")
    with localcontext() as ctx:
        ctx.prec = 80
        values = {}
        totals = []
        for side, name in (("BUY", "bid"), ("SELL", "ask")):
            book = [(Decimal(p), Decimal(q)) for s, p, q in levels if s == side][:n]
            if not book or any(p <= 0 or q < 0 for p, q in book):
                return result(spec, t, knowledge, (row,), {}, "DEPTH_UNAVAILABLE")
            if book != sorted(book, reverse=side == "BUY"):
                return result(spec, t, knowledge, (row,), {}, "INVALID_EVIDENCE")
            totals.append(sum((q for _, q in book), Decimal(0)))
            remaining, cash = size, Decimal(0)
            for price, quantity in book:
                used = min(remaining, quantity)
                cash += price * used
                remaining -= used
            if remaining:
                return result(
                    spec,
                    t,
                    knowledge,
                    (row,),
                    {},
                    "DEPTH_UNAVAILABLE",
                    reasons=("INSUFFICIENT_RETAINED_CAPACITY",),
                )
            values[name + "_vwap"] = cash / size
        if sum(totals) == 0:
            return result(spec, t, knowledge, (row,), {}, "DEPTH_UNAVAILABLE")
        values["top_n_imbalance"] = (totals[0] - totals[1]) / sum(totals)
        return result(spec, t, knowledge, (row,), values)
