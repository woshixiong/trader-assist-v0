"""Frozen L0 identity, pacing and fail-closed qualification predicates."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.build_multi_asset_registry_seed import build_launch_identity
from scripts.e4_nautilus_public_data_probe import (
    QualificationObservation,
    WarmupDispatchPacer,
    evaluate_qualification,
    launch_bars,
)
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.production import (
    THREE_SETUP_CLOSED_BAR_STORE_PATH,
    THREE_SETUP_EVIDENCE_STORE_PATH,
    THREE_SETUP_REGISTRY_ROOT,
    ThreeSetupProductionConfig,
    ThreeSetupProductionError,
    _ObservedQueue,
)
from trader_assist_v0.multi_asset_shadow.resolution import FIRST_LAUNCH_20, resolve_first_launch_20

NS = 1_000_000_000
NOW = datetime(2026, 9, 27, tzinfo=UTC)


def identity():
    native, hip3 = [], []
    for r in FIRST_LAUNCH_20:
        (native if r.dex == "MAIN" else hip3).append(
            {"name": r.coin, "szDecimals": 2, "maxLeverage": 10}
        )
    resolutions = resolve_first_launch_20(
        perp_dexes=[{"name": "main"}, {"name": "xyz"}],
        all_perp_metas=[{"universe": native}, {"universe": hip3}],
        observed_at=NOW,
    )
    seed = RegistryVersion.create(
        version="l0",
        created_at=NOW,
        markets=tuple(r.market for r in resolutions),
    )
    instruments = [
        SimpleNamespace(raw_symbol=r.coin, id=f"{r.coin}.HYPERLIQUID") for r in FIRST_LAUNCH_20
    ]
    snapshot, manifest = build_launch_identity(
        seed=seed,
        instruments=instruments,
        sha="a" * 40,
        tree="b" * 40,
        run_id="l0-test",
        observed_at_ns=NS,
        metadata_evidence={},
    )
    return seed, snapshot, manifest


def test_duplicate_official_metadata_is_not_last_row_wins():
    with pytest.raises(ValueError, match="duplicate"):
        resolve_first_launch_20(
            perp_dexes=[{"name": "main"}],
            all_perp_metas=[{"universe": [{"name": "BTC"}, {"name": "BTC"}]}],
            observed_at=NOW,
        )


def test_identity_uses_actual_provider_objects_and_exact_40_bars():
    seed, snapshot, manifest = identity()
    bars = launch_bars(seed, snapshot)
    assert len(set(bars)) == 40
    assert manifest.subscription_policy["actionable"] == []
    assert manifest.capture_configuration["bar_types"] == list(bars)
    with pytest.raises(ValueError, match="unresolved/ambiguous"):
        build_launch_identity(
            seed=seed,
            instruments=[],
            sha="a" * 40,
            tree="b" * 40,
            run_id="l0-test",
            observed_at_ns=NS,
            metadata_evidence={},
        )


def test_pacer_requires_quiet_and_reserves_inclusive_raw_rows():
    pacer = WarmupDispatchPacer(60 * NS)
    assert not pacer.reserve(59 * NS, 60)
    assert all(pacer.reserve(60 * NS, 60) for _ in range(19))
    assert not pacer.reserve(60 * NS, 60)
    assert pacer.peak_weight == 399
    assert pacer.reserve(120 * NS, 60)


def test_reconnect_requires_observed_sequence_and_one_request():
    observation = QualificationObservation(("BTC.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",))
    observation.request(NS)
    observation.socket("CONNECTED", 2 * NS)
    assert "RECOVERY_SEQUENCE" in observation.failures
    observation.request(3 * NS)
    assert "RECONNECT_REQUEST_COUNT" in observation.failures
    blockers, _ = observation.evaluate(1000 * NS)
    assert "RECOVERY_INCOMPLETE" in blockers


def test_unknown_provider_is_incomplete_without_callback_count_proxy():
    seed, snapshot, manifest = identity()
    observation = QualificationObservation(launch_bars(seed, snapshot))
    report = evaluate_qualification(manifest, observation, NS, {}, [], {}, {})
    assert report["status"] == "INCOMPLETE"
    assert report["reason"] == "COST_AUTHORITY_ABSENT"
    assert report["submission_status"] == "NOT_SUBMITTED"
    assert "PROVIDER_UNKNOWN_OR_EXCEEDED:ws_connections" in report["blockers"]


def test_missing_cost_authority_requires_explicit_data_only(tmp_path: Path):
    paths = dict(
        release_sha="a" * 40,
        evidence_store_path=THREE_SETUP_EVIDENCE_STORE_PATH,
        registry_root=THREE_SETUP_REGISTRY_ROOT,
        closed_bar_store_path=THREE_SETUP_CLOSED_BAR_STORE_PATH,
    )
    with pytest.raises(ThreeSetupProductionError, match="DATA_COLLECTION_ONLY"):
        ThreeSetupProductionConfig(**paths, cost_model=None)
    config = ThreeSetupProductionConfig(**paths, cost_model=None, data_collection_only=True)
    assert config.cost_model is None


def test_finite_queue_reports_actual_capacity_and_overflow():
    queue = _ObservedQueue(2)
    queue.put_nowait("a")
    queue.put_nowait("b")
    with pytest.raises(asyncio.QueueFull):
        queue.put_nowait("c")
    assert queue.health() == {"capacity": 2, "max_depth": 2, "end_depth": 2, "overflows": 1}


@pytest.mark.parametrize("end_ns,passes", [
    (10_000_000_000_000, True),
    (6_400_000_000_000, True),
    (6_399_999_999_999, False),
    (10_000_000_000_001, False),
    (True, False), (False, False), (None, False),
    ("10000000000000", False), (10_000_000_000_000.0, False),
    ([], False), ({}, False), (0, False), (-1, False),
])
def test_startup_expiry_uses_digest_bound_end_ns_only(tmp_path, monkeypatch, end_ns, passes):
    from scripts.e4_nautilus_public_data_probe import L0_PROFILE, L0_SCHEMA
    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.multi_asset_shadow import production

    _, _, manifest = identity()
    manifest_path = tmp_path / "run-manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest.model_dump(mode="json")))
    report = dict(schema=L0_SCHEMA, status="PASS", blockers=[], profile=L0_PROFILE,
                  release_sha=manifest.git_sha, release_tree=manifest.git_tree,
                  manifest_hash=manifest.manifest_hash, snapshot_hash=manifest.pit_snapshot_hash)
    if end_ns is not None:
        report["end_ns"] = end_ns
    digest = sha256_hex(canonical_json_bytes(report))
    report["digest"] = digest
    report_path = tmp_path / "qualification.json"
    report_path.write_bytes(canonical_json_bytes(report))
    config = SimpleNamespace(data_collection_only=True, qualification_path=report_path,
                             qualification_digest=digest, e4_manifest_path=manifest_path)
    monkeypatch.setattr(production.time, "time_ns", lambda: 10_000_000_000_000)
    if passes:
        production.validate_l0_qualification(config)
    else:
        with pytest.raises(ThreeSetupProductionError, match="time|future|expired"):
            production.validate_l0_qualification(config)


@pytest.mark.parametrize("field", ["release_sha", "release_tree", "manifest_hash", "snapshot_hash",
                                    "digest", "profile", "status", "blockers"])
def test_expiry_never_waives_identity_or_digest(tmp_path, monkeypatch, field):
    from scripts.e4_nautilus_public_data_probe import L0_PROFILE, L0_SCHEMA
    from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
    from trader_assist_v0.multi_asset_shadow import production

    _, _, manifest = identity()
    manifest_path = tmp_path / "run-manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest.model_dump(mode="json")))
    report = dict(schema=L0_SCHEMA, status="PASS", blockers=[], profile=L0_PROFILE,
                  release_sha=manifest.git_sha, release_tree=manifest.git_tree,
                  manifest_hash=manifest.manifest_hash, snapshot_hash=manifest.pit_snapshot_hash,
                  end_ns=10_000_000_000_000)
    if field != "digest":
        report[field] = ["failed"] if field == "blockers" else "wrong"
    digest = sha256_hex(canonical_json_bytes(report))
    report["digest"] = "wrong" if field == "digest" else digest
    report_path = tmp_path / "qualification.json"
    report_path.write_bytes(canonical_json_bytes(report))
    config = SimpleNamespace(data_collection_only=True, qualification_path=report_path,
                             qualification_digest=digest, e4_manifest_path=manifest_path)
    monkeypatch.setattr(production.time, "time_ns", lambda: 10_000_000_000_000)
    with pytest.raises(ThreeSetupProductionError):
        production.validate_l0_qualification(config)


def native_log_fixture(tmp_path):
    import json

    from scripts.e4_nautilus_public_data_probe import NATIVE_STARTUP_SEPARATOR, native_marker

    _, _, manifest = identity()
    records = [dict(timestamp=NS, level="INFO", component=native_marker(manifest),
                    message=NATIVE_STARTUP_SEPARATOR)]
    records.append(dict(timestamp=2 * NS, level="DEBUG", component="nautilus_hyperliquid::data",
                        message="Bootstrapped 20 instruments with 20 coin mappings"))
    ledger = []
    for index, bar in enumerate(manifest.capture_configuration["bar_types"]):
        interval = "1m" if "-1-MINUTE-" in bar else "5m"
        duration = 60_000 if interval == "1m" else 300_000
        timestamp = (62 + index // 19 * 60) * NS
        ledger.append(dict(bar_type=bar, coin=bar.split(".HYPERLIQUID")[0], interval=interval,
                           start=1_000_000, end=1_000_000 + duration * 59,
                           raw_max_rows=60, reserved_weight=21, ts_ns=timestamp))
        records.append(dict(timestamp=timestamp + 1, level="DEBUG",
                            component="nautilus_hyperliquid::data",
                            message=f"Fetched 59 bars for {bar}"))
    path = tmp_path / "native.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return manifest, ledger, records, path


def parse_fixture(manifest, ledger, path, *, synced=True):
    from scripts.e4_nautilus_public_data_probe import parse_native_http_log

    metadata = path.stat()
    return parse_native_http_log(path, manifest=manifest, dispatches=ledger,
                                 file_identity=(metadata.st_dev, metadata.st_ino),
                                 sync_succeeded=synced)


def test_native_complete_log_no_debit_proves_zero_extra_not_callback_count(tmp_path):
    manifest, ledger, _, path = native_log_fixture(tmp_path)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "PASS"
    assert report["metadata_requests"] == 5
    assert report["metadata_weight"] == 100
    assert report["raw_response_reservations_verified"] is True
    assert len(report["matched_requests"]) == 40
    assert all(r["actual_extra"] == 0 for r in report["matched_requests"])


@pytest.mark.parametrize("mutation", ["pre_marker", "missing_marker", "duplicate_marker",
                                     "mixed_run", "duplicate_completion", "missing_completion",
                                     "malformed", "malformed_retry", "unsynced", "unterminated"])
def test_native_log_current_run_ambiguity_is_incomplete(tmp_path, mutation):
    import json

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    if mutation == "pre_marker":
        records.insert(0, records[1])
    elif mutation == "missing_marker":
        records.pop(0)
    elif mutation == "duplicate_marker":
        records.insert(1, dict(timestamp=NS, level="INFO",
                               component=records[0]["component"],
                               message=" NAUTILUS TRADER - Automated Algorithmic Trading Platform"))
        records.insert(2, records[1])
    elif mutation == "mixed_run":
        records[0]["component"] += "old-run"
    elif mutation == "duplicate_completion":
        records.insert(3, records[2])
    elif mutation == "missing_completion":
        records.pop(2)
    elif mutation == "malformed":
        records[2].pop("timestamp")
    elif mutation == "malformed_retry":
        records.insert(2, dict(timestamp=3 * NS, level="WARN",
                               component="nautilus_hyperliquid::http::client",
                               message="Transient error; retrying: 408"))
    content = "\n".join(json.dumps(r) for r in records)
    path.write_text(content + ("" if mutation == "unterminated" else "\n"))
    report = parse_fixture(manifest, ledger, path, synced=mutation != "unsynced")
    assert report["status"] == "INCOMPLETE"
    assert report["blockers"]


@pytest.mark.parametrize("extra,passes", [(1, True), (2, False)])
def test_native_debit_is_raw_weight_authority_and_must_fit_reservation(tmp_path, extra, passes):
    import json

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    dispatch = ledger[0]
    endpoint = (f'CandleSnapshot {{ req: CandleSnapshotRequest {{ coin: '
                f'{json.dumps(dispatch["coin"])}, interval: "1m", '
                f'start_time: {dispatch["start"]}, end_time: {dispatch["end"]} }} }}')
    records.insert(2, dict(timestamp=dispatch["ts_ns"], level="DEBUG",
                          component="nautilus_hyperliquid::http::client",
                          message=f"Info debited extra weight: endpoint={endpoint}, "
                                  f"base_w=20, extra={extra}"))
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    report = parse_fixture(manifest, ledger, path)
    assert (report["status"] == "PASS") is passes
    if passes:
        assert report["matched_requests"][0]["actual_weight"] == 21
    else:
        assert "NATIVE_WEIGHT_EXCEEDS_RESERVATION" in report["blockers"]


def test_native_header_marker_is_release_bound_without_synthetic_end(tmp_path):
    from scripts.e4_nautilus_public_data_probe import native_marker

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    assert records[0]["component"] == native_marker(manifest)
    assert not any("L0_NATIVE_HTTP_END" in r["message"] for r in records)
    assert parse_fixture(manifest, ledger, path)["status"] == "PASS"


def test_raw_callback_claim_cannot_replace_native_file_evidence():
    _, _, manifest = identity()
    observation = QualificationObservation(tuple(manifest.capture_configuration["bar_types"]))
    report = evaluate_qualification(manifest, observation, NS,
                                    {"raw_response_reservations_verified": True}, [], {}, {})
    assert "RAW_RESPONSE_WEIGHT_UNPROVEN" in report["blockers"]


def control_fixture(tmp_path, controls, epochs=None, forecast=None, reserve=2):
    import json

    from scripts.e4_nautilus_public_data_probe import parse_native_ws_controls

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    for component, message, timestamp in controls:
        records.append(dict(timestamp=timestamp, level="TRACE", component=component,
                            message=message))
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    native = parse_fixture(manifest, ledger, path)
    return parse_native_ws_controls(path, native_http=native,
                                    epochs=epochs or [dict(start_ns=NS, end_ns=300 * NS)],
                                    outbound_forecast=forecast or [(62 * NS, 100)],
                                    close_reserve=reserve)


@pytest.mark.parametrize("forecast,passes", [(996, True), (997, False)])
def test_b1d_exact_1000_ceiling(tmp_path, forecast, passes):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    report = control_fixture(tmp_path, [(WS_CONTROL_COMPONENT, "Received pong", 62 * NS)],
                             forecast=[(62 * NS, forecast)])
    assert (report["status"] == "PASS") is passes
    assert report["max_rolling_60s"] == forecast + 4


def test_b1d_rolling_boundary_and_unmatched_auto_ping_bound(tmp_path):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    report = control_fixture(tmp_path, [
        (WS_CONTROL_COMPONENT, "Received pong", 62 * NS),
        (WS_CONTROL_COMPONENT, "Received ping frame (0 bytes)", 122 * NS),
    ], forecast=[(62 * NS, 100), (122 * NS, 100)])
    assert report["status"] == "PASS"
    window = next(w for w in report["windows"] if w["end_ns"] == 122 * NS)
    assert window["protocol_pong_rx_count"] == 0
    assert window["auto_pong_count"] == 1
    assert window["auto_ping_upper_bound"] == 1
    assert window["native_outbound_forecast"] == 100


def test_b1d_two_epochs_include_one_unmatched_auto_ping_each(tmp_path):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    report = control_fixture(tmp_path, [(WS_CONTROL_COMPONENT, "Received pong", 62 * NS)],
                             epochs=[dict(start_ns=NS, end_ns=60 * NS),
                                     dict(start_ns=61 * NS, end_ns=300 * NS)])
    window = next(w for w in report["windows"] if w["end_ns"] == 62 * NS)
    assert report["status"] == "PASS"
    assert window["epochs_intersecting"] == 2
    assert window["auto_ping_upper_bound"] == 3


@pytest.mark.parametrize("component,message", [
    ("wrong::component", "Received pong"),
    ("nautilus_network::websocket::client", "Received pong extra"),
    ("nautilus_network::websocket::client", "Received ping frame (True bytes)"),
    ("nautilus_network::websocket::client", "Received ping frame (-1 bytes)"),
])
def test_b1d_control_component_and_message_ambiguity_is_incomplete(tmp_path, component, message):
    report = control_fixture(tmp_path, [(component, message, 62 * NS)])
    assert report["status"] == "INCOMPLETE"


def test_b1d_extra_connection_epoch_is_incomplete(tmp_path):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    report = control_fixture(tmp_path, [(WS_CONTROL_COMPONENT, "Received pong", 62 * NS)],
                             epochs=[dict(start_ns=NS, end_ns=20 * NS),
                                     dict(start_ns=21 * NS, end_ns=40 * NS),
                                     dict(start_ns=41 * NS, end_ns=300 * NS)])
    assert report["status"] == "INCOMPLETE"


def test_b1d_http_trace_is_never_control_authority(tmp_path):
    report = control_fixture(tmp_path, [("nautilus_hyperliquid::http::client",
                                        'raw HTTP response {"pong": true}', 62 * NS)])
    assert report["status"] == "INCOMPLETE"
    assert "WS_CONTROL_TRACE_MISSING" in report["blockers"]


def test_direct_probe_bootstrap_resolves_repository_scripts(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo / "src")
    script = repo / "scripts/e4_nautilus_public_data_probe.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"], cwd=tmp_path, env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--qualify-l0" in result.stdout
    code = f"""
