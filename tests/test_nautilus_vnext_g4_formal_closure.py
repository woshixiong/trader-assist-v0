from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request

import pytest

from scripts import nautilus_vnext_g4_qualification as qualification
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex

HEAD = "1" * 40
TREE = "2" * 40
REVIEW_URL = (
    "https://github.com/woshixiong/trader-assist-v0/"
    "issues/163#issuecomment-5759999998"
)
REATTESTATION_COMMENT_ID = 5759999999
E4_CI_RUN_ID = 35599999999


class _Response:
    def __init__(self, payload: object, url: str) -> None:
        self._payload = json.dumps(payload).encode()
        self._url = url

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._payload


def _install_json_responses(
    monkeypatch: pytest.MonkeyPatch,
    responses: dict[str, object],
) -> None:
    def open_response(request: Request, *, timeout: float) -> _Response:
        assert timeout == 10.0
        assert request.full_url in responses
        return _Response(responses[request.full_url], request.full_url)

    monkeypatch.setattr(qualification, "urlopen", open_response)


def _run_payload(
    run_id: int,
    head: str,
    *,
    event: str,
    **changes: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": run_id,
        "run_attempt": qualification.TASK5B_RUN_ATTEMPT,
        "repository": {
            "id": 1290262291,
            "full_name": qualification.CANONICAL_REPOSITORY,
        },
        "name": qualification.CANONICAL_G4_WORKFLOW_NAME,
        "path": qualification.CANONICAL_G4_WORKFLOW_PATH,
        "event": event,
        "head_sha": head,
        "status": "completed",
        "conclusion": "success",
    }
    payload.update(changes)
    return payload


