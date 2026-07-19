from __future__ import annotations

import hashlib
import json
import weakref
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from itertools import pairwise
from typing import Any, Literal, cast

from trader_assist_v0.contracts.common import canonical_json_bytes

ETH: Literal["ETH"] = "ETH"
INTERVAL_MILLISECONDS: dict[str, int] = {"5m": 5 * 60_000, "15m": 15 * 60_000}
SNAPSHOT_LIMITS: dict[str, int] = {"5m": 64, "15m": 32}
STRATEGY_WARMUP_5M = 64
STRATEGY_WARMUP_15M = 20


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


class OpenCandleIgnored(MarketDataError):
    """A valid public candle observation that is not yet closed or issuable."""


# This registry deliberately binds authority to the object that a reviewed parser
# issued.  A field hash alone is forgeable by a caller; identity plus the frozen
# issuance fingerprint rejects constructors, copies, and post-issuance mutation.
_ISSUED: dict[int, tuple[weakref.ReferenceType[object], str]] = {}


def _issue[Issued](value: Issued, fingerprint: str) -> Issued:
    key = id(value)

    def _release(reference: weakref.ReferenceType[object]) -> None:
        current = _ISSUED.get(key)
        if current is not None and current[0] is reference:
            del _ISSUED[key]

    _ISSUED[key] = (weakref.ref(value, _release), fingerprint)
    return value


def _is_issued(value: object, fingerprint: str) -> bool:
    issued = _ISSUED.get(id(value))
    return issued is not None and issued[0]() is value and issued[1] == fingerprint


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
    return cast(dict[str, Any], value)


def _decimal(
    value: object, name: str, *, positive: bool = False, non_negative: bool = False
) -> Decimal:
    if type(value) is not str:
        raise MarketDataError(f"{name} must be a base-10 decimal string")
    if "e" in value.lower() or not value or value.strip() != value:
        raise MarketDataError(f"{name} must not use exponent or whitespace")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise MarketDataError(f"{name} is not decimal") from exc
    if not result.is_finite() or (positive and result <= 0) or (non_negative and result < 0):
        raise MarketDataError(f"{name} is outside its allowed range")
    return result


def _integer(value: object, name: str) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise MarketDataError(f"{name} must be a non-negative integer")
    return value


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
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

    def __post_init__(self) -> None:
        if type(self.raw_text) is not str or not self.raw_text:
            raise MarketDataError("raw evidence must be exact non-empty text")
        _strict_json(self.raw_text)
        if (
            type(self.sha256) is not str
            or self.sha256
            != hashlib.sha256(self.raw_text.encode("utf-8", errors="strict")).hexdigest()
        ):
            raise MarketDataError("raw evidence hash does not bind its text")
        for value in (self.source_id, self.operation, self.connection_id, self.product_version):
            if type(value) is not str or not value or value.strip() != value:
                raise MarketDataError("evidence identity is incomplete")
        if type(self.receive_sequence) is not int or self.receive_sequence < 0:
            raise MarketDataError("receive sequence must be a non-negative integer")
        object.__setattr__(self, "received_at", _utc(self.received_at))


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
class RollingComposite:
    """A causal, immutable 5m rolling candle composite."""

    symbol: Literal["ETH"]
    span_minutes: Literal[15, 30, 60]
    cutoff_identity: tuple[str, str, int]
    cutoff_close_time_ms: int
    constituent_identities: tuple[tuple[str, str, int], ...]
    constituent_canonical_hashes: tuple[str, ...]
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    midpoint: Decimal
    canonical_hash: str

    def __post_init__(self) -> None:
        expected_count = {15: 3, 30: 6, 60: 12}.get(self.span_minutes)
        if (
            self.symbol != ETH
            or expected_count is None
            or len(self.constituent_identities) != expected_count
            or len(self.constituent_canonical_hashes) != expected_count
            or self.midpoint != (self.high + self.low) / Decimal("2")
            or self.canonical_hash
            != hashlib.sha256(canonical_json_bytes(self.payload())).hexdigest()
        ):
            raise MarketDataError("ROLLING_COMPOSITE_AUTHORITY_INVALID")

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "span_minutes": self.span_minutes,
            "cutoff_identity": self.cutoff_identity,
            "cutoff_close_time_ms": self.cutoff_close_time_ms,
            "constituent_identities": self.constituent_identities,
            "constituent_canonical_hashes": self.constituent_canonical_hashes,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "midpoint": self.midpoint,
        }


