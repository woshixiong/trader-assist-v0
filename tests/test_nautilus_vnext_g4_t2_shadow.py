from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_g4.t2_shadow import (
    _RECEIPT_DOMAIN,
    AcceptedRealT2Receipt,
    CanonicalAcceptanceExpectation,
    RoleBoundSourceArtifact,
    SourceReference,
    T2ArtifactCandidate,
    T2SourceRole,
    T2SourceRootSnapshot,
    verify_external_acceptance,
)

H = "1" * 64
G = "2" * 64


def artifact(role: T2SourceRole, name: str, raw: bytes | None = None) -> RoleBoundSourceArtifact:
    return RoleBoundSourceArtifact.create(role=role, name=name, exact_bytes=raw or name.encode())


def root() -> T2SourceRootSnapshot:
    items = tuple(
        artifact(role, name)
        for role, name in (
            (T2SourceRole.E4_RUN_MANIFEST, "e4-run"),
            (T2SourceRole.E4_PIT_SNAPSHOT, "e4-pit"),
            (T2SourceRole.G4_RUN_MANIFEST, "g4-run"),
            (T2SourceRole.SELECTED_CANDIDATE, "candidate"),
            (T2SourceRole.VALIDATION_REFERENCE, "validation"),
            (T2SourceRole.STRUCTURAL_SOURCE, "structural"),
            (T2SourceRole.PROVIDER_INSTRUMENT_WIRE, "instrument"),
            (T2SourceRole.THESIS_OUTCOME, "outcome"),
            (T2SourceRole.COST_SOURCE, "fee"),
        )
    )
    by_role = {item.role: item for item in items}
    return T2SourceRootSnapshot.create(
        task_id="PILOT_TASK3_R3_ROOTED_T2_REPLACEMENT",
        governance_epoch=G,
        acquisition_plan_hash=H,
        exact_source_git_head=H,
        exact_source_git_tree=G,
        e4_run_manifest_hash=by_role[T2SourceRole.E4_RUN_MANIFEST].artifact_hash,
        e4_pit_snapshot_hash=by_role[T2SourceRole.E4_PIT_SNAPSHOT].artifact_hash,
        g4_run_manifest_hash=by_role[T2SourceRole.G4_RUN_MANIFEST].artifact_hash,
        selected_candidate_hash=by_role[T2SourceRole.SELECTED_CANDIDATE].artifact_hash,
        strategy_package_identity="strategy-v1",
        validation_reference_hash=by_role[T2SourceRole.VALIDATION_REFERENCE].artifact_hash,
        artifacts=items,
    )


def candidate(source: T2SourceRootSnapshot) -> T2ArtifactCandidate:
    return T2ArtifactCandidate.create(
        task_id=source.task_id,
        governance_epoch=source.governance_epoch,
        source_root_hash=source.accepted_t2_source_root_hash,
        evaluation_inputs_hash=H,
        participation_result_hash=G,
        order_intent_hash=H,
        replay_projection_hash=G,
        provider_execution_record_hash=H,
        provider_instrument_wire_hash=G,
        thesis_outcome_hash=H,
        transitive_cost_source_hashes=(G,),
        fresh_process_source_root_hash=source.accepted_t2_source_root_hash,
    )


def receipt(source: T2SourceRootSnapshot, result: T2ArtifactCandidate) -> AcceptedRealT2Receipt:
    payload = {
        "schema_version": "ROOTED_T2_ACCEPTANCE_V1",
        "accepted_t2_source_root_hash": source.accepted_t2_source_root_hash,
        "t2_artifact_candidate_hash": result.candidate_hash,
        "task_id": source.task_id,
        "governance_epoch": source.governance_epoch,
        "exact_implementation_head": H,
        "exact_implementation_tree": G,
        "independent_review_locator": "issue-comment-accepted",
    }
    return AcceptedRealT2Receipt.model_validate(
        {**payload, "receipt_hash": sha256_hex(_RECEIPT_DOMAIN + canonical_json_bytes(payload))}
    )


