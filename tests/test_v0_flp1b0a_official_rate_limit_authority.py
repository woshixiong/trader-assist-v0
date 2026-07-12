from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.contracts.rate_limits import (
    OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION,
    OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION,
    OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION,
    OfficialRateLimitAuthorityV0,
    OfficialRateLimitFactV0,
    OfficialRateLimitSourceV0,
    build_official_rate_limit_authority,
    compute_official_rate_limit_authority_hash,
    validate_official_rate_limit_authority,
)
from trader_assist_v0.contracts.source_catalog import (
    RATE_LIMIT_STATUS,
    SOURCE_CATALOG_HASH,
    assert_rate_limit_allows_live_transport,
    rate_limit_authority_document,
    rate_limit_entry_gate,
)

EXPECTED_SOURCE_CATALOG_HASH = "0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7"
EXPECTED_AUTHORITY_HASH = "d4cfaeaa4c53b2588201ed76059bba6cb51a5582d422a398b9b71b559db8a636"


def _domain_hash(domain: str, payload: dict[str, Any]) -> str:
    return sha256_hex(domain.encode() + b"\0" + canonical_json_bytes(payload))


def _authority_dict() -> dict[str, Any]:
    return BaseModel.model_dump(
        build_official_rate_limit_authority(), mode="python", round_trip=True
    )


def test_current_status_and_every_gate_remain_fail_closed() -> None:
    authority = validate_official_rate_limit_authority(build_official_rate_limit_authority())
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert authority.status == "UNRESOLVED_OFFICIAL_LIMIT"
    assert authority.transition_eligible is False
    assert authority.live_transport_authorized is False
    assert authority.account_readonly_runtime_authorized is False
    assert authority.testnet_execution_authorized is False
    assert authority.mainnet_execution_authorized is False
    assert authority.flp1_implementation_authorized is False
    assert rate_limit_entry_gate()["live_transport_authorized"] is False
    with pytest.raises(ValueError, match="unresolved"):
        assert_rate_limit_allows_live_transport()


def test_official_sources_have_exact_current_binding() -> None:
    sources = build_official_rate_limit_authority().sources
    assert tuple(source.source_id for source in sources) == (
        "hyperliquid-rate-limits-and-user-limits",
        "hyperliquid-info-endpoint",
    )
    assert tuple(source.content_sha256 for source in sources) == (
        "fdaf15ab3ede2056f24673a579684457e6f2eb75bc6626b657c22f47a132895e",
        "db7daffd672132ab651de4398fa7ce47d4bf24797b92d983233f80e4c56ed760",
    )
    assert tuple(source.publication_or_last_updated_marker for source in sources) == (
        "2026-04-28T02:43:32.166Z",
        "2026-06-11T08:02:46.893Z",
    )
    assert all(source.kind == "OFFICIAL_HYPERLIQUID_DOCUMENTATION" for source in sources)


def test_every_frozen_fact_has_exact_complete_numeric_semantics() -> None:
    facts = build_official_rate_limit_authority().documented_facts
    assert len(facts) == 27
    assert len({fact.fact_id for fact in facts}) == len(facts)
    for fact in facts:
        assert type(fact.numeric_value) is int
        assert fact.value_unit
        assert fact.operation_allowlist
        assert fact.scope_kind
        assert fact.source_bindings
        assert (fact.window_value is None) == (fact.window_unit is None)
        assert (fact.response_divisor_value is None) == (fact.response_divisor_unit is None)

    by_id = {fact.fact_id: fact for fact in facts}
    rest = by_id["ip.rest.aggregate-weight"]
    assert (rest.numeric_value, rest.value_unit, rest.window_value, rest.window_unit) == (
        1200,
        "weight",
        1,
        "minute",
    )
    candles = by_id["ip.info.candle-response-divisor"]
    assert candles.operation_allowlist == ("candleSnapshot",)
    assert (candles.numeric_value, candles.response_divisor_value) == (1, 60)
    exchange = by_id["ip.exchange.batch-weight"]
    assert exchange.formula == "1 + floor(batch_length / 40)"
    address = by_id["address.cancel-limit-formula"]
    assert address.formula == "min(limit + 100000, limit * 2)"


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("numeric_value", 1201),
        ("numeric_value", 1199),
        ("value_unit", "requests"),
        ("scope_kind", "per user"),
        ("operation_allowlist", ("candleSnapshot",)),
        ("window_value", 2),
        ("window_unit", "seconds"),
        ("response_divisor_value", 2),
    ],
)
def test_altered_fact_even_with_coherent_fact_hash_is_rejected(
    field: str, replacement: Any
) -> None:
    data = _authority_dict()
    index = 0 if not field.startswith("response") else 5
    fact = data["documented_facts"][index]
    fact[field] = replacement
    payload = dict(fact)
    payload.pop("fact_hash")
    fact["fact_hash"] = _domain_hash(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, payload)
    with pytest.raises(ValidationError, match="altered|mismatched|paired"):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_mandatory_unknowns_include_every_prohibited_inference() -> None:
    unknown_ids = {
        item.field_id for item in build_official_rate_limit_authority().unresolved_fields
    }
    assert unknown_ids == {
        "burst-semantics",
        "window-algorithm",
        "window-alignment",
        "partial-response-bucket-rounding",
        "http-429-status",
        "error-body",
        "error-headers",
        "retry-after",
        "older-block-weight",
        "high-congestion-trigger",
    }