def rolling_composite(
    candles: Iterable[Candle], span_minutes: Literal[15, 30, 60]
) -> RollingComposite:
    """Build a single final composite and reject all non-causal candle authority."""
    count = {15: 3, 30: 6, 60: 12}.get(span_minutes)
    if count is None:
        raise MarketDataError("ROLLING_SPAN_INVALID")
    values = tuple(candles)
    if len(values) < count:
        raise MarketDataError("ROLLING_COMPOSITE_INSUFFICIENT_CANDLES")
    selected = values[-count:]
    for candle in selected:
        _validated_candle(candle)
        if candle.interval != "5m" or candle.close_time_ms > selected[-1].close_time_ms:
            raise MarketDataError("ROLLING_COMPOSITE_UNAUTHORIZED_CANDLE")
    if any(
        right.open_time_ms - left.open_time_ms != INTERVAL_MILLISECONDS["5m"]
        for left, right in pairwise(selected)
    ):
        raise MarketDataError("ROLLING_COMPOSITE_GAP")
    identities = tuple(item.identity for item in selected)
    hashes = tuple(item.canonical_hash for item in selected)
    if len(set(identities)) != len(identities) or len(set(hashes)) != len(hashes):
        raise MarketDataError("ROLLING_COMPOSITE_DUPLICATE_OR_CONFLICT")
    midpoint = (max(item.high for item in selected) + min(item.low for item in selected)) / Decimal(
        "2"
    )
    body = {
        "symbol": ETH,
        "span_minutes": span_minutes,
        "cutoff_identity": selected[-1].identity,
        "cutoff_close_time_ms": selected[-1].close_time_ms,
        "constituent_identities": identities,
        "constituent_canonical_hashes": hashes,
        "open": selected[0].open,
        "high": max(item.high for item in selected),
        "low": min(item.low for item in selected),
        "close": selected[-1].close,
        "volume": sum((item.volume for item in selected), Decimal()),
        "midpoint": midpoint,
    }
    return RollingComposite(
        ETH,
        span_minutes,
        selected[-1].identity,
        selected[-1].close_time_ms,
        identities,
        hashes,
        selected[0].open,
        cast(Decimal, body["high"]),
        cast(Decimal, body["low"]),
        selected[-1].close,
        cast(Decimal, body["volume"]),
        midpoint,
        hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    )


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


@dataclass(frozen=True)
class StrategySnapshot:
    """An EthMarketData-issued, immutable input for deterministic strategy evaluation."""

    candles_5m: tuple[Candle, ...]
    candles_15m: tuple[Candle, ...]
    evaluated_at: datetime
    quality: DataQuality
    active_context: ActiveAssetContext | None
    metadata: AssetMetadata | None


def _evidence_payload(value: RawEvidence) -> dict[str, object]:
    return {
        "raw_text": value.raw_text,
        "sha256": value.sha256,
        "source_id": value.source_id,
        "operation": value.operation,
        "received_at": value.received_at,
        "receive_sequence": value.receive_sequence,
        "connection_id": value.connection_id,
        "product_version": value.product_version,
    }


def _candle_fingerprint(value: Candle) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "interval": value.interval,
                "open_time_ms": value.open_time_ms,
                "close_time_ms": value.close_time_ms,
                "open": value.open,
                "high": value.high,
                "low": value.low,
                "close": value.close,
                "volume": value.volume,
                "evidence": _evidence_payload(value.evidence),
            }
        )
    ).hexdigest()


