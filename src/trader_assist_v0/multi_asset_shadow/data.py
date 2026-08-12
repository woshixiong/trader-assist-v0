"""Closed-bar persistence and strictly causal local aggregation."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .models import ClosedBar, MarketLifecycle, RegistryMarket
from .registry import MarketRegistryManager


class DataRouteError(ValueError):
    pass


class ClosedBarStore:
    """Single-process SQLite evidence store; duplicate equals are idempotent, conflicts fail."""

    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS closed_bars (
                market_id TEXT NOT NULL, interval TEXT NOT NULL, open_time_ms INTEGER NOT NULL,
                canonical_hash TEXT NOT NULL, payload_json BLOB NOT NULL,
                PRIMARY KEY (market_id, interval, open_time_ms)
            )"""
        )

    def put(self, bar: ClosedBar) -> bool:
        encoded = bar.model_dump_json().encode("utf-8")
        existing = self.connection.execute(
            "SELECT canonical_hash FROM closed_bars "
            "WHERE market_id=? AND interval=? AND open_time_ms=?",
            (bar.market_id, bar.interval, bar.open_time_ms),
        ).fetchone()
        if existing is not None:
            if existing[0] == bar.canonical_hash:
                return False
            raise DataRouteError("conflicting closed bar identity")
        self.connection.execute(
            "INSERT INTO closed_bars VALUES (?, ?, ?, ?, ?)",
            (bar.market_id, bar.interval, bar.open_time_ms, bar.canonical_hash, encoded),
        )
        self.connection.commit()
        return True

    def close(self) -> None:
        self.connection.close()


class MultiAssetDataAuthority:
    """Narrow admitted-closed-5m authority for selected Registry markets.

    REST warmup/backfill and reconnect resubscription call this one admission
    path.  Callers cannot pass a hand-made ClosedBar and claim provider
    authority.  A gap or conflicting duplicate blocks only the affected market.
    """

    def __init__(self, *, store: ClosedBarStore, registry: MarketRegistryManager) -> None:
        self.store = store
        self.registry = registry
        self._last_open: dict[str, int] = {}
        self._failed: set[str] = set()
        self._pending_apply: str | None = None

    def request_registry_apply(self, version: str) -> None:
        self.registry.request_apply(version)
        self._pending_apply = version

    def market_failed(self, market_id: str) -> bool:
        return market_id in self._failed

    def can_formalize(self, market: RegistryMarket) -> bool:
        return (
            market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id not in self._failed
        )

    def admit_provider_candle(
        self, *, market: RegistryMarket, payload: object, received_at: datetime
    ) -> ClosedBar | None:
        if received_at.tzinfo is None:
            raise DataRouteError("received_at must be timezone-aware")
        if not isinstance(payload, dict):
            raise DataRouteError("provider candle is not an object")
        try:
            interval, coin = payload["i"], payload["s"]
            open_ms, close_ms = payload["t"], payload["T"]
            values = (payload["o"], payload["h"], payload["l"], payload["c"], payload["v"])
        except KeyError as exc:
            raise DataRouteError("provider candle is incomplete") from exc
        if (
            interval != "5m"
            or coin != market.identity.coin
            or not isinstance(open_ms, int)
            or not isinstance(close_ms, int)
        ):
            raise DataRouteError("provider candle identity is invalid")
        if close_ms <= open_ms or close_ms > int(received_at.timestamp() * 1000):
            # The endpoint includes an open candle.  It is not evidence.
            return None
        try:
            bar = ClosedBar.create(
                market_id=market.identity.market_id,
                open_time_ms=open_ms,
                close_time_ms=close_ms,
                open=Decimal(str(values[0])),
                high=Decimal(str(values[1])),
                low=Decimal(str(values[2])),
                close=Decimal(str(values[3])),
                volume=Decimal(str(values[4])),
                source_id="hyperliquid-public-candleSnapshot",
                provenance_hash=sha256_hex(canonical_json_bytes(payload)),
                received_at=received_at.astimezone(UTC),
            )
        except (ArithmeticError, ValueError) as exc:
            raise DataRouteError("provider candle values are invalid") from exc
        prior = self._last_open.get(bar.market_id)
        if prior is not None and bar.open_time_ms > prior + 300_000:
            self._failed.add(bar.market_id)
            raise DataRouteError("closed 5m gap detected")
        try:
            inserted = self.store.put(bar)
        except DataRouteError:
            self._failed.add(bar.market_id)
            raise
        self._last_open[bar.market_id] = max(
            bar.open_time_ms, prior if prior is not None else bar.open_time_ms
        )
        if inserted:
            if self._pending_apply is not None:
                self.registry.apply_at_closed_5m(self._pending_apply, boundary=bar)
                self._pending_apply = None
            else:
                self.registry.apply_pending_at_closed_5m(boundary=bar)
        return bar if inserted else None


def aggregate_closed_5m(candles: Iterable[ClosedBar], *, minutes: int) -> ClosedBar:
    """Build one 15m or 1h candle from a complete consecutive 5m window only."""
    count = {15: 3, 60: 12}.get(minutes)
    if count is None:
        raise DataRouteError("only 15m and 1h aggregation is authorized")
    values = tuple(candles)
    if len(values) != count or any(value.interval != "5m" for value in values):
        raise DataRouteError("aggregation needs exactly complete closed 5m input")
    market_ids = {value.market_id for value in values}
    if len(market_ids) != 1:
        raise DataRouteError("aggregation cannot cross market identities")
    if any(right.open_time_ms - left.open_time_ms != 300_000 for left, right in pairwise(values)):
        raise DataRouteError("aggregation input has a gap")
    if values[0].open_time_ms % (minutes * 60_000) != 0:
        raise DataRouteError("aggregation window is not aligned")
    provenance = ClosedBar.hash_payload(
        {"source_bars": [value.canonical_hash for value in values], "aggregate_minutes": minutes}
    )
    return ClosedBar.create(
        market_id=values[0].market_id,
        interval="15m" if minutes == 15 else "1h",
        open_time_ms=values[0].open_time_ms,
        close_time_ms=values[-1].close_time_ms,
        open=values[0].open,
        high=max(value.high for value in values),
        low=min(value.low for value in values),
        close=values[-1].close,
        volume=sum((value.volume for value in values), Decimal()),
        source_id="local-5m-causal-aggregation",
        provenance_hash=provenance,
        received_at=values[-1].received_at,
    )
