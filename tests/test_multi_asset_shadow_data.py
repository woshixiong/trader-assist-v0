from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import (
    _HISTORY_BATCH_BARS,
    ClosedBarStore,
    DataRouteError,
    MultiAssetDataAuthority,
    _provider_bar,
    aggregate_closed_5m,
)
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    ClosedBar,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager

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


def _market() -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=NOW,
        metadata_hash="a" * 64,
    )


def _payload(open_ms: int, *, close: str = "100") -> dict[str, object]:
    return {
        "i": "5m",
        "s": "BTC",
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": close,
        "v": "10",
    }


def _authority(tmp_path: Path) -> tuple[MultiAssetDataAuthority, RegistryMarket]:
    market = _market()
    manager = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(version="one", created_at=NOW, markets=(market,))
    manager.stage(version)
    manager.request_apply("one")
    return MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "authority.db"), registry=manager
    ), market


def test_ws_candidate_requires_final_stable_rest_and_real_end_minus_one_geometry(
    tmp_path: Path,
) -> None:
    authority, market = _authority(tmp_path)
    payload = _payload(0)
    fingerprint = authority.offer_ws_candidate(market=market, payload=payload, received_at=NOW)
    assert authority.store.bars(market.identity.market_id) == ()
    assert (
        authority.confirm_ws_candidate(
            market=market,
            open_time_ms=0,
            candidate_fingerprint=fingerprint,
            snapshot=[payload],
            stable_snapshot=[payload],
            received_at=datetime.fromtimestamp(302.5, UTC),
            first_observed_monotonic=1,
            second_observed_monotonic=2,
        )
        is None
    )
    admitted = authority.confirm_ws_candidate(
        market=market,
        open_time_ms=0,
        candidate_fingerprint=fingerprint,
        snapshot=[payload],
        stable_snapshot=[payload],
            received_at=datetime.fromtimestamp(303, UTC),
            first_observed_monotonic=1,
            second_observed_monotonic=2,
    )
    assert admitted is not None and admitted.close_time_ms == 299_999
    assert authority.registry.active() is not None and authority.registry.active().version == "one"