def _context_fingerprint(value: ActiveAssetContext) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "mark_px": value.mark_px,
                "mid_px": value.mid_px,
                "open_interest": value.open_interest,
                "funding": value.funding,
                "source_time_ms": value.source_time_ms,
                "evidence": _evidence_payload(value.evidence),
            }
        )
    ).hexdigest()


def _metadata_fingerprint(value: AssetMetadata) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {"sz_decimals": value.sz_decimals, "evidence": _evidence_payload(value.evidence)}
        )
    ).hexdigest()


def _validated_candle(value: object) -> Candle:
    try:
        valid = type(value) is Candle and _is_issued(value, _candle_fingerprint(value))
    except (AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise MarketDataError("candle is not parser-issued immutable authority")
    return cast(Candle, value)


def _validated_context(value: object) -> ActiveAssetContext:
    try:
        valid = type(value) is ActiveAssetContext and _is_issued(value, _context_fingerprint(value))
    except (AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise MarketDataError("context is not parser-issued immutable authority")
    return cast(ActiveAssetContext, value)


def _validated_metadata(value: object) -> AssetMetadata:
    try:
        valid = type(value) is AssetMetadata and _is_issued(value, _metadata_fingerprint(value))
    except (AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise MarketDataError("metadata is not parser-issued immutable authority")
    return cast(AssetMetadata, value)


def _snapshot_fingerprint(value: StrategySnapshot) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "candles_5m": [_candle_fingerprint(item) for item in value.candles_5m],
                "candles_15m": [_candle_fingerprint(item) for item in value.candles_15m],
                "evaluated_at": value.evaluated_at,
                "quality": {"state": value.quality.state, "reason": value.quality.reason},
                "active_context": (
                    None
                    if value.active_context is None
                    else _context_fingerprint(value.active_context)
                ),
                "metadata": (
                    None if value.metadata is None else _metadata_fingerprint(value.metadata)
                ),
            }
        )
    ).hexdigest()


def _validated_strategy_snapshot(value: object) -> StrategySnapshot:
    if type(value) is not StrategySnapshot:
        raise MarketDataError("strategy snapshot authority is invalid")
    try:
        if (
            type(value.evaluated_at) is not datetime
            or value.evaluated_at.tzinfo is not UTC
            or type(value.quality) is not DataQuality
            or type(value.quality.state) is not DataQualityState
            or type(value.quality.reason) is not str
            or tuple(sorted(value.candles_5m, key=lambda candle: candle.open_time_ms))
            != value.candles_5m
            or tuple(sorted(value.candles_15m, key=lambda candle: candle.open_time_ms))
            != value.candles_15m
        ):
            raise MarketDataError("strategy snapshot authority is invalid")
        for candle in (*value.candles_5m, *value.candles_15m):
            _validated_candle(candle)
            if (
                candle.close_time_ms > int(value.evaluated_at.timestamp() * 1000)
                or candle.evidence.received_at > value.evaluated_at
            ):
                raise MarketDataError("strategy snapshot contains future candle authority")
        if value.active_context is not None:
            _validated_context(value.active_context)
            if value.active_context.evidence.received_at > value.evaluated_at:
                raise MarketDataError("strategy snapshot contains future context authority")
        if value.metadata is not None:
            _validated_metadata(value.metadata)
            if value.metadata.evidence.received_at > value.evaluated_at:
                raise MarketDataError("strategy snapshot contains future metadata authority")
        if not _is_issued(value, _snapshot_fingerprint(value)):
            raise MarketDataError("strategy snapshot authority is invalid")
    except (AttributeError, TypeError, ValueError) as exc:
        raise MarketDataError("strategy snapshot authority is invalid") from exc
    return value


def evidence_from_raw(
    raw_text: str,
    *,
    operation: str,
    received_at: datetime,
    receive_sequence: int,
    connection_id: str,
    source_id: str = "hyperliquid-public-mainnet",
) -> RawEvidence:
    if type(raw_text) is not str or not raw_text:
        raise MarketDataError("raw evidence must be non-empty UTF-8 text")
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


