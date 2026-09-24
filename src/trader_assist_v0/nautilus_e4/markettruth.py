"""Immutable project-owned views over admitted native market data.

This module deliberately accepts primitive values only.  Nautilus owns the
mutable book and transport; consumers receive a hash-bound, immutable top-of-
book fact derived from one admitted native Depth10 update.
"""

from __future__ import annotations

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


MARKETTRUTH_TOPIC = "app.trader_assist.markettruth.v1"


@dataclass(frozen=True)
class MarketTruthFanoutHealth:
    state: str = "HEALTHY"
    transport: str = "NAUTILUS_MESSAGEBUS_SYNC_TOPIC"
    published_count: int = 0
    publish_error_count: int = 0
    last_publish_error: str | None = None
    native_internal_queue_pressure: str = "NOT_APPLICABLE_SYNC_IN_PROCESS_TOPIC"
