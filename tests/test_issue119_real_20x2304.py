"""Real First-Launch-20 durable recovery and first-LIVE scale acceptance."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

from tests.test_first_launch_20_cohort import BudgetClient, candle, exact_first_launch_20
from tests.test_multi_asset_shadow_integration import FakeOneMinuteProvider, FakePlanningData
from trader_assist_v0.multi_asset_shadow.bootstrap import MultiAssetProductionBootstrap
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import (
    EvidenceOutbox,
    EvidenceOutcomeAdapter,
    MultiAssetShadowCoordinator,
)
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle, RegistryVersion
from trader_assist_v0.multi_asset_shadow.outcome_engine import OutcomeEngine
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
from trader_assist_v0.multi_asset_shadow.strategy_continuation import REPRESENTATION_VERSION

FIVE_MINUTES_MS = 300_000
MARKET_COUNT = 20
HISTORY_5M = 2_304
HISTORY_15M = 768
HISTORY_1H = 192
START_OPEN_MS = 1_800_000_000_000


class MutableClock:
    def __init__(self, value_ms: int) -> None:
        self.value_ms = value_ms

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.value_ms / 1_000, tz=UTC)


def test_issue119_real_first_launch_20_x_2304_recovery_to_first_live(tmp_path) -> None:
    markets = tuple(
        item.model_copy(update={"lifecycle": MarketLifecycle.ACTIVE})
        for item in exact_first_launch_20()
    )
    assert len(markets) == MARKET_COUNT
    assert len({item.identity.market_id for item in markets}) == MARKET_COUNT

    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="issue119-first-launch-20-2304",
        created_at=datetime(2026, 8, 25, tzinfo=UTC),
        markets=markets,
    )
    registry.stage(version)
    registry.request_apply(version.version)
    closed = ClosedBarStore(tmp_path / "closed.sqlite")
    data = MultiAssetDataAuthority(store=closed, registry=registry)
    history_boundary = START_OPEN_MS + (HISTORY_5M - 1) * FIVE_MINUTES_MS
    clock = MutableClock(history_boundary + FIVE_MINUTES_MS + 5_000)
    for market in markets:
        data.admit_rest_history(
            market=market,
            snapshot=[
                candle(
                    market.identity.coin,
                    START_OPEN_MS + index * FIVE_MINUTES_MS,
                )
                for index in range(HISTORY_5M)
            ],
            received_at=clock.now(),
        )
    assert registry.active() == version

    interval_counts = {
        str(row[0]): int(row[1])
        for row in closed.connection.execute(
            "SELECT interval, COUNT(*) FROM closed_bars GROUP BY interval"
        )
    }
    assert interval_counts == {
        "5m": MARKET_COUNT * HISTORY_5M,
        "15m": MARKET_COUNT * HISTORY_15M,
        "1h": MARKET_COUNT * HISTORY_1H,
    }

    evidence = EvidenceStore(tmp_path / "evidence.sqlite")
    outbox = EvidenceOutbox(evidence)
    outcome_adapter = EvidenceOutcomeAdapter(evidence)
    outcome = OutcomeEngine(provider=FakeOneMinuteProvider(), sink=outcome_adapter)
    provider = BudgetClient()
    planning = FakePlanningData()
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=data,
        client=provider,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=lambda: 0.0,
        sleep=lambda _: asyncio.sleep(0),
    )
    runtime.health.data_ready = True
    runtime.health.acknowledgements = {market.identity.coin for market in markets}
    coordinator = MultiAssetShadowCoordinator(
        registry=registry,
        data_authority=data,
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
        data_authority=data,
        evidence=evidence,
        outbox=outbox,
        outcome_adapter=outcome_adapter,
        outcome_engine=outcome,
        planning_data=planning,  # type: ignore[arg-type]
        coordinator=coordinator,
        runtime=runtime,
        clock=clock.now,
        sleep=lambda _: asyncio.sleep(0),
    )
    reports = []

    async def capture_report(bar, mode):  # type: ignore[no-untyped-def]
        report = await bootstrap.on_finalized_5m(bar, mode)
        reports.append(report)
        return report

    runtime.on_finalized_5m = capture_report
    runtime.on_maintenance_5m = bootstrap.on_maintenance_5m

    recovery = asyncio.run(
        bootstrap.process_boundary(history_boundary, BoundaryMode.COLD_START_CONTEXT_ONLY)
    )
    assert recovery.failures == ()
    assert recovery.scanner_run_count == 0
    assert recovery.formal_shadow_order_ids == ()
    assert set(recovery.evaluated_market_ids) == {market.identity.market_id for market in markets}
    assert (
        evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
           WHERE record_type IN ('formal_signal', 'plan_record', 'shadow_order',
                                 'notification_outbox_reference')"""
        ).fetchone()[0]
        == 0
    )
    assert outcome.attached_shadow_ids == ()

    continuations = tuple(coordinator._continuations.values())
    assert len(continuations) == MARKET_COUNT
    assert all(state.total_5m == HISTORY_5M for state in continuations)
    assert all(state.total_15m == HISTORY_15M for state in continuations)
    assert all(state.total_1h == HISTORY_1H for state in continuations)
    assert all(
        (len(state.bars_5m), len(state.bars_15m), len(state.bars_1h)) == (21, 98, 10)
        for state in continuations
    )

    first_eligible_index = 44
    recovery_rows_per_market = HISTORY_5M - first_eligible_index
    strategy_count = int(
        evidence._connection.execute(
            "SELECT COUNT(*) FROM immutable_records WHERE record_type='strategy_evaluation'"
        ).fetchone()[0]
    )
    assert strategy_count == MARKET_COUNT * recovery_rows_per_market
    checkpoint_count = int(
        evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
               WHERE record_type='strategy_evaluation'
                 AND json_extract(payload_json, '$.continuation.checkpoint') = 1"""
        ).fetchone()[0]
    )
    assert checkpoint_count <= MARKET_COUNT * (HISTORY_5M // 64 + 2)
    payload_bounds = evidence._connection.execute(
        """SELECT MIN(length(payload_json)), MAX(length(payload_json))
           FROM immutable_records WHERE record_type='strategy_evaluation'"""
    ).fetchone()
    min_payload_bytes, max_payload_bytes = int(payload_bounds[0]), int(payload_bounds[1])
    assert max_payload_bytes < 100_000
    sampled_checkpoint_sizes = tuple(
        int(row[0])
        for row in evidence._connection.execute(
            """SELECT length(payload_json) FROM immutable_records
               WHERE record_type='strategy_evaluation'
                 AND json_extract(payload_json, '$.market_id') = ?
                 AND json_extract(payload_json, '$.source_open_time_ms') IN (?, ?, ?)
               ORDER BY json_extract(payload_json, '$.source_open_time_ms')""",
            (
                markets[0].identity.market_id,
                START_OPEN_MS + 575 * FIVE_MINUTES_MS,
                START_OPEN_MS + 1_151 * FIVE_MINUTES_MS,
                history_boundary,
            ),
        )
    )
    assert len(sampled_checkpoint_sizes) == 3
    assert max(sampled_checkpoint_sizes) - min(sampled_checkpoint_sizes) < 10_000
    evidence_page_size = int(evidence._connection.execute("PRAGMA page_size").fetchone()[0])
    evidence_page_count = int(evidence._connection.execute("PRAGMA page_count").fetchone()[0])
    evidence_db_bytes = evidence_page_size * evidence_page_count
    assert evidence_db_bytes < strategy_count * 100_000

    # The final scale gate is a durable restart, not an in-memory continuation.
    bootstrap.close()
    evidence = EvidenceStore(tmp_path / "evidence.sqlite")
    evidence.reset_query_counters()
    closed.reset_access_counters()
    outbox = EvidenceOutbox(evidence)
    outcome_adapter = EvidenceOutcomeAdapter(evidence)
    outcome = OutcomeEngine(provider=FakeOneMinuteProvider(), sink=outcome_adapter)
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=data,
        client=provider,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=lambda: 0.0,
        sleep=lambda _: asyncio.sleep(0),
    )
    runtime.health.data_ready = True
    runtime.health.acknowledgements = {market.identity.coin for market in markets}
    coordinator = MultiAssetShadowCoordinator(
        registry=registry,
        data_authority=data,
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
        data_authority=data,
        evidence=evidence,
        outbox=outbox,
        outcome_adapter=outcome_adapter,
        outcome_engine=outcome,
        planning_data=planning,  # type: ignore[arg-type]
        coordinator=coordinator,
        runtime=runtime,
        clock=clock.now,
        sleep=lambda _: asyncio.sleep(0),
    )
    runtime.on_finalized_5m = capture_report
    runtime.on_maintenance_5m = bootstrap.on_maintenance_5m
    assert evidence.query_counters["strategy.latest"].returned_rows == MARKET_COUNT
    assert evidence.query_counters["strategy.checkpoint"].returned_rows == MARKET_COUNT
    assert closed.access_counters.returned_rows <= MARKET_COUNT * 63
    assert closed.access_counters.decoded_rows <= MARKET_COUNT * 63
    assert coordinator.pending_formal_decisions() == ()
    assert (
        evidence._connection.execute(
            """SELECT COUNT(*) FROM immutable_records
               WHERE record_type IN ('formal_signal', 'plan_record', 'shadow_order')"""
        ).fetchone()[0]
        == 0
    )

    live_boundary = START_OPEN_MS + HISTORY_5M * FIVE_MINUTES_MS
    clock.value_ms = live_boundary + FIVE_MINUTES_MS + 5_000
    planning.calls.clear()
    closed.reset_access_counters()
    evidence.reset_query_counters()
    asyncio.run(runtime.process_cohort_boundary(live_boundary))
    assert len(reports) == 1
    live = reports[0]
    assert live.failures == ()
    assert live.scanner_run_count == 1
    assert set(live.evaluated_market_ids) == {market.identity.market_id for market in markets}
    live_rows = evidence._connection.execute(
        """SELECT json_extract(payload_json, '$.market_id')
           FROM immutable_records
           WHERE record_type='strategy_evaluation'
             AND json_extract(payload_json, '$.evaluation_mode')='LIVE_ACTIONABLE'
             AND json_extract(payload_json, '$.source_open_time_ms')=?""",
        (live_boundary,),
    ).fetchall()
    assert {str(row[0]) for row in live_rows} == {market.identity.market_id for market in markets}
    assert len(live_rows) == MARKET_COUNT
    scanner = evidence._connection.execute(
        "SELECT payload_json FROM immutable_records WHERE record_type='scanner_evidence'"
    ).fetchone()
    assert scanner is not None
    assert len(json.loads(str(scanner[0]))["observations"]) == MARKET_COUNT
    assert planning.calls.count("SCANNER_L2") == MARKET_COUNT
    assert len(provider.calls) == MARKET_COUNT * 2
    assert all(end_ms - start_ms == FIVE_MINUTES_MS for _, start_ms, end_ms in provider.calls)
    assert runtime.health.callback_failures == []
    assert closed.access_counters.returned_rows <= MARKET_COUNT * 39 + 13 + 1
    assert closed.access_counters.decoded_rows <= MARKET_COUNT * 39 + 13 + 1

    latest_payloads = tuple(
        json.loads(str(row[0]))
        for row in evidence._connection.execute(
            """SELECT payload_json FROM immutable_records
               WHERE record_type='strategy_evaluation'
                 AND json_extract(payload_json, '$.evaluation_mode')='LIVE_ACTIONABLE'
                 AND json_extract(payload_json, '$.source_open_time_ms')=?""",
            (live_boundary,),
        )
    )
    assert len(latest_payloads) == MARKET_COUNT
    assert all(item["representation_version"] == REPRESENTATION_VERSION for item in latest_payloads)
    assert all(len(item["authoritative_input"]["source_bars"]) == 21 for item in latest_payloads)
    assert all(len(item["continuation"]["bars_5m"]) == 21 for item in latest_payloads)
    assert all(len(item["continuation"]["bars_15m"]) <= 98 for item in latest_payloads)
    assert all(len(item["continuation"]["bars_1h"]) <= 10 for item in latest_payloads)

    print(
        "ISSUE119_20X2304_EVIDENCE="
        + json.dumps(
            {
                "markets": MARKET_COUNT,
                "history_5m_per_market": HISTORY_5M,
                "derived_15m_per_market": HISTORY_15M,
                "derived_1h_per_market": HISTORY_1H,
                "strategy_recovery_rows": strategy_count,
                "strategy_checkpoint_rows": checkpoint_count,
                "strategy_payload_min_bytes": min_payload_bytes,
                "strategy_payload_max_bytes": max_payload_bytes,
                "evidence_db_bytes_before_live": evidence_db_bytes,
                "finality_calls": len(provider.calls),
                "scanner_l2_calls": planning.calls.count("SCANNER_L2"),
                "live_strategy_rows": len(live_rows),
                "live_closed_rows_decoded": closed.access_counters.decoded_rows,
            },
            sort_keys=True,
        )
    )
    bootstrap.close()
    closed.close()