def _bound_evidence(raw_text: str, evidence: RawEvidence, operation: str) -> None:
    if type(raw_text) is not str or type(evidence) is not RawEvidence:
        raise MarketDataError("raw evidence authority is invalid")
    # Revalidate direct construction before accepting a lower-level parse path.
    RawEvidence(
        evidence.raw_text,
        evidence.sha256,
        evidence.source_id,
        evidence.operation,
        evidence.received_at,
        evidence.receive_sequence,
        evidence.connection_id,
        evidence.product_version,
    )
    if evidence.raw_text != raw_text or evidence.operation != operation:
        raise MarketDataError("raw text and evidence authority do not match")


def _candle_from_public_object(
    data: object,
    *,
    evidence: RawEvidence,
    requested_interval: Literal["5m", "15m"] | None = None,
) -> Candle:
    """Validate one public candle object without issuing market authority."""
    if type(data) is not dict:
        raise MarketDataError("public candle must be a JSON object")
    if data.get("s") != ETH or data.get("i") not in INTERVAL_MILLISECONDS:
        raise MarketDataError("candle is outside the ETH 5m/15m authority")
    interval = data["i"]
    assert interval in {"5m", "15m"}
    if requested_interval is not None and interval != requested_interval:
        raise MarketDataError("candle snapshot interval does not match request")
    required = {"t", "T", "s", "i", "o", "h", "l", "c", "v", "n"}
    if not required.issubset(data):
        raise MarketDataError("public candle lacks a frozen required field")
    open_time = _integer(data.get("t"), "candle open time")
    close_time = _integer(data.get("T"), "candle close time")
    _integer(data.get("n"), "candle trade count")
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


def _issue_closed_candle(value: Candle) -> Candle:
    """Issue immutable candle authority only after the evidence proves closure."""
    if value.close_time_ms >= int(value.evidence.received_at.timestamp() * 1000):
        raise OpenCandleIgnored("candle is not closed at evidence receipt")
    return _issue(value, _candle_fingerprint(value))


def candles_from_snapshot(
    raw_text: str,
    evidence: RawEvidence,
    *,
    requested_interval: Literal["5m", "15m"],
) -> tuple[Candle, ...]:
    """Return only parser-issued, closed candles from one bounded snapshot response."""
    _bound_evidence(raw_text, evidence, "candleSnapshot")
    if requested_interval not in INTERVAL_MILLISECONDS:
        raise MarketDataError("unsupported candle snapshot interval")
    payload = _strict_json(raw_text)
    if type(payload) is not list or not payload:
        raise MarketDataError("candle snapshot must be a non-empty JSON array")
    if len(payload) > SNAPSHOT_LIMITS[requested_interval]:
        raise MarketDataError("snapshot exceeds its bounded recovery limit")
    parsed = tuple(
        _candle_from_public_object(
            item,
            evidence=evidence,
            requested_interval=requested_interval,
        )
        for item in payload
    )
    opens = [item.open_time_ms for item in parsed]
    if opens != sorted(opens) or len(set(opens)) != len(opens):
        raise MarketDataError("snapshot candle identities must be strictly increasing")
    closed = tuple(
        item for item in parsed if item.close_time_ms < int(evidence.received_at.timestamp() * 1000)
    )
    width = INTERVAL_MILLISECONDS[requested_interval]
    if any(right.open_time_ms - left.open_time_ms != width for left, right in pairwise(closed)):
        raise MarketDataError("snapshot closed candles are non-contiguous")
    return tuple(_issue(item, _candle_fingerprint(item)) for item in closed)


def candle_from_websocket(raw_text: str, evidence: RawEvidence) -> Candle:
    _bound_evidence(raw_text, evidence, "WebSocket")
    message = _strict_object(raw_text)
    if message.get("channel") != "candle" or type(message.get("data")) is not dict:
        raise MarketDataError("expected a candle WebSocket envelope")
    return _issue_closed_candle(_candle_from_public_object(message["data"], evidence=evidence))


