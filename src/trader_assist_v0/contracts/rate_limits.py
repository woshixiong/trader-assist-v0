from __future__ import annotations

import hmac
import json
from collections.abc import Mapping, Set
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


class _RateLimitAuthorityModel(BaseModel):
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
        expected = _SOURCE_SPEC_BY_ID.get(self.source_id)
        if expected is None or _source_payload(self) != expected:
            raise ValueError("unofficial, stale, altered, or mismatched rate-limit source")
        evidence_bytes = canonical_json_bytes(_source_evidence_material(self))
        expected_evidence_hash = sha256_hex(
            OFFICIAL_RATE_LIMIT_OBSERVATION_HASH_VERSION.encode("utf-8") + b"\0" + evidence_bytes
        )
        if self.evidence_length_bytes != len(evidence_bytes):
            raise ValueError("evidence length does not match structured observation")
        if not hmac.compare_digest(self.evidence_hash, expected_evidence_hash):
            raise ValueError("evidence hash does not match structured observation")
        expected_hash = _hash_material(OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION, expected)
        if not hmac.compare_digest(self.source_hash, expected_hash):
            raise ValueError("source_hash does not match frozen official source")
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
        expected = _FACT_SPEC_BY_ID.get(self.fact_id)
        if expected is None or _fact_payload(self) != expected:
            raise ValueError("altered, conflicting, or source-mismatched rate-limit fact")
        expected_hash = _hash_material(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, expected)
        if not hmac.compare_digest(self.fact_hash, expected_hash):
            raise ValueError("fact_hash does not match frozen official fact")
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
        expected = _UNKNOWN_SPEC_BY_ID.get(self.field_id)
        if expected is None or _unknown_payload(self) != expected:
            raise ValueError("mandatory rate-limit unknown was altered or invented")
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
    conflict_state: Literal["NO_CONFLICT_DETECTED"] = "NO_CONFLICT_DETECTED"
    supersession_state: Literal["NO_SUPERSESSION_DETECTED"] = "NO_SUPERSESSION_DETECTED"
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
        expected_sources = official_rate_limit_sources()
        expected_facts = official_rate_limit_facts()
        expected_unknowns = official_rate_limit_unknowns()
        if self.sources != expected_sources:
            raise ValueError("official rate-limit sources are incomplete or altered")
        if self.documented_facts != expected_facts:
            raise ValueError("documented rate-limit facts are incomplete, duplicate, or altered")
        if self.unresolved_fields != expected_unknowns:
            raise ValueError("mandatory rate-limit unknowns are incomplete or altered")
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


def _source_payload(source: OfficialRateLimitSourceV0) -> dict[str, object]:
    payload = BaseModel.model_dump(source, mode="python", round_trip=True)
    payload.pop("source_hash")
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


def _unknown_payload(unknown: OfficialRateLimitUnknownV0) -> dict[str, object]:
    return BaseModel.model_dump(unknown, mode="python", round_trip=True)


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
        "ip.websocket.connections",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("connect",),
        "per IP address",
        10,
        "simultaneous connections",
    ),
    _fact(
        "ip.websocket.new-connections",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("connect",),
        "per IP address",
        30,
        "new connections",
        window=(1, "minute"),
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
        "multiplier of previous-day maker share percentage",
        window=(1, "UTC date"),
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
_FACT_SPEC_BY_ID = {str(item["fact_id"]): item for item in _FACT_SPECS}


def _unknown(field_id: str, reason: str, requirement: str) -> dict[str, object]:
    return {
        "field_id": field_id,
        "affected_endpoint_class": "all documented rate-limited endpoints",
        "affected_operations": ("*",),
        "mandatory": True,
        "blocking": True,
        "reason": reason,
        "evidence": "The frozen official sources do not explicitly specify this semantic.",
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
)
_UNKNOWN_SPEC_BY_ID = {str(item["field_id"]): item for item in _UNKNOWN_SPECS}


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
            "2026-07-12T07:49:50Z",
            "2026-07-12T07:49:51Z",
        ),
        publication_or_last_updated_marker="2026-04-28T02:43:32.166Z",
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
            "The per-IP WebSocket limits are 10 simultaneous connections, 30 new "
            "connections per minute, 1000 subscriptions, and 10 unique users across "
            "user-specific subscriptions.",
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
            "During high congestion, block-space use is limited to 2x the previous-day "
            "maker-share percentage, and maker share is computed once per UTC date.",
            "A batch of n orders or cancels counts as one IP-based request and n "
            "address-based requests.",
            "Burst, window implementation/alignment, partial divisor rounding, "
            "rate-limit HTTP/error/header/Retry-After behavior, exact older-block "
            "weighting, and high-congestion activation remain unspecified.",
        ),
    ),
    _source(
        source_id=INFO_ENDPOINT_SOURCE_ID,
        title="Info endpoint",
        canonical_location=(
            "https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint"
        ),
        retrieval_observations_utc=("2026-07-12T07:50:44Z",),
        publication_or_last_updated_marker="2026-06-11T08:02:46.893Z",
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
        ),
    ),
)
_SOURCE_SPEC_BY_ID = {str(item["source_id"]): item for item in _SOURCE_SPECS}


def official_rate_limit_sources() -> tuple[OfficialRateLimitSourceV0, ...]:
    return tuple(
        OfficialRateLimitSourceV0.model_validate(
            {
                **spec,
                "source_hash": _hash_material(OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION, spec),
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
    payload.pop("authority_hash")
    return _hash_material(OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION, payload)


def _authority_hash_from_values(values: Mapping[str, object]) -> str:
    payload = {
        "schema_version": OFFICIAL_RATE_LIMIT_SCHEMA_VERSION,
        "authority_version": OFFICIAL_RATE_LIMIT_AUTHORITY_VERSION,
        "status": OFFICIAL_RATE_LIMIT_STATUS,
        **values,
        "conflict_state": "NO_CONFLICT_DETECTED",
        "supersession_state": "NO_SUPERSESSION_DETECTED",
        "transition_eligible": False,
        "live_transport_authorized": False,
        "account_readonly_runtime_authorized": False,
        "testnet_execution_authorized": False,
        "mainnet_execution_authorized": False,
        "flp1_implementation_authorized": False,
    }
    return _hash_material(OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION, payload)


def build_official_rate_limit_authority() -> OfficialRateLimitAuthorityV0:
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
    return build_official_rate_limit_authority()


def validate_official_rate_limit_authority(
    authority: OfficialRateLimitAuthorityV0,
) -> OfficialRateLimitAuthorityV0:
    return OfficialRateLimitAuthorityV0.model_validate(authority)
