from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Final, Literal

from .common import canonical_json_bytes, sha256_hex

SOURCE_CATALOG_VERSION: Final = "hyperliquid-public-mainnet.0.1.0"
SOURCE_ID: Final = "hyperliquid-public-mainnet"
OFFICIALLY_VERIFIED_DATE: Final = "2026-07-07"
RATE_LIMIT_STATUS: Final = "UNRESOLVED_OFFICIAL_LIMIT"
RATE_LIMIT_OFFICIAL_SOURCE_TITLE: Final = "Rate limits and user limits"
RATE_LIMIT_OFFICIAL_SOURCE_LOCATION: Final = (
    "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
    "rate-limits-and-user-limits"
)
ALLOWED_COINS: Final[tuple[str, ...]] = ("BTC", "ETH")
RUNTIME_CANDLE_INTERVALS: Final[tuple[str, ...]] = ("1m", "3m", "5m", "15m", "1h")
DOCUMENTED_CANDLE_INTERVALS: Final[tuple[str, ...]] = (
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h",
    "1d", "3d", "1w", "1M",
)

A1_CONTRACT_ID: Final = "V0-01A1-SCOPE-FREEZE"
A3_CONTRACT_ID: Final = "V0-01A3-PUBLIC-READONLY-TRANSPORT-PREFLIGHT-CONTRACT"
PUBLIC_READ_ONLY_ENVIRONMENT: Final = "mainnet public read-only"
PUBLIC_READ_ONLY_OPERATION_CLASS: Final = "public read-only observation only"
CANDLE_WS_ACCEPTED_ENVELOPE_SHAPES: Final[tuple[str, ...]] = ("data:Candle", "data:Candle[]")
CANDLE_WS_POLICY_NOTE: Final = (
    "A1 freezes accepted public envelope policy and fixture shape only; it does not "
    "authorize or implement any live WebSocket client."
)
A1_ALLOWED_CAPTURE_MODES: Final[tuple[str, ...]] = (
    "WS_TEXT_UTF8_APPLICATION_PAYLOAD",
    "HTTP_RESPONSE_BODY",
)
_A1_PROHIBITED_TRANSPORT_MARKERS: Final[tuple[str, ...]] = (
    "private",
    "user",
    "account",
    "wallet",
    "sign",
    "nonce",
    "order",
    "exchange",
)
A3_PREFLIGHT_CREDENTIAL_MARKERS: Final[tuple[str, ...]] = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)
A3_PREFLIGHT_ACCOUNT_MARKERS: Final[tuple[str, ...]] = (
    "account",
    "account_address",
    "address",
    "private",
    "signature",
    "signing",
    "user",
    "wallet",
    "nonce",
)
A3_PREFLIGHT_WRITE_MARKERS: Final[tuple[str, ...]] = (
    "/exchange",
    "exchange",
    "open_orders",
    "openorders",
    "order",
    "order_updates",
    "orderupdates",
    "user_events",
    "userevents",
    "user_fills",
    "userfills",
    "user_fundings",
    "userfundings",
)
A3_PREFLIGHT_EXECUTION_MARKERS: Final[tuple[str, ...]] = (
    "execution",
    "execution_enablement",
    "mainnet_execution",
    "order_mutation",
    "testnet",
)
A3_PREFLIGHT_KILL_SWITCH_BYPASS_MARKERS: Final[tuple[str, ...]] = (
    "bypass",
    "disable_kill_switch",
    "disabled_kill_switch",
    "kill_switch_bypass",
    "kill_switch_override",
    "override",
)
FIXTURE_ALLOWED_PROVENANCE: Final[tuple[str, ...]] = (
    "SYNTHETIC_DOCUMENTATION_DERIVED",
    "MINIMAL_REDACTED_EXAMPLE",
)
_FIXTURE_FORBIDDEN_MARKERS: Final[tuple[str, ...]] = (
    "api_key",
    "apikey",
    "secret",
    "credential",
    "private_key",
    "signature",
    "nonce",
    "wallet",
    "account",
    "database",
    "cache",
    "raw_operational",
)
_FIXTURE_FORBIDDEN_WORD_RE: Final = re.compile(
    r"(?<![a-z0-9_])"
    r"(?:address|authorization|bearer|db|log|logs|password|token)"
    r"(?![a-z0-9_])"
)
_FIXTURE_ADDRESS_RE: Final = re.compile(r"\b0x[0-9a-fA-F]{40}\b")

