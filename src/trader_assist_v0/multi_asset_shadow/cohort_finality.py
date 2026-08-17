"""Cohort-boundary finality seam: coordination separated from transport policy.

The runtime's clock-driven 5m cohort barrier owns WHEN a boundary is
reconciled; a :class:`Closed5mCohortFinality` policy owns HOW provider
evidence proves it.  The current First-Launch policy is strict dual-REST
provider-authoritative confirmation.  A future WS+REST hybrid or other
provider/node-backed finality source can replace the policy object without
touching Bootstrap, Scanner, Strategy, Registry, or EvidenceStore.

This module creates no durable state: it is scheduling-free, transport
policy only, and every durable admission still flows through the unchanged
Data authority.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Protocol

from .data import DataRouteError, MultiAssetDataAuthority
from .finality import (
    FIVE_MINUTES_MS,
    MIN_MONOTONIC_CONFIRMATION_GAP_MS,
    POST_CLOSE_HOLD_MS,
    TARGET_CONFIRMATIONS,
)
from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import ClosedBar, RegistryMarket

# Mirrors the warmup history bound: one boundary may repair at most the same
# bounded history window a cold start would admit.
_PREFIX_BACKFILL_BARS: Final = 2_304


@dataclass(frozen=True)
class CohortFinalityFailure:
    """One market the policy could not prove at the boundary."""

    market_id: str
    reason: str


@dataclass(frozen=True)
class CohortFinalityResult:
    """Provider-authoritative outcome of one cohort boundary proof."""

    boundary_open_time_ms: int
    finalized: tuple[ClosedBar, ...]
    failures: tuple[CohortFinalityFailure, ...]


class Closed5mCohortFinality(Protocol):
    """Provider-evidence policy for one exact 5m cohort boundary."""

    async def confirm_cohort_boundary(
        self,
        *,
        markets: Sequence[RegistryMarket],
        boundary_open_time_ms: int,
        deadline_ms: int,
    ) -> CohortFinalityResult: ...


class RestCohortFinality:
    """Current First-Launch policy: strict dual targeted REST confirmation.

    Every market of the captured cohort is proven at boundary ``T`` by exactly
    ``TARGET_CONFIRMATIONS`` provider observations separated by at least
    ``MIN_MONOTONIC_CONFIRMATION_GAP_MS``.  Each observation must contain
    exactly one exact-T candle, both exact-T payloads must be
    canonical-identical, and admission flows through the unchanged immutable
    ClosedBar + strict continuity/gap/conflict + Registry-binding authority.
    Provider end-inclusive echoes (``T+5m`` or a still-forming bar) are
    ignored as non-target evidence.  No synthetic candle is ever created.
    """

    def __init__(
        self,
        *,
        client: HyperliquidPublicClient,
        authority: MultiAssetDataAuthority,
        clock: Callable[[], datetime],
        monotonic: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        confirmation_concurrency: int = 4,
    ) -> None:
        if confirmation_concurrency < 1:
            raise ValueError("cohort confirmation concurrency must be positive")
        self._client = client
        self._authority = authority
        self._clock = clock
        self._monotonic = monotonic
        self._sleep = sleep
        self._slots = asyncio.Semaphore(confirmation_concurrency)

    async def confirm_cohort_boundary(
        self,
        *,
        markets: Sequence[RegistryMarket],
        boundary_open_time_ms: int,
        deadline_ms: int,
    ) -> CohortFinalityResult:
        del deadline_ms  # Informational for the current policy: freshness is
        # enforced by the readiness authority, never by dropping evidence.
        finalized: list[ClosedBar] = []
        failures: list[CohortFinalityFailure] = []

        async def prove(market: RegistryMarket) -> None:
            async with self._slots:
                try:
                    bar = await self._prove_market(market, boundary_open_time_ms)
                except (DataRouteError, PublicDataError) as exc:
                    failures.append(
                        CohortFinalityFailure(
                            market.identity.market_id, f"{type(exc).__name__}: {exc}"
                        )
                    )
                    return
            if bar is not None:
                finalized.append(bar)

        if markets:
            await asyncio.gather(*(prove(market) for market in markets))
        return CohortFinalityResult(
            boundary_open_time_ms=boundary_open_time_ms,
            finalized=tuple(finalized),
            failures=tuple(failures),
        )

    async def _prove_market(
        self, market: RegistryMarket, boundary_open_ms: int
    ) -> ClosedBar | None:
        market_id = market.identity.market_id
        last_open = self._authority.store.last_open(market_id)
        if last_open is not None and boundary_open_ms > last_open + FIVE_MINUTES_MS:
            await self._admit_silent_prefix(
                market, last_open_ms=last_open, boundary_open_ms=boundary_open_ms
            )
        observations: list[list[object]] = []
        observed_monotonic: list[float] = []
        for index in range(TARGET_CONFIRMATIONS):
            if index:
                await self._sleep(MIN_MONOTONIC_CONFIRMATION_GAP_MS / 1_000)
            snapshot = await asyncio.to_thread(
                self._client.closed_candles,
                coin=market.identity.coin,
                interval="5m",
                start_ms=boundary_open_ms,
                end_ms=boundary_open_ms + FIVE_MINUTES_MS,
            )
            observed_monotonic.append(self._monotonic())
            if not isinstance(snapshot, list):
                raise PublicDataError("candleSnapshot did not return a list")
            observations.append(snapshot)
        return self._authority.confirm_rest_boundary(
            market=market,
            open_time_ms=boundary_open_ms,
            observation_first=observations[0],
            observation_second=observations[1],
            received_at=self._clock(),
            first_observed_monotonic=observed_monotonic[0],
            second_observed_monotonic=observed_monotonic[1],
            hold_ms=POST_CLOSE_HOLD_MS,
            observation_gap_ms=MIN_MONOTONIC_CONFIRMATION_GAP_MS,
        )

    async def _admit_silent_prefix(
        self, market: RegistryMarket, *, last_open_ms: int, boundary_open_ms: int
    ) -> None:
        """Admit the provider's own closed series before a skipped boundary.

        A startup cooldown or deferred boundary can leave the durable series
        behind the cohort boundary.  The strict prefix ``[last_open+5m, T)``
        enters through the accepted official-history path; the live boundary
        ``T`` itself is proven only by the dual targeted confirmation and is
        never admitted here.
        """
        start_ms = last_open_ms + FIVE_MINUTES_MS
        if boundary_open_ms - start_ms > _PREFIX_BACKFILL_BARS * FIVE_MINUTES_MS:
            raise DataRouteError("cohort boundary prefix backfill exceeds bounded history")
        snapshot = await asyncio.to_thread(
            self._client.closed_candles,
            coin=market.identity.coin,
            interval="5m",
            start_ms=start_ms,
            end_ms=boundary_open_ms,
        )
        if not isinstance(snapshot, list):
            raise PublicDataError("candleSnapshot did not return a list")
        prefix: list[dict[str, object]] = []
        for item in snapshot:
            if not isinstance(item, Mapping) or not isinstance(item.get("t"), int):
                raise DataRouteError("cohort prefix snapshot contains a malformed bar")
            open_ms = item["t"]
            if open_ms > boundary_open_ms:
                raise DataRouteError("cohort prefix snapshot contains future evidence")
            if open_ms < boundary_open_ms:
                prefix.append(dict(item))
        if prefix:
            self._authority.admit_rest_history(
                market=market, snapshot=prefix, received_at=self._clock()
            )
