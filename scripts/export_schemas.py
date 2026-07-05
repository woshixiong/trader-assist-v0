from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from trader_assist_v0.contracts import (
    AIRecommendationV0,
    DataHealthEventV0,
    EvidenceBundleManifestV0,
    ExecutionPermitV0,
    HumanReviewDecisionV0,
    NormalizedEventV0,
    OrderPackageV0,
    PromotionRecordV0,
    ProposalV0,
    RawEventV0,
    SeedProvenanceEntryV0,
    StrategyCandidateV0,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schemas" / "v0"
MODELS: tuple[type[BaseModel], ...] = (
    RawEventV0,
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


def render(model: type[BaseModel]) -> str:
    return json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


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
            if not path.exists():
                failures.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(expected, encoding="utf-8")
        else:
            path.write_text(expected, encoding="utf-8")
    if failures:
        raise SystemExit("missing schemas: " + ", ".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
