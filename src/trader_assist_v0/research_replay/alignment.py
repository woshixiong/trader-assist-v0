"""Backward joins and prefix measurements; future propagation is outcome-only."""

from decimal import Decimal, localcontext

from .contracts import (
    Availability,
    FeatureObservation,
    FeatureSpec,
    PropagationLabel,
    checked_observation,
    decimal80,
    wire,
)
from .contracts import (
    _ObservationFields as Observation,
)

GOOD = frozenset({"AVAILABLE_VERIFIED", "COMPLETE"})


def eligible(row: Observation, spec: FeatureSpec, t: int, knowledge: int) -> Availability:
    row = checked_observation(row)
    ref = row.evidence
    if row.ts_event > t or row.known_at > knowledge or (row.bar_end and row.bar_end > t):
        return "MISSING_SOURCE"
    if (
        not ref.valid_from <= row.ts_event < ref.valid_to
        or max(ref.mapping_known_at, ref.mapping_recorded_at) > knowledge
    ):
        return "MAPPING_UNAVAILABLE"
    clock = row.clock(spec.clock)
    if clock is None or clock > (t if spec.clock == "EVENT" else knowledge):
        return "MISSING_SOURCE"
    if row.ts_receive is not None and row.ts_receive < row.ts_event:
        return "CLOCK_SKEW"
    if row.known_at < row.ts_event or (
        row.known_at - row.ts_event > spec.skew_ns
        and spec.availability_claim == "ORIGINAL_RETAINED"
    ):
        return "CLOCK_SKEW"
    flags = set(row.quality) - GOOD
    for flag, status in (
        ("INVALID_EVIDENCE", "INVALID_EVIDENCE"),
        ("CONFLICTED", "AMBIGUOUS"),
        ("GAP", "GAPPED"),
        ("GAPPED", "GAPPED"),
        ("STALE", "STALE"),
        ("CONTINUITY_UNKNOWN", "CONTINUITY_UNKNOWN"),
    ):
        if flag in flags:
            return status  # type: ignore[return-value]
    if flags:
        return "MISSING_SOURCE"
    if t - row.ts_event > spec.stale_ns:
        return "STALE"
    return "AVAILABLE"


def backward(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    *,
    provider: str,
    kind: str,
    expression: str,
) -> tuple[Observation | None, Availability]:
    spec = FeatureSpec.model_validate_json(spec.model_dump_json())
    prefix = tuple(
        r
        for r in rows
        if r.evidence.provider == provider
        and r.kind == kind
        and r.evidence.expression == expression
        and r.ts_event <= t
        and r.known_at <= knowledge
        and (r.bar_end is None or r.bar_end <= t)
    )
    if not prefix:
        return None, "MISSING_SOURCE"
    # Latest knowledge of a gap may never be bypassed by an older healthy quote.
    latest_knowledge = max(prefix, key=lambda r: (r.known_at, r.ordinal))
    if set(latest_knowledge.quality) - GOOD:
        return None, eligible(latest_knowledge, spec, t, knowledge)
    clocked = tuple(r for r in prefix if r.clock(spec.clock) is not None)
    if not clocked:
        return None, "MISSING_SOURCE"
    latest = max(r.clock(spec.clock) or 0 for r in clocked)
    tied = tuple(r for r in clocked if r.clock(spec.clock) == latest)
    if len({(r.values, r.continuity_epoch) for r in tied}) > 1:
        return None, "AMBIGUOUS"
    row = max(tied, key=lambda r: r.ordinal)
    state = eligible(row, spec, t, knowledge)
    return (row if state == "AVAILABLE" else None), state


def result(
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    rows: tuple[Observation, ...],
    values: dict[str, Decimal],
    status: Availability = "AVAILABLE",
    *,
    reasons: tuple[str, ...] = (),
    retrospective: bool = False,
    ancestors: tuple[str, ...] = (),
) -> FeatureObservation:
    return FeatureObservation.create(
        version="B_FEATURE_V1",
        spec_hash=spec.record_hash,
        event_cutoff=t,
        knowledge_cutoff=knowledge,
        input_hashes=tuple(r.record_hash for r in rows),
        mapping_hashes=tuple(r.evidence.interval_hash for r in rows),
        source_modes=tuple(r.evidence.source_mode for r in rows),
        values=tuple(sorted((k, wire(v)) for k, v in values.items()))
        if status == "AVAILABLE"
        else (),
        status=status,
        reasons=reasons or (() if status == "AVAILABLE" else (status,)),
        claim="RETROSPECTIVE_EVENT_TIME"
        if retrospective or spec.availability_claim == "RETROSPECTIVE_EVENT_TIME"
        else "ORIGINAL_AVAILABILITY",
        family=spec.family,
        expression=rows[0].evidence.expression if rows else "UNAVAILABLE",
        unit=spec.unit,
        clock=spec.clock,
        coverage=(min(r.ts_event for r in rows), max(r.ts_event for r in rows)) if rows else None,
        ancestor_features=ancestors,
    )


