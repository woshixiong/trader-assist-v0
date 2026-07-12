from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from trader_assist_v0.contracts import (
    AIRecommendationV0,
    BronzeReplayReportV0,
    CandleCrossSourceReconciliationV0,
    CandlePayloadExtractionV0,
    DataHealthEventV0,
    EvidenceBundleManifestV0,
    ExecutionPermitV0,
    HumanReviewDecisionV0,
    InstrumentPrecisionContractV0,
    NormalizedEventV0,
    OfficialRateLimitAuthorityV0,
    OrderPackageV0,
    PromotionRecordV0,
    ProposalV0,
    RawEventV0,
    RawManifestCheckpointV0,
    RawManifestEntryV0,
    RequiredFeedContractV0,
    SeedProvenanceEntryV0,
    StrategyCandidateV0,
)
from trader_assist_v0.contracts.candle_reconciliation import (
    A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN,
)
from trader_assist_v0.contracts.common import (
    FINITE_DECIMAL_STRING_PATTERN,
    MAX_DECIMAL_WIRE_LENGTH,
    NONNEGATIVE_DECIMAL_STRING_PATTERN,
    POSITIVE_DECIMAL_STRING_PATTERN,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schemas" / "v0"
MODELS: tuple[type[BaseModel], ...] = (
    RawEventV0,
    RawManifestEntryV0,
    RawManifestCheckpointV0,
    BronzeReplayReportV0,
    CandlePayloadExtractionV0,
    CandleCrossSourceReconciliationV0,
    OfficialRateLimitAuthorityV0,
    RequiredFeedContractV0,
    InstrumentPrecisionContractV0,
    NormalizedEventV0,
    DataHealthEventV0,
    StrategyCandidateV0,
    AIRecommendationV0,
    OrderPackageV0,
    ProposalV0,
    HumanReviewDecisionV0,
    PromotionRecordV0,
    ExecutionPermitV0,
    EvidenceBundleManifestV0,
    SeedProvenanceEntryV0,
)
COMPACT_MODELS = frozenset(
    {
        BronzeReplayReportV0,
        ProposalV0,
        RawEventV0,
        RawManifestCheckpointV0,
        RawManifestEntryV0,
        StrategyCandidateV0,
    }
)

PYDANTIC_DECIMAL_STRING_PATTERN = r"^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$"
A6_SCHEMA_BOUNDARY_DESCRIPTION = (
    "Portable structural validation for the A6 reconciliation report. This artifact "
    "enforces JSON-Schema-expressible authority constraints only, including complete "
    "serialized A5 field presence, root WebSocket/Info extraction roles, integer "
    "field-difference value kinds, and portable absolute-end string patterns. Complete "
    "A6 authority validation requires CandleCrossSourceReconciliationV0 runtime semantic "
    "validation for hashes, exact A5 authority, membership, ordering, counts, differences, "
    "and complete logical-key union proof. Schema validation alone does not authenticate "
    "an A6 reconciliation report."
)
OFFICIAL_RATE_LIMIT_SCHEMA_BOUNDARY_DESCRIPTION = (
    "Schema validation proves serialized structure only. It does not authenticate "
    "official sources, exact fact or unknown membership, ordering, duplicate/conflict "
    "rules, semantic evidence, hashes, or transition authority. Pydantic models are "
    "untrusted structural containers; authority requires raw-material reauthentication "
    "with authenticate_official_rate_limit_authority_json at every consumer boundary."
)


def _decimal_pattern(constraints: dict[str, Any]) -> str:
    if constraints.get("exclusiveMinimum") == 0.0 or constraints.get("gt") == "0":
        return POSITIVE_DECIMAL_STRING_PATTERN
    if constraints.get("minimum") == 0.0 or constraints.get("ge") == "0":
        return NONNEGATIVE_DECIMAL_STRING_PATTERN
    return FINITE_DECIMAL_STRING_PATTERN


def _portable_schema(value: Any) -> Any:
    if isinstance(value, dict):
        converted = {key: _portable_schema(item) for key, item in value.items()}
        decimal_patterns = {
            PYDANTIC_DECIMAL_STRING_PATTERN,
            FINITE_DECIMAL_STRING_PATTERN,
            NONNEGATIVE_DECIMAL_STRING_PATTERN,
            POSITIVE_DECIMAL_STRING_PATTERN,
        }
        if value.get("type") == "string" and value.get("pattern") in decimal_patterns:
            converted["pattern"] = _decimal_pattern(value)
            converted["maxLength"] = MAX_DECIMAL_WIRE_LENGTH
            converted.pop("gt", None)
            converted.pop("ge", None)

        branches = value.get("anyOf")
        if isinstance(branches, list):
            number_branch = next(
                (
                    branch
                    for branch in branches
                    if isinstance(branch, dict) and branch.get("type") == "number"
                ),
                None,
            )
            decimal_string_branch = next(
                (
                    branch
                    for branch in branches
                    if isinstance(branch, dict)
                    and branch.get("type") == "string"
                    and branch.get("pattern") in decimal_patterns
                ),
                None,
            )
            if number_branch is not None and decimal_string_branch is not None:
                string_wire = {
                    "type": "string",
                    "pattern": _decimal_pattern(value),
                    "maxLength": MAX_DECIMAL_WIRE_LENGTH,
                }
                null_branches = [
                    _portable_schema(branch)
                    for branch in branches
                    if isinstance(branch, dict) and branch.get("type") == "null"
                ]
                converted.pop("anyOf", None)
                converted.pop("gt", None)
                converted.pop("ge", None)
                if null_branches:
                    converted["anyOf"] = [string_wire, *null_branches]
                else:
                    converted.update(string_wire)
        return converted
    if isinstance(value, list):
        return [_portable_schema(item) for item in value]
    return value


def _has_terminal_unescaped_dollar(pattern: str) -> bool:
    if not pattern.endswith("$"):
        return False
    backslash_count = 0
    index = len(pattern) - 2
    while index >= 0 and pattern[index] == "\\":
        backslash_count += 1
        index -= 1
    return backslash_count % 2 == 0


def _portable_a6_absolute_end_patterns(value: Any) -> Any:
    if isinstance(value, dict):
        converted = {
            key: _portable_a6_absolute_end_patterns(item)
            for key, item in value.items()
        }
        pattern = value.get("pattern")
        if (
            isinstance(pattern, str)
            and pattern.startswith("^")
            and _has_terminal_unescaped_dollar(pattern)
        ):
            converted["pattern"] = pattern[:-1] + r"(?![\s\S])"
        return converted
    if isinstance(value, list):
        return [_portable_a6_absolute_end_patterns(item) for item in value]
    return value


def _a6_authority_schema(schema: dict[str, Any]) -> dict[str, Any]:
    definitions = schema.get("$defs")
    if not isinstance(definitions, dict):
        raise ValueError("A6 schema is missing definitions")
    authority = definitions.get("CandleCrossSourceInputAuthorityV0")
    comparison = definitions.get("CandleCrossSourceComparisonItemV0")
    difference = definitions.get("CandleCrossSourceFieldDifferenceV0")
    extraction = definitions.get("CandlePayloadExtractionV0")
    candle = definitions.get("ExtractedCandleV0")
    if not all(
        isinstance(item, dict)
        for item in (authority, comparison, difference, extraction, candle)
    ):
        raise ValueError("A6 schema is missing authority definitions")

    assert isinstance(authority, dict)
    assert isinstance(comparison, dict)
    assert isinstance(difference, dict)
    assert isinstance(extraction, dict)
    assert isinstance(candle, dict)

    schema["$comment"] = A6_SCHEMA_BOUNDARY_DESCRIPTION
    schema["description"] = A6_SCHEMA_BOUNDARY_DESCRIPTION

    root_properties = schema.get("properties")
    if not isinstance(root_properties, dict):
        raise ValueError("A6 schema is missing root properties")
    ws_extraction = root_properties.get("ws_extraction")
    info_extraction = root_properties.get("info_extraction")
    if not isinstance(ws_extraction, dict) or not isinstance(info_extraction, dict):
        raise ValueError("A6 schema is missing root extraction properties")
    root_properties["ws_extraction"] = {
        "allOf": [
            ws_extraction,
            {
                "properties": {
                    "endpoint_id": {"const": "hl-ws-mainnet-public"},
                    "operation_type": {"const": "candle"},
                    "envelope_shape": {
                        "enum": ["WS_DATA_CANDLE", "WS_DATA_CANDLE_ARRAY"]
                    },
                }
            },
        ]
    }
    root_properties["info_extraction"] = {
        "allOf": [
            info_extraction,
            {
                "properties": {
                    "endpoint_id": {"const": "hl-info-mainnet-public"},
                    "operation_type": {"const": "candleSnapshot"},
                    "envelope_shape": {"const": "INFO_CANDLE_ARRAY"},
                }
            },
        ]
    }

    authority["description"] = (
        "A6 input authority with a JSON-Schema-enforced WS or Info endpoint, operation, "
        "and envelope role."
    )
    authority["oneOf"] = [
        {
            "properties": {
                "side": {"const": "WS"},
                "endpoint_id": {"const": "hl-ws-mainnet-public"},
                "operation_type": {"const": "candle"},
                "envelope_shape": {
                    "enum": ["WS_DATA_CANDLE", "WS_DATA_CANDLE_ARRAY"]
                },
            }
        },
        {
            "properties": {
                "side": {"const": "INFO"},
                "endpoint_id": {"const": "hl-info-mainnet-public"},
                "operation_type": {"const": "candleSnapshot"},
                "envelope_shape": {"const": "INFO_CANDLE_ARRAY"},
            }
        },
    ]

    extraction_required = [
        "schema_version",
        "contract_id",
        "extraction_version",
        "source_id",
        "source_event_id",
        "payload_sha256",
        "endpoint_id",
        "operation_type",
        "coin",
        "candle_interval",
        "envelope_shape",
        "candles",
        "extraction_hash",
    ]
    extraction["required"] = extraction_required
    extraction["description"] = (
        "Complete embedded A5 extraction authority. Every serialized authority field is "
        "required at the A6 boundary; runtime independently revalidates hashes, candle "
        "logical keys, duplicates, and the frozen source role."
    )
    extraction_properties = extraction.get("properties")
    if not isinstance(extraction_properties, dict):
        raise ValueError("A6 embedded extraction schema is missing properties")
    for field_name in extraction_required:
        field_schema = extraction_properties.get(field_name)
        if isinstance(field_schema, dict):
            field_schema.pop("default", None)

    candle_required = [
        "candle_logical_key",
        "open_time_ms",
        "close_time_ms",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_base",
        "trade_count",
    ]
    candle["required"] = candle_required
    candle["description"] = (
        "Complete embedded A5 candle authority. Runtime validation is required to prove "
        "logical-key and extraction membership authority."
    )

    difference["description"] = (
        "A6 exact field difference. close_time_ms and trade_count values use canonical "
        "nonnegative ASCII integer strings; other comparable values use canonical finite "
        "decimal strings."
    )
    difference["allOf"] = [
        {
            "if": {
                "properties": {
                    "field_name": {"enum": ["close_time_ms", "trade_count"]}
                },
                "required": ["field_name"],
            },
            "then": {
                "properties": {
                    "ws_value": {
                        "type": "string",
                        "pattern": A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN,
                    },
                    "info_value": {
                        "type": "string",
                        "pattern": A6_CANONICAL_NONNEGATIVE_INTEGER_STRING_PATTERN,
                    },
                }
            },
        }
    ]

    present = {"not": {"type": "null"}}
    absent = {"type": "null"}
    comparison["description"] = (
        "A6 comparison item with JSON-Schema-enforced source presence and difference "
        "cardinality for MATCH, CONFLICT, WS_ONLY, and INFO_ONLY."
    )
    comparison["oneOf"] = [
        {
            "properties": {
                "status": {"const": "MATCH"},
                "ws_candle": present,
                "ws_authority": present,
                "info_candle": present,
                "info_authority": present,
                "field_differences": {"maxItems": 0},
            }
        },
        {
            "properties": {
                "status": {"const": "CONFLICT"},
                "ws_candle": present,
                "ws_authority": present,
                "info_candle": present,
                "info_authority": present,
                "field_differences": {"minItems": 1},
            }
        },
        {
            "properties": {
                "status": {"const": "WS_ONLY"},
                "ws_candle": present,
                "ws_authority": present,
                "info_candle": absent,
                "info_authority": absent,
                "field_differences": {"maxItems": 0},
            }
        },
        {
            "properties": {
                "status": {"const": "INFO_ONLY"},
                "ws_candle": absent,
                "ws_authority": absent,
                "info_candle": present,
                "info_authority": present,
                "field_differences": {"maxItems": 0},
            }
        },
    ]
    return schema


def _official_rate_limit_authority_schema(schema: dict[str, Any]) -> dict[str, Any]:
    def require_complete_serialization(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            properties = value.get("properties")
            if isinstance(properties, dict):
                value["additionalProperties"] = False
                value["required"] = list(properties)
            for item in value.values():
                require_complete_serialization(item)
        elif isinstance(value, list):
            for item in value:
                require_complete_serialization(item)

    require_complete_serialization(schema)
    schema["$comment"] = OFFICIAL_RATE_LIMIT_SCHEMA_BOUNDARY_DESCRIPTION
    schema["description"] = OFFICIAL_RATE_LIMIT_SCHEMA_BOUNDARY_DESCRIPTION
    return schema


def render(model: type[BaseModel]) -> str:
    schema = _portable_schema(model.model_json_schema())
    if model is CandleCrossSourceReconciliationV0:
        schema = _a6_authority_schema(schema)
        schema = _portable_a6_absolute_end_patterns(schema)
    if model is OfficialRateLimitAuthorityV0:
        schema = _official_rate_limit_authority_schema(schema)
    if model in COMPACT_MODELS:
        return json.dumps(
            schema,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for model in MODELS:
        path = OUT / f"{model.__name__}.schema.json"
        expected = render(model)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                failures.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(expected, encoding="utf-8")
    if failures:
        raise SystemExit("schema drift: " + ", ".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
