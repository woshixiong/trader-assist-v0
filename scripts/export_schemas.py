from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from trader_assist_v0.contracts import (
    AIRecommendationV0,
    DataHealthEventV0,
    EvidenceBundleManifestV0,
    ExecutionPermitV0,
    HumanReviewDecisionV0,
    InstrumentPrecisionContractV0,
    NormalizedEventV0,
    OrderPackageV0,
    PromotionRecordV0,
    ProposalV0,
    RawEventV0,
    RequiredFeedContractV0,
    SeedProvenanceEntryV0,
    StrategyCandidateV0,
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
COMPACT_MODELS = frozenset({ProposalV0, StrategyCandidateV0})

PYDANTIC_DECIMAL_STRING_PATTERN = r"^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$"


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


def render(model: type[BaseModel]) -> str:
    schema = _portable_schema(model.model_json_schema())
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
