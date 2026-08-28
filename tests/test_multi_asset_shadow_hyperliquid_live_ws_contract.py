"""Opt-in public-only rehearsal of the production Hyperliquid WS session."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

import pytest

from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
    OfficialMetadataValidator,
)
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.resolution import resolve_first_launch_20
from trader_assist_v0.multi_asset_shadow.runtime import MultiAssetPublicRuntime


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


@pytest.mark.skipif(
    os.environ.get("TRADE_OS_RUN_HYPERLIQUID_LIVE_WS") != "1",
    reason="opt-in public Hyperliquid rehearsal",
)
@async_test
async def test_canonical_first_launch_20_live_public_session_contract(tmp_path: Path) -> None:
    """Exercise candidate production code without account or exchange-write access."""
    client = HyperliquidPublicClient()
    observed_at = datetime.now(UTC)
    resolved = resolve_first_launch_20(
        perp_dexes=client.perp_dexes(),
        all_perp_metas=client.all_perp_metas(),
        observed_at=observed_at,
    )
    assert len(resolved) == 20
    assert all(item.status == "RESOLVED" and item.market is not None for item in resolved)
    markets = tuple(item.market for item in resolved if item.market is not None)
    assert len(markets) == 20
    assert {market.display for market in markets} >= {"SKHX", "WTIOIL"}

    registry = MarketRegistryManager(
        tmp_path / "registry", metadata_validator=OfficialMetadataValidator(client)
    )
    version = RegistryVersion.create(
        version="issue-129-live-first-launch-20",
        created_at=observed_at,
        markets=markets,
    )
    registry.stage(version)
    registry.request_apply(version.version)
    authority = MultiAssetDataAuthority(
        store=ClosedBarStore(tmp_path / "closed-bars.sqlite"), registry=registry
    )
    runtime = MultiAssetPublicRuntime(
        registry=registry,
        authority=authority,
        client=client,
    )
    shutdown = asyncio.Event()
    task = asyncio.create_task(runtime.run(shutdown))
    try:
        async with asyncio.timeout(300):
            while not runtime.health.data_ready:
                if task.done():
                    await task
                    raise AssertionError("runtime exited before READY")
                await asyncio.sleep(0.1)
            assert runtime.health.subscriptions == 20
            assert runtime.health.expected_acknowledgements == 20
            assert len(runtime.health.acknowledgements) == 20
            assert runtime.health.last_disconnect_error not in {
                "DataRouteError",
                "ReconnectRequired",
            }
            heartbeat_start = runtime.health.heartbeat_sent
            pong_start = runtime.health.heartbeat_pongs
            while (
                runtime.health.heartbeat_sent - heartbeat_start < 2
                or runtime.health.heartbeat_pongs - pong_start < 1
            ):
                if task.done():
                    await task
                    raise AssertionError("runtime exited during heartbeat rehearsal")
                await asyncio.sleep(0.1)
            assert runtime.health.heartbeat_failures == 0
    finally:
        shutdown.set()
        try:
            await task
        finally:
            authority.store.close()

    assert runtime.health.data_ready is False
    assert runtime.health.connection_count == 0
    assert runtime.health.acknowledgements == set()
    assert not {
        item.get_name() for item in asyncio.all_tasks() if item is not asyncio.current_task()
    } & {"hyperliquid-ws-receiver", "hyperliquid-ws-heartbeat"}
