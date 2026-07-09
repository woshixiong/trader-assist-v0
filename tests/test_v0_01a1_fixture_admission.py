from __future__ import annotations

import json
from pathlib import Path

import pytest

from trader_assist_v0.contracts.source_catalog import (
    FIXTURE_ALLOWED_PROVENANCE,
    validate_fixture_admission,
)


def test_synthetic_documentation_derived_candle_fixture_is_allowed() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "hyperliquid"
        / "v0_01a1"
        / "candle_envelopes.json"
    )
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert data["provenance"] in FIXTURE_ALLOWED_PROVENANCE
    validate_fixture_admission(
        provenance=data["provenance"],
        payload_text=data["single_candle_payload"],
        sanitized=True,
    )
    validate_fixture_admission(
        provenance=data["provenance"],
        payload_text=data["array_candle_payload"],
        sanitized=True,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"provenance": "LIVE_OBSERVATION"},
        {"sanitized": False},
        {"raw_operational": True},
        {"private_or_account_data": True},
        {"contains_secret": True},
        {"payload_text": '{"api_key":"redacted"}'},
        {"payload_text": '{"signature":"redacted"}'},
        {"payload_text": '{"nonce":123}'},
        {"payload_text": '{"database":"bronze.db"}'},
        {"payload_text": '{"cache":"runtime-cache"}'},
        {"payload_text": '{"address":"0x1111111111111111111111111111111111111111"}'},
        {"payload_text": '{"log":"runtime observation"}'},
        {"payload_text": '{"db":"bronze.db"}'},
        {"payload_text": '{"authorization":"Bearer redacted"}'},
        {"payload_text": '{"password":"redacted"}'},
        {"payload_text": '{"token":"redacted"}'},
    ],
)
def test_fixture_admission_rejects_operational_private_or_secret_material(
    kwargs: dict[str, object],
) -> None:
    request: dict[str, object] = {
        "provenance": "SYNTHETIC_DOCUMENTATION_DERIVED",
        "payload_text": '{"channel":"candle","data":{"s":"ETH","i":"1m"}}',
        "sanitized": True,
    }
    request.update(kwargs)

    with pytest.raises(ValueError):
        validate_fixture_admission(**request)
