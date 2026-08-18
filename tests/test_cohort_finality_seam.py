"""PHASE 1 frozen contract: Closed5mCohortFinality typed seam.

Packet sections 6C, 7, 8, 9, and ruling 3.  The live finality seam is a
provider-proof worker only: it receives Barrier-approved MISSING_LIVE_ELIGIBLE
markets, proves the exact-T row through the current provider policy, and
returns typed per-market results.  It owns no sticky failure or processed
authority, performs no historical prefix recovery, and lets CancelledError
propagate.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from functools import wraps

import pytest

from trader_assist_v0.multi_asset_shadow.cohort_finality import (
    Closed5mCohortFinality,
    FinalityMarketRequest,
    FinalityMarketResult,
    FinalityOutcome,
)
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import PublicDataError

FIVE_MINUTES_MS = 300_000
T = 100 * FIVE_MINUTES_MS


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def _now() -> datetime:
    return datetime.fromtimestamp((T + FIVE_MINUTES_MS + 4_000) / 1000, UTC)


def _candle(open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": "BTC",
        "t": open_ms,
        "T": open_ms + FIVE_MINUTES_MS - 1,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "10",
    }


class FakeMarket:
    def __init__(self, market_id: str, coin: str) -> None:
        self.identity = type("Identity", (), {"market_id": market_id, "coin": coin})()


class FakeTransport:
    """Synchronous provider transport; deliberately not a real client."""

    def __init__(self, *, response: object = None, error: Exception | None = None) -> None:
        self.response = response if response is not None else [_candle(T)]
        self.error = error
        self.calls: list[tuple[str, int, int]] = []
        self.lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0
        self.delay_seconds = 0.0
        self.release = threading.Event()
        self.blocking = False

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        with self.lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.calls.append((coin, start_ms, end_ms))
        try:
            if self.blocking:
                self.release.wait(timeout=5.0)
            elif self.delay_seconds:
                time.sleep(self.delay_seconds)
            if self.error is not None:
                raise self.error
            if callable(self.response):
                return self.response(coin, start_ms, end_ms)
            return self.response
        finally:
            with self.lock:
                self.in_flight -= 1


def _finality(transport: FakeTransport, *, monotonic=None, sleep=None) -> Closed5mCohortFinality:
    return Closed5mCohortFinality(
        client=transport,  # type: ignore[arg-type]
        clock=_now,
        monotonic=monotonic or time.monotonic,
        sleep=sleep or asyncio.sleep,
        confirmation_concurrency=4,
    )


async def _prove(
    finality: Closed5mCohortFinality,
    *,
    market_ids: tuple[str, ...] = ("market-1",),
    deadline_monotonic: float,
) -> tuple[FinalityMarketResult, ...]:
    requests = tuple(
        FinalityMarketRequest(market=FakeMarket(market_id, "BTC"), boundary_open_ms=T)
        for market_id in market_ids
    )
    return await finality.prove_cohort(
        requests=requests, deadline_monotonic=deadline_monotonic
    )


def test_outcome_enum_is_the_frozen_typed_contract() -> None:
    assert {member.value for member in FinalityOutcome} == {
        "FINALIZED",
        "RECOVERABLE_FAILURE",
        "NONRECOVERABLE_FAILURE",
        "DEADLINE_EXCEEDED",
    }


@async_test
async def test_exact_t_proof_returns_finalized_with_payloads() -> None:
    transport = FakeTransport()
    results = await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    assert len(results) == 1
    result = results[0]
    assert result.outcome is FinalityOutcome.FINALIZED
    assert result.market_id == "market-1"
    assert result.boundary_open_ms == T
    assert result.confirmed_payload is not None and result.confirmed_payload["t"] == T
    assert result.stable_payload == result.confirmed_payload
    # Current provider policy: exactly two targeted exact-T confirmations.
    assert transport.calls == [("BTC", T, T + FIVE_MINUTES_MS)] * 2


@async_test
async def test_provider_transport_error_is_recoverable_failure() -> None:
    transport = FakeTransport(error=PublicDataError("provider unavailable"))
    results = await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    assert results[0].outcome is FinalityOutcome.RECOVERABLE_FAILURE
    assert results[0].error_type == "PublicDataError"


@async_test
async def test_unknown_exception_is_nonrecoverable_finality_unknown() -> None:
    transport = FakeTransport(error=RuntimeError("unexpected internal defect"))
    results = await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    assert results[0].outcome is FinalityOutcome.NONRECOVERABLE_FAILURE
    assert results[0].stage == "finality_unknown"
    assert results[0].error_type == "RuntimeError"


@async_test
async def test_missing_or_duplicate_exact_t_fails_closed_without_payload() -> None:
    transport = FakeTransport(response=[])
    results = await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    assert results[0].outcome is FinalityOutcome.RECOVERABLE_FAILURE
    assert results[0].confirmed_payload is None

    duplicate = FakeTransport(response=[_candle(T), _candle(T)])
    results = await _prove(_finality(duplicate), deadline_monotonic=time.monotonic() + 60.0)
    assert results[0].outcome is FinalityOutcome.RECOVERABLE_FAILURE


@async_test
async def test_conflicting_two_observations_fail_closed() -> None:
    transport = FakeTransport()

    def responses(coin: str, start_ms: int, end_ms: int) -> list[dict[str, object]]:
        payload = _candle(T)
        payload["c"] = "101" if len(transport.calls) > 1 else "100"
        return [payload]

    transport.response = responses
    results = await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    assert results[0].outcome is FinalityOutcome.RECOVERABLE_FAILURE
    assert transport.calls


@async_test
async def test_deadline_exceeded_when_budget_is_exhausted() -> None:
    class BumpMonotonic:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    mono = BumpMonotonic()
    transport = FakeTransport()
    # The first targeted confirmation returns only after the hard action
    # deadline has passed; the second confirmation must never be issued.
    original = transport.closed_candles

    def bump_then_respond(**kwargs: object) -> object:
        result = original(**kwargs)  # type: ignore[arg-type]
        mono.value = 1000.0
        return result

    transport.closed_candles = bump_then_respond  # type: ignore[method-assign]
    results = await _prove(
        _finality(transport, monotonic=mono), deadline_monotonic=60.0
    )
    assert results[0].outcome is FinalityOutcome.DEADLINE_EXCEEDED
    assert results[0].confirmed_payload is None
    assert len(transport.calls) == 1


@async_test
async def test_already_expired_deadline_starts_no_provider_request() -> None:
    transport = FakeTransport()
    results = await _prove(
        _finality(transport, monotonic=lambda: 60.0), deadline_monotonic=60.0
    )
    assert results[0].outcome is FinalityOutcome.DEADLINE_EXCEEDED
    assert results[0].confirmed_payload is None
    assert transport.calls == []


@async_test
async def test_confirmation_gap_crossing_deadline_starts_no_next_provider_request() -> None:
    class Monotonic:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    monotonic = Monotonic()

    async def cross_deadline_after_gap(seconds: float) -> None:
        assert seconds == 1.0
        monotonic.value = 60.0

    transport = FakeTransport()
    results = await _prove(
        _finality(transport, monotonic=monotonic, sleep=cross_deadline_after_gap),
        deadline_monotonic=60.0,
    )
    assert results[0].outcome is FinalityOutcome.DEADLINE_EXCEEDED
    assert transport.calls == [("BTC", T, T + FIVE_MINUTES_MS)]


@async_test
async def test_semaphore_wait_crossing_deadline_does_not_start_waiting_provider() -> None:
    class Monotonic:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    started = threading.Event()
    release = threading.Event()

    class BlockingFirst(FakeTransport):
        def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
            self.calls.append((coin, start_ms, end_ms))
            if coin == "FIRST":
                started.set()
                assert release.wait(timeout=5.0)
            return [_candle(start_ms)]

    monotonic = Monotonic()
    transport = BlockingFirst()
    finality = Closed5mCohortFinality(
        client=transport,  # type: ignore[arg-type]
        clock=_now,
        monotonic=monotonic,
        sleep=asyncio.sleep,
        confirmation_concurrency=1,
    )
    task = asyncio.create_task(
        finality.prove_cohort(
            requests=(
                FinalityMarketRequest(FakeMarket("first", "FIRST"), T),
                FinalityMarketRequest(FakeMarket("second", "SECOND"), T),
            ),
            deadline_monotonic=60.0,
        )
    )
    await asyncio.to_thread(started.wait, 5.0)
    monotonic.value = 60.0
    release.set()
    results = await task
    assert {result.outcome for result in results} == {FinalityOutcome.DEADLINE_EXCEEDED}
    assert [call[0] for call in transport.calls] == ["FIRST"]


@async_test
async def test_late_provider_result_is_discarded_before_finality_admission() -> None:
    class Monotonic:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    started = threading.Event()
    release = threading.Event()

    class Blocking(FakeTransport):
        def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
            self.calls.append((coin, start_ms, end_ms))
            started.set()
            assert release.wait(timeout=5.0)
            return [_candle(start_ms)]

    monotonic = Monotonic()
    transport = Blocking()
    task = asyncio.create_task(
        _prove(
            _finality(transport, monotonic=monotonic), deadline_monotonic=60.0
        )
    )
    await asyncio.to_thread(started.wait, 5.0)
    monotonic.value = 60.0
    release.set()
    results = await task
    result = results[0]
    assert result.outcome is FinalityOutcome.DEADLINE_EXCEEDED
    assert result.confirmed_payload is None
    assert result.stable_payload is None
    assert transport.calls == [("BTC", T, T + FIVE_MINUTES_MS)]


@async_test
async def test_one_market_failure_does_not_cancel_sibling_proof_tasks() -> None:
    calls: list[str] = []

    class Split(FakeTransport):
        def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
            calls.append(coin)
            if coin == "BAD":
                raise RuntimeError("one defective market")
            return [_candle(start_ms)]

    transport = Split()
    finality = Closed5mCohortFinality(
        client=transport,  # type: ignore[arg-type]
        clock=_now,
        monotonic=time.monotonic,
        sleep=asyncio.sleep,
        confirmation_concurrency=4,
    )
    requests = (
        FinalityMarketRequest(market=FakeMarket("market-1", "GOOD"), boundary_open_ms=T),
        FinalityMarketRequest(market=FakeMarket("market-2", "BAD"), boundary_open_ms=T),
    )
    results = await finality.prove_cohort(
        requests=requests, deadline_monotonic=time.monotonic() + 60.0
    )
    by_market = {result.market_id: result.outcome for result in results}
    assert by_market["market-1"] is FinalityOutcome.FINALIZED
    assert by_market["market-2"] is FinalityOutcome.NONRECOVERABLE_FAILURE
    # Both confirmations for the healthy sibling completed despite the defect.
    assert calls.count("GOOD") == 2


@async_test
async def test_concurrency_is_bounded_by_the_confirmation_limit() -> None:
    transport = FakeTransport()
    transport.delay_seconds = 0.02
    finality = Closed5mCohortFinality(
        client=transport,  # type: ignore[arg-type]
        clock=_now,
        monotonic=time.monotonic,
        sleep=asyncio.sleep,
        confirmation_concurrency=4,
    )
    requests = tuple(
        FinalityMarketRequest(market=FakeMarket(f"market-{index}", "BTC"), boundary_open_ms=T)
        for index in range(8)
    )
    results = await finality.prove_cohort(
        requests=requests, deadline_monotonic=time.monotonic() + 30.0
    )
    assert all(result.outcome is FinalityOutcome.FINALIZED for result in results)
    assert len(transport.calls) == 16
    assert transport.max_in_flight <= 4


@async_test
async def test_cancelled_error_propagates_cleanly() -> None:
    transport = FakeTransport()
    transport.blocking = True
    finality = _finality(transport)
    task = asyncio.create_task(
        _prove(finality, deadline_monotonic=time.monotonic() + 30.0)
    )
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    transport.release.set()


@async_test
async def test_no_historical_prefix_recovery_inside_live_finality() -> None:
    transport = FakeTransport()
    await _prove(_finality(transport), deadline_monotonic=time.monotonic() + 60.0)
    for _coin, start_ms, end_ms in transport.calls:
        assert start_ms == T
        assert end_ms == T + FIVE_MINUTES_MS


@async_test
async def test_finality_keeps_no_processed_or_failure_cache() -> None:
    transport = FakeTransport(error=PublicDataError("first attempt fails"))
    finality = _finality(transport)
    first = await _prove(finality, deadline_monotonic=time.monotonic() + 60.0)
    assert first[0].outcome is FinalityOutcome.RECOVERABLE_FAILURE
    # The seam is stateless proof work: a second Barrier-requested proof for
    # the same market/T performs provider work again instead of answering
    # from an internal sticky processed/failure cache.
    transport.error = None
    second = await _prove(finality, deadline_monotonic=time.monotonic() + 60.0)
    assert second[0].outcome is FinalityOutcome.FINALIZED
    assert len(transport.calls) == 3
