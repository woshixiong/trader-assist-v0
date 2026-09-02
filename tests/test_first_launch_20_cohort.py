"""PHASE 1 frozen contract: canonical First-Launch-20 barrier composition.

Packet sections 24 and 32 (attack AN).  Any test claiming EXACT FIRST LAUNCH 20
must derive market identities/order from the production resolver
``resolution.py`` — never a hand-copied COINS tuple.  The provider budget for a
fresh boundary is exactly two targeted exact-T confirmations per market, a
duplicate boundary performs zero additional finality REST, and a lagging
ACTIVE market routes to context recovery without a whole-cohort re-burst.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle, RegistryVersion
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.resolution import (
    INITIAL_40,
    resolve_first_launch_20,
)
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime

FIVE_MINUTES_MS = 300_000
T = 100 * FIVE_MINUTES_MS
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def _metadata() -> tuple[list[object], list[object]]:
    native: list[object] = []
    hip3: list[object] = []
    for request in INITIAL_40:
        raw = {"name": request.coin, "szDecimals": 2, "maxLeverage": 10}
        (native if request.dex == "MAIN" else hip3).append(raw)
    return [{"name": "main"}, {"name": "xyz"}], [{"universe": native}, {"universe": hip3}]


def exact_first_launch_20() -> tuple[object, ...]:
    dexes, metas = _metadata()
    resolved = resolve_first_launch_20(perp_dexes=dexes, all_perp_metas=metas, observed_at=NOW)
    assert all(item.status == "RESOLVED" and item.market is not None for item in resolved)
    return tuple(
        item.market.model_copy(update={"lifecycle": MarketLifecycle.SNAPSHOT_READY})
        for item in resolved
    )


def candle(coin: str, open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + FIVE_MINUTES_MS - 1,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": "100",
        "v": "10",
    }


class BudgetClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert interval == "5m"
        self.calls.append((coin, start_ms, end_ms))
        if end_ms - start_ms == FIVE_MINUTES_MS:
            return [candle(coin, start_ms)]
        return [candle(coin, open_ms) for open_ms in range(start_ms, end_ms, FIVE_MINUTES_MS)]


def compose(
    tmp_path: Path,
    *,
    items: tuple[object, ...] | None = None,
    mark_ready: bool = True,
) -> tuple[
    MultiAssetPublicRuntime, MultiAssetDataAuthority, BudgetClient, list, tuple[object, ...]
]:
    items = items if items is not None else exact_first_launch_20()
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(
        version="first-launch-20-seed", created_at=NOW, markets=items  # type: ignore[arg-type]
    )
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    client = BudgetClient()
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        clock=lambda: datetime.fromtimestamp((T + FIVE_MINUTES_MS + 5_000) / 1000, UTC),
        monotonic=lambda: 0.0,
        sleep=lambda _: asyncio.sleep(0),
        on_finalized_5m=on_finalized,
    )
    if mark_ready:
        runtime.health.data_ready = True
    return runtime, authority, client, wakes, items


def seed_history(
    authority: MultiAssetDataAuthority, items: tuple[object, ...], through: int
) -> None:
    for item in items:
        authority.admit_rest_history(
            market=item,  # type: ignore[arg-type]
            snapshot=[
                candle(item.identity.coin, open_ms)  # type: ignore[attr-defined]
                for open_ms in range(0, through + FIVE_MINUTES_MS, FIVE_MINUTES_MS)
            ],
            received_at=datetime.fromtimestamp((through + FIVE_MINUTES_MS + 4_000) / 1000, UTC),
        )


class SessionCohortSocket:
    def __init__(self) -> None:
        self.frames: asyncio.Queue[str] = asyncio.Queue()
        self.sent: list[str] = []
        self.closed = False

    async def send(self, raw: str) -> None:
        self.sent.append(raw)

    async def recv(self) -> str:
        return await self.frames.get()

    async def close(self) -> None:
        self.closed = True


@async_test
async def test_exact_first_launch_20_uses_real_session_seam_for_ack_and_ready(
    tmp_path: Path,
) -> None:
    runtime, authority, _, wakes, items = compose(tmp_path, mark_ready=False)
    seed_history(authority, items, T)
    shutdown = asyncio.Event()
    socket = SessionCohortSocket()

    async def factory(_: str) -> SessionCohortSocket:
        return socket

    async def ticker(stop: asyncio.Event) -> None:
        await stop.wait()

    runtime.websocket_factory = factory
    runtime._barrier_ticker = ticker  # type: ignore[method-assign]
    task = asyncio.create_task(runtime.run(shutdown))
    async with asyncio.timeout(2):
        while len(socket.sent) != 20:
            await asyncio.sleep(0.001)
        socket.frames.put_nowait("Websocket connection established.")
        for item in items:
            socket.frames.put_nowait(
                json.dumps(
                    {
                        "channel": "subscriptionResponse",
                        "data": {
                            "method": "subscribe",
                            "subscription": {
                                "type": "candle",
                                "coin": item.identity.coin,  # type: ignore[attr-defined]
                                "interval": "5m",
                            },
                        },
                    }
                )
            )
        while not runtime.health.data_ready:
            await asyncio.sleep(0.001)
    assert runtime.health.subscriptions == 20
    assert runtime.health.acknowledgements == {
        item.identity.coin for item in items  # type: ignore[attr-defined]
    }
    assert {item.display for item in items} >= {"SKHX", "WTIOIL"}  # type: ignore[attr-defined]
    subscribed_coins = {
        json.loads(raw)["subscription"]["coin"] for raw in socket.sent
    }
    assert {"xyz:SKHX", "xyz:CL"} <= subscribed_coins
    assert wakes == []
    shutdown.set()
    await task
    assert socket.closed
    assert runtime.health.data_ready is False
    assert runtime.health.acknowledgements == set()


@async_test
async def test_exact_twenty_fresh_boundary_uses_forty_targeted_calls(tmp_path: Path) -> None:
    runtime, authority, client, wakes, items = compose(tmp_path)
    seed_history(authority, items, T - FIVE_MINUTES_MS)
    runtime.health.acknowledgements = {item.identity.coin for item in items}  # type: ignore[attr-defined]
    await runtime.process_cohort_boundary(T)
    exact_calls = [call for call in client.calls if call[2] - call[1] == FIVE_MINUTES_MS]
    assert len(client.calls) == 40
    assert len(exact_calls) == 40
    assert {call[0] for call in exact_calls} == {item.identity.coin for item in items}  # type: ignore[attr-defined]
    # Registry transition at T: no live action on the switch boundary.
    assert wakes == []
    active = runtime.registry.active()
    assert active is not None
    assert all(market.lifecycle is MarketLifecycle.ACTIVE for market in active.markets)


@async_test
async def test_exact_twenty_duplicate_boundary_uses_zero_finality_rest(tmp_path: Path) -> None:
    runtime, authority, client, _, items = compose(tmp_path)
    seed_history(authority, items, T - FIVE_MINUTES_MS)
    runtime.health.acknowledgements = {item.identity.coin for item in items}  # type: ignore[attr-defined]
    await runtime.process_cohort_boundary(T)
    before = len(client.calls)
    await runtime.process_cohort_boundary(T)
    assert len(client.calls) == before
    await runtime.process_cohort_boundary(T + FIVE_MINUTES_MS)
    assert len(client.calls) == before + 40


@async_test
async def test_nineteen_durable_one_missing_proves_only_the_missing_market(
    tmp_path: Path,
) -> None:
    # Nineteen exact-T rows retained before barrier entry are context, not
    # evidence for a new whole-cohort callback. The barrier proves only the
    # one genuinely missing current-live-eligible market (two calls) and does
    # not retrospectively combine it with retained rows into LIVE authority.
    active_items = tuple(
        item.model_copy(update={"lifecycle": MarketLifecycle.ACTIVE})  # type: ignore[attr-defined]
        for item in exact_first_launch_20()
    )
    runtime, authority, client, wakes, items = compose(tmp_path, items=active_items)
    for index, item in enumerate(items):
        seed_history(authority, (item,), T if index < 19 else T - FIVE_MINUTES_MS)
    runtime.health.acknowledgements = {item.identity.coin for item in items}  # type: ignore[attr-defined]
    await runtime.process_cohort_boundary(T)
    missing_coin = items[19].identity.coin  # type: ignore[attr-defined]
    assert {call[0] for call in client.calls} == {missing_coin}
    assert len(client.calls) == 2
    assert authority.store.last_open(items[19].identity.market_id) == T  # type: ignore[attr-defined]
    assert wakes == []
