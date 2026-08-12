"""Explicit per-market generation authority for closed-candle finality.

The coordinator owns candidate supersession, one worker per market, and the
global confirmation bound. A worker may finish transport for an obsolete
generation, but only the latest immutable generation token can reach the
admission callback.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from .models import RegistryMarket

FIVE_MINUTES_MS: Final = 300_000
POST_CLOSE_HOLD_MS: Final = 3_000
TARGET_CONFIRMATIONS: Final = 2
MIN_MONOTONIC_CONFIRMATION_GAP_MS: Final = 1_000


@dataclass(frozen=True)
class FinalityIdentity:
    """The provider candle identity governed by one generation stream."""

    market_id: str
    interval: str
    open_time_ms: int


@dataclass(frozen=True)
class CandidateGeneration:
    """An immutable authority token for one exact candidate payload."""

    identity: FinalityIdentity
    fingerprint: str
    sequence: int
    market: RegistryMarket


class ConfirmationResult(StrEnum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    STALE = "STALE"


ConfirmGeneration = Callable[[CandidateGeneration], Awaitable[ConfirmationResult]]
DiscardCandidate = Callable[[FinalityIdentity], None]
MarkFailed = Callable[[str], None]


class GenerationFinalityAuthority:
    """Bounded latest-generation scheduler for all selected markets."""

    def __init__(
        self,
        *,
        confirm: ConfirmGeneration,
        discard: DiscardCandidate,
        mark_failed: MarkFailed,
        now_ms: Callable[[], int],
        sleep: Callable[[float], Awaitable[None]],
        confirmation_concurrency: int,
    ) -> None:
        if confirmation_concurrency < 1:
            raise ValueError("confirmation concurrency must be positive")
        self._confirm = confirm
        self._discard = discard
        self._mark_failed = mark_failed
        self._now_ms = now_ms
        self._sleep = sleep
        self._slots = asyncio.Semaphore(confirmation_concurrency)
        self._latest: dict[str, CandidateGeneration] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._sequences: dict[str, int] = {}
        self._closed = False

    @property
    def pending(self) -> Mapping[str, CandidateGeneration]:
        return MappingProxyType(self._latest)

    @property
    def tasks(self) -> Mapping[str, asyncio.Task[None]]:
        return MappingProxyType(self._tasks)

    def latest(self, market_id: str) -> CandidateGeneration | None:
        return self._latest.get(market_id)

    def task_for(self, market_id: str) -> asyncio.Task[None] | None:
        return self._tasks.get(market_id)

    def is_latest(self, generation: CandidateGeneration) -> bool:
        return self._latest.get(generation.identity.market_id) == generation

    def offer(
        self, *, market: RegistryMarket, open_time_ms: int, fingerprint: str
    ) -> CandidateGeneration:
        """Coalesce an exact duplicate or advance the market generation."""
        if self._closed:
            raise RuntimeError("finality authority is closed")
        identity = FinalityIdentity(market.identity.market_id, "5m", open_time_ms)
        current = self._latest.get(identity.market_id)
        if (
            current is not None
            and current.identity == identity
            and current.fingerprint == fingerprint
        ):
            return current
        if current is not None and current.identity != identity:
            self._discard(current.identity)
        sequence = self._sequences.get(identity.market_id, 0) + 1
        self._sequences[identity.market_id] = sequence
        generation = CandidateGeneration(identity, fingerprint, sequence, market)
        self._latest[identity.market_id] = generation
        task = self._tasks.get(identity.market_id)
        if task is None or task.done():
            self._tasks[identity.market_id] = asyncio.create_task(
                self._run_market(identity.market_id),
                name=f"candle-finality:{identity.market_id}",
            )
        return generation

    async def _run_market(self, market_id: str) -> None:
        task = asyncio.current_task()
        try:
            while (generation := self._latest.get(market_id)) is not None:
                eligible_ms = (
                    generation.identity.open_time_ms
                    + FIVE_MINUTES_MS
                    + POST_CLOSE_HOLD_MS
                )
                delay = max(0.0, (eligible_ms - self._now_ms()) / 1_000)
                if delay:
                    await self._sleep(delay)
                if not self.is_latest(generation):
                    continue
                async with self._slots:
                    if not self.is_latest(generation):
                        continue
                    try:
                        result = await self._confirm(generation)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        result = ConfirmationResult.FAILED
                if not self.is_latest(generation):
                    continue
                if result is not ConfirmationResult.COMPLETE:
                    # A current token cannot declare itself stale. Treat the
                    # inconsistency as a fail-closed path, never as admission.
                    result = ConfirmationResult.FAILED
                self._latest.pop(market_id, None)
                if result is ConfirmationResult.FAILED:
                    self._discard(generation.identity)
                    self._mark_failed(market_id)
                return
        finally:
            if self._tasks.get(market_id) is task:
                self._tasks.pop(market_id, None)

    async def invalidate_all(self) -> None:
        """Invalidate connection-bound paths and drain their asyncio tasks."""
        generations = tuple(self._latest.values())
        self._latest.clear()
        for generation in generations:
            self._discard(generation.identity)
        tasks = tuple(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    async def close(self) -> None:
        self._closed = True
        await self.invalidate_all()
