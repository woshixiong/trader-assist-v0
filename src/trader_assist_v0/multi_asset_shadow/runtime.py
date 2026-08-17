"""Bounded, public-only selected-market Hyperliquid 5m runtime.

WebSocket traffic only nominates a finality candidate.  Targeted synchronous
``urllib`` calls are deliberately bridged through a bounded thread pool so the
receive loop remains responsive while the finality authority waits for its
provider-close hold and real observation gap.

Cold-start warmup is a bounded cohort process: one captured target boundary
per round, chunked history admission with cooperative event-loop yields, and
an all-market barrier before any WebSocket path may become actionable.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Final, cast

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .data import DataRouteError, MultiAssetDataAuthority
from .finality import (
    FIVE_MINUTES_MS,
    MIN_MONOTONIC_CONFIRMATION_GAP_MS,
    POST_CLOSE_HOLD_MS,
    TARGET_CONFIRMATIONS,
    CandidateGeneration,
    ConfirmationResult,
    FinalityIdentity,
    GenerationFinalityAuthority,
)
from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import ClosedBar, MarketLifecycle, RegistryMarket, RegistryVersion
from .registry import MarketRegistryManager, RegistryError

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
# Mirrors RegistryVersion.version max_length; the lifecycle name chain below
# must never hand schema validation a name it must reject.
_REGISTRY_VERSION_NAME_MAX: Final = 80


def _lifecycle_version_name(predecessor: str, predecessor_hash: str, suffix: str) -> str:
    """Bounded, deterministic, unique lifecycle successor version name.

    The naive chain (predecessor + "-lifecycle-" + suffix) exceeds the
    RegistryVersion 80-character schema bound after a few transitions and
    converts healthy progression into a RegistryError, which the caller then
    records as cohort failure.  Keep the readable chain while it fits; once it
    would overflow, compress the inherited prefix to its stable head plus a
    predecessor-hash tag so lineage stays provable, the name stays unique, and
    the length stays bounded forever.
    """
    tail = f"-lifecycle-{suffix}"
    if len(predecessor) + len(tail) <= _REGISTRY_VERSION_NAME_MAX:
        return f"{predecessor}{tail}"
    tag = f"~{predecessor_hash[:8]}{tail}"
    head = _REGISTRY_VERSION_NAME_MAX - len(tag)
    return f"{predecessor[:head]}{tag}"


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
    # Non-durable, bounded operator diagnostics: the latest failure record per
    # market (one entry per market id; a nonrecoverable classification is
    # never weakened by a later recoverable incident).  Never a durable
    # authority, queue, or platform of its own.
    failure_records: dict[str, MarketFailureRecord] = field(default_factory=dict)
    callback_failures: list[FinalizedCallbackFailure] = field(default_factory=list)
    data_ready: bool = False


@dataclass(frozen=True)
class MarketFailureRecord:
    """Bounded operator-visible record of why one market is failed right now."""

    market_id: str
    coin: str
    open_time_ms: int
    stage: str
    category: str
    recoverable: bool


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


class MultiAssetPublicRuntime:
    """One connection, bounded finality tasks, per-market failure isolation."""

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
        self._finality = GenerationFinalityAuthority(
            confirm=self._confirm_generation,
            discard=self._discard_candidate,
            mark_failed=self._mark_finality_failed,
            now_ms=lambda: int(self.clock().timestamp() * 1000),
            sleep=self.sleep,
            confirmation_concurrency=confirmation_concurrency,
        )
        self._expected_acks: set[str] = set()

    def _mark_finality_failed(self, market_id: str) -> None:
        """Finality authority failure hook: preserve the classified record.

        _confirm_generation already recorded a classified record for the
        failures it understands.  A market reaching this hook without a record
        is an unknown authority failure with no proven recovery path, and must
        fail closed as nonrecoverable instead of silently becoming recoverable.
        """
        if market_id in self.health.failure_records:
            self.health.failed_markets.add(market_id)
            return
        self._record_failure_by_id(
            market_id,
            open_time_ms=0,
            stage="finality_unknown",
            category="unknown finality authority failure: no classified record",
            recoverable=False,
        )

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

        The hard freshness ceiling is now enforced inside
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
        except (DataRouteError, PublicDataError) as exc:
            self._record_market_failure(
                market,
                open_time_ms=target_open_ms,
                stage="warmup",
                category=exc,
            )
            raise
        self._clear_if_proven_recoverable(market.identity.market_id)
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
                    self._clear_if_proven_recoverable(market.identity.market_id)
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
        return recovered

    async def run(self, shutdown: asyncio.Event) -> None:
        """Startup recovery, acknowledgement readiness, then bounded reconnect."""
        try:
            startup_mode = (
                BoundaryMode.RECOVERY_CONTEXT_ONLY
                if any(
                    self.authority.store.last_open(market.identity.market_id) is not None
                    for market in self.selected_markets()
                )
                else BoundaryMode.COLD_START_CONTEXT_ONLY
            )
            if not await self._startup_warmup_barrier(shutdown):
                # A partial or mixed-time cohort must never become actionable:
                # fail closed before any WebSocket, subscription, or live flow.
                return
            await self._maybe_stage_lifecycle(snapshot_ready=False)
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
                    await self._maybe_stage_lifecycle(snapshot_ready=True)
                    self.health.data_ready = True
                    await self._wake_recovered_application(
                        startup_mode if not reconnecting else BoundaryMode.RECOVERY_CONTEXT_ONLY
                    )
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
                    await self._finality.invalidate_all()
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
            await self._finality.close()

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
            fingerprint = self.authority.offer_ws_candidate(
                market=market, payload=payload, received_at=self.clock()
            )
            open_ms = payload.get("t")
            if not isinstance(open_ms, int):
                raise DataRouteError("websocket candle is missing open timestamp")
            self._finality.offer(market=market, open_time_ms=open_ms, fingerprint=fingerprint)
        except DataRouteError as exc:
            self._record_market_failure(
                market,
                open_time_ms=payload.get("t") if isinstance(payload.get("t"), int) else 0,
                stage="ws_candidate",
                category=exc,
                recoverable=False,
            )

    def _discard_candidate(self, identity: FinalityIdentity) -> None:
        self.authority.discard_ws_candidate(
            market_id=identity.market_id, open_time_ms=identity.open_time_ms
        )

    async def _confirm_generation(self, generation: CandidateGeneration) -> ConfirmationResult:
        identity = generation.identity
        try:
            snapshots: list[list[object]] = []
            observed_at: list[float] = []
            for index in range(TARGET_CONFIRMATIONS):
                if index:
                    await self.sleep(MIN_MONOTONIC_CONFIRMATION_GAP_MS / 1_000)
                if not self._finality.is_latest(generation):
                    return ConfirmationResult.STALE
                snapshot = await asyncio.to_thread(
                    self.client.closed_candles,
                    coin=generation.market.identity.coin,
                    interval="5m",
                    start_ms=identity.open_time_ms,
                    end_ms=identity.open_time_ms + _FIVE_MINUTES_MS,
                )
                observed_at.append(self.monotonic())
                if not self._finality.is_latest(generation):
                    return ConfirmationResult.STALE
                if not isinstance(snapshot, list):
                    raise DataRouteError("candleSnapshot did not return a list")
                snapshots.append(snapshot)
            # Give already-queued WebSocket revisions one event-loop turn to
            # advance the generation before the synchronous admission section.
            await asyncio.sleep(0)
            if not self._finality.is_latest(generation):
                return ConfirmationResult.STALE
            await self._backfill_ws_silent_boundaries(generation)
            admitted = self.authority.confirm_ws_candidate(
                market=generation.market,
                open_time_ms=identity.open_time_ms,
                candidate_fingerprint=generation.fingerprint,
                snapshot=snapshots[0],
                stable_snapshot=snapshots[1],
                received_at=self.clock(),
                hold_ms=POST_CLOSE_HOLD_MS,
                first_observed_monotonic=observed_at[0],
                second_observed_monotonic=observed_at[1],
                observation_gap_ms=MIN_MONOTONIC_CONFIRMATION_GAP_MS,
            )
            self._recover_runtime_finality_failure(generation.market)
            await self._maybe_stage_lifecycle(snapshot_ready=self.health.data_ready)
            if admitted is not None:
                await self._notify_finalized(admitted, BoundaryMode.LIVE_ACTIONABLE)
            return ConfirmationResult.COMPLETE
        except asyncio.CancelledError:
            raise
        except (DataRouteError, PublicDataError) as exc:
            if not self._finality.is_latest(generation):
                return ConfirmationResult.STALE
            self._record_market_failure(
                generation.market,
                open_time_ms=identity.open_time_ms,
                stage="finality_confirmation",
                category=exc,
            )
            return ConfirmationResult.FAILED
        except Exception as exc:
            # An unexpected exception is an unknown authority failure with no
            # proven recovery path; it must not hide behind a stale
            # recoverable record, and it must not escape the finality task.
            # GenerationFinalityAuthority keeps its own defensive
            # fail-closed catch; this records the exact generation first.
            if not self._finality.is_latest(generation):
                return ConfirmationResult.STALE
            self._record_market_failure(
                generation.market,
                open_time_ms=identity.open_time_ms,
                stage="finality_unknown",
                category=exc,
                recoverable=False,
            )
            return ConfirmationResult.FAILED

    async def _backfill_ws_silent_boundaries(self, generation: CandidateGeneration) -> None:
        """Admit provider REST evidence for boundaries WS can never nominate.

        The candle channel is trade-driven: a zero-trade 5m boundary emits no
        candidate at all, while the provider's candleSnapshot series stays
        contiguous (zero-volume flat bars, probe-verified 2026-08-17).  Those
        boundaries are admitted from the provider's own series before the live
        candidate's confirmation, so a legitimate provider no-trade bar never
        surfaces as a false Data gap.  A genuine provider omission still fails
        closed inside the unchanged continuity authority.
        """
        market_id = generation.identity.market_id
        prior_open = self.authority.store.last_open(market_id)
        if prior_open is None or generation.identity.open_time_ms <= prior_open + _FIVE_MINUTES_MS:
            return
        start_ms = prior_open + _FIVE_MINUTES_MS
        end_ms = generation.identity.open_time_ms
        if end_ms - start_ms > _WARMUP_5M_BARS * _FIVE_MINUTES_MS:
            raise DataRouteError("ws-silent boundary backfill exceeds bounded history")
        snapshot = await asyncio.to_thread(
            self.client.closed_candles,
            coin=generation.market.identity.coin,
            interval="5m",
            start_ms=start_ms,
            end_ms=end_ms,
        )
        if not isinstance(snapshot, list):
            raise DataRouteError("candleSnapshot did not return a list")
        # candleSnapshot is end-inclusive (probe-verified 2026-08-17): the
        # response can echo the live boundary whose open == end_ms, including a
        # still-forming or disagreeing value.  Only a strict historical prefix
        # may enter through this REST history observation; the live candidate
        # itself stays exclusively governed by confirm_ws_candidate's two
        # targeted stable observations.  Evidence past the candidate is
        # unexpected and fails closed.
        target_open = generation.identity.open_time_ms
        prefix: list[dict[str, object]] = []
        for item in snapshot:
            if not isinstance(item, Mapping) or not isinstance(item.get("t"), int):
                raise DataRouteError("backfill snapshot contains a malformed bar")
            open_ms = item["t"]
            if open_ms > target_open:
                raise DataRouteError("backfill snapshot contains unexpected future evidence")
            if open_ms < target_open:
                prefix.append(dict(item))
        if not prefix:
            return
        self.authority.admit_rest_history(
            market=generation.market, snapshot=prefix, received_at=self.clock()
        )

    def _recover_runtime_finality_failure(self, market: RegistryMarket) -> None:
        """Market-scoped, evidence-derived recovery of a runtime finality failure.

        A later successful provider-authoritative finality may clear ONLY a
        failure that carries an explicit recoverable record, and only while the
        Data authority holds no failure for it and its durable 5m series is
        exactly contiguous.  A market with no record, an application/callback
        failure, a Registry lifecycle failure, an unknown authority failure, a
        Data gap, or any conflict is never cleared here: no record means no
        proven recovery path, so it fails closed.
        """
        market_id = market.identity.market_id
        if market_id not in self.health.failed_markets:
            return
        record = self.health.failure_records.get(market_id)
        if record is None or not record.recoverable:
            return
        if self.authority.market_failed(market_id):
            return
        if not self.authority.store.is_contiguous_5m(market_id):
            return
        self.health.failed_markets.discard(market_id)
        self.health.failure_records.pop(market_id, None)

    def _clear_if_proven_recoverable(self, market_id: str) -> None:
        """Warmup/reconnect success may clear only a proven recoverable record.

        A healthy warmup is market-data evidence only; it can never repair an
        application callback failure, a Registry lifecycle failure, or any
        failure without an explicit recoverable record.
        """
        record = self.health.failure_records.get(market_id)
        if record is None or not record.recoverable:
            return
        if self.authority.market_failed(market_id):
            return
        if not self.authority.store.is_contiguous_5m(market_id):
            return
        self.health.failed_markets.discard(market_id)
        self.health.failure_records.pop(market_id, None)

    def _merge_failure_record(self, record: MarketFailureRecord) -> None:
        """Nonrecoverable failure authority dominates monotonically.

        An application callback failure, a Registry control-plane failure, a
        malformed WS candidate, or an unknown authority failure can never be
        weakened to recoverable by later market-data/warmup/finality
        incidents; only an explicit future application/control-plane recovery
        mechanism (out of scope here) could clear it.  A later nonrecoverable
        failure may refresh the diagnostic while remaining nonrecoverable.
        """
        self.health.failed_markets.add(record.market_id)
        existing = self.health.failure_records.get(record.market_id)
        if existing is not None and not existing.recoverable and record.recoverable:
            return
        self.health.failure_records[record.market_id] = record

    def _record_market_failure(
        self,
        market: RegistryMarket,
        *,
        open_time_ms: int,
        stage: str,
        category: object,
        recoverable: bool | None = None,
    ) -> None:
        market_id = market.identity.market_id
        self._merge_failure_record(
            MarketFailureRecord(
                market_id=market_id,
                coin=market.identity.coin,
                open_time_ms=open_time_ms,
                stage=stage,
                category=f"{type(category).__name__}: {category}"[:160],
                recoverable=(
                    not self.authority.market_failed(market_id)
                    if recoverable is None
                    else recoverable
                ),
            )
        )

    def _record_failure_by_id(
        self,
        market_id: str,
        *,
        open_time_ms: int,
        stage: str,
        category: object,
        recoverable: bool,
    ) -> None:
        """Record a runtime failure without a live generation's market object."""
        coin = market_id
        for market in self.selected_markets():
            if market.identity.market_id == market_id:
                coin = market.identity.coin
                break
        self._merge_failure_record(
            MarketFailureRecord(
                market_id=market_id,
                coin=coin,
                open_time_ms=open_time_ms,
                stage=stage,
                category=f"{type(category).__name__}: {category}"[:160],
                recoverable=recoverable,
            )
        )

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
            # An application callback failure is never repaired by later
            # market-data success: the application itself must be reviewed.
            self._record_failure_by_id(
                bar.market_id,
                open_time_ms=bar.open_time_ms,
                stage="application_callback",
                category=exc,
                recoverable=False,
            )
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

    async def _wake_recovered_application(self, mode: BoundaryMode) -> None:
        """Wake once; retained history lets the reconciler derive every missing prefix."""
        latest: list[ClosedBar] = []
        for market in self.selected_markets():
            bars = self.authority.store.bars(market.identity.market_id)
            if not bars:
                return
            latest.append(bars[-1])
        if not latest or len({bar.open_time_ms for bar in latest}) != 1:
            return
        await self._notify_finalized(latest[0], mode)

    async def _cancel_confirmation_tasks(self) -> None:
        """Compatibility seam for deterministic runtime shutdown tests."""
        await self._finality.invalidate_all()

    async def _maybe_stage_lifecycle(self, *, snapshot_ready: bool) -> None:
        if self.registry.active() is None or self.registry.pending_version() is not None:
            return
        active = self.registry.active()
        assert active is not None
        cohort = [
            market
            for market in active.markets
            if market.lifecycle
            not in {MarketLifecycle.DISABLED, MarketLifecycle.OUTCOMES_COMPLETE}
        ]
        # First Launch: while the Registry holds zero ACTIVE markets, the
        # launch cohort must progress atomically.  A failed or not-yet-eligible
        # member blocks staging for every member, so a partial healthy subset
        # can never become an actionable ACTIVE cohort before the exact
        # selected cohort is coherently current.  Once an ACTIVE cohort
        # exists, a later WARMING market may progress independently (hot-add)
        # and must not pause the already-live cohort.
        launch_cohort = all(
            market.lifecycle is not MarketLifecycle.ACTIVE for market in cohort
        )
        updates: dict[str, MarketLifecycle] = {}
        for market in cohort:
            if market.identity.market_id in self.health.failed_markets:
                continue
            if market.lifecycle is MarketLifecycle.WARMING and self._history_current(market):
                updates[market.identity.market_id] = MarketLifecycle.HISTORY_READY
            elif market.lifecycle is MarketLifecycle.HISTORY_READY and snapshot_ready:
                updates[market.identity.market_id] = MarketLifecycle.SNAPSHOT_READY
            elif market.lifecycle is MarketLifecycle.SNAPSHOT_READY and snapshot_ready:
                updates[market.identity.market_id] = MarketLifecycle.ACTIVE
        if not updates:
            return
        if launch_cohort and len(updates) != len(cohort):
            return
        suffix = "-".join(sorted(value.value.lower() for value in set(updates.values())))
        version = _lifecycle_version_name(active.version, active.content_hash, suffix)
        try:
            candidate = self.registry.lifecycle_successor(
                version=version, updates=updates, now=self.clock()
            )
            self.registry.request_apply(candidate.version)
        except (RegistryError, ValueError) as exc:
            # A filesystem/control-plane conflict or schema rejection (pydantic
            # ValidationError is a ValueError) must not become a different data
            # authority, and must not escape into the confirming market's
            # finality task.  Registry lifecycle failures are operator-review
            # failures: later market-data success must never auto-recover them.
            for market_id in updates:
                self._record_failure_by_id(
                    market_id,
                    open_time_ms=self.authority.store.last_open(market_id) or 0,
                    stage="lifecycle_staging",
                    category=exc,
                    recoverable=False,
                )
