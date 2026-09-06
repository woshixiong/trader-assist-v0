from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts.run_s1_public_provider_rehearsal import (
    ApplicationEventCapture,
    NoNetworkWebhook,
    RecordingHttpPost,
    S1RehearsalError,
    _claim_passes,
    _cold_warmup_reintroduced,
    _durable_source_manifest,
    _live_proof_if_ready,
    _prepare_attempt,
    _validate_attempt_path,
)
from trader_assist_v0.multi_asset_shadow.runtime import (
    RuntimeHealth,
    RuntimeReadinessSnapshot,
)

MARKET_ID = "a" * 64


def _source_checkpoint(root: Path) -> sqlite3.Connection:
    root.mkdir()
    evidence = sqlite3.connect(root / "evidence.sqlite")
    evidence.execute("PRAGMA journal_mode=WAL")
    evidence.execute("CREATE TABLE records (value TEXT NOT NULL)")
    evidence.execute("INSERT INTO records VALUES ('base')")
    evidence.commit()
    evidence.execute("INSERT INTO records VALUES ('wal-commit')")
    evidence.commit()

    with sqlite3.connect(root / "closed-bars.sqlite") as closed:
        closed.execute(
            "CREATE TABLE closed_bars ("
            "market_id TEXT NOT NULL, interval TEXT NOT NULL, open_time_ms INTEGER NOT NULL)"
        )
        closed.execute("INSERT INTO closed_bars VALUES (?, '5m', 300000)", (MARKET_ID,))

    registry = root / "registry"
    (registry / "versions").mkdir(parents=True)
    (registry / "versions" / "one.json").write_text("{}\n", encoding="utf-8")
    (registry / "current.json").write_text("{}\n", encoding="utf-8")
    assert (root / "evidence.sqlite-wal").is_file()
    return evidence


def _ready_application() -> Any:
    health = RuntimeHealth(
        connection_count=1,
        subscriptions=1,
        acknowledgements={"BTC"},
        expected_acknowledgements=1,
        ws_phase="READY",
        ready_transitions=1,
        data_ready=True,
    )
    readiness = RuntimeReadinessSnapshot.create(
        registry_version="v1",
        registry_content_hash="b" * 64,
        data_ready=True,
        ready_market_ids=(MARKET_ID,),
        failed_market_ids=(),
        latest_closed_5m_open_time_ms=300_000,
        observed_at_ms=600_000,
    )
    runtime = SimpleNamespace(health=health, readiness_snapshot=lambda: readiness)
    return SimpleNamespace(bootstrap=SimpleNamespace(runtime=runtime))


def _ready_events() -> tuple[dict[str, object], ...]:
    return (
        {"event": "WS_CONNECTION", "connection_count": 1},
        {"event": "WS_READY", "acknowledged": 1, "expected": 1},
        {"event": "FINALIZED_5M", "evaluation_mode": "LIVE_ACTIONABLE"},
    )


def test_checkpoint_snapshot_includes_live_wal_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    evidence = _source_checkpoint(source)
    before = _durable_source_manifest(source)
    wal_before = (source / "evidence.sqlite-wal").read_bytes()
    try:
        preparation = _prepare_attempt(source, tmp_path / "attempt")
        attempt = tmp_path / "attempt"
        with sqlite3.connect(attempt / "evidence.sqlite") as copied:
            assert copied.execute("SELECT value FROM records ORDER BY value").fetchall() == [
                ("base",),
                ("wal-commit",),
            ]
        assert preparation["source_manifest_before"] == before
        assert _durable_source_manifest(source) == before
        assert (source / "evidence.sqlite-wal").read_bytes() == wal_before
        assert (attempt / "closed-bars.sqlite").is_file()
        assert (attempt / "registry" / "versions" / "one.json").is_file()
        assert not (attempt / "evidence.sqlite-wal").exists()
    finally:
        evidence.close()


def test_missing_known_evidence_wal_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    evidence = _source_checkpoint(source)
    evidence.close()
    wal = source / "evidence.sqlite-wal"
    wal.unlink(missing_ok=True)
    with pytest.raises(S1RehearsalError, match="evidence SQLite WAL"):
        _durable_source_manifest(source)


