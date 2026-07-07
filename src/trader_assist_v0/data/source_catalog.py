from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Literal

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

SOURCE_CATALOG_VERSION: Final = "hyperliquid-public-mainnet.0.1.0"
SOURCE_ID: Final = "hyperliquid-public-mainnet"
OFFICIALLY_VERIFIED_DATE: Final = "2026-07-07"
RATE_LIMIT_STATUS: Final = "UNRESOLVED_OFFICIAL_LIMIT"
RATE_LIMIT_OFFICIAL_SOURCE_TITLE: Final = "Rate limits and user limits"
RATE_LIMIT_OFFICIAL_SOURCE_LOCATION: Final = (
    "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
    "rate-limits-and-user-limits"
)
ALLOWED_COINS: Final = ("BTC", "ETH")
RUNTIME_CANDLE_INTERVALS: Final = ("1m", "3m", "5m", "15m", "1h")
DOCUMENTED_CANDLE_INTERVALS: Final = (
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
)


@dataclass(frozen=True)
class SourceCatalogEntry:
    catalog_version: str
    source_id: str
    endpoint_id: str
    operation_type: str
    allowed_instruments: tuple[str, ...]
    allowed_candle_intervals: tuple[str, ...]
    documented_candle_intervals: tuple[str, ...]
    request_shape: str
    response_envelope: str
    source_timestamp_availability: str
    timestamp_unit: str
    semantics: str
    documented_sequence_availability: str
    native_identity_fields: tuple[str, ...]
    recovery_capability: str
    known_limitations: tuple[str, ...]
    official_source_title: str
    official_source_location: str
    officially_verified_date: str


_WS_DOC = (
    "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/"
    "subscriptions"
)
_INFO_DOC = "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint"


def _entry(
    endpoint_id: str,
    operation_type: str,
    request_shape: str,
    response_envelope: str,
    source_timestamp_availability: str,
    timestamp_unit: str,
    semantics: str,
    native_identity_fields: tuple[str, ...],
    recovery_capability: str,
    known_limitations: tuple[str, ...],
    official_source_title: str,
    official_source_location: str,
    *,
    candle: bool = False,
) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        catalog_version=SOURCE_CATALOG_VERSION,
        source_id=SOURCE_ID,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        allowed_instruments=ALLOWED_COINS,
        allowed_candle_intervals=RUNTIME_CANDLE_INTERVALS if candle else (),
        documented_candle_intervals=DOCUMENTED_CANDLE_INTERVALS if candle else (),
        request_shape=request_shape,
        response_envelope=response_envelope,
        source_timestamp_availability=source_timestamp_availability,
        timestamp_unit=timestamp_unit,
        semantics=semantics,
        documented_sequence_availability="NONE",
        native_identity_fields=native_identity_fields,
        recovery_capability=recovery_capability,
        known_limitations=known_limitations,
        official_source_title=official_source_title,
        official_source_location=official_source_location,
        officially_verified_date=OFFICIALLY_VERIFIED_DATE,
    )


