"""Deterministic production-composition acceptance for the Three Setup release."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.models import (
    AssetClass,
    MarketIdentity,
    MarketLifecycle,
    RegistryMarket,
    RegistryTier,
    RegistryVersion,
)
from trader_assist_v0.multi_asset_shadow.notification_engine import (
    WebhookConfig,
    WebhookDeliveryAdapter,
    WebhookResponse,
)
from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager

SHA = "a" * 40


class Clock:
    def now(self) -> datetime:
        return datetime.fromtimestamp(600, UTC)


class PublicClient:
    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert coin == "BTC" and interval == "5m"
        return [
            {
                "i": "5m",
                "s": coin,
                "t": 300_000,
                "T": 599_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ]


class Webhook:
    def post(self, **_: object) -> WebhookResponse:
        return WebhookResponse(204)


class Socket:
    def __init__(self, shutdown: asyncio.Event) -> None:
        self.shutdown = shutdown
        self.closed = False

    async def send(self, _: str) -> None:
        return None

    async def recv(self) -> str:
        self.shutdown.set()
        return json.dumps(
            {
                "channel": "subscriptionResponse",
                "data": {
                    "method": "subscribe",
                    "subscription": {"type": "candle", "coin": "BTC", "interval": "5m"},
                },
            }
        )

    async def close(self) -> None:
        self.closed = True


class FailingDispatcher:
    def __init__(self) -> None:
        self.closed = False

    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        raise sqlite3.DatabaseError("injected dispatcher authority failure")

    def close(self) -> None:
        self.closed = True


def _config_values() -> dict[str, object]:
    return {
        "schema": production.THREE_SETUP_CONFIG_SCHEMA,
        "release_sha": SHA,
        "evidence_store_path": str(production.THREE_SETUP_EVIDENCE_STORE_PATH),
        "registry_root": str(production.THREE_SETUP_REGISTRY_ROOT),
        "closed_bar_store_path": str(production.THREE_SETUP_CLOSED_BAR_STORE_PATH),
        "cost_model": {
            "version": "cost-1",
            "fee_bps_per_side": "0",
            "slippage_bps_per_side": "0",
            "stress_slippage_bps_per_side": "2",
        },
        "acknowledgement_timeout_seconds": 30,
        "notification_poll_seconds": 1,
    }


def _market() -> RegistryMarket:
    return RegistryMarket(
        display="BTC",
        tier=RegistryTier.P0,
        identity=MarketIdentity.create(dex="MAIN", coin="BTC"),
        asset_class=AssetClass.CRYPTO,
        size_decimals=5,
        price_max_decimals=1,
        max_leverage=Decimal("40"),
        is_hip3=False,
        market_status="ACTIVE",
        lifecycle=MarketLifecycle.ACTIVE,
        metadata_observed_at=datetime(2026, 8, 16, tzinfo=UTC),
        metadata_hash=sha256_hex(b"btc-metadata"),
    )


def test_fixed_manifest_config_is_canonical_and_rejects_legacy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    values = _config_values()
    path = tmp_path / "config.json"
    path.write_bytes(canonical_json_bytes(values))
    config = production.load_three_setup_config(path)
    assert config.evidence_store_path != Path("/var/lib/trader-assist-v0/runtime.db")
    values["closed_bar_store_path"] = "/var/lib/trader-assist-v0/runtime.db"
    path.write_bytes(canonical_json_bytes(values))
    with pytest.raises(production.ThreeSetupProductionError, match="fixed manifest"):
        production.load_three_setup_config(path)


def test_real_composition_owns_one_dispatcher_and_shuts_down_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    values = _config_values()
    config_path = tmp_path / "config.json"
    config_path.write_bytes(canonical_json_bytes(values))
    config = production.load_three_setup_config(config_path)
    registry = MarketRegistryManager(config.registry_root, metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="three-setup", created_at=datetime(2026, 8, 16, tzinfo=UTC), markets=(_market(),)
    )
    registry.stage(version)
    registry.request_apply(version.version)
    closed = ClosedBarStore(config.closed_bar_store_path)
    authority = MultiAssetDataAuthority(store=closed, registry=registry)
    authority.admit_rest_history(
        market=_market(),
        snapshot=[
            {
                "i": "5m",
                "s": "BTC",
                "t": 300_000,
                "T": 599_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ],
        received_at=datetime.fromtimestamp(600, UTC),
    )
    closed.close()
    clock = Clock()
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=WebhookDeliveryAdapter(
            client=Webhook(), config=WebhookConfig(url="https://example.invalid/hook")
        ),
        public_client=PublicClient(),  # type: ignore[arg-type]
        clock=clock.now,
    )
    shutdown = asyncio.Event()
    socket = Socket(shutdown)

    async def factory(_: str) -> Socket:
        return socket

    application.bootstrap.runtime.websocket_factory = factory
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        asyncio.run(application.run(shutdown))
    assert socket.closed
    events = {json.loads(record.message)["event"] for record in caplog.records}
    assert {"STARTUP", "RELEASE_IDENTITY", "REGISTRY_IDENTITY", "WARMUP", "SHUTDOWN"} <= events
    with pytest.raises(sqlite3.ProgrammingError):
        application.bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        application.bootstrap.data_authority.store.connection.execute("SELECT 1")


def test_systemd_execstart_targets_the_executable_three_setup_wrapper() -> None:
    root = Path(__file__).parents[1]
    unit = (root / "deploy/p4a/systemd/trader-assist-v0-three-setup.service").read_text()
    wrapper = root / "scripts/p4a/run_three_setup_shadow_runtime.sh"
    assert "ExecStart=/opt/trader-assist-v0/scripts/p4a/run_three_setup_shadow_runtime.sh" in unit
    assert wrapper.stat().st_mode & 0o111


def test_dispatcher_authority_failure_is_fatal_and_closes_all_stores(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    registry = MarketRegistryManager(tmp_path / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="three-setup", created_at=datetime(2026, 8, 16, tzinfo=UTC), markets=(_market(),)
    )
    registry.stage(version)
    registry.request_apply(version.version)
    closed = ClosedBarStore(tmp_path / "closed.sqlite")
    data = MultiAssetDataAuthority(store=closed, registry=registry)
    data.admit_rest_history(
        market=_market(),
        snapshot=[
            {
                "i": "5m",
                "s": "BTC",
                "t": 300_000,
                "T": 599_999,
                "o": "100",
                "h": "101",
                "l": "99",
                "c": "100",
                "v": "10",
            }
        ],
        received_at=Clock().now(),
    )
    bootstrap = production.MultiAssetProductionBootstrap.compose(
        registry=registry,
        data_authority=data,
        public_client=PublicClient(),  # type: ignore[arg-type]
        evidence_db_path=tmp_path / "evidence.sqlite",
        cost_model=production.CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        release_sha=SHA,
        clock=Clock().now,
    )
    dispatcher = FailingDispatcher()
    application = production.ThreeSetupProductionApplication(
        bootstrap=bootstrap,
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=Clock().now,
        notification_poll_seconds=1,
    )
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(sqlite3.DatabaseError, match="injected dispatcher authority failure"):
            asyncio.run(application.run(asyncio.Event()))
    events = [json.loads(record.message) for record in caplog.records]
    assert {event["event"] for event in events} >= {"NOTIFICATION_FAILURE", "SHUTDOWN"}
    assert next(event for event in events if event["event"] == "NOTIFICATION_FAILURE") == {
        "event": "NOTIFICATION_FAILURE",
        "error_type": "DatabaseError",
    }
    assert dispatcher.closed
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.data_authority.store.connection.execute("SELECT 1")
