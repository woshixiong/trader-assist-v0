"""Thin, public-read-only Hyperliquid `/info` adapter.

The adapter deliberately exposes only the provider's public information and
market-data requests needed by the multi-asset Shadow route.  It has no user,
wallet, signing, exchange, order, or mutation operation.
"""

from __future__ import annotations

import json
import ssl
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

from .models import RegistryMarket
from .outcome_engine import ONE_MINUTE_MS, OneMinuteBar, OutcomeEngineError
from .planning import (
    HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS,
    HARD_MAX_SPREAD_BPS,
    LiquidityAssessment,
    PublicBbo,
    Side,
    assess_l2,
)
from .registry import MarketRegistryManager

if TYPE_CHECKING:
    from .integration import PublicL2Snapshot, ScannerPublicSnapshot

INFO_URL = "https://api.hyperliquid.xyz/info"
_ALLOWED_TYPES = frozenset(
    {"perpDexs", "allPerpMetas", "meta", "metaAndAssetCtxs", "candleSnapshot", "l2Book"}
)


class PublicDataError(RuntimeError):
    pass


_MAX_PUBLIC_EVIDENCE_AGE_MS = 10_000


def _default_wall_clock_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True)
class _NormalizedL2:
    market_id: str
    coin: str
    observed_at_ms: int
    bids: tuple[tuple[Decimal, Decimal], ...]
    asks: tuple[tuple[Decimal, Decimal], ...]
    provenance_hash: str

    @property
    def best_bid(self) -> Decimal:
        return self.bids[0][0]

    @property
    def best_ask(self) -> Decimal:
        return self.asks[0][0]


class HttpPost(Protocol):
    def __call__(self, url: str, body: bytes, timeout_seconds: float) -> bytes: ...


def _default_post(url: str, body: bytes, timeout_seconds: float) -> bytes:
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(
            request, timeout=timeout_seconds, context=ssl.create_default_context()
        ) as response:
            return cast(bytes, response.read())
    except (HTTPError, URLError, TimeoutError, ssl.SSLError) as exc:
        raise PublicDataError("official public API request failed") from exc


@dataclass(frozen=True)
class HyperliquidPublicClient:
    """Provider-native public transport with a narrow allowlist of request shapes."""

    post: HttpPost = _default_post
    timeout_seconds: float = 15.0

    def request(self, payload: Mapping[str, object]) -> object:
        request_type = payload.get("type")
        if request_type not in _ALLOWED_TYPES or not self._is_supported_shape(payload):
            raise PublicDataError("public request is outside the approved market-data surface")
        raw = self.post(
            INFO_URL,
            json.dumps(dict(payload), separators=(",", ":")).encode(),
            self.timeout_seconds,
        )
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicDataError("official public API returned invalid JSON") from exc

    @staticmethod
    def _is_supported_shape(payload: Mapping[str, object]) -> bool:
        request_type = payload.get("type")
        if request_type == "perpDexs":
            return set(payload) == {"type"}
        if request_type == "allPerpMetas":
            return set(payload) == {"type"}
        if request_type in {"meta", "metaAndAssetCtxs"}:
            return set(payload) <= {"type", "dex"} and isinstance(payload.get("dex", ""), str)
        if request_type == "candleSnapshot":
            request = payload.get("req")
            return (
                set(payload) == {"type", "req"}
                and isinstance(request, Mapping)
                and set(request) == {"coin", "interval", "startTime", "endTime"}
                and isinstance(request["coin"], str)
                and request["interval"] in {"1m", "5m"}
                and isinstance(request["startTime"], int)
                and isinstance(request["endTime"], int)
            )
        if request_type == "l2Book":
            return set(payload) <= {"type", "coin", "nSigFigs", "mantissa"} and isinstance(
                payload.get("coin"), str
            )
        return False

    def perp_dexes(self) -> object:
        return self.request({"type": "perpDexs"})

    def metadata(self, dex: str) -> object:
        # The official API represents the first/native perp DEX as omitted or
        # empty.  Internal MAIN is deliberately never emitted on the wire.
        payload: dict[str, object] = {"type": "meta"}
        if dex != "":
            payload["dex"] = dex
        return self.request(payload)

    def metadata_and_context(self, dex: str) -> object:
        payload: dict[str, object] = {"type": "metaAndAssetCtxs"}
        if dex != "":
            payload["dex"] = dex
        return self.request(payload)

    def all_perp_metas(self) -> object:
        return self.request({"type": "allPerpMetas"})

    def closed_candles(self, *, coin: str, interval: str, start_ms: int, end_ms: int) -> object:
        return self.request(
            {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": interval,
                    "startTime": start_ms,
                    "endTime": end_ms,
                },
            }
        )

    def l2_book(self, *, coin: str) -> object:
        return self.request({"type": "l2Book", "coin": coin})

    def liquidity_assessment(
        self, *, market_id: str, coin: str, side: Side, response: object
    ) -> LiquidityAssessment:
        """Parse one official on-demand L2 response into immutable hard-gate evidence."""
        normalized = _normalize_l2(market_id=market_id, coin=coin, response=response)
        return assess_l2(
            market_id=market_id,
            coin=coin,
            side=side,
            observed_at_ms=normalized.observed_at_ms,
            best_bid=normalized.best_bid,
            best_ask=normalized.best_ask,
            levels=normalized.asks if side is Side.LONG else normalized.bids,
            provenance_hash=normalized.provenance_hash,
        )


