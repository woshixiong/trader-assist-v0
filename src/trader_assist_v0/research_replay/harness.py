"""One bounded offline harness; native rc5 owns all simulated fills and positions."""

from __future__ import annotations

import importlib
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from trader_assist_v0.contracts.common import Sha256Hex
from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
from trader_assist_v0.nautilus_g4.catalog_bridge import project_native_replay
from trader_assist_v0.nautilus_g4.runner import (
    assert_exact_nautilus_rc5,
    build_fill_model,
    project_provider_native_state,
)
from trader_assist_v0.nautilus_pilot.contracts import PilotEvaluationEnvelope, StrategyInputEvent
from trader_assist_v0.nautilus_pilot.strategy_package import (
    PilotStrategyEvaluator,
    StrategyPackageManifest,
)
from trader_assist_v0.research_data.contracts import BoundRecord, DatasetManifest
from trader_assist_v0.vnext_g4.contracts import ExecutionModelConfig

from .contracts import (
    Attempt,
    CashFlow,
    DecisionSnapshot,
    FeatureObservation,
    Fill,
    Observation,
    Opportunity,
    ResearchRunSpec,
    decimal80,
    digest,
)
from .evidence import require_pipeline
from .lifecycle import BlockPlan, TrialLedger, VisibilityPolicy
from .paths import funding_settlement, measure_path, net_cash
from .policies import PolicyAction, PolicyContext, PolicySpec, evaluate
from .reporting import CandidateResult, CounterfactualPathRef, Pair, bundle_fingerprint, pair


class CandidatePlan(BoundRecord):
    participation: PolicySpec
    loss: PolicySpec
    reentry: PolicySpec
    exit: PolicySpec
    add: PolicySpec
    max_attempts: int = Field(gt=0, le=20)
    max_adds: int = Field(ge=0, le=10)
    cost_budget_bps: Decimal = Field(ge=0)
    winner_progress_bps: Decimal = Field(gt=0)
    role: Literal["REFERENCE", "CHALLENGER", "NEGATIVE_CONTROL"]

    @model_validator(mode="after")
    def roles(self) -> Self:
        if self.participation.family not in {"CHAMPION", "BASELINE", "EA"} or (
            self.loss.family,
            self.reentry.family,
            self.exit.family,
            self.add.family,
        ) != ("L", "R", "E", "A"):
            raise ValueError("candidate policy-family roles mismatch")
        if not self.cost_budget_bps.is_finite() or not self.winner_progress_bps.is_finite():
            raise ValueError("finite candidate budgets required")
        return self


class ContextFrame(BoundRecord):
    opportunity_hash: Sha256Hex
    context: PolicyContext
    features: tuple[FeatureObservation, ...]

    @model_validator(mode="after")
    def causal_features(self) -> Self:
        if self.context.feature_hashes != tuple(f.record_hash for f in self.features):
            raise ValueError("feature/context identity mismatch")
        if any(
            f.event_cutoff > self.context.at or f.knowledge_cutoff > self.context.at
            for f in self.features
        ):
            raise ValueError("future feature in policy frame")
        if any(f.status != "AVAILABLE" for f in self.features) and self.context.evaluable:
            raise ValueError("missing feature cannot be declared evaluable")
        return self


class ReplayBundle(BoundRecord):
    run_hash: Sha256Hex
    results: tuple[CandidateResult, ...]
    pairs: tuple[Pair, ...]
    artifacts: tuple[tuple[str, Sha256Hex], ...]
    fingerprint: Sha256Hex
    counterfactuals: tuple[CounterfactualPathRef, ...]

    @model_validator(mode="after")
    def fingerprint_binding(self) -> Self:
        if self.fingerprint != bundle_fingerprint(self.run_hash, self.artifacts):
            raise ValueError("bundle fingerprint mismatch")
        if dict(self.artifacts).get("results") != digest(
            "B_RESULTS", tuple(r.record_hash for r in self.results)
        ):
            raise ValueError("bundle output binding mismatch")
        if dict(self.artifacts).get("pairs") != digest(
            "B_PAIRS", tuple(p.record_hash for p in self.pairs)
        ):
            raise ValueError("bundle pair binding mismatch")
        if dict(self.artifacts).get("counterfactuals") != digest(
            "B_COUNTERFACTUALS", tuple(c.record_hash for c in self.counterfactuals)
        ):
            raise ValueError("counterfactual bundle binding mismatch")
        return self


