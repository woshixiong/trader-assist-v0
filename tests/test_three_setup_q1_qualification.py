"""Focused fault checks for the Q1 control harness and actual product store."""

from __future__ import annotations

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
