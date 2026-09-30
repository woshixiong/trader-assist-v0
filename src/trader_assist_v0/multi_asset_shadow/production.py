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
from trader_assist_v0.nautilus_e4.contracts import (
    POST_TERMINAL_MICRO_NS,
    PRE_DECISION_RETENTION_NS,
    PitUniverseSnapshot,
    RunManifest,
)
from trader_assist_v0.nautilus_e4.storage import EvidenceStore as E4EvidenceStore

from .bootstrap import BoundaryReport, MultiAssetProductionBootstrap
from .e4_markettruth import E4MarketTruthProjection
from .integration import (
    M1_BINDING_CONTRACT,
    capture_binding_activation,
    eligible_core_binding_formals,
    verify_binding_activation,
)
from .models import ClosedBar, MarketLifecycle
from .notification_engine import OutboxDispatcher, WebhookDeliveryAdapter
from .planning import CostModel
from .registry import MarketRegistryManager
from .runtime import BoundaryMode, E4ThreeSetupRuntime
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
class _SelectedE4ChildFailure:
    component: str
    error: BaseException
    error_type: str


def _select_e4_child_failure(
    children: tuple[tuple[str, asyncio.Task[None]], ...],
    done: set[asyncio.Task[None]],
    shutdown: asyncio.Event,
) -> _SelectedE4ChildFailure | None:
    """Inspect every completed child before applying stable component precedence."""
    observed: list[tuple[str, str, BaseException | None]] = []
    for component, task in children:
        if task not in done:
            continue
        if task.cancelled():
            observed.append((component, "cancelled", None))
            continue
        error = task.exception()
        observed.append((component, "exception" if error is not None else "normal", error))

    for component, outcome, error in observed:
        if outcome == "exception" and error is not None:
            return _SelectedE4ChildFailure(component, error, type(error).__name__)
    if observed and not shutdown.is_set():
        component, outcome, _ = observed[0]
        description = "was cancelled" if outcome == "cancelled" else "returned normally"
        error = ThreeSetupProductionError(
            f"PRODUCTION_CHILD_EXIT_UNEXPECTED: {component} {description}"
        )
        return _SelectedE4ChildFailure(component, error, type(error).__name__)
    return None


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
    evidence_root = config.e4_evidence_root
    manifest_path = config.e4_manifest_path
    snapshot_path = config.e4_snapshot_path
    assert evidence_root is not None and manifest_path is not None and snapshot_path is not None
    if not evidence_root.is_dir():
        raise ThreeSetupProductionError("E4 evidence root is missing")
    manifest = RunManifest.model_validate_json(manifest_path.read_bytes())
    snapshot = PitUniverseSnapshot.model_validate_json(snapshot_path.read_bytes())
    if manifest.git_sha != config.release_sha or manifest.nautilus_version != "2.0.0rc5":
        raise ThreeSetupProductionError("E4 release or Nautilus identity differs")
    store = E4EvidenceStore(evidence_root)
    if store.load_manifest() != manifest or store.load_snapshot() != snapshot:
        raise ThreeSetupProductionError("E4 identity differs from shared durable evidence")
    registry = MarketRegistryManager(config.registry_root, metadata_validator=lambda _: False)
    selected = registry.active() or registry.pending_version()
    if selected is None:
        raise ThreeSetupProductionError("validated Registry authority is required")
    try:
        from nautilus_trader.model import (  # type: ignore[import-not-found]
            AggregationSource,
            BarAggregation,
            BarType,
            PriceType,
        )
    except ModuleNotFoundError:
        # The optional rc5 package is absent in ordinary dev tests. Deployment
        # preflight separately requires the installed exact rc5 distribution.
        def has_exact_bar(instrument: str, minute: int) -> bool:
            return f"{instrument}-{minute}-MINUTE-LAST-EXTERNAL" in config.e4_bar_types
    else:
        try:
            bars = tuple(BarType.from_str(item) for item in config.e4_bar_types)
        except ValueError as exc:
            raise ThreeSetupProductionError("E4 bar type is invalid") from exc

        def has_exact_bar(instrument: str, minute: int) -> bool:
            return any(
                str(bar.instrument_id) == instrument
                and bar.spec.step == minute
                and bar.spec.aggregation is BarAggregation.MINUTE
                and bar.spec.price_type is PriceType.LAST
                and bar.aggregation_source is AggregationSource.EXTERNAL
                for bar in bars
            )

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
            if not has_exact_bar(expression.instrument_id, minute):
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
                await self._on_dispatch_tick()
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

    async def _on_dispatch_tick(self) -> None:
        """Composition-specific maintenance before the existing outbox poll."""

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
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ThreeSetupProductionApplication:
    """Bind the public Three Setup production entrypoint to E4 market truth."""
    return _compose_e4_three_setup_application(
        config=config,
        notification_adapter=notification_adapter,
        clock=clock,
        sleep=sleep,
    )


