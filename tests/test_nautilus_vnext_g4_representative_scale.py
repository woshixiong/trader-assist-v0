from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest

from scripts import nautilus_vnext_g4_qualification as qualification
from scripts.nautilus_vnext_g4_representative_scale import (
    build_representative_scale_candidate,
)
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.nautilus_e4.contracts import (
    AdmittedEvent,
    DataKind,
    EvidenceState,
    MarketExpression,
    PitUniverseSnapshot,
    RunManifest,
    SourceEvent,
)

COMMENT_ID = 5751000000
HEAD = "1" * 40
TREE = "2" * 40
SOURCE_HEAD = "3" * 40
SOURCE_TREE = "4" * 40
REVIEW_URL = (
    "https://github.com/woshixiong/trader-assist-v0/"
    "issues/163#issuecomment-5751000001"
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


def _source_fixture(
    market_count: int = 20,
) -> tuple[RunManifest, PitUniverseSnapshot, tuple[AdmittedEvent, ...]]:
    expressions: list[MarketExpression] = []
    admissions: list[AdmittedEvent] = []
    for index in range(market_count):
        coin = f"COIN{index:02d}"
        market_id = sha256_hex(f"HYPERLIQUID|MAIN|{coin}".encode())
        instrument_id = f"{coin}-USD-PERP.HYPERLIQUID"
        expression = MarketExpression(
            market_id=market_id,
            dex="MAIN",
            provider_coin=coin,
            instrument_id=instrument_id,
            expression_id=f"expr-{coin.lower()}",
            instrument_metadata_version="PUBLIC_PROVIDER_PROBE_V1",
            instrument_metadata_hash=sha256_hex(f"metadata-{coin}".encode()),
        )
        expressions.append(expression)
        source = SourceEvent.create(
            market_id=market_id,
            expression_id=expression.expression_id,
            provider_id="NAUTILUS_HYPERLIQUID",
            instrument_id=instrument_id,
            data_kind=DataKind.BAR,
            source_event_id=f"bar-{index}",
            native_trade_id=None,
            provider_aggressor_side=None,
            event_context="FINALIZED_1M",
            ts_event=1_000 + index * 10,
            ts_init=1_001 + index * 10,
            true_network_receive_ts=None,
            payload={"finalized": True, "close": str(100 + index)},
        )
        admissions.append(
            AdmittedEvent.create(
                schema_version="E4_CAPTURE_V1",
                process_epoch="process-representative",
                continuity_epoch="continuity-representative",
                admission_epoch="admission-representative",
                admission_ordinal=index + 1,
                admission_ts=1_002 + index * 10,
                source_identity=source.replay_identity,
                out_of_order=False,
                continuity_state=EvidenceState.COMPLETE,
                source=source,
            )
        )
    snapshot = PitUniverseSnapshot.create(
        observed_at_ns=999,
        expressions=tuple(expressions),
    )
    manifest = RunManifest.create(
        run_id="representative-public-capture",
        git_sha=SOURCE_HEAD,
        git_tree=SOURCE_TREE,
        snapshot=snapshot,
        process_epoch="process-representative",
        continuity_epoch="continuity-representative",
        admission_epoch="admission-representative",
        capture_configuration={
            "expressions": [item.model_dump(mode="json") for item in expressions],
            "probe": "BOUNDED_PUBLIC_PROVIDER_REPRESENTATIVE_SCALE_V1",
        },
        subscription_policy={
            "discovery": [item.market_id for item in expressions],
            "watch": [item.market_id for item in expressions],
            "actionable": [],
        },
        trial_ledger_id="representative-public-capture-v1",
    )
    return manifest, snapshot, tuple(admissions)


def _artifact(market_count: int = 20) -> dict[str, object]:
    manifest, snapshot, admissions = _source_fixture(market_count)
    return build_representative_scale_candidate(
        manifest=manifest,
        snapshot=snapshot,
        admissions=admissions,
        source_artifact_hashes={
            "causal-admission-columns.jsonl": "a" * 64,
            "pit-universe-snapshot.json": "b" * 64,
            "run-manifest.json": "c" * 64,
        },
    )


def _replace_admission(
    admission: AdmittedEvent,
    **changes: object,
) -> AdmittedEvent:
    values = admission.model_dump(mode="python", exclude={"admission_hash"})
    values.update(changes)
    return AdmittedEvent.create(**values)


def _write_artifact(tmp_path: Path, artifact: dict[str, object]) -> Path:
    path = tmp_path / "representative-scale-candidate.json"
    path.write_bytes(canonical_json_bytes(artifact) + b"\n")
    return path


def _receipt(artifact: dict[str, object], **changes: object) -> dict[str, object]:
    identity: dict[str, object] = {
        "acceptance_claim": "ACCEPTED",
        "task_id": "PILOT_TASK5B_REAL_20_MARKET_CAPTURE_ACCEPTANCE_AND_FORMAL_G4_CLOSURE",
        "representative_artifact_hash": artifact["artifact_hash"],
        "source_e4_manifest_hash": artifact["source_e4_manifest_hash"],
        "source_e4_exact_head": artifact["source_e4_exact_head"],
        "source_e4_exact_tree": artifact["source_e4_exact_tree"],
        "representative_market_set_hash": artifact[
            "representative_market_set_hash"
        ],
        "representative_market_count": artifact["representative_market_count"],
        "exact_implementation_head": HEAD,
        "exact_implementation_tree": TREE,
        "required_ci_run_ids_and_conclusions": ["run-1:success", "run-2:success"],
        "fresh_independent_review_result_key": "task5b-review-pass",
        "fresh_independent_review_locator": REVIEW_URL,
        "fresh_independent_review_verdict": "PASS",
        "exact_reviewed_head": HEAD,
        "canonical_acceptance_receipt_key": "task5b-representative-acceptance",
    }
    identity.update(changes)
    return {
        **identity,
        "receipt_hash": sha256_hex(canonical_json_bytes(identity)),
    }


def _envelope(
    artifact: dict[str, object],
    *,
    receipt_changes: dict[str, object] | None = None,
    **envelope_changes: object,
) -> bytes:
    payload = {
        "schema_version": qualification.CANONICAL_REPRESENTATIVE_READBACK_SCHEMA,
        "repository": qualification.CANONICAL_REPOSITORY,
        "acceptance": _receipt(artifact, **(receipt_changes or {})),
    }
    envelope: dict[str, Any] = {
        "id": COMMENT_ID,
        "html_url": (
            "https://github.com/woshixiong/trader-assist-v0/"
            f"issues/163#issuecomment-{COMMENT_ID}"
        ),
        "author_association": "OWNER",
        "user": {"login": "woshixiong"},
        "body": (
            f"{qualification.CANONICAL_REPRESENTATIVE_READBACK_HEADING}\n\n"
            f"```json\n{json.dumps(payload, sort_keys=True)}\n```\n"
        ),
    }
    envelope.update(envelope_changes)
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


def test_candidate_requires_twenty_actual_unique_source_bound_markets() -> None:
    artifact = _artifact()
    assert artifact["candidate_only"] is True
    assert artifact["canonical_acceptance_required"] is True
    assert artifact["representative_market_count"] == 20
    assert artifact["unique_retained_event_identity_count"] == 20
    assert len({item["market_id"] for item in artifact["markets"]}) == 20  # type: ignore[index]
    assert len(
        {
            event_hash
            for item in artifact["markets"]  # type: ignore[union-attr]
            for event_hash in item["source_event_hashes"]
        }
    ) == 20
    with pytest.raises(ValueError, match="at least 20"):
        _artifact(19)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("process_epoch", "process epoch"),
        ("continuity_epoch", "continuity epoch"),
        ("admission_epoch", "admission epoch"),
    ),
)
def test_candidate_rejects_admissions_from_another_e4_run(
    field: str,
    message: str,
) -> None:
    manifest, snapshot, admissions = _source_fixture()
    cross_run = _replace_admission(admissions[0], **{field: f"other-{field}"})
    with pytest.raises(ValueError, match=message):
        build_representative_scale_candidate(
            manifest=manifest,
            snapshot=snapshot,
            admissions=(cross_run, *admissions[1:]),
            source_artifact_hashes={"causal-admission-columns.jsonl": "a" * 64},
        )


