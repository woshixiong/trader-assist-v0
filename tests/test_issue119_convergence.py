"""Deterministic Issue #119 convergence, differential, and scale gates."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from tests.test_multi_asset_shadow_integration import (
    FakePlanningData,
    _bootstrap_for_route,
    _payload,
    _route,
    _two_active_market_fixture,
)
from trader_assist_v0.multi_asset_shadow.bootstrap import (
    BoundaryDisposition,
    BoundaryFailure,
    BoundaryReport,
)
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
    HyperliquidPublicPlanningAdapter,
    PublicDataError,
)
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    IntegrationError,
    MultiAssetShadowCoordinator,
    PublicL2Snapshot,
    _continuation_payload,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    FormalShadowView,
    OneMinuteBar,
    OutcomeEngine,
    ShadowState,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    SetupFamily as OutcomeSetupFamily,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import (
    Side as OutcomeSide,
)
from trader_assist_v0.multi_asset_shadow.planning import (
    CostModel,
    PlanningError,
    PublicBbo,
    assess_l2,
)
from trader_assist_v0.multi_asset_shadow.planning import (
    Side as PlanningSide,
)
from trader_assist_v0.multi_asset_shadow.production import ThreeSetupProductionApplication
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
from trader_assist_v0.multi_asset_shadow.strategy_continuation import (
    IncrementalStrategyState,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    EventLedger,
    ScannerCandidate,
    ScannerMarketInput,
    ScannerState,
    StrategyEvaluationInput,
    advance_scanner_candidate,
    aggregate_closed_5m_causally,
    build_zone_book,
    evaluate_strategy,
    scan_cross_section,
    wilder_atr14,
    wilder_atr14_series,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Side as KernelSide,
)

MARKET = "1" * 64


def _bar(index: int, *, market_id: str = MARKET, interval: str = "5m") -> Bar:
    width = {"5m": 300_000, "15m": 900_000}[interval]
    center = Decimal(100 + (index % 9) - 4)
    return Bar(
        market_id=market_id,
        interval=interval,
        open_time_ms=index * width,
        close_time_ms=(index + 1) * width,
        open=center,
        high=center + Decimal("2"),
        low=center - Decimal("2"),
        close=center + Decimal("0.5"),
        volume=Decimal(10 + index % 7),
    )


@pytest.mark.parametrize(
    ("side", "bid", "ask", "level"),
    (
        (PlanningSide.LONG, "2", "3", "3"),
        (PlanningSide.SHORT, "3", "4", "3"),
    ),
)
def test_issue119_l2_exact_touch_is_rational_and_deterministic(
    side: PlanningSide, bid: str, ask: str, level: str
) -> None:
    values = tuple(
        assess_l2(
            market_id="market",
            coin="BTC",
            side=side,
            observed_at_ms=1_000,
            best_bid=Decimal(bid),
            best_ask=Decimal(ask),
            levels=((Decimal(level), Decimal("1000")),),
            provenance_hash="a" * 64,
        )
        for _ in range(2)
    )
    assert values[0] == values[1]
    assert values[0].executable_price == Decimal(level)
    assert values[0].one_way_slippage_bps == 0
    assert values[0].depth_consumed == ((Decimal(level), Decimal("1000") / Decimal(level)),)

    multi = assess_l2(
        market_id="market",
        coin="BTC",
        side=side,
        observed_at_ms=1_000,
        best_bid=Decimal(bid),
        best_ask=Decimal(ask),
        levels=(
            (Decimal(level), Decimal("100")),
            (
                Decimal(level)
                + (Decimal("1") if side is PlanningSide.LONG else Decimal("-1")),
                Decimal("1000"),
            ),
        ),
        provenance_hash="b" * 64,
    )
    assert multi.sufficient_depth
    assert multi.one_way_slippage_bps is not None
    assert multi.one_way_slippage_bps > 0

    contradictory = Decimal(level) - (
        Decimal("1") if side is PlanningSide.LONG else Decimal("-1")
    )
    with pytest.raises(PlanningError, match="ordered outward"):
        assess_l2(
            market_id="market",
            coin="BTC",
            side=side,
            observed_at_ms=1_000,
            best_bid=Decimal(bid),
            best_ask=Decimal(ask),
            levels=((contradictory, Decimal("1000")),),
            provenance_hash="c" * 64,
        )


def test_issue119_reaction_and_zone_identity_survive_bounded_window() -> None:
    values: list[Bar] = []
    high_pivots = {96, 100, 104}
    low_pivots = {98, 102, 106}
    for index in range(120):
        high = Decimal("106") if index in high_pivots else Decimal("103")
        low = Decimal("94") if index in low_pivots else Decimal("97")
        values.append(
            Bar(
                market_id=MARKET,
                interval="15m",
                open_time_ms=index * 900_000,
                close_time_ms=(index + 1) * 900_000,
                open=Decimal("100"),
                high=high,
                low=low,
                close=Decimal("100"),
                volume=Decimal("10"),
            )
        )
    bars = tuple(values)
    atr = wilder_atr14_series(bars)
    full = build_zone_book(bars, minimum_tick=Decimal("0.1"), atr_values=atr)
    offset = len(bars) - 98
    bounded = build_zone_book(
        bars[-98:],
        minimum_tick=Decimal("0.1"),
        atr_values=atr[-98:],
        index_offset=offset,
    )
    assert bounded.reactions == full.reactions
    assert bounded.zones == full.zones
    assert bounded.active_support == full.active_support
    assert bounded.active_resistance == full.active_resistance
    assert all(item.pivot_bar_index >= offset for item in bounded.reactions)


def test_issue119_incremental_strategy_matches_full_history_at_every_boundary(
    tmp_path,
) -> None:
    route = _route(tmp_path, count=180)
    source = tuple(
        route.coordinator._strategy_bar(item)
        for item in route.closed_store.bars(route.market.identity.market_id)
    )
    incremental = IncrementalStrategyState(market_id=route.market.identity.market_id)
    legacy_ledger = EventLedger()
    prior_terminal_ids: set[str] = set()
    compared = 0
    for boundary, bar in enumerate(source):
        incremental.ingest(bar)
        prefix = source[: boundary + 1]
        bars_15m = aggregate_closed_5m_causally(prefix, minutes=15)
        if len(prefix) < 45 or len(bars_15m) < 15:
            continue
        bars_1h = aggregate_closed_5m_causally(prefix, minutes=60)
        zone_book = build_zone_book(bars_15m, minimum_tick=Decimal("0.1"))
        legacy = evaluate_strategy(
            StrategyEvaluationInput(
                bars_5m=prefix,
                bars_15m=bars_15m,
                bars_1h=bars_1h,
                zone_book=zone_book,
                minimum_tick=Decimal("0.1"),
            ),
            legacy_ledger,
        )
        bounded = evaluate_strategy(
            incremental.evaluation_input(minimum_tick=Decimal("0.1"), scanner_linkage=None),
            incremental.ledger,
        )
        current_legacy_events = tuple(
            event
            for event in legacy.ledger.events
            if event.market_event_id not in prior_terminal_ids
        )
        assert bounded.ledger.events == current_legacy_events
        assert bounded.decisions == legacy.decisions
        assert bounded.zones == legacy.zones
        assert bounded.active_support == legacy.active_support
        assert bounded.active_resistance == legacy.active_resistance
        assert bounded.htf_context == legacy.htf_context
        incremental.retain_result(
            bounded.ledger,
            tuple(asdict(item) for item in bounded.ledger.events if item.status.terminal),
        )
        legacy_ledger = legacy.ledger
        prior_terminal_ids.update(
            item.market_event_id for item in legacy.ledger.events if item.status.terminal
        )
        compared += 1
    assert compared == len(source) - 44


def test_issue119_strategy_state_and_first_launch_20_are_history_bounded() -> None:
    payload_sizes: list[int] = []
    single = IncrementalStrategyState(market_id=MARKET)
    for index in range(2_304):
        single.ingest(_bar(index))
        if index + 1 in {576, 1_152, 2_304}:
            payload = _continuation_payload(single)
            payload_sizes.append(len(json.dumps(payload, sort_keys=True)))
            assert len(payload["bars_5m"]) == 21
            assert len(payload["bars_15m"]) <= 98
            assert len(payload["bars_1h"]) <= 10
    assert max(payload_sizes) - min(payload_sizes) < 1_024

    states = [IncrementalStrategyState(market_id=f"{index + 1:064x}") for index in range(20)]
    for index in range(2_304):
        for state in states:
            state.ingest(_bar(index, market_id=state.market_id))
    assert all(state.total_5m == 2_304 for state in states)
    assert all(state.total_15m == 768 and state.total_1h == 192 for state in states)
    assert all(
        (len(state.bars_5m), len(state.bars_15m), len(state.bars_1h)) == (21, 98, 10)
        for state in states
    )


@pytest.mark.parametrize("history_count", (64, 287, 288, 700))
def test_issue119_bounded_scanner_matches_full_history_exactly(history_count: int) -> None:
    full_inputs: list[ScannerMarketInput] = []
    bounded_inputs: list[ScannerMarketInput] = []
    for offset in range(3):
        market_id = f"{offset + 1:064x}"
        bars = tuple(
            Bar(
                market_id=market_id,
                interval="5m",
                open_time_ms=index * 300_000,
                close_time_ms=(index + 1) * 300_000,
                open=Decimal(100 + offset) + Decimal(index % 11) / 10,
                high=Decimal(102 + offset) + Decimal(index % 11) / 10,
                low=Decimal(98 + offset) + Decimal(index % 11) / 10,
                close=Decimal(100 + offset) + Decimal((index * (offset + 1)) % 17) / 10,
                volume=Decimal(10 + (index + offset) % 9),
            )
            for index in range(history_count)
        )
        common = {
            "market_id": market_id,
            "minimum_tick": Decimal("0.1"),
            "current_spread_price": Decimal("0.1"),
            "liquidity_healthy": True,
        }
        full_inputs.append(ScannerMarketInput(bars_5m=bars, **common))
        bounded_inputs.append(
            ScannerMarketInput(
                bars_5m=bars[-37:],
                history_count=len(bars),
                exact_wilder_atr_5m=wilder_atr14(bars),
                **common,
            )
        )
    assert scan_cross_section(tuple(bounded_inputs)) == scan_cross_section(tuple(full_inputs))

    bars = full_inputs[0].bars_5m
    candidate = ScannerCandidate(
        candidate_id="c" * 64,
        market_id=full_inputs[0].market_id,
        side=KernelSide.LONG,
        state=ScannerState.RETEST_PENDING,
        created_bar_open_time_ms=bars[-6].open_time_ms,
        breakout_bar_open_time_ms=bars[-6].open_time_ms,
        breakout_level=Decimal("100"),
        breakout_buffer=Decimal("0.5"),
        secondary_level_broken=False,
        retest_touch_bar_open_time_ms=None,
        chase=None,
        chase_distance_atr=None,
        reason="TEST_ACTIVE_PROGRESSION",
        transitions=("NEW->RETEST_PENDING",),
    )
    full_progression = advance_scanner_candidate(
        candidate,
        bars_5m=bars,
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
    )
    bounded_progression = advance_scanner_candidate(
        candidate,
        bars_5m=bars[-37:],
        current_spread_price=Decimal("0.1"),
        liquidity_healthy=True,
        exact_wilder_atr_5m=wilder_atr14(bars),
    )
    assert bounded_progression == full_progression
    if history_count >= 288:
        gap_candidate = replace(
            candidate,
            breakout_bar_open_time_ms=bars[-50].open_time_ms,
            created_bar_open_time_ms=bars[-50].open_time_ms,
        )
        assert advance_scanner_candidate(
            gap_candidate,
            bars_5m=bars[-37:],
            current_spread_price=Decimal("0.1"),
            liquidity_healthy=True,
            exact_wilder_atr_5m=wilder_atr14(bars),
        ) == advance_scanner_candidate(
            gap_candidate,
            bars_5m=bars,
            current_spread_price=Decimal("0.1"),
            liquidity_healthy=True,
        )


@pytest.mark.parametrize("history_count", (320, 640, 1_280))
def test_issue119_current_t_scanner_access_is_history_bounded(tmp_path, history_count: int) -> None:
    route = _route(tmp_path, count=history_count)
    market_id = route.market.identity.market_id
    full = tuple(
        route.coordinator._strategy_bar(item) for item in route.closed_store.bars(market_id)
    )
    state = IncrementalStrategyState(market_id=market_id)
    for bar in full:
        state.ingest(bar)
    route.coordinator._continuations[market_id] = state
    latest = route.closed_store.tail_bars(
        market_id, at_or_before_ms=(history_count - 1) * 300_000, limit=1
    )[0]
    route.closed_store.reset_access_counters()

    receipt = route.coordinator.scan_finalized(
        {
            market_id: route.planning.fetch_scanner_snapshot(
                market=route.market,
                now_ms=latest.close_time_ms + 1,
                btc_returns=(None, None, None),
            )
        },
        observed_at=datetime.fromtimestamp((latest.close_time_ms + 1) / 1000, UTC),
    )
    assert len(receipt.observations) == 1
    assert route.closed_store.access_counters.returned_rows == 37
    assert route.closed_store.access_counters.decoded_rows == 37
    plan = tuple(
        str(row[3])
        for row in route.closed_store.connection.execute(
            """EXPLAIN QUERY PLAN SELECT payload_json FROM closed_bars
               WHERE market_id=? AND interval=? AND open_time_ms<=?
               ORDER BY open_time_ms DESC LIMIT ?""",
            (market_id, "5m", latest.open_time_ms, 37),
        )
    )
    assert any("SEARCH closed_bars" in item for item in plan)
    assert not any("SCAN closed_bars" in item for item in plan)


def test_issue119_hot_evidence_queries_use_indexed_subsets(tmp_path) -> None:
    route = _route(tmp_path, count=64)
    connection = route.evidence._connection
    queries = (
        (
            """SELECT record_id FROM immutable_records
               WHERE record_type='strategy_evaluation'
                 AND json_extract(payload_json, '$.strategy_version')=?
                 AND json_extract(payload_json, '$.parameter_version')=?
                 AND json_extract(payload_json, '$.market_id')=?
               ORDER BY json_extract(payload_json, '$.source_open_time_ms') DESC LIMIT 1""",
            ("strategy-kernel-v0", "2026-08-03-r1", route.market.identity.market_id),
        ),
        (
            """SELECT record_id FROM immutable_records
               WHERE record_type='scanner_evidence'
                 AND json_extract(payload_json, '$.registry_version')=?
                 AND json_extract(payload_json, '$.scan_boundary_open_time_ms')=?
                 AND json_extract(payload_json, '$.evidence_role')='RAW_DISCOVERY'""",
            ("registry-1", route.latest.open_time_ms),
        ),
        (
            """SELECT record_id FROM immutable_records
               WHERE record_type='candidate'
                 AND json_extract(payload_json, '$.live_authority')=1
                 AND json_extract(payload_json, '$.market_id')=?
                 AND json_extract(payload_json, '$.source_boundary_open_time_ms')=?""",
            (route.market.identity.market_id, route.latest.open_time_ms),
        ),
        (
            """SELECT record_id FROM immutable_records
               WHERE record_type='formalization_disposition'
                 AND json_extract(payload_json, '$.strategy_evaluation_id')=?
                 AND json_extract(payload_json, '$.strategy_decision_id')=?""",
            ("evaluation", "decision"),
        ),
    )
    for sql, parameters in queries:
        plan = tuple(
            str(row[3])
            for row in connection.execute("EXPLAIN QUERY PLAN " + sql, parameters)
        )
        assert any("SEARCH immutable_records" in item for item in plan), plan
        assert not any("SCAN immutable_records" in item for item in plan), plan


def test_issue119_sparse_checkpoint_restart_derives_latest_compact_state(tmp_path) -> None:
    route = _route(tmp_path, count=70)
    market_id = route.market.identity.market_id
    receipts = tuple(
        route.coordinator.evaluate_finalized_market(
            market_id=market_id,
            source_open_time_ms=bar.open_time_ms,
            evaluation_mode=BoundaryMode.RECOVERY_CONTEXT_ONLY,
        )
        for bar in route.closed_store.bars(market_id)[44:]
    )
    rows = route.evidence._connection.execute(
        """SELECT payload_json FROM immutable_records
           WHERE record_type = 'strategy_evaluation'
           ORDER BY json_extract(payload_json, '$.source_open_time_ms')"""
    ).fetchall()
    payloads = tuple(json.loads(row[0]) for row in rows)
    checkpoints = tuple(item for item in payloads if item["continuation"]["checkpoint"])
    compact = tuple(item for item in payloads if not item["continuation"]["checkpoint"])
    assert len(checkpoints) == 2
    assert compact
    assert all("bars_15m" not in item["continuation"] for item in compact)
    assert max(len(json.dumps(item)) for item in compact) < min(
        len(json.dumps(item)) for item in checkpoints
    )

    expected = receipts[-1]
    route.evidence.close()
    reopened = EvidenceStore(tmp_path / "evidence.sqlite")
    reopened.reset_query_counters()
    route.closed_store.reset_access_counters()
    adapter = EvidenceOutcomeAdapter(reopened)
    restarted = MultiAssetShadowCoordinator(
        registry=route.registry,
        data_authority=route.data,
        evidence=reopened,
        outbox=EvidenceOutbox(reopened),
        outcome_engine=OutcomeEngine(sink=adapter),
        outcome_adapter=adapter,
        planning_data=route.planning,
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=route.coordinator._release_sha,
        runtime_readiness=route.readiness,
    )
    assert reopened.query_counters["strategy.latest"].returned_rows == 1
    assert reopened.query_counters["strategy.checkpoint"].returned_rows == 1
    assert route.closed_store.access_counters.returned_rows <= 63
    assert route.closed_store.access_counters.decoded_rows <= 63
    actual = restarted.evaluate_finalized_market(
        market_id=market_id,
        source_open_time_ms=route.latest.open_time_ms,
        evaluation_mode=BoundaryMode.RECOVERY_CONTEXT_ONLY,
    )
    assert actual.input_ledger_hash == expected.input_ledger_hash
    assert actual.output_ledger_hash == expected.output_ledger_hash
    assert restarted._continuations[market_id].source_history_commitment == (
        route.coordinator._continuations[market_id].source_history_commitment
    )
    reopened.close()


def _admit_current_cohort(markets, data, bootstrap, boundary_index):
    admitted = tuple(
        data.admit_rest_history(
            market=market,
            snapshot=[_payload(boundary_index, final=True, coin=market.identity.coin)],
            received_at=bootstrap.clock(),
        )[0]
        for market in markets
    )
    return asyncio.run(
        bootstrap.runtime._notify_finalized(admitted[-1], BoundaryMode.LIVE_ACTIONABLE)
    )


def test_issue119_selected_scanner_authority_rolls_back_as_one_cohort(tmp_path) -> None:
    markets, _, data, bootstrap, boundary_index = _two_active_market_fixture(
        tmp_path, planning=FakePlanningData()
    )
    original = bootstrap.coordinator.compose_scanner_market
    calls = 0

    def fail_after_partial_prepare(**kwargs):
        nonlocal calls
        result = original(**kwargs)
        calls += 1
        if calls == 2:
            raise IntegrationError("injected selected Scanner cohort failure")
        return result

    bootstrap.coordinator.compose_scanner_market = fail_after_partial_prepare  # type: ignore[method-assign]
    report = _admit_current_cohort(markets, data, bootstrap, boundary_index)
    assert report.failures and report.failures[0].stage == "SCANNER"
    assert (
        bootstrap.evidence._connection.execute("SELECT COUNT(*) FROM scanner_evidence").fetchone()[
            0
        ]
        == 1
    )
    retained_selected = bootstrap.evidence._connection.execute(
        """SELECT COUNT(*) FROM immutable_records
           WHERE record_type IN ('candidate', 'scanner_progression')"""
    ).fetchone()[0]
    assert retained_selected == 0
    assert (
        bootstrap.evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
           WHERE record_type IN ('strategy_evaluation', 'formal_signal', 'shadow_order')"""
        ).fetchone()[0]
        == 0
    )


