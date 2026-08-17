"""Post-ACK live finality and lifecycle bounded repair acceptance (Issue #80).

Deterministic offline proofs over the real production control flow:
WS candidate -> GenerationFinalityAuthority -> confirmation semaphore ->
two REST confirmations -> confirm_ws_candidate -> Closed5mAdmission ->
registry pending activation -> _maybe_stage_lifecycle -> successor stage.

Covers the real-host POST_ACK_LIVE_FINALITY_AND_LIFECYCLE_COHORT_FAILURE:
WS-silent zero-trade boundaries, sticky runtime finality failures, the
lifecycle version-name schema bound, bounded failure diagnostics, and the
First-Launch-20 same-boundary burst.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import PublicDataError
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager, RegistryError
from trader_assist_v0.multi_asset_shadow.runtime import (
    MarketFailureRecord,
    MultiAssetPublicRuntime,
    _lifecycle_version_name,
)

SLOT = 300_000
PRODUCTION_SEED = "first-launch-manual-20-20260817"
NATIVE = ("BTC", "ETH", "HYPE", "SOL", "XRP")
XYZ = (
    "xyz:SKHX", "xyz:MU", "xyz:SNDK", "xyz:XYZ100", "xyz:SP500",
    "xyz:CL", "xyz:DRAM", "xyz:SPCX", "xyz:SILVER", "xyz:NVDA",
    "xyz:SMSN", "xyz:EWY", "xyz:GOLD", "xyz:TSLA", "xyz:GOOGL",
)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


class Clock:
    def __init__(self, seconds: int = 303) -> None:
        self.seconds = seconds
        self.monotonic_seconds = 0.0

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return self.monotonic_seconds

    async def sleep(self, seconds: float) -> None:
        self.monotonic_seconds += seconds
        self.seconds += int(seconds)
        await asyncio.sleep(0)


def candle(coin: str, open_ms: int, *, close: str = "101") -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + SLOT - 1,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": close,
        "v": "10",
    }


def flat_candle(coin: str, open_ms: int, *, price: str = "100") -> dict[str, object]:
    """Provider's own zero-trade bar: no volume, unchanged price."""
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + SLOT - 1,
        "o": price,
        "h": price,
        "l": price,
        "c": price,
        "v": "0",
    }


def market(coin: str = "BTC") -> RegistryMarket:
    native = not coin.startswith("xyz:")
    return RegistryMarket(
        display=coin.removeprefix("xyz:"),
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN" if native else "xyz", coin=coin),
        asset_class=AssetClass.CRYPTO if native else AssetClass.EQUITY,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=not native,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.WARMING,
        metadata_observed_at=datetime(2026, 8, 12, tzinfo=UTC),
        metadata_hash=sha256_hex(coin.encode()),
    )


class ScriptedClient:
    """Deterministic public REST: responses are keyed by request start_ms."""

    def __init__(
        self,
        respond: Callable[[str, int, int], object],
    ) -> None:
        self.respond = respond
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        result = self.respond(coin, start_ms, end_ms)
        if isinstance(result, Exception):
            raise result
        return result


def single_market_harness(
    tmp_path: Path,
    *,
    respond: Callable[[str, int, int], object],
    clock: Clock,
    coin: str = "BTC",
) -> tuple[MultiAssetPublicRuntime, MultiAssetDataAuthority, RegistryMarket]:
    item = market(coin)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version=PRODUCTION_SEED, created_at=clock.now(), markets=(item,))
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
    )
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=ScriptedClient(respond),  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    return runtime, authority, item


async def confirm_candidate(
    runtime: MultiAssetPublicRuntime, market_id: str, payload: dict[str, object]
) -> None:
    await runtime.handle_message(json.dumps({"channel": "candle", "data": payload}))
    task = runtime._finality.task_for(market_id)
    assert task is not None
    await task


def poisoned_candle(coin: str, open_ms: int) -> dict[str, object]:
    """Schema-valid but wrong: the unsafe echo an end-inclusive snapshot returns."""
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + SLOT - 1,
        "o": "999",
        "h": "999",
        "l": "1",
        "c": "1",
        "v": "9999",
    }


