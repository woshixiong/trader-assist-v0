"""Closed-bar persistence and strictly causal local aggregation."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from .models import ClosedBar


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