def _artifact_metadata(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": qualification.TASK5B_ARTIFACT_ID,
        "name": qualification.TASK5B_ARTIFACT_NAME,
        "digest": qualification.TASK5B_ARTIFACT_DIGEST,
        "expired": False,
        "workflow_run": {
            "id": qualification.TASK5B_RUN_ID,
            "head_sha": qualification.TASK5B_EXACT_HEAD,
            "repository_id": 1290262291,
            "head_repository_id": 1290262291,
        },
    }
    payload.update(changes)
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _build_artifact(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, object]]:
    source_payloads = {
        "causal-admission-columns.jsonl": b"{}\n",
        "pit-universe-snapshot.json": b'{"snapshot":true}\n',
        "process-segments.jsonl": b'{"segment":1}\n',
        "runtime-checkpoint.json": b'{"checkpoint":1}\n',
    }
    run_manifest = {
        "git_sha": qualification.TASK5B_EXACT_HEAD,
        "git_tree": qualification.TASK5B_EXACT_TREE,
        "manifest_hash": "a" * 64,
        "private_api": False,
        "real_exec_client_registered": False,
        "exchange_write": False,
    }
    _write_json(root / "run-manifest.json", run_manifest)
    for name, payload in source_payloads.items():
        (root / name).write_bytes(payload)
    source_hashes = {
        name: qualification._sha256_file(root / name)
        for name in (*source_payloads, "run-manifest.json")
    }
    markets = [
        {
            "event_count": 1,
            "instrument_id": f"M{ordinal}-USD-PERP.HYPERLIQUID",
            "market_id": f"{ordinal:064x}",
            "source_e4_manifest_hash": "a" * 64,
            "source_event_hashes": [f"{ordinal + 100:064x}"],
            "source_kind": "ACCEPTED_E4_CAUSAL",
        }
        for ordinal in range(1, qualification.REPRESENTATIVE_MARKET_FLOOR + 1)
    ]
    market_set_hash = sha256_hex(
        canonical_json_bytes([record["market_id"] for record in markets])
    )
    candidate: dict[str, object] = {
        "candidate_only": True,
        "canonical_acceptance_required": True,
        "evidence_tier": "E4_PUBLIC_PROVIDER_REPRESENTATIVE_SCALE_CANDIDATE",
        "manual_substitution": False,
        "markets": markets,
        "public_data_only": True,
        "repository": qualification.CANONICAL_REPOSITORY,
        "representative_market_count": qualification.REPRESENTATIVE_MARKET_FLOOR,
        "representative_market_set_hash": market_set_hash,
        "schema_version": qualification.REPRESENTATIVE_ARTIFACT_SCHEMA,
        "source_artifact_hashes": source_hashes,
        "source_e4_exact_head": qualification.TASK5B_EXACT_HEAD,
        "source_e4_exact_tree": qualification.TASK5B_EXACT_TREE,
        "source_e4_manifest_hash": "a" * 64,
        "source_e4_snapshot_hash": "b" * 64,
        "synthetic": False,
        "unique_retained_event_identity_count": len(markets),
        "zero_credentials": True,
        "zero_exchange_write": True,
        "zero_execution_client": True,
        "zero_signing": True,
    }
    candidate["artifact_hash"] = sha256_hex(canonical_json_bytes(candidate))
    _write_json(root / "representative-scale-candidate.json", candidate)
    acquisition = {
        "schema_version": "G4_REPRESENTATIVE_ACQUISITION_RESULT_V1",
        "RESULT": "COMPLETE_REPRESENTATIVE_CANDIDATE_BUILT",
        "G4E8": "NOT_PROVEN",
        "github_run_id": str(qualification.TASK5B_RUN_ID),
        "github_run_attempt": qualification.TASK5B_RUN_ATTEMPT,
        "exact_head": qualification.TASK5B_EXACT_HEAD,
        "exact_tree": qualification.TASK5B_EXACT_TREE,
        "target_count": qualification.REPRESENTATIVE_MARKET_FLOOR,
        "representative_candidate_hash": candidate["artifact_hash"],
        "run_manifest_hash": "a" * 64,
        "automatic_retry": False,
        "manual_market_input": False,
        "post_hoc_market_substitution": False,
        "public_data_only": True,
        "zero_credentials": True,
        "zero_execution_client": True,
        "zero_signing": True,
        "zero_exchange_write": True,
    }
    _write_json(root / "acquisition-result.json", acquisition)
    monkeypatch.setattr(
        qualification,
        "TASK5B_REPRESENTATIVE_ARTIFACT_HASH",
        candidate["artifact_hash"],
    )
    monkeypatch.setattr(
        qualification,
        "TASK5B_REPRESENTATIVE_MARKET_SET_HASH",
        market_set_hash,
    )
    monkeypatch.setattr(qualification, "TASK5B_SOURCE_E4_MANIFEST_HASH", "a" * 64)
    return root, candidate


def _task5b_api_responses(
    *,
    run: dict[str, object] | None = None,
    artifact: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        (
            "https://api.github.com/repos/woshixiong/trader-assist-v0/"
            f"actions/runs/{qualification.TASK5B_RUN_ID}"
        ): run
        or _run_payload(
            qualification.TASK5B_RUN_ID,
            qualification.TASK5B_EXACT_HEAD,
            event="workflow_dispatch",
        ),
        (
            "https://api.github.com/repos/woshixiong/trader-assist-v0/"
            f"actions/artifacts/{qualification.TASK5B_ARTIFACT_ID}"
        ): artifact or _artifact_metadata(),
    }