def _normalize_l2(*, market_id: str, coin: str, response: object) -> _NormalizedL2:
    if not isinstance(response, dict) or response.get("coin") != coin:
        raise PublicDataError("public L2 response identity is invalid")
    observed = response.get("time")
    levels = response.get("levels")
    if (
        not isinstance(observed, int)
        or isinstance(observed, bool)
        or observed < 0
        or not isinstance(levels, list)
        or len(levels) != 2
        or not all(isinstance(side, list) for side in levels)
    ):
        raise PublicDataError("public L2 response shape is invalid")
    try:
        bids = tuple((Decimal(str(item["px"])), Decimal(str(item["sz"]))) for item in levels[0])
        asks = tuple((Decimal(str(item["px"])), Decimal(str(item["sz"]))) for item in levels[1])
    except (KeyError, TypeError, ArithmeticError, ValueError) as exc:
        raise PublicDataError("public L2 levels are invalid") from exc
    if not bids or not asks:
        raise PublicDataError("public L2 book is incomplete")
    if any(
        not price.is_finite() or not size.is_finite() or price <= 0 or size <= 0
        for price, size in bids + asks
    ):
        raise PublicDataError("public L2 book has invalid price or size")
    if any(right[0] > left[0] for left, right in pairwise(bids)):
        raise PublicDataError("public L2 bids are not ordered outward")
    if any(right[0] < left[0] for left, right in pairwise(asks)):
        raise PublicDataError("public L2 asks are not ordered outward")
    if bids[0][0] >= asks[0][0]:
        raise PublicDataError("public L2 book is crossed")
    return _NormalizedL2(
        market_id=market_id,
        coin=coin,
        observed_at_ms=observed,
        bids=bids,
        asks=asks,
        provenance_hash=sha256_hex(canonical_json_bytes(response)),
    )


