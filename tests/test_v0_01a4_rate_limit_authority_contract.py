from __future__ import annotations

import ast
from pathlib import Path

import pytest

from trader_assist_v0.contracts.source_catalog import (
    A4_CONTRACT_ID,
    RATE_LIMIT_ALLOWED_STATUSES,
    RATE_LIMIT_OFFICIAL_SOURCE_LOCATION,
    RATE_LIMIT_OFFICIAL_SOURCE_TITLE,
    RATE_LIMIT_STATUS,
    assert_rate_limit_allows_live_transport,
    rate_limit_authority_document,
    rate_limit_entry_gate,
    source_catalog_document,
    validate_official_rate_limit_authority,
)


def test_a4_current_rate_limit_authority_remains_unresolved_fail_closed() -> None:
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert RATE_LIMIT_ALLOWED_STATUSES == (
        "UNRESOLVED_OFFICIAL_LIMIT",
        "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
    )

    document = rate_limit_authority_document()
    assert document["task_id"] == A4_CONTRACT_ID
    assert document["status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert document["official_source_title"] == RATE_LIMIT_OFFICIAL_SOURCE_TITLE
    assert document["official_source_location"] == RATE_LIMIT_OFFICIAL_SOURCE_LOCATION
    assert document["source_kind"] == "official"
    assert document["official_source_readable"] is False
    assert document["numeric_limits_resolved"] is False
    assert document["numeric_limit_fields"] == ()
    assert document["limit_units"] == ()
    assert document["operation_scope"] == ()
    assert document["ambiguous_fields"]
    assert document["live_transport_authorized"] is False


def test_a4_existing_rate_limit_entry_gate_still_blocks_live_transport() -> None:
    gate = rate_limit_entry_gate()
    assert gate["status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert gate["numeric_limits_resolved"] is False
    assert gate["live_transport_authorized"] is False

    with pytest.raises(ValueError, match="unresolved"):
        assert_rate_limit_allows_live_transport()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"runtime_enabled": True},
        {"live_transport_requested": True},
    ],
)
def test_a4_rate_limit_authority_never_enables_runtime(kwargs: dict[str, bool]) -> None:
    with pytest.raises(ValueError, match="live runtime"):
        validate_official_rate_limit_authority(**kwargs)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        (
            {"source_kind": "community"},
            "frozen official source",
        ),
        (
            {"official_source_title": "community notes"},
            "frozen official source",
        ),
        (
            {"official_source_location": "discord"},
            "frozen official source",
        ),
        (
            {
                "source_kind": "model-memory",
                "official_source_title": "remembered rate limit",
                "official_source_location": "blog/forum",
            },
            "frozen official source",
        ),
        (
            {"numeric_limit_fields": ("request_budget",)},
            "numeric rate-limit material",
        ),
        (
            {"limit_units": ("documented_unit",)},
            "numeric rate-limit material",
        ),
        (
            {"operation_scope": ("public_info",)},
            "numeric rate-limit material",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "source_kind": "community",
                "official_source_title": "community notes",
                "official_source_location": "community forum",
                "official_source_readable": True,
                "numeric_limit_fields": ("request_budget",),
                "limit_units": ("documented_unit",),
                "operation_scope": ("public_info",),
            },
            "official source",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "official_source_readable": False,
                "numeric_limit_fields": ("request_budget",),
                "limit_units": ("documented_unit",),
                "operation_scope": ("public_info",),
            },
            "readable",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "official_source_readable": True,
                "numeric_limit_fields": ("request_budget",),
                "limit_units": ("documented_unit",),
                "operation_scope": ("public_info",),
                "ambiguous_fields": ("missing unit",),
            },
            "ambiguous",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "official_source_readable": True,
                "limit_units": ("documented_unit",),
                "operation_scope": ("public_info",),
            },
            "numeric field names",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "official_source_readable": True,
                "numeric_limit_fields": ("request_budget",),
                "operation_scope": ("public_info",),
            },
            "limit units",
        ),
        (
            {
                "status": "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
                "official_source_readable": True,
                "numeric_limit_fields": ("request_budget",),
                "limit_units": ("documented_unit",),
            },
            "operation scope",
        ),
    ],
)
def test_a4_rejects_unofficial_ambiguous_or_incomplete_rate_limit_authority(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        validate_official_rate_limit_authority(**kwargs)


def test_a4_resolved_candidate_requires_complete_official_metadata_but_no_runtime() -> None:
    candidate = validate_official_rate_limit_authority(
        status="OFFICIAL_NUMERIC_LIMIT_RESOLVED",
        official_source_readable=True,
        numeric_limit_fields=("request_budget",),
        limit_units=("documented_unit",),
        operation_scope=("public_info",),
    )

    assert candidate["task_id"] == A4_CONTRACT_ID
    assert candidate["status"] == "OFFICIAL_NUMERIC_LIMIT_RESOLVED"
    assert candidate["official_source_title"] == RATE_LIMIT_OFFICIAL_SOURCE_TITLE
    assert candidate["official_source_location"] == RATE_LIMIT_OFFICIAL_SOURCE_LOCATION
    assert candidate["official_source_readable"] is True
    assert candidate["numeric_limits_resolved"] is True
    assert candidate["numeric_limit_fields"] == ("request_budget",)
    assert candidate["limit_units"] == ("documented_unit",)
    assert candidate["operation_scope"] == ("public_info",)
    assert candidate["ambiguous_fields"] == ()
    assert candidate["live_transport_authorized"] is False


def test_a4_authority_document_does_not_mutate_source_catalog_hash_input() -> None:
    catalog_document = source_catalog_document()
    authority_document = rate_limit_authority_document()

    assert catalog_document["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert "rate_limit_allowed_statuses" not in catalog_document
    assert authority_document["status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert RATE_LIMIT_ALLOWED_STATUSES == (
        "UNRESOLVED_OFFICIAL_LIMIT",
        "OFFICIAL_NUMERIC_LIMIT_RESOLVED",
    )


FORBIDDEN_IMPORTS = {
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
FORBIDDEN_ASYNC_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
)
FORBIDDEN_RUNTIME_TEXT = (
    "api.hyperliquid.xyz",
    "testnet",
    "/exchange",
)


def test_a4_source_catalog_has_no_network_or_async_capability() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    path = repository_root / "src/trader_assist_v0/contracts/source_catalog.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        assert not isinstance(node, FORBIDDEN_ASYNC_NODES)

    assert not any(
        any(name == bad or name.startswith(bad + ".") for bad in FORBIDDEN_IMPORTS)
        for name in imports
    )

    lowered = text.lower()
    assert all(marker not in lowered for marker in FORBIDDEN_RUNTIME_TEXT)