def test_attempt_path_never_overwrites_or_nests_checkpoint(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(S1RehearsalError, match="already exists"):
        _validate_attempt_path(source, existing)
    with pytest.raises(S1RehearsalError, match="separate sibling"):
        _validate_attempt_path(source, source / "child")


def test_http_recorder_preserves_raw_bytes_and_records_only_public_shape() -> None:
    recorder = RecordingHttpPost(lambda _url, _body, _timeout: b"[]")
    body = json.dumps(
        {
            "type": "candleSnapshot",
            "req": {
                "coin": "BTC",
                "interval": "5m",
                "startTime": 300_000,
                "endTime": 600_000,
            },
        }
    ).encode()
    assert recorder("https://api.hyperliquid.xyz/info", body, 15.0) == b"[]"
    assert recorder.calls == [
        {
            "type": "candleSnapshot",
            "coin": "BTC",
            "interval": "5m",
            "startTime": 300_000,
            "endTime": 600_000,
        }
    ]


def test_http_recorder_rejects_decoded_delegate_output() -> None:
    def bad_delegate(_url: str, _body: bytes, _timeout: float) -> Any:
        return []

    recorder = RecordingHttpPost(bad_delegate)
    with pytest.raises(S1RehearsalError, match="raw-bytes"):
        recorder("https://api.hyperliquid.xyz/info", b'{"type":"perpDexs"}', 15.0)


def test_pre_shutdown_proof_survives_later_teardown_normalization() -> None:
    application = _ready_application()
    proof = _live_proof_if_ready(
        application=application,
        market_id=MARKET_ID,
        coin="BTC",
        lifecycle_sequence=("WARMING", "HISTORY_READY", "SNAPSHOT_READY", "ACTIVE"),
        events=_ready_events(),
    )
    assert proof is not None
    assert proof["captured_before_shutdown"] is True
    assert proof["connection_count"] == 1
    assert proof["data_ready"] is True
    assert proof["ws_phase"] == "READY"

    health = application.bootstrap.runtime.health
    health.connection_count = 0
    health.acknowledgements.clear()
    health.data_ready = False
    health.ws_phase = "SHUTDOWN"

    assert proof["connection_count"] == 1
    assert proof["acknowledgements"] == ["BTC"]
    assert proof["data_ready"] is True
    assert proof["ws_phase"] == "READY"
    assert (
        _live_proof_if_ready(
            application=application,
            market_id=MARKET_ID,
            coin="BTC",
            lifecycle_sequence=("ACTIVE",),
            events=_ready_events(),
        )
        is None
    )


def test_proof_requires_authoritative_ready_event_and_live_actionable_boundary() -> None:
    application = _ready_application()
    assert (
        _live_proof_if_ready(
            application=application,
            market_id=MARKET_ID,
            coin="BTC",
            lifecycle_sequence=("ACTIVE",),
            events=({"event": "WS_CONNECTION"},),
        )
        is None
    )


def test_application_event_capture_ignores_unstructured_output() -> None:
    capture = ApplicationEventCapture()
    logger = logging.getLogger("test.s1.event.capture")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.addHandler(capture)
    logger.info("not-json")
    logger.info('{"event":"WS_READY","expected":1}')
    assert capture.snapshot() == ({"event": "WS_READY", "expected": 1},)


def test_cold_warmup_detection_distinguishes_retained_recovery() -> None:
    last_open = 10_000_000_000
    recovery = (
        {
            "type": "candleSnapshot",
            "interval": "5m",
            "startTime": last_open + 300_000,
        },
    )
    cold = (
        {
            "type": "candleSnapshot",
            "interval": "5m",
            "startTime": last_open - (2_303 * 300_000),
        },
    )
    assert _cold_warmup_reintroduced(recovery, last_open) is False
    assert _cold_warmup_reintroduced(cold, last_open) is True


def test_no_network_webhook_is_observable_without_network() -> None:
    webhook = NoNetworkWebhook()
    response = webhook.post(
        url="https://example.invalid/s1",
        payload=b"{}",
        headers={},
        timeout_seconds=1.0,
    )
    assert response.status_code == 204
    assert webhook.calls == 1


def test_claim_evaluator_requires_all_positive_gates_and_no_cold_warmup() -> None:
    checks = {"one": True, "two": True, "reran_2304_warmup": False}
    assert _claim_passes(checks) is True
    checks["reran_2304_warmup"] = True
    assert _claim_passes(checks) is False
    checks["reran_2304_warmup"] = False
    checks["two"] = False
    assert _claim_passes(checks) is False