def test_finality_authority_rejects_two_rest_observations_without_real_gap(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    payload = _payload(0)
    fingerprint = authority.offer_ws_candidate(market=market, payload=payload, received_at=NOW)
    with pytest.raises(DataRouteError, match="observation gap"):
        authority.confirm_ws_candidate(
            market=market,
            open_time_ms=0,
            candidate_fingerprint=fingerprint,
            snapshot=[payload],
            stable_snapshot=[payload],
            received_at=datetime.fromtimestamp(303, UTC),
            first_observed_monotonic=1,
            second_observed_monotonic=1.5,
        )


def test_conflict_and_gap_are_isolated_and_backfill_recovers(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    received = datetime.fromtimestamp(1_000, UTC)
    authority.admit_rest_history(market=market, snapshot=[_payload(0)], received_at=received)
    with pytest.raises(DataRouteError, match="gap"):
        authority.admit_rest_history(
            market=market, snapshot=[_payload(600_000)], received_at=received
        )
    assert authority.market_failed(market.identity.market_id)
    authority.admit_rest_history(
        market=market, snapshot=[_payload(300_000), _payload(600_000)], received_at=received
    )
    assert not authority.market_failed(market.identity.market_id)
    with pytest.raises(DataRouteError, match="conflicting"):
        authority.admit_rest_history(
            market=market, snapshot=[_payload(600_000, close="101")], received_at=received
        )


def test_restart_recovers_last_authoritative_identity(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    authority.admit_rest_history(
        market=market,
        snapshot=[_payload(0), _payload(300_000)],
        received_at=datetime.fromtimestamp(1_000, UTC),
    )
    restored = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "authority.db"), registry=authority.registry
    )
    assert restored.store.last_open(market.identity.market_id) == 300_000


# ---------------------------------------------------------------------------
# Cold-start throughput acceptance: bounded hot path, exact evidence semantics.


HISTORY_BARS = 2304
RECEIVED = datetime.fromtimestamp(700_000, UTC)


def _hist_payload(index: int, *, close: str | None = None) -> dict[str, object]:
    open_value = 100 + index % 23
    close_value = open_value + (index % 11) - 5
    return {
        "i": "5m",
        "s": "BTC",
        "t": index * 300_000,
        "T": index * 300_000 + 299_999,
        "o": str(open_value),
        "h": str(max(open_value, int(close or close_value)) + 1 + index % 3),
        "l": str(min(open_value, int(close or close_value)) - 1 - index % 4),
        "c": close if close is not None else str(close_value),
        "v": str(10 + index % 19),
    }


def _full_snapshot() -> list[dict[str, object]]:
    return [_hist_payload(index) for index in range(HISTORY_BARS)]


def _row_count(connection: Any, market_id: str, *, interval: str) -> int:
    return int(
        connection.execute(
            "SELECT COUNT(*) FROM closed_bars WHERE market_id=? AND interval=?",
            (market_id, interval),
        ).fetchone()[0]
    )


class _InstrumentedConnection:
    """Counts commits and complete-history payload scans on one connection."""

    def __init__(self, inner: sqlite3.Connection) -> None:
        self._inner = inner
        self.commits = 0
        self.full_history_scans = 0
        self.limited_tail_queries = 0

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> Any:
        if sql.startswith("SELECT payload_json FROM closed_bars"):
            if "LIMIT ?" in sql:
                self.limited_tail_queries += 1
            else:
                self.full_history_scans += 1
        return self._inner.execute(sql, parameters)

    def commit(self) -> None:
        self.commits += 1
        self._inner.commit()

    def rollback(self) -> None:
        self._inner.rollback()

    def close(self) -> None:
        self._inner.close()


def test_2304_bar_realistic_history_is_fully_retained(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    admitted = authority.admit_rest_history(
        market=market, snapshot=_full_snapshot(), received_at=RECEIVED
    )
    assert len(admitted) == HISTORY_BARS
    summary = authority.store.connection.execute(
        "SELECT COUNT(*), MIN(open_time_ms), MAX(open_time_ms) FROM closed_bars "
        "WHERE market_id=? AND interval='5m'",
        (market.identity.market_id,),
    ).fetchone()
    assert summary == (HISTORY_BARS, 0, (HISTORY_BARS - 1) * 300_000)
    assert not authority.market_failed(market.identity.market_id)


def test_hot_admission_path_never_rescans_complete_history(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    store = authority.store
    store.connection = _InstrumentedConnection(store.connection)
    bars_calls: list[object] = []
    original_bars = store.bars

    def counting_bars(*args: object, **kwargs: object) -> object:
        bars_calls.append(args)
        return original_bars(*args, **kwargs)

    store.bars = counting_bars
    admitted = authority.admit_rest_history(
        market=market, snapshot=_full_snapshot(), received_at=RECEIVED
    )
    assert len(admitted) == HISTORY_BARS
    assert len(bars_calls) == 0
    assert store.connection.full_history_scans == 0


def _assert_aggregate_equivalence(
    persisted: tuple[ClosedBar, ...], expected: tuple[ClosedBar, ...], *, interval: str
) -> None:
    assert len(persisted) == len(expected) > 0
    for stored, reference in zip(persisted, expected, strict=True):
        assert stored.canonical_hash == reference.canonical_hash
        assert stored.provenance_hash == reference.provenance_hash
        assert stored.market_id == reference.market_id
        assert stored.interval == reference.interval == interval
        assert stored.open_time_ms == reference.open_time_ms
        assert stored.close_time_ms == reference.close_time_ms
        assert stored.open == reference.open
        assert stored.high == reference.high
        assert stored.low == reference.low
        assert stored.close == reference.close
        assert stored.volume == reference.volume
        assert stored.received_at == reference.received_at
        assert stored.source_id == reference.source_id


def test_chunked_admission_matches_independent_canonical_reference(
    tmp_path: Path,
) -> None:
    authority, market = _authority(tmp_path)
    authority.store.connection = _InstrumentedConnection(authority.store.connection)
    snapshot = _full_snapshot()
    sources = tuple(
        _provider_bar(
            market=market,
            payload=payload,
            received_at=RECEIVED,
            source_id="hyperliquid-public-candleSnapshot-history",
        )
        for payload in snapshot
    )
    inserted_total = 0
    position = 0
    for size in (500, 500, 500, 500, HISTORY_BARS - 2000):
        inserted_total += len(
            authority.admit_rest_history(
                market=market, snapshot=snapshot[position : position + size],
                received_at=RECEIVED,
            )
        )
        position += size
    assert inserted_total == HISTORY_BARS
    assert authority.store.connection.full_history_scans == 0
    # Cross-chunk 1h windows must reseed through the bounded SQL tail path.
    assert authority.store.connection.limited_tail_queries > 0
    assert sources == authority.store.bars(market.identity.market_id)
    expected_15m = tuple(
        aggregate_closed_5m(sources[base : base + 3], minutes=15)
        for base in range(0, HISTORY_BARS, 3)
    )
    expected_1h = tuple(
        aggregate_closed_5m(sources[base : base + 12], minutes=60)
        for base in range(0, HISTORY_BARS, 12)
    )
    _assert_aggregate_equivalence(
        authority.store.bars(market.identity.market_id, interval="15m"),
        expected_15m,
        interval="15m",
    )
    _assert_aggregate_equivalence(
        authority.store.bars(market.identity.market_id, interval="1h"),
        expected_1h,
        interval="1h",
    )


def test_2304_history_uses_bounded_transactions_not_per_row_commits(
    tmp_path: Path,
) -> None:
    authority, market = _authority(tmp_path)
    store = authority.store
    store.connection = _InstrumentedConnection(store.connection)
    authority.admit_rest_history(
        market=market, snapshot=_full_snapshot(), received_at=RECEIVED
    )
    commits = store.connection.commits
    # One durable commit for the Registry-activating causal bar, then one
    # durable commit per bounded batch of source bars.
    expected = 1 + -(-(HISTORY_BARS - 1) // _HISTORY_BATCH_BARS)
    assert commits == expected
    assert commits < HISTORY_BARS // 16
    assert commits >= 2


def test_registry_activates_only_after_causal_5m_is_durable(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    db_path = tmp_path / "authority.db"
    assert authority.registry.active() is None
    assert not authority.registry.pointer.exists()
    durable_counts_at_activation: list[int] = []
    original = authority.registry._apply_admitted

    def durable_first(admission: object) -> object:
        if authority.registry.pending_version() is not None:
            reader = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                durable_counts_at_activation.append(
                    _row_count(reader, market.identity.market_id, interval="5m")
                )
            finally:
                reader.close()
        return original(admission)

    authority.registry._apply_admitted = durable_first
    authority.admit_rest_history(
        market=market, snapshot=_full_snapshot(), received_at=RECEIVED
    )
    assert durable_counts_at_activation == [1]
    active = authority.registry.active()
    assert active is not None and active.version == "one"
    assert authority.registry.pointer.exists()


def test_injected_batch_failure_rolls_back_and_recovers(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    store = authority.store
    original_put = store.put_deferred

    def injected(bar: ClosedBar, **kwargs: object) -> bool:
        if bar.open_time_ms == 100 * 300_000:
            raise RuntimeError("injected batch failure")
        return original_put(bar, **kwargs)

    store.put_deferred = injected
    try:
        with pytest.raises(RuntimeError, match="injected batch failure"):
            authority.admit_rest_history(
                market=market, snapshot=_full_snapshot(), received_at=RECEIVED
            )
    finally:
        del store.put_deferred
    market_id = market.identity.market_id
    connection = store.connection
    assert _row_count(connection, market_id, interval="5m") == 65
    assert _row_count(connection, market_id, interval="15m") == 21
    assert _row_count(connection, market_id, interval="1h") == 5
    rolled_back_window = connection.execute(
        "SELECT COUNT(*) FROM closed_bars WHERE market_id=? AND interval='15m' "
        "AND open_time_ms=?",
        (market_id, 63 * 300_000),
    ).fetchone()[0]
    assert rolled_back_window == 0
    assert authority._last_open[market_id] == store.last_open(market_id) == 64 * 300_000
    assert authority.market_failed(market_id)
    admitted = authority.admit_rest_history(
        market=market, snapshot=_full_snapshot(), received_at=RECEIVED
    )
    assert len(admitted) == HISTORY_BARS - 65
    assert _row_count(connection, market_id, interval="5m") == HISTORY_BARS
    assert not authority.market_failed(market_id)


def test_bounded_continuity_recovery_and_real_gap_detection(tmp_path: Path) -> None:
    authority, market = _authority(tmp_path)
    store = authority.store
    market_id = market.identity.market_id
    bars_calls: list[object] = []
    original_bars = store.bars

    def counting_bars(*args: object, **kwargs: object) -> object:
        bars_calls.append(args)
        return original_bars(*args, **kwargs)

    store.bars = counting_bars
    authority.admit_rest_history(
        market=market, snapshot=[_payload(0)], received_at=RECEIVED
    )
    store.put(bar(2))
    with pytest.raises(DataRouteError, match="gap"):
        authority.admit_rest_history(
            market=market, snapshot=[_payload(600_000)], received_at=RECEIVED
        )
    assert authority.market_failed(market_id)
    # A duplicate cannot clear a real persisted interior gap.
    authority.admit_rest_history(
        market=market, snapshot=[_payload(0)], received_at=RECEIVED
    )
    assert authority.market_failed(market_id)
    # Filling the internal gap is what clears the failure.
    authority.admit_rest_history(
        market=market, snapshot=[_payload(300_000)], received_at=RECEIVED
    )
    assert not authority.market_failed(market_id)
    assert len(bars_calls) == 0


def test_duplicate_history_is_idempotent_and_conflicts_fail_closed(
    tmp_path: Path,
) -> None:
    authority, market = _authority(tmp_path)
    market_id = market.identity.market_id
    snapshot = [_hist_payload(0), _hist_payload(1), _hist_payload(2)]
    assert (
        len(authority.admit_rest_history(market=market, snapshot=snapshot, received_at=RECEIVED))
        == 3
    )
    assert (
        authority.admit_rest_history(market=market, snapshot=snapshot, received_at=RECEIVED)
        == ()
    )
    assert _row_count(authority.store.connection, market_id, interval="5m") == 3
    assert _row_count(authority.store.connection, market_id, interval="15m") == 1
    with pytest.raises(DataRouteError, match="conflicting"):
        authority.admit_rest_history(
            market=market,
            snapshot=[_hist_payload(1, close="777")],
            received_at=RECEIVED,
        )
    assert _row_count(authority.store.connection, market_id, interval="5m") == 3
    assert authority.market_failed(market_id)
