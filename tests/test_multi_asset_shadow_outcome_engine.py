from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    ONE_MINUTE_MS,
    AdmissionStatus,
    FormalShadowOutcome,
    FormalShadowView,
    MaturityStatus,
    OneMinuteBar,
    OutcomeEngine,
    OutcomeTransitionView,
    PathPrimaryResult,
    ReclaimStatus,
    SetupFamily,
    ShadowState,
    Side,
    TransitionKind,
)


@dataclass
class FakeProvider:
    inventory: tuple[OneMinuteBar, ...] = ()
    subscriptions: list[str] = field(default_factory=list)
    unsubscriptions: list[str] = field(default_factory=list)
    backfills: list[tuple[str, int, int]] = field(default_factory=list)

    def subscribe_1m(self, *, market_id: str) -> None:
        self.subscriptions.append(market_id)

    def unsubscribe_1m(self, *, market_id: str) -> None:
        self.unsubscriptions.append(market_id)

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        self.backfills.append((market_id, start_ms, end_ms))
        return tuple(
            bar
            for bar in self.inventory
            if bar.market_id == market_id and start_ms <= bar.open_time_ms < end_ms
        )


@dataclass
class FakeSink:
    outcomes: list[FormalShadowOutcome] = field(default_factory=list)

    def save_outcome(self, outcome: FormalShadowOutcome) -> None:
        self.outcomes.append(outcome)


def _view(
    side: Side = Side.LONG,
    *,
    identity: str = "shadow-1",
    market: str = "market-1",
    setup: SetupFamily = SetupFamily.BREAKOUT_RETEST,
    state: ShadowState = ShadowState.FORMAL_SHADOW_PLAN,
    active: bool = True,
) -> FormalShadowView:
    if side is Side.LONG:
        stop, tp1, tp2 = Decimal("95"), Decimal("105"), Decimal("110")
    else:
        stop, tp1, tp2 = Decimal("105"), Decimal("95"), Decimal("90")
    return FormalShadowView(
        shadow_order_id=identity,
        market_id=market,
        side=side,
        setup_family=setup,
        outcome_start_ms=0,
        planned_entry=Decimal("100"),
        stop=stop,
        tp1=tp1,
        tp2=tp2,
        atr=Decimal("2"),
        zone_low=Decimal("95") if setup is SetupFamily.BREAKOUT_RETEST else None,
        zone_high=Decimal("100") if setup is SetupFamily.BREAKOUT_RETEST else None,
        state=state,
        active=active,
    )


def _bar(
    minute: int,
    *,
    market: str = "market-1",
    open_: str = "100",
    high: str = "101",
    low: str = "99",
    close: str = "100",
    source: str = "PUBLIC_1M",
) -> OneMinuteBar:
    return OneMinuteBar.create(
        market_id=market,
        open_time_ms=minute * ONE_MINUTE_MS,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        source_id=source,
    )


def _admit(engine: OutcomeEngine, bars: tuple[OneMinuteBar, ...]) -> None:
    for bar in bars:
        assert engine.admit_bar(bar) is AdmissionStatus.ADMITTED


@pytest.mark.parametrize(
    ("side", "first", "second"),
    (
        (
            Side.LONG,
            _bar(0, high="106", low="96", close="104"),
            _bar(1, high="104", low="94", close="96"),
        ),
        (
            Side.SHORT,
            _bar(0, high="104", low="94", close="96"),
            _bar(1, high="106", low="96", close="104"),
        ),
    ),
)
def test_long_and_short_tp_first_freeze_before_later_stop(
    side: Side, first: OneMinuteBar, second: OneMinuteBar
) -> None:
    engine = OutcomeEngine()
    view = _view(side)
    engine.attach(view, now_ms=0, recover=False)
    _admit(engine, (first, second))

    outcome = engine.evaluate(view.shadow_order_id, as_of_ms=2 * ONE_MINUTE_MS)

    assert outcome.path.primary_result is PathPrimaryResult.TP_FIRST
    assert outcome.path.tp1_hit is True
    assert outcome.path.stop_hit is True
    assert outcome.path.time_to_one_r_ms == ONE_MINUTE_MS


@pytest.mark.parametrize(
    ("side", "stop_bar"),
    (
        (Side.LONG, _bar(0, high="104", low="94", close="96")),
        (Side.SHORT, _bar(0, high="106", low="96", close="104")),
    ),
)
def test_long_and_short_stop_first(side: Side, stop_bar: OneMinuteBar) -> None:
    engine = OutcomeEngine()
    view = _view(side)
    engine.attach(view, now_ms=0, recover=False)
    _admit(engine, (stop_bar,))

    path = engine.evaluate(view.shadow_order_id, as_of_ms=ONE_MINUTE_MS).path

    assert path.primary_result is PathPrimaryResult.STOP_FIRST
    assert path.stop_hit is True
    assert path.tp1_hit is False
    assert path.ambiguous_path is False


