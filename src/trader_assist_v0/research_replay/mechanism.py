"""Causal composition of existing Strategy owners and a labeled bar arithmetic overlay."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Any

from trader_assist_v0.multi_asset_shadow.strategy_kernel import engine, scanner
from trader_assist_v0.multi_asset_shadow.strategy_kernel.indicators import validate_series
from trader_assist_v0.multi_asset_shadow.strategy_kernel.types import (
    Bar,
    DecisionKind,
    EventLedger,
    KernelInputError,
    ScannerState,
)
from trader_assist_v0.nautilus_pilot.strategy_package import StrategyPackageManifest

from .contracts import decimal80, digest, wire
from .dev_contracts import DevObservation
from .mechanism_contracts import (
    CHAMPION,
    CODES,
    MechanismCandidate,
    MechanismConfig,
    MechanismDecision,
    MechanismOpportunity,
    MechanismPath,
    MechanismResult,
    ModeledFill,
    checked,
)
from .policies import BASELINES, PolicyContext, evaluate

ZERO = Decimal(0)
BPS = Decimal(10000)


def admitted_rows(rows: tuple[DevObservation, ...]) -> tuple[DevObservation, ...]:
    result = tuple(checked(r, DevObservation) for r in rows)
    for r in result:
        e = r.evidence
        if e.owner != "EXTERNAL_REFERENCE" or e.source_tier not in {"R1", "R2", "R3"}:
            raise PermissionError("external R1/R2/R3 only")
        if e.exposure_state != "DEV_EXPOSED":
            raise PermissionError("DEV_EXPOSED only")
    keys = [(r.evidence.dataset_hash, r.evidence.instrument, r.kind, r.ts_event) for r in result]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate/conflicting source facts")
    return tuple(sorted(result, key=lambda r: (r.known_at, r.ts_event, r.ordinal, r.record_hash)))


def bar_view(row: DevObservation, config: MechanismConfig) -> Bar:
    values = dict(row.values)
    start = int(values["start_ns"])
    end = int(values["end_ns"])
    if row.kind != "BAR" or row.bar_end != end or end - start != config.resolution_ns:
        raise KernelInputError("finalized 5m evidence required")
    if start % config.resolution_ns or start % 1000000 or end % 1000000:
        raise KernelInputError("exact UTC-aligned ns to ms conversion required")
    if row.ts_event not in {start, end}:
        raise KernelInputError("bar event timestamp contradicts bounds")
    return Bar(
        market_id=row.evidence.expression,
        interval="5m",
        open_time_ms=start // 1000000,
        close_time_ms=end // 1000000,
        open=row.number("open"),
        high=row.number("high"),
        low=row.number("low"),
        close=row.number("close"),
        volume=row.number("volume"),
        source_identity="EXTERNAL_REFERENCE:" + row.record_hash,
    )


def healthy(row: DevObservation, at: int) -> bool:
    e = row.evidence
    return (
        row.known_at <= at
        and row.ts_event <= at
        and (row.bar_end or 0) <= at
        and e.valid_from <= row.ts_event < e.valid_to
        and max(e.mapping_known_at, e.mapping_recorded_at) <= at
        and not set(row.quality) - {"COMPLETE", "AVAILABLE_VERIFIED"}
    )


def _baseline_terms(
    bar: Bar, side: str, tick: Decimal, multiple: Decimal
) -> tuple[Decimal, Decimal]:
    stop = bar.low - tick if side == "LONG" else bar.high + tick
    sign = Decimal(1) if side == "LONG" else Decimal(-1)
    return stop, bar.close + sign * abs(bar.close - stop) * multiple


def _decision(
    code: str,
    at: int,
    prefix: tuple[str, ...],
    mode: str,
    owner: object,
    *,
    take: bool = False,
    reason: str = "ACTIVATION_PENDING",
    low: Decimal | None = None,
    high: Decimal | None = None,
    chase: Decimal | None = None,
    stop: Decimal | None = None,
    target: Decimal | None = None,
) -> MechanismDecision:
    return MechanismDecision.create(
        version="MECHANISM_DECISION_V1",
        code=code,
        at=at,
        prefix_hashes=prefix,
        participation="TAKE" if take else "WAIT",
        reason=reason,
        mode=mode,
        entry_low=low,
        entry_high=high,
        chase=chase,
        stop=stop,
        target=target,
        owner_hash=digest("MECHANISM_OWNER_RECEIPT_V1", owner),
    )


def derive_mechanism_opportunities(
    rows: tuple[DevObservation, ...], manifest: StrategyPackageManifest, config: MechanismConfig
) -> tuple[MechanismOpportunity, ...]:
    """Union raw episodes before candidate selection, retaining causal decision receipts."""
    rows = admitted_rows(rows)
    config = checked(config, MechanismConfig)
    checked(manifest, StrategyPackageManifest)
    markets = {m.expression: m for m in config.markets}
    if any(r.evidence.expression not in markets for r in rows):
        raise ValueError("evidence outside frozen universe")
    bars = tuple(r for r in rows if r.kind == "BAR")
    # Decision times are data finality AND knowledge; no late fact travels backward.
    times = sorted({max(r.bar_end or 0, r.known_at) for r in bars})
    ledgers = {m: EventLedger() for m in markets}
    scanner_states: dict[str, scanner.ScannerCandidate] = {}
    last_candle: dict[str, str] = {}
    previous_zones: dict[str, tuple[Any, ...]] = {}
    episodes: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    completed: list[dict[str, Any]] = []

    def register(
        key: tuple[str, str, str, str],
        at: int,
        row: DevObservation,
        event_id: str,
        kernel: bool,
        scans: tuple[str, ...],
        availability: str = "AVAILABLE",
    ) -> dict[str, Any]:
        existing = episodes.get(key)
        if existing is not None and (
            at < existing["expiry_ns"] or existing["market_event_id"] == event_id
        ):
            return existing
        if existing is not None:
            completed.append(existing)
        m = markets[key[0]]
        new = dict(
            market_event_id=event_id,
            thesis_id=digest("MECHANISM_THESIS_V1", event_id),
            expression=key[0],
            dataset_hash=row.evidence.dataset_hash,
            family=key[1],
            side=key[2],
            cluster_id=digest("MECHANISM_CLUSTER_V1", (m.cluster, at // config.cluster_window_ns)),
            regime=m.regime,
            start_ns=at,
            expiry_ns=at + config.expiry_ns,
            horizon_end=at + config.horizon_ns,
            kernel_event=kernel,
            availability=availability,
            reasons=() if availability == "AVAILABLE" else ("MISSING_COHORT_OR_WARMUP",),
            original_risk_cash=config.original_risk_cash,
            risk_hash=config.risk_hash,
            config_hash=config.record_hash,
            scan_hashes=scans,
            decisions=[],
        )
        episodes[key] = new
        return new

    for at in times:
        prefixes: dict[str, tuple[DevObservation, ...]] = {
            m: tuple(
                sorted(
                    (r for r in bars if r.evidence.expression == m and healthy(r, at)),
                    key=lambda r: int(dict(r.values)["start_ns"]),
                )
            )
            for m in markets
        }
        views: dict[str, tuple[Bar, ...]] = {}
        for m, prefix in prefixes.items():
            try:
                views[m] = tuple(bar_view(r, config) for r in prefix)
                # Gaps never initialize a secretly repaired series.
                validate_series(views[m], interval="5m")
            except (KernelInputError, KeyError, ValueError):
                views[m] = ()
        cohort_end = max((v[-1].close_time_ms * 1000000 for v in views.values() if v), default=0)
        complete = all(v and v[-1].close_time_ms * 1000000 == cohort_end for v in views.values())
        inputs = tuple(
            scanner.ScannerMarketInput(
                market_id=m,
                bars_5m=v,
                minimum_tick=markets[m].minimum_tick,
                current_spread_price=(v[-1].close * config.spread_bps / BPS if v else ZERO),
                liquidity_healthy=complete and config.scanner_liquidity_healthy,
            )
            for m, v in sorted(views.items())
        )
        scans = scanner.scan_cross_section(inputs)
        scan_by_market = {s.market_id: s for s in scans}
        scan_hashes = tuple(digest("MECHANISM_SCANNER_V1", asdict(s)) for s in scans)
        for m, v in views.items():
            prefix = prefixes[m]
            if not v or not complete:
                # A coverage slot is not an inferred MarketEvent.
                raw = next((r for r in bars if r.evidence.expression == m), None)
                if raw is not None and at >= config.decision_start_ns:
                    register(
                        (m, "BREAKOUT_RETEST", "LONG", "MISSING"),
                        at,
                        raw,
                        digest("MECHANISM_COHORT_V1", (m, at)),
                        False,
                        scan_hashes,
                        "NOT_EVALUABLE",
                    )
                continue
            bar = v[-1]
            if last_candle.get(m) == bar.candle_id:
                continue
            last_candle[m] = bar.candle_id
            candidate = scanner_states.get(m)
            if candidate is not None:
                candidate = scanner.advance_scanner_candidate(
                    candidate,
                    bars_5m=v,
                    current_spread_price=bar.close * config.spread_bps / BPS,
                    liquidity_healthy=config.scanner_liquidity_healthy,
                )
                if (
                    scanner.classify_scanner_state(candidate.state)
                    == scanner.ScannerCandidateClass.TERMINAL
                ):
                    candidate = scan_by_market[m].candidate
            else:
                candidate = scan_by_market[m].candidate
            if candidate is not None:
                scanner_states[m] = candidate
            linkage = candidate.linkage if candidate is not None else None
            try:
                result = engine.evaluate_strategy(
                    engine.StrategyEvaluationInput(
                        bars_5m=v, minimum_tick=markets[m].minimum_tick, scanner_linkage=linkage
                    ),
                    ledgers[m],
                )
            except KernelInputError:
                if at < config.decision_start_ns:
                    continue
                register(
                    (m, "BREAKOUT_RETEST", "LONG", "WARMUP"),
                    at,
                    prefix[-1],
                    digest("MECHANISM_WARMUP_V1", (m, at)),
                    False,
                    scan_hashes,
                    "NOT_EVALUABLE",
                )
                continue
            ledgers[m] = result.ledger
            if at < config.decision_start_ns:
                previous_zones[m] = result.zones
                continue
            hashes = tuple(r.record_hash for r in prefix)
            # Raw kernel events are retained even when never formally confirmed.
            for event in result.ledger.events:
                if event.latest_bar.candle_id != bar.candle_id:
                    continue
                key = (m, event.setup_family.value, event.side.value, event.zone.zone_id)
                ep = register(key, at, prefix[-1], event.market_event_id, True, scan_hashes)
                if at >= ep["expiry_ns"]:
                    continue
                for decision in result.decisions:
                    if decision.market_event_id != event.market_event_id:
                        continue
                    target = decision.target_reference.price if decision.target_reference else None
                    receipt = _decision(
                        CHAMPION,
                        at,
                        hashes,
                        decision.setup_mode.value
                        if decision.setup_mode
                        else ("UNCONFIRMED" if key[1] == "BREAKOUT_RETEST" else "NOT_APPLICABLE"),
                        asdict(decision),
                        take=decision.decision == DecisionKind.FORMAL_SETUP_CONFIRMED,
                        reason=decision.reason,
                        low=decision.ideal_entry_low,
                        high=decision.ideal_entry_high,
                        chase=decision.chase_limit,
                        stop=decision.structural_stop,
                        target=target,
                    )
                    ep["decisions"].append(receipt)
            # Baselines observe prior causal zone snapshots, never future confirmation.
            triggers: list[tuple[str, str, str, str]] = []
            old_zones = previous_zones.get(m, ())
            support = next(
                (
                    z
                    for z in old_zones
                    if z.zone_type.value == "LOW" and z.active_for_new_event and not z.suppressed
                ),
                None,
            )
            resistance = next(
                (
                    z
                    for z in old_zones
                    if z.zone_type.value == "HIGH" and z.active_for_new_event and not z.suppressed
                ),
                None,
            )
            for zone in old_zones:
                if not zone.active_for_new_event or zone.suppressed:
                    continue
                if zone.zone_type.value == "LOW":
                    if bar.low < zone.low and bar.close > zone.high:
                        triggers.append((BASELINES[0], "SWEEP_RECLAIM", "LONG", zone.zone_id))
                    if (
                        resistance is not None
                        and bar.low <= zone.high
                        and zone.high < bar.close < resistance.low
                    ):
                        triggers.append(
                            (BASELINES[3], "RANGE_EDGE_REJECTION", "LONG", zone.zone_id)
                        )
                    if v[-2].close >= zone.low and bar.close < zone.low:
                        triggers.append((BASELINES[1], "BREAKOUT_RETEST", "SHORT", zone.zone_id))
                else:
                    if bar.high > zone.high and bar.close < zone.low:
                        triggers.append((BASELINES[0], "SWEEP_RECLAIM", "SHORT", zone.zone_id))
                    if (
                        support is not None
                        and bar.high >= zone.low
                        and support.high < bar.close < zone.low
                    ):
                        triggers.append(
                            (BASELINES[3], "RANGE_EDGE_REJECTION", "SHORT", zone.zone_id)
                        )
                    if v[-2].close <= zone.high and bar.close > zone.high:
                        triggers.append((BASELINES[1], "BREAKOUT_RETEST", "LONG", zone.zone_id))
            if len(v) > config.donchian_bars:
                prior = v[-config.donchian_bars - 1 : -1]
                high, low = max(b.high for b in prior), min(b.low for b in prior)
                if bar.close > high:
                    triggers.append((BASELINES[2], "BREAKOUT_RETEST", "LONG", "DONCHIAN"))
                if bar.close < low:
                    triggers.append((BASELINES[2], "BREAKOUT_RETEST", "SHORT", "DONCHIAN"))
            if (
                candidate
                and candidate.side
                and candidate.state
                in {
                    ScannerState.BREAKOUT_DETECTED,
                    ScannerState.RETEST_PENDING,
                    ScannerState.BREAKOUT_RETEST_READY,
                    ScannerState.REJECTED_CHASE_FOR_ACTION,
                }
            ):
                register(
                    (m, "BREAKOUT_RETEST", candidate.side.value, "SCANNER"),
                    at,
                    prefix[-1],
                    digest("MECHANISM_SCANNER_EPISODE_V1", candidate.candidate_id),
                    False,
                    scan_hashes,
                )
            for code, family, side, boundary in triggers:
                key = (m, family, side, boundary)
                ep = register(
                    key,
                    at,
                    prefix[-1],
                    digest("MECHANISM_RAW_EPISODE_V1", (key, bar.candle_id)),
                    False,
                    scan_hashes,
                )
                if not any(d.code == code and d.participation == "TAKE" for d in ep["decisions"]):
                    stop, target = _baseline_terms(
                        bar, side, markets[m].minimum_tick, config.baseline_target_r
                    )
                    ep["decisions"].append(
                        _decision(
                            code,
                            at,
                            hashes,
                            "UNCONFIRMED" if family == "BREAKOUT_RETEST" else "NOT_APPLICABLE",
                            (key, bar.candle_id),
                            take=True,
                            reason="SIMPLE_CAUSAL_TRIGGER",
                            stop=stop,
                            target=target,
                        )
                    )
            previous_zones[m] = result.zones
    completed.extend(episodes.values())
    output = []
    for values in completed:
        decisions = tuple(
            sorted(values.pop("decisions"), key=lambda d: (d.at, d.code, d.record_hash))
        )
        modes = (
            ("MICRO_FAST", "STANDARD", "UNCONFIRMED")
            if values["family"] == "BREAKOUT_RETEST"
            else ("NOT_APPLICABLE",)
        )
        for mode in modes:
            output.append(
                MechanismOpportunity.create(
                    version="MECHANISM_OPPORTUNITY_V1", **values, mode=mode, decisions=decisions
                )
            )
    return tuple(sorted(output, key=lambda o: (o.start_ns, o.thesis_id, o.mode, o.record_hash)))


def applicable(op: MechanismOpportunity, code: str) -> bool:
    return (
        code == CHAMPION
        or code
        in {
            "SWEEP_RECLAIM": (BASELINES[0],),
            "BREAKOUT_RETEST": (BASELINES[1], BASELINES[2]),
            "RANGE_EDGE_REJECTION": (BASELINES[3],),
        }[op.family]
    )


def _participation(candidate: MechanismCandidate, decision: MechanismDecision) -> bool:
    """Compose existing participation owner on derived immutable receipts only."""
    c = PolicyContext.create(
        version="MECHANISM_POLICY_CONTEXT_V1",
        at=decision.at,
        source_cutoff=decision.at,
        input_hashes=decision.prefix_hashes,
        feature_hashes=(),
        evaluable=True,
        thesis_valid=True,
        champion_take=decision.code == CHAMPION and decision.participation == "TAKE",
        price_core=False,
        failed_auction=False,
        profile_confirmation=False,
        binance_confirmation=False,
        okx_confirmation=False,
        economics_improvable=False,
        room_to_cost=ZERO,
        adverse_bps=ZERO,
        progress_bps=ZERO,
        volatility_bps=Decimal(1),
        elapsed_ns=0,
        structure_failed=False,
        structural_stop_hit=False,
        microstructure_failed=False,
        structural_target=False,
        fresh_structure=False,
        structural_level=None,
        fresh_condition_ns=None,
        fresh_setup=False,
        fresh_microstructure=False,
        reversal=False,
        retest=False,
        high_water_bps=ZERO,
        giveback_fraction=ZERO,
        net_r=ZERO,
        attempts=0,
        max_attempts=1,
        cumulative_cost_bps=ZERO,
        cost_budget_bps=ZERO,
        since_scratch_ns=0,
        winner=False,
        regime_trending=False,
        continuation=False,
        sweep=decision.code == BASELINES[0] and decision.participation == "TAKE",
        close_breakout=decision.code == BASELINES[1] and decision.participation == "TAKE",
        donchian_breakout=decision.code == BASELINES[2] and decision.participation == "TAKE",
        range_rejection=decision.code == BASELINES[3] and decision.participation == "TAKE",
    )
    return evaluate(candidate.participation, c).action == "ENTER"


@decimal80
def evaluate_mechanism_candidate(
    opportunity: MechanismOpportunity,
    candidate: MechanismCandidate,
    decisions: tuple[MechanismDecision, ...],
    rows: tuple[DevObservation, ...],
    config: MechanismConfig,
    *,
    as_of_ns: int,
) -> MechanismResult:
    if candidate.participation.code == CHAMPION:
        # The package release does not alter pure owner semantics; reconstruct the
        # exact causal receipt graph rather than accept a caller's Champion boolean.
        manifest = StrategyPackageManifest.create(trade_os_release_sha="0" * 40)
        if opportunity not in derive_mechanism_opportunities(rows, manifest, config):
            raise ValueError("Champion receipt was not derived from the current kernel")
    return _evaluate_mechanism_candidate(
        checked(opportunity, MechanismOpportunity),
        checked(candidate, MechanismCandidate),
        decisions,
        admitted_rows(rows),
        checked(config, MechanismConfig),
        as_of_ns=as_of_ns,
    )


@decimal80
def _evaluate_mechanism_candidate(
    opportunity: MechanismOpportunity,
    candidate: MechanismCandidate,
    decisions: tuple[MechanismDecision, ...],
    rows: tuple[DevObservation, ...],
    config: MechanismConfig,
    *,
    as_of_ns: int,
) -> MechanismResult:
    op = opportunity
    if (op.config_hash, candidate.config_hash, op.risk_hash, candidate.risk_hash) != (
        config.record_hash,
        config.record_hash,
        config.risk_hash,
        config.risk_hash,
    ) or op.original_risk_cash != config.original_risk_cash:
        raise ValueError("matched config/original risk required")
    if decisions != op.decisions:
        raise ValueError("caller decision bypass forbidden")
    sources = {r.record_hash: r for r in rows}
    for d in decisions:
        if not set(d.prefix_hashes) <= sources.keys() or any(
            not healthy(sources[h], d.at) for h in d.prefix_hashes
        ):
            raise ValueError("future or unbound decision evidence")
    code = candidate.participation.code
    selected = tuple(
        d
        for d in decisions
        if d.code == code
        and (code != CHAMPION or op.family != "BREAKOUT_RETEST" or d.mode == op.mode)
    )
    ready = next((d for d in selected if _participation(candidate, d)), None)
    path_values: dict[str, Any] = dict(
        version="MECHANISM_PATH_V1",
        status="INCOMPLETE",
        input_hashes=(),
        mfe=None,
        mae=None,
        first_stop_ns=None,
        first_target_ns=None,
        time_to_mfe_ns=None,
        time_to_mae_ns=None,
        recovery_ns=None,
        ambiguous=False,
        reasons=("MISSING_PATH",),
    )
    values: dict[str, Any] = dict(
        version="MECHANISM_RESULT_V1",
        opportunity_hash=op.record_hash,
        candidate_hash=candidate.record_hash,
        code=code,
        thesis_id=op.thesis_id,
        cluster_id=op.cluster_id,
        config_hash=config.record_hash,
        risk_hash=op.risk_hash,
        original_risk_cash=op.original_risk_cash,
        decisions=selected,
        entry=None,
        exit=None,
        counterfactual_r=None,
        net_cash=None,
        net_r=None,
        funding_cash=None,
        additional_cash=ZERO,
        terminal="NOT_EVALUABLE",
        reasons=(),
    )

    def finish() -> MechanismResult:
        return MechanismResult.create(**values, path=MechanismPath.create(**path_values))

    if not applicable(op, code):
        values.update(terminal="NOT_APPLICABLE", reasons=("FAMILY_NOT_APPLICABLE",))
        return finish()
    if op.availability != "AVAILABLE":
        values["reasons"] = op.reasons
        return finish()
    forward = tuple(
        sorted(
            (
                r
                for r in rows
                if r.evidence.expression == op.expression
                and r.evidence.dataset_hash == op.dataset_hash
                and r.kind == "BAR"
                and int(dict(r.values)["start_ns"]) >= op.start_ns
                and (r.bar_end or 0) <= op.horizon_end
                and healthy(r, as_of_ns)
            ),
            key=lambda r: int(dict(r.values)["start_ns"]),
        )
    )
    expected = tuple(range(op.start_ns, op.horizon_end, config.resolution_ns))
    actual = tuple(int(dict(r.values)["start_ns"]) for r in forward)
    path_values["input_hashes"] = tuple(r.record_hash for r in forward)
    if (
        actual != expected
        or as_of_ns < op.horizon_end
        or len({r.continuity_epoch for r in forward}) != 1
    ):
        values["reasons"] = ("GAPPED_OR_CENSORED_HORIZON",)
        return finish()
    if config.funding_applicable and config.funding_bps is None:
        values["reasons"] = ("MISSING_APPLICABLE_FUNDING",)
        return finish()
    if ready is None:
        values.update(
            terminal="SUPPRESSED",
            net_cash=ZERO,
            net_r=ZERO,
            funding_cash=ZERO,
            reasons=("NO_CAUSAL_ACTIVATION",),
        )
        path_values.update(status="COMPLETE", reasons=())
        # Registered reference time uses the first available baseline's causal geometry.
        reference = next(
            (d for d in decisions if d.code != CHAMPION and d.participation == "TAKE"), None
        )
        if reference is not None and reference.code != code:
            baseline = next((c for c in CODES if c == reference.code), None)
            if baseline:
                from .policies import AUTHORITIES, PolicySpec

                ref_candidate = MechanismCandidate.create(
                    version="MECHANISM_CANDIDATE_V1",
                    participation=PolicySpec.create(
                        version="B_POLICY_V1",
                        family="BASELINE",
                        code=baseline,
                        authority=AUTHORITIES["BASELINE"],
                        semantics="ISSUE_FAMILIES_B_V1",
                        parameters=(),
                    ),
                    config_hash=config.record_hash,
                    risk_hash=config.risk_hash,
                    role="BASELINE",
                )
                cf = _evaluate_mechanism_candidate(
                    op, ref_candidate, decisions, rows, config, as_of_ns=as_of_ns
                )
                values["counterfactual_r"] = cf.net_r
        return finish()
    if ready.stop is None or ready.target is None:
        values["reasons"] = ("MISSING_CAUSAL_GEOMETRY",)
        return finish()
    entry_row = next(
        (
            r
            for r in forward
            if int(dict(r.values)["start_ns"]) >= ready.at + config.cost.delay_ns
            and int(dict(r.values)["start_ns"]) < op.expiry_ns
        ),
        None,
    )
    if entry_row is None:
        values.update(
            terminal="NONFILL",
            net_cash=ZERO,
            net_r=ZERO,
            funding_cash=ZERO,
            reasons=("DELAY_OR_EXPIRY",),
        )
        path_values.update(status="COMPLETE", reasons=())
        return finish()
    sign = Decimal(1) if op.side == "LONG" else Decimal(-1)
    raw_price = entry_row.number("open")
    friction = (config.spread_bps / 2 + config.cost.slippage_bps) / BPS
    price = raw_price * (1 + sign * friction)
    if (
        (ready.entry_low is not None and price < ready.entry_low)
        or (ready.entry_high is not None and price > ready.entry_high)
        or (ready.chase is not None and (price - ready.chase) * sign > 0)
    ):
        values.update(
            terminal="NONFILL",
            net_cash=ZERO,
            net_r=ZERO,
            funding_cash=ZERO,
            reasons=("ENTRY_ZONE_OR_CHASE",),
        )
        path_values.update(status="COMPLETE", reasons=())
        return finish()
    if not (price - ready.stop) * sign > 0 or not (ready.target - price) * sign > 0:
        values["reasons"] = ("INVALID_CAUSAL_GEOMETRY",)
        return finish()
    size = min(config.original_risk_cash / abs(price - ready.stop), config.capital_cash / price)
    start = int(dict(entry_row.values)["start_ns"])
    held = tuple(r for r in forward if int(dict(r.values)["start_ns"]) >= start)
    high_water = ZERO
    low_water = ZERO
    exit_row = held[-1]
    exit_price = exit_row.number("close")
    exit_time = exit_row.bar_end or 0
    for r in held:
        ts = r.bar_end or 0
        favorable = ((r.number("high") if sign > 0 else r.number("low")) - price) * sign
        adverse = ((r.number("low") if sign > 0 else r.number("high")) - price) * sign
        if favorable > high_water:
            high_water = favorable
            path_values["time_to_mfe_ns"] = ts - start
        if adverse < low_water:
            low_water = adverse
            path_values["time_to_mae_ns"] = ts - start
        if low_water < 0 and adverse >= 0 and path_values["recovery_ns"] is None:
            path_values["recovery_ns"] = ts
        hit_stop = r.number("low") <= ready.stop if sign > 0 else r.number("high") >= ready.stop
        hit_target = (
            r.number("high") >= ready.target if sign > 0 else r.number("low") <= ready.target
        )
        if hit_stop:
            path_values["first_stop_ns"] = ts
        if hit_target:
            path_values["first_target_ns"] = ts
        if hit_stop or hit_target:
            path_values["ambiguous"] = hit_stop and hit_target
            exit_row, exit_time = r, ts
            exit_price = (
                (
                    min(r.number("open"), ready.stop)
                    if sign > 0
                    else max(r.number("open"), ready.stop)
                )
                if hit_stop
                else ready.target
            )
            break
    exit_price *= 1 - sign * friction
    if exit_price <= 0:
        raise ValueError("nonpositive modeled exit")

    def fill(
        ts: int, px: Decimal, buy: bool, row: DevObservation, reference: Decimal
    ) -> ModeledFill:
        return ModeledFill.create(
            version="MODELED_FILL_V1",
            ts=ts,
            price=wire(px),
            size=wire(size),
            direction="BUY" if buy else "SELL",
            fee=wire(px * size * config.cost.taker_bps / BPS),
            friction_cash=wire(abs(px - reference) * size),
            source_hash=row.record_hash,
            model_hash=config.record_hash,
        )

    entry = fill(start, price, sign > 0, entry_row, raw_price)
    # Exit reference removes exactly the modeled exit friction.
    exit_fill = fill(exit_time, exit_price, sign < 0, exit_row, exit_price / (1 - sign * friction))
    funding = ZERO
    if config.funding_applicable:
        rate = config.funding_bps or ZERO
        count = (exit_time - config.funding_anchor_ns) // config.funding_interval_ns - (
            start - config.funding_anchor_ns
        ) // config.funding_interval_ns
        funding = -sign * price * size * rate / BPS * count
    additional = (price + exit_price) * size * config.cost.additional_cost_bps / BPS
    net = (
        (exit_fill.price - entry.price) * sign * entry.size
        - entry.fee
        - exit_fill.fee
        + funding
        - additional
    )
    path_values.update(status="COMPLETE", mfe=wire(high_water), mae=wire(low_water), reasons=())
    values.update(
        entry=entry,
        exit=exit_fill,
        funding_cash=wire(funding),
        additional_cash=wire(additional),
        terminal="COMPLETE",
        net_cash=wire(net),
        net_r=wire(net / op.original_risk_cash),
    )
    return finish()
