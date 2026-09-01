"""Stable incident vocabulary that points to existing deterministic regressions."""

from __future__ import annotations

import ast
import json
from pathlib import Path

CORPUS = Path(__file__).parent / "fixtures/canonical_incidents.json"
REQUIRED_FIELDS = {
    "INCIDENT_ID",
    "OBSERVED_HIGH_LEVEL_FAILURE",
    "LOWEST_REPRODUCIBLE_CONTRACT",
    "GENERALIZED_INVARIANT",
    "PRODUCTION_COMPOSITION_SCENARIO",
    "RELEASE_OR_HOST_RELEVANCE",
    "FIXED_REGRESSION_ID",
}
CANONICAL_INVARIANTS = {
    "CROSS_LAYER_CONTRACT_CLOSURE",
    "ADMITTED_INPUT_TOTALITY",
    "PRODUCTION_PATH_FIDELITY",
    "VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY",
    "INCIDENT_TO_INVARIANT_CONVERGENCE",
}


def test_canonical_incident_corpus_is_complete_unique_and_bound_to_real_tests() -> None:
    values = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert [item["INCIDENT_ID"] for item in values] == [
        "#119",
        "#129",
        "#131",
        "#134",
        "#136",
        "#138",
    ]
    assert all(set(item) == REQUIRED_FIELDS for item in values)
    assert all(item["GENERALIZED_INVARIANT"] in CANONICAL_INVARIANTS for item in values)
    for item in values:
        path_text, function_name = item["FIXED_REGRESSION_ID"].split("::", 1)
        path = Path(__file__).parents[1] / path_text
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        assert function_name in functions, item["FIXED_REGRESSION_ID"]
