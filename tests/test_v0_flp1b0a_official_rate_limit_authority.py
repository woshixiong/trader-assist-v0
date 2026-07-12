from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError

from trader_assist_v0.contracts.rate_limits import (
    OfficialRateLimitAuthorityV0,
    OfficialRateLimitFactV0,
    OfficialRateLimitSourceV0,
    OfficialRateLimitUnknownV0,
    build_official_rate_limit_authority,
    validate_official_rate_limit_authority,
)
from trader_assist_v0.contracts.source_catalog import (
    RATE_LIMIT_STATUS,
    SOURCE_CATALOG_HASH,
    assert_rate_limit_allows_live_transport,
    rate_limit_authority_document,
    rate_limit_entry_gate,
)

SOURCE_HASH_DOMAIN = "trader-assist-v0/official-rate-limit-source/v1"
OBSERVATION_HASH_DOMAIN = "trader-assist-v0/official-rate-limit-observation/v1"
FACT_HASH_DOMAIN = "trader-assist-v0/official-rate-limit-fact/v1"
AUTHORITY_HASH_DOMAIN = "trader-assist-v0/official-rate-limit-authority-hash/v1"
EXPECTED_SOURCE_CATALOG_HASH = "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"


class FactRow(NamedTuple):
    fact_id: str
    category: str
    transport: str
    endpoint_class: str
    operation_allowlist: tuple[str, ...]
    scope_kind: str
    numeric_value: int
    value_unit: str
    window_value: int | None
    window_unit: str | None
    response_divisor_value: int | None
    response_divisor_unit: str | None
    formula: str | None
    source_bindings: tuple[str, ...]


RATE = "hyperliquid-rate-limits-and-user-limits"
INFO = "hyperliquid-info-endpoint"
RATE_ONLY = (RATE,)
RATE_INFO = (RATE, INFO)

EXPECTED_FACTS: tuple[FactRow, ...] = (
    FactRow(
        "ip.rest.aggregate-weight",
        "IP",
        "REST",
        "documented REST API",
        ("*",),
        "per IP address",
        1200,
        "weight",
        1,
        "minute",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.exchange.batch-weight",
        "IP",
        "REST",
        "exchange API",
        ("all documented exchange actions",),
        "per IP request",
        1,
        "base weight",
        None,
        None,
        None,
        None,
        "1 + floor(batch_length / 40)",
        RATE_ONLY,
    ),
    FactRow(
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
        None,
        None,
        None,
        None,
        None,
        RATE_INFO,
    ),
    FactRow(
        "ip.info.user-role-weight",
        "IP",
        "REST",
        "info API",
        ("userRole",),
        "per IP request",
        60,
        "weight",
        None,
        None,
        None,
        None,
        None,
        RATE_INFO,
    ),
    FactRow(
        "ip.info.default-weight",
        "IP",
        "REST",
        "info API",
        ("all other documented info requests",),
        "per IP request",
        20,
        "weight",
        None,
        None,
        None,
        None,
        None,
        RATE_INFO,
    ),
    FactRow(
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
        None,
        None,
        20,
        "response items",
        None,
        RATE_INFO,
    ),
    FactRow(
        "ip.info.candle-response-divisor",
        "IP",
        "REST",
        "info API",
        ("candleSnapshot",),
        "per IP response",
        1,
        "additional weight",
        None,
        None,
        60,
        "response items",
        None,
        RATE_INFO,
    ),
    FactRow(
        "ip.explorer.weight",
        "IP",
        "REST",
        "explorer API",
        ("all explorer requests",),
        "per IP request",
        40,
        "weight",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.explorer.block-list",
        "IP",
        "REST",
        "explorer API",
        ("blockList",),
        "per IP response",
        1,
        "additional limit unit",
        None,
        None,
        1,
        "block",
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.connections",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("connect",),
        "per IP address",
        10,
        "simultaneous connections",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.new-connections",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("connect",),
        "per IP address",
        30,
        "new connections",
        1,
        "minute",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.subscriptions",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("subscribe",),
        "per IP address",
        1000,
        "subscriptions",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.unique-users",
        "IP",
        "WEBSOCKET",
        "user-specific websocket subscriptions",
        ("subscribe",),
        "per IP address",
        10,
        "unique users",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.messages-sent",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("send message",),
        "per IP address across all connections",
        2000,
        "messages",
        1,
        "minute",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.websocket.inflight-posts",
        "IP",
        "WEBSOCKET",
        "all websocket connections",
        ("post",),
        "per IP address across all connections",
        100,
        "simultaneous inflight post messages",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "ip.evm-json-rpc.requests",
        "IP",
        "JSON-RPC",
        "rpc.hyperliquid.xyz/evm",
        ("all EVM JSON-RPC requests",),
        "per IP address",
        100,
        "requests",
        1,
        "minute",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.volume-request-ratio",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per user; sub-account is separate user",
        1,
        "request",
        None,
        None,
        1,
        "USDC traded cumulatively since address inception",
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.initial-buffer",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per address",
        10000,
        "requests",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.rate-limited-fallback",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("all actions",),
        "per rate-limited address",
        1,
        "request",
        10,
        "seconds",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.cancel-limit-formula",
        "ADDRESS",
        "ACTION",
        "exchange actions",
        ("cancel",),
        "per address cumulative limit",
        100000,
        "requests",
        None,
        None,
        None,
        None,
        "min(limit + 100000, limit * 2)",
        RATE_ONLY,
    ),
    FactRow(
        "address.open-order-base-limit",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        1000,
        "open orders",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.open-order-volume-increment",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        1,
        "additional open order",
        None,
        None,
        5000000,
        "USDC volume",
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.open-order-cap",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place order",),
        "per user",
        5000,
        "open orders",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.open-order-rejection-threshold",
        "ADDRESS",
        "ACTION",
        "open orders",
        ("place reduce-only order", "place trigger order"),
        "per user with other open orders",
        1000,
        "other open orders",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "address.high-congestion-maker-share",
        "ADDRESS",
        "ACTION",
        "block space",
        ("all actions",),
        "per address during high congestion",
        2,
        "multiplier of previous-day maker share percentage",
        1,
        "UTC date",
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "batch.ip-count",
        "BATCH",
        "REST",
        "exchange API",
        ("batched orders", "batched cancels"),
        "IP-based rate limiting",
        1,
        "request per batch",
        None,
        None,
        None,
        None,
        None,
        RATE_ONLY,
    ),
    FactRow(
        "batch.address-count",
        "BATCH",
        "ACTION",
        "exchange API",
        ("batched orders", "batched cancels"),
        "address-based rate limiting",
        1,
        "request per batch item",
        None,
        None,
        None,
        None,
        "n requests for n orders or cancels",
        RATE_ONLY,
    ),
)