EndpointKind = Literal["WEBSOCKET", "INFO"]
DocumentationStatus = Literal["VERIFIED", "AMBIGUOUS_DOCUMENTATION"]


@dataclass(frozen=True)
class SourceCatalogEntry:
    catalog_version: str
    source_id: str
    endpoint_id: str
    endpoint_kind: EndpointKind
    operation_type: str
    coin_required: bool
    allowed_instruments: tuple[str, ...]
    allowed_candle_intervals: tuple[str, ...]
    documented_candle_intervals: tuple[str, ...]
    request_shape: str
    response_envelope: str
    documentation_status: DocumentationStatus
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
    endpoint_kind: EndpointKind,
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
    coin_required: bool,
    candle: bool = False,
    documentation_status: DocumentationStatus = "VERIFIED",
) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        catalog_version=SOURCE_CATALOG_VERSION,
        source_id=SOURCE_ID,
        endpoint_id=endpoint_id,
        endpoint_kind=endpoint_kind,
        operation_type=operation_type,
        coin_required=coin_required,
        allowed_instruments=ALLOWED_COINS if coin_required else (),
        allowed_candle_intervals=RUNTIME_CANDLE_INTERVALS if candle else (),
        documented_candle_intervals=DOCUMENTED_CANDLE_INTERVALS if candle else (),
        request_shape=request_shape,
        response_envelope=response_envelope,
        documentation_status=documentation_status,
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