ENTRIES: Final = (
    _entry(
        "hl-ws-mainnet-public",
        "trades",
        '{"method":"subscribe","subscription":{"type":"trades","coin":"<ETH|BTC>"}}',
        '{"channel":"trades","data":"WsTrade[]"}',
        "FIELD_TIME",
        "MILLISECONDS",
        "BATCHED_STREAM",
        ("time", "coin", "tid"),
        "NO_DOCUMENTED_COMPLETE_PUBLIC_HISTORY_RECOVERY",
        ("no documented source sequence", "reconnect continuity cannot be proven from local order"),
        "WebSocket Subscriptions",
        _WS_DOC,
    ),
    _entry(
        "hl-ws-mainnet-public",
        "l2Book",
        '{"method":"subscribe","subscription":{"type":"l2Book","coin":"<ETH|BTC>"}}',
        '{"channel":"l2Book","data":"WsBook"}',
        "FIELD_TIME",
        "MILLISECONDS",
        "FULL_SNAPSHOT_NOT_DELTA",
        ("coin", "time"),
        "CURRENT_SNAPSHOT_VIA_INFO_L2BOOK",
        ("no documented source sequence", "current snapshot cannot restore intermediate books"),
        "WebSocket Subscriptions",
        _WS_DOC,
    ),
    _entry(
        "hl-ws-mainnet-public",
        "bbo",
        '{"method":"subscribe","subscription":{"type":"bbo","coin":"<ETH|BTC>"}}',
        '{"channel":"bbo","data":"WsBbo"}',
        "FIELD_TIME",
        "MILLISECONDS",
        "CHANGE_ONLY_STREAM",
        ("coin", "time"),
        "CURRENT_STATE_CROSS_CHECK_ONLY",
        ("no documented source sequence", "silence does not imply disconnection"),
        "WebSocket Subscriptions",
        _WS_DOC,
    ),
    _entry(
        "hl-ws-mainnet-public",
        "activeAssetCtx",
        '{"method":"subscribe","subscription":{"type":"activeAssetCtx","coin":"<ETH|BTC>"}}',
        '{"channel":"activeAssetCtx","data":"WsActiveAssetCtx"}',
        "NONE",
        "NONE",
        "CURRENT_OBSERVATION",
        ("coin",),
        "CURRENT_CONTEXT_VIA_META_AND_ASSET_CONTEXTS",
        ("no documented source timestamp", "no documented source sequence"),
        "WebSocket Subscriptions",
        _WS_DOC,
    ),
    _entry(
        "hl-ws-mainnet-public",
        "allMids",
        '{"method":"subscribe","subscription":{"type":"allMids"}}',
        '{"channel":"allMids","data":"AllMids"}',
        "NONE",
        "NONE",
        "CURRENT_MAP_OBSERVATION",
        (),
        "CURRENT_MAP_VIA_INFO_ALL_MIDS",
        ("no documented source timestamp", "no documented source sequence"),
        "WebSocket Subscriptions",
        _WS_DOC,
    ),
    _entry(
        "hl-ws-mainnet-public",
        "candle",
        (
            '{"method":"subscribe","subscription":{"type":"candle",'
            '"coin":"<ETH|BTC>","interval":"<allowed>"}}'
        ),
        '{"channel":"candle","data":"Candle[]"}',
        "BAR_OPEN_AND_CLOSE_FIELDS",
        "MILLISECONDS",
        "MUTABLE_CURRENT_BAR_REVISION_CAPABLE",
        ("coin", "interval", "open_time"),
        "TIME_RANGE_BACKFILL_VIA_CANDLE_SNAPSHOT",
        (
            "logical key is coin plus interval plus open time",
            "runtime enables only the bounded interval allowlist",
        ),
        "WebSocket Subscriptions",
        _WS_DOC,
        candle=True,
    ),
    _entry(
        "hl-info-mainnet-public",
        "meta",
        '{"type":"meta"}',
        "PerpMeta",
        "NONE",
        "NONE",
        "CURRENT_METADATA_SNAPSHOT",
        ("universe_index", "name"),
        "REQUERY_CURRENT_METADATA",
        ("no historical metadata sequence",),
        "Info endpoint",
        _INFO_DOC,
    ),
    _entry(
        "hl-info-mainnet-public",
        "metaAndAssetCtxs",
        '{"type":"metaAndAssetCtxs"}',
        "[PerpMeta,PerpsAssetCtx[]]",
        "NONE",
        "NONE",
        "CURRENT_METADATA_AND_CONTEXT_SNAPSHOT",
        ("universe_index", "name"),
        "REQUERY_CURRENT_METADATA_AND_CONTEXT",
        ("no historical context sequence",),
        "Info endpoint",
        _INFO_DOC,
    ),
    _entry(
        "hl-info-mainnet-public",
        "allMids",
        '{"type":"allMids"}',
        "Record<string,string>",
        "NONE",
        "NONE",
        "CURRENT_MAP_SNAPSHOT",
        (),
        "REQUERY_CURRENT_MAP",
        ("empty books may use last trade price",),
        "Info endpoint",
        _INFO_DOC,
    ),
    _entry(
        "hl-info-mainnet-public",
        "l2Book",
        '{"type":"l2Book","coin":"<ETH|BTC>"}',
        "WsBook",
        "FIELD_TIME",
        "MILLISECONDS",
        "CURRENT_FULL_SNAPSHOT",
        ("coin", "time"),
        "REQUERY_CURRENT_SNAPSHOT",
        ("does not restore intermediate book history",),
        "Info endpoint",
        _INFO_DOC,
    ),
    _entry(
        "hl-info-mainnet-public",
        "candleSnapshot",
        (
            '{"type":"candleSnapshot","req":{"coin":"<ETH|BTC>",'
            '"interval":"<allowed>","startTime":"<ms>","endTime":"<ms>"}}'
        ),
        "Candle[]",
        "BAR_OPEN_AND_CLOSE_FIELDS",
        "MILLISECONDS",
        "TIME_RANGE_SNAPSHOT",
        ("coin", "interval", "open_time"),
        "PAGINATED_TIME_RANGE_BACKFILL",
        ("official retention and response limits apply",),
        "Info endpoint",
        _INFO_DOC,
        candle=True,
    ),
    _entry(
        "hl-info-mainnet-public",
        "fundingHistory",
        '{"type":"fundingHistory","coin":"<ETH|BTC>","startTime":"<ms>"}',
        "FundingHistory[]",
        "FIELD_TIME",
        "MILLISECONDS",
        "TIME_RANGE_SNAPSHOT",
        ("coin", "time"),
        "PAGINATED_TIME_RANGE_BACKFILL",
        ("official retention and response limits apply",),
        "Info endpoint",
        _INFO_DOC,
    ),
    _entry(
        "hl-info-mainnet-public",
        "predictedFundings",
        '{"type":"predictedFundings"}',
        "PredictedFunding[]",
        "SOURCE_DEFINED",
        "MILLISECONDS_WHERE_PRESENT",
        "CURRENT_PREDICTION_SNAPSHOT",
        ("venue", "coin"),
        "REQUERY_CURRENT_PREDICTIONS",
        ("prediction values may change",),
        "Info endpoint",
        _INFO_DOC,
    ),
)

