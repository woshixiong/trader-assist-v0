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
from typing import Any

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from .data import DataRouteError, MultiAssetDataAuthority
from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import MarketLifecycle, RegistryMarket, RegistryVersion
from .registry import MarketRegistryManager, RegistryError

WS_URL = "wss://api.hyperliquid.xyz/ws"
_MAX_RECONNECTS = 3
_WARMUP_5M_BARS = 2_304
_FIVE_MINUTES_MS = 300_000
_CONFIRM_HOLD_MS = 3_000
_CONFIRM_OBSERVATION_GAP_MS = 1_000
_ACK_TIMEOUT_SECONDS = 8.0
_MAX_CONFIRMATIONS = 4


@dataclass
class RuntimeHealth:
    connection_count: int = 0
    subscriptions: int = 0
    reconnects: int = 0
    acknowledgements: set[str] = field(default_factory=set)
    failed_markets: set[str] = field(default_factory=set)
    data_ready: bool = False


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
        self.acknowledgement_timeout_seconds = acknowledgement_timeout_seconds
        self.health = RuntimeHealth()
        self._confirmation_slots = asyncio.Semaphore(confirmation_concurrency)
        self._confirmation_tasks: dict[str, asyncio.Task[None]] = {}
        self._generation: dict[str, int] = {}
        self._candidate_open: dict[str, int] = {}
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
                results[market.identity.market_id] = self.warmup(
                    market, start_ms=start, end_ms=end
                )
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
            await self._warmup_all(recovery=True)
            await self._maybe_stage_lifecycle(snapshot_ready=False)
            for attempt in range(_MAX_RECONNECTS + 1):
                if shutdown.is_set():
                    return
                websocket: Any | None = None
                try:
                    websocket = await self.websocket_factory(WS_URL)
                    self.health.connection_count = 1
                    if attempt:
                        await self._warmup_all(recovery=True)
                    await self._subscribe(websocket)
                    await self._await_acknowledgements(websocket, shutdown)
                    await self._maybe_stage_lifecycle(snapshot_ready=True)
                    self.health.data_ready = True
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
                    if attempt == _MAX_RECONNECTS:
                        return
                    self.health.reconnects += 1
                    await self.sleep(min(2**attempt, 4))
                finally:
                    if websocket is not None:
                        await self._close_socket(websocket)
        finally:
            await self._cancel_confirmation_tasks()

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
            (
                item
                for item in self.selected_markets()
                if item.identity.coin == payload.get("s")
            ),
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
            self._schedule_confirmation(market, open_ms, fingerprint)
        except DataRouteError:
            self.health.failed_markets.add(market.identity.market_id)

    def _schedule_confirmation(
        self, market: RegistryMarket, open_ms: int, fingerprint: str) -> None:
        market_id = market.identity.market_id
        prior_open = self._candidate_open.get(market_id)
        prior = self._confirmation_tasks.get(market_id)
        if prior_open == open_ms and prior is not None and not prior.done():
            # Same generation can be repeated by provider; it is idempotent.
            return
        if prior is not None and not prior.done():
            prior.cancel()
        if prior_open is not None and prior_open != open_ms:
            self.authority.discard_ws_candidate(market_id=market_id, open_time_ms=prior_open)
        generation = self._generation.get(market_id, 0) + 1
        self._generation[market_id] = generation
        self._candidate_open[market_id] = open_ms
        task = asyncio.create_task(self._confirm_later(market, open_ms, fingerprint, generation))
        self._confirmation_tasks[market_id] = task

    async def _confirm_later(
        self, market: RegistryMarket, open_ms: int, fingerprint: str, generation: int) -> None:
        market_id = market.identity.market_id
        try:
            eligible_ms = open_ms + _FIVE_MINUTES_MS + _CONFIRM_HOLD_MS
            delay = max(0, (eligible_ms - int(self.clock().timestamp() * 1000)) / 1000)
            if delay:
                await self.sleep(delay)
            async with self._confirmation_slots:
                if self._generation.get(market_id) != generation:
                    return
                first_at = self.monotonic()
                snapshot = await asyncio.to_thread(
                    self.client.closed_candles,
                    coin=market.identity.coin,
                    interval="5m",
                    start_ms=open_ms,
                    end_ms=open_ms + _FIVE_MINUTES_MS,
                )
                await self.sleep(_CONFIRM_OBSERVATION_GAP_MS / 1000)
                second_at = self.monotonic()
                stable_snapshot = await asyncio.to_thread(
                    self.client.closed_candles,
                    coin=market.identity.coin,
                    interval="5m",
                    start_ms=open_ms,
                    end_ms=open_ms + _FIVE_MINUTES_MS,
                )
                if self._generation.get(market_id) != generation:
                    return
                if not isinstance(snapshot, list) or not isinstance(stable_snapshot, list):
                    raise DataRouteError("candleSnapshot did not return a list")
                self.authority.confirm_ws_candidate(
                    market=market,
                    open_time_ms=open_ms,
                    candidate_fingerprint=fingerprint,
                    snapshot=snapshot,
                    stable_snapshot=stable_snapshot,
                    received_at=self.clock(),
                    hold_ms=_CONFIRM_HOLD_MS,
                    first_observed_monotonic=first_at,
                    second_observed_monotonic=second_at,
                    observation_gap_ms=_CONFIRM_OBSERVATION_GAP_MS,
                )
                await self._maybe_stage_lifecycle(snapshot_ready=self.health.data_ready)
        except asyncio.CancelledError:
            raise
        except (DataRouteError, PublicDataError):
            self.health.failed_markets.add(market_id)
        finally:
            if self._generation.get(market_id) == generation:
                self._confirmation_tasks.pop(market_id, None)

    async def _cancel_confirmation_tasks(self) -> None:
        tasks = tuple(self._confirmation_tasks.values())
        self._confirmation_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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