import runpy
import sys
sys.argv = ['e4_nautilus_public_data_probe.py', '--help']
try:
    runpy.run_path({str(script)!r}, run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
from scripts.e4_nautilus_public_data_probe import native_marker
assert callable(native_marker)
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr


# F1 fixtures use the exact rc5 Rust Debug endpoint and zero-based retry attempt.
def retry_endpoint(dispatch):
    import json

    return (f'CandleSnapshot {{ req: CandleSnapshotRequest {{ '
            f'coin: {json.dumps(dispatch["coin"])}, interval: {json.dumps(dispatch["interval"])}, '
            f'start_time: {dispatch["start"]}, end_time: {dispatch["end"]} }} }}')


def retry_record(endpoint, timestamp, *, attempt=0, status=408, wait_ms=10):
    return dict(timestamp=timestamp, level="WARN", component="nautilus_hyperliquid::http::client",
                message=f"Transient error; retrying: endpoint={endpoint}, attempt={attempt}, "
                        f"status={status}, wait_ms={wait_ms}")


def write_retry_fixture(path, records):
    import json

    path.write_text("".join(json.dumps(r) + "\n" for r in
                            sorted(records, key=lambda r: r["timestamp"])))


def add_candle_retries(ledger, records, *, request_index=0, count=1, status=408):
    dispatch = ledger[request_index]
    for record in records:
        if record["message"] == f'Fetched 59 bars for {dispatch["bar_type"]}':
            record["timestamp"] = dispatch["ts_ns"] + NS
    for attempt in range(count):
        records.append(retry_record(retry_endpoint(dispatch),
                                    dispatch["ts_ns"] + (attempt + 1) * 100_000_000,
                                    attempt=attempt, status=status))


@pytest.mark.parametrize("status", [408, 500, 502, 503, 599])
def test_f1_matched_transient_adds_exact_base_weight_and_never_passes(tmp_path, status):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    baseline = parse_fixture(manifest, ledger, path)
    add_candle_retries(ledger, records, status=status)
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "FAIL"
    assert report["blockers"] == ["NATIVE_TRANSIENT_RETRY_ZERO_PREDICATE_FAILED"]
    assert report["native_retry_count"] == 1
    assert report["warmup_weight_per_60s"] == baseline["warmup_weight_per_60s"] + 20 == 400
    assert report["rest_weight_per_60s"] == baseline["rest_weight_per_60s"] + 20
    assert report["matched_retries"] == [dict(
        request_id=ledger[0]["bar_type"], cohort="warmup", endpoint=retry_endpoint(ledger[0]),
        attempt=0, status=status, wait_ms=10, ts_ns=ledger[0]["ts_ns"] + 100_000_000,
        base_weight=20,
    )]


@pytest.mark.parametrize("request_count,retries,expected", [(1, 2, 420), (1, 3, 440), (4, 3, 620)])
def test_f1_each_retry_charged_once_and_frozen_rest_budgets_fail(
    tmp_path, request_count, retries, expected,
):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    for index in range(request_count):
        add_candle_retries(ledger, records, request_index=index, count=retries, status=503)
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "FAIL"
    assert report["native_retry_count"] == request_count * retries
    assert sum(r["base_weight"] for r in report["matched_retries"]) == 20 * request_count * retries
    assert report["warmup_weight_per_60s"] == expected
    assert report["rest_weight_per_60s"] == expected
    assert "NATIVE_REST_BUDGET_EXCEEDED" in report["blockers"]
    assert "NATIVE_TRANSIENT_RETRY_EVIDENCE_INCOMPLETE" not in report["blockers"]


def test_f1_retry_weight_exact_rolling_boundary():
    from scripts.e4_nautilus_public_data_probe import _rolling_weight

    retry_ns = 62 * NS
    assert _rolling_weight([(retry_ns, 20), (retry_ns + 60 * NS, 400)]) == 400
    assert _rolling_weight([(retry_ns + 1, 20), (retry_ns + 60 * NS, 400)]) == 420
    assert _rolling_weight([(retry_ns, 20), (retry_ns + 60 * NS, 600)]) == 600
    assert _rolling_weight([(retry_ns + 1, 20), (retry_ns + 60 * NS, 600)]) == 620


@pytest.mark.parametrize("mutation", [
    "other_status", "malformed_status", "negative_attempt", "bool_attempt", "missing_attempt",
    "negative_wait", "bool_wait", "zero_wait", "malformed_endpoint", "unmatched_coin",
    "unmatched_interval", "unmatched_start", "unmatched_end", "unexpected_endpoint",
    "duplicate", "duplicate_attempt", "missing_attempt_zero", "attempt_gap", "attempt_exhausted",
    "before_dispatch", "after_completion", "wait_after_completion", "wait_overlaps_next_retry",
    "wrong_component", "wrong_level", "after_success_debit",
])
def test_f1_malformed_unbound_or_impossible_retry_is_incomplete(tmp_path, mutation):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    add_candle_retries(ledger, records, count=2 if mutation in (
        "duplicate_attempt", "attempt_gap", "wait_overlaps_next_retry"
    ) else 1)
    retry = next(r for r in records if r["message"].startswith("Transient error;"))
    message = retry["message"]
    substitutions = {
        "other_status": ("status=408", "status=404"),
        "malformed_status": ("status=408", "status=408x"),
        "negative_attempt": ("attempt=0", "attempt=-1"),
        "bool_attempt": ("attempt=0", "attempt=true"),
        "missing_attempt": (", attempt=0", ""),
        "negative_wait": ("wait_ms=10", "wait_ms=-1"),
        "bool_wait": ("wait_ms=10", "wait_ms=true"),
        "zero_wait": ("wait_ms=10", "wait_ms=0"),
        "malformed_endpoint": ("CandleSnapshot { req:", "CandleSnapshot { other:"),
        "unmatched_coin": (f'coin: "{ledger[0]["coin"]}"', 'coin: "unauthorized"'),
        "unmatched_interval": ('interval: "1m"', 'interval: "15m"'),
        "unmatched_start": ('start_time: 1000000', 'start_time: 1000001'),
        "unmatched_end": (f'end_time: {ledger[0]["end"]}', 'end_time: 1'),
        "unexpected_endpoint": (retry_endpoint(ledger[0]), "Meta { dex: None }"),
        "missing_attempt_zero": ("attempt=0", "attempt=1"),
        "attempt_exhausted": ("attempt=0", "attempt=3"),
        "wait_after_completion": ("wait_ms=10", "wait_ms=1000"),
        "wait_overlaps_next_retry": ("wait_ms=10", "wait_ms=101"),
    }
    if mutation in substitutions:
        old, new = substitutions[mutation]
        assert old in message
        retry["message"] = message.replace(old, new)
    elif mutation == "duplicate":
        records.append(dict(retry))
    elif mutation in ("duplicate_attempt", "attempt_gap"):
        second = [r for r in records if r["message"].startswith("Transient error;")][1]
        attempt = 0 if mutation == "duplicate_attempt" else 2
        second["message"] = second["message"].replace("attempt=1", f"attempt={attempt}")
    elif mutation == "before_dispatch":
        retry["timestamp"] = ledger[0]["ts_ns"] - 1
    elif mutation == "after_completion":
        retry["timestamp"] = ledger[0]["ts_ns"] + 2 * NS
    elif mutation == "wrong_component":
        retry["component"] = "nautilus_hyperliquid::data"
    elif mutation == "wrong_level":
        retry["level"] = "DEBUG"
    elif mutation == "after_success_debit":
        records.append(dict(timestamp=ledger[0]["ts_ns"] + 1, level="DEBUG",
                            component="nautilus_hyperliquid::http::client",
                            message="Info debited extra weight: "
                                    f"endpoint={retry_endpoint(ledger[0])}, base_w=20, extra=1"))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "INCOMPLETE"
    assert ("NATIVE_TRANSIENT_RETRY_EVIDENCE_INCOMPLETE" in report["blockers"]
            or "NATIVE_RECORD_MALFORMED_UNMATCHED_OR_DUPLICATE" in report["blockers"]
            or "NATIVE_LOG_FILE_OR_PARSE_AMBIGUITY" in report["blockers"])


@pytest.mark.parametrize("endpoint", ["SpotMeta", "OutcomeMeta", "PerpDexs"])
def test_f1_metadata_retry_charged_but_not_pass(tmp_path, endpoint):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(retry_record(endpoint, NS + 100_000_000, status=503))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "FAIL"
    assert report["blockers"] == ["NATIVE_TRANSIENT_RETRY_ZERO_PREDICATE_FAILED"]
    assert report["native_retry_count"] == 1
    assert report["matched_retries"][0]["cohort"] == "metadata"
    assert report["matched_retries"][0]["request_id"] == endpoint
    assert report["warmup_weight_per_60s"] == 380
    assert report["rest_weight_per_60s"] == 380
    # Metadata's own exact accounting is 100 source-bound base + 20 per retry.
    from scripts.e4_nautilus_public_data_probe import _rolling_weight

    events = [(report["metadata_end_ns"], report["metadata_weight"])] + [
        (r["ts_ns"], r["base_weight"]) for r in report["matched_retries"]
    ]
    assert _rolling_weight(events) == 120


def test_f1_two_all_perp_metadata_requests_require_unique_native_phase(tmp_path):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.extend([
        retry_record("AllPerpMetas", NS + 100_000_000),
        dict(timestamp=NS + 500_000_000, level="DEBUG",
             component="nautilus_hyperliquid::http::client",
             message="Populated asset indices map (count=20)"),
        retry_record("AllPerpMetas", NS + 700_000_000),
    ])
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "FAIL"
    assert report["native_retry_count"] == 2
    assert [r["request_id"] for r in report["matched_retries"]] == [
        "AllPerpMetas:0", "AllPerpMetas:1",
    ]
    records = [r for r in records if not r["message"].startswith("Populated asset indices")]
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "INCOMPLETE"
    assert report["native_retry_count"] == 0


@pytest.mark.parametrize("mutation", [
    "after_bootstrap", "backwards_endpoint", "extra_request", "fallback",
])
def test_f1_metadata_impossible_or_unexpected_retry_is_incomplete(tmp_path, mutation):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(retry_record("SpotMeta", NS + 100_000_000))
    if mutation == "after_bootstrap":
        records[-1]["timestamp"] = 3 * NS
    elif mutation == "backwards_endpoint":
        records.append(retry_record("OutcomeMeta", NS + 50_000_000))
    elif mutation == "extra_request":
        records.append(retry_record("SpotMeta", NS + 200_000_000))
    elif mutation == "fallback":
        records.append(dict(timestamp=NS + 500_000_000, level="WARN",
                            component="nautilus_hyperliquid::http::client",
                            message="Failed to load allPerpMetas, falling back to meta: error"))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "INCOMPLETE"
    assert report["blockers"]


def test_f1_429_retry_and_terminal_rate_limit_failure_remain_fail_closed(tmp_path):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(dict(timestamp=ledger[0]["ts_ns"], level="WARN",
                        component="nautilus_hyperliquid::http::client",
                        message="429 Too Many Requests; backing off: "
                                f"endpoint={retry_endpoint(ledger[0])}, attempt=0, wait_ms=10"))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] == "FAIL"
    assert report["http_429"] == 1
    assert "NATIVE_HTTP_429_RETRY" in report["blockers"]
    records[-1]["message"] = "request failed: rate limit exceeded"
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] != "PASS"


