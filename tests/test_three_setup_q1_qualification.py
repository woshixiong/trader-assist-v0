"""Focused fault checks for the Q1 control harness and actual product store."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from scripts import three_setup_q1_qualification as q1
from trader_assist_v0.multi_asset_shadow.e4_markettruth import E4MemoryBarStore


def test_exact_identity_fails_closed_on_head_tree_and_dirty_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = {"HEAD": q1.BASE_SHA, "HEAD^{tree}": q1.BASE_TREE, "status": ""}

    def fake_git(_root: Path, *args: str) -> str:
        if args[0] == "status":
            return observed["status"]
        return observed[args[-1]]

    monkeypatch.setattr(q1, "_git", fake_git)
    q1.exact_identity(tmp_path, q1.BASE_SHA, q1.BASE_TREE)
    for field, bad in (("HEAD", "0" * 40), ("HEAD^{tree}", "1" * 40), ("status", " M src/a.py")):
        observed[field] = bad
        with pytest.raises(q1.QualificationGap):
            q1.exact_identity(tmp_path, q1.BASE_SHA, q1.BASE_TREE)
        observed[field] = (
            "" if field == "status" else q1.BASE_SHA if field == "HEAD" else q1.BASE_TREE
        )
    with pytest.raises(q1.QualificationGap):
        q1.exact_identity(tmp_path, "2" * 40, q1.BASE_TREE)


def test_import_outside_candidate_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = Path(__file__).parents[1]
    untrusted = ModuleType("trader_assist_v0.untrusted")
    untrusted.__file__ = "/private/tmp/outside-product.py"
    monkeypatch.setitem(
        sys.modules,
        "trader_assist_v0.untrusted",
        untrusted,
    )
    with pytest.raises(q1.QualificationGap):
        q1._assert_import_origins(candidate)


def test_classifier_never_promotes_missing_or_incomplete_claims() -> None:
    complete = dict.fromkeys(q1.MANDATORY, True)
    assert q1.classify(complete, None) == "PASS"
    assert set(q1.adversarial_matrix(complete)) == set(q1.ADVERSARIAL)
    assert all(q1.adversarial_matrix(complete).values())
    for cause in q1.CLASSES[1:]:
        assert q1.classify(complete, cause) == cause
    for claim in q1.MANDATORY:
        incomplete = complete | {claim: False}
        assert q1.classify(incomplete, None) != "PASS", claim
    assert q1.classify({}, None) != "PASS"


def test_product_closed_bar_store_is_the_live_memory_connection() -> None:
    product = E4MemoryBarStore()
    try:
        assert q1._integrity(product.connection)
        database = product.connection.execute("PRAGMA database_list").fetchone()
        assert database[2] == ""
        product.connection.execute(
            "INSERT INTO closed_bars VALUES (?,?,?,?,?,?,?,?,?)",
            ("m", "5m", 0, "h", "v", "r", "f", 0, b"{}"),
        )
        product.connection.commit()
        assert product.connection.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 1
    finally:
        product.close()
    reconstructed = E4MemoryBarStore()
    try:
        assert (
            reconstructed.connection.execute("SELECT COUNT(*) FROM closed_bars").fetchone()[0] == 0
        )
        assert q1._integrity(reconstructed.connection)
    finally:
        reconstructed.close()


def test_domain_integrity_and_identity_checks_use_actual_file(tmp_path: Path) -> None:
    path = tmp_path / "evidence.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE immutable_records (record_id TEXT, record_type TEXT, payload_json TEXT)"
        )
        db.execute(
            "CREATE TABLE notification_outbox "
            "(idempotency_key TEXT, state TEXT, attempt_count INTEGER)"
        )
        db.execute(
            "INSERT INTO immutable_records VALUES (?,?,?)",
            (
                "shadow-1",
                "shadow_order",
                json.dumps({"submission_status": "NOT_SUBMITTED", "venue_submitted": False}),
            ),
        )
        db.execute("INSERT INTO notification_outbox VALUES (?,?,?)", ("key-1", "DELIVERED", 1))
    state = q1._domain_state(path)
    assert state["integrity_ok"]
    assert state["all_not_submitted"]
    assert state["record_ids"] == ["shadow-1"]
    assert state["outbox"][0]["idempotency_key"] == "key-1"


def test_corrupt_domain_database_is_product_blocker(tmp_path: Path) -> None:
    path = tmp_path / "evidence.sqlite"
    path.write_bytes(b"not a SQLite database")
    with pytest.raises(q1.ProductBlocker):
        q1._domain_state(path)


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ({"venue_submitted": False, "not_submitted": True}, True),
        ({"venue_submitted": True, "not_submitted": False}, False),
        ({"venue_submitted": False, "not_submitted": False}, False),
    ],
)
def test_execution_chain_flags_must_remain_not_submitted(
    evidence: dict[str, bool], expected: bool
) -> None:
    count, valid = q1._submission_proof({"execution_chain": evidence})
    assert count == 1
    assert valid is expected


@pytest.mark.parametrize(
    "private_value",
    [
        {"api_key": "x"},
        {"private_key": "x"},
        {"account_address": "x"},
        {"authorization": "Bearer x"},
        {"raw_log": "x"},
    ],
)
def test_private_artifact_rejected(private_value: dict[str, str]) -> None:
    with pytest.raises(q1.QualificationGap):
        q1._safe_artifact(private_value)


def test_memory_adapter_records_identity_without_transport() -> None:
    adapter = q1.MemoryNotificationAdapter()
    assert adapter.deliver(SimpleNamespace(idempotency_key="only-local")).status_code == 204
    assert adapter.attempted == ["only-local"]
    assert not hasattr(adapter, "post")


@pytest.mark.parametrize(
    ("status", "error"),
    [
        ("PRODUCT_BLOCKER", q1.ProductBlocker),
        ("PROVIDER_DATA_INCOMPLETE", q1.ProviderIncomplete),
        ("HARNESS_OR_EXECUTION_SURFACE_GAP", q1.QualificationGap),
    ],
)
def test_child_result_preserves_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    error: type[Exception],
) -> None:
    def fake_run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        result_path = Path(command[command.index("--result") + 1])
        result_path.write_text(json.dumps({"classification": status}))
        return subprocess.CompletedProcess(command, 2, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(error):
        q1._run_child(tmp_path, tmp_path, 1, q1.BASE_SHA, q1.BASE_TREE, 60)


def test_known_custom_failure_has_bounded_stage_and_guard() -> None:
    q1._mark_stage("DEPENDENCY_LOCKS")
    diagnostic = q1._failure_diagnostic(q1.QualificationGap("pilot lock identity differs"))
    assert diagnostic == {
        "reason_stage": "DEPENDENCY_LOCKS",
        "reason_code": "QualificationGap",
        "reason_detail": "pilot lock identity differs",
    }
    q1._safe_artifact(diagnostic)
    assert (
        q1.classify(dict.fromkeys(q1.MANDATORY, True), "HARNESS_OR_EXECUTION_SURFACE_GAP")
        != "PASS"
    )


def test_async_failure_stage_reaches_outer_handler() -> None:
    async def fail() -> None:
        q1._mark_stage("PUBLIC_FIXTURE")
        raise q1.ProviderIncomplete("public MAIN metadata unavailable")

    with pytest.raises(q1.ProviderIncomplete) as caught:
        asyncio.run(fail())
    assert q1._failure_diagnostic(caught.value) == {
        "reason_stage": "PUBLIC_FIXTURE",
        "reason_code": "ProviderIncomplete",
        "reason_detail": "public MAIN metadata unavailable",
    }
    q1._mark_stage("CHILD_LIVE")
    assert q1._failure_diagnostic(q1.ProductBlocker("old boundary became newly actionable")) == {
        "reason_stage": "CHILD_LIVE",
        "reason_code": "ProductBlocker",
        "reason_detail": "old boundary became newly actionable",
    }


def test_unknown_exception_never_exposes_its_message() -> None:
    q1._mark_stage("PUBLIC_FIXTURE")
    diagnostic = q1._failure_diagnostic(ValueError("api_key=private account secret"))
    assert diagnostic == {"reason_stage": "PUBLIC_FIXTURE", "reason_code": "ValueError"}
    q1._safe_artifact(diagnostic)
    assert q1._failure_diagnostic(q1.QualificationGap("api_key=private account secret")) == {
        "reason_stage": "PUBLIC_FIXTURE", "reason_code": "QualificationGap"
    }


def test_child_bounded_reason_propagates_to_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        result_path = Path(command[command.index("--result") + 1])
        result_path.write_text(json.dumps({
            "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP",
            "reason_stage": "CHILD_COMPOSITION",
            "reason_code": "QualificationGap",
            "reason_detail": "exact external LAST 1m/5m BarTypes are unavailable",
        }))
        return subprocess.CompletedProcess(command, 2, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(q1.QualificationGap) as caught:
        q1._run_child(tmp_path, tmp_path, 1, q1.BASE_SHA, q1.BASE_TREE, 60)
    assert q1._failure_diagnostic(caught.value) == {
        "reason_stage": "CHILD_COMPOSITION",
        "reason_code": "QualificationGap",
        "reason_detail": "exact external LAST 1m/5m BarTypes are unavailable",
    }
    assert (
        q1.classify(dict.fromkeys(q1.MANDATORY, True), "HARNESS_OR_EXECUTION_SURFACE_GAP")
        != "PASS"
    )


def test_child_untrusted_reason_is_not_propagated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        result_path = Path(command[command.index("--result") + 1])
        result_path.write_text(json.dumps({
            "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP",
            "reason_stage": "CHILD_COMPOSITION",
            "reason_code": "QualificationGap",
            "reason_detail": "api_key=private account secret",
        }))
        return subprocess.CompletedProcess(command, 2, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(q1.QualificationGap) as caught:
        q1._run_child(tmp_path, tmp_path, 1, q1.BASE_SHA, q1.BASE_TREE, 60)
    assert q1._failure_diagnostic(caught.value) == {
        "reason_stage": "CHILD_RESULT",
        "reason_code": "QualificationGap",
        "reason_detail": "child segment execution surface failed",
    }
    with pytest.raises(q1.QualificationGap):
        q1._safe_artifact({"reason_detail": "api_key=private account secret"})


def test_child_entry_checkpoint_precedes_candidate_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "child-result.json"
    stages: list[str] = []
    checkpoint = q1._child_checkpoint

    def recording_checkpoint(path: Path, stage: str) -> None:
        stages.append(stage)
        checkpoint(path, stage)

    def abrupt_identity(_candidate: Path, _sha: str, _tree: str) -> None:
        assert json.loads(target.read_text()) == {
            "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP",
            "reason_code": "ChildInProgress",
            "reason_stage": "CHILD_IDENTITY",
        }
        raise SystemExit(7)

    monkeypatch.setattr(q1, "exact_identity", abrupt_identity)
    monkeypatch.setattr(q1, "_child_checkpoint", recording_checkpoint)
    monkeypatch.setattr(sys, "argv", [
        "q1", "--candidate", str(tmp_path), "--result", str(target),
        "--root", str(tmp_path), "--internal-segment", "1",
    ])
    with pytest.raises(SystemExit):
        q1.main()
    assert stages == ["CHILD_ENTRY", "CHILD_IDENTITY"]
    assert json.loads(target.read_text())["reason_stage"] == "CHILD_IDENTITY"


@pytest.mark.parametrize(
    ("failure", "expected_code", "expected_detail"),
    [
        (q1.QualificationGap("candidate HEAD drift"), "QualificationGap", "candidate HEAD drift"),
        (ValueError("api_key=hidden"), "ValueError", None),
    ],
)
def test_caught_child_failure_replaces_checkpoint_without_raw_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_code: str,
    expected_detail: str | None,
) -> None:
    target = tmp_path / "child-result.json"

    def failing_identity(_candidate: Path, _sha: str, _tree: str) -> None:
        raise failure

    monkeypatch.setattr(q1, "exact_identity", failing_identity)
    monkeypatch.setattr(sys, "argv", [
        "q1", "--candidate", str(tmp_path), "--result", str(target),
        "--root", str(tmp_path), "--internal-segment", "1",
    ])
    assert q1.main() == 2
    result = json.loads(target.read_text())
    assert result["classification"] == "HARNESS_OR_EXECUTION_SURFACE_GAP"
    assert result["reason_stage"] == "CHILD_IDENTITY"
    assert result["reason_code"] == expected_code
    assert result.get("reason_detail") == expected_detail
    assert "api_key" not in target.read_text()


def test_child_checkpoints_advance_and_final_result_replaces_them(tmp_path: Path) -> None:
    target = tmp_path / "child-result.json"
    stages = (
        "CHILD_ENTRY", "CHILD_IDENTITY", "CHILD_RETAINED", "CHILD_COMPOSITION",
        "CHILD_LIVE", "CHILD_ARTIFACT_WRITE",
    )
    for stage in stages:
        q1._child_checkpoint(target, stage)
        assert json.loads(target.read_text()) == {
            "classification": "HARNESS_OR_EXECUTION_SURFACE_GAP",
            "reason_stage": stage,
            "reason_code": "ChildInProgress",
        }
    with pytest.raises(ValueError):
        q1._child_checkpoint(target, "UNBOUNDED_STAGE")
    q1._write_child_result(target, {"classification": "SEGMENT_COMPLETE"})
    assert json.loads(target.read_text()) == {"classification": "SEGMENT_COMPLETE"}


@pytest.mark.parametrize(
    ("returncode", "expected_signal"), [(127, None), (-9, ("SIGKILL", 9))]
)
def test_abrupt_child_exit_preserves_checkpoint_and_bounded_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    expected_signal: tuple[str, int] | None,
) -> None:
    def fake_run(command: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
        target = Path(command[command.index("--result") + 1])
        q1._child_checkpoint(target, "CHILD_COMPOSITION")
        return subprocess.CompletedProcess(
            command, returncode, "api_key=hidden-output", "private account stderr"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(q1.QualificationGap) as caught:
        q1._run_child(tmp_path, tmp_path, 1, q1.BASE_SHA, q1.BASE_TREE, 60)
    diagnostic = q1._failure_diagnostic(caught.value)
    assert diagnostic["reason_stage"] == "CHILD_COMPOSITION"
    assert diagnostic["reason_code"] == "ChildInProgress"
    assert diagnostic["reason_returncode"] == returncode
    if expected_signal is None:
        assert "reason_signal" not in diagnostic
    else:
        assert (diagnostic["reason_signal"], diagnostic["reason_signal_number"]) == expected_signal
    assert "api_key" not in json.dumps(diagnostic)
    assert "stderr" not in json.dumps(diagnostic)
    q1._safe_artifact(diagnostic)
    assert (
        q1.classify(dict.fromkeys(q1.MANDATORY, True), "HARNESS_OR_EXECUTION_SURFACE_GAP")
        != "PASS"
    )


def test_example_declares_distinct_store_lifetimes() -> None:
    example = json.loads(
        (
            Path(__file__).parents[1]
            / "deploy/p4a/evidence/three-setup-q1-qualification-v1.json.example"
        ).read_text()
    )
    assert set(example["acceptance_matrix"]) == set(q1.MANDATORY)
    assert set(example["adversarial_matrix"]) == set(q1.ADVERSARIAL)
    assert (
        example["sqlite_integrity"]["product_closed_bar_store"]["storage_mode"] == "sqlite::memory:"
    )
    assert example["sqlite_integrity"]["domain_evidence"] == []
    assert example["classification"] != "PASS"
    assert example["reason_stage"] == example["reason_code"] == "UNRUN"
    assert example["reason_detail"] is None
    assert example["reason_returncode"] is None
    assert example["reason_signal"] is None
    assert example["reason_signal_number"] is None
