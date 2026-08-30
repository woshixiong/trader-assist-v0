"""Issue #134 partial-prefix continuation and real post-ACTIVE acceptance."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from tests.test_issue131_lifecycle_liveness import (
    AckFromOutboundSocket,
    ControlledClock,
    _first_launch_markets,
    async_test,
    candle,
    wait_until,
)
from tests.test_multi_asset_shadow_integration import (
    FakeOneMinuteProvider,
    FakePlanningData,
)
from trader_assist_v0.multi_asset_shadow import strategy_continuation
from trader_assist_v0.multi_asset_shadow.bootstrap import (
    BoundaryReport,
    MultiAssetProductionBootstrap,
)
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
    MultiAssetDataAuthority,
)
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    MultiAssetShadowCoordinator,
    _continuation_from_payload,
    _continuation_payload,
)
from trader_assist_v0.multi_asset_shadow.models import (
    MarketLifecycle,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.outcome_engine import OutcomeEngine
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.production import (
    ThreeSetupProductionApplication,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import (
    BoundaryMode,
    MultiAssetPublicRuntime,
)
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
from trader_assist_v0.multi_asset_shadow.strategy_continuation import (
    IncrementalStrategyState,
)
from trader_assist_v0.multi_asset_shadow.strategy_kernel import (
    Bar,
    aggregate_closed_5m_causally,
)

FIVE_MINUTES_MS = 300_000
MARKET = "1" * 64
REALISTIC_HISTORY = 2_304
REALISTIC_PREFIX = 2_308
COMPOSITION_HISTORY = 49
COMPOSITION_T0 = 1_800_000_300_000


def _bar(index: int, *, market_id: str = MARKET) -> Bar:
    center = Decimal(100 + index % 9)
    return Bar(
        market_id=market_id,
        interval="5m",
        open_time_ms=index * FIVE_MINUTES_MS,
        close_time_ms=(index + 1) * FIVE_MINUTES_MS,
        open=center,
        high=center + Decimal("2"),
        low=center - Decimal("2"),
        close=center + Decimal("0.5"),
        volume=Decimal(10 + index % 7),
    )


@pytest.mark.parametrize("start_phase", range(12))
def test_issue134_all_start_phases_match_causal_aggregation_at_every_prefix(
    start_phase: int,
) -> None:
    source = tuple(_bar(start_phase + offset) for offset in range(REALISTIC_PREFIX))
    complete_15m = aggregate_closed_5m_causally(source, minutes=15)
    complete_1h = aggregate_closed_5m_causally(source, minutes=60)
    count_15m_at_close = {
        item.close_time_ms: index + 1 for index, item in enumerate(complete_15m)
    }
    count_1h_at_close = {
        item.close_time_ms: index + 1 for index, item in enumerate(complete_1h)
    }
    literal_differential_prefixes = set(range(1, 15)) | {
        REALISTIC_HISTORY,
        REALISTIC_PREFIX,
    }
    expected_15m = 0
    expected_1h = 0
    state = IncrementalStrategyState(market_id=MARKET)

    for prefix_length, bar in enumerate(source, start=1):
        state.ingest(bar)
        expected_15m = count_15m_at_close.get(bar.close_time_ms, expected_15m)
        expected_1h = count_1h_at_close.get(bar.close_time_ms, expected_1h)

        # A complete aggregate's close is the exact source prefix where the
        # accepted causal aggregator's count advances.  This proves equality
        # at every prefix without constructing the same O(n^2) aggregate set.
        assert state.total_15m == expected_15m
        assert state.total_1h == expected_1h
        if prefix_length in literal_differential_prefixes:
            prefix = source[:prefix_length]
            assert state.total_15m == len(
                aggregate_closed_5m_causally(prefix, minutes=15)
            )
            assert state.total_1h == len(
                aggregate_closed_5m_causally(prefix, minutes=60)
            )


@pytest.mark.parametrize(
    "next_index",
    (20, 19, 22),
    ids=("duplicate", "reorder", "internal-gap"),
)
def test_issue134_chronology_attacks_remain_fail_closed(next_index: int) -> None:
    state = IncrementalStrategyState(market_id=MARKET)
    state.ingest(_bar(20))
    with pytest.raises(ValueError, match="source history is not chronological"):
        state.ingest(_bar(next_index))


@pytest.mark.parametrize(
    ("minutes", "required", "message"),
    (
        (15, 3, "15m continuation aggregation is incomplete"),
        (60, 12, "1h continuation aggregation is incomplete"),
    ),
)
def test_issue134_complete_bucket_still_requires_exactly_one_aggregate(
    monkeypatch: pytest.MonkeyPatch,
    minutes: int,
    required: int,
    message: str,
) -> None:
    original = aggregate_closed_5m_causally

    def incomplete(bars: tuple[Bar, ...] | list[Bar], *, minutes: int) -> tuple[Bar, ...]:
        if minutes == target_minutes:
            return ()
        return original(bars, minutes=minutes)

    target_minutes = minutes
    monkeypatch.setattr(
        strategy_continuation, "aggregate_closed_5m_causally", incomplete
    )
    state = IncrementalStrategyState(market_id=MARKET)
    source = tuple(_bar(index) for index in range(required))
    for bar in source[:-1]:
        state.ingest(bar)
    with pytest.raises(ValueError, match=message):
        state.ingest(source[-1])


def test_issue134_checkpoint_restore_continuation_is_exact() -> None:
    source = tuple(_bar(2 + offset) for offset in range(160))
    original = IncrementalStrategyState(market_id=MARKET)
    for bar in source[:79]:
        original.ingest(bar)

    restored = _continuation_from_payload(_continuation_payload(original))
    assert restored == original
    for bar in source[79:]:
        original.ingest(bar)
        restored.ingest(bar)
        assert restored == original


class _RetainedHistoryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(
        self, *, coin: str, interval: str, start_ms: int, end_ms: int
    ) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        retained_start = max(
            start_ms, end_ms - COMPOSITION_HISTORY * FIVE_MINUTES_MS
        )
        return [
            candle(coin, open_ms)
            for open_ms in range(retained_start, end_ms, FIVE_MINUTES_MS)
        ]


class _NoopDispatcher:
    def __init__(self) -> None:
        self.closed = False

    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        return ()

    def close(self) -> None:
        self.closed = True


@async_test  # type: ignore[misc]
async def test_issue134_real_first_launch_20_reaches_post_active_boundary_report(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    markets = _first_launch_markets()
    assert len(markets) == 20
    assert all(item.lifecycle is MarketLifecycle.WARMING for item in markets)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(
        version="issue134-first-launch-20-cold",
        created_at=datetime(2026, 8, 30, tzinfo=UTC),
        markets=markets,
    )
    registry.stage(seed)
    registry.request_apply(seed.version)
    closed = ClosedBarStore(tmp_path / "closed.sqlite")
    authority = MultiAssetDataAuthority(store=closed, registry=registry)
    evidence = EvidenceStore(tmp_path / "evidence.sqlite")
    outbox = EvidenceOutbox(evidence)
    outcome_adapter = EvidenceOutcomeAdapter(evidence)
    outcome = OutcomeEngine(provider=FakeOneMinuteProvider(), sink=outcome_adapter)
    planning = FakePlanningData()
    client = _RetainedHistoryClient()
    clock = ControlledClock()
    clock.value_ms = COMPOSITION_T0 + FIVE_MINUTES_MS + 5_000
    socket = AckFromOutboundSocket()

    async def factory(_: str) -> AckFromOutboundSocket:
        return socket

    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        websocket_factory=factory,
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        heartbeat_interval_seconds=3_600,
    )
    coordinator = MultiAssetShadowCoordinator(
        registry=registry,
        data_authority=authority,
        evidence=evidence,
        outbox=outbox,
        outcome_engine=outcome,
        outcome_adapter=outcome_adapter,
        planning_data=planning,
        cost_model=CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha="1" * 40,
        runtime_readiness=runtime,
        clock=clock.now,
    )
    bootstrap = MultiAssetProductionBootstrap(
        registry=registry,
        data_authority=authority,
        evidence=evidence,
        outbox=outbox,
        outcome_adapter=outcome_adapter,
        outcome_engine=outcome,
        planning_data=planning,  # type: ignore[arg-type]
        coordinator=coordinator,
        runtime=runtime,
        clock=clock.now,
        sleep=clock.sleep,
    )
    runtime.on_maintenance_5m = bootstrap.on_maintenance_5m
    dispatcher = _NoopDispatcher()
    application = ThreeSetupProductionApplication(
        bootstrap=bootstrap,
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=clock.now,
        sleep=clock.sleep,
        notification_poll_seconds=60,
    )
    production_callback = runtime.on_finalized_5m
    assert production_callback is not None
    reports: list[BoundaryReport] = []

    async def capture_production_report(bar: Any, mode: BoundaryMode) -> BoundaryReport:
        result = production_callback(bar, mode)
        report = await result if isinstance(result, Awaitable) else result
        assert isinstance(report, BoundaryReport)
        reports.append(report)
        return report

    runtime.on_finalized_5m = capture_production_report
    shutdown = asyncio.Event()
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        application_task = asyncio.create_task(application.run(shutdown))
        await wait_until(
            lambda: runtime.health.data_ready and len(socket.sent) == 20,
            timeout=120,
        )
        first_open = (
            COMPOSITION_T0
            + FIVE_MINUTES_MS
            - COMPOSITION_HISTORY * FIVE_MINUTES_MS
        )
        assert first_open % 900_000 != 0
        assert first_open % 3_600_000 != 0
        assert all(
            closed.connection.execute(
                "SELECT MIN(open_time_ms) FROM closed_bars "
                "WHERE market_id=? AND interval='5m'",
                (market.identity.market_id,),
            ).fetchone()[0]
            == first_open
            for market in markets
        )

        for index, expected in enumerate(
            (
                MarketLifecycle.HISTORY_READY,
                MarketLifecycle.SNAPSHOT_READY,
                MarketLifecycle.ACTIVE,
            )
        ):
            await wait_until(lambda expected_wait=index + 1: clock.tick_waits >= expected_wait)
            boundary = COMPOSITION_T0 + index * FIVE_MINUTES_MS
            clock.release(boundary, 60.0 + index * 100.0)
            await wait_until(
                lambda expected_state=expected: all(
                    item.lifecycle is expected_state
                    for item in (registry.active() or seed).markets
                )
            )
            assert reports == []
            assert not application_task.done()

        await wait_until(lambda: clock.tick_waits >= 4)
        live_boundary = COMPOSITION_T0 + 3 * FIVE_MINUTES_MS
        clock.release(live_boundary, 360.0)
        await wait_until(
            lambda: bool(reports) or bool(runtime.health.callback_failures),
            timeout=120,
        )
        assert runtime.health.callback_failures == []
        assert len(reports) == 1
        report = reports[0]
        assert report.boundary_open_time_ms == live_boundary
        assert report.evaluation_mode is BoundaryMode.LIVE_ACTIONABLE
        assert report.failures == ()
        assert report.scanner_run_count == 1
        assert len(report.evaluated_market_ids) == 20
        assert set(report.evaluated_market_ids) == {
            market.identity.market_id for market in markets
        }
        assert not application_task.done()
        shutdown.set()
        await application_task

    events = [json.loads(record.message) for record in caplog.records]
    assert not any(
        item["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED" for item in events
    )
    assert any(item["event"] == "BOUNDARY_REPORT" for item in events)
    assert socket.closed
    assert dispatcher.closed