ENTRIES: Final[tuple[SourceCatalogEntry, ...]] = (
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "trades",
        '{"method":"subscribe","subscription":{"type":"trades","coin":"<ETH|BTC>"}}',
        '{"channel":"trades","data":"WsTrade[]"}',
        "FIELD_TIME", "MILLISECONDS", "BATCHED_STREAM", ("time", "coin", "tid"),
        "NO_DOCUMENTED_COMPLETE_PUBLIC_HISTORY_RECOVERY",
        ("no documented source sequence", "reconnect continuity cannot be proven"),
        "WebSocket Subscriptions", _WS_DOC, coin_required=True,
    ),
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "l2Book",
        '{"method":"subscribe","subscription":{"type":"l2Book","coin":"<ETH|BTC>"}}',
        '{"channel":"l2Book","data":"WsBook"}',
        "FIELD_TIME", "MILLISECONDS", "FULL_SNAPSHOT_NOT_DELTA", ("coin", "time"),
        "CURRENT_SNAPSHOT_VIA_INFO_L2BOOK",
        ("no documented source sequence", "current snapshot cannot restore intermediate books"),
        "WebSocket Subscriptions", _WS_DOC, coin_required=True,
    ),
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "bbo",
        '{"method":"subscribe","subscription":{"type":"bbo","coin":"<ETH|BTC>"}}',
        '{"channel":"bbo","data":"WsBbo"}',
        "FIELD_TIME", "MILLISECONDS", "CHANGE_ONLY_STREAM", ("coin", "time"),
        "CURRENT_STATE_CROSS_CHECK_ONLY",
        ("no documented source sequence", "silence does not imply disconnection"),
        "WebSocket Subscriptions", _WS_DOC, coin_required=True,
    ),
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "activeAssetCtx",
        '{"method":"subscribe","subscription":{"type":"activeAssetCtx","coin":"<ETH|BTC>"}}',
        '{"channel":"activeAssetCtx","data":"WsActiveAssetCtx"}',
        "NONE", "NONE", "CURRENT_OBSERVATION", ("coin",),
        "CURRENT_CONTEXT_VIA_META_AND_ASSET_CONTEXTS",
        ("no documented source timestamp", "no documented source sequence"),
        "WebSocket Subscriptions", _WS_DOC, coin_required=True,
    ),
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "allMids",
        '{"method":"subscribe","subscription":{"type":"allMids"}}',
        '{"channel":"allMids","data":"AllMids"}',
        "NONE", "NONE", "CURRENT_MAP_OBSERVATION", (), "CURRENT_MAP_VIA_INFO_ALL_MIDS",
        ("no documented source timestamp", "no documented source sequence"),
        "WebSocket Subscriptions", _WS_DOC, coin_required=False,
    ),
    _entry(
        "hl-ws-mainnet-public", "WEBSOCKET", "candle",
        (
            '{"method":"subscribe","subscription":{"type":"candle",'
            '"coin":"<ETH|BTC>","interval":"<allowed>"}}'
        ),
        '{"channel":"candle","data":"Candle or Candle[]; official documentation differs"}',
        "BAR_OPEN_AND_CLOSE_FIELDS", "MILLISECONDS", "MUTABLE_CURRENT_BAR_REVISION_CAPABLE",
        ("coin", "interval", "open_time"), "TIME_RANGE_BACKFILL_VIA_CANDLE_SNAPSHOT",
        (
            "logical key is coin plus interval plus open time",
            "runtime enables only the bounded interval allowlist",
            "actual data envelope must be fixture-verified before public transport is authorized",
        ),
        "WebSocket Subscriptions", _WS_DOC, coin_required=True, candle=True,
        documentation_status="AMBIGUOUS_DOCUMENTATION",
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "meta", '{"type":"meta"}', "PerpMeta",
        "NONE", "NONE", "CURRENT_METADATA_SNAPSHOT", ("universe_index", "name"),
        "REQUERY_CURRENT_METADATA", ("no historical metadata sequence",),
        "Info endpoint", _INFO_DOC, coin_required=False,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "metaAndAssetCtxs", '{"type":"metaAndAssetCtxs"}',
        "[PerpMeta,PerpsAssetCtx[]]", "NONE", "NONE",
        "CURRENT_METADATA_AND_CONTEXT_SNAPSHOT", ("universe_index", "name"),
        "REQUERY_CURRENT_METADATA_AND_CONTEXT", ("no historical context sequence",),
        "Info endpoint", _INFO_DOC, coin_required=False,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "allMids", '{"type":"allMids"}',
        "Record<string,string>", "NONE", "NONE", "CURRENT_MAP_SNAPSHOT", (),
        "REQUERY_CURRENT_MAP", ("empty books may use last trade price",),
        "Info endpoint", _INFO_DOC, coin_required=False,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "l2Book",
        '{"type":"l2Book","coin":"<ETH|BTC>"}', "WsBook", "FIELD_TIME", "MILLISECONDS",
        "CURRENT_FULL_SNAPSHOT", ("coin", "time"), "REQUERY_CURRENT_SNAPSHOT",
        ("does not restore intermediate book history",),
        "Info endpoint", _INFO_DOC, coin_required=True,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "candleSnapshot",
        (
            '{"type":"candleSnapshot","req":{"coin":"<ETH|BTC>",'
            '"interval":"<allowed>","startTime":"<ms>","endTime":"<ms>"}}'
        ),
        "Candle[]", "BAR_OPEN_AND_CLOSE_FIELDS", "MILLISECONDS", "TIME_RANGE_SNAPSHOT",
        ("coin", "interval", "open_time"), "PAGINATED_TIME_RANGE_BACKFILL",
        ("official retention and response limits apply",),
        "Info endpoint", _INFO_DOC, coin_required=True, candle=True,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "fundingHistory",
        '{"type":"fundingHistory","coin":"<ETH|BTC>","startTime":"<ms>"}',
        "FundingHistory[]", "FIELD_TIME", "MILLISECONDS", "TIME_RANGE_SNAPSHOT",
        ("coin", "time"), "PAGINATED_TIME_RANGE_BACKFILL",
        ("official retention and response limits apply",),
        "Info endpoint", _INFO_DOC, coin_required=True,
    ),
    _entry(
        "hl-info-mainnet-public", "INFO", "predictedFundings",
        '{"type":"predictedFundings"}', "PredictedFunding[]", "SOURCE_DEFINED",
        "MILLISECONDS_WHERE_PRESENT", "CURRENT_PREDICTION_SNAPSHOT", ("venue", "coin"),
        "REQUERY_CURRENT_PREDICTIONS", ("prediction values may change",),
        "Info endpoint", _INFO_DOC, coin_required=False,
    ),
)