class E4ThreeSetupProductionApplication(ThreeSetupProductionApplication):
    """One Nautilus node and one bounded Three Setup consumer/dispatcher."""

    def __init__(
        self,
        *,
        node: Any,
        capture: Any,
        snapshot: PitUniverseSnapshot,
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
        self._binding_enabled = hasattr(capture, "activate_binding")
        self.snapshot = snapshot
        self.e4_runtime = cast(E4ThreeSetupRuntime, self.bootstrap.runtime)
        self.projection = cast(E4MarketTruthProjection, self.bootstrap.data_authority)
        self.e4_runtime.on_domain_error = self._on_domain_error
        self.capture.set_admitted_event_observer(self.e4_runtime.offer_admission)
        self.bootstrap.on_formalized = self._on_formalized

    def _binding_identity(self) -> tuple[str, str]:
        session = self.capture.capture_session
        return session.manifest.run_id, session.manifest.manifest_hash

    def _initialize_binding(self) -> None:
        run_id, manifest_hash = self._binding_identity()
        release_sha = self.bootstrap.coordinator._release_sha
        activation = self.capture.binding_activation
        if activation is None:
            if self.capture.bound_packages() or self.capture.bound_opening_intents():
                raise ThreeSetupProductionError("E4 structural state lacks activation fence")
            activation = capture_binding_activation(
                self.bootstrap.evidence, release_sha=release_sha,
                run_id=run_id, manifest_hash=manifest_hash,
            )
            self.capture.activate_binding(activation)
        verify_binding_activation(
            self.bootstrap.evidence, activation, release_sha=release_sha,
            run_id=run_id, manifest_hash=manifest_hash,
        )
        self._reconcile_binding()

    def _on_formalized(self, _artifacts: object) -> None:
        # The domain bundle is already durable. Exact retained readback is the
        # authority for both first delivery and replay.
        self._reconcile_binding()

    def _reconcile_binding(self) -> None:
        try:
            self._reconcile_binding_checked()
        except Exception:
            # A contradictory domain authority must stop rich retention even if
            # the node is still unwinding after this failure.
            for package_id in self.capture.bound_packages():
                self.capture.block_bound_package(
                    package_id=package_id, reason="BINDING_AUTHORITY_FAILED"
                )
            raise

    def _reconcile_binding_checked(self) -> None:
        activation = self.capture.binding_activation
        if activation is None:
            raise ThreeSetupProductionError("E4 binding activation is absent")
        run_id, manifest_hash = self._binding_identity()
        fence = verify_binding_activation(
            self.bootstrap.evidence, activation,
            release_sha=self.bootstrap.coordinator._release_sha,
            run_id=run_id, manifest_hash=manifest_hash,
        )
        formals = eligible_core_binding_formals(
            self.bootstrap.evidence, fence=fence,
            release_sha=self.bootstrap.coordinator._release_sha,
        )
        selected = self.bootstrap.registry.active() or self.bootstrap.registry.pending_version()
        if selected is None:
            raise ThreeSetupProductionError("E4 binding lacks Registry authority")
        markets = {item.identity.market_id: item for item in selected.markets}
        expressions = {
            item.market_id: item for item in self.snapshot.expressions
        }
        existing = self.capture.bound_packages()
        intents = self.capture.bound_opening_intents()
        eligible_packages = {
            f"m1:shadow:{formal.shadow.record_id}" for formal in formals
        }
        if not (set(existing) | set(intents)) <= eligible_packages:
            raise ThreeSetupProductionError("E4 binding has lost its Formal domain authority")
        observed_ns = self.capture.observed_ns()
        for formal in formals:
            shadow = formal.shadow
            market_id = str(shadow.payload["market_id"])
            if market_id not in markets or market_id not in expressions:
                raise ThreeSetupProductionError("eligible Formal market lacks E4 expression")
            package_id = f"m1:shadow:{shadow.record_id}"
            horizon_ns = formal.horizon_ms * 1_000_000
            if horizon_ns <= 0 or horizon_ns >= 2**63:
                raise ThreeSetupProductionError("eligible Formal horizon is outside E4 ns range")
            prior = existing.get(package_id)
            intent = intents.get(package_id)
            if prior is None and intent is None and observed_ns >= horizon_ns:
                raise ThreeSetupProductionError("eligible Formal missed its E4 opening window")
            created_ts = (
                prior["binding"]["created_ts"] if prior is not None
                else intent["created_ts"] if intent is not None
                else None
            )
            opening: dict[str, Any] = dict(
                package_id=package_id,
                opportunity_id=f"m1:event:{formal.market_event.record_id}",
                thesis_id=f"m1:signal:{formal.signal.record_id}",
                market_id=market_id,
                expression_id=expressions[market_id].expression_id,
                horizon_ns=horizon_ns,
                release_sha=self.bootstrap.coordinator._release_sha,
                contract_id=M1_BINDING_CONTRACT,
            )
            if created_ts is not None:
                opening["created_ts"] = created_ts
            self.capture.open_bound_structural_package(**opening)
            if observed_ns >= horizon_ns:
                self.capture.close_bound_window(
                    package_id=package_id, terminal_ts=horizon_ns,
                    complete=formal.complete_outcome,
                    reason=("OUTCOME_MATURE" if formal.complete_outcome else "OUTCOME_INCOMPLETE"),
                )
        self.capture.advance_bound_windows()

    def read_core_binding_research(self) -> tuple[dict[str, object], ...]:
        """Read validated domain/E4 linkage from existing durable authorities."""
        activation = self.capture.binding_activation
        assert activation is not None
        run_id, manifest_hash = self._binding_identity()
        fence = verify_binding_activation(
            self.bootstrap.evidence, activation,
            release_sha=self.bootstrap.coordinator._release_sha,
            run_id=run_id, manifest_hash=manifest_hash,
        )
        formals = eligible_core_binding_formals(
            self.bootstrap.evidence, fence=fence,
            release_sha=self.bootstrap.coordinator._release_sha,
        )
        session = self.capture.capture_session
        if session.evidence_store is None:
            raise ThreeSetupProductionError("E4 research readback lacks durable evidence")
        admissions = session.evidence_store.load_admissions()
        lifecycle = session.evidence_store.load_lifecycle()
        packages = self.capture.bound_packages()
        checkpoint = session.evidence_store.load_runtime_checkpoint(session.manifest)
        if checkpoint is None or checkpoint.state.get("binding_activation") != activation:
            raise ThreeSetupProductionError("E4 binding checkpoint readback conflicts")
        result: list[dict[str, object]] = []
        for formal in formals:
            package_id = f"m1:shadow:{formal.shadow.record_id}"
            package = packages.get(package_id)
            if package is None:
                raise ThreeSetupProductionError("eligible Formal lacks E4 package readback")
            binding = package["binding"]
            durable_package = checkpoint.state.get("packages", {}).get(package_id)
            if not isinstance(durable_package, dict) or durable_package.get("binding") != binding:
                raise ThreeSetupProductionError("E4 package checkpoint readback conflicts")
            opportunity_id = f"m1:event:{formal.market_event.record_id}"
            thesis_id = f"m1:signal:{formal.signal.record_id}"
            facts = tuple(
                item for item in lifecycle
                if item.package_id == package_id
            )
            opportunities = tuple(item for item in facts if item.object_id == opportunity_id)
            theses = tuple(item for item in facts if item.object_id == thesis_id)
            if (
                len(opportunities) != 1
                or not theses
                or len(facts) != len(opportunities) + len(theses)
                or opportunities[0].state_ts != binding["created_ts"]
                or theses[0].state_ts != binding["created_ts"]
                or opportunities[0].kind.value != "OPPORTUNITY"
                or theses[0].kind.value != "THESIS"
                or binding["horizon_ns"] != formal.horizon_ms * 1_000_000
            ):
                raise ThreeSetupProductionError("E4 lifecycle or horizon readback conflicts")
            market_id = formal.signal.payload["market_id"]
            raw = tuple(
                item for item in admissions
                if item.source.market_id == market_id
                and item.source.data_kind.value in {"BBO", "TRADE"}
                and binding["created_ts"] - PRE_DECISION_RETENTION_NS
                <= item.admission_ts <= binding["horizon_ns"] + POST_TERMINAL_MICRO_NS
            )
            outcomes = self.bootstrap.evidence._query_records(
                "binding.research.outcome",
                """SELECT record_id, record_type, canonical_hash, identity_json, payload_json
                   FROM immutable_records WHERE record_type='outcome_envelope'
                   AND json_extract(payload_json, '$.shadow_order_id')=?""",
                (formal.shadow.record_id,),
            )
            plan = self.bootstrap.evidence.get(str(formal.shadow.payload["plan_id"]))
            provenance = self.bootstrap.evidence.get(str(formal.signal.payload["provenance_id"]))
            if plan is None or provenance is None:
                raise ThreeSetupProductionError("Formal plan or provenance readback is absent")
            result.append({
                "market_event": formal.market_event.canonical_row(),
                "formal_signal": formal.signal.canonical_row(),
                "shadow_order": formal.shadow.canonical_row(),
                "plan_record": plan.canonical_row(),
                "provenance": provenance.canonical_row(),
                "outcomes": [item.canonical_row() for item in outcomes],
                "package_id": package_id,
                "binding": binding,
                "tail": package["tail"],
                "predecision_state": package["predecision_state"],
                "lifecycle": [item.model_dump(mode="json") for item in facts],
                "admissions": [item.model_dump(mode="json") for item in raw],
                "evidence_state": package["tail"]["evidence_state"],
                "missingness": (
                    "ADMISSIONS_ABSENT" if not raw
                    else "INCOMPLETE" if package["tail"]["evidence_state"] != "COMPLETE"
                    else None
                ),
                "coefficient_level_after_cost_reconstruction": "NOT_PROVEN",
            })
        return tuple(result)

    def export_core_binding_research_jsonl(self) -> bytes:
        return b"".join(
            canonical_json_bytes(item) + b"\n"
            for item in self.read_core_binding_research()
        )

    async def _on_dispatch_tick(self) -> None:
        if self._binding_enabled:
            self._reconcile_binding()

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
        if getattr(self, "_binding_enabled", False):
            self._initialize_binding()
        _journal(
            self.logger,
            "STARTUP",
            registry_version=active.version,
            registry_content_hash=active.content_hash,
        )
        handle = self.node.handle()
        dispatcher_task = asyncio.create_task(self._dispatch_loop(shutdown))
        domain_task = asyncio.create_task(self.e4_runtime.run(shutdown))
        node_task = asyncio.create_task(self.node.run_async())
        children = (("node", node_task), ("domain", domain_task), ("dispatcher", dispatcher_task))
        tasks = tuple(task for _, task in children)
        primary: _SelectedE4ChildFailure | None = None
        interrupted: BaseException | None = None
        cleanup_error: BaseException | None = None
        node_complete = False
        try:
            # A created run task is not a Running node. All three children are
            # supervised during the bounded hosted-loop startup wait.
            while True:
                done = {task for task in tasks if task.done()}
                primary = _select_e4_child_failure(children, done, shutdown)
                if primary is not None or shutdown.is_set():
                    break
                if handle.is_running:
                    break
                done, _ = await asyncio.wait(
                    tasks, timeout=0.01, return_when=asyncio.FIRST_COMPLETED
                )
                primary = _select_e4_child_failure(children, done, shutdown)
                if primary is not None or shutdown.is_set():
                    break
            if primary is None and not shutdown.is_set():
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                primary = _select_e4_child_failure(children, done, shutdown)
            if primary is not None:
                _journal(
                    self.logger,
                    "PRODUCTION_CHILD_EXIT_UNEXPECTED",
                    component=primary.component,
                    error_type=primary.error_type,
                )
        except BaseException as exc:
            interrupted = exc
        finally:
            shutdown.set()
            stop_failed = False
            try:
                handle.stop()
            except BaseException as exc:
                cleanup_error = exc
                stop_failed = True
            for task in (dispatcher_task, domain_task):
                if not task.done():
                    task.cancel()
            try:
                results = await asyncio.gather(dispatcher_task, domain_task, return_exceptions=True)
                for result in results:
                    if isinstance(result, BaseException) and not isinstance(
                        result, asyncio.CancelledError
                    ) and cleanup_error is None:
                        cleanup_error = result
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            try:
                if stop_failed and not node_task.done():
                    # A failed stop must not leave cleanup blocked forever or
                    # permit disposal of a still-running node.
                    await asyncio.wait({node_task}, timeout=1.0)
                else:
                    await asyncio.gather(node_task, return_exceptions=True)
                node_complete = node_task.done()
                if node_complete and not node_task.cancelled():
                    node_error = node_task.exception()
                    if node_error is not None and cleanup_error is None:
                        cleanup_error = node_error
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            try:
                await self._close_dispatcher()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            try:
                self.bootstrap.close()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            try:
                self.projection.close()
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            if node_complete:
                try:
                    self.node.dispose()
                except BaseException as exc:
                    if cleanup_error is None:
                        cleanup_error = exc
            elif cleanup_error is None:
                cleanup_error = ThreeSetupProductionError("LiveNode run completion was not proven")
            try:
                _journal(self.logger, "SHUTDOWN")
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
        if primary is not None:
            raise primary.error
        if interrupted is not None:
            raise interrupted
        if cleanup_error is not None:
            raise cleanup_error


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
        snapshot=snapshot,
        bootstrap=bootstrap,
        dispatcher=OutboxDispatcher(outbox=bootstrap.outbox, adapter=notification_adapter),
        clock=clock,
        sleep=sleep,
        notification_poll_seconds=config.notification_poll_seconds,
    )