@dataclass
class HyperliquidPublicPlanningAdapter:
    """One-request BBO/L2 adapter over official public, on-demand L2 evidence."""

    client: HyperliquidPublicClient
    max_age_ms: int = _MAX_PUBLIC_EVIDENCE_AGE_MS
    wall_clock_ms: Callable[[], int] = _default_wall_clock_ms
    _pending: dict[str, _NormalizedL2] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.max_age_ms < 0:
            raise ValueError("public L2 maximum age must be non-negative")

    def fetch_bbo(self, *, market: RegistryMarket, now_ms: int) -> PublicBbo:
        normalized = self._fresh_l2(market)
        self._pending[normalized.market_id] = normalized
        return PublicBbo(
            best_bid=normalized.best_bid,
            best_ask=normalized.best_ask,
            observed_at_ms=normalized.observed_at_ms,
            market_id=normalized.market_id,
            coin=normalized.coin,
        )

    def fetch_l2(
        self, *, market: RegistryMarket, side: Side, bbo: PublicBbo
    ) -> PublicL2Snapshot:
        from .integration import PublicL2Snapshot

        normalized = self._pending.pop(market.identity.market_id, None)
        if (
            normalized is None
            or bbo.market_id != market.identity.market_id
            or bbo.coin != market.identity.coin
            or normalized.observed_at_ms != bbo.observed_at_ms
            or normalized.best_bid != bbo.best_bid
            or normalized.best_ask != bbo.best_ask
        ):
            raise PublicDataError("BBO does not bind one retained public L2 response")
        return PublicL2Snapshot(
            market_id=normalized.market_id,
            coin=normalized.coin,
            observed_at_ms=normalized.observed_at_ms,
            best_bid=normalized.best_bid,
            best_ask=normalized.best_ask,
            levels=normalized.asks if side is Side.LONG else normalized.bids,
            provenance_hash=normalized.provenance_hash,
        )

    def fetch_scanner_snapshot(
        self,
        *,
        market: RegistryMarket,
        now_ms: int,
        btc_returns: tuple[Decimal | None, Decimal | None, Decimal | None],
    ) -> ScannerPublicSnapshot:
        from .integration import ScannerPublicSnapshot

        normalized = self._fresh_l2(market)
        assessments = tuple(
            assess_l2(
                market_id=normalized.market_id,
                coin=normalized.coin,
                side=side,
                observed_at_ms=normalized.observed_at_ms,
                best_bid=normalized.best_bid,
                best_ask=normalized.best_ask,
                levels=normalized.asks if side is Side.LONG else normalized.bids,
                provenance_hash=normalized.provenance_hash,
            )
            for side in (Side.LONG, Side.SHORT)
        )
        healthy = (
            PublicBbo(normalized.best_bid, normalized.best_ask).spread_bps
            <= HARD_MAX_SPREAD_BPS
            and all(
                item.sufficient_depth
                and item.one_way_slippage_bps is not None
                and item.one_way_slippage_bps
                <= HARD_MAX_PRIMARY_ONE_WAY_SLIPPAGE_BPS
                for item in assessments
            )
        )
        return ScannerPublicSnapshot(
            current_spread_price=normalized.best_ask - normalized.best_bid,
            liquidity_healthy=healthy,
            btc_returns=btc_returns,
        )

    def _fresh_l2(self, market: RegistryMarket) -> _NormalizedL2:
        response = self.client.l2_book(coin=market.identity.coin)
        post_response_wall_ms = self.wall_clock_ms()
        normalized = _normalize_l2(
            market_id=market.identity.market_id,
            coin=market.identity.coin,
            response=response,
        )
        if not 0 <= post_response_wall_ms - normalized.observed_at_ms <= self.max_age_ms:
            raise PublicDataError("public L2 response is stale or future-dated")
        return normalized