def replay_champion(
    manifest: StrategyPackageManifest,
    events: tuple[StrategyInputEvent, ...],
    *,
    market_id: str,
    minimum_tick: Decimal,
) -> tuple[PilotEvaluationEnvelope, ...]:
    """Delegate finality, warmup, continuation and Three Setup rules to their owner."""
    evaluator = PilotStrategyEvaluator(
        manifest=manifest, market_id=market_id, minimum_tick=minimum_tick
    )
    outputs = []
    for event in events:
        output = evaluator.evaluate(event)
        if output is not None:
            outputs.append(output)
    return tuple(outputs)


def trial_identity(run: ResearchRunSpec, candidate: CandidatePlan) -> str:
    """Noncircular material identity; excludes operational runtime and ledger envelope."""
    return digest(
        "B_MATERIAL_TRIAL_V1",
        (
            candidate.record_hash,
            run.strategy_hash,
            run.dataset_hashes,
            run.feature_hashes,
            run.roster_hash,
            run.cost.record_hash,
            run.horizon_ns,
            run.seed,
            run.block_plan_hash,
            run.visibility_hash,
            run.ambiguity,
        ),
    )


def validate_inputs(
    run: ResearchRunSpec,
    datasets: tuple[DatasetManifest, ...],
    rows: tuple[Observation, ...],
    roster: tuple[Opportunity, ...],
    candidates: tuple[CandidatePlan, ...],
    frames: tuple[ContextFrame, ...],
    ledger: TrialLedger,
    blocks: BlockPlan,
    visibility: VisibilityPolicy,
) -> None:
    run = ResearchRunSpec.model_validate_json(run.model_dump_json())
    datasets = tuple(require_pipeline(d) for d in datasets)  # first: no byte hashing before gate
    if tuple(d.record_hash for d in datasets) != run.dataset_hashes:
        raise ValueError("dataset identity mismatch")
    if len(rows) > run.max_observations or len(candidates) > run.max_candidates:
        raise ValueError("bounded observations/candidates exceeded")
    if not candidates or len({c.record_hash for c in candidates}) != len(candidates):
        raise ValueError("empty/duplicate candidate roster")
    if tuple(c.record_hash for c in candidates) != run.policy_hashes:
        raise ValueError("fixed candidate roster mismatch")
    if digest("B_ROSTER", tuple(o.record_hash for o in roster)) != run.roster_hash:
        raise ValueError("frozen opportunity roster mismatch")
    if len({o.opportunity_id for o in roster}) != len(roster):
        raise ValueError("duplicate opportunity")
    for value in (ledger, blocks, visibility):
        type(value).model_validate_json(value.model_dump_json())
    if (ledger.record_hash, blocks.record_hash, visibility.record_hash) != (
        run.trial_ledger_hash,
        run.block_plan_hash,
        run.visibility_hash,
    ):
        raise ValueError("trial/block/visibility identity mismatch")
    if ledger.preregistration.stage != "S0" or ledger.history != "COMPLETE":
        raise PermissionError("only fully logged S0 engineering runs executable")
    if (
        ledger.preregistration.cost_hash != run.cost.record_hash
        or ledger.preregistration.block_plan_hash != blocks.record_hash
    ):
        raise ValueError("preregistered assumptions mismatch")
    if (
        ledger.preregistration.visibility_hash != visibility.record_hash
        or run.horizon_ns > ledger.preregistration.max_horizon_ns
    ):
        raise ValueError("visibility/horizon changed within certification")
    allowed_variants = {t.semantic_hash for t in ledger.trials}
    if not {trial_identity(run, c) for c in candidates} <= allowed_variants:
        raise ValueError("unlogged material candidate")
    manifests = {d.record_hash: d for d in datasets}
    for raw in rows:
        row = Observation.model_validate_json(raw.model_dump_json())
        ref = row.evidence
        ds = manifests.get(ref.dataset_hash)
        if ds is None or (ref.source_tier, ref.exposure_state) != (
            ds.source_tier,
            ds.exposure_state,
        ):
            raise ValueError("derived evidence outside lifecycle binding")
        if ref.instrument not in ds.instruments or not ds.start_ns <= row.ts_event < ds.end_ns:
            raise ValueError("evidence outside exact authorized cut")
        if (ref.coverage_start, ref.coverage_end) != (ds.start_ns, ds.end_ns):
            raise ValueError("coverage identity mismatch")
        if ref.rights_hash != (ds.rights.record_hash if ds.rights else None):
            raise ValueError("rights provenance mismatch")
    observations = {r.record_hash: r for r in rows}
    opportunities = {o.record_hash: o for o in roster}
    for opportunity in roster:
        Opportunity.model_validate_json(opportunity.model_dump_json())
        if opportunity.strategy_hash != run.strategy_hash:
            raise ValueError("opportunity Strategy identity mismatch")
        if not set(opportunity.prefix_hashes) <= observations.keys():
            raise ValueError("unbound opportunity prefix")
        if any(
            observations[h].ts_event > opportunity.decision_ns
            or observations[h].known_at > opportunity.knowledge_ns
            for h in opportunity.prefix_hashes
        ):
            raise ValueError("future opportunity prefix")
    for candidate in candidates:
        CandidatePlan.model_validate_json(candidate.model_dump_json())
    for raw_frame in frames:
        frame = ContextFrame.model_validate_json(raw_frame.model_dump_json())
        if frame.opportunity_hash not in opportunities:
            raise ValueError("frame outside roster")
        if not set(frame.context.input_hashes) <= observations.keys():
            raise ValueError("frame source not retained")
        if any(
            observations[h].ts_event > frame.context.at
            or observations[h].known_at > frame.context.source_cutoff
            for h in frame.context.input_hashes
        ):
            raise ValueError("future policy source")
        op = opportunities[frame.opportunity_hash]
        sources = tuple(observations[h] for h in frame.context.input_hashes)
        if frame.context.evaluable and not any(
            r.evidence.owner == "HL_E4"
            and r.evidence.expression == op.market_id
            and r.evidence.registry_hash == op.registry_hash
            and not set(r.quality) - {"COMPLETE", "AVAILABLE_VERIFIED"}
            and r.evidence.valid_from <= r.ts_event < r.evidence.valid_to
            and max(r.evidence.mapping_known_at, r.evidence.mapping_recorded_at)
            <= frame.context.source_cutoff
            for r in sources
        ):
            raise ValueError("evaluable policy requires bound healthy exact-venue truth")
        for feature in frame.features:
            if (
                feature.spec_hash not in run.feature_hashes
                or not set(feature.input_hashes) <= observations.keys()
            ):
                raise ValueError("unbound feature/version")
            if any(
                observations[h].ts_event > feature.event_cutoff
                or observations[h].known_at > feature.knowledge_cutoff
                for h in feature.input_hashes
            ):
                raise ValueError("future feature source")


