from __future__ import annotations

import subprocess
import sys
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trader_assist_v0.nautilus_g4.t2_shadow import (
    CostClaimState,
    CostEvidence,
    RealT2Artifact,
    ReplayEquivalence,
    RestartIdentitySet,
    project_cost_evidence,
)
from trader_assist_v0.vnext_g4.contracts import ParticipationDecision
from trader_assist_v0.vnext_g4.reporting import CostComponent, CostProvenance, ThesisOutcome

H = "a" * 64


def component(provenance: CostProvenance, amount: Decimal | None = Decimal("1")) -> CostComponent:
    if provenance is CostProvenance.NOT_APPLICABLE:
        amount = None
    if provenance is CostProvenance.PROVEN_ZERO:
        amount = Decimal("0")
    if provenance is CostProvenance.MISSING:
        return CostComponent(provenance=provenance, reason="not observed")
    return CostComponent(provenance=provenance, amount_bps=amount, source_hash=H)


def outcome(**changes: CostComponent) -> ThesisOutcome:
    costs = {
        name: component(CostProvenance.OBSERVED)
        for name in (
            "fee",
            "spread",
            "slippage",
            "impact_size_feasibility",
            "funding",
            "implementation_shortfall",
        )
    }
    costs.update(changes)
    return ThesisOutcome(
        thesis_id="thesis",
        market_id=H,
        provider_state_source_hash=H,
        order_intent_hash=H,
        decision=ParticipationDecision.TAKE,
        attempt_count=1,
        **costs,
    )


def test_cost_projection_preserves_provenance_and_exact_states() -> None:
    values = project_cost_evidence(
        outcome(
            fee=component(CostProvenance.MODELLED),
            spread=component(CostProvenance.PROVEN_ZERO),
            funding=component(CostProvenance.NOT_APPLICABLE),
        )
    )
    assert values[0].provenance is CostProvenance.MODELLED
    assert values[0].claim_state is CostClaimState.PROVEN
    assert values[1].claim_state is CostClaimState.PROVEN_ZERO
    assert values[4].claim_state is CostClaimState.NOT_APPLICABLE


@pytest.mark.parametrize(
    "name",
    ["fee", "spread", "slippage", "impact_size_feasibility", "funding", "implementation_shortfall"],
)
def test_each_missing_cost_fails_closed(name: str) -> None:
    with pytest.raises(ValueError, match="MISSING"):
        project_cost_evidence(outcome(**{name: component(CostProvenance.MISSING)}))


def test_artifact_hash_tamper_fails_before_claim_acceptance() -> None:
    with pytest.raises(ValidationError):
        RealT2Artifact.model_validate({"final_t2_artifact_hash": H})


@pytest.mark.parametrize(
    ("provenance", "state", "amount"),
    [
        (CostProvenance.MISSING, CostClaimState.PROVEN, "1"),
        (CostProvenance.OBSERVED, CostClaimState.NOT_APPLICABLE, "1"),
        (CostProvenance.PROVEN_ZERO, CostClaimState.PROVEN_ZERO, "1"),
        (CostProvenance.NOT_APPLICABLE, CostClaimState.NOT_APPLICABLE, "not-a-number"),
    ],
)
def test_serialized_cost_evidence_fails_closed(
    provenance: CostProvenance, state: CostClaimState, amount: str
) -> None:
    with pytest.raises(ValidationError):
        CostEvidence.model_validate(
            {
                "name": "fee",
                "claim_state": state,
                "provenance": provenance,
                "amount_bps": amount,
                "source_hash": H,
            }
        )


def test_caller_authored_restart_echo_is_not_a_composition_capability() -> None:
    identities = RestartIdentitySet.create(
        structural_decision_hash=H,
        causal_lineage_hash=H,
        evaluation_inputs_hash=H,
        order_intent_hash=H,
        provider_state_projection_hash=H,
        outcome_report_hash=H,
    )
    forged = ReplayEquivalence(
        source_bundle_hash=H,
        original=identities,
        rebuilt=identities,
        child_pid=1 if 1 != __import__("os").getpid() else 2,
    )
    # Construction is only a wire-shape check; composition additionally requires
    # the process-local capability minted after the worker subprocess completes.
    from trader_assist_v0.nautilus_g4 import t2_shadow

    with pytest.raises(ValueError, match="not minted"):
        t2_shadow._require_minted_restart(forged)


def test_cli_is_truthfully_nondecisive_without_real_bundle() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/nautilus_vnext_g4_t2_shadow.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout.splitlines() == [
        "R3_RUNTIME_T2_STATUS=NONDECISIVE_REAL_INPUT_ABSENT",
        "REAL_T2_CREDIT=NO",
    ]


def test_worker_rejects_self_asserted_identity_set() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/nautilus_vnext_g4_t2_shadow.py", "--rebuild-identities"],
        input='{"source_bundle_hash":"' + H + '","source":{"identity_set":{}}}',
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "copied original identity sets are forbidden" in result.stderr
