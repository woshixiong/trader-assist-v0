from __future__ import annotations

import hmac
import json
from collections.abc import Mapping, Set
from dataclasses import dataclass
from typing import Any, Literal, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)
from pydantic.config import ExtraValues

from .common import Sha256Hex, canonical_json_bytes, sha256_hex

OFFICIAL_RATE_LIMIT_SCHEMA_VERSION = "0.1.0"
OFFICIAL_RATE_LIMIT_AUTHORITY_VERSION = "trader-assist-v0/official-rate-limit-authority/v1"
OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION = "trader-assist-v0/official-rate-limit-source/v1"
OFFICIAL_RATE_LIMIT_OBSERVATION_HASH_VERSION = "trader-assist-v0/official-rate-limit-observation/v1"
OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION = "trader-assist-v0/official-rate-limit-fact/v1"
OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION = (
    "trader-assist-v0/official-rate-limit-authority-hash/v1"
)
OFFICIAL_RATE_LIMIT_STATUS = "UNRESOLVED_OFFICIAL_LIMIT"


@dataclass(frozen=True, slots=True)
class OfficialRateLimitAuthenticationResult:
    """Immutable proof of one authentication call, not a reusable capability."""

    canonical_json: bytes
    authority_hash: str
    source_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]
    unknown_ids: tuple[str, ...]
    conflict_state: Literal["OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED"]
    supersession_state: Literal["EFFECTIVE_VARIANT_UNDETERMINED"]
    transition_eligible: Literal[False]
    live_transport_authorized: Literal[False]
    account_readonly_runtime_authorized: Literal[False]
    testnet_execution_authorized: Literal[False]
    mainnet_execution_authorized: Literal[False]
    flp1_implementation_authorized: Literal[False]