ENTRY_BY_KEY: Final = {(entry.endpoint_id, entry.operation_type): entry for entry in ENTRIES}


def source_catalog_document() -> dict[str, object]:
    return {
        "catalog_version": SOURCE_CATALOG_VERSION,
        "source_id": SOURCE_ID,
        "venue": "Hyperliquid",
        "environment": "mainnet public read-only",
        "allowed_coins": list(ALLOWED_COINS),
        "runtime_candle_intervals": list(RUNTIME_CANDLE_INTERVALS),
        "documented_candle_intervals": list(DOCUMENTED_CANDLE_INTERVALS),
        "rate_limit_status": RATE_LIMIT_STATUS,
        "rate_limit_official_source_title": RATE_LIMIT_OFFICIAL_SOURCE_TITLE,
        "rate_limit_official_source_location": RATE_LIMIT_OFFICIAL_SOURCE_LOCATION,
        "rate_limit_verified_date": OFFICIALLY_VERIFIED_DATE,
        "entries": [asdict(entry) for entry in ENTRIES],
    }


def source_catalog_hash() -> str:
    material = canonical_json_bytes(source_catalog_document())
    return sha256_hex(b"trader-assist-v0/source-catalog/v1\0" + material)


SOURCE_CATALOG_HASH: Final = source_catalog_hash()


def get_entry(endpoint_id: str, operation_type: str) -> SourceCatalogEntry:
    try:
        return ENTRY_BY_KEY[(endpoint_id, operation_type)]
    except KeyError as exc:
        raise ValueError("unsupported source endpoint or operation") from exc


def validate_public_selection(
    endpoint_id: str,
    operation_type: str,
    *,
    coin: str | None = None,
    interval: str | None = None,
) -> SourceCatalogEntry:
    entry = get_entry(endpoint_id, operation_type)
    if coin is not None and coin not in entry.allowed_instruments:
        raise ValueError("unsupported instrument")
    if operation_type not in {"allMids", "meta", "metaAndAssetCtxs", "predictedFundings"}:
        if coin is None:
            raise ValueError("coin is required for this source operation")
    if operation_type in {"candle", "candleSnapshot"}:
        if interval not in entry.allowed_candle_intervals:
            raise ValueError("unsupported candle interval")
    elif interval is not None:
        raise ValueError("interval is only valid for candle operations")
    return entry


def endpoint_kind(endpoint_id: str) -> Literal["WEBSOCKET", "INFO"]:
    if endpoint_id == "hl-ws-mainnet-public":
        return "WEBSOCKET"
    if endpoint_id == "hl-info-mainnet-public":
        return "INFO"
    raise ValueError("unsupported endpoint")