def test_f1_transport_failure_remains_request_failure(tmp_path):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(dict(timestamp=ledger[0]["ts_ns"], level="ERROR",
                        component="nautilus_hyperliquid::http::client",
                        message="transport error: connection failed"))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] != "PASS"
    assert "NATIVE_RETRY_FALLBACK_OR_FAILURE" in report["blockers"]


def data_only_composition(tmp_path, monkeypatch):
    """Real composition/Registry/projection/runtime, offline node and capture facade."""
    from types import ModuleType

    from trader_assist_v0.multi_asset_shadow import production
    from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
    from trader_assist_v0.nautilus_e4.capture import CaptureSession, SubscriptionPolicy
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore

    seed, snapshot, manifest = identity()
    root = tmp_path / "state"
    for name, value in (
        ("THREE_SETUP_STATE_ROOT", root),
        ("THREE_SETUP_EVIDENCE_STORE_PATH", root / "evidence.sqlite"),
        ("THREE_SETUP_REGISTRY_ROOT", root / "registry"),
        ("THREE_SETUP_CLOSED_BAR_STORE_PATH", root / "closed-bars.sqlite"),
    ):
        monkeypatch.setattr(production, name, value)
    store = EvidenceStore(tmp_path / "e4")
    store.initialize(manifest, snapshot)
    registry = MarketRegistryManager(root / "registry", metadata_validator=lambda _: True)
    registry.stage(seed)
    registry.request_apply(seed.version)
    policy = SubscriptionPolicy(discovery=frozenset(e.market_id for e in snapshot.expressions),
                                watch=frozenset(e.market_id for e in snapshot.expressions),
                                actionable=frozenset())
    session = CaptureSession(manifest=manifest, policy=policy, raw_sink=None,
                             evidence_store=store, batch_size=1)
    processed = []
    capture = SimpleNamespace(
        capture_session=session, observer=None,
        warmup_health={"readiness": "READY"},
        capture_health={"stream_health": "HEALTHY", "continuity_requirements_remaining": 0,
                        "storage_failures": 0, "admitted_observer_failures": ()},
        record_l0_processed=lambda event, now: processed.append((event, now)),
    )
    capture.set_admitted_event_observer = lambda observer: setattr(capture, "observer", observer)
    capture.enable_l0_qualification = lambda: None
    node = SimpleNamespace(strategies=[])
    node.add_strategy = node.strategies.append
    host = ModuleType("trader_assist_v0.nautilus_e4.host")
    host.build_public_data_node = lambda **_: node
    host.build_capture_strategy = lambda **_: capture
    monkeypatch.setitem(sys.modules, "trader_assist_v0.nautilus_e4.host", host)
    config = production.ThreeSetupProductionConfig(
        release_sha=manifest.git_sha, evidence_store_path=root / "evidence.sqlite",
        registry_root=root / "registry", closed_bar_store_path=root / "closed-bars.sqlite",
        cost_model=None, data_collection_only=True, e4_evidence_root=store.root,
        e4_manifest_path=store.manifest_path, e4_snapshot_path=store.snapshot_path,
        e4_bar_types=launch_bars(seed, snapshot),
    )
    app = production.compose_three_setup_application(config=config, clock=lambda: NOW)
    assert node.strategies == [capture]
    return app, capture, store, snapshot, processed


