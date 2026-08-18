"""Bounded, public-only selected-market Hyperliquid 5m runtime.

SINGLE_OWNER_5M_COHORT_BARRIER: one clock-driven barrier owns whole-cohort
actionability, retained-epoch classification, current-process failure state,
the only global Scanner/Strategy application wake, lifecycle progression, and
safe-boundary Registry switching.  WebSocket traffic, subscription
acknowledgement, reconnect, warmup completion, and individual market
callbacks only update observations, candidates, and readiness.

Targeted synchronous ``urllib`` calls are bridged through a bounded thread
pool so the receive loop stays responsive while provider proof and durable
admission remain serialized on the event-loop thread.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, cast

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .cohort_finality import (
    Closed5mCohortFinality,
    FinalityMarketRequest,
    FinalityOutcome,
)
from .data import ClosedBarStore, DataRouteError, MultiAssetDataAuthority
from .finality import FIVE_MINUTES_MS
from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import ClosedBar, MarketLifecycle, RegistryMarket, RegistryVersion
from .registry import CohortWitness, MarketRegistryManager, RegistryError

WS_URL = "wss://api.hyperliquid.xyz/ws"
_MAX_RECONNECTS = 3
_WARMUP_5M_BARS = 2_304
_FIVE_MINUTES_MS = FIVE_MINUTES_MS
_ACK_TIMEOUT_SECONDS = 8.0
_MAX_CONFIRMATIONS = 4
_MAX_CALLBACK_FAILURES = 100

# First-Launch cold-start tuning values.  They bound runtime-local behavior
# only and are deliberately explicit rather than scattered literals.
WARMUP_ADMISSION_CHUNK_BARS: Final = 64
WARMUP_CATCHUP_ROUNDS_MAX: Final = 3
FRESHNESS_TARGET_SECONDS: Final = 30.0
FRESHNESS_ACTION_CEILING_SECONDS: Final = 60.0
# Operational pacing only (packet section 23): after a heavy cold warmup, the
# first live full-cohort REST burst waits at least this long.  Not durable
# authority and not market truth; skipping the earliest boundary is acceptable.
STARTUP_REST_COOLDOWN_SECONDS: Final = 60.0
# One real hard action deadline per boundary: T close + 60 seconds (section 8).
BOUNDARY_ACTION_DEADLINE_SECONDS: Final = 60.0
# Clock-driven barrier tick: how often the completed-boundary edge is checked.
_BARRIER_TICK_SECONDS: Final = 5.0
_BARRIER_ISSUER: Final = "SINGLE_OWNER_5M_COHORT_BARRIER"
_PRE_ACTIVE_ORDER: Final[dict[MarketLifecycle, int]] = {
    MarketLifecycle.WARMING: 0,
    MarketLifecycle.HISTORY_READY: 1,
    MarketLifecycle.SNAPSHOT_READY: 2,
}


class BoundaryMode(StrEnum):
    """Provider-independent semantics for one finalized 5m application boundary."""

    LIVE_ACTIONABLE = "LIVE_ACTIONABLE"
    RECOVERY_CONTEXT_ONLY = "RECOVERY_CONTEXT_ONLY"
    COLD_START_CONTEXT_ONLY = "COLD_START_CONTEXT_ONLY"


@dataclass
class RuntimeHealth:
    connection_count: int = 0
    subscriptions: int = 0
    reconnects: int = 0
    acknowledgements: set[str] = field(default_factory=set)
    failed_markets: set[str] = field(default_factory=set)
    nonrecoverable_markets: set[str] = field(default_factory=set)
    callback_failures: list[FinalizedCallbackFailure] = field(default_factory=list)
    data_ready: bool = False


@dataclass(frozen=True)
class FinalizedCallbackFailure:
    market_id: str
    open_time_ms: int
    evaluation_mode: BoundaryMode
    error_type: str
    reason: str


@dataclass(frozen=True)
class RuntimeReadinessSnapshot:
    """Immutable A1 authority presented to every new-activity integration gate."""

    registry_version: str
    registry_content_hash: str
    data_ready: bool
    ready_market_ids: tuple[str, ...]
    failed_market_ids: tuple[str, ...]
    latest_closed_5m_open_time_ms: int
    observed_at_ms: int
    snapshot_hash: str

    @classmethod
    def create(
        cls,
        *,
        registry_version: str,
        registry_content_hash: str,
        data_ready: bool,
        ready_market_ids: tuple[str, ...],
        failed_market_ids: tuple[str, ...],
        latest_closed_5m_open_time_ms: int,
        observed_at_ms: int,
    ) -> RuntimeReadinessSnapshot:
        ready = tuple(sorted(ready_market_ids))
        failed = tuple(sorted(failed_market_ids))
        payload = {
            "registry_version": registry_version,
            "registry_content_hash": registry_content_hash,
            "data_ready": data_ready,
            "ready_market_ids": ready,
            "failed_market_ids": failed,
            "latest_closed_5m_open_time_ms": latest_closed_5m_open_time_ms,
            "observed_at_ms": observed_at_ms,
        }
        return cls(
            registry_version=registry_version,
            registry_content_hash=registry_content_hash,
            data_ready=data_ready,
            ready_market_ids=ready,
            failed_market_ids=failed,
            latest_closed_5m_open_time_ms=latest_closed_5m_open_time_ms,
            observed_at_ms=observed_at_ms,
            snapshot_hash=sha256_hex(canonical_json_bytes(payload)),
        )

    def __post_init__(self) -> None:
        if tuple(sorted(set(self.ready_market_ids))) != self.ready_market_ids:
            raise ValueError("ready market identities must be unique and ordered")
        if tuple(sorted(set(self.failed_market_ids))) != self.failed_market_ids:
            raise ValueError("failed market identities must be unique and ordered")
        if set(self.ready_market_ids) & set(self.failed_market_ids):
            raise ValueError("a market cannot be both ready and failed")
        if not self.data_ready and self.ready_market_ids:
            raise ValueError("disconnected runtime cannot expose ready markets")
        payload = {
            "registry_version": self.registry_version,
            "registry_content_hash": self.registry_content_hash,
            "data_ready": self.data_ready,
            "ready_market_ids": self.ready_market_ids,
            "failed_market_ids": self.failed_market_ids,
            "latest_closed_5m_open_time_ms": self.latest_closed_5m_open_time_ms,
            "observed_at_ms": self.observed_at_ms,
        }
        if self.snapshot_hash != sha256_hex(canonical_json_bytes(payload)):
            raise ValueError("runtime readiness snapshot hash is invalid")


class ReconnectRequired(RuntimeError):
    """An expected transport/readiness incident, not an authority failure."""


@dataclass(frozen=True)
class _WarmupCohort:
    """Runtime-local ephemeral control state for exactly one warmup round.

    A cohort binds one captured closed-5m target to the selected acquisition
    Registry identity.  It is deliberately not durable authority: no table,
    file, or queue is created, and every market in the round is judged against
    the captured target rather than a recomputed wall-clock target.
    """

    registry_version: str
    registry_content_hash: str
    market_ids: tuple[str, ...]
    target_open_ms: int

    @property
    def identity(self) -> tuple[str, str, tuple[str, ...]]:
        return (self.registry_version, self.registry_content_hash, self.market_ids)


class RetainedBoundaryClass(StrEnum):
    """The five frozen retained exact-T semantic states (Barrier-owned)."""

    CURRENT_EPOCH_FINALIZED = "CURRENT_EPOCH_FINALIZED"
    PREDECESSOR_CONTEXT_ONLY = "PREDECESSOR_CONTEXT_ONLY"
    MISSING_LIVE_ELIGIBLE = "MISSING_LIVE_ELIGIBLE"
    MISSING_NEEDS_RECOVERY = "MISSING_NEEDS_RECOVERY"
    INVALID_BINDING = "INVALID_BINDING"


def classify_retained_boundary(
    *,
    store: ClosedBarStore,
    registry: MarketRegistryManager,
    market_id: str,
    boundary_open_ms: int,
    captured_version: str,
    captured_hash: str,
) -> RetainedBoundaryClass:
    """Classify durable exact-T state against the exact captured Registry epoch.

    The five retained states are semantically distinct (packet sections 6A/11
    and ruling 2).  A valid exact-T row never becomes invalid merely because
    later boundaries are also durable: stale/backward T handling belongs to
    Barrier freshness logic, which must never produce retrospective action.
    A predecessor binding counts only for an actually superseded active epoch;
    a staged-never-active candidate is not a predecessor.
    """
    row = store.connection.execute(
        "SELECT registry_version, registry_content_hash FROM closed_bars "
        "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
        (market_id, boundary_open_ms),
    ).fetchone()
    last_open = store.last_open(market_id)
    if row is None:
        if last_open is not None and last_open > boundary_open_ms:
            # Durable rows beyond T without an exact-T row are a continuity
            # hole that cannot exist under the legal single-owner ordering.
            return RetainedBoundaryClass.INVALID_BINDING
        if last_open is None or last_open < boundary_open_ms - _FIVE_MINUTES_MS:
            return RetainedBoundaryClass.MISSING_NEEDS_RECOVERY
        return RetainedBoundaryClass.MISSING_LIVE_ELIGIBLE
    version = str(row[0])
    content_hash = str(row[1])
    if version == captured_version:
        if content_hash != captured_hash:
            return RetainedBoundaryClass.INVALID_BINDING
        return RetainedBoundaryClass.CURRENT_EPOCH_FINALIZED
    try:
        historical = registry.prior_active(version)
    except RegistryError:
        return RetainedBoundaryClass.INVALID_BINDING
    if historical is None or historical.content_hash != content_hash:
        return RetainedBoundaryClass.INVALID_BINDING
    return RetainedBoundaryClass.PREDECESSOR_CONTEXT_ONLY


class MultiAssetPublicRuntime:
    """One connection, one clock-driven cohort barrier, bounded provider proof."""

    def __init__(
        self,
        *,
        registry: MarketRegistryManager,
        authority: MultiAssetDataAuthority,
        client: HyperliquidPublicClient,
        websocket_factory: Callable[[str], Awaitable[Any]] = connect,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        on_finalized_5m: (
            Callable[[ClosedBar, BoundaryMode], Awaitable[object] | object | None] | None
        ) = None,
        on_reconnect: Callable[[int], object | None] | None = None,
        confirmation_concurrency: int = _MAX_CONFIRMATIONS,
        acknowledgement_timeout_seconds: float = _ACK_TIMEOUT_SECONDS,
    ) -> None:
        if confirmation_concurrency < 1 or acknowledgement_timeout_seconds <= 0:
            raise ValueError("runtime bounds must be positive")
        self.registry = registry
        self.authority = authority
        self.client = client
        self.websocket_factory = websocket_factory
        self.clock = clock
        self.monotonic = monotonic
        self.sleep = sleep
        self.on_finalized_5m = on_finalized_5m
        self.on_reconnect = on_reconnect
        self.acknowledgement_timeout_seconds = acknowledgement_timeout_seconds
        self.health = RuntimeHealth()
        # Evidence-derived maintenance lane invoked by the barrier whether or
        # not the boundary produced new action (packet section 20).
        self.on_maintenance_5m: (
            Callable[[int], Awaitable[None] | object | None] | None
        ) = None
        # Replaceable provider-proof seam: no processed-boundary state, no
        # failure state, no lifecycle or Registry authority of its own.
        self._cohort_finality = Closed5mCohortFinality(
            client=client,
            clock=clock,
            monotonic=monotonic,
            sleep=sleep,
            confirmation_concurrency=confirmation_concurrency,
        )
        self._barrier_lock = asyncio.Lock()
        self._last_barrier_boundary: int | None = None
        self._rest_cooldown_until: float | None = None
        self._integrity_failed = False
        self._expected_acks: set[str] = set()

    def acquisition_registry(self) -> RegistryVersion:
        """Active markets plus the strictly bounded initial bootstrap exception."""
        active = self.registry.active()
        if active is not None:
            pending = self.registry.pending_version()
            if pending is None:
                return active
            # A pending add is allowed only to warm its new WARMING identity;
            # it cannot replace an active market's authority before activation.
            active_ids = {market.identity.market_id for market in active.markets}
            extra = tuple(
                market
                for market in pending.markets
                if market.identity.market_id not in active_ids
                and market.lifecycle is MarketLifecycle.WARMING
            )
            return active.model_copy(update={"markets": active.markets + extra})
        pending = self.registry.pending_version()
        if pending is None:
            raise DataRouteError("validated active or initial pending Registry is required")
        return pending

    def selected_markets(self) -> tuple[RegistryMarket, ...]:
        return tuple(
            market
            for market in self.acquisition_registry().markets
            if market.lifecycle not in {MarketLifecycle.DISABLED, MarketLifecycle.OUTCOMES_COMPLETE}
        )

    def readiness_snapshot(self) -> RuntimeReadinessSnapshot:
        """Return current A1 transport, Registry, failure, and finality authority."""
        active = self.registry.active()
        if active is None:
            raise DataRouteError("active Registry is required for runtime readiness")
        # One captured observation: the latest completed 5m boundary and the
        # freshness ceiling are both derived from this single timestamp so an
        # adversarial clock cannot split readiness across internal calls.
        observed_at_ms = int(self.clock().timestamp() * 1000)
        latest_open = self._latest_completed_open_at(observed_at_ms)
        failed = {
            market.identity.market_id
            for market in active.markets
            if market.identity.market_id in self.health.failed_markets
            or market.identity.market_id in self.health.nonrecoverable_markets
            or self.authority.market_failed(market.identity.market_id)
        }
        # Hard new-activity gate on the production path: a boundary observed
        # older than the actionability ceiling is not exposed in
        # ready_market_ids at all, not merely in the convenience method.
        within_action_ceiling = observed_at_ms - (
            latest_open + _FIVE_MINUTES_MS
        ) <= int(FRESHNESS_ACTION_CEILING_SECONDS * 1000)
        ready = tuple(
            market.identity.market_id
            for market in active.markets
            if self.health.data_ready
            and market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id not in failed
            and within_action_ceiling
            and self._history_current_at(market, latest_open)
        )
        return RuntimeReadinessSnapshot.create(
            registry_version=active.version,
            registry_content_hash=active.content_hash,
            data_ready=self.health.data_ready,
            ready_market_ids=ready,
            failed_market_ids=tuple(failed),
            latest_closed_5m_open_time_ms=latest_open,
            observed_at_ms=observed_at_ms,
        )

    def freshness_lag_seconds(self, snapshot: RuntimeReadinessSnapshot) -> float:
        """Age of the latest authoritative closed-5m boundary when observed."""
        close_ms = snapshot.latest_closed_5m_open_time_ms + _FIVE_MINUTES_MS
        return (snapshot.observed_at_ms - close_ms) / 1_000

    def freshness_within_target(self, snapshot: RuntimeReadinessSnapshot) -> bool:
        """Operational First-Launch freshness target metric (not a hard gate)."""
        return self.freshness_lag_seconds(snapshot) <= FRESHNESS_TARGET_SECONDS

    def actionable_ready_market_ids(self) -> tuple[str, ...]:
        """New-activity gate: ready markets inside the hard freshness ceiling.

        The hard freshness ceiling is enforced inside
        :meth:`readiness_snapshot` itself, so production paths consuming
        ``ready_market_ids`` directly are fail-closed.  This convenience method
        is retained for explicit new-activity callers.
        """
        return self.readiness_snapshot().ready_market_ids

    def subscriptions(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": market.identity.coin, "interval": "5m"},
            }
            for market in self.selected_markets()
        )

    def begin_cold_start_rest_cooldown(self) -> None:
        """Operational pacing only: pause the first live full-cohort REST burst."""
        self._rest_cooldown_until = self.monotonic() + STARTUP_REST_COOLDOWN_SECONDS

    async def process_cohort_boundary(self, boundary_open_ms: int) -> None:
        """The single global authority for one completed 5m boundary.

        Serialized by one process-local lock (concurrency control only, never
        durable processed-boundary authority).  Restarts re-derive everything
        from durable evidence, so duplicate or stale wakes converge without a
        second authority.
        """
        if (
            not isinstance(boundary_open_ms, int)
            or boundary_open_ms < 0
            or boundary_open_ms % _FIVE_MINUTES_MS != 0
        ):
            raise DataRouteError("cohort boundary must be an aligned closed 5m open")
        async with self._barrier_lock:
            if (
                self._rest_cooldown_until is not None
                and self.monotonic() < self._rest_cooldown_until
            ):
                return
            if (
                self._last_barrier_boundary is not None
                and boundary_open_ms <= self._last_barrier_boundary
            ):
                return
            active = self.registry.active()
            if active is None:
                # No active Registry yet: the initial-bootstrap exception is
                # owned by the Data authority's first validated admission.
                self._last_barrier_boundary = boundary_open_ms
                return
            self._last_barrier_boundary = boundary_open_ms
            try:
                await self._reconcile_boundary(boundary_open_ms, active)
            except RegistryError:
                # Registry/lifecycle control-plane contradiction is a
                # nonrecoverable current-process class (packet section 21).
                self._integrity_failed = True
                raise

    async def _reconcile_boundary(
        self, boundary_open_ms: int, active: RegistryVersion
    ) -> None:
        """CAPTURE R -> classify -> lanes -> action under R -> maintenance -> switch."""
        captured_version = active.version
        captured_hash = active.content_hash
        # Explicit single-owner crash convergence first: a pending pointer left
        # stale by crash-after-pointer-switch/before-pending-cleanup is
        # recognized as already applied and cleaned idempotently here, never
        # inside an ordinary Registry read accessor.
        pending_at_start = self.registry.reconcile_pending()
        selected = self.selected_markets()
        observed_ms = int(self.clock().timestamp() * 1000)
        deadline_ms = boundary_open_ms + _FIVE_MINUTES_MS + int(
            BOUNDARY_ACTION_DEADLINE_SECONDS * 1000
        )
        within_deadline = observed_ms <= deadline_ms

        classes: dict[str, RetainedBoundaryClass] = {}
        for market in selected:
            classes[market.identity.market_id] = classify_retained_boundary(
                store=self.authority.store,
                registry=self.registry,
                market_id=market.identity.market_id,
                boundary_open_ms=boundary_open_ms,
                captured_version=captured_version,
                captured_hash=captured_hash,
            )
        self.health.nonrecoverable_markets |= {
            market_id
            for market_id, state in classes.items()
            if state is RetainedBoundaryClass.INVALID_BINDING
        }

        active_selected = [
            market for market in selected if market.lifecycle is MarketLifecycle.ACTIVE
        ]
        first_launch = not active_selected and any(
            market.lifecycle in _PRE_ACTIVE_ORDER for market in selected
        )
        epoch_states = {
            classes[market.identity.market_id] for market in active_selected
        } & {
            RetainedBoundaryClass.CURRENT_EPOCH_FINALIZED,
            RetainedBoundaryClass.PREDECESSOR_CONTEXT_ONLY,
        }
        if len(epoch_states) > 1:
            # A mixed-epoch ACTIVE cohort cannot exist under the legal
            # single-owner ordering: integrity failure, not a repair condition.
            self._integrity_failed = True
            self.health.nonrecoverable_markets |= {
                market.identity.market_id for market in active_selected
            }

        finalized_now: set[str] = set()
        if within_deadline and not self._integrity_failed:
            await self._run_recovery_context_lane(
                boundary_open_ms, selected, classes, first_launch
            )
            finalized_now = await self._run_live_finality_lane(
                boundary_open_ms, selected, classes, first_launch, deadline_ms
            )

        if self._whole_cohort_actionable(active_selected, classes, finalized_now, deadline_ms):
            bars = self.authority.store.tail_bars(
                active_selected[0].identity.market_id,
                at_or_before_ms=boundary_open_ms,
                limit=1,
            )
            if bars:
                # The one and only global application wake, entirely under R.
                await self._notify_finalized(bars[-1], BoundaryMode.LIVE_ACTIONABLE)

        await self._run_maintenance(boundary_open_ms)

        await self._reconcile_successor(
            boundary_open_ms,
            active,
            pending_at_start,
            selected,
            active_selected,
            within_deadline,
        )

    async def _run_recovery_context_lane(
        self,
        boundary_open_ms: int,
        selected: tuple[RegistryMarket, ...],
        classes: dict[str, RetainedBoundaryClass],
        first_launch: bool,
    ) -> None:
        """Recovery/context lane: authoritative catch-up that never acts on T.

        A market that entered T behind T-1 recovers history as context only.
        Even when recovery reaches T during this reconciliation, no new
        Scanner/Strategy/Formal authority is created for T; live action may
        resume only at a later fresh boundary.
        """
        for market in selected:
            state = classes[market.identity.market_id]
            needs_recovery = state is RetainedBoundaryClass.MISSING_NEEDS_RECOVERY or (
                state is RetainedBoundaryClass.MISSING_LIVE_ELIGIBLE
                and not first_launch
                and market.lifecycle in _PRE_ACTIVE_ORDER
            )
            if not needs_recovery:
                continue
            try:
                await self._warmup_market(
                    market, recovery=True, target_open_ms=boundary_open_ms
                )
            except asyncio.CancelledError:
                raise
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
            except Exception:
                self.health.nonrecoverable_markets.add(market.identity.market_id)

    async def _run_live_finality_lane(
        self,
        boundary_open_ms: int,
        selected: tuple[RegistryMarket, ...],
        classes: dict[str, RetainedBoundaryClass],
        first_launch: bool,
        deadline_ms: int,
    ) -> set[str]:
        """Live finality lane: only MISSING_LIVE_ELIGIBLE action-cohort markets."""
        targets = [
            market
            for market in selected
            if classes[market.identity.market_id] is RetainedBoundaryClass.MISSING_LIVE_ELIGIBLE
            and (first_launch or market.lifecycle is MarketLifecycle.ACTIVE)
        ]
        if not targets:
            return set()
        remaining_ms = deadline_ms - int(self.clock().timestamp() * 1000)
        if remaining_ms <= 0:
            return set()
        results = await self._cohort_finality.prove_cohort(
            requests=tuple(
                FinalityMarketRequest(market=market, boundary_open_ms=boundary_open_ms)
                for market in targets
            ),
            deadline_monotonic=self.monotonic() + remaining_ms / 1_000,
        )
        finalized: set[str] = set()
        for market, result in zip(targets, results, strict=True):
            market_id = market.identity.market_id
            if (
                result.outcome is FinalityOutcome.FINALIZED
                and result.confirmed_payload is not None
            ):
                try:
                    # Durable validation/admission happens on the event-loop
                    # thread; the worker only carried raw provider transport.
                    self.authority.admit_rest_history(
                        market=market,
                        snapshot=[result.confirmed_payload],
                        received_at=self.clock(),
                    )
                    if self._durable_boundary_row(market_id, boundary_open_ms):
                        finalized.add(market_id)
                    else:
                        # Strict admission discarded the payload (for example a
                        # close time still ahead of the wall clock): the
                        # provider proof did not become durable evidence.
                        self.health.failed_markets.add(market_id)
                except (DataRouteError, PublicDataError):
                    self.health.failed_markets.add(market_id)
            elif result.outcome is FinalityOutcome.NONRECOVERABLE_FAILURE:
                self.health.nonrecoverable_markets.add(market_id)
            else:
                self.health.failed_markets.add(market_id)
        return finalized

    def _durable_boundary_row(self, market_id: str, boundary_open_ms: int) -> bool:
        """Confirm one exact-T durable row exists under the captured epoch."""
        row = self.authority.store.connection.execute(
            "SELECT 1 FROM closed_bars "
            "WHERE market_id=? AND interval='5m' AND open_time_ms=?",
            (market_id, boundary_open_ms),
        ).fetchone()
        return row is not None

    def _whole_cohort_actionable(
        self,
        active_selected: list[RegistryMarket],
        classes: dict[str, RetainedBoundaryClass],
        finalized_now: set[str],
        deadline_ms: int,
    ) -> bool:
        """Whole-cohort actionability decision owned by the barrier alone."""
        if self._integrity_failed or not self.health.data_ready or not active_selected:
            return False
        for market in active_selected:
            market_id = market.identity.market_id
            if (
                market_id in self.health.failed_markets
                or market_id in self.health.nonrecoverable_markets
                or self.authority.market_failed(market_id)
            ):
                return False
            if market_id in finalized_now:
                continue
            if classes[market_id] is not RetainedBoundaryClass.CURRENT_EPOCH_FINALIZED:
                return False
        # Hard freshness re-check immediately before the only global wake.
        return int(self.clock().timestamp() * 1000) <= deadline_ms

    async def _run_maintenance(self, boundary_open_ms: int) -> None:
        """Action deferral never defers maintenance (packet section 20)."""
        callback = self.on_maintenance_5m
        if callback is None:
            return
        try:
            result = callback(boundary_open_ms)
            if isinstance(result, Awaitable):
                await cast(Awaitable[None], result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.health.callback_failures.append(
                FinalizedCallbackFailure(
                    market_id="",
                    open_time_ms=boundary_open_ms,
                    evaluation_mode=BoundaryMode.RECOVERY_CONTEXT_ONLY,
                    error_type=type(exc).__name__,
                    reason=str(exc),
                )
            )

    async def _reconcile_successor(
        self,
        boundary_open_ms: int,
        active: RegistryVersion,
        pending_at_start: RegistryVersion | None,
        selected: tuple[RegistryMarket, ...],
        active_selected: list[RegistryMarket],
        within_deadline: bool,
    ) -> None:
        """Lifecycle planning and at most one witness-authorized switch at T."""
        if self._integrity_failed or not within_deadline:
            return
        planner_updates = self._plan_lifecycle_updates(
            boundary_open_ms=boundary_open_ms,
            selected=selected,
            active_selected=active_selected,
        )
        try:
            if pending_at_start is not None:
                # Never overwrite an existing pending Registry and never mint a
                # second lifecycle successor in the same boundary.
                transition = self._pending_lifecycle_transition(active, pending_at_start)
                if transition is None:
                    # External/manual membership successor: preserve existing
                    # safe-boundary semantics through the same exact witness.
                    evidence = frozenset(
                        market.identity.market_id for market in active_selected
                    )
                    if evidence and self.authority.prove_boundary_evidence(
                        boundary_open_time_ms=boundary_open_ms,
                        market_ids=evidence,
                        base_registry_version=active.version,
                        base_registry_hash=active.content_hash,
                    ):
                        self._apply_successor_witness(
                            boundary_open_ms=boundary_open_ms,
                            base=active,
                            successor=pending_at_start,
                            evidence_market_ids=evidence,
                        )
                elif planner_updates == transition:
                    self._apply_successor_witness(
                        boundary_open_ms=boundary_open_ms,
                        base=active,
                        successor=pending_at_start,
                        evidence_market_ids=self._successor_evidence_ids(
                            selected, active_selected, transition
                        ),
                    )
                # A lifecycle pending the current planner would not reproduce
                # is a stale/conflicting control-plane proposal: no apply.
                return
            if not planner_updates:
                return
            suffix = "-".join(
                sorted(value.value.lower() for value in set(planner_updates.values()))
            )
            candidate = self.registry.lifecycle_successor(
                version=f"{active.version}-lifecycle-{suffix}",
                updates=planner_updates,
                now=self.clock(),
            )
            self.registry.request_apply(candidate.version)
            self._apply_successor_witness(
                boundary_open_ms=boundary_open_ms,
                base=active,
                successor=candidate,
                evidence_market_ids=self._successor_evidence_ids(
                    selected, active_selected, planner_updates
                ),
            )
        except RegistryError:
            # Control-plane contradiction: fail closed for the involved cohort.
            self.health.nonrecoverable_markets |= set(planner_updates) | {
                market.identity.market_id for market in active_selected
            }

    def _plan_lifecycle_updates(
        self,
        *,
        boundary_open_ms: int,
        selected: tuple[RegistryMarket, ...],
        active_selected: list[RegistryMarket],
    ) -> dict[str, MarketLifecycle]:
        """Pure deterministic lifecycle planner; no durable writes occur here."""
        selected_coins = {market.identity.coin for market in selected}
        snapshot_ready = (
            self.health.data_ready
            and selected_coins <= self.health.acknowledgements
        )

        def blocked(market: RegistryMarket) -> bool:
            market_id = market.identity.market_id
            return (
                market_id in self.health.nonrecoverable_markets
                or market_id in self.health.failed_markets
                or self.authority.market_failed(market_id)
            )

        def current(market: RegistryMarket) -> bool:
            return self._history_current_at(market, boundary_open_ms)

        members = [market for market in selected if market.lifecycle in _PRE_ACTIVE_ORDER]
        if not active_selected:
            # Initial-Launch mode: the cohort advances atomically.  A failed
            # selected member holds progression, only the minimum PRE_ACTIVE
            # stage advances, and markets ahead remain unchanged.
            if not members or any(blocked(market) or not current(market) for market in members):
                return {}
            minimum = min(
                members, key=lambda market: _PRE_ACTIVE_ORDER[market.lifecycle]
            ).lifecycle
            if minimum is MarketLifecycle.WARMING:
                return {
                    market.identity.market_id: MarketLifecycle.HISTORY_READY
                    for market in members
                    if market.lifecycle is MarketLifecycle.WARMING
                }
            if not snapshot_ready:
                return {}
            target = (
                MarketLifecycle.SNAPSHOT_READY
                if minimum is MarketLifecycle.HISTORY_READY
                else MarketLifecycle.ACTIVE
            )
            return {
                market.identity.market_id: target
                for market in members
                if market.lifecycle is minimum
            }
        updates: dict[str, MarketLifecycle] = {}
        for market in members:
            if blocked(market) or not current(market):
                continue
            if market.lifecycle is MarketLifecycle.WARMING:
                updates[market.identity.market_id] = MarketLifecycle.HISTORY_READY
            elif snapshot_ready:
                updates[market.identity.market_id] = (
                    MarketLifecycle.SNAPSHOT_READY
                    if market.lifecycle is MarketLifecycle.HISTORY_READY
                    else MarketLifecycle.ACTIVE
                )
        if updates and any(
            blocked(market) or not current(market) for market in active_selected
        ):
            # A Registry switch at T requires the current ACTIVE cohort to be
            # coherent at T (packet section 14).
            return {}
        return updates

    def _successor_evidence_ids(
        self,
        selected: tuple[RegistryMarket, ...],
        active_selected: list[RegistryMarket],
        updates: dict[str, MarketLifecycle],
    ) -> frozenset[str]:
        if not active_selected:
            # Initial Launch: the complete selected launch cohort, never empty.
            return frozenset(market.identity.market_id for market in selected)
        return frozenset(market.identity.market_id for market in active_selected) | frozenset(
            updates
        )

    def _pending_lifecycle_transition(
        self, active: RegistryVersion, pending: RegistryVersion
    ) -> dict[str, MarketLifecycle] | None:
        """Exact lifecycle-only diff, or None for an external successor."""
        active_by_id = {market.identity.market_id: market for market in active.markets}
        pending_by_id = {market.identity.market_id: market for market in pending.markets}
        if set(active_by_id) != set(pending_by_id):
            return None
        updates: dict[str, MarketLifecycle] = {}
        for market_id, market in pending_by_id.items():
            prior = active_by_id[market_id]
            if market.lifecycle is prior.lifecycle:
                if market != prior:
                    return None
                continue
            if market != prior.model_copy(update={"lifecycle": market.lifecycle}):
                return None
            updates[market_id] = market.lifecycle
        return updates or None

    def _apply_successor_witness(
        self,
        *,
        boundary_open_ms: int,
        base: RegistryVersion,
        successor: RegistryVersion,
        evidence_market_ids: frozenset[str],
    ) -> None:
        """Activate exactly one successor through the one-use cohort witness."""
        witness = CohortWitness.create(
            boundary_open_time_ms=boundary_open_ms,
            base_registry_version=base.version,
            base_registry_hash=base.content_hash,
            expected_successor_version=successor.version,
            expected_successor_hash=successor.content_hash,
            required_evidence_market_ids=evidence_market_ids,
            issuer=_BARRIER_ISSUER,
        )
        self.registry.apply_witness(
            witness, evidence_authority=self.authority
        )

    def _window(self) -> tuple[int, int]:
        end_ms = int(self.clock().timestamp() * 1000)
        end_ms -= end_ms % _FIVE_MINUTES_MS
        return end_ms - _WARMUP_5M_BARS * _FIVE_MINUTES_MS, end_ms

    def warmup(self, market: RegistryMarket, *, start_ms: int, end_ms: int) -> int:
        snapshot = self.client.closed_candles(
            coin=market.identity.coin, interval="5m", start_ms=start_ms, end_ms=end_ms
        )
        if not isinstance(snapshot, list):
            raise PublicDataError("candleSnapshot did not return a list")
        return len(
            self.authority.admit_rest_history(
                market=market, snapshot=snapshot, received_at=self.clock()
            )
        )

    def _latest_completed_open(self) -> int:
        _, end = self._window()
        return end - _FIVE_MINUTES_MS

    def _latest_completed_open_at(self, observed_at_ms: int) -> int:
        """Derive the latest completed 5m boundary from one captured observation."""
        end_boundary = observed_at_ms - (observed_at_ms % _FIVE_MINUTES_MS)
        return end_boundary - _FIVE_MINUTES_MS

    def _capture_cohort(self) -> _WarmupCohort:
        """Bind one warmup round to the acquisition Registry and one target."""
        registry = self.acquisition_registry()
        selected = self.selected_markets()
        return _WarmupCohort(
            registry_version=registry.version,
            registry_content_hash=registry.content_hash,
            market_ids=tuple(sorted(item.identity.market_id for item in selected)),
            target_open_ms=self._latest_completed_open(),
        )

    def _cohort_identity(self) -> tuple[str, str, tuple[str, ...]]:
        """Registry identity only; does NOT derive a new warmup target."""
        registry = self.acquisition_registry()
        selected = self.selected_markets()
        return (
            registry.version,
            registry.content_hash,
            tuple(sorted(item.identity.market_id for item in selected)),
        )

    def _history_current_at(self, market: RegistryMarket, target_open_time_ms: int) -> bool:
        """Prove durable history ended exactly at one captured cohort target."""
        return (
            not self.authority.market_failed(market.identity.market_id)
            and self.authority.store.last_open(market.identity.market_id)
            == target_open_time_ms
        )

    def _history_current(self, market: RegistryMarket) -> bool:
        return self._history_current_at(market, self._latest_completed_open())

    async def _admit_history_chunked(
        self,
        market: RegistryMarket,
        snapshot: list[object],
        *,
        received_at: datetime,
        shutdown: asyncio.Event | None,
    ) -> int:
        """Admit one fetched history in bounded chunks with cooperative yields.

        SQLite admission stays serialized on the event-loop thread; the loop
        is only given a chance to run shutdown/monitoring between chunks.
        """
        # One deterministic global ordering equivalent to the accepted Data
        # authority ordering, applied BEFORE chunking so per-chunk admission is
        # identical to one-shot admission of the whole snapshot.  Malformed
        # provider objects are retained (sort key -1) so Data validation still
        # fails closed on them; they are never silently discarded here.
        ordered = sorted(
            snapshot, key=lambda item: item.get("t", -1) if isinstance(item, dict) else -1
        )
        admitted = 0
        for offset in range(0, len(ordered), WARMUP_ADMISSION_CHUNK_BARS):
            chunk = ordered[offset : offset + WARMUP_ADMISSION_CHUNK_BARS]
            admitted += len(
                self.authority.admit_rest_history(
                    market=market, snapshot=chunk, received_at=received_at
                )
            )
            await self.sleep(0)
            if shutdown is not None and shutdown.is_set():
                break
        return admitted

    async def _warmup_market(
        self,
        market: RegistryMarket,
        *,
        recovery: bool,
        target_open_ms: int,
        shutdown: asyncio.Event | None = None,
    ) -> int:
        end_ms = target_open_ms + _FIVE_MINUTES_MS
        start_ms = end_ms - _WARMUP_5M_BARS * _FIVE_MINUTES_MS
        last = self.authority.store.last_open(market.identity.market_id)
        if recovery and last is not None:
            start_ms = last + _FIVE_MINUTES_MS
        if start_ms >= end_ms:
            if self._history_current_at(market, target_open_ms):
                return 0
            raise DataRouteError("persisted closed-bar state is stale")
        try:
            # urllib is synchronous; only transport runs in a worker.  SQLite
            # evidence admission remains serialized on the event-loop thread,
            # but is split into bounded chunks below.
            snapshot = await asyncio.to_thread(
                self.client.closed_candles,
                coin=market.identity.coin,
                interval="5m",
                start_ms=start_ms,
                end_ms=end_ms,
            )
            if not isinstance(snapshot, list):
                raise PublicDataError("candleSnapshot did not return a list")
            # Canonical identity is bound to one provider observation: a single
            # received_at for the entire fetched snapshot regardless of admission
            # chunking, so ClosedBar.canonical_hash stays equivalent to one-shot.
            history_received_at = self.clock()
            count = await self._admit_history_chunked(
                market, snapshot, received_at=history_received_at, shutdown=shutdown
            )
            if shutdown is not None and shutdown.is_set():
                # A clean operator shutdown exits at a bounded chunk boundary;
                # it is not a provider market failure and must not be marked one.
                return count
            if not self._history_current_at(market, target_open_ms):
                raise DataRouteError("warmup did not prove current contiguous 5m history")
        except (DataRouteError, PublicDataError):
            self.health.failed_markets.add(market.identity.market_id)
            raise
        self.health.failed_markets.discard(market.identity.market_id)
        return count

    async def _warmup_all(
        self,
        *,
        recovery: bool,
        shutdown: asyncio.Event | None = None,
        cohort: _WarmupCohort | None = None,
    ) -> dict[str, int]:
        """One cohort round: every selected market judged against one target."""
        results: dict[str, int] = {}
        if cohort is None:
            cohort = self._capture_cohort()
        for market in self.selected_markets():
            if shutdown is not None and shutdown.is_set():
                break
            try:
                results[market.identity.market_id] = await self._warmup_market(
                    market,
                    recovery=recovery,
                    target_open_ms=cohort.target_open_ms,
                    shutdown=shutdown,
                )
            except (DataRouteError, PublicDataError):
                continue
        return results

    async def _startup_warmup_barrier(self, shutdown: asyncio.Event) -> bool:
        """Fail-closed all-market barrier before any WebSocket path.

        Every selected market must converge onto one common authoritative
        closed-5m boundary, with a small explicit bound on whole-cohort
        catch-up rounds.  A genuine market failure, a Registry identity
        change mid-round, shutdown, or an outrun catch-up bound all fail
        closed rather than opening a mixed-time cohort.
        """
        for _round in range(1 + WARMUP_CATCHUP_ROUNDS_MAX):
            if shutdown.is_set():
                return False
            cohort = self._capture_cohort()
            results = await self._warmup_all(
                recovery=True, shutdown=shutdown, cohort=cohort
            )
            if shutdown.is_set():
                return False
            selected = self.selected_markets()
            if len(results) != len(selected):
                return False
            if not all(
                self._history_current_at(item, cohort.target_open_ms) for item in selected
            ):
                return False
            if self._cohort_identity() != cohort.identity:
                return False
            if self._latest_completed_open() == cohort.target_open_ms:
                return True
        return False

    def warmup_all(self) -> dict[str, int]:
        """Synchronous diagnostic helper; ``run`` invokes its own lifecycle."""
        start, end = self._window()
        results: dict[str, int] = {}
        for market in self.selected_markets():
            try:
                results[market.identity.market_id] = self.warmup(market, start_ms=start, end_ms=end)
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
        return results

    def recover_gaps(self) -> dict[str, int]:
        """Synchronous diagnostic helper; reconnects use ``_warmup_all``."""
        _, end = self._window()
        recovered: dict[str, int] = {}
        for market in self.selected_markets():
            last = self.authority.store.last_open(market.identity.market_id)
            start = end - _WARMUP_5M_BARS * _FIVE_MINUTES_MS
            if last is not None:
                start = last + _FIVE_MINUTES_MS
            if start >= end:
                continue
            try:
                recovered[market.identity.market_id] = self.warmup(
                    market, start_ms=start, end_ms=end
                )
                if self._history_current(market):
                    self.health.failed_markets.discard(market.identity.market_id)
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
        return recovered

    async def run(self, shutdown: asyncio.Event) -> None:
        """Startup recovery, bounded reconnect, and the clock-driven barrier."""
        if not await self._startup_warmup_barrier(shutdown):
            # A partial or mixed-time cohort must never become actionable:
            # fail closed before any WebSocket, subscription, or live flow.
            return
        self.begin_cold_start_rest_cooldown()
        ticker = asyncio.create_task(self._barrier_ticker(shutdown))
        try:
            reconnecting = False
            consecutive_incomplete_recoveries = 0
            while True:
                if shutdown.is_set():
                    return
                websocket: Any | None = None
                recovery_complete = False
                try:
                    websocket = await self.websocket_factory(WS_URL)
                    self.health.connection_count = 1
                    if reconnecting:
                        await self._warmup_all(recovery=True, shutdown=shutdown)
                        if shutdown.is_set():
                            return
                    await self._subscribe(websocket)
                    await self._await_acknowledgements(websocket, shutdown)
                    self.health.data_ready = True
                    recovery_complete = True
                    consecutive_incomplete_recoveries = 0
                    await self._receive_loop(websocket, shutdown)
                    return
                except (
                    ConnectionClosedOK,
                    ConnectionClosedError,
                    OSError,
                    TimeoutError,
                    ReconnectRequired,
                ):
                    self.health.connection_count = 0
                    self.health.data_ready = False
                    if reconnecting and not recovery_complete:
                        consecutive_incomplete_recoveries += 1
                        if consecutive_incomplete_recoveries >= _MAX_RECONNECTS:
                            return
                    self.health.reconnects += 1
                    if self.on_reconnect is not None:
                        try:
                            self.on_reconnect(self.health.reconnects)
                        except Exception:
                            # Observability must not create a second runtime authority.
                            pass
                    await self.sleep(min(2**consecutive_incomplete_recoveries, 4))
                    reconnecting = True
                finally:
                    if websocket is not None:
                        await self._close_socket(websocket)
        finally:
            ticker.cancel()
            await asyncio.gather(ticker, return_exceptions=True)

    async def _barrier_ticker(self, shutdown: asyncio.Event) -> None:
        """Clock-driven edge detection only; the barrier is the authority."""
        while not shutdown.is_set():
            await self.sleep(_BARRIER_TICK_SECONDS)
            if shutdown.is_set():
                return
            try:
                boundary = self._latest_completed_open()
                if (
                    self._last_barrier_boundary is None
                    or boundary > self._last_barrier_boundary
                ):
                    await self.process_cohort_boundary(boundary)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.health.callback_failures.append(
                    FinalizedCallbackFailure(
                        market_id="",
                        open_time_ms=self._last_barrier_boundary or 0,
                        evaluation_mode=BoundaryMode.RECOVERY_CONTEXT_ONLY,
                        error_type=type(exc).__name__,
                        reason=str(exc),
                    )
                )
                if len(self.health.callback_failures) > _MAX_CALLBACK_FAILURES:
                    del self.health.callback_failures[:-_MAX_CALLBACK_FAILURES]

    async def _close_socket(self, websocket: Any) -> None:
        close = getattr(websocket, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def _subscribe(self, websocket: Any) -> None:
        requests = self.subscriptions()
        self._expected_acks = {request["subscription"]["coin"] for request in requests}  # type: ignore[index]
        self.health.acknowledgements.clear()
        for request in requests:
            await websocket.send(json.dumps(request, separators=(",", ":")))
        self.health.subscriptions = len(requests)

    async def _await_acknowledgements(self, websocket: Any, shutdown: asyncio.Event) -> None:
        deadline = self.monotonic() + self.acknowledgement_timeout_seconds
        while not self._expected_acks.issubset(self.health.acknowledgements):
            if shutdown.is_set():
                return
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise ReconnectRequired("subscription acknowledgement timeout")
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=remaining)
            except TimeoutError as exc:
                raise ReconnectRequired("subscription acknowledgement timeout") from exc
            await self.handle_message(raw)

    async def _receive_loop(self, websocket: Any, shutdown: asyncio.Event) -> None:
        recv = asyncio.create_task(websocket.recv())
        stopped = asyncio.create_task(shutdown.wait())
        try:
            while True:
                done, _ = await asyncio.wait({recv, stopped}, return_when=asyncio.FIRST_COMPLETED)
                if stopped in done:
                    return
                raw = recv.result()
                await self.handle_message(raw)
                recv = asyncio.create_task(websocket.recv())
        finally:
            for task in (recv, stopped):
                task.cancel()
            await asyncio.gather(recv, stopped, return_exceptions=True)

    def _acknowledge(self, message: dict[str, object]) -> None:
        data = message.get("data")
        if not isinstance(data, dict) or data.get("method") != "subscribe":
            raise ReconnectRequired("subscription acknowledgement is invalid")
        subscription = data.get("subscription")
        if not isinstance(subscription, dict):
            raise ReconnectRequired("subscription acknowledgement is invalid")
        if (
            subscription.get("type") != "candle"
            or subscription.get("interval") != "5m"
            or not isinstance(subscription.get("coin"), str)
        ):
            raise ReconnectRequired("subscription acknowledgement is invalid")
        coin = subscription["coin"]
        if coin not in self._expected_acks:
            raise ReconnectRequired("subscription acknowledgement is unknown")
        self.health.acknowledgements.add(coin)

    async def handle_message(self, raw: str) -> None:
        """Observations and candidates only: no staging, no wake, no Registry."""
        try:
            message = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DataRouteError("websocket message is invalid") from exc
        if not isinstance(message, dict):
            raise DataRouteError("websocket message is invalid")
        if message.get("channel") == "subscriptionResponse":
            self._acknowledge(message)
            return
        if message.get("channel") != "candle" or not isinstance(message.get("data"), dict):
            return
        payload = message["data"]
        market = next(
            (item for item in self.selected_markets() if item.identity.coin == payload.get("s")),
            None,
        )
        if market is None:
            return
        try:
            self.authority.offer_ws_candidate(
                market=market, payload=payload, received_at=self.clock()
            )
            open_ms = payload.get("t")
            last_open = self.authority.store.last_open(market.identity.market_id)
            if isinstance(open_ms, int) and last_open is not None and open_ms <= last_open:
                # A candidate for an already provider-finalized boundary is
                # worthless observation state; drop it so retention stays
                # bounded to the open boundary.
                self.authority.discard_ws_candidate(
                    market_id=market.identity.market_id, open_time_ms=open_ms
                )
        except DataRouteError:
            self.health.failed_markets.add(market.identity.market_id)

    async def _notify_finalized(self, bar: ClosedBar, mode: BoundaryMode) -> object | None:
        callback = self.on_finalized_5m
        if callback is None:
            return None
        try:
            result = callback(bar, mode)
            if isinstance(result, Awaitable):
                return await cast(Awaitable[object], result)
            return result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Application callback authority failure is nonrecoverable within
            # this process (packet section 21).
            self.health.nonrecoverable_markets.add(bar.market_id)
            self.health.callback_failures.append(
                FinalizedCallbackFailure(
                    market_id=bar.market_id,
                    open_time_ms=bar.open_time_ms,
                    evaluation_mode=mode,
                    error_type=type(exc).__name__,
                    reason=str(exc),
                )
            )
            if len(self.health.callback_failures) > _MAX_CALLBACK_FAILURES:
                del self.health.callback_failures[:-_MAX_CALLBACK_FAILURES]
            return None