def mid(row: Observation) -> Decimal:
    row = checked_observation(row)
    bid, ask = row.number("bid"), row.number("ask")
    if not 0 < bid <= ask:
        raise ValueError("invalid BBO")
    return (bid + ask) / 2


def cross_venue(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    expression: str,
    hl_provider: str = "NAUTILUS_HYPERLIQUID",
) -> FeatureObservation:
    hl, state = backward(
        rows, spec, t, knowledge, provider=hl_provider, kind="BBO", expression=expression
    )
    if hl is None or hl.evidence.owner != "HL_E4":
        return result(spec, t, knowledge, (), {}, state, reasons=("HL_TRUTH_UNAVAILABLE",))
    used = [hl]
    values = {"expected": Decimal(2)}
    available = agreeing = stale = missing = 0
    basis: dict[str, Decimal] = {}
    component_reasons: list[str] = []
    with localcontext() as ctx:
        ctx.prec = 80
        for provider in ("BINANCE", "OKX"):
            row, quality = backward(
                rows, spec, t, knowledge, provider=provider, kind="BBO", expression=expression
            )
            if row is None:
                component_reasons.append(f"{provider}_{quality}")
                stale += quality == "STALE"
                missing += quality != "STALE"
                continue
            if row.evidence.owner != "EXTERNAL_REFERENCE" or (
                row.evidence.price_unit != hl.evidence.price_unit
            ):
                missing += 1
                component_reasons.append(f"{provider}_INCOMPARABLE_UNITS_OR_OWNER")
                continue
            used.append(row)
            basis[provider] = (mid(row) / mid(hl) - 1) * 10_000
            values[provider + "_basis_bps"] = basis[provider]
            values[provider + "_age_ns"] = Decimal(t - row.ts_event)
            available += 1
            agreeing += abs(basis[provider]) <= Decimal(dict(spec.parameters)["confirmation_bps"])
        if len(basis) == 2:
            values["disagreement_bps"] = basis["BINANCE"] - basis["OKX"]
        values.update(
            eligible=Decimal(available),
            agreeing=Decimal(agreeing),
            disagreeing=Decimal(available - agreeing),
            stale=Decimal(stale),
            missing=Decimal(missing),
            confirmation_fraction=Decimal(agreeing) / 2,
        )
    return result(
        spec,
        t,
        knowledge,
        tuple(used),
        values,
        reasons=tuple(component_reasons),
    )


def lead_lag(
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    t: int,
    knowledge: int,
    expression: str,
    leader: str,
    follower: str,
    horizon_ns: int,
    lag_ns: int,
) -> FeatureObservation:
    if horizon_ns <= 0 or lag_ns < 0 or horizon_ns + lag_ns > spec.window_ns:
        raise ValueError("probe horizons must be registered inside window")
    selected: list[Observation] = []
    for provider, cutoff in (
        (leader, t - lag_ns - horizon_ns),
        (leader, t - lag_ns),
        (follower, t - horizon_ns),
        (follower, t),
    ):
        row, status = backward(
            rows, spec, cutoff, knowledge, provider=provider, kind="BBO", expression=expression
        )
        if row is None:
            return result(spec, t, knowledge, tuple(selected), {}, status)
        selected.append(row)
    if len({r.evidence.price_unit for r in selected}) != 1:
        return result(spec, t, knowledge, tuple(selected), {}, "INVALID_EVIDENCE")
    with localcontext() as ctx:
        ctx.prec = 80
        a = (mid(selected[1]) / mid(selected[0]) - 1) * 10_000
        b = (mid(selected[3]) / mid(selected[2]) - 1) * 10_000
        return result(
            spec,
            t,
            knowledge,
            tuple(selected),
            {"leader_return_bps": a, "follower_return_bps": b, "lag_ns": Decimal(lag_ns)},
        )