def test_issue119_strategy_prepare_failure_publishes_zero_live_cohort(tmp_path) -> None:
    markets, _, data, bootstrap, boundary_index = _two_active_market_fixture(
        tmp_path, planning=FakePlanningData()
    )
    original = bootstrap.coordinator.prepare_finalized_market

    def fail_second_market(**kwargs):
        if kwargs["market_id"] == markets[1].identity.market_id:
            raise IntegrationError("injected Strategy prepare failure")
        return original(**kwargs)

    bootstrap.coordinator.prepare_finalized_market = fail_second_market  # type: ignore[method-assign]
    report = _admit_current_cohort(markets, data, bootstrap, boundary_index)
    assert any(item.stage == "STRATEGY" for item in report.failures)
    assert (
        bootstrap.evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
           WHERE record_type = 'strategy_evaluation'
             AND json_extract(payload_json, '$.evaluation_mode') = 'LIVE_ACTIONABLE'"""
        ).fetchone()[0]
        == 0
    )
    assert (
        bootstrap.evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
           WHERE record_type IN ('formal_signal', 'shadow_order')"""
        ).fetchone()[0]
        == 0
    )


def test_issue119_late_scanner_workers_are_discarded_without_authority(tmp_path) -> None:
    late = False

    class LatePlanning(FakePlanningData):
        raw_calls = 0
        staged_calls = 0

        def fetch_raw_l2(self, *, market):
            nonlocal late
            self.raw_calls += 1
            late = True
            return {"late": market.identity.coin}

        def stage_raw_l2(self, **_kwargs):
            self.staged_calls += 1

    planning = LatePlanning()
    markets, _, data, bootstrap, boundary_index = _two_active_market_fixture(
        tmp_path, planning=planning
    )
    base_clock = bootstrap.clock

    def clock():
        value = base_clock()
        return value + timedelta(seconds=61) if late else value

    bootstrap.clock = clock
    bootstrap.runtime.clock = clock
    report = _admit_current_cohort(markets, data, bootstrap, boundary_index)
    assert report.failures and report.failures[0].stage == "SCANNER"
    assert report.failures[0].market_id in {
        market.identity.market_id for market in markets
    }
    failed_market = next(
        market for market in markets if market.identity.market_id == report.failures[0].market_id
    )
    assert report.failures[0].provider_coin == failed_market.identity.coin
    assert report.failures[0].provider_provenance == "hyperliquid-public-info:l2Book"
    assert planning.raw_calls >= 1
    assert planning.staged_calls == 0
    assert bootstrap.evidence.count() == 0