def context_from_websocket(raw_text: str, evidence: RawEvidence) -> ActiveAssetContext:
    _bound_evidence(raw_text, evidence, "WebSocket")
    message = _strict_object(raw_text)
    if message.get("channel") != "activeAssetCtx" or type(message.get("data")) is not dict:
        raise MarketDataError("expected an activeAssetCtx WebSocket envelope")
    data = message["data"]
    context = data.get("ctx") if type(data.get("ctx")) is dict else data
    if data.get("coin") != ETH:
        raise MarketDataError("asset context is not ETH")
    mid = context.get("midPx")
    source_time = context.get("time")
    context_value = ActiveAssetContext(
        mark_px=_decimal(context.get("markPx"), "markPx", positive=True),
        mid_px=None if mid is None else _decimal(mid, "midPx", positive=True),
        open_interest=_decimal(context.get("openInterest"), "openInterest", non_negative=True),
        funding=_decimal(context.get("funding"), "funding"),
        source_time_ms=None if source_time is None else _integer(source_time, "context time"),
        evidence=evidence,
    )
    return _issue(context_value, _context_fingerprint(context_value))


def metadata_from_info(raw_text: str, evidence: RawEvidence) -> AssetMetadata:
    _bound_evidence(raw_text, evidence, "metaAndAssetCtxs")
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
    metadata_value = AssetMetadata(sz_decimals=decimals, evidence=evidence)
    return _issue(metadata_value, _metadata_fingerprint(metadata_value))