@dataclass
class HyperliquidRestOneMinuteProvider:
    """REST-only closed-1m provider with bounded demand bookkeeping."""

    client: HyperliquidPublicClient
    registry: MarketRegistryManager
    subscribed_market_ids: set[str] = field(default_factory=set, init=False)

    def subscribe_1m(self, *, market_id: str) -> None:
        self._market(market_id)
        self.subscribed_market_ids.add(market_id)

    def unsubscribe_1m(self, *, market_id: str) -> None:
        self.subscribed_market_ids.discard(market_id)

    def backfill_1m(
        self, *, market_id: str, start_ms: int, end_ms: int
    ) -> tuple[OneMinuteBar, ...]:
        market = self._market(market_id)
        if (
            isinstance(start_ms, bool)
            or isinstance(end_ms, bool)
            or not isinstance(start_ms, int)
            or not isinstance(end_ms, int)
            or start_ms < 0
            or end_ms <= start_ms
            or start_ms % ONE_MINUTE_MS
            or end_ms % ONE_MINUTE_MS
        ):
            raise PublicDataError("public 1m request window is invalid")
        response = self.client.closed_candles(
            coin=market.identity.coin,
            interval="1m",
            start_ms=start_ms,
            end_ms=end_ms,
        )
        if not isinstance(response, list):
            raise PublicDataError("candleSnapshot did not return a list")
        bars = tuple(
            self._bar(market=market, payload=item, start_ms=start_ms, end_ms=end_ms)
            for item in response
        )
        ordered = tuple(sorted(bars, key=lambda bar: (bar.open_time_ms, bar.canonical_hash)))
        if len({bar.open_time_ms for bar in ordered}) != len(ordered):
            raise PublicDataError("public 1m response has duplicate time slots")
        return ordered

    def _market(self, market_id: str) -> RegistryMarket:
        registry = self.registry.active()
        if registry is None:
            raise PublicDataError("active Registry is required for public 1m identity")
        matches = tuple(
            market for market in registry.markets if market.identity.market_id == market_id
        )
        if len(matches) != 1:
            raise PublicDataError("public 1m market identity is not active Registry authority")
        return matches[0]

    @staticmethod
    def _bar(
        *, market: RegistryMarket, payload: object, start_ms: int, end_ms: int
    ) -> OneMinuteBar:
        if not isinstance(payload, dict):
            raise PublicDataError("public 1m candle is invalid")
        try:
            interval = payload["i"]
            coin = payload["s"]
            open_ms = payload["t"]
            close_ms = payload["T"]
            values = (payload["o"], payload["h"], payload["l"], payload["c"])
        except KeyError as exc:
            raise PublicDataError("public 1m candle is incomplete") from exc
        if (
            interval != "1m"
            or coin != market.identity.coin
            or not isinstance(open_ms, int)
            or isinstance(open_ms, bool)
            or not isinstance(close_ms, int)
            or isinstance(close_ms, bool)
            or open_ms % ONE_MINUTE_MS
            or close_ms != open_ms + ONE_MINUTE_MS - 1
            or not start_ms <= open_ms < end_ms
        ):
            raise PublicDataError("public 1m candle identity or window is invalid")
        try:
            return OneMinuteBar.create(
                market_id=market.identity.market_id,
                open_time_ms=open_ms,
                open=Decimal(str(values[0])),
                high=Decimal(str(values[1])),
                low=Decimal(str(values[2])),
                close=Decimal(str(values[3])),
                source_id="hyperliquid-public-candleSnapshot-1m",
            )
        except (ArithmeticError, OutcomeEngineError, ValueError) as exc:
            raise PublicDataError("public 1m candle values are invalid") from exc


class OfficialMetadataValidator:
    """One bounded official metadata snapshot for Registry identity validation."""

    def __init__(self, client: HyperliquidPublicClient) -> None:
        self._client = client
        self._records: dict[tuple[str, str], dict[str, object]] | None = None

    def _load(self) -> dict[tuple[str, str], dict[str, object]]:
        if self._records is not None:
            return self._records
        try:
            dexes = self._client.perp_dexes()
            metas = self._client.all_perp_metas()
        except PublicDataError:
            raise
        if not isinstance(dexes, list) or not isinstance(metas, list) or len(dexes) != len(metas):
            raise PublicDataError("official metadata response has incompatible DEX indexes")
        records: dict[tuple[str, str], dict[str, object]] = {}
        for index, meta in enumerate(metas):
            dex = (
                "MAIN"
                if index == 0
                else (dexes[index].get("name") if isinstance(dexes[index], dict) else None)
            )
            if not isinstance(dex, str) or not isinstance(meta, dict):
                raise PublicDataError("official metadata response has invalid DEX identity")
            universe = meta.get("universe")
            if not isinstance(universe, list):
                raise PublicDataError("official metadata response has invalid universe")
            for raw in universe:
                if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
                    raise PublicDataError("official metadata response has invalid market")
                records[(dex, raw["name"])] = raw
        self._records = records
        return records

    def __call__(self, market: RegistryMarket) -> bool:
        raw = self._load().get((market.identity.dex, market.identity.coin))
        if raw is None:
            return False
        try:
            return (
                market.metadata_hash == sha256_hex(canonical_json_bytes(raw))
                and raw.get("szDecimals") == market.size_decimals
                and Decimal(str(raw.get("maxLeverage"))) == market.max_leverage
                and market.price_max_decimals == 6 - market.size_decimals
            )
        except (ArithmeticError, TypeError, ValueError):
            return False