def test_same_bar_stop_and_tp_is_ambiguous_and_conservatively_stop_first() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    _admit(engine, (_bar(0, high="106", low="94", close="100"),))

    path = engine.evaluate(view.shadow_order_id, as_of_ms=ONE_MINUTE_MS).path

    assert path.primary_result is PathPrimaryResult.STOP_FIRST
    assert path.ambiguous_path is True
    assert path.ambiguous_bar_open_times == (0,)
    assert path.stop_hit is True
    assert path.tp1_hit is False
    assert path.one_r_hit is False


def test_no_hit_mfe_mae_atr_normalization_and_30_60_120_maturity() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    bars = tuple(_bar(index, high="103", low="98", close="101") for index in range(120))
    _admit(engine, bars)

    at_30 = engine.evaluate(view.shadow_order_id, as_of_ms=30 * ONE_MINUTE_MS)
    assert tuple(item.maturity for item in at_30.horizons) == (
        MaturityStatus.MATURE,
        MaturityStatus.PENDING,
        MaturityStatus.PENDING,
    )
    assert at_30.horizons[0].mfe == Decimal("3")
    assert at_30.horizons[0].mae == Decimal("2")
    assert at_30.horizons[0].mfe_atr == Decimal("1.5")
    assert at_30.horizons[0].mae_atr == Decimal("1")

    at_120 = engine.evaluate(view.shadow_order_id, as_of_ms=120 * ONE_MINUTE_MS)
    assert all(item.maturity is MaturityStatus.MATURE for item in at_120.horizons)
    assert at_120.path.primary_result is PathPrimaryResult.NO_HIT
    assert at_120.path_maturity_status is MaturityStatus.MATURE


def test_missing_elapsed_minute_is_gapped_and_does_not_publish_metrics() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    _admit(engine, (_bar(0), _bar(2)))

    outcome = engine.evaluate(view.shadow_order_id, as_of_ms=3 * ONE_MINUTE_MS)

    assert outcome.path_maturity_status is MaturityStatus.GAPPED
    assert outcome.horizons[0].maturity is MaturityStatus.GAPPED
    assert outcome.horizons[0].mfe is None
    assert outcome.horizons[0].mae is None


def test_one_one_and_half_two_r_and_time_to_one_r() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    _admit(
        engine,
        (
            _bar(0, high="104", low="99", close="103"),
            _bar(1, open_="103", high="107.5", low="101", close="106"),
            _bar(2, open_="106", high="111", low="104", close="109"),
        ),
    )

    path = engine.evaluate(view.shadow_order_id, as_of_ms=3 * ONE_MINUTE_MS).path

    assert path.one_r_hit is True
    assert path.one_and_half_r_hit is True
    assert path.two_r_hit is True
    assert path.time_to_one_r_ms == 2 * ONE_MINUTE_MS
    assert path.max_mfe_before_stop == Decimal("11")


def test_rest_gap_recovery_requests_only_missing_contiguous_range() -> None:
    missing = _bar(2)
    provider = FakeProvider(inventory=(missing,))
    engine = OutcomeEngine(provider=provider)
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    _admit(engine, (_bar(0), _bar(1), _bar(3), _bar(4)))

    requests = engine.recover(now_ms=5 * ONE_MINUTE_MS)

    assert requests == (("market-1", 2 * ONE_MINUTE_MS, 3 * ONE_MINUTE_MS),)
    assert provider.backfills == list(requests)
    assert engine.admit_bar(missing) is AdmissionStatus.DUPLICATE


def test_required_window_rejects_unrelated_bar_and_incremental_path_updates() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)

    assert engine.required_window(view.shadow_order_id) == (0, 120 * ONE_MINUTE_MS)
    assert engine.admit_bar(_bar(120)) is AdmissionStatus.OUTSIDE_REQUIRED_WINDOW
    assert engine.admit_bar(_bar(0, high="104", low="99")) is AdmissionStatus.ADMITTED
    assert (
        engine.evaluate(view.shadow_order_id, as_of_ms=ONE_MINUTE_MS).path.primary_result
        is PathPrimaryResult.NO_HIT
    )
    assert engine.admit_bar(_bar(1, high="104", low="94")) is AdmissionStatus.ADMITTED
    assert (
        engine.evaluate(view.shadow_order_id, as_of_ms=2 * ONE_MINUTE_MS).path.primary_result
        is PathPrimaryResult.STOP_FIRST
    )