@async_test
async def test_backfill_attack_end_inclusive_echo_admits_prefix_only(
    tmp_path: Path,
) -> None:
    """Mandatory attack test against real provider end-inclusive semantics.

    The backfill window is (prior_open + 5m, candidate_open); a real
    candleSnapshot response may include the candidate bar itself because
    endTime is inclusive.  That echo carries values that would be unsafe to
    admit as final authority.  Prove the prefix is admitted, the candidate is
    NOT admitted through admit_rest_history, and only the two targeted stable
    REST observations admit the candidate.
    """
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms == 2 * SLOT:
            return [candle(coin, 2 * SLOT, close="101")]
        if start_ms == SLOT:
            # End-inclusive echo of the live boundary, deliberately poisoned.
            return [flat_candle(coin, SLOT), poisoned_candle(coin, 2 * SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(
        tmp_path, respond=respond, clock=clock
    )
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 2 * SLOT))

    bars = authority.store.bars(item.identity.market_id)
    assert [bar.open_time_ms for bar in bars] == [0, SLOT, 2 * SLOT]
    candidate = bars[2]
    assert str(candidate.close) == "101"
    assert str(candidate.open) == "100"
    assert str(candidate.volume) == "10"
    # The poisoned echo (o=999, c=1, v=9999) never became durable evidence:
    # only the two targeted stable observations admitted the candidate.
    assert str(candidate.open) != "999" and str(candidate.close) != "1"
    # Two targeted REST observations precede the backfill observation.
    client = runtime.client
    assert isinstance(client, ScriptedClient)
    assert client.calls == [
        ("BTC", 2 * SLOT, 2 * SLOT + SLOT),
        ("BTC", 2 * SLOT, 2 * SLOT + SLOT),
        ("BTC", SLOT, 2 * SLOT),
    ]
    assert item.identity.market_id not in runtime.health.failed_markets
    assert authority.store.is_contiguous_5m(item.identity.market_id)


@async_test
async def test_backfill_future_evidence_fails_closed(tmp_path: Path) -> None:
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms == 2 * SLOT:
            return [candle(coin, 2 * SLOT)]
        if start_ms == SLOT:
            # Evidence beyond the candidate boundary is unexpected and must
            # fail closed without admitting anything from this observation.
            return [flat_candle(coin, SLOT), candle(coin, 3 * SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(
        tmp_path, respond=respond, clock=clock
    )
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 2 * SLOT))
    market_id = item.identity.market_id
    assert market_id in runtime.health.failed_markets
    assert runtime.health.failure_records[market_id].stage == "finality_confirmation"
    assert authority.store.last_open(market_id) == 0
    assert len(authority.store.bars(market_id)) == 1


@async_test
async def test_targeted_snapshot_conflict_fails_closed_candidate_not_admitted(
    tmp_path: Path,
) -> None:
    clock = Clock(seconds=603)
    state = {"calls": 0}

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms == 2 * SLOT:
            state["calls"] += 1
            close = "101" if state["calls"] == 1 else "102"
            return [candle(coin, 2 * SLOT, close=close)]
        if start_ms == SLOT:
            return [flat_candle(coin, SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(
        tmp_path, respond=respond, clock=clock
    )
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 2 * SLOT))
    market_id = item.identity.market_id
    assert market_id in runtime.health.failed_markets
    opens = [bar.open_time_ms for bar in authority.store.bars(market_id)]
    # The silent prefix was admitted; the conflicting candidate was not.
    assert opens == [0, SLOT]
    assert authority.store.last_open(market_id) == SLOT


@async_test
async def test_transient_finality_failure_fails_closed_then_recovers_market_scoped(
    tmp_path: Path,
) -> None:
    clock = Clock(seconds=603)
    state = {"fail_once": True}

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if state["fail_once"] and start_ms == SLOT:
            state["fail_once"] = False
            return PublicDataError("transient public route failure")
        if start_ms == SLOT:
            return [candle(coin, SLOT)]
        if start_ms == 2 * SLOT:
            return [candle(coin, 2 * SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )

    clock.seconds = SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", SLOT))
    market_id = item.identity.market_id
    assert market_id in runtime.health.failed_markets
    record = runtime.health.failure_records[market_id]
    assert record.stage == "finality_confirmation"
    assert record.recoverable is True
    assert "PublicDataError" in record.category
    assert authority.store.last_open(market_id) == 0

    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 2 * SLOT))
    assert market_id not in runtime.health.failed_markets
    assert market_id not in runtime.health.failure_records
    opens = [bar.open_time_ms for bar in authority.store.bars(market_id)]
    assert opens == [0, SLOT, 2 * SLOT]

    # A recovered market must not stay lifecycle-stuck.
    clock.seconds = 1_000
    runtime.health.data_ready = True
    await runtime._maybe_stage_lifecycle(snapshot_ready=True)
    pending = runtime.registry.pending_version()
    assert pending is not None and pending.markets[0].lifecycle is MarketLifecycle.HISTORY_READY


