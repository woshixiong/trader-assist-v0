"""Frozen L0 identity, pacing and fail-closed qualification predicates."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import UTC, datetime
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
                                     "malformed", "retry", "unsynced", "unterminated"])
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
    elif mutation == "retry":
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
