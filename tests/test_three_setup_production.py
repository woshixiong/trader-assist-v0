"""Deterministic production-composition acceptance for the Three Setup release."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import sys
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow import production
from trader_assist_v0.multi_asset_shadow.data import ClosedBarStore, MultiAssetDataAuthority
from trader_assist_v0.multi_asset_shadow.integration import IntegrationError
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
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore
from trader_assist_v0.nautilus_e4.contracts import (
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4Store

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
    def __init__(self) -> None:
        self.calls = 0

    def post(self, **_: object) -> WebhookResponse:
        self.calls += 1
        return WebhookResponse(204)


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


class E4Node:
    def __init__(self) -> None:
        self.strategy: object | None = None
        self.started = threading.Event()
        self.stopped = threading.Event()
        self.disposed = False
        self.run_calls = 0

    def add_strategy(self, strategy: object) -> None:
        self.strategy = strategy

    def run(self) -> None:
        self.run_calls += 1
        self.started.set()
        self.stopped.wait(timeout=2)

    def handle(self) -> E4Node:
        return self

    def stop(self) -> None:
        self.stopped.set()

    def dispose(self) -> None:
        self.disposed = True


class E4Capture:
    def __init__(self) -> None:
        self.warmup_health = {"readiness": "READY"}
        self.capture_health = {
            "stream_health": "HEALTHY",
            "continuity_requirements_remaining": 0,
            "storage_failures": 0,
            "admitted_observer_failures": (),
        }
        self.observer: object | None = None

    def set_admitted_event_observer(self, observer: object) -> None:
        self.observer = observer


def _e4_composition_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[production.ThreeSetupProductionConfig, E4Node, E4Capture]:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    market = _market()
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=1_800_000_000_000,
        expressions=(
            MarketExpression(
                market_id=market.identity.market_id,
                dex="MAIN",
                provider_coin=market.identity.coin,
                instrument_id="BTC-PERP.HYPERLIQUID",
                expression_id="expr-BTC",
                instrument_metadata_version="v1",
                instrument_metadata_hash=market.metadata_hash,
            ),
        ),
    )
    manifest = RunManifest.create(
        run_id="ts5a-e4-production-test",
        git_sha=SHA,
        git_tree="b" * 40,
        snapshot=snapshot,
        process_epoch="process-1",
        continuity_epoch="continuity-1",
        admission_epoch="admission-1",
        capture_configuration={"bar_types": ["1-MINUTE", "5-MINUTE"]},
        subscription_policy={
            "discovery": [market.identity.market_id],
            "watch": [market.identity.market_id],
            "actionable": [market.identity.market_id],
        },
        trial_ledger_id="ts5a-test",
    )
    e4 = E4Store(tmp_path / "e4")
    e4.initialize(manifest, snapshot)
    registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="three-setup-e4",
        created_at=datetime(2026, 9, 27, tzinfo=UTC),
        markets=(market,),
    )
    registry.stage(version)
    registry.request_apply(version.version)
    node = E4Node()
    capture = E4Capture()
    fake_host = ModuleType("trader_assist_v0.nautilus_e4.host")
    fake_host.build_public_data_node = lambda: node  # type: ignore[attr-defined]
    fake_host.build_capture_strategy = lambda **_kwargs: capture  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "trader_assist_v0.nautilus_e4.host", fake_host)
    config = production.ThreeSetupProductionConfig(
        release_sha=SHA,
        evidence_store_path=root / "evidence.sqlite",
        registry_root=root / "registry",
        closed_bar_store_path=root / "closed-bars.sqlite",
        cost_model=production.CostModel("cost-1", Decimal(), Decimal(), Decimal("2")),
        notification_poll_seconds=1,
        e4_evidence_root=tmp_path / "e4",
        e4_manifest_path=e4.manifest_path,
        e4_snapshot_path=e4.snapshot_path,
        e4_bar_types=(
            "BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
            "BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
        ),
    )
    return config, node, capture


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


@pytest.mark.parametrize(
    "retained_work",
    ("scanner_evidence", "strategy_evaluation", "formal_signal", "notification_outbox"),
)
def test_initial_pending_registry_rejects_retained_application_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retained_work: str
) -> None:
    config, _node, _capture = _e4_composition_fixture(tmp_path, monkeypatch)
    evidence = EvidenceStore(config.evidence_store_path)
    with evidence._connection:
        if retained_work == "scanner_evidence":
            evidence._connection.execute(
                """INSERT INTO immutable_records(
                    record_id, record_type, canonical_hash, identity_json, payload_json
                ) VALUES ('retained-scanner', 'scanner_evidence', '0', '{}', '{}')"""
            )
        else:
            evidence._connection.execute(
                """INSERT INTO notification_outbox(
                    idempotency_key, schema_version, kind, content, created_at, state,
                    attempt_count, next_attempt_at
                ) VALUES ('retained-notification', '1', 'WATCH', '{}', '2026-08-16T00:00:00Z',
                          'PENDING', 0, '2026-08-16T00:00:00Z')"""
            )
    evidence.close()

    with pytest.raises(
        IntegrationError,
        match="cannot restore retained application evidence without active Registry authority",
    ):
        production.compose_three_setup_application(
            config=config,
            notification_adapter=WebhookDeliveryAdapter(
                client=Webhook(), config=WebhookConfig(url="https://example.invalid/hook")
            ),
            clock=Clock().now,
        )

def test_real_composition_owns_one_dispatcher_and_shuts_down_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    config, node, capture = _e4_composition_fixture(tmp_path, monkeypatch)
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=WebhookDeliveryAdapter(
            client=Webhook(), config=WebhookConfig(url="https://example.invalid/hook")
        ),
        clock=Clock().now,
    )
    assert isinstance(application, production.E4ThreeSetupProductionApplication)
    assert node.strategy is capture
    assert capture.observer is not None
    dispatcher_starts = 0
    original_dispatch_loop = application._dispatch_loop

    async def counted_dispatch_loop(shutdown: asyncio.Event) -> None:
        nonlocal dispatcher_starts
        dispatcher_starts += 1
        await original_dispatch_loop(shutdown)

    monkeypatch.setattr(application, "_dispatch_loop", counted_dispatch_loop)

    async def exercise() -> None:
        shutdown = asyncio.Event()
        task = asyncio.create_task(application.run(shutdown))
        started = await asyncio.wait_for(asyncio.to_thread(node.started.wait), timeout=1)
        assert started
        shutdown.set()
        await task

    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        asyncio.run(exercise())
    assert dispatcher_starts == 1
    assert node.run_calls == 1
    assert node.stopped.is_set() and node.disposed
    events = {json.loads(record.message)["event"] for record in caplog.records}
    assert {"STARTUP", "SHUTDOWN"} <= events
    with pytest.raises(sqlite3.ProgrammingError):
        application.bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        application.projection.store.connection.execute("SELECT 1")

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


class SupervisorCloser:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class SupervisorRuntime:
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.on_finalized_5m = None
        self.on_reconnect = None
        self.on_session_event = None

    async def run(self, shutdown: asyncio.Event) -> None:
        if self.outcome == "normal":
            return
        if self.outcome == "exception":
            raise RuntimeError("runtime child failed")
        await shutdown.wait()


class SupervisorDispatcher(SupervisorCloser):
    def dispatch_due(self, *, now: datetime) -> tuple[object, ...]:
        del now
        return ()


def supervisor_application(runtime_outcome: str = "wait") -> tuple[object, object, object]:
    evidence = SupervisorCloser()
    closed_store = SupervisorCloser()
    bootstrap_closed = SupervisorCloser()
    runtime = SupervisorRuntime(runtime_outcome)
    active = SimpleNamespace(version="v1", content_hash="hash")
    bootstrap = SimpleNamespace(
        runtime=runtime,
        registry=SimpleNamespace(active=lambda: active, pending_version=lambda: None),
        coordinator=SimpleNamespace(_release_sha=SHA),
        evidence=evidence,
        data_authority=SimpleNamespace(store=closed_store),
        close=bootstrap_closed.close,
    )
    dispatcher = SupervisorDispatcher()
    application = production.ThreeSetupProductionApplication(
        bootstrap=bootstrap,  # type: ignore[arg-type]
        dispatcher=dispatcher,  # type: ignore[arg-type]
        clock=Clock().now,
        notification_poll_seconds=1,
    )
    return application, dispatcher, closed_store


@pytest.mark.parametrize("outcome", ["normal", "exception"])
def test_runtime_child_exit_before_operator_shutdown_is_fatal(
    outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, dispatcher, store = supervisor_application(outcome)
    expected = (
        "PRODUCTION_CHILD_EXIT_UNEXPECTED" if outcome == "normal" else "runtime child failed"
    )
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(Exception, match=expected):
            asyncio.run(application.run(asyncio.Event()))  # type: ignore[attr-defined]
    child_event = next(
        json.loads(record.message)
        for record in caplog.records
        if json.loads(record.message)["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
    )
    assert child_event["component"] == "runtime"
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]


@pytest.mark.parametrize("outcome", ["normal", "exception"])
def test_dispatcher_child_exit_before_operator_shutdown_is_fatal(
    outcome: str, caplog: pytest.LogCaptureFixture
) -> None:
    application, dispatcher, store = supervisor_application()

    async def dispatcher_exit(_: asyncio.Event) -> None:
        if outcome == "exception":
            raise RuntimeError("dispatcher child failed")

    application._dispatch_loop = dispatcher_exit  # type: ignore[attr-defined,method-assign]
    expected = (
        "PRODUCTION_CHILD_EXIT_UNEXPECTED" if outcome == "normal" else "dispatcher child failed"
    )
    with caplog.at_level(logging.INFO, logger="trader_assist_v0.three_setup"):
        with pytest.raises(Exception, match=expected):
            asyncio.run(application.run(asyncio.Event()))  # type: ignore[attr-defined]
    child_event = next(
        json.loads(record.message)
        for record in caplog.records
        if json.loads(record.message)["event"] == "PRODUCTION_CHILD_EXIT_UNEXPECTED"
    )
    assert child_event["component"] == "dispatcher"
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]


def test_explicit_operator_shutdown_is_clean() -> None:
    application, dispatcher, store = supervisor_application()
    shutdown = asyncio.Event()
    shutdown.set()
    asyncio.run(application.run(shutdown))  # type: ignore[attr-defined]
    assert dispatcher.closed and store.closed  # type: ignore[attr-defined]
