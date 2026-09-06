"""Non-regression proof for the repository-owned Issue #102 S1 harness."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts import s1_native_single_market_rehearsal as s1
from trader_assist_v0.multi_asset_shadow.hyperliquid_public import HyperliquidPublicClient


def _sqlite(path: Path, *, value: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE proof(value TEXT NOT NULL)")
        connection.execute("INSERT INTO proof(value) VALUES (?)", (value,))
        connection.commit()


def _checkpoint(root: Path) -> Path:
    root.mkdir()
    _sqlite(root / "evidence.sqlite", value="evidence")
    _sqlite(root / "closed-bars.sqlite", value="bars")
    registry = root / "registry"
    registry.mkdir()
    (registry / "active.json").write_text('{"version":"s1"}\n', encoding="utf-8")
    return root


def test_http_post_wrapper_preserves_raw_bytes_and_client_owns_json_decode() -> None:
    raw = b'[{"ok":true}]'

    def delegate(url: str, body: bytes, timeout_seconds: float) -> bytes:
        assert url == s1.INFO_URL
        assert timeout_seconds > 0
        assert json.loads(body)["type"] in {"candleSnapshot", "l2Book"}
        return raw

    observed = s1.CountingRawPost(delegate)
    client = HyperliquidPublicClient(post=observed)
    result = client.closed_candles(coin="BTC", interval="5m", start_ms=0, end_ms=300_000)
    assert result == [{"ok": True}]
    assert observed.request_types == ["candleSnapshot"]
    assert observed(s1.INFO_URL, b'{"type":"l2Book","coin":"BTC"}', 1.0) is raw
    assert observed.request_types == ["candleSnapshot", "l2Book"]


def test_sqlite_backup_preserves_committed_wal_state(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite"
    connection = sqlite3.connect(source)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE proof(value TEXT NOT NULL)")
        connection.commit()
        connection.execute("INSERT INTO proof(value) VALUES ('committed-in-wal')")
        connection.commit()
        wal = Path(f"{source}-wal")
        assert wal.exists() and wal.stat().st_size > 0

        destination = tmp_path / "snapshot.sqlite"
        s1._sqlite_snapshot(source, destination)
        with sqlite3.connect(destination) as copied:
            assert copied.execute("SELECT value FROM proof").fetchall() == [("committed-in-wal",)]
            assert copied.execute("PRAGMA quick_check").fetchall() == [("ok",)]
            assert copied.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
    finally:
        connection.close()


def test_checkpoint_snapshot_preserves_source_and_uses_exact_owned_assets(tmp_path: Path) -> None:
    source = _checkpoint(tmp_path / "checkpoint")
    attempt = tmp_path / "attempt"
    before = {
        "evidence": s1._logical_sqlite_hash(source / "evidence.sqlite"),
        "bars": s1._logical_sqlite_hash(source / "closed-bars.sqlite"),
        "registry": s1._tree_manifest(source / "registry"),
    }

    snapshot = s1.snapshot_checkpoint(source, attempt)

    after = {
        "evidence": s1._logical_sqlite_hash(source / "evidence.sqlite"),
        "bars": s1._logical_sqlite_hash(source / "closed-bars.sqlite"),
        "registry": s1._tree_manifest(source / "registry"),
    }
    assert snapshot.source_preserved is True
    assert before == after
    assert s1._logical_sqlite_hash(attempt / "evidence.sqlite") == before["evidence"]
    assert s1._logical_sqlite_hash(attempt / "closed-bars.sqlite") == before["bars"]
    assert s1._tree_manifest(attempt / "registry") == before["registry"]


def test_checkpoint_snapshot_includes_committed_wal_state(tmp_path: Path) -> None:
    source = _checkpoint(tmp_path / "checkpoint")
    evidence = sqlite3.connect(source / "evidence.sqlite")
    try:
        assert evidence.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        evidence.execute("PRAGMA wal_autocheckpoint=0")
        evidence.execute("INSERT INTO proof(value) VALUES ('wal-commit')")
        evidence.commit()
        wal = Path(f"{source / 'evidence.sqlite'}-wal")
        assert wal.exists() and wal.stat().st_size > 0
        source_hash = s1._logical_sqlite_hash(source / "evidence.sqlite")

        attempt = tmp_path / "attempt"
        snapshot = s1.snapshot_checkpoint(source, attempt)

        assert snapshot.source_preserved is True
        assert s1._logical_sqlite_hash(attempt / "evidence.sqlite") == source_hash
        with sqlite3.connect(attempt / "evidence.sqlite") as copied:
            assert copied.execute("SELECT value FROM proof ORDER BY rowid").fetchall() == [
                ("evidence",),
                ("wal-commit",),
            ]
    finally:
        evidence.close()


def test_checkpoint_snapshot_fails_closed_on_existing_attempt_and_missing_owned_db(
    tmp_path: Path,
) -> None:
    source = _checkpoint(tmp_path / "checkpoint")
    existing = tmp_path / "attempt"
    existing.mkdir()
    with pytest.raises(s1.S1HarnessError, match="already exists"):
        s1.snapshot_checkpoint(source, existing)

    missing = _checkpoint(tmp_path / "missing")
    (missing / "closed-bars.sqlite").unlink()
    with pytest.raises(s1.S1HarnessError, match="closed-bars.sqlite"):
        s1.snapshot_checkpoint(missing, tmp_path / "new-attempt")


def test_ready_and_ack_witness_survives_post_teardown_zero_state(tmp_path: Path) -> None:
    witness = s1.SessionWitness(tmp_path / "witness.jsonl")
    witness.record("CONNECTION", {"connection_count": 1})
    witness.record("ACK_PROGRESS", {"acknowledged": 1, "expected": 1})
    witness.record("READY", {"acknowledged": 1, "expected": 1})

    post_teardown_health = {
        "connection_count": 0,
        "acknowledgements": [],
        "data_ready": False,
        "ws_phase": "SHUTDOWN",
    }
    assert post_teardown_health["connection_count"] == 0
    assert post_teardown_health["data_ready"] is False
    assert witness.connection_proven is True
    assert witness.acknowledgement_proven is True
    assert witness.ready_proven is True

    raw = witness.path.read_bytes()
    assert raw.endswith(b"\n")
    persisted = [json.loads(line) for line in raw.splitlines()]
    assert [item["event"] for item in persisted] == ["CONNECTION", "ACK_PROGRESS", "READY"]
    assert [item["sequence"] for item in persisted] == [1, 2, 3]


def test_claim_classification_separates_harness_and_application_failure() -> None:
    base = dict(
        timed_out=False,
        source_preserved=True,
        connection_proven=True,
        acknowledgement_proven=True,
        ready_proven=True,
        live_actionable_finalized_count=1,
        final_lifecycle="ACTIVE",
        provider_request_types=("candleSnapshot", "l2Book"),
    )
    assert s1.classify_claim(
        s1.ClaimInputs(application_error=None, harness_error="S1HarnessError", **base)
    ) == ("UNPROVEN", "WRAPPER_OR_HARNESS_FAILURE")
    assert s1.classify_claim(
        s1.ClaimInputs(application_error="DataRouteError", harness_error=None, **base)
    ) == ("FAIL", "APPLICATION_FAILURE")
    assert s1.classify_claim(
        s1.ClaimInputs(application_error=None, harness_error=None, **base)
    ) == ("PASS", None)


def test_post_teardown_state_is_not_an_input_to_claim_classification() -> None:
    inputs = s1.ClaimInputs(
        application_error=None,
        harness_error=None,
        timed_out=False,
        source_preserved=True,
        connection_proven=True,
        acknowledgement_proven=True,
        ready_proven=True,
        live_actionable_finalized_count=1,
        final_lifecycle="ACTIVE",
        provider_request_types=("candleSnapshot", "l2Book"),
    )
    assert not hasattr(inputs, "post_teardown_health")
    assert s1.classify_claim(inputs) == ("PASS", None)


def test_unexpected_metadata_request_fails_s1_claim() -> None:
    inputs = s1.ClaimInputs(
        application_error=None,
        harness_error=None,
        timed_out=False,
        source_preserved=True,
        connection_proven=True,
        acknowledgement_proven=True,
        ready_proven=True,
        live_actionable_finalized_count=1,
        final_lifecycle="ACTIVE",
        provider_request_types=("meta", "candleSnapshot", "l2Book"),
    )
    assert s1.classify_claim(inputs) == ("FAIL", "UNEXPECTED_PROVIDER_REQUEST")


def test_notification_sink_is_network_free() -> None:
    sink = s1.NoNetworkWebhook()
    response = sink.post(url="https://should-not-be-contacted.invalid")
    assert response.status_code == 204
    assert sink.calls == 1
