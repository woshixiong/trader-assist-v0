"""Production composition for the public-only Three Setup shadow release.

This module deliberately binds existing MultiAsset authorities.  It does not
introduce another runtime, scanner, strategy, planner, evidence store, or
notification engine.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.nautilus_e4.capture import SubscriptionPolicy
from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot, RunManifest
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

from .bootstrap import BoundaryReport, MultiAssetProductionBootstrap
from .data import ClosedBarStore, MultiAssetDataAuthority
from .e4_markettruth import E4MarketTruthProjection
from .hyperliquid_public import HyperliquidPublicClient, OfficialMetadataValidator
from .models import ClosedBar, MarketLifecycle
from .notification_engine import OutboxDispatcher, WebhookDeliveryAdapter
from .planning import CostModel
from .registry import MarketRegistryManager
from .runtime import BoundaryMode, E4ThreeSetupRuntime, MultiAssetPublicRuntime
from .shadow_records import EvidenceStore

THREE_SETUP_CONFIG_SCHEMA = "trader-assist-v0/three-setup-production-config/v1"
THREE_SETUP_E4_CONFIG_SCHEMA = "trader-assist-v0/three-setup-production-config/v2"
THREE_SETUP_RELEASE_MODE = "THREE_SETUP_SHADOW_RELEASE"
THREE_SETUP_STATE_ROOT = Path("/var/lib/trader-assist-v0/three-setup-shadow")
THREE_SETUP_EVIDENCE_STORE_PATH = THREE_SETUP_STATE_ROOT / "evidence.sqlite"
THREE_SETUP_REGISTRY_ROOT = THREE_SETUP_STATE_ROOT / "registry"
THREE_SETUP_CLOSED_BAR_STORE_PATH = THREE_SETUP_STATE_ROOT / "closed-bars.sqlite"
THREE_SETUP_CONFIG_PATH = Path("/etc/trader-assist-v0/three-setup-shadow.json")


class ThreeSetupProductionError(ValueError):
    """The fixed Three Setup production contract is invalid."""


@dataclass(frozen=True)
class ThreeSetupProductionConfig:
    """Non-secret, canonical configuration for the fixed durable asset layout."""

    release_sha: str
    evidence_store_path: Path
    registry_root: Path
    closed_bar_store_path: Path
    cost_model: CostModel
    acknowledgement_timeout_seconds: float = 30.0
    notification_poll_seconds: float = 5.0
    e4_evidence_root: Path | None = None
    e4_manifest_path: Path | None = None
    e4_snapshot_path: Path | None = None
    e4_bar_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.release_sha) != 40 or any(
            ch not in "0123456789abcdef" for ch in self.release_sha
        ):
            raise ThreeSetupProductionError(
                "release_sha must be exactly 40 lowercase hex characters"
            )
        if (
            self.evidence_store_path != THREE_SETUP_EVIDENCE_STORE_PATH
            or self.registry_root != THREE_SETUP_REGISTRY_ROOT
            or self.closed_bar_store_path != THREE_SETUP_CLOSED_BAR_STORE_PATH
        ):
            raise ThreeSetupProductionError("Three Setup durable paths must use the fixed manifest")
        if not 1 <= self.acknowledgement_timeout_seconds <= 60:
            raise ThreeSetupProductionError(
                "acknowledgement timeout must be between 1 and 60 seconds"
            )
        if not 1 <= self.notification_poll_seconds <= 60:
            raise ThreeSetupProductionError(
                "notification poll interval must be between 1 and 60 seconds"
            )
        fields = (self.e4_evidence_root, self.e4_manifest_path, self.e4_snapshot_path)
        if any(value is not None for value in fields) and (
            any(value is None for value in fields) or not self.e4_bar_types
        ):
            raise ThreeSetupProductionError(
                "E4 identity requires root, manifest, snapshot and bars"
            )


def load_three_setup_config(path: Path) -> ThreeSetupProductionConfig:
    """Load one canonical non-secret configuration file without guessing paths."""
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ThreeSetupProductionError(
            "Three Setup config is unavailable or invalid JSON"
        ) from exc
    if not isinstance(value, dict) or raw != canonical_json_bytes(value):
        raise ThreeSetupProductionError("Three Setup config must be canonical JSON")
    expected = {
        "schema",
        "release_sha",
        "evidence_store_path",
        "registry_root",
        "closed_bar_store_path",
        "cost_model",
        "acknowledgement_timeout_seconds",
        "notification_poll_seconds",
    }
    e4_fields = {"e4_evidence_root", "e4_manifest_path", "e4_snapshot_path", "e4_bar_types"}
    schema = value.get("schema")
    if not (
        (schema == THREE_SETUP_CONFIG_SCHEMA and set(value) == expected)
        or (schema == THREE_SETUP_E4_CONFIG_SCHEMA and set(value) == expected | e4_fields)
    ):
        raise ThreeSetupProductionError("Three Setup config schema is invalid")
    cost = value["cost_model"]
    if not isinstance(cost, dict) or set(cost) != {
        "version",
        "fee_bps_per_side",
        "slippage_bps_per_side",
        "stress_slippage_bps_per_side",
    }:
        raise ThreeSetupProductionError("Three Setup cost model is invalid")
    try:
        return ThreeSetupProductionConfig(
            release_sha=_exact_string(value["release_sha"], "release_sha"),
            evidence_store_path=Path(_exact_string(value["evidence_store_path"], "evidence path")),
            registry_root=Path(_exact_string(value["registry_root"], "registry root")),
            closed_bar_store_path=Path(
                _exact_string(value["closed_bar_store_path"], "closed bar path")
            ),
            cost_model=CostModel(
                version=_exact_string(cost["version"], "cost version"),
                fee_bps_per_side=Decimal(_exact_string(cost["fee_bps_per_side"], "fee")),
                slippage_bps_per_side=Decimal(
                    _exact_string(cost["slippage_bps_per_side"], "slippage")
                ),
                stress_slippage_bps_per_side=Decimal(
                    _exact_string(cost["stress_slippage_bps_per_side"], "stress slippage")
                ),
            ),
            acknowledgement_timeout_seconds=_exact_number(
                value["acknowledgement_timeout_seconds"], "acknowledgement timeout"
            ),
            notification_poll_seconds=_exact_number(
                value["notification_poll_seconds"], "notification poll interval"
            ),
            e4_evidence_root=(
                Path(_exact_string(value["e4_evidence_root"], "E4 evidence root"))
                if schema == THREE_SETUP_E4_CONFIG_SCHEMA
                else None
            ),
            e4_manifest_path=(
                Path(_exact_string(value["e4_manifest_path"], "E4 manifest path"))
                if schema == THREE_SETUP_E4_CONFIG_SCHEMA
                else None
            ),
            e4_snapshot_path=(
                Path(_exact_string(value["e4_snapshot_path"], "E4 snapshot path"))
                if schema == THREE_SETUP_E4_CONFIG_SCHEMA
                else None
            ),
            e4_bar_types=(
                tuple(_exact_string(item, "E4 bar type") for item in value["e4_bar_types"])
                if schema == THREE_SETUP_E4_CONFIG_SCHEMA
                and isinstance(value["e4_bar_types"], list)
                else ()
            ),
        )
    except ThreeSetupProductionError:
        raise
    except (ArithmeticError, ValueError) as exc:
        raise ThreeSetupProductionError("Three Setup config values are invalid") from exc


def _exact_string(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise ThreeSetupProductionError(f"{label} must be a non-empty string")
    return value


def _exact_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ThreeSetupProductionError(f"{label} must be a number")
    return float(value)


def validate_three_setup_e4_identity(config: ThreeSetupProductionConfig) -> None:
    """Read exact public identity without constructing or starting a node."""
    if (
        config.e4_evidence_root is None
        or config.e4_manifest_path is None
        or config.e4_snapshot_path is None
        or not config.e4_bar_types
    ):
        raise ThreeSetupProductionError("active Three Setup requires explicit E4 identity")
    manifest = RunManifest.model_validate_json(config.e4_manifest_path.read_bytes())
    snapshot = PitUniverseSnapshot.model_validate_json(config.e4_snapshot_path.read_bytes())
    store = E4EvidenceStore(config.e4_evidence_root)
    if store.load_manifest() != manifest or store.load_snapshot() != snapshot:
        raise ThreeSetupProductionError("E4 identity differs from shared durable evidence")
    registry = MarketRegistryManager(config.registry_root, metadata_validator=lambda _: False)
    selected = registry.active() or registry.pending_version()
    if selected is None:
        raise ThreeSetupProductionError("validated Registry authority is required")
    expressions = {item.market_id: item for item in snapshot.expressions}
    for market in selected.markets:
        expression = expressions.get(market.identity.market_id)
        if (
            expression is None
            or expression.dex != market.identity.dex
            or expression.provider_coin != market.identity.coin
            or expression.instrument_metadata_hash != market.metadata_hash
        ):
            raise ThreeSetupProductionError("Registry market differs from current E4 PIT metadata")
        for minute in (1, 5):
            prefix = f"{expression.instrument_id}-{minute}-MINUTE-"
            if not any(item.startswith(prefix) for item in config.e4_bar_types):
                raise ThreeSetupProductionError("E4 subscriptions lack selected 1m/5m market")


def _journal(logger: logging.Logger, event: str, **fields: object) -> None:
    """Emit structured, non-secret operator events to journald."""
    logger.info(json.dumps({"event": event, **fields}, sort_keys=True, separators=(",", ":")))


class ThreeSetupProductionApplication:
    """Owns one runtime loop and one dispatcher task for this composition."""

    def __init__(
        self,
        *,
        bootstrap: MultiAssetProductionBootstrap,
        dispatcher: OutboxDispatcher,
        clock: Callable[[], datetime],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        notification_poll_seconds: float = 5.0,
        logger: logging.Logger | None = None,
    ) -> None:
        self.bootstrap = bootstrap
        self.dispatcher = dispatcher
        self.clock = clock
        self.sleep = sleep
        self.notification_poll_seconds = notification_poll_seconds
        self.logger = logger or logging.getLogger("trader_assist_v0.three_setup")
        self.bootstrap.runtime.on_finalized_5m = self._on_finalized_5m
        self.bootstrap.runtime.on_reconnect = self._on_reconnect
        self.bootstrap.runtime.on_session_event = self._on_session_event

    async def run(self, shutdown: asyncio.Event) -> None:
        active = self.bootstrap.registry.active() or self.bootstrap.registry.pending_version()
        if active is None:
            raise ThreeSetupProductionError("validated Registry authority is required")
        _journal(self.logger, "STARTUP")
        _journal(
            self.logger,
            "RELEASE_IDENTITY",
            release_sha=self.bootstrap.coordinator._release_sha,
        )
        _journal(
            self.logger,
            "REGISTRY_IDENTITY",
            registry_version=active.version,
            registry_content_hash=active.content_hash,
        )
        _journal(self.logger, "WARMUP")
        dispatcher_task = asyncio.create_task(self._dispatch_loop(shutdown))
        runtime_task = asyncio.create_task(self.bootstrap.runtime.run(shutdown))
        try:
            done, _ = await asyncio.wait(
                (runtime_task, dispatcher_task), return_when=asyncio.FIRST_COMPLETED
            )
            if not shutdown.is_set():
                failed_children = tuple(
                    task
                    for task in (runtime_task, dispatcher_task)
                    if task in done and not task.cancelled() and task.exception() is not None
                )
                child = (
                    failed_children[0]
                    if failed_children
                    else (runtime_task if runtime_task in done else dispatcher_task)
                )
                component = "runtime" if child is runtime_task else "dispatcher"
                if child.cancelled():
                    error: BaseException = ThreeSetupProductionError(
                        f"PRODUCTION_CHILD_EXIT_UNEXPECTED: {component} was cancelled"
                    )
                else:
                    error = child.exception() or ThreeSetupProductionError(
                        f"PRODUCTION_CHILD_EXIT_UNEXPECTED: {component} returned normally"
                    )
                _journal(
                    self.logger,
                    "PRODUCTION_CHILD_EXIT_UNEXPECTED",
                    component=component,
                    error_type=type(error).__name__,
                )
                shutdown.set()
                sibling = dispatcher_task if child is runtime_task else runtime_task
                if not sibling.done():
                    sibling.cancel()
                await asyncio.gather(sibling, return_exceptions=True)
                raise error
            results = await asyncio.gather(runtime_task, dispatcher_task, return_exceptions=True)
            for component, result in zip(("runtime", "dispatcher"), results, strict=True):
                if isinstance(result, BaseException) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    _journal(
                        self.logger,
                        "PRODUCTION_CHILD_EXIT_UNEXPECTED",
                        component=component,
                        error_type=type(result).__name__,
                    )
                    raise result
        finally:
            shutdown.set()
            for task in (runtime_task, dispatcher_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(runtime_task, dispatcher_task, return_exceptions=True)
            try:
                await self._close_dispatcher()
            finally:
                try:
                    self.bootstrap.close()
                finally:
                    try:
                        self.bootstrap.data_authority.store.close()
                    finally:
                        _journal(self.logger, "SHUTDOWN")

    async def _on_finalized_5m(self, bar: ClosedBar, mode: BoundaryMode) -> BoundaryReport:
        report = await self.bootstrap.on_finalized_5m(bar, mode)
        _journal(
            self.logger,
            "FINALIZED_5M",
            boundary_open_time_ms=report.boundary_open_time_ms,
            evaluation_mode=report.evaluation_mode.value,
        )
        for failure in report.failures:
            event = "FORMAL" if failure.stage.startswith("FORMAL") else failure.stage
            _journal(
                self.logger,
                event,
                market_id=failure.market_id,
                error_type=failure.error_type,
                provider_coin=failure.provider_coin,
                provider_provenance=failure.provider_provenance,
                side=failure.side,
            )
        _journal(
            self.logger,
            "BOUNDARY_REPORT",
            boundary_open_time_ms=report.boundary_open_time_ms,
            scanner_run_count=report.scanner_run_count,
            disposition=report.disposition.value,
        )
        readiness = self.bootstrap.runtime.readiness_snapshot()
        _journal(
            self.logger,
            "READINESS",
            data_ready=readiness.data_ready,
            runtime_readiness_hash=readiness.snapshot_hash,
        )
        if mode is BoundaryMode.RECOVERY_CONTEXT_ONLY:
            await self.bootstrap.reconcile()
        return report

    def _on_reconnect(self, count: int) -> None:
        _journal(self.logger, "RECONNECT", reconnect_count=count)

    def _on_session_event(self, event: str, fields: dict[str, object]) -> None:
        _journal(self.logger, f"WS_{event}", **fields)

    async def _dispatch_loop(self, shutdown: asyncio.Event) -> None:
        try:
            while not shutdown.is_set():
                now = self.clock()
                if now.tzinfo is not UTC:
                    raise ThreeSetupProductionError("dispatcher clock must be exact UTC")
                results = self.dispatcher.dispatch_due(now=now)
                for result in results:
                    _journal(
                        self.logger,
                        "NOTIFICATION",
                        idempotency_key=result.idempotency_key,
                        state=result.transition.state.value,
                        reason=result.transition.reason,
                    )
                try:
                    await asyncio.wait_for(shutdown.wait(), timeout=self.notification_poll_seconds)
                except TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _journal(self.logger, "NOTIFICATION_FAILURE", error_type=type(exc).__name__)
            raise

    async def _close_dispatcher(self) -> None:
        """Close an injected production dispatcher when it exposes a closer."""
        closer = getattr(self.dispatcher, "close", None)
        if closer is None:
            return
        result = closer()
        if isinstance(result, Awaitable):
            await result


def compose_three_setup_application(
    *,
    config: ThreeSetupProductionConfig,
    notification_adapter: WebhookDeliveryAdapter,
    public_client: HyperliquidPublicClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ThreeSetupProductionApplication:
    """Bind exactly the accepted public components to the fixed path manifest."""
    if public_client is None:
        return _compose_e4_three_setup_application(
            config=config,
            notification_adapter=notification_adapter,
            clock=clock,
            sleep=sleep,
        )
    client = public_client or HyperliquidPublicClient()
    config.evidence_store_path.parent.mkdir(parents=True, exist_ok=True)
    config.closed_bar_store_path.parent.mkdir(parents=True, exist_ok=True)
    config.registry_root.mkdir(parents=True, exist_ok=True)
    registry = MarketRegistryManager(
        config.registry_root, metadata_validator=OfficialMetadataValidator(client)
    )
    data = MultiAssetDataAuthority(
        store=ClosedBarStore(config.closed_bar_store_path), registry=registry
    )
    bootstrap = MultiAssetProductionBootstrap.compose(
        registry=registry,
        data_authority=data,
        public_client=client,
        evidence_db_path=config.evidence_store_path,
        cost_model=config.cost_model,
        release_sha=config.release_sha,
        clock=clock,
        sleep=sleep,
    )
    cast(
        MultiAssetPublicRuntime, bootstrap.runtime
    ).acknowledgement_timeout_seconds = config.acknowledgement_timeout_seconds
    return ThreeSetupProductionApplication(
        bootstrap=bootstrap,
        dispatcher=OutboxDispatcher(outbox=bootstrap.outbox, adapter=notification_adapter),
        clock=clock,
        sleep=sleep,
        notification_poll_seconds=config.notification_poll_seconds,
    )


class E4ThreeSetupProductionApplication(ThreeSetupProductionApplication):
    """One Nautilus node and one bounded Three Setup consumer/dispatcher."""

    def __init__(
        self,
        *,
        node: Any,
        capture: Any,
        bootstrap: MultiAssetProductionBootstrap,
        dispatcher: OutboxDispatcher,
        clock: Callable[[], datetime],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        notification_poll_seconds: float = 5.0,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            bootstrap=bootstrap,
            dispatcher=dispatcher,
            clock=clock,
            sleep=sleep,
            notification_poll_seconds=notification_poll_seconds,
            logger=logger,
        )
        self.node = node
        self.capture = capture
        self.e4_runtime = cast(E4ThreeSetupRuntime, self.bootstrap.runtime)
        self.projection = cast(E4MarketTruthProjection, self.bootstrap.data_authority)
        self.e4_runtime.on_domain_error = self._on_domain_error
        self.capture.set_admitted_event_observer(self.e4_runtime.offer_admission)

    def _on_domain_error(self, market_id: str, admission_hash: str, error_type: str) -> None:
        _journal(
            self.logger,
            "DOMAIN_ADAPTER_FAILURE",
            market_id=market_id,
            admission_hash=admission_hash,
            error_type=error_type,
        )

    async def run(self, shutdown: asyncio.Event) -> None:
        active = self.bootstrap.registry.active() or self.bootstrap.registry.pending_version()
        if active is None:
            raise ThreeSetupProductionError("validated Registry authority is required")
        _journal(
            self.logger,
            "STARTUP",
            registry_version=active.version,
            registry_content_hash=active.content_hash,
        )
        dispatcher_task = asyncio.create_task(self._dispatch_loop(shutdown))
        domain_task = asyncio.create_task(self.e4_runtime.run(shutdown))
        await asyncio.sleep(0)
        node_task = asyncio.create_task(asyncio.to_thread(self.node.run))
        tasks = (dispatcher_task, domain_task, node_task)
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if not shutdown.is_set():
                task = next(
                    (item for item in done if item.exception() is not None), next(iter(done))
                )
                error = task.exception() or ThreeSetupProductionError("E4 production child exited")
                _journal(
                    self.logger, "PRODUCTION_CHILD_EXIT_UNEXPECTED", error_type=type(error).__name__
                )
                raise error
        finally:
            shutdown.set()
            self.node.handle().stop()
            for task in (dispatcher_task, domain_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await self._close_dispatcher()
            finally:
                self.bootstrap.close()
                self.projection.close()
                self.node.dispose()
                _journal(self.logger, "SHUTDOWN")


def _compose_e4_three_setup_application(
    *,
    config: ThreeSetupProductionConfig,
    notification_adapter: WebhookDeliveryAdapter,
    clock: Callable[[], datetime],
    sleep: Callable[[float], Awaitable[None]],
) -> E4ThreeSetupProductionApplication:
    from trader_assist_v0.nautilus_e4.host import build_capture_strategy, build_public_data_node

    validate_three_setup_e4_identity(config)
    e4_manifest_path = config.e4_manifest_path
    e4_snapshot_path = config.e4_snapshot_path
    e4_evidence_root = config.e4_evidence_root
    assert e4_manifest_path is not None
    assert e4_snapshot_path is not None
    assert e4_evidence_root is not None
    manifest = RunManifest.model_validate_json(e4_manifest_path.read_bytes())
    snapshot = PitUniverseSnapshot.model_validate_json(e4_snapshot_path.read_bytes())
    e4_store = E4EvidenceStore(e4_evidence_root)
    if e4_store.load_manifest() != manifest or e4_store.load_snapshot() != snapshot:
        raise ThreeSetupProductionError("E4 identity differs from shared durable evidence")
    config.evidence_store_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = EvidenceStore(config.evidence_store_path)
    holder: dict[str, E4MarketTruthProjection] = {}
    registry = MarketRegistryManager(
        config.registry_root,
        metadata_validator=lambda market: holder["projection"].validate_market(market),
    )
    selected = registry.active() or registry.pending_version()
    if selected is None:
        evidence.close()
        raise ThreeSetupProductionError("validated Registry authority is required")
    policy = SubscriptionPolicy(
        discovery=frozenset(item.market_id for item in snapshot.expressions),
        watch=frozenset(m.identity.market_id for m in selected.markets),
        actionable=frozenset(
            m.identity.market_id for m in selected.markets if m.lifecycle is MarketLifecycle.ACTIVE
        ),
    )
    node = build_public_data_node()
    capture = build_capture_strategy(
        manifest=manifest,
        snapshot=snapshot,
        policy=policy,
        bar_types=config.e4_bar_types,
        evidence_root=e4_evidence_root,
    )
    projection = E4MarketTruthProjection(
        e4_store=e4_store,
        domain_evidence=evidence,
        registry=registry,
        manifest=manifest,
        snapshot=snapshot,
        warmup_health=lambda: capture.warmup_health,
        capture_health=lambda: capture.capture_health,
        clock_ms=lambda: int(clock().timestamp() * 1_000),
    )
    holder["projection"] = projection
    if not all(projection.validate_market(market) for market in selected.markets):
        raise ThreeSetupProductionError("Registry market differs from current E4 PIT metadata")
    registry.bind_e4_evidence_authority(projection)
    node.add_strategy(capture)
    bootstrap = MultiAssetProductionBootstrap.compose_e4(
        registry=registry,
        projection=projection,
        evidence=evidence,
        cost_model=config.cost_model,
        release_sha=config.release_sha,
        clock=clock,
        sleep=sleep,
    )
    return E4ThreeSetupProductionApplication(
        node=node,
        capture=capture,
        bootstrap=bootstrap,
        dispatcher=OutboxDispatcher(outbox=bootstrap.outbox, adapter=notification_adapter),
        clock=clock,
        sleep=sleep,
        notification_poll_seconds=config.notification_poll_seconds,
    )
