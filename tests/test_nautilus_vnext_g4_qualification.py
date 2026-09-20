from __future__ import annotations

import json
from typing import Any
from urllib.request import Request

import pytest

from scripts import nautilus_vnext_g4_qualification as qualification
from trader_assist_v0.nautilus_g4.runner import formal_g4_acceptance
from trader_assist_v0.nautilus_g4.t2_shadow import (
    AcceptedRealT2Receipt,
    CanonicalAcceptanceExpectation,
)

COMMENT_ID = 5750000000
HEAD = "1" * 40
TREE = "2" * 40
SOURCE_ROOT = "3" * 64
CANDIDATE = "4" * 64
GOVERNANCE_EPOCH = "5" * 64
REVIEW_URL = (
    "https://github.com/woshixiong/trader-assist-v0/"
    "issues/163#issuecomment-5749999999"
)


class _Response:
    def __init__(self, payload: bytes, url: str) -> None:
        self._payload = payload
        self._url = url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._payload


def _receipt(
    *,
    reviewed_head: str = HEAD,
    ci: tuple[str, ...] = ("run-1:success", "run-2:success"),
) -> AcceptedRealT2Receipt:
    return AcceptedRealT2Receipt.create(
        acceptance_claim="ACCEPTED",
        task_id="PILOT_TASK3_R3_ROOTED_T2_V3_REPLACEMENT",
        governance_epoch=GOVERNANCE_EPOCH,
        accepted_t2_source_root_hash=SOURCE_ROOT,
        t2_artifact_candidate_hash=CANDIDATE,
        exact_implementation_head=HEAD,
        exact_implementation_tree=TREE,
        required_ci_run_ids_and_conclusions=ci,
        fresh_independent_review_result_key="rooted-t2-review-pass",
        fresh_independent_review_locator=REVIEW_URL,
        fresh_independent_review_verdict="PASS",
        exact_reviewed_head=reviewed_head,
        canonical_acceptance_receipt_key="rooted-t2-canonical-receipt",
    )


def _envelope(
    receipt: AcceptedRealT2Receipt,
    **changes: object,
) -> bytes:
    payload = {
        "schema_version": qualification.CANONICAL_T2_READBACK_SCHEMA,
        "repository": qualification.CANONICAL_REPOSITORY,
        "acceptance": receipt.model_dump(mode="json"),
    }
    body = (
        f"{qualification.CANONICAL_T2_READBACK_HEADING}\n\n"
        f"```json\n{json.dumps(payload, sort_keys=True)}\n```\n"
    )
    envelope: dict[str, Any] = {
        "id": COMMENT_ID,
        "html_url": (
            "https://github.com/woshixiong/trader-assist-v0/"
            f"issues/163#issuecomment-{COMMENT_ID}"
        ),
        "author_association": "OWNER",
        "user": {"login": "woshixiong"},
        "body": body,
    }
    envelope.update(changes)
    return json.dumps(envelope).encode()


def _install_response(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    *,
    redirected: bool = False,
) -> None:
    def open_response(request: Request, *, timeout: float) -> _Response:
        assert timeout == 10.0
        url = "https://example.invalid/redirect" if redirected else request.full_url
        return _Response(payload, url)

    monkeypatch.setattr(qualification, "urlopen", open_response)


def test_no_canonical_readback_keeps_all_causal_gates_not_proven() -> None:
    gates, state = qualification._canonical_t2_state(None)
    assert gates == {
        "G4E1": "NOT_PROVEN",
        "G4E2": "NOT_PROVEN",
        "G4E5": "NOT_PROVEN",
        "G4E7": "NOT_PROVEN",
    }
    assert state == {
        "accepted": False,
        "reason": "NO_CANONICAL_ACCEPTED_T2_READBACK_SUPPLIED",
    }


def test_owner_authored_canonical_readback_promotes_only_causal_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response(monkeypatch, _envelope(_receipt()))
    gates, state = qualification._canonical_t2_state(COMMENT_ID)
    assert gates == {"G4E1": "PASS", "G4E2": "PASS", "G4E5": "PASS", "G4E7": "PASS"}
    assert state["accepted"] is True
    assert state["source_root_hash"] == SOURCE_ROOT
    assert state["artifact_candidate_hash"] == CANDIDATE
    assert state["implementation_head"] == state["reviewed_head"] == HEAD
    assert state["implementation_tree"] == TREE
    assert state["required_ci"] == ["run-1:success", "run-2:success"]
    assert state["review_locator"] == REVIEW_URL

    ladder = {
        "G4E0": "PASS",
        **gates,
        "G4E3": "PASS",
        "G4E4": "PASS",
        "G4E6": "PASS",
        "G4E8": "NOT_PROVEN",
    }
    assert formal_g4_acceptance(ladder) is False


def test_local_matching_receipt_or_expectation_cannot_mint_credit() -> None:
    receipt = _receipt()
    expectation = CanonicalAcceptanceExpectation(
        task_id=receipt.task_id,
        governance_epoch=receipt.governance_epoch,
        source_root_hash=receipt.accepted_t2_source_root_hash,
        candidate_hash=receipt.t2_artifact_candidate_hash,
        implementation_head=receipt.exact_implementation_head,
        implementation_tree=receipt.exact_implementation_tree,
        required_ci_run_ids_and_conclusions=("run-1:success", "run-2:success"),
        independent_review_result_key=receipt.fresh_independent_review_result_key,
        independent_review_locator=receipt.fresh_independent_review_locator,
        exact_reviewed_head=receipt.exact_reviewed_head,
        canonical_receipt_key=receipt.canonical_acceptance_receipt_key,
        copied_receipt_evidence_hash=receipt.evidence_hash,
    )
    for local_object in (receipt, expectation, receipt.model_dump(mode="json")):
        gates, state = qualification._canonical_t2_state(local_object)
        assert set(gates.values()) == {"NOT_PROVEN"}
        assert state["accepted"] is False
        assert state["reason"] == "CANONICAL_T2_READBACK_REJECTED:ValueError"


@pytest.mark.parametrize(
    "payload",
    (
        _envelope(_receipt(), author_association="COLLABORATOR"),
        _envelope(_receipt(), user={"login": "not-the-repository-owner"}),
        _envelope(_receipt(reviewed_head="6" * 40)),
        _envelope(_receipt(ci=("run-1:failure",))),
        _envelope(_receipt(ci=("run-1:success", "run-1:success"))),
        _envelope(_receipt(), html_url="https://example.invalid/comment"),
        _envelope(_receipt()).replace(
            qualification.CANONICAL_REPOSITORY.encode(),
            b"wrong-owner/wrong-repository",
        ),
        _envelope(_receipt()).replace(
            qualification.CANONICAL_T2_READBACK_SCHEMA.encode(),
            b"ROOTED_T2_CALLER_SUPPLIED_RECEIPT_V1",
        ),
    ),
)
def test_noncanonical_or_cross_bound_readback_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    _install_response(monkeypatch, payload)
    gates, state = qualification._canonical_t2_state(COMMENT_ID)
    assert set(gates.values()) == {"NOT_PROVEN"}
    assert state["accepted"] is False
    assert state["reason"] == "CANONICAL_T2_READBACK_REJECTED:ValueError"


def test_redirected_github_readback_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_response(monkeypatch, _envelope(_receipt()), redirected=True)
    gates, state = qualification._canonical_t2_state(COMMENT_ID)
    assert set(gates.values()) == {"NOT_PROVEN"}
    assert state["accepted"] is False