def test_issue119_scanner_market_failure_reaches_operator_evidence(caplog) -> None:
    failure = BoundaryFailure(
        stage="SCANNER",
        market_id=MARKET,
        error_type="PublicDataError",
        reason="injected",
        provider_coin="BTC",
        provider_provenance="hyperliquid-public-info:l2Book",
    )
    report = BoundaryReport(
        boundary_open_time_ms=300_000,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
        disposition=BoundaryDisposition.PROCESSED,
        scanner_run_count=0,
        evaluated_market_ids=(),
        formal_shadow_order_ids=(),
        plan_rejections=(),
        failures=(failure,),
    )

    class FakeBootstrap:
        def __init__(self) -> None:
            self.runtime = SimpleNamespace(
                on_finalized_5m=None,
                on_reconnect=None,
                readiness_snapshot=lambda: SimpleNamespace(
                    data_ready=True, snapshot_hash="r" * 64
                ),
            )

        async def on_finalized_5m(self, _bar, _mode):
            return report

    logger = logging.getLogger("issue119-scanner-attribution")
    caplog.set_level(logging.INFO, logger=logger.name)
    app = ThreeSetupProductionApplication(
        bootstrap=FakeBootstrap(),  # type: ignore[arg-type]
        dispatcher=object(),  # type: ignore[arg-type]
        clock=lambda: datetime.now(UTC),
        logger=logger,
    )
    asyncio.run(app._on_finalized_5m(None, BoundaryMode.LIVE_ACTIONABLE))  # type: ignore[arg-type]
    events = tuple(json.loads(item.message) for item in caplog.records)
    scanner = next(item for item in events if item["event"] == "SCANNER")
    assert scanner["market_id"] == MARKET
    assert scanner["provider_coin"] == "BTC"
    assert scanner["provider_provenance"] == "hyperliquid-public-info:l2Book"


