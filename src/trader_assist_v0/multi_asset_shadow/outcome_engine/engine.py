"""Deterministic, on-demand 1m outcome orchestration for Formal Shadow plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from itertools import groupby

from .models import (
    ONE_MINUTE_MS,
    OUTCOME_HORIZONS_MINUTES,
    AdmissionStatus,
    BarConflict,
    FailedBreakoutResearch,
    FormalShadowOutcome,
    FormalShadowView,
    HorizonMetrics,
    MaturityStatus,
    OneMinuteBar,
    OneMinuteProvider,
    OutcomeEngineError,
    OutcomeSink,
    OutcomeTransitionView,
    PathEvaluation,
    PathPrimaryResult,
    ReclaimStatus,
    ReverseHorizonMetrics,
    SetupFamily,
    ShadowState,
    Side,
    TransitionKind,
)

_EXTENDING_TRANSITIONS = frozenset(
    {TransitionKind.ACCEPTED_REENTRY, TransitionKind.FAILED_BREAKOUT}
)


@dataclass
class _OutcomeState:
    view: FormalShadowView
    transitions: dict[str, OutcomeTransitionView] = field(default_factory=dict)
    forced_detached: bool = False


def _floor_minute(value: int) -> int:
    return value - value % ONE_MINUTE_MS


def _elapsed_end(*, start_ms: int, end_ms: int, as_of_ms: int) -> int:
    if as_of_ms <= start_ms:
        return start_ms
    return min(end_ms, _floor_minute(as_of_ms))


def _expected_opens(start_ms: int, end_ms: int) -> range:
    return range(start_ms, end_ms, ONE_MINUTE_MS)


def _favorable_adverse(
    *, side: Side, entry: Decimal, bars: tuple[OneMinuteBar, ...]
) -> tuple[Decimal | None, Decimal | None]:
    if not bars:
        return None, None
    if side is Side.LONG:
        favorable = max(Decimal(), max(bar.high for bar in bars) - entry)
        adverse = max(Decimal(), entry - min(bar.low for bar in bars))
    else:
        favorable = max(Decimal(), entry - min(bar.low for bar in bars))
        adverse = max(Decimal(), max(bar.high for bar in bars) - entry)
    return favorable, adverse


def _profit_path_statistics(
    *, side: Side, entry: Decimal, bars: tuple[OneMinuteBar, ...]
) -> tuple[Decimal, bool]:
    """Measure giveback and entry return without inventing same-bar ordering.

    A favorable extreme from a prior closed bar, or the current bar's open, is
    authoritative before the current high/low.  An otherwise ambiguous
    same-bar high/low sequence cannot establish a profit-then-return path.
    """
    prior_peak_favorable = Decimal()
    max_giveback = Decimal()
    returned_to_entry = False
    for bar in bars:
        if side is Side.LONG:
            opening_favorable = max(Decimal(), bar.open - entry)
            favorable = max(Decimal(), bar.high - entry)
            worst_later_price = bar.low
            crosses_entry = bar.low <= entry
        else:
            opening_favorable = max(Decimal(), entry - bar.open)
            favorable = max(Decimal(), entry - bar.low)
            worst_later_price = bar.high
            crosses_entry = bar.high >= entry

        established_peak = max(prior_peak_favorable, opening_favorable)
        if established_peak > 0:
            retained_favorable = (
                max(Decimal(), worst_later_price - entry)
                if side is Side.LONG
                else max(Decimal(), entry - worst_later_price)
            )
            giveback = established_peak - min(established_peak, retained_favorable)
            max_giveback = max(max_giveback, giveback)
            returned_to_entry = returned_to_entry or crosses_entry
        prior_peak_favorable = max(established_peak, favorable)
    return max_giveback, returned_to_entry


class OutcomeEngine:
    """On-demand path manager with no strategy, account, or write authority."""

    def __init__(
        self,
        *,
        provider: OneMinuteProvider | None = None,
        sink: OutcomeSink | None = None,
    ) -> None:
        self.provider = provider
        self.sink = sink
        self._states: dict[str, _OutcomeState] = {}
        self._bars: dict[str, dict[int, OneMinuteBar]] = {}
        self._conflicts: dict[tuple[str, int], set[str]] = {}
        self._subscribed_markets: set[str] = set()
        self._last_saved: dict[str, FormalShadowOutcome] = {}

    @property
    def attached_shadow_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._states))

    @property
    def subscription_requirements(self) -> tuple[str, ...]:
        return tuple(sorted(self._subscribed_markets))

    def required_window(self, shadow_order_id: str) -> tuple[int, int]:
        state = self._state(shadow_order_id)
        return state.view.outcome_start_ms, self._required_end(state)

    def attach(
        self,
        view: FormalShadowView,
        *,
        now_ms: int,
        recover: bool = True,
    ) -> bool:
        """Attach one active Formal Shadow plan; WATCH never starts 1m."""
        self._validate_now(now_ms)
        if view.state is not ShadowState.FORMAL_SHADOW_PLAN or not view.active:
            return False
        existing = self._states.get(view.shadow_order_id)
        if existing is not None:
            if existing.view != view:
                raise OutcomeEngineError("shadow_order_id has conflicting Formal Shadow views")
            self._synchronize_subscriptions(now_ms)
            return False
        self._states[view.shadow_order_id] = _OutcomeState(view=view)
        self._bars.setdefault(view.market_id, {})
        self._synchronize_subscriptions(now_ms)
        if recover:
            self.recover(now_ms=now_ms, shadow_order_ids=(view.shadow_order_id,))
        return True

    def admit_transition(
        self,
        transition: OutcomeTransitionView,
        *,
        now_ms: int,
        recover: bool = True,
    ) -> bool:
        """Attach an existing transition and extend research retention if required."""
        self._validate_now(now_ms)
        state = self._state(transition.shadow_order_id)
        if transition.market_id != state.view.market_id:
            raise OutcomeEngineError("transition market does not match Formal Shadow")
        if transition.occurred_at_ms < state.view.outcome_start_ms:
            raise OutcomeEngineError("transition predates the Formal Shadow outcome")
        if transition.occurred_at_ms > now_ms:
            raise OutcomeEngineError("transition cannot be admitted before it occurs")
        if transition.kind in _EXTENDING_TRANSITIONS and (
            state.view.setup_family is not SetupFamily.BREAKOUT_RETEST
        ):
            raise OutcomeEngineError("breakout transition cannot extend a non-breakout plan")
        existing = state.transitions.get(transition.transition_id)
        if existing is not None:
            if existing != transition:
                raise OutcomeEngineError("transition_id has conflicting evidence")
            return False
        state.transitions[transition.transition_id] = transition
        self._synchronize_subscriptions(now_ms)
        if recover:
            self.recover(now_ms=now_ms, shadow_order_ids=(transition.shadow_order_id,))
        return True

    def detach(self, shadow_order_id: str, *, now_ms: int) -> bool:
        """Stop future streaming for one outcome without deleting its evidence."""
        self._validate_now(now_ms)
        state = self._state(shadow_order_id)
        if state.forced_detached:
            return False
        state.forced_detached = True
        self._synchronize_subscriptions(now_ms)
        return True

    def admit_bar(self, bar: OneMinuteBar) -> AdmissionStatus:
        """Admit one closed bar idempotently and freeze conflicts as evidence."""
        relevant = tuple(
            state
            for state in self._states.values()
            if state.view.market_id == bar.market_id
            and state.view.outcome_start_ms <= bar.open_time_ms < self._required_end(state)
        )
        if not relevant:
            return AdmissionStatus.OUTSIDE_REQUIRED_WINDOW
        market_bars = self._bars.setdefault(bar.market_id, {})
        existing = market_bars.get(bar.open_time_ms)
        if existing is None:
            market_bars[bar.open_time_ms] = bar
            return AdmissionStatus.ADMITTED
        if existing.canonical_hash == bar.canonical_hash:
            return AdmissionStatus.DUPLICATE
        conflict_key = (bar.market_id, bar.open_time_ms)
        self._conflicts.setdefault(conflict_key, set()).update(
            (existing.canonical_hash, bar.canonical_hash)
        )
        return AdmissionStatus.CONFLICT

    def recover(
        self,
        *,
        now_ms: int,
        shadow_order_ids: tuple[str, ...] | None = None,
    ) -> tuple[tuple[str, int, int], ...]:
        """Request REST backfill for elapsed missing intervals, coalesced by market."""
        self._validate_now(now_ms)
        if self.provider is None:
            return ()
        selected = (
            tuple(self._states.values())
            if shadow_order_ids is None
            else tuple(self._state(identity) for identity in shadow_order_ids)
        )
        missing_by_market: dict[str, set[int]] = {}
        for state in selected:
            if state.forced_detached:
                continue
            view = state.view
            end_ms = _elapsed_end(
                start_ms=view.outcome_start_ms,
                end_ms=self._required_end(state),
                as_of_ms=now_ms,
            )
            admitted = self._bars.setdefault(view.market_id, {})
            missing_by_market.setdefault(view.market_id, set()).update(
                point
                for point in _expected_opens(view.outcome_start_ms, end_ms)
                if point not in admitted
            )
        requests: list[tuple[str, int, int]] = []
        for market_id in sorted(missing_by_market):
            points = sorted(missing_by_market[market_id])
            grouped_points = groupby(
                enumerate(points),
                lambda item: item[1] - item[0] * ONE_MINUTE_MS,
            )
            for _, grouped in grouped_points:
                block = [item[1] for item in grouped]
                start_ms, end_ms = block[0], block[-1] + ONE_MINUTE_MS
                requests.append((market_id, start_ms, end_ms))
                recovered = self.provider.backfill_1m(
                    market_id=market_id, start_ms=start_ms, end_ms=end_ms
                )
                for bar in recovered:
                    if bar.market_id != market_id or not start_ms <= bar.open_time_ms < end_ms:
                        raise OutcomeEngineError("backfill returned a bar outside its request")
                    self.admit_bar(bar)
        return tuple(requests)

    def evaluate(self, shadow_order_id: str, *, as_of_ms: int) -> FormalShadowOutcome:
        self._validate_now(as_of_ms)
        state = self._state(shadow_order_id)
        view = state.view
        required_end = self._required_end(state)
        horizons = tuple(
            self._horizon(state, minutes=minutes, as_of_ms=as_of_ms)
            for minutes in OUTCOME_HORIZONS_MINUTES
        )
        original_status = self._window_status(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=view.original_deadline_ms,
            as_of_ms=as_of_ms,
        )
        original_bars = self._usable_bars(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=view.original_deadline_ms,
            as_of_ms=as_of_ms,
        )
        path = self._evaluate_path(view, original_bars)
        overall_status = self._window_status(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=required_end,
            as_of_ms=as_of_ms,
        )
        if state.forced_detached and overall_status is MaturityStatus.PENDING:
            overall_status = MaturityStatus.DETACHED
        research = self._failed_breakout_research(state, as_of_ms=as_of_ms)
        time_to_retest = self._time_to_retest(view, original_bars)
        return_inside = bool(research and research.first_return_inside_range_time_ms is not None)
        # A gapped/conflicted original path cannot assert an observed path fact,
        # but any existing transition remains preserved inside research.
        if original_status in {MaturityStatus.GAPPED, MaturityStatus.CONFLICTED}:
            path = self._evaluate_path(view, ())
            time_to_retest = None
            if not self._has_existing_failure_transition(state):
                return_inside = False
        return FormalShadowOutcome(
            shadow_order_id=view.shadow_order_id,
            market_id=view.market_id,
            evaluated_at_ms=as_of_ms,
            required_start_ms=view.outcome_start_ms,
            original_deadline_ms=view.original_deadline_ms,
            required_end_ms=required_end,
            path_maturity_status=overall_status,
            unresolved=overall_status is not MaturityStatus.MATURE,
            horizons=horizons,
            path=path,
            time_to_retest_ms=time_to_retest,
            return_inside_range=return_inside,
            failed_breakout=bool(research and research.failed_breakout),
            research=research,
            conflicts=self._state_conflicts(state),
        )

    def tick(self, *, now_ms: int) -> tuple[FormalShadowOutcome, ...]:
        """Recover gaps, emit changed snapshots, and detach completed streams."""
        self._validate_now(now_ms)
        self.recover(now_ms=now_ms)
        outcomes = tuple(
            self.evaluate(identity, as_of_ms=now_ms) for identity in sorted(self._states)
        )
        if self.sink is not None:
            for outcome in outcomes:
                if self._last_saved.get(outcome.shadow_order_id) != outcome:
                    self.sink.save_outcome(outcome)
                    self._last_saved[outcome.shadow_order_id] = outcome
        self._synchronize_subscriptions(now_ms)
        return outcomes

    @classmethod
    def reconstruct(
        cls,
        *,
        shadows: tuple[FormalShadowView, ...],
        transitions: tuple[OutcomeTransitionView, ...],
        bars: tuple[OneMinuteBar, ...],
        now_ms: int,
        provider: OneMinuteProvider | None = None,
        sink: OutcomeSink | None = None,
        recover: bool = False,
    ) -> OutcomeEngine:
        """Rebuild the same state from stable views, independent of input order."""
        engine = cls(provider=provider, sink=sink)
        for view in sorted(shadows, key=lambda item: item.shadow_order_id):
            engine.attach(view, now_ms=now_ms, recover=False)
        for transition in sorted(
            transitions,
            key=lambda item: (item.occurred_at_ms, item.transition_id),
        ):
            engine.admit_transition(transition, now_ms=now_ms, recover=False)
        for bar in sorted(
            bars,
            key=lambda item: (item.market_id, item.open_time_ms, item.canonical_hash),
        ):
            engine.admit_bar(bar)
        engine._synchronize_subscriptions(now_ms)
        if recover:
            engine.recover(now_ms=now_ms)
        return engine

    def _state(self, shadow_order_id: str) -> _OutcomeState:
        try:
            return self._states[shadow_order_id]
        except KeyError as exc:
            raise OutcomeEngineError("Formal Shadow is not attached") from exc

    @staticmethod
    def _validate_now(now_ms: int) -> None:
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
            raise OutcomeEngineError("time must be a non-negative integer millisecond")

    def _required_end(self, state: _OutcomeState) -> int:
        end_ms = state.view.original_deadline_ms
        if state.view.setup_family is SetupFamily.BREAKOUT_RETEST:
            for transition in state.transitions.values():
                if transition.kind in _EXTENDING_TRANSITIONS:
                    end_ms = max(end_ms, transition.occurred_at_ms + 120 * ONE_MINUTE_MS)
        return end_ms

    def _synchronize_subscriptions(self, now_ms: int) -> None:
        required = {
            state.view.market_id
            for state in self._states.values()
            if not state.forced_detached and now_ms < self._required_end(state)
        }
        for market_id in sorted(required - self._subscribed_markets):
            if self.provider is not None:
                self.provider.subscribe_1m(market_id=market_id)
        for market_id in sorted(self._subscribed_markets - required):
            if self.provider is not None:
                self.provider.unsubscribe_1m(market_id=market_id)
        self._subscribed_markets = required

    def _state_conflicts(self, state: _OutcomeState) -> tuple[BarConflict, ...]:
        start_ms, end_ms = state.view.outcome_start_ms, self._required_end(state)
        values: list[BarConflict] = []
        for (market_id, open_ms), hashes in self._conflicts.items():
            if market_id != state.view.market_id or not start_ms <= open_ms < end_ms:
                continue
            ordered = sorted(hashes)
            values.extend(
                BarConflict(
                    market_id=market_id,
                    open_time_ms=open_ms,
                    retained_hash=ordered[0],
                    conflicting_hash=conflicting_hash,
                )
                for conflicting_hash in ordered[1:]
            )
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.open_time_ms,
                    item.retained_hash,
                    item.conflicting_hash,
                ),
            )
        )

    def _window_status(
        self,
        state: _OutcomeState,
        *,
        start_ms: int,
        end_ms: int,
        as_of_ms: int,
    ) -> MaturityStatus:
        elapsed_end = _elapsed_end(start_ms=start_ms, end_ms=end_ms, as_of_ms=as_of_ms)
        if any(
            market_id == state.view.market_id and start_ms <= open_ms < elapsed_end
            for market_id, open_ms in self._conflicts
        ):
            return MaturityStatus.CONFLICTED
        admitted = self._bars.get(state.view.market_id, {})
        if any(point not in admitted for point in _expected_opens(start_ms, elapsed_end)):
            return MaturityStatus.GAPPED
        if as_of_ms < end_ms:
            return MaturityStatus.PENDING
        if any(point not in admitted for point in _expected_opens(start_ms, end_ms)):
            return MaturityStatus.GAPPED
        return MaturityStatus.MATURE

    def _usable_bars(
        self,
        state: _OutcomeState,
        *,
        start_ms: int,
        end_ms: int,
        as_of_ms: int,
    ) -> tuple[OneMinuteBar, ...]:
        status = self._window_status(state, start_ms=start_ms, end_ms=end_ms, as_of_ms=as_of_ms)
        if status in {MaturityStatus.GAPPED, MaturityStatus.CONFLICTED}:
            return ()
        elapsed_end = _elapsed_end(start_ms=start_ms, end_ms=end_ms, as_of_ms=as_of_ms)
        admitted = self._bars.get(state.view.market_id, {})
        return tuple(admitted[point] for point in _expected_opens(start_ms, elapsed_end))

    def _horizon(self, state: _OutcomeState, *, minutes: int, as_of_ms: int) -> HorizonMetrics:
        view = state.view
        end_ms = view.outcome_start_ms + minutes * ONE_MINUTE_MS
        maturity = self._window_status(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=end_ms,
            as_of_ms=as_of_ms,
        )
        bars = self._usable_bars(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=end_ms,
            as_of_ms=as_of_ms,
        )
        mfe, mae = _favorable_adverse(side=view.side, entry=view.planned_entry, bars=bars)
        path = self._evaluate_path(view, bars)
        return HorizonMetrics(
            horizon_minutes=minutes,
            maturity=maturity,
            window_end_ms=end_ms,
            mfe=mfe,
            mae=mae,
            mfe_atr=None if mfe is None else mfe / view.atr,
            mae_atr=None if mae is None else mae / view.atr,
            one_r_hit=path.one_r_hit,
            one_and_half_r_hit=path.one_and_half_r_hit,
            two_r_hit=path.two_r_hit,
            stop_hit=path.stop_hit,
        )

    @staticmethod
    def _evaluate_path(view: FormalShadowView, bars: tuple[OneMinuteBar, ...]) -> PathEvaluation:
        primary = PathPrimaryResult.NO_HIT
        stop_hit = tp1_hit = tp2_hit = False
        stop_time = tp1_time = tp2_time = time_to_one = None
        one_hit = one_half_hit = two_hit = False
        ambiguous: list[int] = []
        max_before_stop = Decimal()
        one_level = view.r_level(Decimal("1"))
        one_half_level = view.r_level(Decimal("1.5"))
        two_level = view.r_level(Decimal("2"))
        max_profit_giveback, return_to_entry_after_profit = _profit_path_statistics(
            side=view.side,
            entry=view.planned_entry,
            bars=bars,
        )
        for bar in bars:
            if view.side is Side.LONG:
                bar_stop = bar.low <= view.stop
                bar_tp1 = bar.high >= view.tp1
                bar_tp2 = view.tp2 is not None and bar.high >= view.tp2
                bar_one = bar.high >= one_level
                bar_one_half = bar.high >= one_half_level
                bar_two = bar.high >= two_level
                favorable = max(Decimal(), bar.high - view.planned_entry)
            else:
                bar_stop = bar.high >= view.stop
                bar_tp1 = bar.low <= view.tp1
                bar_tp2 = view.tp2 is not None and bar.low <= view.tp2
                bar_one = bar.low <= one_level
                bar_one_half = bar.low <= one_half_level
                bar_two = bar.low <= two_level
                favorable = max(Decimal(), view.planned_entry - bar.low)
            if bar_stop and (bar_tp1 or bar_tp2):
                ambiguous.append(bar.open_time_ms)
                stop_hit = True
                stop_time = bar.close_time_ms
                if primary is PathPrimaryResult.NO_HIT:
                    primary = PathPrimaryResult.STOP_FIRST
                break
            if bar_stop:
                stop_hit = True
                stop_time = bar.close_time_ms
                if primary is PathPrimaryResult.NO_HIT:
                    primary = PathPrimaryResult.STOP_FIRST
                break
            if bar_tp1 and not tp1_hit:
                tp1_hit, tp1_time = True, bar.close_time_ms
                if primary is PathPrimaryResult.NO_HIT:
                    primary = PathPrimaryResult.TP_FIRST
            if bar_tp2 and not tp2_hit:
                tp2_hit, tp2_time = True, bar.close_time_ms
                if primary is PathPrimaryResult.NO_HIT:
                    primary = PathPrimaryResult.TP_FIRST
            if bar_one and not one_hit:
                one_hit = True
                time_to_one = bar.close_time_ms - view.outcome_start_ms
            one_half_hit = one_half_hit or bar_one_half
            two_hit = two_hit or bar_two
            max_before_stop = max(max_before_stop, favorable)
        return PathEvaluation(
            primary_result=primary,
            ambiguous_path=bool(ambiguous),
            ambiguous_bar_open_times=tuple(ambiguous),
            stop_hit=stop_hit,
            stop_hit_time_ms=stop_time,
            tp1_hit=tp1_hit,
            tp1_hit_time_ms=tp1_time,
            tp2_hit=tp2_hit,
            tp2_hit_time_ms=tp2_time,
            one_r_hit=one_hit,
            one_and_half_r_hit=one_half_hit,
            two_r_hit=two_hit,
            time_to_one_r_ms=time_to_one,
            max_mfe_before_stop=max_before_stop,
            max_profit_giveback=max_profit_giveback,
            return_to_entry_after_profit=return_to_entry_after_profit,
        )

    @staticmethod
    def _time_to_retest(view: FormalShadowView, bars: tuple[OneMinuteBar, ...]) -> int | None:
        if view.setup_family is not SetupFamily.BREAKOUT_RETEST:
            return None
        if view.zone_low is None or view.zone_high is None:
            return None
        for bar in bars:
            touched = (
                bar.low <= view.zone_high if view.side is Side.LONG else bar.high >= view.zone_low
            )
            if touched:
                return bar.close_time_ms - view.outcome_start_ms
        return None

    @staticmethod
    def _transitions(
        state: _OutcomeState, *kinds: TransitionKind
    ) -> tuple[OutcomeTransitionView, ...]:
        allowed = frozenset(kinds)
        return tuple(
            sorted(
                (item for item in state.transitions.values() if item.kind in allowed),
                key=lambda item: (item.occurred_at_ms, item.transition_id),
            )
        )

    def _has_existing_failure_transition(self, state: _OutcomeState) -> bool:
        return bool(self._transitions(state, *_EXTENDING_TRANSITIONS))

    def _failed_breakout_research(
        self, state: _OutcomeState, *, as_of_ms: int
    ) -> FailedBreakoutResearch | None:
        view = state.view
        if view.setup_family is not SetupFamily.BREAKOUT_RETEST:
            return None
        original_bars = self._usable_bars(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=view.original_deadline_ms,
            as_of_ms=as_of_ms,
        )
        return_transitions = self._transitions(state, TransitionKind.RETURN_INSIDE_RANGE)
        accepted_transitions = self._transitions(state, TransitionKind.ACCEPTED_REENTRY)
        failure_transitions = self._transitions(state, TransitionKind.FAILED_BREAKOUT)
        first_return_time: int | None = (
            return_transitions[0].occurred_at_ms if return_transitions else None
        )
        return_depth: Decimal | None = None
        if view.zone_low is not None and view.zone_high is not None:
            for bar in original_bars:
                returned = (
                    bar.close <= view.zone_high
                    if view.side is Side.LONG
                    else bar.close >= view.zone_low
                )
                if returned and first_return_time is None:
                    first_return_time = bar.close_time_ms
                    return_depth = (
                        max(Decimal(), view.zone_high - bar.close) / view.atr
                        if view.side is Side.LONG
                        else max(Decimal(), bar.close - view.zone_low) / view.atr
                    )
            if return_depth is None and return_transitions:
                reference = return_transitions[0].reference_price
                if reference is not None:
                    return_depth = (
                        max(Decimal(), view.zone_high - reference) / view.atr
                        if view.side is Side.LONG
                        else max(Decimal(), reference - view.zone_low) / view.atr
                    )
        accepted_time = accepted_transitions[0].occurred_at_ms if accepted_transitions else None
        failed = accepted_time is not None or bool(failure_transitions)
        pre_reentry_cutoff = first_return_time or accepted_time
        pre_reentry = (
            tuple(bar for bar in original_bars if bar.close_time_ms < pre_reentry_cutoff)
            if pre_reentry_cutoff is not None
            else original_bars
        )
        mfe_before, _ = _favorable_adverse(
            side=view.side, entry=view.planned_entry, bars=pre_reentry
        )
        if view.zone_low is None or view.zone_high is None:
            outside_bars = 0
        else:
            outside_bars = sum(
                1
                for bar in pre_reentry
                if (
                    bar.close > view.zone_high
                    if view.side is Side.LONG
                    else bar.close < view.zone_low
                )
            )
        time_outside = outside_bars * ONE_MINUTE_MS
        attempts = self._transitions(state, TransitionKind.RECLAIM_ATTEMPT)
        succeeded = self._transitions(state, TransitionKind.RECLAIM_SUCCEEDED)
        failed_reclaim = self._transitions(state, TransitionKind.RECLAIM_FAILED)
        if succeeded and failed_reclaim:
            reclaim = (
                ReclaimStatus.SUCCEEDED
                if succeeded[0].occurred_at_ms < failed_reclaim[0].occurred_at_ms
                else ReclaimStatus.FAILED
            )
        elif succeeded:
            reclaim = ReclaimStatus.SUCCEEDED
        elif failed_reclaim or failure_transitions:
            reclaim = ReclaimStatus.FAILED
        elif failed:
            reclaim = ReclaimStatus.UNRESOLVED
        else:
            reclaim = ReclaimStatus.NOT_APPLICABLE
        failure_anchors = self._transitions(state, TransitionKind.FAILED_BREAKOUT)
        accepted_anchors = self._transitions(state, TransitionKind.ACCEPTED_REENTRY)
        anchor = (
            failure_anchors[0]
            if failure_anchors
            else accepted_anchors[0]
            if accepted_anchors
            else None
        )
        reverse_entry = self._transition_reference(state, anchor) if anchor is not None else None
        required_bars = self._usable_bars(
            state,
            start_ms=view.outcome_start_ms,
            end_ms=self._required_end(state),
            as_of_ms=as_of_ms,
        )
        after_reentry = (
            tuple(bar for bar in required_bars if bar.open_time_ms >= accepted_time)
            if accepted_time is not None
            else ()
        )
        _, mae_after = _favorable_adverse(
            side=view.side, entry=view.planned_entry, bars=after_reentry
        )
        reverse = (
            self._reverse_horizons(
                state,
                anchor_time_ms=anchor.occurred_at_ms,
                entry=reverse_entry,
                as_of_ms=as_of_ms,
            )
            if anchor is not None and reverse_entry is not None
            else ()
        )
        original_path = self._evaluate_path(view, original_bars)
        return FailedBreakoutResearch(
            failed_breakout=failed,
            first_return_inside_range_time_ms=first_return_time,
            return_inside_range_depth_atr=return_depth,
            accepted_reentry_time_ms=accepted_time,
            mfe_before_first_reentry=mfe_before,
            bars_outside_zone=outside_bars,
            time_outside_zone_ms=time_outside,
            reclaim_attempt_count=len(attempts),
            reclaim_status=reclaim,
            mae_after_reentry=mae_after,
            original_stop=view.stop,
            original_r=view.risk_distance,
            original_stop_hit=original_path.stop_hit,
            reverse_anchor_time_ms=None if anchor is None else anchor.occurred_at_ms,
            reverse_entry=reverse_entry,
            hypothetical_reverse=reverse,
        )

    def _transition_reference(
        self, state: _OutcomeState, transition: OutcomeTransitionView
    ) -> Decimal | None:
        if transition.reference_price is not None:
            return transition.reference_price
        candidates = (
            bar
            for bar in self._bars.get(state.view.market_id, {}).values()
            if bar.close_time_ms <= transition.occurred_at_ms
        )
        latest = max(candidates, key=lambda bar: bar.close_time_ms, default=None)
        return None if latest is None else latest.close

    def _reverse_horizons(
        self,
        state: _OutcomeState,
        *,
        anchor_time_ms: int,
        entry: Decimal,
        as_of_ms: int,
    ) -> tuple[ReverseHorizonMetrics, ...]:
        side = Side.SHORT if state.view.side is Side.LONG else Side.LONG
        values: list[ReverseHorizonMetrics] = []
        for minutes in OUTCOME_HORIZONS_MINUTES:
            end_ms = anchor_time_ms + minutes * ONE_MINUTE_MS
            maturity = self._window_status(
                state,
                start_ms=anchor_time_ms,
                end_ms=end_ms,
                as_of_ms=as_of_ms,
            )
            bars = self._usable_bars(
                state,
                start_ms=anchor_time_ms,
                end_ms=end_ms,
                as_of_ms=as_of_ms,
            )
            mfe, mae = _favorable_adverse(side=side, entry=entry, bars=bars)
            values.append(
                ReverseHorizonMetrics(
                    horizon_minutes=minutes,
                    maturity=maturity,
                    window_end_ms=end_ms,
                    mfe=mfe,
                    mae=mae,
                    mfe_atr=None if mfe is None else mfe / state.view.atr,
                    mae_atr=None if mae is None else mae / state.view.atr,
                )
            )
        return tuple(values)
