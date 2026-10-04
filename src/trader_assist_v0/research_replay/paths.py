"""Matured forward measurement is separated from immutable policy prefixes."""

from decimal import Decimal, localcontext

from .contracts import (
    Attempt,
    CashFlow,
    DecisionSnapshot,
    Fill,
    Opportunity,
    PathResult,
    checked_observation,
    decimal80,
    digest,
)
from .contracts import (
    _ObservationFields as Observation,
)


@decimal80
def measure_path(
    snapshot: DecisionSnapshot,
    opportunity: Opportunity,
    rows: tuple[Observation, ...],
    *,
    as_of: int,
    fill: Fill | None = None,
) -> PathResult:
    rows = tuple(checked_observation(r) for r in rows)
    snapshot = DecisionSnapshot.model_validate_json(snapshot.model_dump_json())
    opportunity = Opportunity.model_validate_json(opportunity.model_dump_json())
    if fill:
        fill = Fill.model_validate_json(fill.model_dump_json())
    if snapshot.opportunity_hash != opportunity.record_hash:
        raise ValueError("forward path binds wrong decision")
    start = fill.ts if fill else snapshot.decision_ns
    entry = fill.price if fill else opportunity.entry
    end = snapshot.horizon_end
    if fill and fill.ts < snapshot.decision_ns:
        raise ValueError("counterfactual fill cannot predate reference decision")
    selected = tuple(
        sorted(
            (
                checked_observation(r)
                for r in rows
                if start <= r.ts_event <= min(end, as_of) and r.known_at <= as_of
            ),
            key=lambda r: (r.ts_event, r.ordinal),
        )
    )
    selected = tuple(r for r in selected if r.evidence.expression == opportunity.market_id)
    reasons: list[str] = []
    ambiguous = bounds = False
    primary = "NO_HIT"
    market: list[tuple[int, Decimal, Decimal]] = []
    executable: list[tuple[int, Decimal, Decimal]] = []
    first_up = first_down = recovered = None
    first_stop = first_target = None
    side = Decimal(1) if opportunity.side == "LONG" else Decimal(-1)
    if len({r.continuity_epoch for r in selected if r.evidence.owner == "HL_E4"}) > 1:
        reasons.append("CONTINUITY_BREAK")
    truth = tuple(r for r in selected if r.evidence.owner == "HL_E4")
    if truth and min(r.evidence.coverage_start for r in truth) > start:
        reasons.append("CENSORED_PREFIX")
    groups: dict[int, list[Observation]] = {}
    for r in selected:
        groups.setdefault(r.ts_event, []).append(r)
    for ts, group in groups.items():
        stop_hit = target_hit = False
        for row in group:
            if row.evidence.owner != "HL_E4":
                continue  # external references never repair exact-venue paths
            if set(row.quality) - {"COMPLETE", "AVAILABLE_VERIFIED"}:
                reasons.append("GAPPED_OR_UNAVAILABLE_PATH")
                continue
            if (
                not row.evidence.valid_from <= row.ts_event < row.evidence.valid_to
                or max(row.evidence.mapping_known_at, row.evidence.mapping_recorded_at)
                > row.known_at
            ):
                reasons.append("GAPPED_OR_UNAVAILABLE_PATH")
                continue
            if row.kind == "BBO":
                price = row.number("bid" if side > 0 else "ask")
                excursion = (price - entry) * side
                executable.append((ts, excursion, excursion))
                price = (row.number("bid") + row.number("ask")) / 2
                favorable = adverse = (price - entry) * side
            elif row.kind == "TRADE":
                price = row.number("price")
                favorable = adverse = (price - entry) * side
            elif row.kind == "BAR":
                bounds = True
                if int(dict(row.values).get("start_ns", "0")) < start:
                    ambiguous = True
                    reasons.append("PARTIAL_TRIGGER_BAR")
                    continue
                if row.bar_end is None or row.bar_end > as_of:
                    continue
                high, low = row.number("high"), row.number("low")
                favorable = ((high if side > 0 else low) - entry) * side
                adverse = ((low if side > 0 else high) - entry) * side
            else:
                continue
            market.append((ts, favorable, adverse))
            if favorable > 0 and first_up is None:
                first_up = ts
            if adverse < 0 and first_down is None:
                first_down = ts
            if first_down is not None and ts > first_down and adverse >= 0 and recovered is None:
                recovered = ts
            stop_value = excursion if row.kind == "BBO" else adverse
            target_value = excursion if row.kind == "BBO" else favorable
            stop_hit |= stop_value <= (opportunity.stop - entry) * side
            target_hit |= target_value >= (opportunity.target - entry) * side
        if stop_hit and target_hit:
            ambiguous = True
        if stop_hit and first_stop is None:
            first_stop = ts
        if target_hit and first_target is None:
            first_target = ts
        if primary == "NO_HIT" and stop_hit:
            primary = "STOP_FIRST"
        elif primary == "NO_HIT" and target_hit:
            primary = "TARGET_FIRST"
    if not market:
        reasons.append("MISSING_FORWARD_PATH")
    if not executable:
        reasons.append("EXECUTABLE_PATH_MISSING")
    if as_of < end or not truth or min(r.evidence.coverage_end for r in truth) <= end:
        reasons.append("CENSORED_HORIZON")
    if ambiguous:
        reasons.append("AMBIGUOUS_ORDER")

    def extrema(
        values: list[tuple[int, Decimal, Decimal]],
    ) -> tuple[Decimal | None, Decimal | None]:
        if not values:
            return None, None
        return max(Decimal(0), max(v[1] for v in values)), min(
            Decimal(0), min(v[2] for v in values)
        )

    mfe, mae = extrema(market)
    emfe, emae = extrema(executable)
    invalid = "GAPPED_OR_UNAVAILABLE_PATH" in reasons or "CONTINUITY_BREAK" in reasons
    if invalid:
        mfe = mae = emfe = emae = None
        first_up = first_down = recovered = None
        first_stop = first_target = None
    return PathResult.create(
        version="B_PATH_V1",
        snapshot_hash=snapshot.record_hash,
        status="NOT_RECONSTRUCTABLE"
        if not market or invalid
        else "PARTIAL"
        if reasons
        else "RECONSTRUCTABLE",
        reasons=tuple(sorted(set(reasons))),
        input_hashes=tuple(r.record_hash for r in truth),
        market_mfe=mfe,
        market_mae=mae,
        exec_mfe=emfe,
        exec_mae=emae,
        first_favorable_ns=first_up,
        first_adverse_ns=first_down,
        time_to_mfe_ns=None
        if mfe is None
        else next(ts - start for ts, f, _ in market if f == mfe)
        if any(f == mfe for _, f, _ in market)
        else None,
        time_to_mae_ns=None
        if mae is None
        else next(ts - start for ts, _, a in market if a == mae)
        if any(a == mae for _, _, a in market)
        else None,
        recovery_ns=recovered,
        same_bar_ambiguous=ambiguous,
        primary=primary if market and not invalid else "UNKNOWN",
        censored="CENSORED_HORIZON" in reasons,
        basis="FILL" if fill else "TRIGGER",
        bounds_only=bounds,
        first_stop_ns=first_stop,
        first_target_ns=first_target,
    )


