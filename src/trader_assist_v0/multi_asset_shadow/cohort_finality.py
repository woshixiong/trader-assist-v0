"""Provider-proof seam for current live exact-T cohort finality.

This module is deliberately NOT a global authority.  It receives only
Barrier-classified MISSING_LIVE_ELIGIBLE markets, proves the exact boundary
row through the current provider policy, and returns typed per-market
results.  It keeps no processed-boundary state and no failure state: the
Cohort Barrier owns current-process failure merging and whole-cohort
actionability.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final

from trader_assist_v0.contracts.common import canonical_json_bytes

from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import RegistryMarket

FIVE_MINUTES_MS: Final = 300_000
POST_CLOSE_HOLD_MS: Final = 3_000
TARGET_CONFIRMATIONS: Final = 2
MIN_MONOTONIC_CONFIRMATION_GAP_MS: Final = 1_000


class FinalityOutcome(StrEnum):
    """Typed non-authoritative result of one provider proof attempt."""

    FINALIZED = "FINALIZED"
    RECOVERABLE_FAILURE = "RECOVERABLE_FAILURE"
    NONRECOVERABLE_FAILURE = "NONRECOVERABLE_FAILURE"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"


@dataclass(frozen=True)
class FinalityMarketRequest:
    """One Barrier-approved MISSING_LIVE_ELIGIBLE market at one boundary."""

    market: RegistryMarket
    boundary_open_ms: int


@dataclass(frozen=True)
class FinalityMarketResult:
    market_id: str
    boundary_open_ms: int
    outcome: FinalityOutcome
    confirmed_payload: dict[str, object] | None = None
    stable_payload: dict[str, object] | None = None
    stage: str | None = None
    error_type: str | None = None


class _FinalityProofError(Exception):
    """Fail-closed provider-evidence condition with proven recovery semantics."""


def _exact_observation(snapshot: object, boundary_open_ms: int) -> dict[str, object]:
    """Select the single exact-T provider observation, ignoring later echoes."""
    if not isinstance(snapshot, list):
        raise _FinalityProofError("candleSnapshot did not return a list")
    matches = [
        item
        for item in snapshot
        if isinstance(item, dict) and item.get("t") == boundary_open_ms
    ]
    if len(matches) != 1:
        raise _FinalityProofError("exact-T provider observation is missing or duplicated")
    observation = dict(matches[0])
    if observation.get("i") != "5m":
        raise _FinalityProofError("provider observation is not a 5m candle")
    return observation


class Closed5mCohortFinality:
    """Stateless proof worker for genuinely missing current-live-eligible rows.

    Worker threads carry raw provider transport only; validation and any
    durable admission happen on the event-loop side inside the Cohort
    Barrier.  Ordinary per-market exceptions become typed results so one
    defective market never cancels healthy siblings inside the TaskGroup.
    """

    def __init__(
        self,
        *,
        client: HyperliquidPublicClient,
        clock: Callable[[], datetime],
        monotonic: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
        confirmation_concurrency: int,
    ) -> None:
        if confirmation_concurrency < 1:
            raise ValueError("confirmation concurrency must be positive")
        self._client = client
        self._clock = clock
        self._monotonic = monotonic
        self._sleep = sleep
        self._confirmation_concurrency = confirmation_concurrency

    async def prove_cohort(
        self,
        *,
        requests: tuple[FinalityMarketRequest, ...],
        deadline_monotonic: float,
    ) -> tuple[FinalityMarketResult, ...]:
        """Prove every requested market boundary; never raises ordinary errors."""
        results: dict[str, FinalityMarketResult] = {}
        slots = asyncio.Semaphore(self._confirmation_concurrency)
        async with asyncio.TaskGroup() as group:
            for request in requests:
                group.create_task(
                    self._prove_one(request, deadline_monotonic, slots, results),
                    name=f"cohort-finality:{request.market.identity.market_id}",
                )
        return tuple(
            results[request.market.identity.market_id] for request in requests
        )

    async def _prove_one(
        self,
        request: FinalityMarketRequest,
        deadline_monotonic: float,
        slots: asyncio.Semaphore,
        results: dict[str, FinalityMarketResult],
    ) -> None:
        market = request.market
        market_id = market.identity.market_id
        boundary = request.boundary_open_ms
        try:
            payload = await self._confirm_boundary(
                market=market,
                boundary_open_ms=boundary,
                deadline_monotonic=deadline_monotonic,
                slots=slots,
            )
            results[market_id] = FinalityMarketResult(
                market_id=market_id,
                boundary_open_ms=boundary,
                outcome=FinalityOutcome.FINALIZED,
                confirmed_payload=payload,
                stable_payload=dict(payload),
            )
        except asyncio.CancelledError:
            raise
        except _DeadlineExceeded:
            results[market_id] = FinalityMarketResult(
                market_id=market_id,
                boundary_open_ms=boundary,
                outcome=FinalityOutcome.DEADLINE_EXCEEDED,
                stage="finality_deadline_exceeded",
            )
        except PublicDataError as exc:
            results[market_id] = FinalityMarketResult(
                market_id=market_id,
                boundary_open_ms=boundary,
                outcome=FinalityOutcome.RECOVERABLE_FAILURE,
                error_type=type(exc).__name__,
            )
        except _FinalityProofError as exc:
            results[market_id] = FinalityMarketResult(
                market_id=market_id,
                boundary_open_ms=boundary,
                outcome=FinalityOutcome.RECOVERABLE_FAILURE,
                stage="finality_proof_failed",
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            results[market_id] = FinalityMarketResult(
                market_id=market_id,
                boundary_open_ms=boundary,
                outcome=FinalityOutcome.NONRECOVERABLE_FAILURE,
                stage="finality_unknown",
                error_type=type(exc).__name__,
            )

    async def _confirm_boundary(
        self,
        *,
        market: RegistryMarket,
        boundary_open_ms: int,
        deadline_monotonic: float,
        slots: asyncio.Semaphore,
    ) -> dict[str, object]:
        eligible_ms = boundary_open_ms + FIVE_MINUTES_MS + POST_CLOSE_HOLD_MS
        hold_seconds = (eligible_ms - int(self._clock().timestamp() * 1000)) / 1_000
        if hold_seconds > 0:
            await self._sleep(hold_seconds)
        if self._monotonic() >= deadline_monotonic:
            raise _DeadlineExceeded
        confirmed: dict[str, object] | None = None
        for index in range(TARGET_CONFIRMATIONS):
            if index:
                await self._sleep(MIN_MONOTONIC_CONFIRMATION_GAP_MS / 1_000)
            if self._monotonic() >= deadline_monotonic:
                raise _DeadlineExceeded
            async with slots:
                if self._monotonic() >= deadline_monotonic:
                    raise _DeadlineExceeded
                snapshot = await asyncio.to_thread(
                    self._client.closed_candles,
                    coin=market.identity.coin,
                    interval="5m",
                    start_ms=boundary_open_ms,
                    end_ms=boundary_open_ms + FIVE_MINUTES_MS,
                )
                if self._monotonic() >= deadline_monotonic:
                    raise _DeadlineExceeded
            observation = _exact_observation(snapshot, boundary_open_ms)
            if confirmed is None:
                confirmed = observation
            elif canonical_json_bytes(observation) != canonical_json_bytes(confirmed):
                raise _FinalityProofError("targeted REST confirmation is not exact")
        assert confirmed is not None
        return confirmed


class _DeadlineExceeded(Exception):
    """Internal marker: the hard action deadline passed before proof completed."""