class _RateLimitAuthorityModel(BaseModel):
    """Untrusted structural container; authentication is a separate raw-material step."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
        allow_inf_nan=False,
    )

    @model_validator(mode="before")
    @classmethod
    def enforce_strict_raw_representation(cls, value: Any) -> Mapping[str, Any]:
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise ValueError(f"expected exact {cls.__name__} authority object")
            value = BaseModel.model_dump(value, mode="python", round_trip=True)
        if not isinstance(value, Mapping):
            raise TypeError("rate-limit authority input must be an exact mapping")
        extras = set(value).difference(cls.model_fields)
        if extras:
            raise ValueError("rate-limit authority input contains extra fields")
        integer_fields = {
            "evidence_length_bytes",
            "numeric_value",
            "window_value",
            "response_divisor_value",
        }
        boolean_fields = {
            "mandatory",
            "blocking",
            "transition_eligible",
            "live_transport_authorized",
            "account_readonly_runtime_authorized",
            "testnet_execution_authorized",
            "mainnet_execution_authorized",
            "flp1_implementation_authorized",
        }
        for field in integer_fields.intersection(value):
            item = value[field]
            if item is not None and type(item) is not int:
                raise TypeError(f"{field} must be an exact integer")
        for field in boolean_fields.intersection(value):
            if type(value[field]) is not bool:
                raise TypeError(f"{field} must be an exact boolean")
        return value

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is not None and strict is not True:
            raise TypeError("rate-limit authority validation is permanently strict")
        if extra not in (None, "forbid"):
            raise TypeError("rate-limit authority validation permanently forbids extras")
        if from_attributes is not None and from_attributes is not False:
            raise TypeError("rate-limit authority validation forbids from_attributes")
        if isinstance(obj, BaseModel):
            if type(obj) is not cls:
                raise ValueError(f"expected exact {cls.__name__} authority object")
            obj = BaseModel.model_dump(obj, mode="python", round_trip=True)
        return super().model_validate(
            obj,
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_json(
        cls,
        json_data: str | bytes | bytearray,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        if strict is not None and strict is not True:
            raise TypeError("rate-limit JSON validation is permanently strict")
        if extra not in (None, "forbid"):
            raise TypeError("rate-limit JSON validation permanently forbids extras")

        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON object key")
                result[key] = value
            return result

        def reject_non_finite(token: str) -> None:
            raise ValueError(f"non-finite JSON number is prohibited: {token}")

        if isinstance(json_data, bytearray):
            json_data = bytes(json_data)
        if isinstance(json_data, bytes):
            json_data = json_data.decode("utf-8", errors="strict")
        if type(json_data) is not str:
            raise TypeError("rate-limit JSON input must be exact text or bytes")
        decoded = json.loads(
            json_data,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )

        def freeze_arrays(value: Any) -> Any:
            if isinstance(value, list):
                return tuple(freeze_arrays(item) for item in value)
            if isinstance(value, dict):
                return {key: freeze_arrays(item) for key, item in value.items()}
            return value

        return cls.model_validate(
            freeze_arrays(decoded),
            strict=True,
            extra="forbid",
            from_attributes=False,
            context=context,
            by_alias=by_alias,
            by_name=by_name,
        )

    @classmethod
    def model_validate_strings(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        extra: ExtraValues | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self:
        raise TypeError("rate-limit authority string validation is unsupported")

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> Self:
        raise TypeError("rate-limit authority models cannot bypass validation")

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        raise TypeError("rate-limit authority models cannot be copied")

    def copy(
        self,
        *,
        include: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        exclude: Set[int] | Set[str] | Mapping[int, Any] | Mapping[str, Any] | None = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        raise TypeError("rate-limit authority models cannot be copied")


class OfficialRateLimitSourceV0(_RateLimitAuthorityModel):
    source_id: StrictStr = Field(min_length=1, max_length=120)
    kind: Literal["OFFICIAL_HYPERLIQUID_DOCUMENTATION"]
    title: StrictStr = Field(min_length=1, max_length=160)
    canonical_location: StrictStr = Field(min_length=1, max_length=500)
    retrieval_observations_utc: tuple[StrictStr, ...] = Field(min_length=1)
    publication_or_last_updated_marker: StrictStr | None
    semantic_locator: StrictStr = Field(min_length=1, max_length=240)
    bound_fact_ids: tuple[StrictStr, ...]
    bound_unknown_ids: tuple[StrictStr, ...]
    semantic_observation: tuple[StrictStr, ...] = Field(min_length=1)
    evidence_hash: Sha256Hex
    evidence_length_bytes: StrictInt = Field(gt=0)
    source_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if type(self) is not OfficialRateLimitSourceV0:
            raise ValueError("expected exact OfficialRateLimitSourceV0 authority object")
        evidence_bytes = canonical_json_bytes(_source_evidence_material(self))
        expected_evidence_hash = sha256_hex(
            OFFICIAL_RATE_LIMIT_OBSERVATION_HASH_VERSION.encode("utf-8") + b"\0" + evidence_bytes
        )
        if self.evidence_length_bytes != len(evidence_bytes):
            raise ValueError("evidence length does not match structured observation")
        if not hmac.compare_digest(self.evidence_hash, expected_evidence_hash):
            raise ValueError("evidence hash does not match structured observation")
        expected_hash = _hash_material(
            OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION,
            _source_hash_material(self),
        )
        if not hmac.compare_digest(self.source_hash, expected_hash):
            raise ValueError("source_hash does not match the structural source container")
        return self


class OfficialRateLimitFactV0(_RateLimitAuthorityModel):
    fact_id: StrictStr = Field(min_length=1, max_length=160)
    category: StrictStr = Field(min_length=1, max_length=80)
    transport: StrictStr = Field(min_length=1, max_length=80)
    endpoint_class: StrictStr = Field(min_length=1, max_length=120)
    operation_allowlist: tuple[StrictStr, ...] = Field(min_length=1)
    scope_kind: StrictStr = Field(min_length=1, max_length=120)
    numeric_value: StrictInt = Field(ge=0)
    value_unit: StrictStr = Field(min_length=1, max_length=80)
    window_value: StrictInt | None = Field(default=None, gt=0)
    window_unit: StrictStr | None = Field(default=None, min_length=1, max_length=80)
    response_divisor_value: StrictInt | None = Field(default=None, gt=0)
    response_divisor_unit: StrictStr | None = Field(default=None, min_length=1, max_length=80)
    formula: StrictStr | None = Field(default=None, min_length=1, max_length=240)
    source_bindings: tuple[StrictStr, ...] = Field(min_length=1)
    fact_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_fact(self) -> Self:
        if type(self) is not OfficialRateLimitFactV0:
            raise ValueError("expected exact OfficialRateLimitFactV0 authority object")
        if (self.window_value is None) != (self.window_unit is None):
            raise ValueError("rate-limit window value and unit must be paired")
        if (self.response_divisor_value is None) != (self.response_divisor_unit is None):
            raise ValueError("response divisor value and unit must be paired")
        if len(set(self.operation_allowlist)) != len(self.operation_allowlist):
            raise ValueError("duplicate operation in rate-limit fact")
        if len(set(self.source_bindings)) != len(self.source_bindings):
            raise ValueError("duplicate source binding in rate-limit fact")
        expected_hash = _hash_material(
            OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION,
            _fact_payload(self),
        )
        if not hmac.compare_digest(self.fact_hash, expected_hash):
            raise ValueError("fact_hash does not match the structural fact container")
        return self


class OfficialRateLimitUnknownV0(_RateLimitAuthorityModel):
    field_id: StrictStr = Field(min_length=1, max_length=160)
    affected_endpoint_class: StrictStr = Field(min_length=1, max_length=120)
    affected_operations: tuple[StrictStr, ...] = Field(min_length=1)
    mandatory: StrictBool
    blocking: StrictBool
    reason: StrictStr = Field(min_length=1, max_length=500)
    evidence: StrictStr = Field(min_length=1, max_length=500)
    resolution_requirement: StrictStr = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_unknown(self) -> Self:
        if type(self) is not OfficialRateLimitUnknownV0:
            raise ValueError("expected exact OfficialRateLimitUnknownV0 authority object")
        if self.mandatory is not True or self.blocking is not True:
            raise ValueError("rate-limit unknowns must be exact mandatory blocking truths")
        return self


class OfficialRateLimitAuthorityV0(_RateLimitAuthorityModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    authority_version: Literal["trader-assist-v0/official-rate-limit-authority/v1"] = (
        "trader-assist-v0/official-rate-limit-authority/v1"
    )
    status: Literal["UNRESOLVED_OFFICIAL_LIMIT"] = "UNRESOLVED_OFFICIAL_LIMIT"
    sources: tuple[OfficialRateLimitSourceV0, ...]
    documented_facts: tuple[OfficialRateLimitFactV0, ...]
    unresolved_fields: tuple[OfficialRateLimitUnknownV0, ...]
    conflict_state: Literal["OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED"] = (
        "OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED"
    )
    supersession_state: Literal["EFFECTIVE_VARIANT_UNDETERMINED"] = (
        "EFFECTIVE_VARIANT_UNDETERMINED"
    )
    transition_eligible: StrictBool = False
    live_transport_authorized: StrictBool = False
    account_readonly_runtime_authorized: StrictBool = False
    testnet_execution_authorized: StrictBool = False
    mainnet_execution_authorized: StrictBool = False
    flp1_implementation_authorized: StrictBool = False
    authority_hash: Sha256Hex

    @model_validator(mode="after")
    def validate_authority(self) -> Self:
        if type(self) is not OfficialRateLimitAuthorityV0:
            raise ValueError("expected exact OfficialRateLimitAuthorityV0 authority object")
        gates = (
            self.transition_eligible,
            self.live_transport_authorized,
            self.account_readonly_runtime_authorized,
            self.testnet_execution_authorized,
            self.mainnet_execution_authorized,
            self.flp1_implementation_authorized,
        )
        if any(type(value) is not bool or value is not False for value in gates):
            raise ValueError("all rate-limit authority gates must be exact false")
        if len({item.source_id for item in self.sources}) != len(self.sources):
            raise ValueError("duplicate source identifier")
        if len({item.fact_id for item in self.documented_facts}) != len(
            self.documented_facts
        ):
            raise ValueError("duplicate fact identifier")
        if len({item.field_id for item in self.unresolved_fields}) != len(
            self.unresolved_fields
        ):
            raise ValueError("duplicate unknown identifier")
        if not self.unresolved_fields or not all(
            item.mandatory and item.blocking for item in self.unresolved_fields
        ):
            raise ValueError("mandatory unknowns must keep rate-limit authority unresolved")
        expected_hash = compute_official_rate_limit_authority_hash(self)
        if not hmac.compare_digest(self.authority_hash, expected_hash):
            raise ValueError("authority_hash does not match canonical authority")
        return self


def _hash_material(domain: str, payload: Mapping[str, object]) -> str:
    return sha256_hex(domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload))


def _source_hash_material(
    source: OfficialRateLimitSourceV0 | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(source, OfficialRateLimitSourceV0):
        payload = BaseModel.model_dump(source, mode="python", round_trip=True)
    else:
        payload = dict(source)
    payload.pop("source_hash", None)
    payload.pop("retrieval_observations_utc", None)
    return payload


def _source_evidence_material(
    source: OfficialRateLimitSourceV0 | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(source, OfficialRateLimitSourceV0):
        payload = BaseModel.model_dump(source, mode="python", round_trip=True)
    else:
        payload = dict(source)
    fields = (
        "source_id",
        "kind",
        "title",
        "canonical_location",
        "publication_or_last_updated_marker",
        "semantic_locator",
        "bound_fact_ids",
        "bound_unknown_ids",
        "semantic_observation",
    )
    return {field: payload[field] for field in fields}


def _fact_payload(fact: OfficialRateLimitFactV0) -> dict[str, object]:
    payload = BaseModel.model_dump(fact, mode="python", round_trip=True)
    payload.pop("fact_hash")
    return payload


RATE_LIMIT_PAGE_SOURCE_ID = "hyperliquid-rate-limits-and-user-limits"
INFO_ENDPOINT_SOURCE_ID = "hyperliquid-info-endpoint"


def _fact(
    fact_id: str,
    category: str,
    transport: str,
    endpoint_class: str,
    operations: tuple[str, ...],
    scope_kind: str,
    value: int,
    unit: str,
    *,
    window: tuple[int, str] | None = None,
    divisor: tuple[int, str] | None = None,
    formula: str | None = None,
    sources: tuple[str, ...] = (RATE_LIMIT_PAGE_SOURCE_ID,),
) -> dict[str, object]:
    return {
        "fact_id": fact_id,
        "category": category,
        "transport": transport,
        "endpoint_class": endpoint_class,
        "operation_allowlist": operations,
        "scope_kind": scope_kind,
        "numeric_value": value,
        "value_unit": unit,
        "window_value": None if window is None else window[0],
        "window_unit": None if window is None else window[1],
        "response_divisor_value": None if divisor is None else divisor[0],
        "response_divisor_unit": None if divisor is None else divisor[1],
        "formula": formula,
        "source_bindings": sources,
    }


_INFO_SOURCES = (RATE_LIMIT_PAGE_SOURCE_ID, INFO_ENDPOINT_SOURCE_ID)
_FACT_SPECS: tuple[dict[str, object], ...] = (
    _fact(
        "ip.rest.aggregate-weight",
        "IP",
        "REST",
        "documented REST API",
        ("*",),
        "per IP address",
        1200,
        "weight",
        window=(1, "minute"),
    ),
    _fact(
        "ip.exchange.batch-weight",
        "IP",
        "REST",
        "exchange API",
        ("all documented exchange actions",),
        "per IP request",
        1,
        "base weight",
        formula="1 + floor(batch_length / 40)",
    ),
    _fact(
        "ip.info.weight-2",
        "IP",
        "REST",
        "info API",
        (
            "l2Book",
            "allMids",
            "clearinghouseState",
            "orderStatus",
            "spotClearinghouseState",
            "exchangeStatus",
        ),
        "per IP request",
        2,
        "weight",
        sources=_INFO_SOURCES,
    ),
    _fact(
        "ip.info.user-role-weight",
        "IP",
        "REST",
        "info API",
        ("userRole",),
        "per IP request",
        60,
        "weight",
        sources=_INFO_SOURCES,
    ),
    _fact(
        "ip.info.default-weight",
        "IP",
        "REST",
        "info API",
        ("all other documented info requests",),
        "per IP request",
        20,
        "weight",
        sources=_INFO_SOURCES,
    ),
    _fact(
        "ip.info.response-item-divisor",
        "IP",
        "REST",
        "info API",
        (
            "recentTrades",
            "historicalOrders",
            "userFills",
            "userFillsByTime",
            "fundingHistory",
            "userFunding",
            "nonUserFundingUpdates",
            "twapHistory",
            "userTwapSliceFills",
            "userTwapSliceFillsByTime",
            "delegatorHistory",
            "delegatorRewards",
            "validatorStats",
        ),
        "per IP response",
        1,
        "additional weight",
        divisor=(20, "response items"),
        sources=_INFO_SOURCES,
    ),
    _fact(
        "ip.info.candle-response-divisor",
        "IP",
        "REST",
        "info API",
        ("candleSnapshot",),
        "per IP response",
        1,
        "additional weight",
        divisor=(60, "response items"),
        sources=_INFO_SOURCES,
    ),
    _fact(
        "ip.explorer.weight",
        "IP",
        "REST",
        "explorer API",
        ("all explorer requests",),
        "per IP request",
        40,
        "weight",
    ),
    _fact(
        "ip.explorer.block-list",
        "IP",
        "REST",
        "explorer API",
        ("blockList",),
        "per IP response",
        1,
        "additional limit unit",
        divisor=(1, "block"),
    ),
    _fact(
        "ip.websocket.subscriptions",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("subscribe",),
        "per IP address",
        1000,
        "subscriptions",
    ),
    _fact(
        "ip.websocket.unique-users",
        "IP",
        "WEBSOCKET",
        "user-specific websocket subscriptions",
        ("subscribe",),
        "per IP address",
        10,
        "unique users",
    ),
    _fact(
        "ip.websocket.messages-sent",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("send message",),
        "per IP address across all connections",
        2000,
        "messages",
        window=(1, "minute"),
    ),
    _fact(
        "ip.websocket.inflight-posts",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("post",),
        "per IP address across all connections",
        100,
        "simultaneous inflight post messages",
    ),
    _fact(
        "ip.evm-json-rpc.requests",
        "IP",
        "JSON-RPC",
        "rpc.hyperliquid.xyz/evm",
        ("all EVM JSON-RPC requests",),
        "per IP address",
        100,
        "requests",
        window=(1, "minute"),
    ),
    _fact(
        "address.volume-request-ratio",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per user; sub-account is separate user",
        1,
        "request",
        divisor=(1, "USDC traded cumulatively since address inception"),
    ),
    _fact(
        "address.initial-buffer",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per address",
        10000,
        "requests",
    ),
    _fact(
        "address.rate-limited-fallback",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per rate-limited address",
        1,
        "request",
        window=(10, "seconds"),
    ),
    _fact(
        "address.cancel-limit-formula",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("cancel",),
        "per address cumulative limit",
        100000,
        "requests",
        formula="min(limit + 100000, limit * 2)",
    ),
    _fact(
        "address.open-order-base-limit",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        1000,
        "open orders",
    ),
    _fact(
        "address.open-order-volume-increment",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        1,
        "additional open order",
        divisor=(5000000, "USDC volume"),
    ),
    _fact(
        "address.open-order-cap",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        5000,
        "open orders",
    ),
    _fact(
        "address.open-order-rejection-threshold",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place reduce-only order", "place trigger order"),
        "per user with other open orders",
        1000,
        "other open orders",
    ),
    _fact(
        "address.high-congestion-maker-share",
        "ADDRESS",
        "ACTION",
        "block space",
        ("all actions",),
        "per address during high congestion",
        2,
        "multiplier of maker share percentage",
    ),
    _fact(
        "batch.ip-count",
        "BATCH",
        "REST",
        "exchange API",
        ("batched orders", "batched cancels"),
        "IP-based rate limiting",
        1,
        "request per batch",
    ),
    _fact(
        "batch.address-count",
        "BATCH",
        "ACTION",
        "exchange API",
        ("batched orders", "batched cancels"),
        "address-based rate limiting",
        1,
        "request per batch item",
        formula="n requests for n orders or cancels",
    ),
)
def _unknown(
    field_id: str,
    reason: str,
    requirement: str,
    *,
    affected_endpoint_class: str = "all documented rate-limited endpoints",
    affected_operations: tuple[str, ...] = ("*",),
    evidence: str = "The frozen official sources do not explicitly specify this semantic.",
) -> dict[str, object]:
    return {
        "field_id": field_id,
        "affected_endpoint_class": affected_endpoint_class,
        "affected_operations": affected_operations,
        "mandatory": True,
        "blocking": True,
        "reason": reason,
        "evidence": evidence,
        "resolution_requirement": requirement,
    }


_UNKNOWN_SPECS: tuple[dict[str, object], ...] = (
    _unknown(
        "burst-semantics",
        "Burst capacity and burst handling are not documented.",
        "An official source must define burst capacity and handling.",
    ),
    _unknown(
        "window-algorithm",
        "Fixed, sliding, and token-bucket window behavior is not documented.",
        "An official source must define the rate-limit window algorithm.",
    ),
    _unknown(
        "window-alignment",
        "The alignment origin for documented windows is not documented.",
        "An official source must define window alignment.",
    ),
    _unknown(
        "partial-response-bucket-rounding",
        "Rounding for partial 20-item and 60-item response buckets is not documented.",
        "An official source must define partial-bucket rounding.",
    ),
    _unknown(
        "http-429-status",
        "HTTP 429 behavior is not documented on the frozen rate-limit page.",
        "An official source must define the HTTP status behavior when limited.",
    ),
    _unknown(
        "error-body",
        "The rate-limit error body is not documented.",
        "An official source must define the rate-limit error body contract.",
    ),
    _unknown(
        "error-headers",
        "Rate-limit response headers are not documented.",
        "An official source must define authoritative rate-limit response headers.",
    ),
    _unknown(
        "retry-after",
        "Retry-After presence, unit, and meaning are not documented.",
        "An official source must define Retry-After behavior or explicitly state "
        "that it is absent.",
    ),
    _unknown(
        "older-block-weight",
        "The official source says older uncached blocks may be weighted more heavily "
        "but gives no exact formula.",
        "An official source must define the exact older-block weight formula.",
    ),
    _unknown(
        "high-congestion-trigger",
        "The activation and deactivation semantics for high congestion are not documented.",
        "An official source must define high-congestion state transitions.",
    ),
    _unknown(
        "websocket-simultaneous-connection-limit",
        "Canonical official page variants conflict on the simultaneous WebSocket "
        "connection limit: one states 10 and another states 100.",
        "An official explicit version, effective marker, or supersession statement must "
        "resolve the simultaneous WebSocket connection limit.",
        affected_endpoint_class="WebSocket connection establishment",
        affected_operations=("connect",),
        evidence=(
            "Observed canonical official variants state maximums of 10 and 100 "
            "simultaneous WebSocket connections, with no independently confirmable "
            "effective-variant marker."
        ),
    ),
    _unknown(
        "websocket-new-connection-or-reconnection-rate",
        "Canonical official page variants conflict on whether a new-connection or "
        "reconnection rate is documented.",
        "An official explicit version, effective marker, or supersession statement must "
        "resolve the new-connection and reconnection rate.",
        affected_endpoint_class="WebSocket connection establishment and reconnection",
        affected_operations=("connect", "reconnect"),
        evidence=(
            "One observed canonical official variant states 30 new WebSocket connections "
            "per minute; another has no documented new-connection or reconnection rate."
        ),
    ),
    _unknown(
        "maker-share-reference-period",
        "Canonical official page variants conflict on the reference period for the "
        "high-congestion maker-share percentage.",
        "An official explicit version, effective marker, or supersession statement must "
        "resolve the maker-share reference period.",
        affected_endpoint_class="high-congestion address block-space limit",
        affected_operations=("all actions",),
        evidence=(
            "One observed canonical official variant refers to previous-day maker share; "
            "another gives no documented maker-share reference period."
        ),
    ),
    _unknown(
        "maker-share-computation-or-update-cadence",
        "Canonical official page variants conflict on whether a maker-share computation "
        "or update cadence is documented.",
        "An official explicit version, effective marker, or supersession statement must "
        "resolve the maker-share computation or update cadence.",
        affected_endpoint_class="high-congestion address block-space limit",
        affected_operations=("all actions",),
        evidence=(
            "One observed canonical official variant states maker share is computed once "
            "per UTC date; another gives no documented computation or update cadence."
        ),
    ),
)
def _source(
    *,
    source_id: str,
    title: str,
    canonical_location: str,
    retrieval_observations_utc: tuple[str, ...],
    publication_or_last_updated_marker: str | None,
    semantic_locator: str,
    bound_fact_ids: tuple[str, ...],
    bound_unknown_ids: tuple[str, ...],
    semantic_observation: tuple[str, ...],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_id": source_id,
        "kind": "OFFICIAL_HYPERLIQUID_DOCUMENTATION",
        "title": title,
        "canonical_location": canonical_location,
        "retrieval_observations_utc": retrieval_observations_utc,
        "publication_or_last_updated_marker": publication_or_last_updated_marker,
        "semantic_locator": semantic_locator,
        "bound_fact_ids": bound_fact_ids,
        "bound_unknown_ids": bound_unknown_ids,
        "semantic_observation": semantic_observation,
    }
    evidence_bytes = canonical_json_bytes(_source_evidence_material(payload))
    payload["evidence_hash"] = sha256_hex(
        OFFICIAL_RATE_LIMIT_OBSERVATION_HASH_VERSION.encode("utf-8") + b"\0" + evidence_bytes
    )
    payload["evidence_length_bytes"] = len(evidence_bytes)
    return payload


_RATE_FACT_IDS = tuple(str(item["fact_id"]) for item in _FACT_SPECS)
_INFO_FACT_IDS = tuple(
    str(item["fact_id"])
    for item in _FACT_SPECS
    if INFO_ENDPOINT_SOURCE_ID in cast(tuple[str, ...], item["source_bindings"])
)
_RATE_UNKNOWN_IDS = tuple(str(item["field_id"]) for item in _UNKNOWN_SPECS)

_SOURCE_SPECS: tuple[dict[str, object], ...] = (
    _source(
        source_id=RATE_LIMIT_PAGE_SOURCE_ID,
        title="Rate limits and user limits",
        canonical_location=(
            "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
            "rate-limits-and-user-limits"
        ),
        retrieval_observations_utc=(
            "2026-07-12T14:34:55Z",
            "2026-07-12T14:35:06Z",
        ),
        publication_or_last_updated_marker=None,
        semantic_locator="Rate limits and user limits / complete page body",
        bound_fact_ids=_RATE_FACT_IDS,
        bound_unknown_ids=_RATE_UNKNOWN_IDS,
        semantic_observation=(
            "REST requests share an aggregated weight limit of 1200 per minute.",
            "Documented exchange requests weigh 1 + floor(batch_length / 40).",
            "l2Book, allMids, clearinghouseState, orderStatus, "
            "spotClearinghouseState, and exchangeStatus Info requests weigh 2.",
            "userRole Info requests weigh 60; all other documented Info requests weigh 20.",
            "The listed Info history operations add weight per 20 response items; "
            "candleSnapshot adds weight per 60 response items.",
            "Explorer requests weigh 40; blockList adds 1 per block, while the exact "
            "additional weight for older uncached blocks is not specified.",
            "The common-subset per-IP WebSocket limits are 1000 subscriptions and 10 "
            "unique users across user-specific subscriptions.",
            "Across all WebSocket connections, at most 2000 messages may be sent per "
            "minute and 100 post messages may be simultaneously inflight.",
            "rpc.hyperliquid.xyz/evm permits 100 EVM JSON-RPC requests per minute per IP.",
            "Address limits apply per user, with sub-accounts treated as separate users.",
            "Address allowance is 1 request per 1 USDC traded cumulatively since "
            "inception, with an initial buffer of 10000 requests and, when limited, "
            "1 request every 10 seconds.",
            "Cancel allowance is min(limit + 100000, limit * 2), and address limits "
            "apply to actions rather than Info requests.",
            "Open-order allowance starts at 1000, adds 1 per 5M USDC volume, and is "
            "capped at 5000; reduce-only or trigger orders are rejected at the stated "
            "1000-other-open-order threshold.",
            "Across observed canonical variants, the common high-congestion semantic is "
            "a 2x multiplier of maker-share percentage.",
            "A batch of n orders or cancels counts as one IP-based request and n "
            "address-based requests.",
            "Burst, window implementation/alignment, partial divisor rounding, "
            "rate-limit HTTP/error/header/Retry-After behavior, exact older-block "
            "weighting, and high-congestion activation remain unspecified.",
            "Observed canonical primary-page variants conflict on simultaneous WebSocket "
            "connections, the new-connection or reconnection rate, the maker-share "
            "reference period, and the maker-share computation or update cadence.",
            "No independently confirmable effective marker or supersession statement "
            "determines which observed canonical variant is effective.",
            "Only common-subset semantics are documented facts; all disputed semantics "
            "are mandatory blocking unknowns.",
        ),
    ),
    _source(
        source_id=INFO_ENDPOINT_SOURCE_ID,
        title="Info endpoint",
        canonical_location=(
            "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint"
        ),
        retrieval_observations_utc=("2026-07-12T14:35:14Z",),
        publication_or_last_updated_marker=None,
        semantic_locator="Info endpoint / operation request-body identities",
        bound_fact_ids=_INFO_FACT_IDS,
        bound_unknown_ids=(),
        semantic_observation=(
            "Info operations are selected by the POST /info request-body type.",
            "The supporting page identifies l2Book, allMids, clearinghouseState, "
            "orderStatus, spotClearinghouseState, exchangeStatus, userRole, "
            "candleSnapshot, and the response-weighted history operation identities.",
            "This supporting source binds operation identity and does not independently "
            "define the numeric rate-limit weights.",
            "This supporting source does not resolve the observed canonical primary-page "
            "variant conflict or determine an effective variant.",
        ),
    ),
)
def official_rate_limit_sources() -> tuple[OfficialRateLimitSourceV0, ...]:
    return tuple(
        OfficialRateLimitSourceV0.model_validate(
            {
                **spec,
                "source_hash": _hash_material(
                    OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION,
                    _source_hash_material(spec),
                ),
            }
        )
        for spec in _SOURCE_SPECS
    )


def official_rate_limit_facts() -> tuple[OfficialRateLimitFactV0, ...]:
    return tuple(
        OfficialRateLimitFactV0.model_validate(
            {
                **spec,
                "fact_hash": _hash_material(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, spec),
            }
        )
        for spec in _FACT_SPECS
    )


def official_rate_limit_unknowns() -> tuple[OfficialRateLimitUnknownV0, ...]:
    return tuple(OfficialRateLimitUnknownV0.model_validate(spec) for spec in _UNKNOWN_SPECS)


def compute_official_rate_limit_authority_hash(
    authority: OfficialRateLimitAuthorityV0,
) -> str:
    if type(authority) is not OfficialRateLimitAuthorityV0:
        raise ValueError("expected exact OfficialRateLimitAuthorityV0 authority object")
    payload = BaseModel.model_dump(authority, mode="python", round_trip=True)
    return _hash_material(
        OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION,
        _authority_hash_material(payload),
    )


def _authority_hash_material(values: Mapping[str, object]) -> dict[str, object]:
    payload = dict(values)
    payload.pop("authority_hash", None)
    sources = []
    for source in cast(tuple[object, ...] | list[object], payload["sources"]):
        if isinstance(source, BaseModel):
            source_payload = BaseModel.model_dump(source, mode="python", round_trip=True)
        else:
            source_payload = dict(cast(Mapping[str, object], source))
        source_payload.pop("retrieval_observations_utc", None)
        sources.append(source_payload)
    payload["sources"] = sources
    return payload


def _authority_hash_from_values(values: Mapping[str, object]) -> str:
    payload = {
        "schema_version": OFFICIAL_RATE_LIMIT_SCHEMA_VERSION,
        "authority_version": OFFICIAL_RATE_LIMIT_AUTHORITY_VERSION,
        "status": OFFICIAL_RATE_LIMIT_STATUS,
        **values,
        "conflict_state": "OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED",
        "supersession_state": "EFFECTIVE_VARIANT_UNDETERMINED",
        "transition_eligible": False,
        "live_transport_authorized": False,
        "account_readonly_runtime_authorized": False,
        "testnet_execution_authorized": False,
        "mainnet_execution_authorized": False,
        "flp1_implementation_authorized": False,
    }
    return _hash_material(
        OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION,
        _authority_hash_material(payload),
    )


def _to_exact_json_primitives(value: object) -> object:
    if type(value) is dict:
        return {
            cast(str, key): _to_exact_json_primitives(item)
            for key, item in cast(dict[object, object], value).items()
        }
    if type(value) is tuple:
        return [_to_exact_json_primitives(item) for item in cast(tuple[object, ...], value)]
    if type(value) in (str, int, bool) or value is None:
        return value
    raise TypeError("official rate-limit specification is not an exact JSON primitive")


def _build_official_rate_limit_authority_mapping() -> dict[str, object]:
    """Build exact repository-owned primitives for the private consumer boundary."""

    sources: list[object] = []
    for spec in _SOURCE_SPECS:
        source = cast(dict[str, object], _to_exact_json_primitives(spec))
        source["source_hash"] = _hash_material(
            OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION,
            _source_hash_material(source),
        )
        sources.append(source)
    facts: list[object] = []
    for spec in _FACT_SPECS:
        fact = cast(dict[str, object], _to_exact_json_primitives(spec))
        fact["fact_hash"] = _hash_material(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, fact)
        facts.append(fact)
    unknowns = [
        cast(dict[str, object], _to_exact_json_primitives(spec))
        for spec in _UNKNOWN_SPECS
    ]
    authority: dict[str, object] = {
        "schema_version": OFFICIAL_RATE_LIMIT_SCHEMA_VERSION,
        "authority_version": OFFICIAL_RATE_LIMIT_AUTHORITY_VERSION,
        "status": OFFICIAL_RATE_LIMIT_STATUS,
        "sources": sources,
        "documented_facts": facts,
        "unresolved_fields": unknowns,
        "conflict_state": "OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED",
        "supersession_state": "EFFECTIVE_VARIANT_UNDETERMINED",
        "transition_eligible": False,
        "live_transport_authorized": False,
        "account_readonly_runtime_authorized": False,
        "testnet_execution_authorized": False,
        "mainnet_execution_authorized": False,
        "flp1_implementation_authorized": False,
    }
    authority["authority_hash"] = _hash_material(
        OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION,
        _authority_hash_material(authority),
    )
    return authority


def _assert_exact_json_primitive_tree(value: object, path: str = "$") -> None:
    if type(value) is dict:
        for key, item in cast(dict[object, object], value).items():
            if type(key) is not str:
                raise TypeError(f"{path} contains a non-exact-string object key")
            _assert_exact_json_primitive_tree(item, f"{path}.{key}")
        return
    if type(value) is list:
        for index, item in enumerate(cast(list[object], value)):
            _assert_exact_json_primitive_tree(item, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise TypeError(f"{path} contains a non-exact JSON primitive")


def _assert_expected_tree(actual: object, expected: object, path: str = "$") -> None:
    if type(actual) is not type(expected):
        raise ValueError(f"{path} has the wrong exact JSON type")
    if type(expected) is dict:
        actual_dict = cast(dict[str, object], actual)
        expected_dict = cast(dict[str, object], expected)
        if set(actual_dict) != set(expected_dict):
            raise ValueError(f"{path} has missing or extra fields")
        for key, expected_item in expected_dict.items():
            _assert_expected_tree(actual_dict[key], expected_item, f"{path}.{key}")
        return
    if type(expected) is list:
        actual_list = cast(list[object], actual)
        expected_list = cast(list[object], expected)
        if len(actual_list) != len(expected_list):
            raise ValueError(f"{path} has the wrong membership count")
        for index, expected_item in enumerate(expected_list):
            _assert_expected_tree(actual_list[index], expected_item, f"{path}[{index}]")
        return
    if actual != expected:
        raise ValueError(f"{path} does not match the frozen official authority")


def _require_unique_identity_and_semantics(
    items: list[object], id_field: str, excluded_fields: tuple[str, ...]
) -> None:
    identifiers: list[str] = []
    signatures: list[bytes] = []
    for raw_item in items:
        item = cast(dict[str, object], raw_item)
        identifiers.append(cast(str, item[id_field]))
        signatures.append(
            canonical_json_bytes(
                {
                    key: value
                    for key, value in item.items()
                    if key not in excluded_fields
                }
            )
        )
    if len(set(identifiers)) != len(identifiers):
        raise ValueError(f"duplicate {id_field}")
    if len(set(signatures)) != len(signatures):
        raise ValueError(f"semantic alias in {id_field} collection")


def _require_exact_object_fields(
    items: list[object], expected_items: list[object], collection_name: str
) -> None:
    if not expected_items or type(expected_items[0]) is not dict:
        raise AssertionError("frozen authority collection has no object template")
    expected_fields = set(cast(dict[str, object], expected_items[0]))
    for index, item in enumerate(items):
        if type(item) is not dict:
            raise TypeError(f"{collection_name}[{index}] must be an exact built-in dict")
        if set(cast(dict[str, object], item)) != expected_fields:
            raise ValueError(f"{collection_name}[{index}] has missing or extra fields")


def _authenticate_official_rate_limit_authority_mapping(
    raw_mapping: object,
) -> OfficialRateLimitAuthenticationResult:
    """Authenticate exact owned primitives; external-parser provenance is unrecoverable."""

    if type(raw_mapping) is not dict:
        raise TypeError("authority authentication requires an exact built-in dict")
    _assert_exact_json_primitive_tree(raw_mapping)
    authority = cast(dict[str, object], raw_mapping)
    expected = _build_official_rate_limit_authority_mapping()
    if set(authority) != set(expected):
        raise ValueError("authority root has missing or extra fields")

    sources = cast(list[object], authority["sources"])
    facts = cast(list[object], authority["documented_facts"])
    unknowns = cast(list[object], authority["unresolved_fields"])
    if type(sources) is not list or type(facts) is not list or type(unknowns) is not list:
        raise ValueError("authority collections must be exact built-in lists")
    _require_exact_object_fields(
        sources, cast(list[object], expected["sources"]), "sources"
    )
    _require_exact_object_fields(
        facts, cast(list[object], expected["documented_facts"]), "documented_facts"
    )
    _require_exact_object_fields(
        unknowns, cast(list[object], expected["unresolved_fields"]), "unresolved_fields"
    )
    _require_unique_identity_and_semantics(
        sources,
        "source_id",
        ("source_id", "source_hash", "retrieval_observations_utc"),
    )
    _require_unique_identity_and_semantics(facts, "fact_id", ("fact_id", "fact_hash"))
    _require_unique_identity_and_semantics(unknowns, "field_id", ("field_id",))

    for source_raw in sources:
        source = cast(dict[str, object], source_raw)
        canonical_location = source.get("canonical_location")
        if type(canonical_location) is not str:
            raise TypeError("official source location must be an exact string")
        if "?" in canonical_location or "#" in canonical_location:
            raise ValueError("official source location must not contain query or fragment")
        evidence_bytes = canonical_json_bytes(_source_evidence_material(source))
        if source.get("evidence_length_bytes") != len(evidence_bytes):
            raise ValueError("source evidence length mismatch")
        evidence_hash = sha256_hex(
            OFFICIAL_RATE_LIMIT_OBSERVATION_HASH_VERSION.encode("utf-8")
            + b"\0"
            + evidence_bytes
        )
        if not hmac.compare_digest(cast(str, source.get("evidence_hash")), evidence_hash):
            raise ValueError("source evidence hash mismatch")
        source_hash = _hash_material(
            OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION,
            _source_hash_material(source),
        )
        if not hmac.compare_digest(cast(str, source.get("source_hash")), source_hash):
            raise ValueError("source hash mismatch")
    for fact_raw in facts:
        fact = cast(dict[str, object], fact_raw)
        fact_material = dict(fact)
        supplied_hash = cast(str, fact_material.pop("fact_hash", ""))
        fact_hash = _hash_material(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, fact_material)
        if not hmac.compare_digest(supplied_hash, fact_hash):
            raise ValueError("fact hash mismatch")
    authority_hash = _hash_material(
        OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION,
        _authority_hash_material(authority),
    )
    if not hmac.compare_digest(cast(str, authority.get("authority_hash")), authority_hash):
        raise ValueError("authority hash mismatch")

    _assert_expected_tree(authority, expected)
    gate_fields = (
        "transition_eligible",
        "live_transport_authorized",
        "account_readonly_runtime_authorized",
        "testnet_execution_authorized",
        "mainnet_execution_authorized",
        "flp1_implementation_authorized",
    )
    if any(
        type(authority[field]) is not bool or authority[field] is not False
        for field in gate_fields
    ):
        raise ValueError("all authority gates must be exact false")
    return OfficialRateLimitAuthenticationResult(
        canonical_json=canonical_json_bytes(authority),
        authority_hash=authority_hash,
        source_ids=tuple(cast(str, cast(dict[str, object], item)["source_id"]) for item in sources),
        fact_ids=tuple(cast(str, cast(dict[str, object], item)["fact_id"]) for item in facts),
        unknown_ids=tuple(
            cast(str, cast(dict[str, object], item)["field_id"])
            for item in unknowns
        ),
        conflict_state="OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED",
        supersession_state="EFFECTIVE_VARIANT_UNDETERMINED",
        transition_eligible=False,
        live_transport_authorized=False,
        account_readonly_runtime_authorized=False,
        testnet_execution_authorized=False,
        mainnet_execution_authorized=False,
        flp1_implementation_authorized=False,
    )


def authenticate_official_rate_limit_authority_json(
    raw_json: str | bytes,
) -> OfficialRateLimitAuthenticationResult:
    """Authenticate exact raw JSON through the sole public authority-input boundary."""

    if type(raw_json) is bytes:
        raw_text = raw_json.decode("utf-8", errors="strict")
    elif type(raw_json) is str:
        raw_text = raw_json
    else:
        raise TypeError("raw authority must be an exact str or exact bytes")

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    def reject_non_finite(token: str) -> None:
        raise ValueError(f"non-finite JSON number is prohibited: {token}")

    decoded = json.loads(
        raw_text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_non_finite,
    )
    return _authenticate_official_rate_limit_authority_mapping(decoded)


def build_official_rate_limit_authority() -> OfficialRateLimitAuthorityV0:
    """Build an untrusted structural candidate, not authenticated authority."""

    sources = official_rate_limit_sources()
    facts = official_rate_limit_facts()
    unknowns = official_rate_limit_unknowns()
    values: dict[str, object] = {
        "sources": sources,
        "documented_facts": facts,
        "unresolved_fields": unknowns,
    }
    return OfficialRateLimitAuthorityV0(
        sources=sources,
        documented_facts=facts,
        unresolved_fields=unknowns,
        authority_hash=_authority_hash_from_values(values),
    )


def official_rate_limit_authority() -> OfficialRateLimitAuthorityV0:
    """Return an untrusted structural candidate for serialization and Schema use."""

    return build_official_rate_limit_authority()
