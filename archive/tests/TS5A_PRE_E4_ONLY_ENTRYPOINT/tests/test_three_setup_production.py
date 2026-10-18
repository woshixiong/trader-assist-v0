"""Deterministic production-composition acceptance for the Three Setup release."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

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
from trader_assist_v0.multi_asset_shadow.runtime import BoundaryMode
from trader_assist_v0.multi_asset_shadow.shadow_records import EvidenceStore

SHA = "a" * 40
OFFICIAL_BTC_METADATA = {"name": "BTC", "szDecimals": 5, "maxLeverage": "40"}


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


class MutableClock:
    def __init__(self, seconds: int) -> None:
        self.seconds = seconds

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.seconds, UTC)


def _candle(index: int) -> dict[str, object]:
    open_ms = index * 300_000
    return {
        "i": "5m",
        "s": "BTC",
        "t": open_ms,
        "T": open_ms + 299_999,
        "o": "100",
        "h": "101",
        "l": "99",
        "c": "100",
        "v": "10",
    }


class StartupPublicClient:
    def __init__(self, clock: MutableClock) -> None:
        self.clock = clock

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        assert coin == "BTC" and interval == "5m"
        return [
            _candle(index)
            for index in range(start_ms // 300_000, end_ms // 300_000)
        ]

    def l2_book(self, *, coin: str) -> object:
        assert coin == "BTC"
        return {
            "coin": coin,
            "time": int(self.clock.now().timestamp() * 1000),
            "levels": [
                [{"px": "100", "sz": "100"}],
                [{"px": "100.1", "sz": "100"}],
            ],
        }

    def perp_dexes(self) -> object:
        return [{}]

    def all_perp_metas(self) -> object:
        return [{"universe": [OFFICIAL_BTC_METADATA]}]


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


def test_initial_pending_registry_composes_then_activates_only_from_provider_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    config_path = tmp_path / "config.json"
    config_path.write_bytes(canonical_json_bytes(_config_values()))
    config = production.load_three_setup_config(config_path)
    registry = MarketRegistryManager(config.registry_root, metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="manual-40",
        created_at=datetime(2026, 8, 16, tzinfo=UTC),
        markets=(
            _market().model_copy(
                update={
                    "lifecycle": MarketLifecycle.WARMING,
                    "metadata_hash": sha256_hex(canonical_json_bytes(OFFICIAL_BTC_METADATA)),
                }
            ),
        ),
    )
    registry.stage(version)
    registry.request_apply(version.version)
    pending = registry.pending_version()
    assert registry.active() is None and pending is not None
    pending_identity = (pending.version, pending.content_hash)

    clock = MutableClock(seconds=64 * 300 + 3)
    webhook = Webhook()
    application = production.compose_three_setup_application(
        config=config,
        notification_adapter=WebhookDeliveryAdapter(
            client=webhook, config=WebhookConfig(url="https://example.invalid/hook")
        ),
        public_client=StartupPublicClient(clock),  # type: ignore[arg-type]
        clock=clock.now,
    )
    bootstrap = application.bootstrap
    assert bootstrap.registry.active() is None
    assert (current := bootstrap.registry.pending_version()) is not None
    assert (current.version, current.content_hash) == pending_identity
    immutable_count = bootstrap.evidence._connection.execute(
        "SELECT COUNT(*) FROM immutable_records"
    ).fetchone()[0]
    outbox_count = bootstrap.evidence._connection.execute(
        "SELECT COUNT(*) FROM notification_outbox"
    ).fetchone()[0]
    assert immutable_count == 0
    assert outbox_count == 0
    for table in (
        "scanner_evidence",
        "strategy_evaluations",
        "formal_signals",
        "plan_records",
        "shadow_orders",
    ):
        count = bootstrap.evidence._connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        assert count == 0
    assert bootstrap.data_authority.store.connection.execute(
        "SELECT COUNT(*) FROM closed_bars"
    ).fetchone()[0] == 0
    assert webhook.calls == 0

    # This public warmup is the existing MultiAssetDataAuthority path.  It is
    # the first operation allowed to consume the provider admission capability.
    warming = bootstrap.runtime.selected_markets()[0]
    assert bootstrap.runtime.warmup(warming, start_ms=0, end_ms=64 * 300_000) == 64
    active = bootstrap.registry.active()
    assert active is not None and active.markets[0].lifecycle is MarketLifecycle.WARMING
    assert bootstrap.registry.pending_version() is None
    assert bootstrap.runtime._history_current(active.markets[0])

    lifecycles = [active.markets[0].lifecycle]
    for open_ms, snapshot_ready, expected in (
        (64 * 300_000, False, MarketLifecycle.HISTORY_READY),
        (65 * 300_000, True, MarketLifecycle.SNAPSHOT_READY),
        (66 * 300_000, True, MarketLifecycle.ACTIVE),
    ):
        bootstrap.runtime.health.data_ready = snapshot_ready
        bootstrap.runtime.health.acknowledgements = {active.markets[0].identity.coin}
        clock.seconds = (open_ms + 303_000) // 1000
        admitted = bootstrap.data_authority.admit_rest_history(
            market=active.markets[0],
            snapshot=[_candle(open_ms // 300_000)],
            received_at=clock.now(),
        )
        assert len(admitted) == 1
        # Lifecycle staging is owned solely by the cohort barrier: each
        # boundary advances exactly one legal stage under the single owner.
        asyncio.run(bootstrap.runtime.process_cohort_boundary(open_ms))
        active = bootstrap.registry.active()
        assert active is not None and active.markets[0].lifecycle is expected
        lifecycles.append(active.markets[0].lifecycle)
    assert lifecycles == [
        MarketLifecycle.WARMING,
        MarketLifecycle.HISTORY_READY,
        MarketLifecycle.SNAPSHOT_READY,
        MarketLifecycle.ACTIVE,
    ]

    bootstrap.runtime.health.data_ready = True
    assert asyncio.run(bootstrap.reconcile()) == ()
    # The activation boundary is bound to the prior lifecycle version.  The
    # next provider-admitted close is the first legitimate ACTIVE boundary.
    boundary = 67 * 300_000
    clock.seconds = (boundary + 303_000) // 1000
    admitted = bootstrap.data_authority.admit_rest_history(
        market=active.markets[0],
        snapshot=[_candle(boundary // 300_000)],
        received_at=clock.now(),
    )
    assert len(admitted) == 1
    bootstrap.coordinator.evaluate_finalized_market(
        market_id=active.markets[0].identity.market_id,
        source_open_time_ms=boundary,
        evaluation_mode=BoundaryMode.LIVE_ACTIONABLE,
    )
    assert bootstrap.evidence._connection.execute(
        "SELECT COUNT(*) FROM strategy_evaluations"
    ).fetchone()[0] == 1

    boundary += 300_000
    clock.seconds = (boundary + 303_000) // 1000
    admitted = bootstrap.data_authority.admit_rest_history(
        market=active.markets[0],
        snapshot=[_candle(boundary // 300_000)],
        received_at=clock.now(),
    )
    assert len(admitted) == 1
    report = asyncio.run(bootstrap.process_boundary(boundary, BoundaryMode.LIVE_ACTIONABLE))
    assert report.failures == ()
    assert report.evaluated_market_ids == (active.markets[0].identity.market_id,)
    strategy_count = bootstrap.evidence._connection.execute(
        "SELECT COUNT(*) FROM strategy_evaluations"
    ).fetchone()[0]
    assert strategy_count == 2
    duplicate = asyncio.run(bootstrap.process_boundary(boundary, BoundaryMode.LIVE_ACTIONABLE))
    assert duplicate.failures == ()
    assert bootstrap.evidence._connection.execute(
        "SELECT COUNT(*) FROM strategy_evaluations"
    ).fetchone()[0] == strategy_count
    assert webhook.calls == 0

    bootstrap.close()
    bootstrap.data_authority.store.close()
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.evidence._connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        bootstrap.data_authority.store.connection.execute("SELECT 1")


@pytest.mark.parametrize(
    "retained_work",
    ("scanner_evidence", "strategy_evaluation", "formal_signal", "notification_outbox"),
)
def test_initial_pending_registry_rejects_retained_application_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retained_work: str
) -> None:
    root = tmp_path / "state"
    monkeypatch.setattr(production, "THREE_SETUP_STATE_ROOT", root)
    monkeypatch.setattr(production, "THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite")
    monkeypatch.setattr(production, "THREE_SETUP_REGISTRY_ROOT", root / "registry")
    monkeypatch.setattr(
        production, "THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"
    )
    config_path = tmp_path / "config.json"
    config_path.write_bytes(canonical_json_bytes(_config_values()))
    config = production.load_three_setup_config(config_path)
    registry = MarketRegistryManager(config.registry_root, metadata_validator=lambda _: True)
    version = RegistryVersion.create(
        version="manual-40", created_at=datetime(2026, 8, 16, tzinfo=UTC), markets=(_market(),)
    )
    registry.stage(version)
    registry.request_apply(version.version)
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
            public_client=PublicClient(),  # type: ignore[arg-type]
            clock=Clock().now,
        )


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
