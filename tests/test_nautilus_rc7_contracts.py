import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from trader_assist_v0.nautilus_e4.contracts import GuardInputs
from trader_assist_v0.nautilus_e4.native_execution import SubmitCertificate, final_submit_reasons
from trader_assist_v0.nautilus_e4.native_health import NativeHealth
from trader_assist_v0.nautilus_e4.shadow_ledger import ShadowLedger


def verified_cycle() -> dict[str, object]:
    return {
        "status": "PASS",
        "instance_id": "current",
        "bounded_duration_complete": True,
        "public_coverage": "PASS",
        "missing_streams": [],
        "event_failures": [],
        "freshness_reasons": [],
        "types": {"QuoteTick": {"count": 3}},
        "stream_counts": {"ETH:quote": 3},
    }


@pytest.mark.parametrize(
    "change",
    [
        {"status": "FAIL"},
        {"instance_id": "previous"},
        {"bounded_duration_complete": False},
        {"public_coverage": "INCOMPLETE"},
        {"missing_streams": ["ETH:5m"]},
        {"event_failures": ["OUT_OF_ORDER_OR_GAP"]},
        {"freshness_reasons": ["STALE:ETH:quote"]},
        {"types": {}},
        {"stream_counts": {}},
    ],
)
def test_service_cycle_cannot_admit_failed_or_old_proof(change: dict[str, object]) -> None:
    from scripts.rc7.run_public import require_verified_cycle

    require_verified_cycle(verified_cycle(), "current")
    with pytest.raises(RuntimeError, match="FAIL_CLOSED"):
        require_verified_cycle({**verified_cycle(), **change}, "current")
    with pytest.raises(RuntimeError, match="FAIL_CLOSED"):
        require_verified_cycle({}, "current")


def test_capture_gap_is_measured_without_claiming_exchange_loss() -> None:
    from scripts.rc7.run_public import capture_gap

    assert capture_gap(100, 350) == {
        "state": "CAPTURE_GAP",
        "measurement": "CALLBACK_INTERVAL",
        "previous_last_observed_ns": 100,
        "first_observed_ns": 350,
        "interval_ns": 250,
    }
    assert capture_gap(None, 350)["measurement"] == "UNKNOWN"
    assert capture_gap(100, None)["interval_ns"] is None
    with pytest.raises(ValueError, match="CLOCK_INVALID"):
        capture_gap(350, 100)


def test_public_process_exits_nonzero_on_capacity_despite_prior_success(tmp_path: Path) -> None:
    import json
    import os
    import subprocess
    import sys

    prior = tmp_path / "close-proof.json"
    prior.write_text(json.dumps(verified_cycle()))
    original = prior.read_bytes()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.rc7.run_public",
            "--provider-coins",
            "ETH",
            "xyz:SKHX",
            "--root",
            str(tmp_path),
            "--max-archive-bytes",
            "1",
        ],
        env={**os.environ, "PYTHONPATH": "src:."},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0
    assert "ARCHIVE_BUDGET_EXHAUSTED_SOURCES_RETAINED" in result.stderr
    assert "VERIFIED_SUCCESS" not in result.stdout
    assert prior.read_bytes() == original


def test_public_unit_only_cycles_on_verified_zero_exit() -> None:
    import configparser
    import shlex

    unit = configparser.ConfigParser(interpolation=None, strict=False)
    unit.read("deploy/systemd/tradeos-rc7-public.service")
    service = unit["Service"]
    assert service["Type"] == "simple"
    assert service["Restart"] == "on-success"
    assert set(service["RestartPreventExitStatus"].split()) == {
        "SIGHUP",
        "SIGINT",
        "SIGTERM",
        "SIGPIPE",
    }
    assert "SuccessExitStatus" not in service and "RestartForceExitStatus" not in service
    assert int(service["RestartSec"]) >= 15
    assert int(unit["Unit"]["StartLimitBurst"]) <= 3
    assert unit["Unit"]["ConditionPathExists"] == "/etc/tradeos/rc7-public-authorized"
    assert service["User"] == service["Group"] == "tradeos"
    command = shlex.split(service["ExecStart"])
    assert command[1:3] == ["-m", "scripts.rc7.run_public"]
    assert not {"--sandbox", "--sandbox-probe", "--strategy-manifest"} & set(command)