@pytest.mark.parametrize(
    "source_field", ["kind", "title", "canonical_location", "retrieved_at", "content_sha256"]
)
def test_unofficial_altered_or_stale_source_is_rejected_even_if_rehashed(
    source_field: str,
) -> None:
    data = _authority_dict()
    source = data["sources"][0]
    source[source_field] = {
        "kind": "UNOFFICIAL",
        "title": "Altered title",
        "canonical_location": "https://example.invalid/unofficial",
        "retrieved_at": "2026-07-12T04:24:41Z",
        "content_sha256": "1" * 64,
    }[source_field]
    payload = dict(source)
    payload.pop("source_hash")
    source["source_hash"] = _domain_hash(OFFICIAL_RATE_LIMIT_SOURCE_HASH_VERSION, payload)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


@pytest.mark.parametrize("attack", ["duplicate", "omit", "inject", "omit-unknown"])
def test_membership_attacks_are_rejected(attack: str) -> None:
    data = _authority_dict()
    if attack == "duplicate":
        data["documented_facts"] = data["documented_facts"] + (data["documented_facts"][0],)
    elif attack == "omit":
        data["documented_facts"] = data["documented_facts"][1:]
    elif attack == "inject":
        injected = dict(data["documented_facts"][0])
        injected["fact_id"] = "invented.retry-after"
        payload = dict(injected)
        payload.pop("fact_hash")
        injected["fact_hash"] = _domain_hash(OFFICIAL_RATE_LIMIT_FACT_HASH_VERSION, payload)
        data["documented_facts"] = data["documented_facts"] + (injected,)
    else:
        data["unresolved_fields"] = data["unresolved_fields"][1:]
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_tampered_instance_and_coherently_rehashed_dict_are_rejected() -> None:
    authority = build_official_rate_limit_authority()
    object.__setattr__(authority, "status", "OFFICIAL_NUMERIC_LIMIT_RESOLVED")
    with pytest.raises(ValidationError):
        validate_official_rate_limit_authority(authority)

    data = _authority_dict()
    data["unresolved_fields"] = data["unresolved_fields"][1:]
    payload = dict(data)
    payload.pop("authority_hash")
    data["authority_hash"] = _domain_hash(OFFICIAL_RATE_LIMIT_AUTHORITY_HASH_VERSION, payload)
    with pytest.raises(ValidationError):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_model_construct_copy_subclass_and_wrong_model_attacks_fail_closed() -> None:
    authority = build_official_rate_limit_authority()
    with pytest.raises(TypeError):
        OfficialRateLimitAuthorityV0.model_construct(**_authority_dict())
    with pytest.raises(TypeError):
        authority.model_copy()

    class AuthoritySubclass(OfficialRateLimitAuthorityV0):
        pass

    with pytest.raises(ValidationError, match="exact OfficialRateLimitAuthorityV0"):
        AuthoritySubclass(**_authority_dict())
    with pytest.raises(ValueError, match="exact OfficialRateLimitAuthorityV0"):
        validate_official_rate_limit_authority(authority.sources[0])  # type: ignore[arg-type]


def test_source_and_fact_models_cannot_be_constructed_or_copied() -> None:
    authority = build_official_rate_limit_authority()
    with pytest.raises(TypeError):
        OfficialRateLimitSourceV0.model_construct()
    with pytest.raises(TypeError):
        OfficialRateLimitFactV0.model_construct()
    with pytest.raises(TypeError):
        authority.sources[0].model_copy(update={"title": "changed"})
    with pytest.raises(TypeError):
        authority.documented_facts[0].model_copy(update={"numeric_value": 1201})


def test_authority_hash_is_deterministic_and_revalidated() -> None:
    first = build_official_rate_limit_authority()
    second = build_official_rate_limit_authority()
    assert first == second
    assert first.authority_hash == EXPECTED_AUTHORITY_HASH
    assert compute_official_rate_limit_authority_hash(first) == EXPECTED_AUTHORITY_HASH
    data = _authority_dict()
    data["authority_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="authority_hash"):
        OfficialRateLimitAuthorityV0.model_validate(data)


def test_source_catalog_hash_is_unchanged_and_document_is_strengthened() -> None:
    assert SOURCE_CATALOG_HASH == EXPECTED_SOURCE_CATALOG_HASH
    document = rate_limit_authority_document()
    assert document["authority_hash"] == EXPECTED_AUTHORITY_HASH
    assert len(document["documented_facts"]) == 27
    assert len(document["unresolved_fields"]) == 10
    assert document["transition_eligible"] is False


def test_contract_has_no_network_async_runtime_exchange_or_credentials_capability() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "src/trader_assist_v0/contracts/rate_limits.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        assert not isinstance(
            node, ast.AsyncFor | ast.AsyncFunctionDef | ast.AsyncWith | ast.Await
        )
    forbidden_imports = {
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
        name == bad or name.startswith(bad + ".") for name in imports for bad in forbidden_imports
    )
    assert "api.hyperliquid.xyz" not in text.lower()
    assert "/exchange" not in text.lower()