def _reattestation_receipt(**changes: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "acceptance_claim": "RE_ATTESTED",
        "canonical_g4e8_acceptance_comment_id": (
            qualification.TASK5B_CANONICAL_G4E8_ACCEPTANCE_COMMENT_ID
        ),
        "canonical_g4e8_acceptance_receipt_hash": (
            qualification.TASK5B_CANONICAL_G4E8_ACCEPTANCE_RECEIPT_HASH
        ),
        "exact_implementation_head": HEAD,
        "exact_implementation_tree": TREE,
        "exact_reviewed_head": HEAD,
        "fresh_independent_review_locator": REVIEW_URL,
        "fresh_independent_review_result_key": "task5c-review-pass",
        "fresh_independent_review_verdict": "PASS",
        "representative_artifact_hash": (
            qualification.TASK5B_REPRESENTATIVE_ARTIFACT_HASH
        ),
        "representative_market_set_hash": (
            qualification.TASK5B_REPRESENTATIVE_MARKET_SET_HASH
        ),
        "representative_source_artifact_id": qualification.TASK5B_ARTIFACT_ID,
        "representative_source_run_id": qualification.TASK5B_RUN_ID,
        "required_ci_run_ids_and_conclusions": [f"{E4_CI_RUN_ID}:success"],
        "source_e4_manifest_hash": qualification.TASK5B_SOURCE_E4_MANIFEST_HASH,
        "task_id": "PILOT_TASK5C_FORMAL_G4_END_TO_END_CLOSURE_PHASE_A",
    }
    receipt.update(changes)
    receipt["reattestation_hash"] = sha256_hex(canonical_json_bytes(receipt))
    return receipt


def _reattestation_envelope(
    receipt: dict[str, object],
    **changes: object,
) -> bytes:
    payload = {
        "schema_version": qualification.CANONICAL_G4E8_REATTESTATION_SCHEMA,
        "repository": qualification.CANONICAL_REPOSITORY,
        "acceptance": receipt,
    }
    body = (
        f"{qualification.CANONICAL_G4E8_REATTESTATION_HEADING}\n\n"
        f"```json\n{json.dumps(payload, sort_keys=True)}\n```\n"
    )
    envelope: dict[str, object] = {
        "id": REATTESTATION_COMMENT_ID,
        "html_url": (
            "https://github.com/woshixiong/trader-assist-v0/"
            f"issues/163#issuecomment-{REATTESTATION_COMMENT_ID}"
        ),
        "author_association": "OWNER",
        "user": {"login": "woshixiong"},
        "body": body,
    }
    envelope.update(changes)
    return json.dumps(envelope).encode()


@pytest.mark.parametrize(
    ("run_id", "changes", "expected"),
    (
        (None, {}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"repository": {"full_name": "wrong/repo"}}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"path": ".github/workflows/wrong.yml"}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"head_sha": "9" * 40}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"status": "in_progress", "conclusion": None}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"conclusion": "cancelled"}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {"conclusion": "failure"}, "NOT_PROVEN"),
        (E4_CI_RUN_ID, {}, "PASS"),
    ),
)
def test_g4e6_requires_exact_authoritative_success(
    monkeypatch: pytest.MonkeyPatch,
    run_id: int | None,
    changes: dict[str, object],
    expected: str,
) -> None:
    if run_id is not None:
        run = _run_payload(E4_CI_RUN_ID, HEAD, event="pull_request", **changes)
        _install_json_responses(
            monkeypatch,
            {
                (
                    "https://api.github.com/repos/woshixiong/"
                    f"trader-assist-v0/actions/runs/{E4_CI_RUN_ID}"
                ): run
            },
        )
    state = qualification._authoritative_e4_ci_state(
        run_id,
        expected_head=HEAD,
        github_token="workflow-token",
    )
    assert state["status"] == expected


def test_local_g4e6_pass_value_cannot_mint_credit() -> None:
    state = qualification._authoritative_e4_ci_state(
        {"status": "PASS"},
        expected_head=HEAD,
        github_token="workflow-token",
    )
    assert state["status"] == "NOT_PROVEN"


def test_task5b_artifact_requires_provider_and_content_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _candidate = _build_artifact(tmp_path, monkeypatch)
    _install_json_responses(monkeypatch, _task5b_api_responses())
    state = qualification._task5b_artifact_state(
        root,
        github_token="workflow-token",
    )
    assert state["status"] == "PASS"
    assert state["artifact_id"] == qualification.TASK5B_ARTIFACT_ID


