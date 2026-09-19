#!/usr/bin/env python3
# mypy: disable-error-code="import-not-found"
"""R3 Real-T2 status CLI and isolated restart worker."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, cast


def _rebuild(source: dict[str, object]) -> dict[str, object]:
    from nautilus_trader.model import CryptoPerpetual

    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.nautilus_e4.contracts import AdmittedEvent
    from trader_assist_v0.nautilus_g4.catalog_bridge import project_native_replay
    from trader_assist_v0.nautilus_g4.runner import execute_provider_native_state
    from trader_assist_v0.nautilus_g4.t2_shadow import (
        _EVALUATION_DOMAIN,
        _OUTCOME_DOMAIN,
        _STRUCTURAL_DOMAIN,
        RestartIdentitySet,
        project_cost_evidence,
    )
    from trader_assist_v0.vnext_g4.contracts import (
        CausalLineage,
        HypotheticalOrderIntent,
        ValidationReference,
    )
    from trader_assist_v0.vnext_g4.evaluator import EvaluationInputs
    from trader_assist_v0.vnext_g4.reporting import ThesisOutcome

    events = tuple(AdmittedEvent.model_validate(item) for item in cast(list[Any], source["events"]))
    projection = project_native_replay(
        events=events,
        market_id=str(source["market_id"]),
        expression_id=str(source["expression_id"]),
        instrument_id=str(source["instrument_id"]),
    )
    lineage = CausalLineage.model_validate(source["lineage"])
    evaluation = EvaluationInputs.model_validate(source["evaluation_inputs"])
    ValidationReference.model_validate(source["validation"])
    intent = HypotheticalOrderIntent.model_validate(source["intent"])
    outcome = ThesisOutcome.model_validate(source["outcome"])
    project_cost_evidence(outcome)
    decision = source["structural_decision"]
    if not isinstance(decision, dict) or decision.get("decision") != "FORMAL_SETUP_CONFIRMED":
        raise ValueError("serialized structural decision is not formal")
    from_dict = getattr(CryptoPerpetual, "from_dict", None)
    if not callable(from_dict):
        raise RuntimeError("CryptoPerpetual lacks exact public from_dict surface")
    instrument = from_dict(source["provider_instrument"])
    with tempfile.TemporaryDirectory(prefix="ta-r3-restart-") as catalog:
        evidence = execute_provider_native_state(
            projection=projection,
            intent=intent,
            trigger_admission_hash=str(source["trigger_admission_hash"]),
            provider_instrument=instrument,
            catalog_path=Path(catalog),
        )
    if outcome.provider_state_source_hash != evidence.record.provider_state.state_hash:
        raise ValueError("rebuilt provider state does not bind source ThesisOutcome")
    values = {
        "structural_decision_hash": sha256_hex(_STRUCTURAL_DOMAIN + canonical_json_bytes(decision)),
        "causal_lineage_hash": lineage.lineage_hash,
        "evaluation_inputs_hash": sha256_hex(
            _EVALUATION_DOMAIN + canonical_json_bytes(evaluation.model_dump(mode="json"))
        ),
        "order_intent_hash": intent.order_intent_hash,
        "provider_state_projection_hash": evidence.record.provider_state.state_hash,
        "outcome_report_hash": sha256_hex(
            _OUTCOME_DOMAIN + canonical_json_bytes(outcome.model_dump(mode="json"))
        ),
    }
    return RestartIdentitySet.create(**values).model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-identities", action="store_true")
    args = parser.parse_args()
    if not args.rebuild_identities:
        print("R3_RUNTIME_T2_STATUS=NONDECISIVE_REAL_INPUT_ABSENT")
        print("REAL_T2_CREDIT=NO")
        return 0
    request = json.load(sys.stdin)
    if set(request) != {"source_bundle_hash", "source"}:
        raise ValueError("fresh-process worker accepts only immutable source inputs")
    source = request["source"]
    if not isinstance(source, dict) or "identity_set" in source:
        raise ValueError("copied original identity sets are forbidden")
    print(
        json.dumps(
            {"pid": os.getpid(), "identity_set": _rebuild(source)},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
