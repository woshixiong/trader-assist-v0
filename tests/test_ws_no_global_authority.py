"""PHASE 1 frozen contract: WebSocket paths hold no global authority.

Packet rulings 1 and 15, and attack matrix AR/AV.  WebSocket messages,
subscription ACKs, reconnect, and per-market callbacks may update observations
and readiness only.  No flag, compatibility mode, test mode, or default may
let them stage lifecycle, activate a Registry successor, or wake the global
Scanner/Strategy application.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

from trader_assist_v0.contracts.common import sha256_hex
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


class Clock:
    def __init__(self, seconds: int = 603) -> None:
        self.seconds = seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)

    def monotonic(self) -> float:
        return 0.0

    async def sleep(self, seconds: float) -> None:
        self.seconds += int(seconds)
        await asyncio.sleep(0)


def candle(coin: str, open_ms: int) -> dict[str, object]:
    return {
        "i": "5m",
        "s": coin,
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "102",
        "l": "99",
        "c": "100",
        "v": "10",
    }


def market(coin: str = "BTC") -> RegistryMarket:
    return RegistryMarket(
        display=coin,
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin=coin),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=40,
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.WARMING,
        metadata_observed_at=datetime(2026, 8, 12, tzinfo=UTC),
        metadata_hash=sha256_hex(coin.encode()),
    )


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        self.calls.append((coin, start_ms, end_ms))
        return [candle(coin, open_ms) for open_ms in range(start_ms, end_ms, 300_000)]


def setup(tmp_path: Path) -> tuple[
    MultiAssetPublicRuntime, MultiAssetDataAuthority, RegistryMarket, RecordingClient, list
]:
    clock = Clock()
    item = market()
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    seed = RegistryVersion.create(version="seed", created_at=clock.now(), markets=(item,))
    registry.stage(seed)
    registry.request_apply(seed.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed.sqlite"), registry=registry
    )
    client = RecordingClient()
    wakes: list[tuple[int, BoundaryMode]] = []

    async def on_finalized(bar: object, mode: BoundaryMode) -> None:
        wakes.append((bar.open_time_ms, mode))  # type: ignore[attr-defined]

    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,  # type: ignore[arg-type]
        clock=clock.now,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        on_finalized_5m=on_finalized,
    )
    return runtime, authority, item, client, wakes


def ack(coin: str = "BTC") -> str:
    return json.dumps(
        {
            "channel": "subscriptionResponse",
            "data": {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": coin, "interval": "5m"},
            },
        }
    )


@async_test
async def test_ws_candle_message_never_wakes_application(tmp_path: Path) -> None:
    runtime, authority, item, client, wakes = setup(tmp_path)
    # Establish the initial active Registry through the accepted first
    # provider admission; the WS path itself must then stay observation-only.
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=datetime(2026, 8, 12, tzinfo=UTC)
    )
    runtime.health.data_ready = True
    pointer_before = (tmp_path / "registry" / "current.json").read_bytes()
    bars_before = authority.store.bars(item.identity.market_id)
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 0)}))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert wakes == []
    assert client.calls == []
    assert authority.store.bars(item.identity.market_id) == bars_before
    assert (tmp_path / "registry" / "current.json").read_bytes() == pointer_before
    assert registry_pending_is_none(tmp_path)


@async_test
async def test_ws_candle_message_never_stages_lifecycle(tmp_path: Path) -> None:
    runtime, authority, item, _, _ = setup(tmp_path)
    # Make the market history-eligible so old WS-driven staging would have
    # advanced WARMING -> HISTORY_READY if any authority remained.
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=datetime(2026, 8, 12, tzinfo=UTC)
    )
    runtime.health.data_ready = True
    active_before = runtime.registry.active()
    assert active_before is not None
    await runtime.handle_message(json.dumps({"channel": "candle", "data": candle("BTC", 300_000)}))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    active_after = runtime.registry.active()
    assert active_after is not None
    assert active_after.version == active_before.version
    assert active_after.content_hash == active_before.content_hash
    assert registry_pending_is_none(tmp_path)


@async_test
async def test_acknowledgement_path_performs_no_lifecycle_staging(tmp_path: Path) -> None:
    runtime, authority, item, _, _ = setup(tmp_path)
    # Establish the initial active Registry through the first provider
    # admission; the ACK path itself must then stay observation-only.
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=datetime(2026, 8, 12, tzinfo=UTC)
    )
    runtime._expected_acks = {"BTC"}
    await runtime.handle_message(ack())
    assert runtime.health.acknowledgements == {"BTC"}
    assert registry_pending_is_none(tmp_path)
    active = runtime.registry.active()
    assert active is not None and active.markets[0].lifecycle is MarketLifecycle.WARMING


@async_test
async def test_reconnect_recovery_never_wakes_application(tmp_path: Path) -> None:
    runtime, authority, item, _, wakes = setup(tmp_path)
    authority.admit_rest_history(
        market=item, snapshot=[candle("BTC", 0)], received_at=datetime(2026, 8, 12, tzinfo=UTC)
    )
    await runtime._warmup_all(recovery=True)
    assert wakes == []


def test_runtime_exposes_no_ws_finality_authority_or_flag() -> None:
    # The per-market WS finality scheduler itself must be gone, and the
    # constructor must offer no compatibility flag that could restore a
    # second global wake path.
    assert not hasattr(MultiAssetPublicRuntime, "ws_candidate_finality")
    parameters = inspect.signature(MultiAssetPublicRuntime.__init__).parameters
    assert "ws_candidate_finality" not in parameters
    runtime_attributes = {
        name for name in vars(MultiAssetPublicRuntime) if not name.startswith("__")
    }
    assert "_finality" not in runtime_attributes
    assert "_confirm_generation" not in runtime_attributes


def registry_pending_is_none(tmp_path: Path) -> bool:
    return not (tmp_path / "registry" / "pending.json").exists()
