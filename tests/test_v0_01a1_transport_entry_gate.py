from __future__ import annotations

import pytest

from trader_assist_v0.contracts.source_catalog import (
    PUBLIC_READ_ONLY_ENVIRONMENT,
    PUBLIC_READ_ONLY_OPERATION_CLASS,
    RATE_LIMIT_STATUS,
    SOURCE_ID,
    assert_rate_limit_allows_live_transport,
    rate_limit_entry_gate,
    validate_a1_to_a2_gate,
    validate_read_only_transport_entry,
)


def test_unresolved_rate_limit_blocks_live_transport_authorization() -> None:
    gate = rate_limit_entry_gate()

    assert RATE_LIMIT_STATUS == "UNRESOLVED_OFFICIAL_LIMIT"
    assert gate["status"] == "UNRESOLVED_OFFICIAL_LIMIT"
    assert gate["numeric_limits_resolved"] is False
    assert gate["live_transport_authorized"] is False
    with pytest.raises(ValueError, match="unresolved"):
        assert_rate_limit_allows_live_transport()


def test_read_only_transport_entry_accepts_only_public_mainnet_config() -> None:
    ws_entry = validate_read_only_transport_entry(
        source_id=SOURCE_ID,
        environment=PUBLIC_READ_ONLY_ENVIRONMENT,
        endpoint_id="hl-ws-mainnet-public",
        operation_type="candle",
        coin="ETH",
        interval="1m",
        capture_mode="WS_TEXT_UTF8_APPLICATION_PAYLOAD",
        operation_class=PUBLIC_READ_ONLY_OPERATION_CLASS,
    )
    assert ws_entry.endpoint_kind == "WEBSOCKET"

    info_entry = validate_read_only_transport_entry(
        source_id=SOURCE_ID,
        environment=PUBLIC_READ_ONLY_ENVIRONMENT,
        endpoint_id="hl-info-mainnet-public",
        operation_type="allMids",
        capture_mode="HTTP_RESPONSE_BODY",
        operation_class=PUBLIC_READ_ONLY_OPERATION_CLASS,
    )
    assert info_entry.endpoint_kind == "INFO"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source_id": "other-source"},
        {"environment": "mainnet execution"},
        {"operation_class": "order mutation"},
        {"endpoint_id": "hl-private-mainnet"},
        {"endpoint_id": "hl-user-mainnet"},
        {"endpoint_id": "hl-account-mainnet"},
        {"operation_type": "/exchange"},
        {"operation_type": "order"},
        {"operation_type": "nonce"},
        {"capture_mode": "HTTP_RESPONSE_BODY"},
        {"coin": "SOL"},
        {"interval": "30m"},
    ],
)
def test_read_only_transport_entry_rejects_unsupported_or_write_classes(
    kwargs: dict[str, str],
) -> None:
    request = {
        "source_id": SOURCE_ID,
        "environment": PUBLIC_READ_ONLY_ENVIRONMENT,
        "endpoint_id": "hl-ws-mainnet-public",
        "operation_type": "candle",
        "coin": "ETH",
        "interval": "1m",
        "capture_mode": "WS_TEXT_UTF8_APPLICATION_PAYLOAD",
        "operation_class": PUBLIC_READ_ONLY_OPERATION_CLASS,
    }
    request.update(kwargs)

    with pytest.raises(ValueError):
        validate_read_only_transport_entry(**request)


def test_a1_to_a2_gate_requires_all_authorities() -> None:
    with pytest.raises(ValueError, match="A2 gate"):
        validate_a1_to_a2_gate(
            a1_pr_merged=True,
            external_exact_head_review_passed=True,
            rate_limit_entry_gate_explicit=True,
            public_source_envelope_contract_frozen=True,
            new_exact_head_lease_granted=False,
        )

    validate_a1_to_a2_gate(
        a1_pr_merged=True,
        external_exact_head_review_passed=True,
        rate_limit_entry_gate_explicit=True,
        public_source_envelope_contract_frozen=True,
        new_exact_head_lease_granted=True,
    )