class UnknownRow(NamedTuple):
    field_id: str
    reason: str
    resolution_requirement: str


EXPECTED_UNKNOWNS: tuple[UnknownRow, ...] = (
    UnknownRow(
        "burst-semantics",
        "Burst capacity and burst handling are not documented.",
        "An official source must define burst capacity and handling.",
    ),
    UnknownRow(
        "window-algorithm",
        "Fixed, sliding, and token-bucket window behavior is not documented.",
        "An official source must define the rate-limit window algorithm.",
    ),
    UnknownRow(
        "window-alignment",
        "The alignment origin for documented windows is not documented.",
        "An official source must define window alignment.",
    ),
    UnknownRow(
        "partial-response-bucket-rounding",
        "Rounding for partial 20-item and 60-item response buckets is not documented.",
        "An official source must define partial-bucket rounding.",
    ),
    UnknownRow(
        "http-429-status",
        "HTTP 429 behavior is not documented on the frozen rate-limit page.",
        "An official source must define the HTTP status behavior when limited.",
    ),
    UnknownRow(
        "error-body",
        "The rate-limit error body is not documented.",
        "An official source must define the rate-limit error body contract.",
    ),
    UnknownRow(
        "error-headers",
        "Rate-limit response headers are not documented.",
        "An official source must define authoritative rate-limit response headers.",
    ),
    UnknownRow(
        "retry-after",
        "Retry-After presence, unit, and meaning are not documented.",
        "An official source must define Retry-After behavior or explicitly state "
        "that it is absent.",
    ),
    UnknownRow(
        "older-block-weight",
        "The official source says older uncached blocks may be weighted more heavily "
        "but gives no exact formula.",
        "An official source must define the exact older-block weight formula.",
    ),
    UnknownRow(
        "high-congestion-trigger",
        "The activation and deactivation semantics for high congestion are not documented.",
        "An official source must define high-congestion state transitions.",
    ),
)

EXPECTED_GATES = {
    "status": "UNRESOLVED_OFFICIAL_LIMIT",
    "transition_eligible": False,
    "live_transport_authorized": False,
    "account_readonly_runtime_authorized": False,
    "testnet_execution_authorized": False,
    "mainnet_execution_authorized": False,
    "flp1_implementation_authorized": False,
}

