from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from itertools import pairwise
from typing import Any, Literal

from trader_assist_v0.contracts.common import canonical_json_bytes

ETH = "ETH"
INTERVAL_MILLISECONDS: dict[str, int] = {"5m": 5 * 60_000, "15m": 15 * 60_000}
SNAPSHOT_LIMITS: dict[str, int] = {"5m": 64, "15m": 32}


class DataQualityState(StrEnum):
    READY = "READY"
    WARMING = "WARMING"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"
    GAP = "GAP"
    CONFLICT = "CONFLICT"
    INVALID = "INVALID"
    METADATA_UNAVAILABLE = "METADATA_UNAVAILABLE"


class MarketDataError(ValueError):
    """An observation cannot become an ETH-LDAR input."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MarketDataError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise MarketDataError("non-finite JSON values are prohibited")


def _strict_json(raw_text: str) -> object:
    try:
        value = json.loads(
            raw_text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, MarketDataError) as exc:
        raise MarketDataError("raw evidence is not a strict JSON object") from exc
    return value


def _strict_object(raw_text: str) -> dict[str, Any]:
    value = _strict_json(raw_text)
    if type(value) is not dict:
        raise MarketDataError("raw evidence must be a JSON object")
    return value


def _decimal(value: object, name: str, *, positive: bool = False) -> Decimal:
    if type(value) is not str:
        raise MarketDataError(f"{name} must be a base-10 decimal string")
    if "e" in value.lower() or not value or value.strip() != value:
        raise MarketDataError(f"{name} must not use exponent or whitespace")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise MarketDataError(f"{name} is not decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise MarketDataError(f"{name} is outside its allowed range")
    return result


def _integer(value: object, name: str) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise MarketDataError(f"{name} must be a non-negative integer")
    return value


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MarketDataError("receive timestamps must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class RawEvidence:
    raw_text: str
    sha256: str
    source_id: str
    operation: str
    received_at: datetime
    receive_sequence: int
    connection_id: str
    product_version: str = "ETH-public-normalized-v0.1"


@dataclass(frozen=True)
class Candle:
    interval: Literal["5m", "15m"]
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    evidence: RawEvidence

    @property
    def identity(self) -> tuple[str, str, int]:
        return (ETH, self.interval, self.open_time_ms)

    @property
    def canonical_hash(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(
                {
                    "symbol": ETH,
                    "interval": self.interval,
                    "open_time_ms": self.open_time_ms,
                    "close_time_ms": self.close_time_ms,
                    "open": str(self.open),
                    "high": str(self.high),
                    "low": str(self.low),
                    "close": str(self.close),
                    "volume": str(self.volume),
                }
            )
        ).hexdigest()


@dataclass(frozen=True)
class ActiveAssetContext:
    mark_px: Decimal
    mid_px: Decimal | None
    open_interest: Decimal
    funding: Decimal
    source_time_ms: int | None
    evidence: RawEvidence

    @property
    def reference_price(self) -> Decimal | None:
        if self.mid_px is not None and self.mid_px > 0:
            return self.mid_px
        return self.mark_px if self.mark_px > 0 else None


@dataclass(frozen=True)
class AssetMetadata:
    sz_decimals: int
    evidence: RawEvidence


@dataclass(frozen=True)
class DataQuality:
    state: DataQualityState
    reason: str


def evidence_from_raw(
    raw_text: str,
    *,
    operation: str,
    received_at: datetime,
    receive_sequence: int,
    connection_id: str,
    source_id: str = "hyperliquid-public-mainnet",
) -> RawEvidence:
    if not raw_text or type(raw_text) is not str:
        raise MarketDataError("raw evidence must be non-empty UTF-8 text")
    if not operation or not connection_id or receive_sequence < 0:
        raise MarketDataError("evidence identity is incomplete")
    encoded = raw_text.encode("utf-8", errors="strict")
    _strict_json(raw_text)
    return RawEvidence(
        raw_text=raw_text,
        sha256=hashlib.sha256(encoded).hexdigest(),
        source_id=source_id,
        operation=operation,
        received_at=_utc(received_at),
        receive_sequence=receive_sequence,
        connection_id=connection_id,
    )


def candle_from_websocket(raw_text: str, evidence: RawEvidence) -> Candle:
    message = _strict_object(raw_text)
    if message.get("channel") != "candle" or type(message.get("data")) is not dict:
        raise MarketDataError("expected a candle WebSocket envelope")
    data = message["data"]
    if data.get("s") != ETH or data.get("i") not in INTERVAL_MILLISECONDS:
        raise MarketDataError("candle is outside the ETH 5m/15m authority")
    interval = data["i"]
    assert interval in {"5m", "15m"}
    open_time = _integer(data.get("t"), "candle open time")
    close_time = _integer(data.get("T"), "candle close time")
    if close_time - open_time != INTERVAL_MILLISECONDS[interval]:
        raise MarketDataError("candle interval boundary is invalid")
    candle = Candle(
        interval=interval,
        open_time_ms=open_time,
        close_time_ms=close_time,
        open=_decimal(data.get("o"), "open", positive=True),
        high=_decimal(data.get("h"), "high", positive=True),
        low=_decimal(data.get("l"), "low", positive=True),
        close=_decimal(data.get("c"), "close", positive=True),
        volume=_decimal(data.get("v"), "volume"),
        evidence=evidence,
    )
    if candle.low > min(candle.open, candle.close) or candle.high < max(candle.open, candle.close):
        raise MarketDataError("candle OHLC range is invalid")
    if candle.volume < 0:
        raise MarketDataError("candle volume is invalid")
    return candle


def context_from_websocket(raw_text: str, evidence: RawEvidence) -> ActiveAssetContext:
    message = _strict_object(raw_text)
    if message.get("channel") != "activeAssetCtx" or type(message.get("data")) is not dict:
        raise MarketDataError("expected an activeAssetCtx WebSocket envelope")
    data = message["data"]
    context = data.get("ctx") if type(data.get("ctx")) is dict else data
    if data.get("coin", ETH) != ETH:
        raise MarketDataError("asset context is not ETH")
    mid = context.get("midPx")
    source_time = context.get("time")
    return ActiveAssetContext(
        mark_px=_decimal(context.get("markPx"), "markPx", positive=True),
        mid_px=None if mid is None else _decimal(mid, "midPx", positive=True),
        open_interest=_decimal(context.get("openInterest"), "openInterest"),
        funding=_decimal(context.get("funding"), "funding"),
        source_time_ms=None if source_time is None else _integer(source_time, "context time"),
        evidence=evidence,
    )


def metadata_from_info(raw_text: str, evidence: RawEvidence) -> AssetMetadata:
    payload = _strict_json(raw_text)
    if type(payload) is list:
        if not payload or type(payload[0]) is not dict:
            raise MarketDataError("metaAndAssetCtxs has an invalid metadata object")
        metadata = payload[0]
    elif type(payload) is dict:
        metadata = payload
    else:
        raise MarketDataError("metadata must be a JSON object or metaAndAssetCtxs array")
    universe = metadata.get("universe")
    if type(universe) is not list:
        raise MarketDataError("metadata must contain a universe array")
    matches = [item for item in universe if type(item) is dict and item.get("name") == ETH]
    if len(matches) != 1:
        raise MarketDataError("metadata must contain exactly one ETH entry")
    decimals = matches[0].get("szDecimals")
    if type(decimals) is not int or isinstance(decimals, bool) or decimals < 0 or decimals > 18:
        raise MarketDataError("ETH szDecimals is invalid")
    return AssetMetadata(sz_decimals=decimals, evidence=evidence)


@dataclass
class EthMarketData:
    """Fail-closed normalized data authority for the First Launch strategy."""

    candles: dict[str, dict[int, Candle]] = field(
        default_factory=lambda: {"5m": {}, "15m": {}}
    )
    active_context: ActiveAssetContext | None = None
    metadata: AssetMetadata | None = None
    disconnected: bool = True
    invalid_reason: str | None = None
    conflicts: set[tuple[str, str, int]] = field(default_factory=set)
    transitions: list[DataQuality] = field(default_factory=list)

    def begin_connection(self) -> None:
        """A reconnect starts a new warm-up; prior prices cannot bridge it."""
        self.disconnected = False
        self.candles = {"5m": {}, "15m": {}}
        self.active_context = None

    def mark_disconnected(self) -> None:
        self.disconnected = True

    def accept_candle(self, candle: Candle) -> Literal["ACCEPTED", "DUPLICATE", "CONFLICT"]:
        if candle.evidence.received_at.timestamp() * 1000 <= candle.close_time_ms:
            self.invalid_reason = "CANDLE_NOT_CLOSED"
            return "CONFLICT"
        interval_candles = self.candles[candle.interval]
        existing = interval_candles.get(candle.open_time_ms)
        if existing is None:
            interval_candles[candle.open_time_ms] = candle
            return "ACCEPTED"
        if existing.canonical_hash == candle.canonical_hash:
            return "DUPLICATE"
        self.conflicts.add(candle.identity)
        return "CONFLICT"

    def recover_snapshot(self, interval: Literal["5m", "15m"], candles: Iterable[Candle]) -> None:
        recovered = tuple(candles)
        if len(recovered) > SNAPSHOT_LIMITS[interval]:
            raise MarketDataError("snapshot exceeds its bounded recovery limit")
        if any(candle.interval != interval for candle in recovered):
            raise MarketDataError("snapshot interval does not match its authority")
        for candle in recovered:
            self.accept_candle(candle)

    def accept_context(self, context: ActiveAssetContext) -> None:
        if context.reference_price is None:
            self.invalid_reason = "REFERENCE_PRICE_INVALID"
            return
        self.active_context = context

    def accept_metadata(self, metadata: AssetMetadata) -> None:
        self.metadata = metadata

    def ingest_websocket(
        self,
        raw_text: str,
        *,
        received_at: datetime,
        receive_sequence: int,
        connection_id: str,
    ) -> Literal["ACCEPTED", "DUPLICATE", "CONFLICT", "CONTEXT_ACCEPTED"]:
        """Apply one original WebSocket text frame through the live/replay path."""
        evidence = evidence_from_raw(
            raw_text,
            operation="WebSocket",
            received_at=received_at,
            receive_sequence=receive_sequence,
            connection_id=connection_id,
        )
        try:
            message = _strict_object(raw_text)
            if message.get("channel") == "candle":
                return self.accept_candle(candle_from_websocket(raw_text, evidence))
            if message.get("channel") == "activeAssetCtx":
                self.accept_context(context_from_websocket(raw_text, evidence))
                return "CONTEXT_ACCEPTED"
            raise MarketDataError("WebSocket channel is outside the First Launch authority")
        except MarketDataError:
            self.invalid_reason = "WEBSOCKET_OBSERVATION_INVALID"
            raise

    def ingest_metadata_info(
        self,
        raw_text: str,
        *,
        received_at: datetime,
        receive_sequence: int,
        connection_id: str,
    ) -> None:
        """Apply the cold-start/recovery metadata response; no polling is implied."""
        evidence = evidence_from_raw(
            raw_text,
            operation="metaAndAssetCtxs",
            received_at=received_at,
            receive_sequence=receive_sequence,
            connection_id=connection_id,
        )
        try:
            self.accept_metadata(metadata_from_info(raw_text, evidence))
        except MarketDataError:
            self.invalid_reason = "METADATA_OBSERVATION_INVALID"
            raise

    def _contiguous(self, interval: Literal["5m", "15m"], required: int) -> bool:
        values = sorted(self.candles[interval])
        if len(values) < required:
            return False
        recent = values[-required:]
        width = INTERVAL_MILLISECONDS[interval]
        return all(right - left == width for left, right in pairwise(recent))

    def quality(self, evaluated_at: datetime) -> DataQuality:
        now = _utc(evaluated_at)
        result: DataQuality
        if self.invalid_reason is not None:
            result = DataQuality(DataQualityState.INVALID, self.invalid_reason)
        elif self.conflicts:
            result = DataQuality(DataQualityState.CONFLICT, "CANDLE_IDENTITY_CONFLICT")
        elif (
            len(self.candles["5m"]) >= 36
            and len(self.candles["15m"]) >= 20
            and (not self._contiguous("5m", 36) or not self._contiguous("15m", 20))
        ):
            result = DataQuality(DataQualityState.GAP, "CANDLE_SEQUENCE_GAP")
        elif self.disconnected:
            result = DataQuality(DataQualityState.DISCONNECTED, "PUBLIC_CONNECTION_DISCONNECTED")
        elif self.metadata is None:
            result = DataQuality(
                DataQualityState.METADATA_UNAVAILABLE,
                "ETH_SZ_DECIMALS_UNAVAILABLE",
            )
        elif not self._contiguous("5m", 36) or not self._contiguous("15m", 20):
            result = DataQuality(DataQualityState.WARMING, "INSUFFICIENT_CLOSED_CANDLES")
        elif self.active_context is None:
            result = DataQuality(DataQualityState.WARMING, "ACTIVE_ASSET_CONTEXT_UNAVAILABLE")
        else:
            latest_5m = max(self.candles["5m"].values(), key=lambda item: item.close_time_ms)
            latest_15m = max(self.candles["15m"].values(), key=lambda item: item.close_time_ms)
            if now - self.active_context.evidence.received_at > timedelta(seconds=15):
                result = DataQuality(DataQualityState.STALE, "ACTIVE_ASSET_CONTEXT_STALE")
            elif now.timestamp() * 1000 - latest_5m.close_time_ms > 390_000:
                result = DataQuality(DataQualityState.STALE, "CANDLE_5M_STALE")
            elif now.timestamp() * 1000 - latest_15m.close_time_ms > 990_000:
                result = DataQuality(DataQualityState.STALE, "CANDLE_15M_STALE")
            elif now - self.metadata.evidence.received_at > timedelta(hours=24):
                result = DataQuality(DataQualityState.STALE, "METADATA_STALE")
            else:
                result = DataQuality(DataQualityState.READY, "ALL_REQUIRED_INPUTS_FRESH")
        if not self.transitions or self.transitions[-1] != result:
            self.transitions.append(result)
        return result


@dataclass
class ReconnectController:
    """One-attempt-at-a-time reconnect schedule with no jitter or overlap."""

    attempt_count: int = 0
    attempt_in_flight: bool = False
    healthy_since: datetime | None = None

    def on_disconnect(self) -> None:
        self.attempt_in_flight = False
        self.healthy_since = None

    def next_delay_seconds(self) -> int:
        if self.attempt_in_flight:
            raise MarketDataError("overlapping public connection attempt")
        schedule = (1, 2, 4, 8, 16, 30)
        delay = schedule[min(self.attempt_count, len(schedule) - 1)]
        self.attempt_count += 1
        self.attempt_in_flight = True
        return delay

    def connection_opened(self, now: datetime) -> None:
        if not self.attempt_in_flight:
            raise MarketDataError("connection opened without a scheduled attempt")
        self.attempt_in_flight = False
        self.healthy_since = _utc(now)

    def observe_health(self, now: datetime) -> None:
        if (
            self.healthy_since is not None
            and _utc(now) - self.healthy_since >= timedelta(minutes=5)
        ):
            self.attempt_count = 0