@async_test
async def test_callback_failure_is_not_auto_recovered_by_later_finality(
    tmp_path: Path,
) -> None:
    """Classification B: an application failure needs application review."""
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms in (2 * SLOT, 3 * SLOT):
            return [candle(coin, start_ms)]
        if start_ms == SLOT:
            return [flat_candle(coin, SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    market_id = item.identity.market_id

    def broken_callback(bar, mode):  # type: ignore[no-untyped-def]
        raise RuntimeError("application callback down")

    runtime.on_finalized_5m = broken_callback
    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, market_id, candle("BTC", 2 * SLOT))
    assert market_id in runtime.health.failed_markets
    record = runtime.health.failure_records[market_id]
    assert record.stage == "application_callback"
    assert record.recoverable is False
    assert len(runtime.health.callback_failures) == 1

    runtime.on_finalized_5m = None
    clock.seconds = 3 * SLOT // 1000 + 5
    await confirm_candidate(runtime, market_id, candle("BTC", 3 * SLOT))
    # Market data keeps progressing, but the application failure is sticky.
    assert market_id in runtime.health.failed_markets
    assert runtime.health.failure_records[market_id].stage == "application_callback"
    assert authority.store.last_open(market_id) == 3 * SLOT


@async_test
async def test_lifecycle_staging_failure_is_not_auto_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Classification C: a Registry control-plane failure needs operator review."""
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms in (SLOT, 2 * SLOT):
            return [candle(coin, start_ms)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    market_id = item.identity.market_id
    runtime.health.data_ready = True

    def broken_successor(**_: object) -> RegistryVersion:
        raise RegistryError("forced control-plane failure")

    monkeypatch.setattr(runtime.registry, "lifecycle_successor", broken_successor)
    clock.seconds = SLOT // 1000 + 5
    await confirm_candidate(runtime, market_id, candle("BTC", SLOT))
    assert market_id in runtime.health.failed_markets
    record = runtime.health.failure_records[market_id]
    assert record.stage == "lifecycle_staging"
    assert record.recoverable is False
    assert "RegistryError" in record.category

    monkeypatch.undo()
    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, market_id, candle("BTC", 2 * SLOT))
    assert market_id in runtime.health.failed_markets
    assert runtime.health.failure_records[market_id].stage == "lifecycle_staging"
    assert authority.store.last_open(market_id) == 2 * SLOT


@async_test
async def test_failure_without_record_is_not_auto_recovered(tmp_path: Path) -> None:
    """Classification D: no record means no proven recovery path."""
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms == SLOT:
            return [candle(coin, SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    market_id = item.identity.market_id
    runtime.health.failed_markets.add(market_id)
    assert market_id not in runtime.health.failure_records

    clock.seconds = SLOT // 1000 + 5
    await confirm_candidate(runtime, market_id, candle("BTC", SLOT))
    assert authority.store.last_open(market_id) == SLOT
    assert market_id in runtime.health.failed_markets


@async_test
async def test_warmup_success_does_not_clear_nonrecoverable_failures(
    tmp_path: Path,
) -> None:
    """Classification E: healthy market data cannot repair an application."""
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        if start_ms < 0:
            return [candle(coin, 0), candle(coin, SLOT)]
        raise AssertionError(f"unexpected window {start_ms}")

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    market_id = item.identity.market_id
    runtime.health.failed_markets.add(market_id)
    runtime.health.failure_records[market_id] = MarketFailureRecord(
        market_id=market_id,
        coin="BTC",
        open_time_ms=0,
        stage="application_callback",
        category="RuntimeError: application callback down",
        recoverable=False,
    )

    count = await runtime._warmup_market(item, recovery=False, target_open_ms=SLOT)
    assert count == 2
    assert authority.store.last_open(market_id) == SLOT
    assert market_id in runtime.health.failed_markets
    assert runtime.health.failure_records[market_id].recoverable is False


@async_test
async def test_genuine_provider_omission_remains_failed_no_broad_reset(
    tmp_path: Path,
) -> None:
    clock = Clock(seconds=603)

    def respond(coin: str, start_ms: int, end_ms: int) -> object:
        # The provider genuinely omits slot 1 from every REST surface.
        if start_ms == 2 * SLOT:
            return [candle(coin, 2 * SLOT)]
        if start_ms == 3 * SLOT:
            return [candle(coin, 3 * SLOT)]
        return []

    runtime, authority, item = single_market_harness(tmp_path, respond=respond, clock=clock)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=clock.now()
    )
    market_id = item.identity.market_id

    clock.seconds = 2 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 2 * SLOT))
    assert market_id in runtime.health.failed_markets
    assert authority.market_failed(market_id)
    record = runtime.health.failure_records[market_id]
    assert record.recoverable is False

    clock.seconds = 3 * SLOT // 1000 + 5
    await confirm_candidate(runtime, item.identity.market_id, candle("BTC", 3 * SLOT))
    assert market_id in runtime.health.failed_markets
    assert authority.market_failed(market_id)
    assert authority.store.last_open(market_id) == 0
    active_item = item.model_copy(update={"lifecycle": MarketLifecycle.ACTIVE})
    assert not authority.can_formalize(active_item)


def test_lifecycle_version_name_stays_bounded_deterministic_and_unique() -> None:
    predecessor = PRODUCTION_SEED
    predecessor_hash = sha256_hex(b"seed")
    names = []
    for suffix in ("history_ready", "snapshot_ready", "active", "active", "history_ready"):
        name = _lifecycle_version_name(predecessor, predecessor_hash, suffix)
        assert len(name) <= 80
        names.append(name)
        predecessor = name
        predecessor_hash = sha256_hex(predecessor.encode())
    assert len(set(names)) == len(names)
    assert names[0] == f"{PRODUCTION_SEED}-lifecycle-history_ready"
    again = _lifecycle_version_name(PRODUCTION_SEED, sha256_hex(b"seed"), "history_ready")
    assert again == names[0]


@async_test
async def test_lifecycle_reaches_active_with_production_length_seed(tmp_path: Path) -> None:
    clock = Clock(seconds=603)
    runtime, authority, item = single_market_harness(
        tmp_path, respond=lambda coin, start, end: [candle(coin, start)], clock=clock
    )
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", SLOT)], received_at=clock.now()
    )
    assert runtime.registry.active() is not None
    for open_ms, expected in (
        (2 * SLOT, MarketLifecycle.HISTORY_READY),
        (3 * SLOT, MarketLifecycle.SNAPSHOT_READY),
        (4 * SLOT, MarketLifecycle.ACTIVE),
    ):
        await runtime._maybe_stage_lifecycle(snapshot_ready=True)
        pending = runtime.registry.pending_version()
        assert pending is not None
        assert len(pending.version) <= 80
        assert pending.markets[0].lifecycle is expected
        clock.seconds = open_ms // 1000 + 303
        authority.admit_rest_history(
            market=pending.markets[0], snapshot=[candle("BTC", open_ms)], received_at=clock.now()
        )
    active = runtime.registry.active()
    assert active is not None
    assert active.markets[0].lifecycle is MarketLifecycle.ACTIVE
    assert len(active.version) <= 80
    assert item.identity.market_id not in runtime.health.failed_markets


@async_test
async def test_failure_records_expose_bounded_non_durable_diagnostics(tmp_path: Path) -> None:
    clock = Clock(seconds=603)
    runtime, authority, item = single_market_harness(
        tmp_path, respond=lambda coin, start, end: [candle(coin, start)], clock=clock
    )
    market_id = item.identity.market_id
    await runtime.handle_message(
        json.dumps({"channel": "candle", "data": {"i": "5m", "s": "BTC"}})
    )
    assert market_id in runtime.health.failed_markets
    record = runtime.health.failure_records[market_id]
    assert record.stage == "ws_candidate"
    assert record.coin == "BTC"
    assert record.recoverable is False
    assert len(record.category) <= 160
    # RuntimeHealth diagnostics are memory-only: the durable evidence store
    # schema is untouched by the repair.
    tables = {
        row[0]
        for row in authority.store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "failure_records" not in tables


class QueueSocket:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()

    async def send(self, raw: str) -> None:
        return None

    async def recv(self) -> str:
        return await self.queue.get()

    async def close(self) -> None:
        return None


def ack_frame(coin: str) -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": coin, "interval": "5m"},
            },
        }
    )


class CohortGrid:
    """End-inclusive provider grid: silent xyz slot 1, one genuine SP500 omission."""

    def __init__(self) -> None:
        self.fail_btc_once = True

    def candles(self, coin: str, start_ms: int, end_ms: int) -> list[dict[str, object]]:
        # Real candleSnapshot is end-inclusive: a window (start, end) may
        # include the bar whose open == end, exactly as the live probe showed.
        out: list[dict[str, object]] = []
        for open_ms in range(max(0, start_ms), end_ms + SLOT, SLOT):
            if coin == "xyz:SP500" and open_ms == 2 * SLOT:
                continue
            if coin in XYZ and open_ms == SLOT:
                out.append(flat_candle(coin, open_ms))
            else:
                out.append(candle(coin, open_ms))
        return out


@async_test
async def test_first_launch_20_same_boundary_burst_converges_strictly(tmp_path: Path) -> None:
    clock = Clock(seconds=303)
    coins = NATIVE + XYZ
    markets = tuple(market(coin) for coin in coins)
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(
        version=PRODUCTION_SEED, created_at=clock.now(), markets=markets
    )
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "evidence.db"), registry=registry
    )
    grid = CohortGrid()
    client = ScriptedGrid(grid)
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )
    socket = QueueSocket()

    async def factory(_: str) -> QueueSocket:
        return socket

    runtime.websocket_factory = factory  # type: ignore[assignment]
    finalized: list[tuple[str, int]] = []
    runtime.on_finalized_5m = lambda bar, mode: finalized.append(
        (bar.market_id, bar.open_time_ms)
    )
    shutdown = asyncio.Event()
    run_task = asyncio.create_task(runtime.run(shutdown))
    for _ in range(20_000):
        if runtime.health.subscriptions == 20 or run_task.done():
            break
        await asyncio.sleep(0)
    for coin in coins:
        await socket.queue.put(ack_frame(coin))
    for _ in range(20_000):
        if runtime.health.data_ready or run_task.done():
            break
        await asyncio.sleep(0)
    assert runtime.health.data_ready

    # Slot 1: natives trade, every xyz market is WS-silent. Slot 2 onward:
    # everyone trades except that SP500's own provider row is genuinely gone.
    phases = (
        (SLOT, NATIVE),
        (2 * SLOT, coins),
        (3 * SLOT, coins),
    )
    for open_ms, trading in phases:
        for coin in trading:
            await socket.queue.put(
                json.dumps({"channel": "candle", "data": candle(coin, open_ms)})
            )
        clock.seconds = open_ms // 1000 + 303
        clock.monotonic_seconds = clock.seconds
        for _ in range(50_000):
            await asyncio.sleep(0)
        for task in list(runtime._finality.tasks.values()):
            if not task.done():
                await asyncio.wait_for(asyncio.shield(task), timeout=5)

    shutdown.set()
    await socket.queue.put(ack_frame("BTC"))
    await asyncio.wait_for(run_task, timeout=10)

    active = registry.active()
    assert active is not None
    sp500_id = next(m.identity.market_id for m in markets if m.identity.coin == "xyz:SP500")
    healthy = [m for m in active.markets if m.identity.market_id != sp500_id]
    assert all(m.lifecycle is MarketLifecycle.ACTIVE for m in healthy)
    assert authority.market_failed(sp500_id)
    assert runtime.health.failed_markets == {sp500_id}

    clock.seconds = 3 * SLOT // 1000 + 303
    ready = runtime.readiness_snapshot()
    assert set(ready.ready_market_ids) == {m.identity.market_id for m in healthy}
    assert ready.failed_market_ids == (sp500_id,)
    healthy_ids = {m.identity.market_id for m in healthy}
    for market_id in healthy_ids:
        assert authority.store.last_open(market_id) == 3 * SLOT
    live_finalized = [open_ms for _, open_ms in finalized if open_ms > 0]
    assert live_finalized and all(open_ms == SLOT for open_ms in live_finalized[:4])


class ScriptedGrid(ScriptedClient):
    def __init__(self, grid: CohortGrid) -> None:
        super().__init__(lambda coin, start, end: self._respond(coin, start, end))
        self.grid = grid

    def _respond(self, coin: str, start_ms: int, end_ms: int) -> object:
        if coin == "BTC" and self.grid.fail_btc_once and start_ms == SLOT:
            self.grid.fail_btc_once = False
            return PublicDataError("transient public route failure")
        return self.grid.candles(coin, start_ms, end_ms)