def test_issue119_l2_fresh_at_fetch_but_stale_at_use_is_discarded(tmp_path) -> None:
    markets, _, _, _, _ = _two_active_market_fixture(tmp_path, planning=FakePlanningData())
    market = markets[0]
    adapter = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=lambda *_: pytest.fail("transport must not run"))
    )
    response = {
        "coin": market.identity.coin,
        "time": 1_000,
        "levels": [
            [{"px": "100", "sz": "20"}],
            [{"px": "100.1", "sz": "20"}],
        ],
    }
    adapter.stage_raw_l2(market=market, response=response, now_ms=1_000)
    with pytest.raises(PublicDataError, match="became stale at use"):
        adapter.scanner_snapshot_from_staged(
            market=market,
            now_ms=11_001,
            btc_returns=(None, None, None),
        )
    assert market.identity.market_id not in adapter._pending


def _formal_commit_crossing_fixture(tmp_path, *, crossing_ms: int):
    route = _route(tmp_path)
    route.coordinator.evaluate_finalized_market(
        market_id=route.market.identity.market_id,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )

    class MutableClock:
        def __init__(self) -> None:
            self.value = route.latest.close_time_ms + 5_000

        def now(self):
            return datetime.fromtimestamp(self.value / 1000, tz=UTC)

    clock = MutableClock()

    class CrossingPlanning(FakePlanningData):
        def __init__(self) -> None:
            super().__init__()
            self.observed_at_ms = clock.value
            self.crossed = False

        def fetch_bbo(self, *, market, now_ms: int) -> PublicBbo:
            del now_ms
            self.calls.append("BBO")
            return PublicBbo(
                best_bid=self.best_bid,
                best_ask=self.best_ask,
                observed_at_ms=self.observed_at_ms,
                market_id=market.identity.market_id,
                coin=market.identity.coin,
            )

        def fetch_l2(self, *, market, side, bbo: PublicBbo) -> PublicL2Snapshot:
            snapshot = super().fetch_l2(market=market, side=side, bbo=bbo)
            if not self.crossed:
                clock.value += crossing_ms
                self.crossed = True
            return snapshot

    planning = CrossingPlanning()
    bootstrap = _bootstrap_for_route(route, planning=planning, clock=clock.now)
    return route, bootstrap


