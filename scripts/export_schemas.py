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


def _portable_schema(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                PORTABLE_DECIMAL_STRING_PATTERN
                if key == "pattern" and item == DECIMAL_STRING_PATTERN
                else _portable_schema(item)
            )
            for key, item in value.items()
        }
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
