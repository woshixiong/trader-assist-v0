from __future__ import annotations

import ast
import inspect

import pytest

from trader_assist_v0.contracts import source_catalog
from trader_assist_v0.contracts.source_catalog import (
    A3_CONTRACT_ID,
    PUBLIC_READ_ONLY_ENVIRONMENT,
    PUBLIC_READ_ONLY_OPERATION_CLASS,
    RATE_LIMIT_STATUS,
    SOURCE_ID,
    validate_public_readonly_transport_preflight,
    validate_read_only_transport_entry,
)


def _valid_ws_request() -> dict[str, object]:
    return {
        "source_id": SOURCE_ID,
        "environment": PUBLIC_READ_ONLY_ENVIRONMENT,
        "endpoint_id": "hl-ws-mainnet-public",
        "operation_type": "candle",
        "coin": "ETH",
        "interval": "1m",
        "capture_mode": "WS_TEXT_UTF8_APPLICATION_PAYLOAD",
        "operation_class": PUBLIC_READ_ONLY_OPERATION_CLASS,
    }


def _valid_info_request() -> dict[str, object]:
    return {
        "source_id": SOURCE_ID,
        "environment": PUBLIC_READ_ONLY_ENVIRONMENT,
        "endpoint_id": "hl-info-mainnet-public",
        "operation_type": "allMids",
        "capture_mode": "HTTP_RESPONSE_BODY",
        "operation_class": PUBLIC_READ_ONLY_OPERATION_CLASS,
    }


def test_valid_ws_candle_preflight_is_accepted_but_runtime_disabled() -> None:
    result = validate_public_readonly_transport_preflight(**_valid_ws_request())

    assert result["task_id"] == A3_CONTRACT_ID
    assert result["endpoint_kind"] == "WEBSOCKET"
    assert result["runtime_enabled"] is False
    assert result["live_transport_authorized"] is False
    assert result["rate_limit_status"] == "UNRESOLVED_OFFICIAL_LIMIT"


def test_valid_info_all_mids_preflight_is_accepted_but_runtime_disabled() -> None:
    result = validate_public_readonly_transport_preflight(**_valid_info_request())

    assert result["task_id"] == A3_CONTRACT_ID
    assert result["endpoint_kind"] == "INFO"
    assert result["runtime_enabled"] is False
    assert result["live_transport_authorized"] is False


def test_rate_limit_status_remains_unresolved() -> None:
    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"


def test_runtime_enabled_defaults_false() -> None:
    result = validate_public_readonly_transport_preflight(**_valid_ws_request())

    assert result["runtime_enabled"] is False
    assert result["live_transport_authorized"] is False


def test_runtime_enabled_true_fails_while_rate_limits_unresolved() -> None:
    request = _valid_ws_request()
    request["runtime_enabled"] = True

    with pytest.raises(ValueError, match="rate limit unresolved"):
        validate_public_readonly_transport_preflight(**request)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kill_switch_enabled": False},
        {"config_keys": ("kill_switch_bypass",)},
        {"config_values": ("kill switch override",)},
    ],
)
def test_kill_switch_disabled_bypass_or_override_fails_closed(
    kwargs: dict[str, object],
) -> None:
    request = _valid_ws_request()
    request.update(kwargs)

    with pytest.raises(ValueError):
        validate_public_readonly_transport_preflight(**request)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation_type": "/exchange"},
        {"endpoint_id": "hl-private-mainnet"},
        {"endpoint_id": "hl-user-mainnet"},
        {"endpoint_id": "hl-account-mainnet"},
        {"operation_type": "order"},
        {"operation_type": "orderUpdates"},
        {"operation_type": "userFills"},
        {"operation_type": "userEvents"},
        {"operation_type": "openOrders"},
        {"operation_type": "userFundings"},
        {"config_keys": ("api_key",)},
        {"config_keys": ("authorization_token",)},
        {"config_keys": ("wallet",)},
        {"config_keys": ("signing_nonce",)},
        {"config_keys": ("account_address",)},
        {"config_values": ("testnet execution",)},
        {"config_values": ("Mainnet execution enablement",)},
        {"coin": "SOL"},
        {"interval": "30m"},
        {"capture_mode": "RAW_BYTES"},
    ],
)
def test_preflight_rejects_forbidden_or_unsupported_material(
    kwargs: dict[str, object],
) -> None:
    request = _valid_ws_request()
    request.update(kwargs)

    with pytest.raises(ValueError):
        validate_public_readonly_transport_preflight(**request)


def test_preflight_rejects_capture_mode_mismatch_by_endpoint_kind() -> None:
    request = _valid_info_request()
    request["capture_mode"] = "WS_TEXT_UTF8_APPLICATION_PAYLOAD"

    with pytest.raises(ValueError, match="capture mode"):
        validate_public_readonly_transport_preflight(**request)


def test_existing_a1_entry_gate_remains_compatible() -> None:
    entry = validate_read_only_transport_entry(**_valid_ws_request())

    assert entry.endpoint_kind == "WEBSOCKET"
    assert entry.operation_type == "candle"


def test_source_catalog_has_no_network_imports_or_async_syntax() -> None:
    tree = ast.parse(inspect.getsource(source_catalog))
    forbidden_imports = {
        "aiohttp",
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
    imported_modules: set[str] = set()
    forbidden_async_nodes = (
        ast.AsyncFunctionDef,
        ast.AsyncFor,
        ast.AsyncWith,
        ast.Await,
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        elif isinstance(node, forbidden_async_nodes):
            raise AssertionError("source catalog must not contain async syntax")

    assert imported_modules.isdisjoint(forbidden_imports)
