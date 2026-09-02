"""Decisive regressions for the post-G11 whole-cohort liveness contract."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from scripts import run_three_setup_g11_probe as probe
from trader_assist_v0.multi_asset_shadow.bootstrap import (
    BoundaryDisposition,
    BoundaryReport,
    MultiAssetProductionBootstrap,
)
from trader_assist_v0.multi_asset_shadow.cohort_finality import (
    Closed5mCohortFinality,
    FinalityMarketRequest,
    FinalityOutcome,
)
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
    HyperliquidPublicPlanningAdapter,
)
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode

FIVE_MINUTES_MS = 300_000
T = 100 * FIVE_MINUTES_MS


def _candle(coin: str, open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + FIVE_MINUTES_MS - 1,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "10",
    }


def test_public_client_optional_timeout_is_positive_and_never_exceeds_default() -> None:
    observed: list[float] = []

    def post(_url: str, body: bytes, timeout: float) -> bytes:
        observed.append(timeout)
        payload = json.loads(body)
        request = payload["req"]
        return json.dumps([_candle(request["coin"], request["startTime"])]).encode()

    client = HyperliquidPublicClient(post=post, timeout_seconds=15.0)
    client.closed_candles(
        coin="BTC", interval="5m", start_ms=T, end_ms=T + FIVE_MINUTES_MS
    )
    client.closed_candles(
        coin="BTC",
        interval="5m",
        start_ms=T,
        end_ms=T + FIVE_MINUTES_MS,
        timeout_seconds=2.5,
    )
    client.closed_candles(
        coin="BTC",
        interval="5m",
        start_ms=T,
        end_ms=T + FIVE_MINUTES_MS,
        timeout_seconds=30.0,
    )
    assert observed == [15.0, 2.5, 15.0]
    with pytest.raises(ValueError, match="positive"):
        client.l2_book(coin="BTC", timeout_seconds=0)
    with pytest.raises(ValueError, match="positive"):
        HyperliquidPublicClient(timeout_seconds=0)


def test_finality_and_l2_raw_reads_receive_remaining_boundary_budget() -> None:
    candle_timeouts: list[float] = []

    def candle_post(_url: str, body: bytes, timeout: float) -> bytes:
        candle_timeouts.append(timeout)
        request = json.loads(body)["req"]
        return json.dumps([_candle(request["coin"], request["startTime"])]).encode()

    client = HyperliquidPublicClient(post=candle_post)
    market = SimpleNamespace(identity=SimpleNamespace(market_id="market-1", coin="BTC"))

    async def no_sleep(_: float) -> None:
        return None

    finality = Closed5mCohortFinality(
        client=client,
        clock=lambda: datetime.fromtimestamp((T + FIVE_MINUTES_MS + 4_000) / 1000, UTC),
        monotonic=time.monotonic,
        sleep=no_sleep,
        confirmation_concurrency=4,
    )

    async def prove() -> object:
        return await finality.prove_cohort(
            requests=(FinalityMarketRequest(market=market, boundary_open_ms=T),),
            deadline_monotonic=time.monotonic() + 2.0,
        )

    results = asyncio.run(prove())
    assert results[0].outcome is FinalityOutcome.FINALIZED
    assert len(candle_timeouts) == 2
    assert all(0 < timeout <= 2.0 for timeout in candle_timeouts)

    l2_timeouts: list[float] = []

    def l2_post(_url: str, _body: bytes, timeout: float) -> bytes:
        l2_timeouts.append(timeout)
        return b'{}'

    bootstrap = MultiAssetProductionBootstrap.__new__(MultiAssetProductionBootstrap)
    bootstrap.planning_data = HyperliquidPublicPlanningAdapter(
        HyperliquidPublicClient(post=l2_post)
    )
    bootstrap._fetch_raw_l2_with_budget(market, 1.75)
    assert l2_timeouts == [1.75]
    source = inspect.getsource(MultiAssetProductionBootstrap)
    assert source.count("self._fetch_raw_l2_with_budget") == 2  # Scanner and Formal


class _FakeApplication:
    def __init__(self, *, emit: bool, duplicate: bool = False) -> None:
        ids = tuple(f"market-{index:02d}" for index in range(20))
        markets = tuple(
            SimpleNamespace(
                identity=SimpleNamespace(market_id=market_id),
                lifecycle=MarketLifecycle.ACTIVE,
            )
            for market_id in ids
        )
        self.report = BoundaryReport(
            boundary_open_time_ms=T,
            evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
            disposition=BoundaryDisposition.PROCESSED,
            scanner_run_count=1,
            evaluated_market_ids=ids,
            formal_shadow_order_ids=(),
            plan_rejections=(),
            failures=(),
        )

        async def production_callback(_bar: object, _mode: BoundaryMode) -> BoundaryReport:
            return self.report

        self.runtime = SimpleNamespace(
            on_finalized_5m=production_callback,
            health=SimpleNamespace(boundary_diagnostics=[]),
        )
        self.bootstrap = SimpleNamespace(
            runtime=self.runtime,
            registry=SimpleNamespace(
                active=lambda: SimpleNamespace(markets=markets)
            ),
        )
        self.emit = emit
        self.duplicate = duplicate
        self.shutdown_observed = False

    async def run(self, shutdown: asyncio.Event) -> None:
        if self.emit:
            await self.runtime.on_finalized_5m(
                SimpleNamespace(open_time_ms=T), BoundaryMode.LIVE_ACTIONABLE
            )
            if self.duplicate:
                await self.runtime.on_finalized_5m(
                    SimpleNamespace(open_time_ms=T), BoundaryMode.LIVE_ACTIONABLE
                )
        await shutdown.wait()
        self.shutdown_observed = True


def test_g11_probe_observes_real_report_counts_and_clean_shutdown() -> None:
    application = _FakeApplication(emit=True)
    result = asyncio.run(
        probe.qualify_application(
            application,  # type: ignore[arg-type]
            qualification_timeout_seconds=1,
            duplicate_observation_seconds=0,
        )
    )
    assert result["status"] == "PASS"
    assert result["callback_report_count"] == 1
    assert result["scanner_run_count"] == 1
    assert result["strategy_market_count"] == 20
    assert application.shutdown_observed


def test_g11_probe_timeout_is_structured_semantic_fail_and_shutdown() -> None:
    application = _FakeApplication(emit=False)
    result = asyncio.run(
        probe.qualify_application(
            application,  # type: ignore[arg-type]
            qualification_timeout_seconds=0.01,
            duplicate_observation_seconds=0,
        )
    )
    assert result["status"] == "FAIL"
    assert result["reason"] == "NO_LIVE_ACTIONABLE_COHORT_WITHIN_BOUNDED_WINDOW"
    assert result["callback_report_count"] == 0
    assert application.shutdown_observed


def test_g11_probe_rejects_duplicate_callback_for_one_boundary() -> None:
    application = _FakeApplication(emit=True, duplicate=True)
    result = asyncio.run(
        probe.qualify_application(
            application,  # type: ignore[arg-type]
            qualification_timeout_seconds=1,
            duplicate_observation_seconds=0,
        )
    )
    assert result["status"] == "FAIL"
    assert result["reason"] == "DUPLICATE_LIVE_ACTIONABLE_CALLBACK"
    assert result["duplicate_callback_count"] == 1


def test_g11_probe_is_default_off_and_always_emits_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert probe.main(()) == 1
    line = capsys.readouterr().out.strip()
    assert line.startswith("G11_RESULT=")
    assert json.loads(line.removeprefix("G11_RESULT="))["status"] == "FAIL"
