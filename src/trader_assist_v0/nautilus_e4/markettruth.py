"""Immutable project-owned views over admitted native market data.

This module deliberately accepts primitive values only.  Nautilus owns the
mutable book and transport; consumers receive a hash-bound, immutable top-of-
book fact derived from one admitted native Depth10 update.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

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
DEPTH10_MAX_ADMISSION_LAG_NS = 5_000_000_000


@dataclass(frozen=True)
class MarketTruthFanoutHealth:
    state: str = "HEALTHY"
    transport: str = "NAUTILUS_MESSAGEBUS_SYNC_TOPIC"
    published_count: int = 0
    publish_error_count: int = 0
    last_publish_error: str | None = None
    native_internal_queue_pressure: str = "NOT_APPLICABLE_SYNC_IN_PROCESS_TOPIC"


class Depth10PublicationGate:
    """Per-stream, project-owned currentness gate for immutable MarketTruth."""

    def __init__(self, *, max_admission_lag_ns: int = DEPTH10_MAX_ADMISSION_LAG_NS) -> None:
        self._max_admission_lag_ns = max_admission_lag_ns
        self._last_event_ts: dict[str, int] = {}

    def admit(
        self,
        *,
        market_id: str,
        ts_event: int,
        ts_init: int,
        admission_ts: int,
        continuity_complete: bool,
        decision_ts: int | None = None,
    ) -> str | None:
        if not continuity_complete:
            return "DEPTH10_CONTINUITY_NOT_COMPLETE"
        if decision_ts is not None and (ts_event > decision_ts or ts_init > decision_ts):
            return "DEPTH10_FUTURE"
        if admission_ts - ts_init > self._max_admission_lag_ns:
            return "DEPTH10_STALE"
        previous = self._last_event_ts.get(market_id)
        if previous is not None and ts_event <= previous:
            return "DEPTH10_NOT_CURRENT"
        self._last_event_ts[market_id] = ts_event
        return None


class MarketTruthFanout:
    """Truthful shared health for native publication and project subscribers."""

    def __init__(self) -> None:
        self._health = MarketTruthFanoutHealth()

    @property
    def health(self) -> MarketTruthFanoutHealth:
        return self._health

    def publish(self, publisher: Callable[[str, object], None], ref: MarketTruthRef) -> None:
        try:
            publisher(MARKETTRUTH_TOPIC, ref)
        except Exception as exc:
            self._health = replace(
                self._health,
                state="DEGRADED",
                publish_error_count=self._health.publish_error_count + 1,
                last_publish_error=type(exc).__name__,
            )
        else:
            self._health = replace(
                self._health,
                published_count=self._health.published_count + 1,
                # Native rc5 does not report subscriber success. Never clear a
                # previously observed project-subscriber failure here.
                state=("DEGRADED" if self._health.state == "DEGRADED" else "HEALTHY"),
            )

    def record_subscriber_failure(self, error: Exception) -> None:
        self._health = replace(
            self._health,
            state="DEGRADED",
            publish_error_count=self._health.publish_error_count + 1,
            last_publish_error=f"SUBSCRIBER_{type(error).__name__}",
        )


class MarketTruthSubscriber:
    """Bounded adapter that makes project subscriber failure observable."""

    def __init__(
        self,
        handler: Callable[[MarketTruthRef], None],
        fanout: MarketTruthFanout,
    ) -> None:
        self._handler = handler
        self._fanout = fanout

    def __call__(self, message: object) -> None:
        if not isinstance(message, MarketTruthRef):
            self._fanout.record_subscriber_failure(TypeError("MARKETTRUTH_TYPE"))
            return
        try:
            self._handler(message)
        except Exception as exc:
            self._fanout.record_subscriber_failure(exc)