@pytest.mark.parametrize(
    "mutate",
    (
        lambda run, artifact: run.update(id=1),
        lambda run, artifact: artifact.update(id=1),
        lambda run, artifact: artifact.update(name="wrong"),
        lambda run, artifact: artifact.update(digest="sha256:" + "0" * 64),
        lambda run, artifact: artifact.update(expired=True),
        lambda run, artifact: run.update(head_sha="9" * 40),
    ),
)
def test_task5b_wrong_provider_provenance_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutate: Callable[[dict[str, object], dict[str, object]], None],
) -> None:
    root, _candidate = _build_artifact(tmp_path, monkeypatch)
    run = _run_payload(
        qualification.TASK5B_RUN_ID,
        qualification.TASK5B_EXACT_HEAD,
        event="workflow_dispatch",
    )
    artifact = _artifact_metadata()
    mutate(run, artifact)
    _install_json_responses(
        monkeypatch,
        _task5b_api_responses(run=run, artifact=artifact),
    )
    state = qualification._task5b_artifact_state(
        root,
        github_token="workflow-token",
    )
    assert state["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "path",
    (
        "representative-scale-candidate.json",
        "run-manifest.json",
        "causal-admission-columns.jsonl",
    ),
)
def test_task5b_changed_or_missing_content_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    root, _candidate = _build_artifact(tmp_path, monkeypatch)
    (root / path).write_text("changed\n", encoding="utf-8")
    _install_json_responses(monkeypatch, _task5b_api_responses())
    state = qualification._task5b_artifact_state(
        root,
        github_token="workflow-token",
    )
    assert state["status"] == "FAIL_CLOSED"


@pytest.mark.parametrize(
    "changes",
    (
        {"source_e4_exact_head": "9" * 40},
        {"source_e4_exact_tree": "9" * 40},
        {"source_e4_manifest_hash": "9" * 64},
        {"representative_market_set_hash": "9" * 64},
        {"synthetic": True},
        {"manual_substitution": True},
    ),
)
def test_task5b_changed_candidate_identity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
) -> None:
    root, candidate = _build_artifact(tmp_path, monkeypatch)
    candidate.update(changes)
    candidate.pop("artifact_hash")
    candidate["artifact_hash"] = sha256_hex(canonical_json_bytes(candidate))
    _write_json(root / "representative-scale-candidate.json", candidate)
    _install_json_responses(monkeypatch, _task5b_api_responses())
    state = qualification._task5b_artifact_state(
        root,
        github_token="workflow-token",
    )
    assert state["status"] == "FAIL_CLOSED"


def test_same_head_g4e8_reattestation_promotes_only_exact_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = _reattestation_receipt()
    readback = qualification._parse_canonical_g4e8_reattestation(
        _reattestation_envelope(receipt),
        expected_comment_id=REATTESTATION_COMMENT_ID,
    )
    monkeypatch.setattr(
        qualification,
        "_fetch_canonical_g4e8_reattestation",
        lambda _comment_id: readback,
    )
    monkeypatch.setattr(
        qualification,
        "_representative_scale_probe",
        lambda *_args, **_kwargs: {"status": "PASS"},
    )
    artifact_state = {
        "status": "PASS",
        "candidate_path": "candidate.json",
        "representative_market_count": 20,
    }
    state = qualification._formal_g4e8_state(
        artifact_state,
        REATTESTATION_COMMENT_ID,
        expected_head=HEAD,
        expected_tree=TREE,
        authoritative_e4_ci_run_id=E4_CI_RUN_ID,
    )
    assert state["status"] == "PASS"