RATE_OBSERVATION = (
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
    "A batch of n orders or cancels counts as one IP-based request and n address-based requests.",
    "Burst, window implementation/alignment, partial divisor rounding, "
    "rate-limit HTTP/error/header/Retry-After behavior, exact older-block "
    "weighting, and high-congestion activation remain unspecified.",
)
INFO_OBSERVATION = (
    "Info operations are selected by the POST /info request-body type.",
    "The supporting page identifies l2Book, allMids, clearinghouseState, "
    "orderStatus, spotClearinghouseState, exchangeStatus, userRole, "
    "candleSnapshot, and the response-weighted history operation identities.",
    "This supporting source binds operation identity and does not independently "
    "define the numeric rate-limit weights.",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _hash(domain: str, payload: dict[str, Any]) -> str:
    return hashlib.sha256(domain.encode() + b"\0" + _canonical(payload)).hexdigest()


def _fact_payload(row: FactRow) -> dict[str, Any]:
    payload = row._asdict()
    payload["fact_hash"] = _hash(FACT_HASH_DOMAIN, payload)
    return payload


def _unknown_payload(row: UnknownRow) -> dict[str, Any]:
    return {
        "field_id": row.field_id,
        "affected_endpoint_class": "all documented rate-limited endpoints",
        "affected_operations": ("*",),
        "mandatory": True,
        "blocking": True,
        "reason": row.reason,
        "evidence": "The frozen official sources do not explicitly specify this semantic.",
        "resolution_requirement": row.resolution_requirement,
    }


def _source_payload(
    *,
    source_id: str,
    title: str,
    location: str,
    retrievals: tuple[str, ...],
    marker: str,
    locator: str,
    fact_ids: tuple[str, ...],
    unknown_ids: tuple[str, ...],
    observation: tuple[str, ...],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": source_id,
        "kind": "OFFICIAL_HYPERLIQUID_DOCUMENTATION",
        "title": title,
        "canonical_location": location,
        "retrieval_observations_utc": retrievals,
        "publication_or_last_updated_marker": marker,
        "semantic_locator": locator,
        "bound_fact_ids": fact_ids,
        "bound_unknown_ids": unknown_ids,
        "semantic_observation": observation,
    }
    evidence_material = {
        key: payload[key]
        for key in (
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
    }
    evidence_bytes = _canonical(evidence_material)
    payload["evidence_hash"] = hashlib.sha256(
        OBSERVATION_HASH_DOMAIN.encode() + b"\0" + evidence_bytes
    ).hexdigest()
    payload["evidence_length_bytes"] = len(evidence_bytes)
    payload["source_hash"] = _hash(SOURCE_HASH_DOMAIN, payload)
    return payload


EXPECTED_FACT_PAYLOADS = tuple(_fact_payload(row) for row in EXPECTED_FACTS)
EXPECTED_UNKNOWN_PAYLOADS = tuple(_unknown_payload(row) for row in EXPECTED_UNKNOWNS)
ALL_FACT_IDS = tuple(row.fact_id for row in EXPECTED_FACTS)
INFO_FACT_IDS = tuple(row.fact_id for row in EXPECTED_FACTS if INFO in row.source_bindings)
ALL_UNKNOWN_IDS = tuple(row.field_id for row in EXPECTED_UNKNOWNS)
EXPECTED_SOURCES = (
    _source_payload(
        source_id=RATE,
        title="Rate limits and user limits",
        location="https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits",
        retrievals=("2026-07-12T07:49:50Z", "2026-07-12T07:49:51Z"),
        marker="2026-04-28T02:43:32.166Z",
        locator="Rate limits and user limits / complete page body",
        fact_ids=ALL_FACT_IDS,
        unknown_ids=ALL_UNKNOWN_IDS,
        observation=RATE_OBSERVATION,
    ),
    _source_payload(
        source_id=INFO,
        title="Info endpoint",
        location="https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint",
        retrievals=("2026-07-12T07:50:44Z",),
        marker="2026-06-11T08:02:46.893Z",
        locator="Info endpoint / operation request-body identities",
        fact_ids=INFO_FACT_IDS,
        unknown_ids=(),
        observation=INFO_OBSERVATION,
    ),
)


def _expected_authority_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "authority_version": "trader-assist-v0/official-rate-limit-authority/v1",
        **EXPECTED_GATES,
        "sources": EXPECTED_SOURCES,
        "documented_facts": EXPECTED_FACT_PAYLOADS,
        "unresolved_fields": EXPECTED_UNKNOWN_PAYLOADS,
        "conflict_state": "NO_CONFLICT_DETECTED",
        "supersession_state": "NO_SUPERSESSION_DETECTED",
    }
    payload["authority_hash"] = _hash(AUTHORITY_HASH_DOMAIN, payload)
    return payload


EXPECTED_AUTHORITY = _expected_authority_payload()
EXPECTED_AUTHORITY_HASH = EXPECTED_AUTHORITY["authority_hash"]


def _actual_dict() -> dict[str, Any]:
    return BaseModel.model_dump(
        build_official_rate_limit_authority(), mode="python", round_trip=True
    )


def _fact_index(fact_id: str) -> int:
    return ALL_FACT_IDS.index(fact_id)


def _coherently_rehash_fact(fact: dict[str, Any]) -> None:
    payload = dict(fact)
    payload.pop("fact_hash")
    fact["fact_hash"] = _hash(FACT_HASH_DOMAIN, payload)


def test_test_owned_matrices_match_complete_executable_authority() -> None:
    actual = _actual_dict()
    assert actual["sources"] == EXPECTED_SOURCES
    assert actual["documented_facts"] == EXPECTED_FACT_PAYLOADS
    assert actual["unresolved_fields"] == EXPECTED_UNKNOWN_PAYLOADS
    assert {key: actual[key] for key in EXPECTED_GATES} == EXPECTED_GATES
    assert actual == EXPECTED_AUTHORITY


def test_current_source_reconciliation_is_frozen_exactly() -> None:
    assert len(EXPECTED_SOURCES) == 2
    assert len(EXPECTED_FACTS) == 27
    assert len(EXPECTED_UNKNOWNS) == 10
    assert EXPECTED_SOURCES[0]["retrieval_observations_utc"] == (
        "2026-07-12T07:49:50Z",
        "2026-07-12T07:49:51Z",
    )
    by_id = {row.fact_id: row for row in EXPECTED_FACTS}
    assert by_id["ip.websocket.connections"].numeric_value == 10
    assert by_id["ip.websocket.new-connections"].numeric_value == 30
    assert by_id["ip.websocket.new-connections"].window_value == 1
    assert by_id["ip.websocket.new-connections"].window_unit == "minute"
    maker = by_id["address.high-congestion-maker-share"]
    assert maker.value_unit == "multiplier of previous-day maker share percentage"
    assert (maker.window_value, maker.window_unit) == (1, "UTC date")


def test_structured_observation_hash_and_length_are_independently_recomputable() -> None:
    for source in EXPECTED_SOURCES:
        material = {
            key: source[key]
            for key in (
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
        }
        evidence = _canonical(material)
        assert source["evidence_length_bytes"] == len(evidence)
        assert (
            source["evidence_hash"]
            == hashlib.sha256(OBSERVATION_HASH_DOMAIN.encode() + b"\0" + evidence).hexdigest()
        )
        assert "content_sha256" not in source
        assert "content_length_bytes" not in source
        assert "html-sha256" not in json.dumps(source)


@pytest.mark.parametrize(
    "fact_id,field,replacement",
    [
        ("ip.rest.aggregate-weight", "numeric_value", 1201),
        ("ip.rest.aggregate-weight", "numeric_value", 1199),
        ("ip.rest.aggregate-weight", "value_unit", "requests"),
        ("ip.rest.aggregate-weight", "scope_kind", "per user"),
        (
            "ip.info.weight-2",
            "operation_allowlist",
            (
                "allMids",
                "l2Book",
                "clearinghouseState",
                "orderStatus",
                "spotClearinghouseState",
                "exchangeStatus",
            ),
        ),
        ("ip.rest.aggregate-weight", "window_value", 2),
        ("ip.rest.aggregate-weight", "window_unit", "seconds"),
        ("ip.websocket.connections", "window_value", 1),
        ("ip.websocket.connections", "window_unit", "minute"),
        ("ip.info.response-item-divisor", "response_divisor_value", 21),
        ("ip.info.response-item-divisor", "response_divisor_unit", "rows"),
        ("ip.websocket.connections", "response_divisor_value", 1),
        ("ip.exchange.batch-weight", "formula", "1 + floor(batch_length / 39)"),
        ("ip.websocket.connections", "formula", "invented"),
        ("ip.rest.aggregate-weight", "source_bindings", RATE_INFO),
        ("ip.websocket.connections", "numeric_value", 100),
        ("address.high-congestion-maker-share", "value_unit", "multiplier of maker share"),
        ("address.high-congestion-maker-share", "window_unit", "day"),
    ],
)
def test_every_semantic_fact_mutation_is_rejected_even_when_rehashed(
    fact_id: str, field: str, replacement: Any
) -> None:
    data = _actual_dict()
    fact = data["documented_facts"][_fact_index(fact_id)]
    fact[field] = replacement
    _coherently_rehash_fact(fact)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


@pytest.mark.parametrize("member", ["sources", "documented_facts", "unresolved_fields"])
def test_membership_omission_duplication_and_reordering_fail(member: str) -> None:
    for operation in ("omit", "duplicate", "reorder"):
        data = _actual_dict()
        values = data[member]
        if operation == "omit":
            data[member] = values[1:]
        elif operation == "duplicate":
            data[member] = (*values, values[0])
        else:
            data[member] = tuple(reversed(values))
        with pytest.raises(ValidationError):
            OfficialRateLimitAuthorityV0.model_validate(data)


def test_semantic_duplicate_new_id_and_no_30_minute_planning_attack_fail() -> None:
    data = _actual_dict()
    duplicate = copy.deepcopy(data["documented_facts"][0])
    duplicate["fact_id"] = "invented.semantic-duplicate"
    _coherently_rehash_fact(duplicate)
    data["documented_facts"] += (duplicate,)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)

    data = _actual_dict()
    index = _fact_index("ip.websocket.new-connections")
    data["documented_facts"] = (
        data["documented_facts"][:index] + data["documented_facts"][index + 1 :]
    )
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


@pytest.mark.parametrize(
    "model,payload",
    [
        (OfficialRateLimitSourceV0, lambda: _actual_dict()["sources"][0]),
        (OfficialRateLimitFactV0, lambda: _actual_dict()["documented_facts"][0]),
        (OfficialRateLimitUnknownV0, lambda: _actual_dict()["unresolved_fields"][0]),
        (OfficialRateLimitAuthorityV0, _actual_dict),
    ],
)
def test_all_validation_entry_points_are_permanently_strict(
    model: type[BaseModel], payload: Any
) -> None:
    value = payload()
    with pytest.raises(TypeError):
        model.model_validate(value, strict=False)
    with pytest.raises(TypeError):
        model.model_validate(value, from_attributes=True)
    with pytest.raises(TypeError):
        model.model_validate(value, extra="allow")
    with pytest.raises(TypeError):
        model.model_validate(value, extra="ignore")
    with pytest.raises(TypeError):
        model.model_validate_json(json.dumps(value), strict=False)
    with pytest.raises(TypeError):
        model.model_validate_strings(value)


@pytest.mark.parametrize("replacement", ["1200", 1200.0, True])
def test_python_and_json_numeric_coercion_attacks_fail(replacement: Any) -> None:
    data = _actual_dict()
    data["documented_facts"][0]["numeric_value"] = replacement
    with pytest.raises((TypeError, ValidationError)):
        OfficialRateLimitAuthorityV0.model_validate(data)
    with pytest.raises((TypeError, ValidationError)):
        OfficialRateLimitAuthorityV0.model_validate_json(json.dumps(data))


def test_base_and_core_validation_cannot_reenable_numeric_coercion() -> None:
    data = _actual_dict()
    data["documented_facts"][0]["numeric_value"] = "1200"
    with pytest.raises(TypeError, match="exact integer"):
        BaseModel.model_validate.__func__(
            OfficialRateLimitAuthorityV0,
            data,
            strict=False,
            extra="allow",
        )
    with pytest.raises(TypeError, match="exact integer"):
        OfficialRateLimitAuthorityV0.__pydantic_validator__.validate_python(
            data,
            strict=False,
            extra="allow",
        )


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("sources", 0, "evidence_length_bytes"), "3382"),
        (("sources", 0, "evidence_length_bytes"), 3382.0),
        (("documented_facts", 0, "window_value"), "1"),
        (("documented_facts", 5, "response_divisor_value"), 20.0),
        (("unresolved_fields", 0, "mandatory"), 1),
        (("unresolved_fields", 0, "blocking"), "true"),
        ((None, None, "transition_eligible"), 0),
        ((None, None, "live_transport_authorized"), "false"),
        ((None, None, "account_readonly_runtime_authorized"), 0),
        ((None, None, "testnet_execution_authorized"), 0),
        ((None, None, "mainnet_execution_authorized"), "false"),
        ((None, None, "flp1_implementation_authorized"), 0),
    ],
)
def test_nested_integer_and_boolean_coercion_attacks_fail(
    path: tuple[str | None, int | None, str], replacement: Any
) -> None:
    data = _actual_dict()
    collection, index, field = path
    if collection is None:
        data[field] = replacement
    else:
        assert index is not None
        data[collection][index][field] = replacement
    with pytest.raises((TypeError, ValidationError)):
        OfficialRateLimitAuthorityV0.model_validate(data)
    with pytest.raises((TypeError, ValidationError)):
        OfficialRateLimitAuthorityV0.model_validate_json(json.dumps(data))