def snapshot(
    run: ResearchRunSpec,
    opportunity: Opportunity,
    candidate: CandidatePlan,
    frame: ContextFrame,
) -> DecisionSnapshot:
    action = evaluate(candidate.participation, frame.context)
    return DecisionSnapshot.create(
        version="B_DECISION_V1",
        opportunity_hash=opportunity.record_hash,
        policy_hash=candidate.record_hash,
        decision=action.participation,
        reasons=(action.reason,),
        decision_ns=frame.context.at,
        prefix_hashes=frame.context.input_hashes,
        feature_hashes=frame.context.feature_hashes,
        cost_hash=run.cost.record_hash,
        horizon_end=opportunity.decision_ns + run.horizon_ns,
    )


@decimal80
def _native_candidate(
    run: ResearchRunSpec,
    opportunity: Opportunity,
    candidate: CandidatePlan,
    rows: tuple[Observation, ...],
    frames: tuple[ContextFrame, ...],
    events: tuple[AdmittedEvent, ...],
    instrument: object,
    execution: ExecutionModelConfig,
    cashflows: tuple[CashFlow, ...],
    funding_complete: bool,
    funding_applicable: bool,
    *,
    counterfactual: bool = False,
) -> CandidateResult:
    """Any is confined to the optional rc5 Python/Rust callback boundary."""
    assert_exact_nautilus_rc5()
    native = importlib.import_module("nautilus_trader.model")
    backtest = importlib.import_module("nautilus_trader.backtest")
    trading = importlib.import_module("nautilus_trader.trading")
    provider: Any = instrument
    if not isinstance(provider, native.CryptoPerpetual) or str(provider.id.venue) != "HYPERLIQUID":
        raise TypeError("native Hyperliquid CryptoPerpetual required")
    if (
        Decimal(str(provider.maker_fee)) * 10_000 != run.cost.maker_bps
        or Decimal(str(provider.taker_fee)) * 10_000 != run.cost.taker_bps
    ):
        raise ValueError("native fee profile differs from matched cost identity")
    if (
        execution.book_type != "L1_MBP"
        or execution.order_primitive.value != "MARKETABLE"
        or execution.queue_position
    ):
        raise ValueError("initial B native adapter supports explicit marketable L1 only")
    if digest("B_NATIVE_EXECUTION", execution.model_dump(mode="json")) != run.cost.fill_model_hash:
        raise ValueError("native fill model identity mismatch")
    if run.cost.slippage_bps != 0:
        raise ValueError("native slippage must use bound rc5 fill model, not a second fill engine")
    if execution.random_seed != run.seed:
        raise ValueError("native seed differs from paired run")
    checked_events = tuple(AdmittedEvent.model_validate_json(e.model_dump_json()) for e in events)
    refs = {
        r.evidence.source_hash: r
        for r in rows
        if r.evidence.owner == "HL_E4"
        and r.evidence.expression == opportunity.market_id
        and r.evidence.instrument == str(provider.id)
    }
    if any(
        e.admission_hash not in refs or e.source.instrument_id != str(provider.id)
        for e in checked_events
    ):
        raise ValueError("native source not bound to admitted HL evidence")
    projection = project_native_replay(
        events=tuple(
            e for e in checked_events if e.source.data_kind.value in {"BBO", "TRADE", "BAR"}
        ),
        market_id=opportunity.market_id,
        expression_id=checked_events[0].source.expression_id,
        instrument_id=str(provider.id),
    )
    # Consumption clock is retained admission, not a fabricated receive time or raw rewrite.
    replay_events: list[Any] = []
    for source_hash, native_event in zip(
        projection.identity.ordered_source_admission_hashes, projection.events, strict=True
    ):
        projected: Any = native_event
        payload = projected.to_dict()
        payload["ts_init"] = refs[source_hash].known_at
        replay_events.append(type(projected).from_dict(payload))
    quotes = {r.known_at: r for r in refs.values() if r.kind == "BBO"}
    if len(quotes) != sum(r.kind == "BBO" for r in refs.values()):
        raise ValueError("equal init-time quote ambiguity refused by native adapter")
    if tuple(f.context.at for f in frames) != tuple(sorted({f.context.at for f in frames})):
        raise ValueError("frames must be strictly chronological")
    if not frames or frames[0].context.at != opportunity.decision_ns:
        raise ValueError("original causal decision frame required")
    decisions: list[DecisionSnapshot] = []
    actions: list[PolicyAction] = []
    fills: list[Fill] = []
    attempts: list[Attempt] = []
    limitations = {"L1_NO_QUEUE_OR_IMPACT_PROOF"}
    state: dict[str, Any] = dict(
        frame_index=0,
        position=Decimal(0),
        pending=None,
        pending_order=None,
        entry=None,
        last_scratch=0,
        high_water=Decimal(0),
        adds=0,
        ratchet=None,
        terminal=False,
        no_submit=False,
        trigger=opportunity.decision_ns,
    )
    side = Decimal(1) if opportunity.side == "LONG" else Decimal(-1)

    def on_start(self: Any) -> None:
        self.subscribe_quotes(provider.id)

    def queue(action: PolicyAction, at: int) -> None:
        if state["pending"] is None:
            state["pending"] = (action, at + run.cost.delay_ns)

    def on_quote(self: Any, quote: Any) -> None:
        now = int(quote.ts_init)
        row = quotes.get(now)
        if row is None or row.evidence.owner != "HL_E4":
            raise RuntimeError("native quote missing exact source")
        if row.known_at > now or row.ts_event > now:
            raise RuntimeError("native clock precedes original admission")
        if row.ts_event > opportunity.decision_ns + run.horizon_ns:
            return
        while state["frame_index"] < len(frames) and frames[state["frame_index"]].context.at <= now:
            frame = frames[state["frame_index"]]
            state["frame_index"] += 1
            c = frame.context
            valid = (
                c.thesis_valid
                and c.at < opportunity.expiry_ns
                and (opportunity.invalidation_ns is None or c.at < opportunity.invalidation_ns)
            )
            if state["entry"] is not None:
                price = row.number("bid" if side > 0 else "ask")
                entry: Fill = state["entry"]
                progress = (price / entry.price - 1) * side * 10_000
                # Only the current source and earlier high-water may influence this decision.
                if row.known_at > c.at:
                    raise ValueError(
                        "context would use later quote; supply frame on admitted quote"
                    )
                state["high_water"] = max(state["high_water"], progress)
                stop = state["ratchet"] if state["ratchet"] is not None else opportunity.stop
                updates = dict(
                    progress_bps=progress,
                    adverse_bps=max(Decimal(0), -progress),
                    elapsed_ns=c.at - entry.ts,
                    high_water_bps=state["high_water"],
                    giveback_fraction=(state["high_water"] - progress) / state["high_water"]
                    if state["high_water"] > 0
                    else Decimal(0),
                    net_r=(price - entry.price) * side / abs(opportunity.entry - opportunity.stop),
                    structural_stop_hit=(price - stop) * side <= 0,
                    structural_target=(price - opportunity.target) * side >= 0,
                    winner=progress >= candidate.winner_progress_bps,
                )
            else:
                updates = dict(winner=False, progress_bps=Decimal(0), structural_stop_hit=False)
            fees_bps = (
                (
                    sum((f.fee for f in fills), Decimal(0))
                    + sum(
                        (
                            max(Decimal(0), (a.fill.price - a.exit_fill.price) * side * a.fill.size)
                            for a in attempts
                            if a.state == "SCRATCHED" and a.fill and a.exit_fill
                        ),
                        Decimal(0),
                    )
                )
                / (opportunity.entry * run.cost.size)
                * 10_000
            )
            c = PolicyContext.create(
                **{
                    **c.model_dump(exclude={"record_hash"}),
                    **updates,
                    "thesis_valid": valid,
                    "attempts": len(attempts),
                    "max_attempts": candidate.max_attempts,
                    "cumulative_cost_bps": fees_bps,
                    "cost_budget_bps": candidate.cost_budget_bps,
                    "since_scratch_ns": c.at - state["last_scratch"],
                }
            )
            if c.winner and attempts and attempts[-1].winner_confirmed_ns is None:
                attempts[-1] = Attempt.create(
                    **{
                        **attempts[-1].model_dump(exclude={"record_hash"}),
                        "state": "WINNER_CONFIRMED",
                        "winner_confirmed_ns": c.at,
                    }
                )
            if state["position"] == 0 and state["pending_order"] is None and not state["terminal"]:
                if attempts:
                    action = evaluate(candidate.reentry, c)
                else:
                    snap = snapshot(
                        run,
                        opportunity,
                        candidate,
                        ContextFrame.create(
                            version=frame.version,
                            opportunity_hash=frame.opportunity_hash,
                            context=c,
                            features=frame.features,
                        ),
                    )
                    decisions.append(snap)
                    action = evaluate(candidate.participation, c)
                    if counterfactual and len(decisions) == 1 and valid and c.evaluable:
                        action = PolicyAction.create(
                            version="B_ACTION_V1",
                            policy_hash=candidate.participation.record_hash,
                            context_hash=c.record_hash,
                            participation="TAKE",
                            action="ENTER",
                            fraction=Decimal(1),
                            reason="PREREGISTERED_COUNTERFACTUAL_TAKE",
                        )
                    if snap.decision in {"PASS", "BLOCKED", "NOT_EVALUABLE"} and not counterfactual:
                        state["terminal"] = True
                actions.append(action)
                if action.action in {"ENTER", "REENTER"}:
                    queue(action, c.at)
            elif state["position"] != 0 and state["pending_order"] is None:
                loss = evaluate(candidate.loss, c)
                exit_action = evaluate(candidate.exit, c)
                action = loss if loss.action == "SCRATCH" else exit_action
                # Invalidation/protection wins over winner add/scale on the same observation.
                if not valid or c.structural_stop_hit:
                    action = PolicyAction.create(
                        version="B_ACTION_V1",
                        policy_hash=candidate.exit.record_hash,
                        context_hash=c.record_hash,
                        participation="TAKE",
                        action="EXIT",
                        fraction=Decimal(1),
                        reason="PROTECTION_FIRST",
                    )
                if action.action == "HOLD" and state["adds"] < candidate.max_adds:
                    action = evaluate(candidate.add, c)
                actions.append(action)
                if action.action == "RATCHET":
                    # Registered structural level, effective on subsequent frames only.
                    if c.structural_level is None:
                        limitations.add("STRUCTURAL_RATCHET_LEVEL_MISSING")
                    else:
                        state["ratchet"] = (
                            max(state["ratchet"] or opportunity.stop, c.structural_level)
                            if side > 0
                            else min(state["ratchet"] or opportunity.stop, c.structural_level)
                        )
                elif action.action != "HOLD":
                    queue(action, c.at)
        if state["pending_order"] is not None or state["pending"] is None:
            return
        action, arrival = state["pending"]
        if now < arrival:
            return
        state["pending"] = None
        if (
            set(row.quality) - {"COMPLETE", "AVAILABLE_VERIFIED"}
            or now - row.ts_event > run.cost.quote_age_ns
        ):
            limitations.add("ARRIVAL_QUOTE_UNAVAILABLE")
            state["no_submit"] = True
            return
        entry_order = action.action in {"ENTER", "REENTER", "ADD"}
        if entry_order and (
            now >= opportunity.expiry_ns
            or (opportunity.invalidation_ns is not None and now >= opportunity.invalidation_ns)
        ):
            limitations.add("THESIS_EXPIRED_BEFORE_ARRIVAL")
            state["no_submit"] = True
            return
        direction = "BUY" if (side > 0) == entry_order else "SELL"
        size = (
            run.cost.size * action.fraction
            if entry_order
            else abs(state["position"]) * action.fraction
        )
        if size <= 0 or size > row.number("ask_size" if direction == "BUY" else "bid_size"):
            limitations.add("ARRIVAL_CAPACITY_NONFILL")
            state["no_submit"] = True
            return
        quantity = provider.make_qty(float(size))
        if Decimal(str(quantity)) != size:
            raise ValueError("native lot rounding changed registered size")
        state["trigger"] = arrival - run.cost.delay_ns
        order = self.order_factory.market(
            instrument_id=provider.id,
            order_side=native.OrderSide.BUY if direction == "BUY" else native.OrderSide.SELL,
            quantity=quantity,
            reduce_only=not entry_order,
        )
        state["pending_order"] = (str(order.client_order_id), action, row.record_hash, direction)
        self.submit_order(order)

    def on_fill(self: Any, event: Any) -> None:
        if not isinstance(event, native.OrderFilled) or state["pending_order"] is None:
            raise TypeError("only source-bound native OrderFilled accepted")
        order_id, action, source_hash, direction = state["pending_order"]
        if str(event.client_order_id) != order_id:
            raise RuntimeError("unexpected native order identity")
        fill = Fill(
            ts=int(event.ts_event),
            price=Decimal(str(event.last_px)),
            size=Decimal(str(event.last_qty)),
            direction=direction,
            fee=Decimal(str(event.commission.as_decimal())),
            source_hash=source_hash,
        )
        if fill.ts < state["trigger"] + run.cost.delay_ns:
            raise RuntimeError("native fill precedes modeled arrival")
        fills.append(fill)
        state["pending_order"] = None
        state["position"] += fill.size if direction == "BUY" else -fill.size
        if action.action in {"ENTER", "REENTER"}:
            state["entry"] = fill
            state["high_water"] = Decimal(0)
            attempts.append(
                Attempt.create(
                    version="B_ATTEMPT_V1",
                    thesis_id=opportunity.thesis_id,
                    policy_hash=candidate.record_hash,
                    index=len(attempts) + 1,
                    trigger_ns=state["trigger"],
                    fill=fill,
                    exit_fill=None,
                    state="PROBE_OPEN",
                    fresh_condition_hash=action.context_hash,
                    reason=action.reason,
                )
            )
        elif action.action == "ADD":
            state["adds"] += 1
        elif state["position"] == 0:
            attempts[-1] = Attempt.create(
                **{
                    **attempts[-1].model_dump(exclude={"record_hash"}),
                    "exit_fill": fill,
                    "state": "SCRATCHED" if action.action == "SCRATCH" else "COMPLETE",
                    "reason": action.reason,
                }
            )
            state["last_scratch"] = fill.ts
            state["entry"] = None
            state["terminal"] = action.action != "SCRATCH"

    bridge = type(
        "PackageBPolicyBridge",
        (trading.Strategy,),
        {
            "on_start": on_start,
            "on_quote": on_quote,
            "on_order_filled": on_fill,
        },
    )
    engine = backtest.BacktestEngine(
        backtest.BacktestEngineConfig(
            trader_id=native.TraderId("PKGB-" + candidate.record_hash[:16]),
            bypass_logging=True,
            run_analysis=False,
        )
    )
    try:
        engine.add_venue(
            venue=provider.id.venue,
            oms_type=native.OmsType.NETTING,
            account_type=native.AccountType.MARGIN,
            starting_balances=[native.Money(Decimal("1000000"), provider.quote_currency)],
            base_currency=provider.quote_currency,
            book_type=native.BookType.L1_MBP,
            fill_model=build_fill_model(execution),
            bar_execution=False,
            trade_execution=execution.trade_execution,
            liquidity_consumption=execution.liquidity_consumption,
            queue_position=False,
        )
        engine.add_instrument(provider)
        engine.add_data(replay_events)
        engine.add_strategy(bridge())
        engine.run()
        native_state = project_provider_native_state(
            engine.cache, engine.portfolio, venue=provider.id.venue
        )
        native_quantity = sum(
            (
                Decimal(p.quantity) * (Decimal(1) if p.side == "LONG" else Decimal(-1))
                for p in native_state.position_semantics
                if p.side != "FLAT"
            ),
            Decimal(0),
        )
        if native_quantity != state["position"]:
            raise RuntimeError("native Cache position differs from fill ledger")
        if state["pending_order"] is not None:
            limitations.add("NATIVE_PARTIAL_OR_NONFILL")
        if not decisions:
            decisions.append(snapshot(run, opportunity, candidate, frames[0]))
        path = measure_path(
            decisions[0], opportunity, rows, as_of=opportunity.decision_ns + run.horizon_ns
        )
        first_fill = fills[0] if fills else None
        fill_path = (
            measure_path(
                decisions[0],
                opportunity,
                rows,
                as_of=opportunity.decision_ns + run.horizon_ns,
                fill=first_fill,
            )
            if first_fill
            else None
        )
        if cashflows:
            raise ValueError(
                "unbound caller cash flows forbidden; use retained settlement evidence"
            )
        matured_end = opportunity.decision_ns + run.horizon_ns
        relevant_flows: list[CashFlow] = []
        for fill in fills:
            if run.cost.additional_cost_bps:
                relevant_flows.append(
                    CashFlow(
                        ts=fill.ts,
                        amount=-fill.price * fill.size * run.cost.additional_cost_bps / 10_000,
                        source_hash=digest(
                            "B_ADDITIONAL_MODELED_COST",
                            (run.cost.record_hash, fill.model_dump(mode="json")),
                        ),
                        kind="ADDITIONAL_COST",
                    )
                )
        settlement_rows = tuple(
            r
            for r in refs.values()
            if r.kind == "CONTEXT"
            and dict(r.values).get("field") == "FUNDING"
            and dict(r.values).get("settlement_ns")
        )
        for rate in settlement_rows:
            settlement = int(dict(rate.values)["settlement_ns"])
            if not first_fill or settlement < first_fill.ts or settlement > matured_end:
                continue
            if state["position"] == 0 and settlement > fills[-1].ts:
                continue
            marks = tuple(
                r
                for r in refs.values()
                if r.kind == "BBO"
                and r.ts_event <= settlement
                and r.known_at <= matured_end
                and settlement - r.ts_event <= run.cost.quote_age_ns
            )
            if not marks:
                funding_complete = False
                continue
            mark = max(marks, key=lambda r: (r.ts_event, r.ordinal))
            flow = funding_settlement(
                tuple(fills),
                rate,
                mark,
                as_of=matured_end,
                profile_hash=digest("B_FUNDING_PROFILE", run.cost.funding_profile),
            )
            if flow.amount != 0 and not funding_applicable:
                raise ValueError("no-span funding claim contradicts retained exposure/settlement")
            relevant_flows.append(flow)
        if funding_applicable and not any(c.kind == "FUNDING" for c in relevant_flows):
            funding_complete = False
        relevant = tuple(relevant_flows)
        cash = (
            net_cash(
                tuple(fills),
                relevant,
                funding_complete=funding_complete,
                funding_applicable=funding_applicable,
            )
            if state["position"] == 0
            else None
        )
        if not fills and decisions[-1].decision != "TAKE":
            cash = Decimal(0)
        risk = abs(opportunity.entry - opportunity.stop) * run.cost.size
        return CandidateResult.create(
            version="B_CANDIDATE_RESULT_V1",
            candidate_hash=candidate.record_hash,
            opportunity_hash=opportunity.record_hash,
            market_event_id=opportunity.market_event_id,
            thesis_id=opportunity.thesis_id,
            cluster_id=opportunity.cluster_id,
            setup=opportunity.setup,
            regime=opportunity.regime,
            snapshots=tuple(decisions),
            trigger_path=path,
            fill_path=fill_path,
            attempt_hashes=tuple(a.record_hash for a in attempts),
            fill_hashes=tuple(digest("B_NATIVE_FILL", f.model_dump(mode="json")) for f in fills),
            policy_action_hashes=tuple(a.record_hash for a in actions),
            cost_hash=run.cost.record_hash,
            net_cash=cash,
            net_r=cash / risk if cash is not None else None,
            fee_cash=sum((f.fee for f in fills), Decimal(0)),
            funding_cash=sum((c.amount for c in relevant if c.kind == "FUNDING"), Decimal(0))
            if funding_complete or not funding_applicable
            else None,
            outstanding_size=abs(state["position"]),
            limitations=tuple(sorted(limitations)),
            terminal="UNFINISHED"
            if state["position"]
            else "COMPLETE"
            if fills
            else "NO_SUBMIT"
            if state["no_submit"]
            else "NONFILL"
            if decisions[-1].decision == "TAKE"
            else "SUPPRESSED",
            attempts=tuple(attempts),
            fills=tuple(fills),
            actions=tuple(actions),
            cashflows=relevant,
        )
    finally:
        engine.dispose()