def _assert_zero_formal_publication(route) -> None:
    formal_types = (
        "provenance",
        "market_event",
        "formal_signal",
        "plan_record",
        "shadow_order",
        "notification_outbox_reference",
    )
    retained = route.evidence._connection.execute(
        """SELECT COUNT(*) FROM immutable_records
           WHERE record_type IN (?, ?, ?, ?, ?, ?)""",
        formal_types,
    ).fetchone()[0]
    assert retained == 0
    assert (
        route.evidence._connection.execute("SELECT COUNT(*) FROM notification_outbox").fetchone()[0]
        == 0
    )
    assert route.outcome.attached_shadow_ids == ()


def test_issue119_formal_commit_time_deadline_crossing_rejects_real_publication(
    tmp_path,
) -> None:
    route, bootstrap = _formal_commit_crossing_fixture(tmp_path, crossing_ms=61_000)
    assert asyncio.run(bootstrap.reconcile()) == ()
    _assert_zero_formal_publication(route)


def test_issue119_formal_commit_time_freshness_crossing_rejects_real_publication(
    tmp_path,
) -> None:
    route, bootstrap = _formal_commit_crossing_fixture(tmp_path, crossing_ms=10_001)
    assert asyncio.run(bootstrap.reconcile()) == ()
    _assert_zero_formal_publication(route)