@decimal80
def propagation(
    impulse: Observation,
    previous: Observation,
    rows: tuple[Observation, ...],
    spec: FeatureSpec,
    *,
    follower: str,
    horizon_ns: int,
    as_of: int,
) -> PropagationLabel:
    """Forward response is released separately, never appended to the impulse prefix."""
    impulse = checked_observation(impulse)
    previous = checked_observation(previous)
    spec = FeatureSpec.model_validate_json(spec.model_dump_json())
    if horizon_ns <= 0 or horizon_ns > spec.window_ns or impulse.kind not in {"BBO", "TRADE"}:
        raise ValueError("registered bounded quote/trade impulse required")
    start = impulse.clock(spec.clock)
    if previous.evidence.provider != impulse.evidence.provider or previous.kind != impulse.kind:
        raise ValueError("impulse baseline stream mismatch")
    if (
        previous.ts_event >= impulse.ts_event
        or previous.known_at > impulse.known_at
        or (previous.evidence.expression, previous.evidence.price_unit, previous.continuity_epoch)
        != (impulse.evidence.expression, impulse.evidence.price_unit, impulse.continuity_epoch)
    ):
        raise ValueError("impulse baseline must be a causal comparable prefix")
    baseline, status = backward(
        rows,
        spec,
        impulse.ts_event,
        impulse.known_at,
        provider=follower,
        kind="BBO",
        expression=impulse.evidence.expression,
    )
    source_change = None
    if impulse.kind == "BBO":
        source_change = (mid(impulse) / mid(previous) - 1) * 10_000
    elif dict(impulse.values).get("aggressor") in {"BUY", "SELL", "BUYER", "SELLER"}:
        source_change = impulse.number("size") * (
            1 if dict(impulse.values)["aggressor"] in {"BUY", "BUYER"} else -1
        )
    unavailable = start is None or baseline is None or source_change is None
    end = (start or impulse.ts_event) + horizon_ns
    response = None
    response_value = None
    ambiguous = False
    if not unavailable and baseline is not None and start is not None:
        candidates = tuple(
            sorted(
                (
                    r
                    for r in rows
                    if r.evidence.provider == follower
                    and r.evidence.expression == impulse.evidence.expression
                    and r.kind == "BBO"
                    and r.clock(spec.clock) is not None
                    and start <= (r.clock(spec.clock) or 0) <= end
                    and r.known_at <= as_of
                ),
                key=lambda r: (r.clock(spec.clock) or 0, r.ordinal),
            )
        )
        for row in candidates:
            if (
                eligible(row, spec, row.ts_event, as_of) != "AVAILABLE"
                or row.evidence.price_unit != baseline.evidence.price_unit
            ):
                unavailable = True
                break
            change = (mid(row) / mid(baseline) - 1) * 10_000
            if abs(change) >= Decimal(dict(spec.parameters)["response_bps"]):
                if (
                    row.clock(spec.clock) == start
                    or len(
                        {
                            r.values
                            for r in candidates
                            if r.clock(spec.clock) == row.clock(spec.clock)
                        }
                    )
                    > 1
                ):
                    ambiguous = True
                response, response_value = row, change
                break
    state = (
        "UNAVAILABLE"
        if unavailable
        else "CENSORED"
        if as_of < end
        else "AMBIGUOUS"
        if ambiguous
        else "RESPONSE"
        if response
        else "NO_RESPONSE"
    )
    response_ns = response.clock(spec.clock) if response else None
    return PropagationLabel.create(
        version="B_PROPAGATION_V1",
        spec_hash=spec.record_hash,
        impulse_hash=impulse.record_hash,
        baseline_hash=baseline.record_hash if baseline else None,
        response_hash=response.record_hash if response and state != "CENSORED" else None,
        impulse_ns=start or impulse.ts_event,
        horizon_end=end,
        response_ns=response_ns if state == "RESPONSE" else None,
        elapsed_ns=response_ns - start
        if response_ns is not None and start is not None and state == "RESPONSE"
        else None,
        source_impulse=source_change,
        response_bps=response_value if state == "RESPONSE" else None,
        clock=spec.clock,
        state=state,
        reason=status if unavailable else state,
    )