def test_duplicate_is_idempotent_and_conflict_fails_closed_with_evidence() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    first = _bar(0, close="100")
    conflict = _bar(0, high="102", close="101", source="REST_RECOVERY")

    assert engine.admit_bar(first) is AdmissionStatus.ADMITTED
    assert engine.admit_bar(first) is AdmissionStatus.DUPLICATE
    assert (
        engine.admit_bar(_bar(0, close="100", source="REST_RECOVERY")) is AdmissionStatus.DUPLICATE
    )
    assert (
        engine.admit_bar(_bar(0, open_="100.0", high="101.0", low="99.0", close="100.0"))
        is AdmissionStatus.DUPLICATE
    )
    assert engine.admit_bar(conflict) is AdmissionStatus.CONFLICT
    outcome = engine.evaluate(view.shadow_order_id, as_of_ms=ONE_MINUTE_MS)

    assert outcome.path_maturity_status is MaturityStatus.CONFLICTED
    assert outcome.horizons[0].maturity is MaturityStatus.CONFLICTED
    assert len(outcome.conflicts) == 1
    assert {outcome.conflicts[0].retained_hash, outcome.conflicts[0].conflicting_hash} == {
        first.canonical_hash,
        conflict.canonical_hash,
    }


def test_two_outcomes_same_market_share_subscription_until_last_detach() -> None:
    provider = FakeProvider()
    engine = OutcomeEngine(provider=provider)
    first = _view(identity="shadow-a")
    second = _view(identity="shadow-b")

    assert engine.attach(first, now_ms=0, recover=False) is True
    assert engine.attach(second, now_ms=0, recover=False) is True
    assert engine.attach(second, now_ms=0, recover=False) is False
    assert provider.subscriptions == ["market-1"]
    assert engine.subscription_requirements == ("market-1",)

    engine.detach(first.shadow_order_id, now_ms=ONE_MINUTE_MS)
    assert provider.unsubscriptions == []
    engine.detach(second.shadow_order_id, now_ms=ONE_MINUTE_MS)
    assert provider.unsubscriptions == ["market-1"]
    assert engine.subscription_requirements == ()


@pytest.mark.parametrize(
    ("state", "active"),
    (
        (ShadowState.WATCH, True),
        (ShadowState.FORMAL_SHADOW_PLAN, False),
    ),
)
def test_watch_or_inactive_plan_does_not_start_one_minute(state: ShadowState, active: bool) -> None:
    provider = FakeProvider()
    engine = OutcomeEngine(provider=provider)

    attached = engine.attach(_view(state=state, active=active), now_ms=0, recover=False)

    assert attached is False
    assert engine.attached_shadow_ids == ()
    assert provider.subscriptions == []
    assert provider.backfills == []


def test_failed_breakout_transition_extends_deadline_and_success_control_does_not() -> None:
    provider = FakeProvider()
    engine = OutcomeEngine(provider=provider)
    failed = _view(identity="failed")
    control = _view(identity="control", market="market-2")
    engine.attach(failed, now_ms=0, recover=False)
    engine.attach(control, now_ms=0, recover=False)
    engine.admit_transition(
        OutcomeTransitionView(
            transition_id="accepted",
            shadow_order_id=failed.shadow_order_id,
            market_id=failed.market_id,
            kind=TransitionKind.ACCEPTED_REENTRY,
            occurred_at_ms=90 * ONE_MINUTE_MS,
            reference_price=Decimal("99"),
        ),
        now_ms=90 * ONE_MINUTE_MS,
        recover=False,
    )

    assert engine.required_window("failed") == (0, 210 * ONE_MINUTE_MS)
    assert engine.required_window("control") == (0, 120 * ONE_MINUTE_MS)

    engine.tick(now_ms=120 * ONE_MINUTE_MS)
    assert provider.unsubscriptions == ["market-2"]
    assert engine.subscription_requirements == ("market-1",)
    engine.tick(now_ms=210 * ONE_MINUTE_MS)
    assert provider.unsubscriptions == ["market-2", "market-1"]