def _outcome_view(identity: str) -> FormalShadowView:
    return FormalShadowView(
        shadow_order_id=identity,
        market_id="market",
        side=OutcomeSide.LONG,
        setup_family=OutcomeSetupFamily.SWEEP_RECLAIM,
        outcome_start_ms=0,
        planned_entry=Decimal("100"),
        stop=Decimal("95"),
        tp1=Decimal("105"),
        tp2=None,
        atr=Decimal("2"),
        zone_low=None,
        zone_high=None,
        state=ShadowState.FORMAL_SHADOW_PLAN,
        active=True,
    )


@pytest.mark.parametrize("mature_count", (10, 10_000))
def test_issue119_outcome_tick_passivates_mature_lifetime_history(mature_count: int) -> None:
    engine = OutcomeEngine()
    synchronize = engine._synchronize_subscriptions
    engine._synchronize_subscriptions = lambda _now_ms: None
    for index in range(mature_count):
        engine.attach(_outcome_view(f"shadow-{index}"), now_ms=0, recover=False)
    engine._synchronize_subscriptions = synchronize
    for minute in range(120):
        engine.admit_bar(
            OneMinuteBar.create(
                market_id="market",
                open_time_ms=minute * 60_000,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
            )
        )
    assert len(engine.tick(now_ms=120 * 60_000, recover=False)) == mature_count
    assert engine.attached_shadow_ids == ()
    assert engine.tick(now_ms=120 * 60_000, recover=False) == ()
    assert engine._bars == {}