def source_fact(expression, kind, index, *, minutes=1, historical=False):
    from trader_assist_v0.nautilus_e4.contracts import DataKind, SourceEvent

    open_ns = (600 + index * 300) * NS
    init_ns = open_ns + minutes * 60 * NS if kind is DataKind.BAR else open_ns + 1
    bar_type = f"{expression.instrument_id}-{minutes}-MINUTE-LAST-EXTERNAL"
    payload = (dict(open="10", high="11", low="9", close="10", volume="2", finalized=True)
               if kind is DataKind.BAR else dict(index=index))
    return SourceEvent.create(
        market_id=expression.market_id, expression_id=expression.expression_id,
        provider_id="NAUTILUS_HYPERLIQUID", instrument_id=expression.instrument_id,
        data_kind=kind, source_event_id=f"{kind}:{index}:{minutes}:{historical}",
        native_trade_id=str(index) if kind is DataKind.TRADE else None,
        provider_aggressor_side="BUYER" if kind is DataKind.TRADE else None,
        event_context=bar_type if kind is DataKind.BAR else f"block-{index}",
        ts_event=open_ns, ts_init=init_ns, true_network_receive_ts=None, payload=payload,
    )


def test_data_only_real_composition_filters_after_full_upstream_admission(tmp_path, monkeypatch):
    from trader_assist_v0.nautilus_e4.capture import CaptureSession
    from trader_assist_v0.nautilus_e4.contracts import DataKind
    from trader_assist_v0.nautilus_e4.storage import EvidenceStore

    app, capture, store, snapshot, processed = data_only_composition(tmp_path, monkeypatch)
    baseline_store = EvidenceStore(tmp_path / "baseline")
    baseline_store.initialize(capture.capture_session.manifest, snapshot)
    baseline = CaptureSession(manifest=capture.capture_session.manifest,
                              policy=capture.capture_session.policy, raw_sink=None,
                              evidence_store=baseline_store, batch_size=1)

    async def exercise():
        runtime = app.e4_runtime
        domain_failures = []
        runtime.on_domain_error = lambda *args: domain_failures.append(args)
        runtime._loop = asyncio.get_running_loop()
        queued = 0

        class CountingLoop:
            def call_soon_threadsafe(self, callback):
                nonlocal queued
                queued += 1
                callback()

        runtime._loop = CountingLoop()
        all_events = []
        # Old all-event demand exceeds 2048; typed non-BAR demand schedules nothing.
        for index in range(2200):
            kind = (DataKind.BBO, DataKind.TRADE, DataKind.DEPTH10, DataKind.CONTEXT)[index % 4]
            expression = snapshot.expressions[(index // 4) % 20]
            source = source_fact(expression, kind, index)
            event = capture.capture_session.ingest(source, admission_ts=source.ts_init).event
            expected = baseline.ingest(source, admission_ts=source.ts_init).event
            assert event == expected
            all_events.append(event)
            capture.observer(event, None)
        assert queued == runtime._queue.qsize() == runtime._queue.overflows == 0
        for index, expression in enumerate(snapshot.expressions):
            for minutes in (1, 5):
                # Historical/live BAR admissions both retain the existing forward path.
                historical = minutes == 1
                source = source_fact(expression, DataKind.BAR, 2200 + index,
                                     minutes=minutes, historical=historical)
                event = capture.capture_session.ingest(
                    source, admission_ts=source.ts_init, historical=historical).event
                assert event == baseline.ingest(
                    source, admission_ts=source.ts_init, historical=historical).event
                capture.observer(event, None)
                all_events.append(event)
        assert queued == 40 and runtime._queue.maxsize == 2048
        shutdown = asyncio.Event()
        consumer = asyncio.create_task(runtime.run(shutdown))
        try:
            await asyncio.wait_for(runtime._queue.join(), timeout=10)
        finally:
            shutdown.set()
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)
        assert len(processed) == 40
        assert domain_failures == []
        assert {event.admission_hash for event, _ in processed} == {
            event.admission_hash for event in all_events if event.source.data_kind is DataKind.BAR
        }
        old_queue = _ObservedQueue(2048)
        for event in all_events[:2048]:
            old_queue.put_nowait(event)
        with pytest.raises(asyncio.QueueFull):
            old_queue.put_nowait(all_events[2048])
        assert old_queue.overflows == 1 and runtime._queue.overflows == 0

    try:
        asyncio.run(exercise())
        assert capture.capture_session.health_summary()["capture_counts"] == (
            baseline.health_summary()["capture_counts"])
        assert store.load_admissions() == baseline_store.load_admissions()
        assert len(store.load_admissions()) == 590  # BAR/CONTEXT retained under existing policy.
        assert capture.capture_health["admitted_observer_failures"] == ()
        assert app.dispatcher is None and not hasattr(app.bootstrap, "coordinator")
        assert all(getattr(app.e4_runtime, name) is None for name in (
            "on_finalized_5m", "on_maintenance_5m", "on_completed_1m", "on_reconnect",
            "on_session_event"))
    finally:
        app.projection.close()
        app.bootstrap.close()


def test_data_only_real_bar_overload_and_bad_input_fail_closed(tmp_path, monkeypatch):
    from trader_assist_v0.nautilus_e4.contracts import DataKind, SourceEvent

    app, capture, _, snapshot, processed = data_only_composition(tmp_path, monkeypatch)
    source = source_fact(snapshot.expressions[0], DataKind.BAR, 1)
    event = capture.capture_session.ingest(source, admission_ts=source.ts_init).event
    failures = []
    app.e4_runtime.on_domain_error = lambda *args: failures.append(args)
    app.e4_runtime._loop = SimpleNamespace(call_soon_threadsafe=lambda callback: callback())
    try:
        for _ in range(2049):
            capture.observer(event, None)
        assert app.e4_runtime._queue.maxsize == 2048
        assert app.e4_runtime._queue.overflows == 1
        assert failures == [(event.source.market_id, event.admission_hash, "QUEUE_FULL")]
        assert app.projection.market_failed(event.source.market_id)
        assert not processed
        with pytest.raises(ThreeSetupProductionError, match="typed"):
            capture.observer(SimpleNamespace(source=SimpleNamespace(data_kind="BAR")), None)
        invalid_kind = event.model_copy(update={
            "source": event.source.model_copy(update={"data_kind": "UNKNOWN"}),
        })
        with pytest.raises(ThreeSetupProductionError, match="typed"):
            capture.observer(invalid_kind, None)
        values = source.model_dump(exclude={"payload_hash"})
        values["payload"] = dict(values["payload"], finalized=False)
        values["source_event_id"] = "invalid-finality"
        bad_source = SourceEvent.create(**values)
        bad_event = capture.capture_session.ingest(bad_source, admission_ts=source.ts_init).event
        with pytest.raises(ValueError, match="finalized"):
            app.projection.accept(bad_event)
        assert not processed
    finally:
        app.projection.close()
        app.bootstrap.close()


def test_native_l0_on_start_registers_all_100_using_installed_rc5(tmp_path):
    import importlib.util
    import platform
    from importlib.metadata import version

    if importlib.util.find_spec("nautilus_trader") is None:
        assert os.environ.get("NAUTILUS_E4_REQUIRED") != "1", "exact rc5 CI cannot skip L0"
        pytest.skip("optional native rc5 absent; authoritative Linux CI required")
    assert version("nautilus-trader") == "2.0.0rc5"
    if os.environ.get("NAUTILUS_E4_REQUIRED") == "1":
        assert sys.version_info[:2] == (3, 12)
        assert sys.platform == "linux" and platform.machine() == "x86_64"
    from trader_assist_v0.nautilus_e4.host import NautilusE4CaptureStrategy

    seed, snapshot, manifest = identity()
    calls = []
    harness = SimpleNamespace(
        _expressions={e.instrument_id: e for e in snapshot.expressions},
        _bar_types=launch_bars(seed, snapshot), _l0=True, _l0_registered=set(),
        _l0_native_registered=[], _registered_bar_streams=set(), _continuity_streams=set(),
        _registered_depth10_streams=set(),
        _policy=SimpleNamespace(watch=set(manifest.subscription_policy["watch"]), actionable=set()),
        _session=SimpleNamespace(await_continuity=lambda **_: None),
        _start_historical_warmup=lambda: None, subscribe_socket_state=lambda: None,
        subscribe_queue_state=lambda: None,
    )
    for method, kind in (("subscribe_bars", "bar"), ("subscribe_quotes", "bbo"),
                         ("subscribe_trades", "trade"), ("subscribe_book_depth10", "depth10")):
        setattr(harness, method, lambda value, *_args, kind=kind: calls.append((kind, str(value))))
    NautilusE4CaptureStrategy.on_start(harness)
    assert len(calls) == len(set(calls)) == 100
    assert {kind: sum(k == kind for k, _ in calls)
            for kind in ("bar", "bbo", "trade", "depth10")} == {
        "bar": 40, "bbo": 20, "trade": 20, "depth10": 20,
    }
    assert {(r["kind"], r["identity"]) for r in harness._l0_native_registered} == set(calls)
    from trader_assist_v0.nautilus_e4.causal import CausalAdmissionLedger
    from trader_assist_v0.nautilus_e4.contracts import DataKind, SourceEvent

    ledger = CausalAdmissionLedger(process_epoch=manifest.process_epoch,
                                  continuity_epoch=manifest.continuity_epoch,
                                  admission_epoch=manifest.admission_epoch)
    observation = QualificationObservation(launch_bars(seed, snapshot))
    observation.request(599 * NS)
    observation.socket("DISCONNECTED", 599 * NS)
    observation.socket("CONNECTED", 600 * NS)
    harness._l0_observation, harness._l0_live_ids = observation, set()
    admissions = []
    for expression in snapshot.expressions:
        for minutes in (1, 5):
            values = source_fact(expression, DataKind.BAR, 0, minutes=minutes).model_dump(
                exclude={"payload_hash"})
            values.update(ts_event=(600 - minutes * 60) * NS, ts_init=600 * NS)
            source = SourceEvent.create(**values)
            event = ledger.admit(source, admission_ts=600 * NS).event
            admissions.append(event)
            NautilusE4CaptureStrategy.record_l0_processed(harness, event, 600 * NS)
    assert not observation.recovered  # Historical-only acknowledgments lack live authority.
    harness._l0_live_ids.update(event.admission_hash for event in admissions)
    for event in admissions:
        NautilusE4CaptureStrategy.record_l0_processed(harness, event, 600 * NS)
    assert observation.recovered == set(observation.bars)
    assert observation.window_start_ns == 600 * NS and not harness._l0_live_ids


@pytest.mark.parametrize("shape", ["completion", "bootstrap", "asset_map", "debit", "retry", "429"])
@pytest.mark.parametrize("mutation", ["wrong_owner", "TRACE", "INFO", "malformed"])
def test_http_authority_binds_exact_source_level_and_grammar(tmp_path, shape, mutation):
    from scripts.e4_nautilus_public_data_probe import DATA_COMPONENT, HTTP_COMPONENT

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    if shape in ("completion", "bootstrap"):
        record = records[2] if shape == "completion" else records[1]
    else:
        messages = {
            "asset_map": "Populated asset indices map (count=20)",
            "debit": f"Info debited extra weight: endpoint={retry_endpoint(ledger[0])}, "
                     "base_w=20, extra=1",
            "retry": f"Transient error; retrying: endpoint={retry_endpoint(ledger[0])}, "
                     "attempt=0, status=408, wait_ms=10",
            "429": f"429 Too Many Requests; backing off: endpoint={retry_endpoint(ledger[0])}, "
                   "attempt=0, wait_ms=10",
        }
        record = dict(timestamp=ledger[0]["ts_ns"], component=HTTP_COMPONENT,
                      level="WARN" if shape in ("retry", "429") else "DEBUG",
                      message=messages[shape])
        records.append(record)
    if mutation == "wrong_owner":
        record["component"] = HTTP_COMPONENT if record["component"] == DATA_COMPONENT else (
            "nautilus_hyperliquid::websocket::handler")
    elif mutation == "malformed":
        record["message"] += " MALFORMED"
    else:
        record["level"] = mutation
    write_retry_fixture(path, records)
    assert parse_fixture(manifest, ledger, path)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("message,level", [
    ("request_bars failed: transport error", "WARN"),
    ("Failed to send bars response: closed channel", "ERROR"),
    ("Failed to convert candle to bar: bad candle", "WARN"),
    ("request_bars failed: transport error", "DEBUG"),
    ("Failed to load allPerpMetas, falling back to meta: error", "WARN"),
    ("Skipping Hyperliquid outcome metadata: error", "DEBUG"),
    ("Failed to load perpDexs, inferring dex names: error", "WARN"),
])
def test_http_failure_call_sites_remain_fail_closed(tmp_path, message, level):
    from scripts.e4_nautilus_public_data_probe import DATA_COMPONENT, HTTP_COMPONENT

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    component = DATA_COMPONENT if message.startswith(("request_bars", "Failed to send bars",
                                                       "Failed to convert")) else HTTP_COMPONENT
    records.append(dict(timestamp=3 * NS, component=component, level=level, message=message))
    write_retry_fixture(path, records)
    report = parse_fixture(manifest, ledger, path)
    assert report["status"] != "PASS"
    assert "NATIVE_HTTP_REQUEST_METADATA_OR_TRANSPORT_FAILURE" in report["blockers"]


def ws_parse_fixture(manifest, ledger, path, *, request=None, epochs=None, synced=True):
    from scripts.e4_nautilus_public_data_probe import parse_native_ws_controls

    native = parse_fixture(manifest, ledger, path, synced=synced)
    return native, parse_native_ws_controls(
        path, native_http=native,
        epochs=epochs or [dict(start_ns=NS, end_ns=200 * NS)],
        outbound_forecast=[(62 * NS, 100)], close_reserve=2,
        planned_reconnect_request_ns=request,
    )


def add_controls(records):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    records.append(dict(timestamp=190 * NS, component=WS_CONTROL_COMPONENT,
                        level="TRACE", message="Received pong"))


@pytest.mark.parametrize("owner,message,ws_pass", [
    ("nautilus_network::websocket::client", "Reconnect attempt 1 failed: transport error", False),
    ("nautilus_hyperliquid::websocket::handler", "WS transport error", False),
    ("nautilus_hyperliquid::data", "WebSocket error: connection failed", False),
    ("nautilus_hyperliquid::http::client",
     "Missing cached Hyperliquid instrument for dex='xyz' raw_symbol='xyz:FOO'", True),
    ("unrelated_native_component", "unrelated native warning", True),
])
def test_http_pass_and_independent_ws_or_safety_failure(tmp_path, owner, message, ws_pass):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(dict(timestamp=185 * NS, component=owner, level="WARN", message=message))
    add_controls(records)
    write_retry_fixture(path, records)
    native, ws = ws_parse_fixture(manifest, ledger, path)
    assert native["status"] == "PASS"
    assert (ws["status"] == "PASS") is ws_pass
    # Non-HTTP warnings are never blanket-approved as an overall zero proof.
    if ws_pass:
        assert any(r["level"] == "WARN" for r in records)


def test_http_failure_does_not_invalidate_file_or_independent_ws(tmp_path):
    from scripts.e4_nautilus_public_data_probe import _apply_ws_proof

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(dict(timestamp=ledger[0]["ts_ns"], level="WARN",
                        component="nautilus_hyperliquid::http::client",
                        message="429 Too Many Requests; backing off: "
                                f"endpoint={retry_endpoint(ledger[0])}, "
                                "attempt=0, wait_ms=10"))
    add_controls(records)
    write_retry_fixture(path, records)
    native, ws = ws_parse_fixture(manifest, ledger, path)
    assert native["status"] == "FAIL" and native["http_429"] == 1
    assert native["log_binding"]["status"] == ws["status"] == "PASS"
    for throttle in (None, 1):
        provider = dict(native_http_evidence=native, http_429=1, transport_failures=1)
        if throttle is not None:
            provider["provider_throttle_events"] = throttle
        _apply_ws_proof(provider, ws)
        assert provider["http_429"] == provider["transport_failures"] == 1
        assert provider.get("provider_throttle_events") == throttle


@pytest.mark.parametrize("mutation", [
    "unsynced", "append", "replace", "rotate", "symlink", "mixed",
])
def test_ws_requires_same_immutable_synced_file_binding(tmp_path, mutation):
    from scripts.e4_nautilus_public_data_probe import parse_native_ws_controls

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    add_controls(records)
    write_retry_fixture(path, records)
    native = parse_fixture(manifest, ledger, path, synced=mutation != "unsynced")
    if mutation == "append":
        path.write_bytes(path.read_bytes() + b'{}\n')
    elif mutation == "replace":
        saved = path.read_bytes()
        path.unlink()
        path.write_bytes(saved)
    elif mutation == "rotate":
        path.with_suffix(".jsonl.1").write_bytes(path.read_bytes())
    elif mutation == "symlink":
        moved = tmp_path / "other.jsonl"
        path.rename(moved)
        path.symlink_to(moved)
    elif mutation == "mixed":
        records[0]["component"] += "other_run"
        write_retry_fixture(path, records)
    ws = parse_native_ws_controls(path, native_http=native,
                                  epochs=[dict(start_ns=NS, end_ns=200 * NS)],
                                  outbound_forecast=[(62 * NS, 100)], close_reserve=2)
    assert ws["status"] == "INCOMPLETE"


@pytest.mark.parametrize("mutation", [None, "unrequested", "wrong_owner", "wrong_level", "attempt2",
                                     "duplicate", "wait_impossible", "outside_gap", "failure"])
def test_planned_ws_backoff_requires_unique_source_request_and_epoch(tmp_path, mutation):
    from scripts.e4_nautilus_public_data_probe import WS_CONTROL_COMPONENT

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    delay = dict(timestamp=100 * NS, component=WS_CONTROL_COMPONENT,
                 level="WARN", message="Backing off for 0.5s...")
    attempt = dict(timestamp=101 * NS, component=WS_CONTROL_COMPONENT,
                   level="DEBUG", message="Reconnection attempt 1 of unlimited")
    records.extend((delay, attempt))
    add_controls(records)
    if mutation == "wrong_owner":
        delay["component"] = "nautilus_network::websocket::other"
    elif mutation == "wrong_level":
        delay["level"] = "DEBUG"
    elif mutation == "attempt2":
        attempt["message"] = "Reconnection attempt 2 of unlimited"
    elif mutation == "duplicate":
        records.append(dict(delay, timestamp=100 * NS + 1))
    elif mutation == "wait_impossible":
        delay["message"] = "Backing off for 9s..."
    elif mutation == "outside_gap":
        delay["timestamp"] = 90 * NS
    elif mutation == "failure":
        records.append(dict(attempt, timestamp=102 * NS, level="WARN",
                            message="Reconnect attempt 1 failed: transport error"))
    write_retry_fixture(path, records)
    native, ws = ws_parse_fixture(manifest, ledger, path,
                                 request=None if mutation == "unrequested" else 98 * NS,
                                 epochs=[dict(start_ns=NS, end_ns=99 * NS),
                                         dict(start_ns=103 * NS, end_ns=200 * NS)])
    assert native["status"] == "PASS"
    assert (ws["status"] == "PASS") is (mutation is None)


def test_ws_rechecks_ctime_even_with_identical_inode_mtime_size_and_bytes(tmp_path, monkeypatch):
    from scripts.e4_nautilus_public_data_probe import parse_native_ws_controls

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    add_controls(records)
    write_retry_fixture(path, records)
    native, original_ws = ws_parse_fixture(manifest, ledger, path)
    assert native["status"] == original_ws["status"] == "PASS"
    before = path.lstat()
    assert native["log_binding"]["file_state"] == [
        before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns,
    ]
    # Model Linux inode reuse with restored mtime and identical content: ctime
    # is the only changed witness. Keep the existing real replacement test intact.
    reused = SimpleNamespace(st_mode=before.st_mode, st_dev=before.st_dev,
                             st_ino=before.st_ino, st_size=before.st_size,
                             st_mtime_ns=before.st_mtime_ns, st_ctime_ns=before.st_ctime_ns + 1)
    lstat = Path.lstat
    monkeypatch.setattr(Path, "lstat", lambda target, *a, **kw:
                        reused if target == path else lstat(target, *a, **kw))
    monkeypatch.setattr(os, "fstat", lambda _fd: reused)
    ws = parse_native_ws_controls(path, native_http=native,
                                  epochs=[dict(start_ns=NS, end_ns=200 * NS)],
                                  outbound_forecast=[(62 * NS, 100)], close_reserve=2)
    assert ws["status"] == "INCOMPLETE"
    assert ws["blockers"] == ["WS_CONTROL_FILE_EPOCH_OR_FORECAST_INCOMPLETE"]


def resource_sample(ts_ns, **changes):
    return dict(ts_ns=ts_ns, memory_used_percent=20, cpu_percent=5, swap_activity=0,
                root_used_percent=20, root_7d_projection_percent=25) | changes


@pytest.mark.parametrize("wake_delay", [0, 0.1, 1.5])
def test_resource_absolute_slots_allow_measured_terminal_sample(wake_delay):
    from scripts.e4_nautilus_public_data_probe import _ResourceSchedule

    schedule = _ResourceSchedule(1200)
    samples = []
    now = 2.5  # First sample is genuinely later than window start.
    while now < schedule.deadline:
        if schedule.due(now):
            samples.append(resource_sample(int((1000 + now) * NS)))
            schedule.attempted(now, accepted=True)
        if schedule.complete(samples):
            break
        now = schedule.next_sample + wake_delay
    assert 16 <= len(samples) <= 33
    assert samples[-1]["ts_ns"] - samples[0]["ts_ns"] >= 900 * NS
    assert max(b["ts_ns"] - a["ts_ns"] for a, b in pairwise(samples)) <= 60 * NS
    assert schedule.anchor == 2.5 and schedule.deadline == 932.5


def complete_observation(manifest):
    observation = QualificationObservation(tuple(manifest.capture_configuration["bar_types"]))
    observation.request(599 * NS)
    observation.socket("DISCONNECTED", 599 * NS)
    observation.socket("CONNECTED", 600 * NS)
    for bar in observation.bars:
        minutes = 1 if "-1-MINUTE-" in bar else 5
        observation.processed(bar, (600 - minutes * 60) * NS, 600 * NS, "a" * 64)
    assert observation.window_start_ns == 600 * NS
    for bar in observation.bars:
        minutes = 1 if "-1-MINUTE-" in bar else 5
        for offset in range(0, 900, minutes * 60):
            observation.processed(bar, (600 + offset) * NS,
                                  (600 + offset + minutes * 60) * NS, "b" * 64)
    return observation


def passing_report_inputs(tmp_path):
    from scripts.e4_nautilus_public_data_probe import RC5_SOURCE, ZERO_COUNTERS

    manifest, ledger, records, path = native_log_fixture(tmp_path)
    add_controls(records)
    write_retry_fixture(path, records)
    native, ws = ws_parse_fixture(manifest, ledger, path)
    provider = dict(native, **{key: 0 for key in ZERO_COUNTERS})
    provider.update(native_http_evidence=native, native_ws_control_evidence=ws,
                    ws_connections=1, ws_new_connections_per_60s=2,
                    ws_active_plus_pending_subscriptions=100, ws_outbound_messages_per_60s=104)
    resources = [resource_sample((600 + i * 30) * NS) for i in range(31)]
    queues = dict(native_capacity="NOT_APPLICABLE_UNBOUNDED", monitor_observed=True,
                  monotonic_backlog_3_cohorts=False,
                  finite=[dict(capacity=2048, max_depth=40, end_depth=0)])
    forecast = dict(bars=40, bbo=20, trade=20, depth10=20, native_subscriptions=100,
                    rc5_source=RC5_SOURCE)
    return manifest, complete_observation(manifest), provider, resources, queues, forecast


def test_all_40_recovery_and_15m_counts_have_complete_positive_proof(tmp_path):
    manifest, observation, provider, resources, queues, forecast = passing_report_inputs(tmp_path)
    report = evaluate_qualification(manifest, observation, 1500 * NS,
                                    provider, resources, queues, forecast)
    assert report["status"] == "PASS" and report["blockers"] == []
    assert len(report["streams"]) == 40
    assert sorted(s["count"] for s in report["streams"].values()) == [3] * 20 + [15] * 20
    before = {bar: dict(values) for bar, values in observation.live.items()}
    for bar in observation.bars:
        observation.processed(bar, 1500 * NS, 1800 * NS, "c" * 64)
    assert observation.live == before  # Resource tail never widens BAR membership.
    assert "OBSERVATION_15M_INCOMPLETE" in observation.evaluate(1500 * NS - 1)[0]


@pytest.mark.parametrize("mutation", ["missing", "gap", "duplicate", "conflict", "future", "stale",
                                     "p95", "extra", "extra_reconnect", "slow_recovery"])
@pytest.mark.parametrize("minutes", [1, 5])
def test_full_bar_qualification_remains_fail_closed(tmp_path, mutation, minutes):
    manifest, observation, provider, resources, queues, forecast = passing_report_inputs(tmp_path)
    bar = observation.bars[0 if minutes == 1 else 1]
    if mutation == "missing":
        observation.live[bar].pop(min(observation.live[bar]))
    elif mutation == "gap":
        values = observation.live[bar]
        values[max(values) + minutes * 60 * NS] = values.pop(sorted(values)[len(values) // 2])
    elif mutation in ("duplicate", "conflict"):
        observation.processed(bar, 600 * NS, (600 + minutes * 60) * NS,
                              "b" * 64 if mutation == "duplicate" else "c" * 64)
    elif mutation == "future":
        observation.processed(bar, (1500 - minutes * 60) * NS, 1499 * NS, "c" * 64)
    elif mutation == "stale":
        observation.live[bar][600 * NS] = (61 * NS, "b" * 64)
    elif mutation == "p95":
        observation.live[bar] = {open_ns: (31 * NS, value[1])
                                 for open_ns, value in observation.live[bar].items()}
    elif mutation == "extra":
        observation.processed(bar, 630 * NS, (630 + minutes * 60) * NS, "c" * 64)
    elif mutation == "extra_reconnect":
        observation.request(1000 * NS)
    else:
        late = QualificationObservation(observation.bars)
        late.request(530 * NS)
        late.socket("DISCONNECTED", 531 * NS)
        late.socket("CONNECTED", 600 * NS)
        for stream in late.bars:
            minutes = 1 if "-1-MINUTE-" in stream else 5
            late.processed(stream, (600 - minutes * 60) * NS, 600 * NS, "a" * 64)
        assert "RECOVERY_OVER_60S" in late.failures
        observation = late
    assert evaluate_qualification(manifest, observation, 1500 * NS,
                                  provider, resources, queues, forecast)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("mutation", ["count", "span", "gap", "memory", "cpu_peak", "cpu_mean",
                                     "swap", "disk", "projection", "missing_field",
                                     "queue_peak", "queue_end", "queue_unknown", "drop", "storage",
                                     "throttle", "registration"])
def test_resource_provider_and_queue_ceilings_are_unchanged(tmp_path, mutation):
    manifest, observation, provider, resources, queues, forecast = passing_report_inputs(tmp_path)
    if mutation == "count":
        resources = resources[:15]
    elif mutation == "span":
        resources = resources[:-1]
    elif mutation == "gap":
        resources[1]["ts_ns"] = resources[0]["ts_ns"] + 61 * NS
    elif mutation in ("memory", "cpu_peak", "disk", "projection", "swap"):
        key, value = {"memory": ("memory_used_percent", 81), "cpu_peak": ("cpu_percent", 81),
                      "disk": ("root_used_percent", 71),
                      "projection": ("root_7d_projection_percent", 71),
                      "swap": ("swap_activity", 1)}[mutation]
        resources[-1][key] = value
    elif mutation == "cpu_mean":
        for resource in resources:
            resource["cpu_percent"] = 21
    elif mutation == "missing_field":
        resources[-1].pop("cpu_percent")
    elif mutation == "queue_peak":
        queues["finite"][0]["max_depth"] = 1640
    elif mutation == "queue_end":
        queues["finite"][0]["end_depth"] = 410
    elif mutation == "queue_unknown":
        queues["monotonic_backlog_3_cohorts"] = None
    elif mutation == "registration":
        forecast["native_subscriptions"] = 99
    else:
        provider[{"drop": "dropped_events", "storage": "storage_failures",
                  "throttle": "provider_throttle_events"}[mutation]] = 1
    assert evaluate_qualification(manifest, observation, 1500 * NS,
                                  provider, resources, queues, forecast)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("scenario", [
    "drift", "delayed_first", "terminal_failure", "short_deadline",
    "missed_slot", "early_exit", "non_http_warning", "observer_failure", "fanout_failure",
    "storage_failure",
    "registration_missing", "registration_duplicate", "registration_substituted",
    "queue_rising", "queue_monitor_missing", "queue_cohorts_missing",
])
def test_actual_qualification_loop_measures_bounded_resource_tail(tmp_path, monkeypatch, scenario):
    from types import ModuleType

    from scripts import e4_nautilus_public_data_probe as probe
    from trader_assist_v0.multi_asset_shadow import production

    app, capture, _, snapshot, _ = data_only_composition(tmp_path, monkeypatch)
    manifest, ledger, records, log_path = native_log_fixture(tmp_path)
    assert manifest == capture.capture_session.manifest
    capture.qualification_observation = complete_observation(manifest)
    observation = capture.qualification_observation
    health = dict(
        history_requests=ledger, registered_bars=list(observation.bars), queue_events=100,
        native_registered=[dict(kind="bar", identity=bar) for bar in observation.bars] + [
            dict(kind=kind, identity=e.instrument_id)
            for e in snapshot.expressions for kind in ("bbo", "trade", "depth10")],
        socket_events=[dict(client_id="HYPERLIQUID", endpoint="hyperliquid-data-streams",
                            state=state, ts_ns=ts) for state, ts in (
                                ("DISCONNECTED", 599 * NS), ("CONNECTED", 600 * NS))],
        live_processing_buffer=dict(capacity=100, max_depth=0, end_depth=0),
        queue_states={"data": dict(depth=0)},
    )
    capture.l0_health = health
    if scenario == "queue_monitor_missing":
        health["queue_events"] = 0
    elif scenario == "queue_cohorts_missing":
        health["queue_states"] = {}
    if scenario == "registration_missing":
        health["native_registered"].pop()
    elif scenario == "registration_duplicate":
        health["native_registered"][-1] = dict(health["native_registered"][-2])
    elif scenario == "registration_substituted":
        health["native_registered"][-1]["identity"] = "UNEXPECTED.HYPERLIQUID"
    capture.capture_health["markettruth_fanout"] = dict(publish_error_count=0)
    if scenario == "observer_failure":
        capture.capture_health["admitted_observer_failures"] = ({"error_type": "RuntimeError"},)
    elif scenario == "fanout_failure":
        capture.capture_health["markettruth_fanout"]["publish_error_count"] = 1
    elif scenario == "storage_failure":
        capture.capture_health["storage_failures"] = 1
    finished = []
    capture.finish_l0_qualification = lambda: finished.append(True)
    capture.request_l0_reconnect = lambda: pytest.fail("must preserve the existing one request")
    records.append(dict(timestamp=1520 * NS, component=probe.WS_CONTROL_COMPONENT,
                        level="TRACE", message="Received pong"))
    if scenario == "non_http_warning":
        records.append(dict(timestamp=1510 * NS, component=probe.HTTP_COMPONENT, level="WARN",
                            message="Missing cached Hyperliquid instrument for dex='xyz' "
                                    "raw_symbol='xyz:FOO'"))
    write_retry_fixture(log_path, records)
    config = SimpleNamespace(data_collection_only=True)
    monkeypatch.setattr(production, "load_three_setup_config", lambda _: config)
    monkeypatch.setattr(production, "compose_three_setup_application", lambda **_: app)
    common = ModuleType("nautilus_trader.common")
    common.logging_sync_to_disk = lambda: True
    monkeypatch.setitem(sys.modules, "nautilus_trader.common", common)

    class Clock:
        now = 0.0

        def monotonic(self):
            return self.now

        def time_ns(self):
            return int((600 + self.now) * NS)

    clock = Clock()
    if scenario == "delayed_first":
        clock.now = 2.5
    monkeypatch.setattr(probe, "time", clock)
    measured = []

    def collect(_self, _root):
        if scenario == "terminal_failure" and clock.now >= 900:
            raise OSError("terminal /proc read failed")
        clock.now += 0.2  # Actual field-read work, not a backdated timestamp.
        sample = resource_sample(clock.time_ns())
        if scenario == "queue_rising":
            health["queue_states"] = {"data": dict(depth=len(measured))}
        measured.append(dict(sample))
        return sample

    monkeypatch.setattr(probe._ResourceSampler, "collect", collect)
    early_exit = asyncio.Event()

    async def run(shutdown):
        if scenario == "early_exit":
            await early_exit.wait()
        else:
            await shutdown.wait()

    app.run = run

    async def sleep(_seconds):
        clock.now += 0.1
        if scenario == "missed_slot" and 89 < clock.now < 90:
            clock.now += 90  # No fabricated catch-up cohort after a stall.
        if scenario == "early_exit" and clock.now > 400:
            early_exit.set()
        await asyncio.sleep(0)

    monkeypatch.setattr(probe, "asyncio", SimpleNamespace(
        Event=asyncio.Event, create_task=asyncio.create_task, sleep=sleep))
    args = SimpleNamespace(config_path=tmp_path / "config.json", evidence_path=tmp_path,
                           ci_instrument_id=None, actionable_market_id=[],
                           run_seconds=900 if scenario == "short_deadline" else 1200)
    try:
        exit_code, report = asyncio.run(probe._run_l0_qualification(args))
        assert report["resources"] == measured
        assert len(measured) <= 33 and clock.now <= 933
        assert finished == [True]
        assert all(stream["count"] in (15, 3) for stream in report["streams"].values())
        if scenario in ("drift", "delayed_first"):
            assert exit_code == probe.PASS and report["status"] == "PASS"
            assert len(measured) >= 16
            assert measured[-1]["ts_ns"] - measured[0]["ts_ns"] >= 900 * NS
            assert measured[-1]["ts_ns"] > observation.window_start_ns + 900 * NS
            assert report["provider"]["dropped_events"] == 0
        else:
            assert exit_code == probe.PROVIDER_DATA_INCOMPLETE
            assert report["status"] == "INCOMPLETE"
            if scenario == "terminal_failure":
                assert "TARGET_RESOURCE_SAMPLE_INCOMPLETE" in report["blockers"]
            if scenario == "non_http_warning":
                assert report["provider"]["native_http_evidence"]["status"] == "PASS"
                assert "NATIVE_NON_HTTP_SAFETY_FAILURE_OR_AMBIGUITY" in report["blockers"]
            if scenario in ("observer_failure", "fanout_failure"):
                assert report["provider"]["dropped_events"] == 1
            if scenario == "storage_failure":
                assert report["provider"]["storage_failures"] == 1
            if scenario.startswith("registration_"):
                assert "NATIVE_REGISTRATION_PROOF_INCOMPLETE" in report["blockers"]
            if scenario.startswith("queue_"):
                assert "NATIVE_QUEUE_PROOF_INCOMPLETE" in report["blockers"]
    finally:
        app.projection.close()
        app.bootstrap.close()


def test_resource_collector_timestamps_only_successful_complete_reads(tmp_path, monkeypatch):
    from scripts import e4_nautilus_public_data_probe as probe

    original = Path.read_text
    fake_files = {
        "/proc/meminfo": "MemTotal: 1000 kB\nMemAvailable: 800 kB\n",
        "/proc/stat": "cpu 100 0 0 900 0 0 0 0\n",
        "/proc/vmstat": "pswpin 0\npswpout 0\n",
    }
    clock_reads = []
    monkeypatch.setattr(Path, "read_text", lambda path, *a, **kw: fake_files.get(str(path))
                        if str(path) in fake_files else original(path, *a, **kw))
    monkeypatch.setattr(probe.os, "statvfs", lambda _: SimpleNamespace(
        f_blocks=1000, f_frsize=1000, f_bfree=800))
    monkeypatch.setattr(probe, "time", SimpleNamespace(
        time_ns=lambda: clock_reads.append(True) or len(clock_reads) * 30 * NS))
    sampler = probe._ResourceSampler()
    assert sampler.collect(tmp_path)["ts_ns"] == 30 * NS
    fake_files["/proc/stat"] = "cpu 110 0 0 990 0 0 0 0\n"
    second = sampler.collect(tmp_path)
    assert second["ts_ns"] == 60 * NS and second["cpu_percent"] == pytest.approx(10)
    baseline = sampler.previous_cpu
    fake_files["/proc/meminfo"] = "MemTotal: invalid kB\n"
    with pytest.raises(ValueError):
        sampler.collect(tmp_path)
    assert len(clock_reads) == 2 and sampler.previous_cpu == baseline


@pytest.mark.parametrize("span_ns,passes", [(900 * NS, True), (900 * NS - 1, False)])
def test_exact_measured_resource_span_boundary(tmp_path, span_ns, passes):
    manifest, observation, provider, _, queues, forecast = passing_report_inputs(tmp_path)
    resources = [resource_sample(600 * NS + i * 60 * NS) for i in range(16)]
    resources[-1]["ts_ns"] = resources[0]["ts_ns"] + span_ns
    assert (evaluate_qualification(manifest, observation, 1500 * NS, provider, resources,
                                   queues, forecast)["status"] == "PASS") is passes


@pytest.mark.parametrize("domain,key", [("native_http_evidence", "log_binding"),
                                        ("native_ws_control_evidence", "file_identity"),
                                        ("native_ws_control_evidence", "path"),
                                        ("native_ws_control_evidence", "begin_marker")])
def test_overall_qualification_requires_shared_binding_not_status_alone(tmp_path, domain, key):
    manifest, observation, provider, resources, queues, forecast = passing_report_inputs(tmp_path)
    provider[domain][key] = None
    assert evaluate_qualification(manifest, observation, 1500 * NS, provider, resources,
                                  queues, forecast)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("message", [
    "transport error: connection failed", "request failed: closed",
])
def test_http_failure_cannot_be_hidden_by_trace_level(tmp_path, message):
    manifest, ledger, records, path = native_log_fixture(tmp_path)
    records.append(dict(timestamp=3 * NS, level="TRACE",
                        component="nautilus_hyperliquid::http::client", message=message))
    write_retry_fixture(path, records)
    assert parse_fixture(manifest, ledger, path)["status"] == "INCOMPLETE"


def test_ws_unknown_proof_cannot_preserve_shared_zero():
    from scripts.e4_nautilus_public_data_probe import _apply_ws_proof

    provider = dict(native_http_evidence={"status": "PASS"}, provider_throttle_events=0,
                    transport_failures=1)
    _apply_ws_proof(provider, {"status": "INCOMPLETE"})
    assert "provider_throttle_events" not in provider and provider["transport_failures"] == 1
