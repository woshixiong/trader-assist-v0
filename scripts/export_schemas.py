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

DECIMAL_STRING_PATTERN = r"^(?!^[-+.]*$)[+-]?0*\d*\.?\d*$"
PORTABLE_DECIMAL_STRING_PATTERN = r"^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"
POSITIVE_DECIMAL_STRING_PATTERN = (
    r"^\+?(?=[0-9.]*[1-9])(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"
)
NONNEGATIVE_DECIMAL_STRING_PATTERN = r"^\+?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"


def _decimal_pattern(number_branch: dict[str, Any]) -> str:
    if number_branch.get("exclusiveMinimum") == 0.0:
        return POSITIVE_DECIMAL_STRING_PATTERN
    if number_branch.get("minimum") == 0.0:
        return NONNEGATIVE_DECIMAL_STRING_PATTERN
    return PORTABLE_DECIMAL_STRING_PATTERN


def _portable_schema(value: Any) -> Any:
    if isinstance(value, dict):
        converted = {key: _portable_schema(item) for key, item in value.items()}
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
                    and branch.get("pattern") == DECIMAL_STRING_PATTERN
                ),
                None,
            )
            if number_branch is not None and decimal_string_branch is not None:
                string_wire = {
                    "type": "string",
                    "pattern": _decimal_pattern(number_branch),
                }
                null_branches = [
                    _portable_schema(branch)
                    for branch in branches
                    if isinstance(branch, dict) and branch.get("type") == "null"
                ]
                converted.pop("anyOf", None)
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