def thesis_state(
    attempts: tuple[Attempt, ...],
    *,
    thesis_id: str,
    at: int,
    invalidation_ns: int | None,
    max_attempts: int,
) -> str:
    for index, attempt in enumerate(attempts, 1):
        attempt = Attempt.model_validate_json(attempt.model_dump_json())
        if attempt.thesis_id != thesis_id or attempt.index != index:
            raise ValueError("attempt lineage/index mismatch")
        if invalidation_ns and attempt.trigger_ns >= invalidation_ns:
            raise ValueError("attempt triggered after Thesis invalidation")
    if invalidation_ns is not None and at >= invalidation_ns:
        return "THESIS_INVALIDATED"
    if len(attempts) > max_attempts:
        raise ValueError("attempt budget exceeded")
    if not attempts:
        return "WAITING_FOR_ENTRY"
    if attempts[-1].state == "SCRATCHED":
        return "WAITING_FOR_REENTRY" if len(attempts) < max_attempts else "COMPLETE"
    return attempts[-1].state


def net_cash(
    fills: tuple[Fill, ...],
    cashflows: tuple[CashFlow, ...],
    *,
    funding_complete: bool,
    funding_applicable: bool,
) -> Decimal | None:
    if funding_applicable and not funding_complete:
        return None
    with localcontext() as ctx:
        ctx.prec = 80
        result = sum(
            (
                (Decimal(-1) if f.direction == "BUY" else Decimal(1)) * f.price * f.size - f.fee
                for f in fills
            ),
            Decimal(0),
        )
        return result + sum((c.amount for c in cashflows), Decimal(0))


@decimal80
def funding_settlement(
    fills: tuple[Fill, ...],
    rate: Observation,
    mark: Observation,
    *,
    as_of: int,
    profile_hash: str,
) -> CashFlow:
    """Signed native-position cash flow from retained exact-venue public settlement evidence."""
    rate = checked_observation(rate)
    mark = checked_observation(mark)
    if (
        rate.evidence.owner != "HL_E4"
        or mark.evidence.owner != "HL_E4"
        or (rate.evidence.expression != mark.evidence.expression)
    ):
        raise ValueError("external funding cannot replace exact-venue settlement")
    if rate.kind != "CONTEXT" or dict(rate.values).get("field") != "FUNDING":
        raise ValueError("typed funding settlement source required")
    settlement = int(dict(rate.values)["settlement_ns"])
    if max(rate.known_at, mark.known_at, settlement) > as_of or mark.ts_event > settlement:
        raise ValueError("funding settlement has not matured")
    if dict(rate.values).get("unit") != "FRACTION_PER_SETTLEMENT":
        raise ValueError("registered funding units required")
    if set(rate.quality + mark.quality) - {"COMPLETE", "AVAILABLE_VERIFIED"}:
        raise ValueError("incomplete settlement evidence")
    price = (
        (mark.number("bid") + mark.number("ask")) / 2
        if mark.kind == "BBO"
        else mark.number("value")
    )
    position = sum(
        (
            (Decimal(1) if f.direction == "BUY" else Decimal(-1)) * f.size
            for f in fills
            if f.ts <= settlement
        ),
        Decimal(0),
    )
    return CashFlow(
        ts=settlement,
        amount=-position * price * rate.number("value"),
        kind="FUNDING",
        source_hash=digest(
            "B_FUNDING_SETTLEMENT", (rate.record_hash, mark.record_hash, profile_hash)
        ),
        input_hashes=(rate.record_hash, mark.record_hash),
    )