def test_native_systemd_255_verifies_unit_and_rejects_oneshot_restart(tmp_path: Path) -> None:
    import getpass
    import platform
    import shutil
    import subprocess
    import sys

    if platform.system() != "Linux":
        pytest.skip("native systemd validation runs on isolated Ubuntu CI")
    binary = shutil.which("systemd-analyze")
    assert binary is not None, "Linux CI requires native systemd-analyze"
    version = subprocess.check_output([binary, "--version"], text=True)
    assert version.splitlines()[0].startswith("systemd 255 "), version.splitlines()[0]
    source = Path("deploy/systemd/tradeos-rc7-public.service").read_text()
    # Substitute only unavailable target-host paths/account for parse-only CI.
    # No unit is installed, started or sent to a service manager.
    for key, value in {
        "ExecStart": f"{sys.executable} -c pass",
        "WorkingDirectory": str(tmp_path),
        "ReadWritePaths": str(tmp_path),
        "User": getpass.getuser(),
        "Group": getpass.getuser(),
    }.items():
        source = (
            "\n".join(
                f"{key}={value}" if line.startswith(key + "=") else line
                for line in source.splitlines()
            )
            + "\n"
        )
    path = tmp_path / "tradeos-rc7-public.service"
    path.write_text(source)
    result = subprocess.run(
        [binary, "verify", "--man=no", str(path)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    path.write_text(source.replace("Type=simple", "Type=oneshot"))
    invalid = subprocess.run(
        [binary, "verify", "--man=no", str(path)], capture_output=True, text=True
    )
    assert invalid.returncode != 0
    assert "on-success" in invalid.stderr and "oneshot" in invalid.stderr


def test_archive_admission_retains_evidence_and_never_certifies_staging(tmp_path: Path) -> None:
    from scripts.rc7.qualify_health import validate_report
    from trader_assist_v0.nautilus_e4.native_archive import (
        observe_archive,
        require_archive_capacity,
    )

    stage = tmp_path / "live" / "run"
    stage.mkdir(parents=True)
    source = stage / "quote.feather.partial"
    source.write_bytes(b"native-source-placeholder")
    observed = observe_archive(tmp_path, stage)
    assert observed.total_bytes == observed.stage_bytes == source.stat().st_size
    assert observed.evidence(now_ns=source.stat().st_mtime_ns)["writer"] == (
        "STAGING_ACTIVITY_OBSERVED"
    )
    assert observed.evidence(now_ns=source.stat().st_mtime_ns + 16_000_000_000)["writer"] == (
        "UNKNOWN_OR_QUIET"
    )
    require_archive_capacity(observed, max_bytes=100, free_bytes=100, minimum_free_bytes=10)
    for budget, free, error in ((observed.total_bytes, 100, "BUDGET"), (100, 1, "DISK_LOW")):
        with pytest.raises(RuntimeError, match=error):
            require_archive_capacity(
                observed, max_bytes=budget, free_bytes=free, minimum_free_bytes=10
            )
    assert source.read_bytes() == b"native-source-placeholder"
    health = NativeHealth({"ETH:quote": 100})
    health.socket(True)
    health.observe("ETH:quote", ts_event=100, ts_init=100, now=100)
    report = health.report(now=100, generated=100, free_bytes=10**12)
    report["archive"] = observed.evidence(now_ns=source.stat().st_mtime_ns)
    with pytest.raises(ValueError, match="DEGRADED"):
        validate_report(report, 100)
    (tmp_path / "external-link").symlink_to(stage, target_is_directory=True)
    with pytest.raises(RuntimeError, match="SYMLINK"):
        observe_archive(tmp_path, stage)


def inputs() -> GuardInputs:
    return GuardInputs(
        data_evaluable=True,
        bbo_state_valid=True,
        intended_notional="10",
        top_level_notional="100",
        remaining_room_bps="100",
        all_in_friction_bps="10",
        minimum_room_to_cost="2",
        spread_bps="1",
        guard_config_version="v1",
    )


def test_health_requires_native_events_fresh_report_writer_catalog_and_disk() -> None:
    health = NativeHealth({"ETH:quote": 100, "ETH:1m": 1000}, minimum_free_bytes=100)
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"
    health.socket(True)
    health.writer_ok = health.catalog_verified = True
    for stream in health.required:
        assert health.observe(stream, ts_event=990, ts_init=995, now=1000)
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "HEALTHY"
    assert health.report(now=1200, generated=1200, free_bytes=1000)["status"] == "DEGRADED"
    assert health.report(now=1000, generated=1000, free_bytes=1)["status"] == "DEGRADED"
    assert (
        health.report(now=20_000_000_000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"
    )
    health.socket(False)
    health.socket(True)  # ACK alone never restores fresh events in a new continuity epoch.
    assert health.report(now=1000, generated=1000, free_bytes=1000)["status"] == "DEGRADED"


def test_unknown_future_out_of_order_events_cannot_make_healthy() -> None:
    health = NativeHealth({"ETH:quote": 100}, max_future_skew_ns=1)
    assert not health.observe("OTHER:quote", ts_event=10, ts_init=10, now=10)
    assert not health.observe("ETH:quote", ts_event=20, ts_init=20, now=10)
    assert health.observe("ETH:quote", ts_event=10, ts_init=10, now=10)
    assert not health.observe("ETH:quote", ts_event=9, ts_init=11, now=11)
    assert health.out_of_order == 1
    assert "OUT_OF_ORDER_OR_GAP" in health.failures


def test_closed_bar_freshness_uses_close_without_changing_source_open_time() -> None:
    second = 1_000_000_000
    health = NativeHealth({"ETH:5m": 360 * second})
    health.socket(True)
    health.writer_ok = health.catalog_verified = True
    assert health.observe(
        "ETH:5m",
        ts_event=300 * second,
        event_end_ns=600 * second,
        ts_init=600 * second,
        now=900 * second,
    )
    assert health.last["ETH:5m"][0] == 300 * second
    assert (
        health.report(now=900 * second, generated=900 * second, free_bytes=10**12)["status"]
        == "HEALTHY"
    )
    assert (
        health.report(now=1000 * second, generated=1000 * second, free_bytes=10**12)["status"]
        == "DEGRADED"
    )
    assert not health.observe(
        "ETH:5m",
        ts_event=600 * second,
        event_end_ns=900 * second,
        ts_init=899 * second,
        now=900 * second,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"instrument_id": "OTHER"},
        {"epoch": 2},
        {"valid_until_ns": 99},
        {"signal_valid_until_ns": 99},
        {"generated_ns": 101},
        {"account_reconciled": False},
        {"price_known": False},
        {"native_connected": False},
        {"feed_health": "GAPPED"},
        {"feed_health": "UNKNOWN"},
        {"feed_health": "STALE"},
    ],
)
def test_final_submit_rechecks_each_safety_failure(change: dict[str, object]) -> None:
    good = SubmitCertificate("ETH", 1, 200, 200, True, True, True, "HEALTHY", 90)
    assert not final_submit_reasons(
        certificate=good, instrument_id="ETH", epoch=1, now_ns=100, inputs=inputs()
    )
    assert final_submit_reasons(
        certificate=replace(good, **change),
        instrument_id="ETH",
        epoch=1,
        now_ns=100,
        inputs=inputs(),
    )


def test_unknown_certificate_and_existing_economic_guard_fail_closed() -> None:
    assert final_submit_reasons(
        certificate=None, instrument_id="ETH", epoch=1, now_ns=100, inputs=inputs()
    )
    bad = inputs().model_copy(update={"data_evaluable": False})
    good = SubmitCertificate("ETH", 1, 200, 200, True, True, True, "HEALTHY", 90)
    assert "DATA_NOT_EVALUABLE" in final_submit_reasons(
        certificate=good, instrument_id="ETH", epoch=1, now_ns=100, inputs=bad
    )


def test_decisions_no_fill_reject_and_partial_fill_survive_restart(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    ledger = ShadowLedger(path, strategy_id="approved-strategy", strategy_version="v1")
    for i, outcome in enumerate(("REJECT", "WAIT", "PASS", "UNFILLED", "LOST", "SUBMIT")):
        ledger.decision(
            decision_id=str(i),
            ts_ns=100,
            source_identity=f"quote:{i}",
            source_ts_ns=90,
            outcome=outcome,
            details={},
        )
    for i, qty in enumerate(("0.1", "0.2")):
        ledger.append(
            event_id=f"fill:{i}",
            kind="OrderFilled",
            ts_ns=110 + i,
            payload={
                "native_order_id": "order-1",
                "last_qty": qty,
                "commission": "0.01 USDC",
                "liquidity_side": "TAKER",
            },
        )
    assert ledger.verify() == 8
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        ledger.db.execute("DELETE FROM events")
    ledger.close()
    reopened = ShadowLedger(path, strategy_id="approved-strategy", strategy_version="v1")
    assert reopened.verify() == 8
    assert reopened.db.execute("SELECT count(*) FROM events WHERE kind='DECISION'").fetchone() == (
        6,
    )
    with pytest.raises(ValueError, match="conflicting"):
        reopened.append(event_id="fill:0", kind="OrderFilled", ts_ns=120, payload={})
    reopened.close()


def test_approved_strategy_retains_cold_start_no_signal_denominator(tmp_path: Path) -> None:
    from decimal import Decimal

    from test_nautilus_pilot_contracts import _closed_bar, _manifest

    from trader_assist_v0.nautilus_e4.registered_shadow import RegisteredShadowEvaluator

    manifest = _manifest()
    ledger = ShadowLedger(
        tmp_path / "strategy.sqlite",
        strategy_id=manifest.package_version,
        strategy_version=manifest.strategy_version,
    )
    evaluator = RegisteredShadowEvaluator(
        manifest=manifest,
        market_id=_closed_bar(0).market_id,
        minimum_tick=Decimal("0.1"),
        ledger=ledger,
    )
    for i in range(3):
        bar = _closed_bar(i)
        assert evaluator.evaluate(bar, now_ns=bar.close_time_ms * 1_000_000) is None
    assert ledger.verify() == 3
    evaluator.evaluate(_closed_bar(2), now_ns=_closed_bar(2).close_time_ms * 1_000_000)
    assert ledger.verify() == 3  # replay does not inflate the strategy decision denominator
    with pytest.raises(ValueError, match="lookahead"):
        evaluator.evaluate(_closed_bar(3), now_ns=1)
    ledger.close()


def test_native_universe_uses_provider_identity_without_inventing_symbols() -> None:
    from types import SimpleNamespace

    from trader_assist_v0.nautilus_e4.native_capture import NativeUniverse

    universe = NativeUniverse(("ETH", "xyz:SKHX"), None)
    with pytest.raises(ValueError, match="MISSING"):
        universe.current_snapshot(now_ns=1)

    class Identity:
        venue = "HYPERLIQUID"

        def __init__(self, symbol: str) -> None:
            self.symbol = symbol

        def __str__(self) -> str:
            return self.symbol + ".HYPERLIQUID"

    for coin, symbol in (("ETH", "provider-eth"), ("xyz:SKHX", "provider-rwa")):
        native = SimpleNamespace(
            raw_symbol=coin, id=Identity(symbol), to_dict=lambda value=coin: {"coin": value}
        )
        expression = universe.admit(native)
        assert expression is not None
        assert expression.instrument_id == str(native.id)
    snapshot = universe.current_snapshot(now_ns=1)
    pinned = NativeUniverse(("ETH", "xyz:SKHX"), snapshot)
    with pytest.raises(ValueError, match="identity mismatch"):
        pinned.admit(SimpleNamespace(raw_symbol="ETH", id=native.id))
    assert not universe.missing
    with pytest.raises(ValueError, match="approved registry"):
        NativeUniverse(("ETH", "fake:NEW"), None)


@pytest.mark.parametrize("minutes", [1, 5])
def test_native_closed_bar_admission_has_no_partial_or_future_bar(minutes: int) -> None:
    from types import SimpleNamespace

    from trader_assist_v0.nautilus_e4.native_capture import closed_bar_window

    duration = minutes * 60_000_000_000
    event = SimpleNamespace(
        bar_type=SimpleNamespace(spec=SimpleNamespace(step=minutes)),
        ts_event=duration,
        ts_init=2 * duration,
    )
    assert closed_bar_window(event, now_ns=2 * duration) == (
        duration // 1_000_000,
        2 * duration // 1_000_000 - 1,
    )
    event.ts_init -= 1
    with pytest.raises(ValueError, match="NOT_CLOSED"):
        closed_bar_window(event, now_ns=2 * duration)
    event.ts_init = 2 * duration + 1
    with pytest.raises(ValueError, match="FUTURE"):
        closed_bar_window(event, now_ns=2 * duration)