@dataclass
class EthMarketData:
    """Fail-closed normalized data authority for the First Launch strategy."""

    candles: dict[str, dict[int, Candle]] = field(default_factory=lambda: {"5m": {}, "15m": {}})
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
        candle = _validated_candle(candle)
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
        if any(_validated_candle(candle).interval != interval for candle in recovered):
            raise MarketDataError("snapshot interval does not match its authority")
        for candle in recovered:
            self.accept_candle(candle)

    def accept_context(self, context: ActiveAssetContext) -> None:
        context = _validated_context(context)
        if context.reference_price is None:
            self.invalid_reason = "REFERENCE_PRICE_INVALID"
            return
        self.active_context = context

    def accept_metadata(self, metadata: AssetMetadata) -> None:
        self.metadata = _validated_metadata(metadata)

    def ingest_websocket(
        self,
        raw_text: str,
        *,
        received_at: datetime,
        receive_sequence: int,
        connection_id: str,
    ) -> Literal["ACCEPTED", "DUPLICATE", "CONFLICT", "CONTEXT_ACCEPTED", "IGNORED_OPEN"]:
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
                candle = candle_from_websocket(raw_text, evidence)
                return self.accept_candle(candle)
            if message.get("channel") == "activeAssetCtx":
                self.accept_context(context_from_websocket(raw_text, evidence))
                return "CONTEXT_ACCEPTED"
            raise MarketDataError("WebSocket channel is outside the First Launch authority")
        except OpenCandleIgnored:
            return "IGNORED_OPEN"
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

    @staticmethod
    def _eligible(values: Iterable[Candle], evaluated_at: datetime) -> tuple[Candle, ...]:
        """Return only evidence that existed at the requested decision cutoff."""
        cutoff_ms = int(evaluated_at.timestamp() * 1000)
        return tuple(
            sorted(
                (
                    candle
                    for candle in values
                    if candle.close_time_ms <= cutoff_ms
                    and candle.evidence.received_at <= evaluated_at
                ),
                key=lambda candle: candle.open_time_ms,
            )
        )

    @staticmethod
    def _contiguous_values(values: tuple[Candle, ...], required: int) -> bool:
        if len(values) < required:
            return False
        recent = values[-required:]
        width = INTERVAL_MILLISECONDS[recent[-1].interval]
        return all(
            right.open_time_ms - left.open_time_ms == width for left, right in pairwise(recent)
        )

    def quality(self, evaluated_at: datetime) -> DataQuality:
        now = _utc(evaluated_at)
        candles_5m = self._eligible(self.candles["5m"].values(), now)
        candles_15m = self._eligible(self.candles["15m"].values(), now)
        context = (
            self.active_context
            if self.active_context is not None and self.active_context.evidence.received_at <= now
            else None
        )
        metadata = (
            self.metadata
            if self.metadata is not None and self.metadata.evidence.received_at <= now
            else None
        )
        result: DataQuality
        if self.invalid_reason is not None:
            result = DataQuality(DataQualityState.INVALID, self.invalid_reason)
        elif self.conflicts:
            result = DataQuality(DataQualityState.CONFLICT, "CANDLE_IDENTITY_CONFLICT")
        elif (
            len(candles_5m) >= STRATEGY_WARMUP_5M
            and len(candles_15m) >= STRATEGY_WARMUP_15M
            and (
                not self._contiguous_values(candles_5m, STRATEGY_WARMUP_5M)
                or not self._contiguous_values(candles_15m, STRATEGY_WARMUP_15M)
            )
        ):
            result = DataQuality(DataQualityState.GAP, "CANDLE_SEQUENCE_GAP")
        elif self.disconnected:
            result = DataQuality(DataQualityState.DISCONNECTED, "PUBLIC_CONNECTION_DISCONNECTED")
        elif metadata is None:
            result = DataQuality(
                DataQualityState.METADATA_UNAVAILABLE,
                "ETH_SZ_DECIMALS_UNAVAILABLE",
            )
        elif not self._contiguous_values(
            candles_5m, STRATEGY_WARMUP_5M
        ) or not self._contiguous_values(candles_15m, STRATEGY_WARMUP_15M):
            result = DataQuality(DataQualityState.WARMING, "INSUFFICIENT_CLOSED_CANDLES")
        elif context is None:
            result = DataQuality(DataQualityState.WARMING, "ACTIVE_ASSET_CONTEXT_UNAVAILABLE")
        else:
            latest_5m = candles_5m[-1]
            latest_15m = candles_15m[-1]
            if now - context.evidence.received_at > timedelta(seconds=15):
                result = DataQuality(DataQualityState.STALE, "ACTIVE_ASSET_CONTEXT_STALE")
            elif now.timestamp() * 1000 - latest_5m.close_time_ms > 390_000:
                result = DataQuality(DataQualityState.STALE, "CANDLE_5M_STALE")
            elif now.timestamp() * 1000 - latest_15m.close_time_ms > 990_000:
                result = DataQuality(DataQualityState.STALE, "CANDLE_15M_STALE")
            elif now - metadata.evidence.received_at > timedelta(hours=24):
                result = DataQuality(DataQualityState.STALE, "METADATA_STALE")
            else:
                result = DataQuality(DataQualityState.READY, "ALL_REQUIRED_INPUTS_FRESH")
        if not self.transitions or self.transitions[-1] != result:
            self.transitions.append(result)
        return result

    def strategy_snapshot(self, evaluated_at: datetime) -> StrategySnapshot:
        """Freeze the only strategy input that this market authority can issue."""
        now = _utc(evaluated_at)
        candles_5m = self._eligible(self.candles["5m"].values(), now)
        candles_15m = self._eligible(self.candles["15m"].values(), now)
        for candle in (*candles_5m, *candles_15m):
            _validated_candle(candle)
        context = (
            self.active_context
            if self.active_context is not None and self.active_context.evidence.received_at <= now
            else None
        )
        metadata = (
            self.metadata
            if self.metadata is not None and self.metadata.evidence.received_at <= now
            else None
        )
        if context is not None:
            _validated_context(context)
        if metadata is not None:
            _validated_metadata(metadata)
        snapshot = StrategySnapshot(
            candles_5m=candles_5m,
            candles_15m=candles_15m,
            evaluated_at=now,
            quality=self.quality(now),
            active_context=context,
            metadata=metadata,
        )
        return _issue(snapshot, _snapshot_fingerprint(snapshot))


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
        if self.healthy_since is not None and _utc(now) - self.healthy_since >= timedelta(
            minutes=5
        ):
            self.attempt_count = 0
