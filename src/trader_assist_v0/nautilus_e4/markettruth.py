"""Immutable project-owned views over admitted native market data.

This module deliberately accepts primitive values only.  Nautilus owns the
mutable book and transport; consumers receive a hash-bound, immutable top-of-
book fact derived from one admitted native Depth10 update.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex


class MarketTruthRef(BaseModel):
    """A non-mutable, project-owned reference to one admitted market fact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    market_id: str = Field(min_length=64, max_length=64)
    instrument_id: str = Field(min_length=3, max_length=160)
    source_event_id: str = Field(min_length=1, max_length=256)
    ts_event: int = Field(ge=0)
    ts_init: int = Field(ge=0)
    continuity_epoch: str = Field(min_length=1, max_length=160)
    bid_price: str = Field(min_length=1, max_length=80)
    bid_size: str = Field(min_length=1, max_length=80)
    ask_price: str = Field(min_length=1, max_length=80)
    ask_size: str = Field(min_length=1, max_length=80)
    ref_hash: str = Field(min_length=64, max_length=64)

    @classmethod
    def create(cls, **values: object) -> MarketTruthRef:
        digest = sha256_hex(canonical_json_bytes(values))
        return cls.model_validate({**values, "ref_hash": digest})


@dataclass(frozen=True)
class MarketTruthHandoffHealth:
    queued: int
    capacity: int
    dropped: int


class BoundedMarketTruthHandoff:
    """A capture-safe, bounded best-effort handoff for downstream readers."""

    def __init__(self, *, capacity: int = 256) -> None:
        if capacity < 1:
            raise ValueError("MarketTruth handoff capacity must be positive")
        self._capacity = capacity
        self._items: deque[MarketTruthRef] = deque()
        self._dropped = 0

    def offer(self, item: MarketTruthRef) -> None:
        if len(self._items) == self._capacity:
            self._items.popleft()
            self._dropped += 1
        self._items.append(item)

    def drain(self) -> tuple[MarketTruthRef, ...]:
        items = tuple(self._items)
        self._items.clear()
        return items

    @property
    def health(self) -> MarketTruthHandoffHealth:
        return MarketTruthHandoffHealth(
            queued=len(self._items), capacity=self._capacity, dropped=self._dropped
        )