def test_issue119_notification_due_polling_searches_partial_index(tmp_path) -> None:
    store = EvidenceStore(tmp_path / "evidence.sqlite")
    delivered = tuple(
        (
            f"delivered-{index}",
            "NOTIFICATION_V1",
            "WATCH",
            "content",
            "2026-08-25T00:00:00Z",
            "DELIVERED",
            1,
            "2026-08-25T00:00:00Z",
        )
        for index in range(10_000)
    )
    store._connection.executemany(
        """INSERT INTO notification_outbox(
               idempotency_key, schema_version, kind, content, created_at,
               state, attempt_count, next_attempt_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        delivered,
    )
    store._connection.execute(
        """INSERT INTO notification_outbox(
               idempotency_key, schema_version, kind, content, created_at,
               state, attempt_count, next_attempt_at
           ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?)""",
        (
            "due",
            "NOTIFICATION_V1",
            "WATCH",
            "content",
            "2026-08-25T00:00:00Z",
            "2026-08-25T00:00:00Z",
        ),
    )
    store._connection.commit()
    plan = store._connection.execute(
        """EXPLAIN QUERY PLAN SELECT * FROM notification_outbox
           WHERE state = 'PENDING' AND next_attempt_at <= ?
             AND (claim_token IS NULL OR claim_expires_at <= ?)
           ORDER BY next_attempt_at, created_at, idempotency_key
           LIMIT ?""",
        ("2026-08-25T00:00:01Z", "2026-08-25T00:00:01Z", 10),
    ).fetchall()
    details = tuple(str(row[3]) for row in plan)
    assert any(
        "SEARCH notification_outbox USING INDEX notification_outbox_pending_due" in item
        for item in details
    ), details

    strategy_plan = store._connection.execute(
        """EXPLAIN QUERY PLAN SELECT record_id FROM immutable_records
           WHERE record_type = 'strategy_evaluation'
             AND json_extract(payload_json, '$.evaluation_id') = ?""",
        ("evaluation",),
    ).fetchall()
    assert any(
        "USING INDEX immutable_strategy_evaluation_id" in str(row[3]) for row in strategy_plan
    )
    outcome_plan = store._connection.execute(
        """EXPLAIN QUERY PLAN SELECT 1 FROM immutable_records
           WHERE record_type = 'outcome_bar'
             AND json_extract(payload_json, '$.market_id') = ?
             AND json_extract(payload_json, '$.open_time_ms') = ?
             AND json_extract(payload_json, '$.canonical_hash') = ?
           LIMIT 1""",
        ("market", 0, "hash"),
    ).fetchall()
    assert any("USING INDEX immutable_outcome_bar_identity" in str(row[3]) for row in outcome_plan)
    store.close()