ENTRY_BY_KEY: Final[dict[tuple[str, str], SourceCatalogEntry]] = {
    (entry.endpoint_id, entry.operation_type): entry for entry in ENTRIES
}
if len(ENTRY_BY_KEY) != len(ENTRIES):
    raise RuntimeError("source catalog entry keys must be unique")


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
    return sha256_hex(
        b"trader-assist-v0/source-catalog/v1\0" + canonical_json_bytes(source_catalog_document())
    )


SOURCE_CATALOG_HASH: Final = source_catalog_hash()
CATALOG_ENTRY_HASH_VERSION: Final = "trader-assist-v0/source-catalog-entry/v1"


def catalog_entry_hash(entry: SourceCatalogEntry) -> str:
    return sha256_hex(
        CATALOG_ENTRY_HASH_VERSION.encode() + b"\0" + canonical_json_bytes(asdict(entry))
    )


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
    if entry.coin_required:
        if coin is None:
            raise ValueError("coin is required for this source operation")
        if coin not in entry.allowed_instruments:
            raise ValueError("unsupported instrument")
    elif coin is not None:
        raise ValueError("coin is not valid for this source operation")
    if entry.allowed_candle_intervals:
        if interval not in entry.allowed_candle_intervals:
            raise ValueError("unsupported candle interval")
    elif interval is not None:
        raise ValueError("interval is only valid for candle operations")
    return entry


def endpoint_kind(endpoint_id: str) -> EndpointKind:
    kinds: set[EndpointKind] = {entry.endpoint_kind for entry in ENTRIES if entry.endpoint_id == endpoint_id}
    if len(kinds) != 1:
        raise ValueError("unsupported or ambiguous endpoint")
    return next(iter(kinds))


def validate_candle_websocket_envelope_shape(envelope_shape: str) -> str:
    if envelope_shape not in CANDLE_WS_ACCEPTED_ENVELOPE_SHAPES:
        raise ValueError("unsupported candle websocket envelope shape")
    return envelope_shape


def rate_limit_entry_gate() -> dict[str, object]:
    numeric_limits_resolved = RATE_LIMIT_STATUS != "UNRESOLVED_OFFICIAL_LIMIT"
    return {
        "task_id": A1_CONTRACT_ID,
        "status": RATE_LIMIT_STATUS,
        "official_source_title": RATE_LIMIT_OFFICIAL_SOURCE_TITLE,
        "official_source_location": RATE_LIMIT_OFFICIAL_SOURCE_LOCATION,
        "numeric_limits_resolved": numeric_limits_resolved,
        "live_transport_authorized": numeric_limits_resolved,
    }


def assert_rate_limit_allows_live_transport() -> None:
    if RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT":
        raise ValueError(
            "official numeric rate limit is unresolved; live transport remains blocked"
        )


def _reject_prohibited_transport_text(*values: str) -> None:
    candidate = " ".join(values).lower()
    if any(marker in candidate for marker in _A1_PROHIBITED_TRANSPORT_MARKERS):
        raise ValueError("prohibited transport endpoint class")


def validate_read_only_transport_entry(
    *,
    source_id: str,
    environment: str,
    endpoint_id: str,
    operation_type: str,
    capture_mode: str,
    operation_class: str,
    coin: str | None = None,
    interval: str | None = None,
) -> SourceCatalogEntry:
    if source_id != SOURCE_ID:
        raise ValueError("unsupported source")
    if environment != PUBLIC_READ_ONLY_ENVIRONMENT:
        raise ValueError("unsupported public observation environment")
    if operation_class != PUBLIC_READ_ONLY_OPERATION_CLASS:
        raise ValueError("unsupported operation class")
    if capture_mode not in A1_ALLOWED_CAPTURE_MODES:
        raise ValueError("unsupported capture mode")
    _reject_prohibited_transport_text(endpoint_id, operation_type)
    entry = validate_public_selection(
        endpoint_id,
        operation_type,
        coin=coin,
        interval=interval,
    )
    expected_mode = (
        "WS_TEXT_UTF8_APPLICATION_PAYLOAD"
        if entry.endpoint_kind == "WEBSOCKET"
        else "HTTP_RESPONSE_BODY"
    )
    if capture_mode != expected_mode:
        raise ValueError("capture mode does not match source endpoint kind")
    return entry


def _a3_normalized_text(*values: str) -> str:
    return " ".join(values).lower().replace("-", "_")


