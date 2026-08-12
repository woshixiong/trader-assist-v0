from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    ClosedBarStore,
    DataRouteError,
    aggregate_closed_5m,
)
from trader_assist_v0.multi_asset_shadow.models import ClosedBar, MarketIdentity

MARKET_ID = MarketIdentity.create(dex="MAIN", coin="BTC").market_id
NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def bar(index: int, *, close: str = "101") -> ClosedBar:
    start = index * 300_000
    return ClosedBar.create(
        market_id=MARKET_ID,
        open_time_ms=start,
        close_time_ms=start + 300_000,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        volume=Decimal("10"),
        source_id="hyperliquid-public-mainnet",
        provenance_hash=sha256_hex(f"source-{index}".encode()),
        received_at=NOW,
    )


def test_closed_bar_store_is_idempotent_but_rejects_conflicts(tmp_path: Path) -> None:
    store = ClosedBarStore(tmp_path / "evidence.db")
    value = bar(0)
    assert store.put(value)
    assert not store.put(value)
    with pytest.raises(DataRouteError, match="conflicting"):
        store.put(bar(0, close="100"))
    store.close()


def test_15m_and_1h_are_complete_aligned_causal_5m_aggregates() -> None:
    fifteen = aggregate_closed_5m([bar(0), bar(1), bar(2)], minutes=15)
    assert fifteen.interval == "15m"
    assert fifteen.open_time_ms == 0
    assert fifteen.volume == Decimal("30")
    hour = aggregate_closed_5m([bar(index) for index in range(12)], minutes=60)
    assert hour.interval == "1h"
    assert hour.close_time_ms == 3_600_000


def test_gap_or_misaligned_aggregate_fails_closed() -> None:
    with pytest.raises(DataRouteError, match="gap"):
        aggregate_closed_5m([bar(0), bar(1), bar(3)], minutes=15)
    with pytest.raises(DataRouteError, match="aligned"):
        aggregate_closed_5m([bar(1), bar(2), bar(3)], minutes=15)