def test_accepted_reentry_and_hypothetical_reverse_research_metrics() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    transitions = (
        OutcomeTransitionView(
            transition_id="accepted",
            shadow_order_id=view.shadow_order_id,
            market_id=view.market_id,
            kind=TransitionKind.ACCEPTED_REENTRY,
            occurred_at_ms=3 * ONE_MINUTE_MS,
            reference_price=Decimal("99.8"),
        ),
        OutcomeTransitionView(
            transition_id="attempt-1",
            shadow_order_id=view.shadow_order_id,
            market_id=view.market_id,
            kind=TransitionKind.RECLAIM_ATTEMPT,
            occurred_at_ms=4 * ONE_MINUTE_MS,
        ),
        OutcomeTransitionView(
            transition_id="reclaim-failed",
            shadow_order_id=view.shadow_order_id,
            market_id=view.market_id,
            kind=TransitionKind.RECLAIM_FAILED,
            occurred_at_ms=5 * ONE_MINUTE_MS,
        ),
    )
    for transition in transitions:
        engine.admit_transition(transition, now_ms=transition.occurred_at_ms, recover=False)
    early = (
        _bar(0, open_="102", high="104", low="101", close="102"),
        _bar(1, open_="102", high="106", low="102", close="103"),
        _bar(2, open_="103", high="104", low="99", close="99.8"),
    )
    later = tuple(
        _bar(
            minute,
            open_=str(Decimal("100") - Decimal(minute) / Decimal("10")),
            high=str(Decimal("101") - Decimal(minute) / Decimal("10")),
            low=str(Decimal("99") - Decimal(minute) / Decimal("10")),
            close=str(Decimal("100") - Decimal(minute) / Decimal("10")),
        )
        for minute in range(3, 123)
    )
    _admit(engine, early + later)

    outcome = engine.evaluate(view.shadow_order_id, as_of_ms=123 * ONE_MINUTE_MS)
    research = outcome.research

    assert research is not None
    assert outcome.path_maturity_status is MaturityStatus.MATURE
    assert outcome.failed_breakout is True
    assert outcome.return_inside_range is True
    assert outcome.time_to_retest_ms == 3 * ONE_MINUTE_MS
    assert research.first_return_inside_range_time_ms == 3 * ONE_MINUTE_MS
    assert research.return_inside_range_depth_atr == Decimal("0.1")
    assert research.accepted_reentry_time_ms == 3 * ONE_MINUTE_MS
    assert research.mfe_before_first_reentry == Decimal("6")
    assert research.bars_outside_zone == 2
    assert research.time_outside_zone_ms == 2 * ONE_MINUTE_MS
    assert research.reclaim_attempt_count == 1
    assert research.reclaim_status is ReclaimStatus.FAILED
    assert research.mae_after_reentry is not None and research.mae_after_reentry > 0
    assert research.original_stop == Decimal("95")
    assert research.original_r == Decimal("5")
    assert research.original_stop_hit is True
    assert research.reverse_entry == Decimal("99.8")
    assert tuple(item.maturity for item in research.hypothetical_reverse) == (
        MaturityStatus.MATURE,
        MaturityStatus.MATURE,
        MaturityStatus.MATURE,
    )
    assert research.hypothetical_reverse[0].mfe is not None
    assert research.hypothetical_reverse[0].mfe > 0


def test_successful_breakout_is_control_without_reverse_or_extension() -> None:
    engine = OutcomeEngine()
    view = _view()
    engine.attach(view, now_ms=0, recover=False)
    _admit(
        engine,
        tuple(_bar(index, open_="102", high="104", low="101", close="103") for index in range(120)),
    )

    outcome = engine.evaluate(view.shadow_order_id, as_of_ms=120 * ONE_MINUTE_MS)

    assert outcome.required_end_ms == view.original_deadline_ms
    assert outcome.failed_breakout is False
    assert outcome.return_inside_range is False
    assert outcome.research is not None
    assert outcome.research.accepted_reentry_time_ms is None
    assert outcome.research.hypothetical_reverse == ()


def test_restart_reconstruction_is_deterministic_and_sink_is_change_only() -> None:
    view = _view()
    transition = OutcomeTransitionView(
        transition_id="failure",
        shadow_order_id=view.shadow_order_id,
        market_id=view.market_id,
        kind=TransitionKind.FAILED_BREAKOUT,
        occurred_at_ms=2 * ONE_MINUTE_MS,
        reference_price=Decimal("99"),
    )
    bars = tuple(_bar(index, high="102", low="98", close="99") for index in range(122))
    first = OutcomeEngine.reconstruct(
        shadows=(view,),
        transitions=(transition,),
        bars=bars,
        now_ms=122 * ONE_MINUTE_MS,
    )
    second = OutcomeEngine.reconstruct(
        shadows=(view,),
        transitions=(transition,),
        bars=tuple(reversed(bars)),
        now_ms=122 * ONE_MINUTE_MS,
    )

    assert first.evaluate(view.shadow_order_id, as_of_ms=122 * ONE_MINUTE_MS) == second.evaluate(
        view.shadow_order_id, as_of_ms=122 * ONE_MINUTE_MS
    )

    sink = FakeSink()
    persisted = OutcomeEngine.reconstruct(
        shadows=(view,),
        transitions=(),
        bars=bars[:1],
        now_ms=ONE_MINUTE_MS,
        sink=sink,
    )
    persisted.tick(now_ms=ONE_MINUTE_MS)
    persisted.tick(now_ms=ONE_MINUTE_MS)
    assert len(sink.outcomes) == 1