def _reject_a3_markers(reason: str, markers: tuple[str, ...], *values: str) -> None:
    candidate = _a3_normalized_text(*values)
    if any(marker in candidate for marker in markers):
        raise ValueError(reason)


def validate_public_readonly_transport_preflight(
    *,
    source_id: str,
    environment: str,
    endpoint_id: str,
    operation_type: str,
    capture_mode: str,
    operation_class: str,
    coin: str | None = None,
    interval: str | None = None,
    runtime_enabled: bool | None = None,
    kill_switch_enabled: bool | None = True,
    live_transport_requested: bool = False,
    config_keys: tuple[str, ...] = (),
    config_values: tuple[str, ...] = (),
) -> dict[str, object]:
    if runtime_enabled:
        if RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT":
            raise ValueError("official numeric rate limit unresolved; live runtime blocked")
        raise ValueError("live runtime is outside the A3 preflight contract")
    if live_transport_requested:
        raise ValueError("live transport is not authorized by A3")
    if kill_switch_enabled is False:
        raise ValueError("kill switch must fail closed")

    text_values: tuple[str, ...] = (
        source_id,
        environment,
        endpoint_id,
        operation_type,
        operation_class,
        *config_keys,
        *config_values,
    )
    _reject_a3_markers(
        "kill-switch bypass material is prohibited",
        A3_PREFLIGHT_KILL_SWITCH_BYPASS_MARKERS,
        *text_values,
    )
    _reject_a3_markers(
        "credential-like material is prohibited",
        A3_PREFLIGHT_CREDENTIAL_MARKERS,
        *text_values,
    )
    _reject_a3_markers(
        "private/user/account material is prohibited",
        A3_PREFLIGHT_ACCOUNT_MARKERS,
        *text_values,
    )
    _reject_a3_markers(
        "write or exchange material is prohibited",
        A3_PREFLIGHT_WRITE_MARKERS,
        *text_values,
    )
    _reject_a3_markers(
        "Testnet/Mainnet execution wording is prohibited",
        A3_PREFLIGHT_EXECUTION_MARKERS,
        *text_values,
    )

    entry = validate_read_only_transport_entry(
        source_id=source_id,
        environment=environment,
        endpoint_id=endpoint_id,
        operation_type=operation_type,
        capture_mode=capture_mode,
        operation_class=operation_class,
        coin=coin,
        interval=interval,
    )
    return {
        "task_id": A3_CONTRACT_ID,
        "source_id": source_id,
        "environment": environment,
        "endpoint_id": endpoint_id,
        "operation_type": operation_type,
        "endpoint_kind": entry.endpoint_kind,
        "capture_mode": capture_mode,
        "runtime_enabled": False,
        "kill_switch_enabled": kill_switch_enabled is not False,
        "rate_limit_status": RATE_LIMIT_STATUS,
        "live_transport_authorized": False,
    }


def validate_fixture_admission(
    *,
    provenance: str,
    payload_text: str,
    sanitized: bool,
    raw_operational: bool = False,
    private_or_account_data: bool = False,
    contains_secret: bool = False,
) -> None:
    if provenance not in FIXTURE_ALLOWED_PROVENANCE:
        raise ValueError("unsupported fixture provenance")
    if not sanitized:
        raise ValueError("fixture must be sanitized before admission")
    if raw_operational or private_or_account_data or contains_secret:
        raise ValueError("fixture contains prohibited operational or private material")
    lowered = payload_text.lower()
    if (
        any(marker in lowered for marker in _FIXTURE_FORBIDDEN_MARKERS)
        or _FIXTURE_FORBIDDEN_WORD_RE.search(lowered)
        or _FIXTURE_ADDRESS_RE.search(payload_text)
    ):
        raise ValueError("fixture contains prohibited marker")


def validate_a1_to_a2_gate(
    *,
    a1_pr_merged: bool,
    external_exact_head_review_passed: bool,
    rate_limit_entry_gate_explicit: bool,
    public_source_envelope_contract_frozen: bool,
    new_exact_head_lease_granted: bool,
) -> None:
    if not all(
        (
            a1_pr_merged,
            external_exact_head_review_passed,
            rate_limit_entry_gate_explicit,
            public_source_envelope_contract_frozen,
            new_exact_head_lease_granted,
        )
    ):
        raise ValueError("A2 gate is closed")