def replay(
    run: ResearchRunSpec,
    datasets: tuple[DatasetManifest, ...],
    rows: tuple[Observation, ...],
    roster: tuple[Opportunity, ...],
    candidates: tuple[CandidatePlan, ...],
    frames: tuple[ContextFrame, ...],
    ledger: TrialLedger,
    blocks: BlockPlan,
    visibility: VisibilityPolicy,
    *,
    events: tuple[AdmittedEvent, ...],
    instruments: dict[str, object],
    execution: ExecutionModelConfig,
    cashflows: tuple[CashFlow, ...] = (),
    funding_complete: bool,
    funding_applicable: bool,
) -> ReplayBundle:
    validate_inputs(run, datasets, rows, roster, candidates, frames, ledger, blocks, visibility)
    if len(frames) > run.max_observations or len(roster) > run.max_observations:
        raise ValueError("bounded frames/roster exceeded")
    results: list[CandidateResult] = []
    pairs: list[Pair] = []
    counterfactuals: list[CounterfactualPathRef] = []
    for opportunity in roster:
        selected = tuple(f for f in frames if f.opportunity_hash == opportunity.record_hash)
        local_events = tuple(e for e in events if e.source.market_id == opportunity.market_id)
        instrument = instruments[opportunity.market_id]
        local = tuple(
            _native_candidate(
                run,
                opportunity,
                candidate,
                rows,
                selected,
                local_events,
                instrument,
                execution,
                cashflows,
                funding_complete,
                funding_applicable,
            )
            for candidate in candidates
        )
        results.extend(local)
        pairs.extend(pair(local[0], row) for row in local[1:])
        for candidate, observed in zip(candidates, local, strict=True):
            if observed.snapshots[0].decision in {"WAIT", "PASS", "BLOCKED", "NOT_EVALUABLE"}:
                scenario = _native_candidate(
                    run,
                    opportunity,
                    candidate,
                    rows,
                    selected,
                    local_events,
                    instrument,
                    execution,
                    cashflows,
                    funding_complete,
                    funding_applicable,
                    counterfactual=True,
                )
                counterfactuals.append(
                    CounterfactualPathRef.create(
                        version="B_COUNTERFACTUAL_V1",
                        snapshot_hash=observed.snapshots[0].record_hash,
                        scenario="REGISTERED_REFERENCE_TIME_NATIVE_TAKE",
                        cost_hash=run.cost.record_hash,
                        result=scenario,
                        status=scenario.trigger_path.status,
                        reason="SAME_MODEL_REFERENCE_TIME; NO_OPTIMAL_FUTURE_ENTRY",
                    )
                )
    artifacts = tuple(
        sorted(
            (
                ("inputs", digest("B_INPUTS", tuple(r.record_hash for r in rows))),
                ("frames", digest("B_FRAMES", tuple(f.record_hash for f in frames))),
                ("results", digest("B_RESULTS", tuple(r.record_hash for r in results))),
                ("pairs", digest("B_PAIRS", tuple(p.record_hash for p in pairs))),
                (
                    "counterfactuals",
                    digest("B_COUNTERFACTUALS", tuple(c.record_hash for c in counterfactuals)),
                ),
            )
        )
    )
    return ReplayBundle.create(
        version="B_BUNDLE_V1",
        run_hash=run.record_hash,
        results=tuple(results),
        pairs=tuple(pairs),
        artifacts=artifacts,
        fingerprint=bundle_fingerprint(run.record_hash, artifacts),
        counterfactuals=tuple(counterfactuals),
    )
