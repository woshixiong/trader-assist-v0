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

from trader_assist_v0.contracts.common import canonical_json_bytes

from .bootstrap import BoundaryReport, MultiAssetProductionBootstrap
from .data import ClosedBarStore, MultiAssetDataAuthority
from .hyperliquid_public import HyperliquidPublicClient, OfficialMetadataValidator
from .models import ClosedBar
from .notification_engine import OutboxDispatcher, WebhookDeliveryAdapter
from .planning import CostModel
from .registry import MarketRegistryManager
from .runtime import BoundaryMode

THREE_SETUP_CONFIG_SCHEMA = "trader-assist-v0/three-setup-production-config/v1"
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
    if set(value) != expected or value.get("schema") != THREE_SETUP_CONFIG_SCHEMA:
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
    bootstrap.runtime.acknowledgement_timeout_seconds = config.acknowledgement_timeout_seconds
    return ThreeSetupProductionApplication(
        bootstrap=bootstrap,
        dispatcher=OutboxDispatcher(outbox=bootstrap.outbox, adapter=notification_adapter),
        clock=clock,
        sleep=sleep,
        notification_poll_seconds=config.notification_poll_seconds,
    )