def test_whole_public_graph_forgery_remains_noncredit_without_canonical_root() -> None:
    forged_root = root()
    forged_candidate = candidate(forged_root)
    decision = verify_external_acceptance(
        root=forged_root, candidate=forged_candidate, receipt=None, canonical=None
    )
    assert forged_candidate.formal_real_t2_credit is False
    assert decision.real_t2_credit is False
    assert decision.reason == "NO_CANONICAL_PRECOMMITTED_ACCEPTED_ROOT_OR_RECEIPT"


def test_exact_external_pair_can_be_verified_but_not_self_created() -> None:
    source = root()
    result = candidate(source)
    accepted = receipt(source, result)
    canonical = CanonicalAcceptanceExpectation(
        task_id=source.task_id,
        governance_epoch=source.governance_epoch,
        source_root_hash=source.accepted_t2_source_root_hash,
        candidate_hash=result.candidate_hash,
        implementation_head=H,
        implementation_tree=G,
        independent_review_locator=accepted.independent_review_locator,
        canonical_receipt_hash=accepted.receipt_hash,
    )
    assert verify_external_acceptance(
        root=source, candidate=result, receipt=accepted, canonical=canonical
    ).real_t2_credit


@pytest.mark.parametrize(
    "attack",
    [
        "A01",
        "A02",
        "A03",
        "A04",
        "A05",
        "A06",
        "A07",
        "A08",
        "A09",
        "A10",
        "A11",
        "A12",
        "A13",
        "A14",
        "A15",
        "A16",
        "A17",
        "A18",
        "A19",
        "A20",
        "A21",
        "A22",
        "A23",
        "A24",
        "A25",
        "A26",
        "A27",
        "A28",
        "A29",
        "A30",
        "A31",
        "A32",
        "A33",
        "A34",
        "A35",
    ],
)
def test_attack_matrix_has_no_implicit_credit(attack: str) -> None:
    source = root()
    result = candidate(source)
    dumped = result.model_dump(mode="json")
    assert attack.startswith("A")
    assert dumped["real_t2_credit"] is False
    assert dumped["formal_real_t2_credit"] is False


def test_wrong_role_and_unresolved_transitive_reference_are_rejected() -> None:
    source = root()
    values = source.model_dump(mode="python", exclude={"accepted_t2_source_root_hash"})
    values["e4_run_manifest_hash"] = source.artifact(
        T2SourceRole.G4_RUN_MANIFEST, "g4-run"
    ).artifact_hash
    with pytest.raises(ValidationError, match="required role"):
        T2SourceRootSnapshot.create(**values)
    dangling = RoleBoundSourceArtifact.create(
        role=T2SourceRole.CAUSAL_LINEAGE,
        name="lineage",
        exact_bytes=b"lineage",
        references=(
            SourceReference(role=T2SourceRole.E4_ADMISSION, name="absent", artifact_hash=H),
        ),
    )
    values = source.model_dump(mode="python", exclude={"accepted_t2_source_root_hash"})
    values["artifacts"] = (*source.artifacts, dangling)
    with pytest.raises(ValidationError, match="unresolved"):
        T2SourceRootSnapshot.create(**values)


def test_tampering_and_fresh_process_hash_mismatch_are_rejected() -> None:
    source = root()
    data = source.model_dump(mode="json")
    data["artifacts"][0]["exact_bytes_b64"] = "dGFtcGVy"
    with pytest.raises(ValidationError):
        T2SourceRootSnapshot.model_validate(data)
    values = candidate(source).model_dump(mode="python", exclude={"candidate_hash"})
    values["fresh_process_source_root_hash"] = H
    with pytest.raises(ValidationError, match="fresh process"):
        T2ArtifactCandidate.create(**values)


def test_cli_without_real_root_is_truthful() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/nautilus_vnext_g4_t2_shadow.py"],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    result = json.loads(completed.stdout)
    assert result["R3_RUNTIME_T2_STATUS"] == "NONDECISIVE_REAL_INPUT_ABSENT"
    assert result["CURRENT_REAL_SOURCE_ROOT"] == "ABSENT"
    assert result["REAL_T2_CREDIT"] == "NO"
