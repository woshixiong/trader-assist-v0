"""Opt-in public-only rehearsal of the production Hyperliquid WS session."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable
from datetime import UTC, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

import pytest

from scripts.build_multi_asset_registry_seed import build_seed
from scripts.verify_exact_release import build_release_manifest, exact_clean_head
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.bootstrap import BoundaryReport
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import (
    HyperliquidPublicClient,
    OfficialMetadataValidator,
)
from trader_assist_v0.multi_asset_shadow.models import MarketLifecycle, RegistryVersion
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.planning import CostModel
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
from trader_assist_v0.multi_asset_shadow.resolution import resolve_first_launch_20
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode, MultiAssetPublicRuntime


def async_test(function):  # type: ignore[no-untyped-def]
    @wraps(function)
    def runner(*args, **kwargs):  # type: ignore[no-untyped-def]
        return asyncio.run(function(*args, **kwargs))

    return runner


def _rehearsal_release_identity(root: Path) -> tuple[str, str]:
    if os.environ.get("TRADE_OS_RUN_HYPERLIQUID_FULL_APPLICATION") != "1":
        raise ValueError("full-application public rehearsal is default-off")
    expected = os.environ.get("TRADE_OS_PUBLIC_REHEARSAL_RELEASE_SHA", "")
    head = exact_clean_head(root, expected_head=expected)
    manifest = build_release_manifest(root, release_sha=head)
    return head, str(manifest["manifest_sha256"])


class NoNetworkNotificationClient:
    """Injected delivery sink: records envelopes and performs no network I/O."""

    def __init__(self) -> None:
        self.calls = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


def test_full_application_rehearsal_guard_is_default_off_and_identity_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRADE_OS_RUN_HYPERLIQUID_FULL_APPLICATION", raising=False)
    monkeypatch.delenv("TRADE_OS_PUBLIC_REHEARSAL_RELEASE_SHA", raising=False)
    with pytest.raises(ValueError, match="default-off"):
        _rehearsal_release_identity(Path(__file__).parents[1])


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


@pytest.mark.skipif(
    os.environ.get("TRADE_OS_RUN_HYPERLIQUID_FULL_APPLICATION") != "1",
    reason="opt-in public Hyperliquid full-application rehearsal",
)
@async_test
async def test_public_provider_rehearsal_drives_full_three_setup_application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public-only G9: real composition, temporary state, no notification network."""
    root = Path(__file__).parents[1]
    release_sha, release_manifest_sha = _rehearsal_release_identity(root)
    state = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", state)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", state / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", state / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", state / "closed-bars.sqlite"
    )

    client = HyperliquidPublicClient()
    observed_at = datetime.now(UTC)
    seed = build_seed(
        version=f"public-rehearsal-{release_sha[:12]}",
        observed_at=observed_at,
        client=client,
    )
    assert len(seed.markets) == 20
    registry = MarketRegistryManager(
        production.THREE_SETUP_REGISTRY_ROOT,
        metadata_validator=OfficialMetadataValidator(client),
    )
    registry.stage(seed)
    registry.request_apply(seed.version)
    sink = NoNetworkNotificationClient()
    config = production.ThreeSetupProductionConfig(
        release_sha=release_sha,
        evidence_store_path=production.THREE_SETUP_EVIDENCE_STORE_PATH,
        registry_root=production.THREE_SETUP_REGISTRY_ROOT,
        closed_bar_store_path=production.THREE_SETUP_CLOSED_BAR_STORE_PATH,
        cost_model=CostModel("public-rehearsal", Decimal(), Decimal(), Decimal("2")),
        acknowledgement_timeout_seconds=30,
        notification_poll_seconds=1,
    )
    notification_adapter = WebhookDeliveryAdapter(
        client=sink,
        config=WebhookConfig(url="https://example.invalid/no-network"),
    )
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=notification_adapter,
        public_client=client,
    )
    assert notification_adapter._client is sink
    reports: list[BoundaryReport] = []
    real_callback = application.bootstrap.runtime.on_finalized_5m
    assert real_callback is not None

    async def observe_real_callback(bar: object, mode: BoundaryMode) -> object:
        value = real_callback(bar, mode)  # type: ignore[arg-type]
        report = await value if isinstance(value, Awaitable) else value
        assert isinstance(report, BoundaryReport)
        reports.append(report)
        return report

    application.bootstrap.runtime.on_finalized_5m = observe_real_callback  # type: ignore[assignment]
    shutdown = asyncio.Event()
    task = asyncio.create_task(application.run(shutdown))
    try:
        # WARMING -> HISTORY_READY -> SNAPSHOT_READY -> ACTIVE, followed by a
        # fresh natural 5m boundary, may span four provider boundaries.
        async with asyncio.timeout(1_800):
            while not application.bootstrap.runtime.health.data_ready:
                if task.done():
                    await task
                    raise AssertionError("full application exited before READY")
                await asyncio.sleep(0.1)
            assert application.bootstrap.runtime.health.subscriptions == 20
            assert len(application.bootstrap.runtime.health.acknowledgements) == 20
            assert application.bootstrap.registry.active() is not None
            assert application.bootstrap.evidence._connection.execute(
                "SELECT COUNT(*) FROM immutable_records"
            ).fetchone() is not None
            while True:
                if task.done():
                    await task
                    raise AssertionError("full application exited before LIVE_ACTIONABLE")
                active = application.bootstrap.registry.active()
                target_ids = (
                    ()
                    if active is None
                    else tuple(
                        market.identity.market_id
                        for market in active.markets
                        if market.lifecycle is MarketLifecycle.ACTIVE
                    )
                )
                qualifying = [
                    report
                    for report in reports
                    if report.evaluation_mode is BoundaryMode.LIVE_ACTIONABLE
                    and report.scanner_run_count == 1
                    and report.evaluated_market_ids == target_ids
                    and len(target_ids) == 20
                ]
                if qualifying:
                    report = qualifying[-1]
                    assert report.failures == ()
                    await asyncio.sleep(6)
                    assert sum(
                        item.boundary_open_time_ms == report.boundary_open_time_ms
                        for item in reports
                    ) == 1
                    break
                await asyncio.sleep(0.1)
    finally:
        shutdown.set()
        await task

    assert application.bootstrap.runtime.health.data_ready is False
    print(f"PUBLIC_REHEARSAL_RELEASE_SHA={release_sha}")
    print(f"PUBLIC_REHEARSAL_MANIFEST_SHA256={release_manifest_sha}")