def test_candidate_rejects_source_expression_outside_bound_snapshot() -> None:
    manifest, snapshot, admissions = _source_fixture()
    original = admissions[0]
    source_values = original.source.model_dump(
        mode="python",
        exclude={"payload_hash"},
    )
    source_values["expression_id"] = "expr-from-another-run"
    mismatched_source = SourceEvent.create(**source_values)
    mismatch = _replace_admission(
        original,
        source=mismatched_source,
        source_identity=mismatched_source.replay_identity,
    )
    with pytest.raises(ValueError, match="expression"):
        build_representative_scale_candidate(
            manifest=manifest,
            snapshot=snapshot,
            admissions=(mismatch, *admissions[1:]),
            source_artifact_hashes={"causal-admission-columns.jsonl": "a" * 64},
        )


def test_valid_self_hash_without_canonical_readback_cannot_promote(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    result = qualification._representative_scale_probe(
        _write_artifact(tmp_path, artifact),
        expected_head=HEAD,
        expected_tree=TREE,
    )
    assert result["status"] == "NOT_PROVEN"
    assert result["actual_representative_market_count"] == 20
    assert result["reason"] == (
        "NO_CANONICAL_REPRESENTATIVE_ACCEPTANCE_READBACK_SUPPLIED"
    )


def test_owner_authored_exact_readback_promotes_g4e8(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact()
    _install_response(monkeypatch, _envelope(artifact))
    result = qualification._representative_scale_probe(
        _write_artifact(tmp_path, artifact),
        COMMENT_ID,
        expected_head=HEAD,
        expected_tree=TREE,
    )
    assert result["status"] == "PASS"
    assert result["canonical_acceptance_comment_id"] == COMMENT_ID
    assert result["representative_artifact_hash"] == artifact["artifact_hash"]
    assert result["source_e4_manifest_hash"] == artifact["source_e4_manifest_hash"]
    assert result["accepted_required_ci"] == ["run-1:success", "run-2:success"]
    assert result["accepted_review_locator"] == REVIEW_URL


@pytest.mark.parametrize(
    ("receipt_changes", "envelope_changes", "expected_reason"),
    (
        ({"representative_artifact_hash": "d" * 64}, {}, "BINDING"),
        ({"source_e4_manifest_hash": "d" * 64}, {}, "BINDING"),
        ({"source_e4_exact_head": "d" * 40}, {}, "BINDING"),
        ({"source_e4_exact_tree": "d" * 40}, {}, "BINDING"),
        ({"representative_market_set_hash": "d" * 64}, {}, "BINDING"),
        ({"exact_implementation_head": "6" * 40, "exact_reviewed_head": "6" * 40}, {}, "BINDING"),
        ({"exact_implementation_tree": "7" * 40}, {}, "BINDING"),
        ({"required_ci_run_ids_and_conclusions": ["run-1:failure"]}, {}, "ValueError"),
        ({"fresh_independent_review_verdict": "REJECT"}, {}, "ValueError"),
        (
            {"fresh_independent_review_locator": "https://example.invalid/review"},
            {},
            "ValueError",
        ),
        ({"exact_reviewed_head": "8" * 40}, {}, "ValueError"),
        ({}, {"author_association": "COLLABORATOR"}, "ValueError"),
        ({}, {"user": {"login": "someone-else"}}, "ValueError"),
        ({}, {"id": COMMENT_ID + 1}, "ValueError"),
        ({}, {"html_url": "https://example.invalid/comment"}, "ValueError"),
    ),
)
def test_wrong_canonical_binding_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt_changes: dict[str, object],
    envelope_changes: dict[str, object],
    expected_reason: str,
) -> None:
    artifact = _artifact()
    _install_response(
        monkeypatch,
        _envelope(
            artifact,
            receipt_changes=receipt_changes,
            **envelope_changes,
        ),
    )
    result = qualification._representative_scale_probe(
        _write_artifact(tmp_path, artifact),
        COMMENT_ID,
        expected_head=HEAD,
        expected_tree=TREE,
    )
    assert result["status"] == "NOT_PROVEN"
    assert expected_reason in str(result["reason"])


def test_redirected_canonical_readback_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _artifact()
    _install_response(monkeypatch, _envelope(artifact), redirected=True)
    result = qualification._representative_scale_probe(
        _write_artifact(tmp_path, artifact),
        COMMENT_ID,
        expected_head=HEAD,
        expected_tree=TREE,
    )
    assert result["status"] == "NOT_PROVEN"
    assert result["reason"] == "CANONICAL_REPRESENTATIVE_READBACK_REJECTED:ValueError"