@pytest.mark.parametrize(
    "payload",
    (
        _reattestation_envelope(
            _reattestation_receipt(),
            author_association="COLLABORATOR",
        ),
        _reattestation_envelope(
            _reattestation_receipt(),
            user={"login": "not-the-repository-owner"},
        ),
        _reattestation_envelope(
            _reattestation_receipt(),
            html_url="https://example.invalid/comment",
        ),
        _reattestation_envelope(_reattestation_receipt()).replace(
            qualification.CANONICAL_G4E8_REATTESTATION_SCHEMA.encode(),
            b"LOCAL_G4E8_RECEIPT_V1",
        ),
        _reattestation_envelope(_reattestation_receipt()).replace(
            qualification.CANONICAL_REPOSITORY.encode(),
            b"wrong-owner/wrong-repository",
        ),
    ),
)
def test_noncanonical_g4e8_reattestation_is_rejected(payload: bytes) -> None:
    with pytest.raises(ValueError):
        qualification._parse_canonical_g4e8_reattestation(
            payload,
            expected_comment_id=REATTESTATION_COMMENT_ID,
        )


@pytest.mark.parametrize(
    "changes",
    (
        {"exact_reviewed_head": "9" * 40},
        {"representative_artifact_hash": "9" * 64},
        {"representative_source_run_id": 1},
        {"required_ci_run_ids_and_conclusions": ["1:success"]},
    ),
)
def test_changed_g4e8_reattestation_binding_is_not_proven(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
) -> None:
    readback = qualification._parse_canonical_g4e8_reattestation(
        _reattestation_envelope(_reattestation_receipt(**changes)),
        expected_comment_id=REATTESTATION_COMMENT_ID,
    )
    monkeypatch.setattr(
        qualification,
        "_fetch_canonical_g4e8_reattestation",
        lambda _comment_id: readback,
    )
    monkeypatch.setattr(
        qualification,
        "_representative_scale_probe",
        lambda *_args, **_kwargs: {"status": "PASS"},
    )
    state = qualification._formal_g4e8_state(
        {
            "status": "PASS",
            "candidate_path": "candidate.json",
            "representative_market_count": 20,
        },
        REATTESTATION_COMMENT_ID,
        expected_head=HEAD,
        expected_tree=TREE,
        authoritative_e4_ci_run_id=E4_CI_RUN_ID,
    )
    assert state["status"] == "NOT_PROVEN"


def test_old_g4e8_receipt_or_local_object_cannot_mint_same_head_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_body = {
        "id": qualification.TASK5B_CANONICAL_G4E8_ACCEPTANCE_COMMENT_ID,
        "html_url": (
            "https://github.com/woshixiong/trader-assist-v0/issues/"
            f"163#issuecomment-{qualification.TASK5B_CANONICAL_G4E8_ACCEPTANCE_COMMENT_ID}"
        ),
        "author_association": "OWNER",
        "user": {"login": "woshixiong"},
        "body": "## G4 REPRESENTATIVE-SCALE CANONICAL ACCEPTANCE READBACK V1",
    }
    with pytest.raises(ValueError):
        qualification._parse_canonical_g4e8_reattestation(
            json.dumps(old_body).encode(),
            expected_comment_id=(
                qualification.TASK5B_CANONICAL_G4E8_ACCEPTANCE_COMMENT_ID
            ),
        )
    monkeypatch.setattr(
        qualification,
        "_representative_scale_probe",
        lambda *_args, **_kwargs: {"status": "PASS"},
    )
    state = qualification._formal_g4e8_state(
        {"status": "PASS", "candidate_path": "candidate.json"},
        {"status": "PASS"},  # type: ignore[arg-type]
        expected_head=HEAD,
        expected_tree=TREE,
        authoritative_e4_ci_run_id=E4_CI_RUN_ID,
    )
    assert state["status"] == "NOT_PROVEN"


def test_formal_g4_requires_exact_nine_literal_pass_values() -> None:
    ladder = {key: "PASS" for key in qualification.FORMAL_G4_GATE_KEYS}
    assert qualification._exact_formal_g4_acceptance(ladder) is True
    assert qualification._exact_formal_g4_acceptance(
        {**ladder, "G4E9": "PASS"}
    ) is False
    for value in ("NOT_PROVEN", "PASS_REQUIRES_EXACT_HEAD_E4_CI", "pass", ""):
        assert qualification._exact_formal_g4_acceptance(
            {**ladder, "G4E6": value}
        ) is False
