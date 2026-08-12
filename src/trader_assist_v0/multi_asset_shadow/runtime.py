"""Minimal selected-market, public-only Hyperliquid 5m runtime.

It keeps one websocket for all selected Registry markets, confirms every WS
candle through the bounded REST finality path, and intentionally has no user,
account, signing, or exchange-write capability.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from websockets.asyncio.client import connect

from .data import DataRouteError, MultiAssetDataAuthority
from .hyperliquid_public import HyperliquidPublicClient, PublicDataError
from .models import RegistryMarket
from .registry import MarketRegistryManager

WS_URL = "wss://api.hyperliquid.xyz/ws"
_MAX_RECONNECTS = 3
_WARMUP_5M_BARS = 2_304  # 8 days: 96x15m Zone plus 1h ATR/context margin.


@dataclass
class RuntimeHealth:
    connection_count: int = 0
    subscriptions: int = 0
    reconnects: int = 0
    acknowledgements: set[str] = field(default_factory=set)
    failed_markets: set[str] = field(default_factory=set)


class MultiAssetPublicRuntime:
    """One public connection, bounded recovery, and per-market isolation."""

    def __init__(
        self,
        *,
        registry: MarketRegistryManager,
        authority: MultiAssetDataAuthority,
        client: HyperliquidPublicClient,
        websocket_factory: Callable[[str], Awaitable[Any]] = connect,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.registry = registry
        self.authority = authority
        self.client = client
        self.websocket_factory = websocket_factory
        self.clock = clock
        self.health = RuntimeHealth()

    def selected_markets(self) -> tuple[RegistryMarket, ...]:
        active = self.registry.active()
        if active is None:
            raise DataRouteError("validated active Registry is required")
        return tuple(item for item in active.markets if item.lifecycle.value != "DISABLED")

    def subscriptions(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "method": "subscribe",
                "subscription": {"type": "candle", "coin": item.identity.coin, "interval": "5m"},
            }
            for item in self.selected_markets()
        )

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

    def warmup_all(self) -> dict[str, int]:
        now_ms = int(self.clock().timestamp() * 1000)
        end_ms = now_ms - (now_ms % 300_000)
        start_ms = end_ms - _WARMUP_5M_BARS * 300_000
        results: dict[str, int] = {}
        for market in self.selected_markets():
            try:
                results[market.identity.market_id] = self.warmup(
                    market, start_ms=start_ms, end_ms=end_ms
                )
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
        return results

    def recover_gaps(self) -> dict[str, int]:
        """Bounded REST recovery after a disconnect; isolated per market."""
        now_ms = int(self.clock().timestamp() * 1000)
        end_ms = now_ms - (now_ms % 300_000)
        recovered: dict[str, int] = {}
        for market in self.selected_markets():
            last = self.authority.store.last_open(market.identity.market_id)
            start_ms = end_ms - _WARMUP_5M_BARS * 300_000 if last is None else last + 300_000
            if start_ms >= end_ms:
                continue
            try:
                recovered[market.identity.market_id] = self.warmup(
                    market, start_ms=start_ms, end_ms=end_ms
                )
                self.health.failed_markets.discard(market.identity.market_id)
            except (DataRouteError, PublicDataError):
                self.health.failed_markets.add(market.identity.market_id)
        return recovered

    async def run(self, shutdown: asyncio.Event) -> None:
        """Run until shutdown, retrying a finite number of expected disconnects."""
        for attempt in range(_MAX_RECONNECTS + 1):
            if shutdown.is_set():
                return
            try:
                websocket = await self.websocket_factory(WS_URL)
                self.health.connection_count = 1
                if attempt:
                    self.recover_gaps()
                await self._subscribe(websocket)
                await self._receive_loop(websocket, shutdown)
                return
            except (TimeoutError, OSError, PublicDataError, DataRouteError):
                self.health.connection_count = 0
                if attempt == _MAX_RECONNECTS:
                    return
                self.health.reconnects += 1
                await asyncio.sleep(min(2**attempt, 4))

    async def _subscribe(self, websocket: Any) -> None:
        requests = self.subscriptions()
        for request in requests:
            await websocket.send(json.dumps(request, separators=(",", ":")))
        self.health.subscriptions = len(requests)

    async def _receive_loop(self, websocket: Any, shutdown: asyncio.Event) -> None:
        while not shutdown.is_set():
            raw = await websocket.recv()
            await self.handle_message(raw)

    async def handle_message(self, raw: str) -> None:
        try:
            message = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise DataRouteError("websocket message is invalid") from exc
        if not isinstance(message, dict):
            raise DataRouteError("websocket message is invalid")
        if message.get("channel") == "subscriptionResponse":
            data = message.get("data")
            if isinstance(data, dict) and isinstance(data.get("subscription"), dict):
                coin = data["subscription"].get("coin")
                if isinstance(coin, str):
                    self.health.acknowledgements.add(coin)
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
            candidate = self.authority.offer_ws_candidate(
                market=market, payload=payload, received_at=self.clock()
            )
            open_ms = payload.get("t")
            if not isinstance(open_ms, int):
                raise DataRouteError("websocket candle is missing open timestamp")
            # A bounded target REST request is the admission finality check.
            snapshot = self.client.closed_candles(
                coin=market.identity.coin,
                interval="5m",
                start_ms=open_ms,
                end_ms=open_ms + 300_000,
            )
            stable_snapshot = self.client.closed_candles(
                coin=market.identity.coin,
                interval="5m",
                start_ms=open_ms,
                end_ms=open_ms + 300_000,
            )
            if not isinstance(snapshot, list) or not isinstance(stable_snapshot, list):
                raise DataRouteError("candleSnapshot did not return a list")
            self.authority.confirm_ws_candidate(
                market=market,
                open_time_ms=open_ms,
                candidate_fingerprint=candidate,
                snapshot=snapshot,
                stable_snapshot=stable_snapshot,
                received_at=self.clock(),
            )
        except (DataRouteError, PublicDataError):
            self.health.failed_markets.add(market.identity.market_id)