def test_native_json_types_validate_but_extra_fields_do_not() -> None:
    encoded = json.dumps(_actual_dict(), ensure_ascii=False, separators=(",", ":"))
    assert OfficialRateLimitAuthorityV0.model_validate_json(encoded).authority_hash
    for collection in (None, "sources", "documented_facts", "unresolved_fields"):
        data = _actual_dict()
        if collection is None:
            data["extra"] = "forbidden"
        else:
            data[collection][0]["extra"] = "forbidden"
        with pytest.raises(ValidationError):
            OfficialRateLimitAuthorityV0.model_validate_json(json.dumps(data))


def test_exact_instance_tampering_construct_copy_subclass_and_unicode_fail() -> None:
    authority = build_official_rate_limit_authority()
    object.__setattr__(authority, "status", "OFFICIAL_NUMERIC_LIMIT_RESOLVED")
    with pytest.raises(ValidationError):
        validate_official_rate_limit_authority(authority)
    with pytest.raises(TypeError):
        OfficialRateLimitAuthorityV0.model_construct(**_actual_dict())
    with pytest.raises(TypeError):
        build_official_rate_limit_authority().model_copy()

    class AuthoritySubclass(OfficialRateLimitAuthorityV0):
        pass

    with pytest.raises(ValidationError):
        AuthoritySubclass(**_actual_dict())

    data = _actual_dict()
    data["sources"][0]["title"] = "Rate limits and user limit\N{COMBINING ACUTE ACCENT}s"
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_independent_hash_oracle_and_coherent_rehash_attack() -> None:
    actual = _actual_dict()
    assert actual["authority_hash"] == EXPECTED_AUTHORITY_HASH
    data = _actual_dict()
    data["unresolved_fields"] = data["unresolved_fields"][1:]
    material = dict(data)
    material.pop("authority_hash")
    data["authority_hash"] = _hash(AUTHORITY_HASH_DOMAIN, material)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_schema_is_complete_structural_only_and_counterfeit_needs_executable_rejection() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas/v0/OfficialRateLimitAuthorityV0.schema.json").read_text())
    assert "Schema validation proves serialized structure only" in schema["$comment"]
    for candidate in (schema, *schema["$defs"].values()):
        if "properties" in candidate:
            assert candidate["additionalProperties"] is False
            assert set(candidate["required"]) == set(candidate["properties"])
            assert all("default" not in value for value in candidate["properties"].values())

    counterfeit = json.loads(json.dumps(_actual_dict()))
    counterfeit["sources"][0]["title"] = "Counterfeit official title"
    validator = Draft202012Validator(schema)
    validator.validate(counterfeit)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate_json(json.dumps(counterfeit))


def test_source_catalog_hash_and_all_gates_remain_fail_closed() -> None:
    assert SOURCE_CATALOG_HASH == EXPECTED_SOURCE_CATALOG_HASH
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    document = rate_limit_authority_document()
    assert document["authority_hash"] == EXPECTED_AUTHORITY_HASH
    assert len(document["documented_facts"]) == 27
    assert len(document["unresolved_fields"]) == 10
    gate = rate_limit_entry_gate()
    assert gate["transition_eligible"] is False
    assert gate["live_transport_authorized"] is False
    with pytest.raises(ValueError, match="unresolved"):
        assert_rate_limit_allows_live_transport()


def test_contract_has_no_network_async_runtime_or_exchange_capability() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "src/trader_assist_v0/contracts/rate_limits.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        assert not isinstance(node, ast.AsyncFor | ast.AsyncFunctionDef | ast.AsyncWith | ast.Await)
    forbidden = {
        "asyncio",
        "http.client",
        "httpx",
        "requests",
        "socket",
        "ssl",
        "urllib",
        "urllib.request",
        "urllib3",
        "websocket",
        "websockets",
    }
    assert not any(
        name == bad or name.startswith(bad + ".") for name in imports for bad in forbidden
    )
