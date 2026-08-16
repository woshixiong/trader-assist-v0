"""Bounded, public-only selected-market Hyperliquid 5m runtime.

WebSocket traffic only nominates a finality candidate.  Targeted synchronous
``urllib`` calls are deliberately bridged through a bounded thread pool so the
receive loop remains responsive while the finality authority waits for its
provider-close hold and real observation gap.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, cast

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
            mark_failed=self.health.failed_markets.add,
            now_ms=lambda: int(self.clock().timestamp() * 1000),
            sleep=self.sleep,
            confirmation_concurrency=confirmation_concurrency,
        )
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
        latest_open = self._latest_completed_open()
        failed = {
            market.identity.market_id
            for market in active.markets
            if market.identity.market_id in self.health.failed_markets
            or self.authority.market_failed(market.identity.market_id)
        }
        ready = tuple(
            market.identity.market_id
            for market in active.markets
            if self.health.data_ready
            and market.lifecycle is MarketLifecycle.ACTIVE
            and market.identity.market_id not in failed
            and self._history_current(market)
        )
        return RuntimeReadinessSnapshot.create(
            registry_version=active.version,
            registry_content_hash=active.content_hash,
            data_ready=self.health.data_ready,
            ready_market_ids=ready,
            failed_market_ids=tuple(failed),
            latest_closed_5m_open_time_ms=latest_open,
            observed_at_ms=int(self.clock().timestamp() * 1000),
        )

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

    def _history_current(self, market: RegistryMarket) -> bool:
        return (
            not self.authority.market_failed(market.identity.market_id)
            and self.authority.store.last_open(market.identity.market_id)
            == self._latest_completed_open()
        )

    async def _warmup_market(self, market: RegistryMarket, *, recovery: bool) -> int:
        start, end = self._window()
        last = self.authority.store.last_open(market.identity.market_id)
        if recovery and last is not None:
            start = last + _FIVE_MINUTES_MS
        if start >= end:
            if self._history_current(market):
                return 0
            raise DataRouteError("persisted closed-bar state is stale")
        try:
            # urllib is synchronous; only transport runs in a worker.  SQLite
            # evidence admission remains serialized on the event-loop thread.
            snapshot = await asyncio.to_thread(
                self.client.closed_candles,
                coin=market.identity.coin,
                interval="5m",
                start_ms=start,
                end_ms=end,
            )
            if not isinstance(snapshot, list):
                raise PublicDataError("candleSnapshot did not return a list")
            count = len(
                self.authority.admit_rest_history(
                    market=market, snapshot=snapshot, received_at=self.clock()
                )
            )
            if not self._history_current(market):
                raise DataRouteError("warmup did not prove current contiguous 5m history")
        except (DataRouteError, PublicDataError):
            self.health.failed_markets.add(market.identity.market_id)
            raise
        self.health.failed_markets.discard(market.identity.market_id)
        return count

    async def _warmup_all(self, *, recovery: bool) -> dict[str, int]:
        results: dict[str, int] = {}
        for market in self.selected_markets():
            try:
                results[market.identity.market_id] = await self._warmup_market(
                    market, recovery=recovery
                )
            except (DataRouteError, PublicDataError):
                continue
        return results

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
            await self._warmup_all(recovery=True)
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
                        await self._warmup_all(recovery=True)
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
        except DataRouteError:
            self.health.failed_markets.add(market.identity.market_id)

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
            await self._maybe_stage_lifecycle(snapshot_ready=self.health.data_ready)
            if admitted is not None:
                await self._notify_finalized(admitted, BoundaryMode.LIVE_ACTIONABLE)
            return ConfirmationResult.COMPLETE
        except asyncio.CancelledError:
            raise
        except (DataRouteError, PublicDataError):
            if not self._finality.is_latest(generation):
                return ConfirmationResult.STALE
            return ConfirmationResult.FAILED

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
            self.health.failed_markets.add(bar.market_id)
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
        updates: dict[str, MarketLifecycle] = {}
        for market in active.markets:
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
        suffix = "-".join(sorted(value.value.lower() for value in set(updates.values())))
        version = f"{active.version}-lifecycle-{suffix}"
        try:
            candidate = self.registry.lifecycle_successor(
                version=version, updates=updates, now=self.clock()
            )
            self.registry.request_apply(candidate.version)
        except RegistryError:
            # A filesystem/control-plane conflict must not become a different
            # data authority.  Leave markets below ACTIVE for operator review.
            self.health.failed_markets.update(updates)
