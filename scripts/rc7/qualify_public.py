"""Bounded isolated public native reconnect/staging proof; never usable as an execution launcher."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.native_catalog import read_staged_run


def qualify(root: Path, output: Path) -> dict[str, Any]:
    if platform.system() != "Linux" or sys.version_info[:2] != (3, 13):
        raise RuntimeError("isolated Linux Python 3.13 required")
    if root.exists() and any(root.iterdir()):
        raise ValueError("qualification requires a fresh isolated catalog root")
    output.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "FAIL",
        "public_provider": "NOT_QUALIFIED",
        "sandbox": "NOT_QUALIFIED",
        "real_execution": "OFF_NO_CLIENT",
        "target_host_24h": "NOT_RUN",
        "started_ns": time.time_ns(),
    }
    try:
        command = [
            sys.executable,
            "-m",
            "scripts.rc7.run_public",
            "--root",
            str(root),
            "--duration-seconds",
            "420",
            "--qualification-reconnect",
            "--provider-coins",
            "ETH",
            "xyz:SKHX",
        ]
        with (output / "capture.log").open("w") as log:
            with subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT) as process:
                try:
                    # One process/one writer: native reconnect at ~60s, inspect
                    # sealed stage while still running, then explicit test stop.
                    process.wait(timeout=330)
                    raise RuntimeError("PUBLIC_CAPTURE_STOPPED_BEFORE_ACTIVE_STAGE_PROBE")
                except subprocess.TimeoutExpired:
                    health = json.loads((root / "health.json").read_text())
                    active = read_staged_run(root, health["instance_id"])
                    if (
                        not active["types"].get("QuoteTick", {}).get("count")
                        or not active["open_partials"]
                    ):
                        process.terminate()
                        raise RuntimeError("NATIVE_ACTIVE_STAGE_NOT_QUALIFIED") from None
                    active["same_capture_pid"] = process.pid
                    (output / "active-stage-proof.json").write_text(json.dumps(active, indent=2))
                try:
                    exit_code = process.wait(timeout=240)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise RuntimeError("PUBLIC_QUALIFICATION_TIMEOUT") from None
        if exit_code:
            raise RuntimeError(f"NATIVE_PUBLIC_RUNTIME_EXIT:{exit_code}")
        proof = json.loads((root / "close-proof.json").read_text())
        (output / "close-proof.json").write_text(json.dumps(proof, indent=2))
        if proof["public_coverage"] != "PASS":
            raise RuntimeError("PUBLIC_STREAM_COVERAGE_INCOMPLETE")
        recovered = [
            gap
            for gap in proof["stream_gaps"]
            if gap["reason"] == "NATIVE_DISCONNECT" and gap["next_ts_init"] is not None
        ]
        if not proof["reconnect_probe_requested"] or not recovered:
            raise RuntimeError("NATIVE_SOCKET_RECONNECT_NOT_QUALIFIED")
        result.update(
            status="PASS_BOUNDED_CONTINUOUS_NODE_STAGE_AND_NATIVE_RECONNECT",
            public_provider="PASS_ETH_AND_XYZ_SKHX_ALL_FIVE_STREAMS",
            sandbox="NOT_RUN_APPROVED_STRATEGY_ORDER_MAPPING_MISSING",
            recovered_stream_gaps=recovered,
            stage=proof["types"],
            parquet_catalog="NOT_AUTOMATICALLY_PROMOTED_NOT_LIVE_QUALIFIED",
            native_node_processes=1,
            writer_restarts=0,
        )
    except Exception as exc:
        result["failure"] = f"{type(exc).__name__}:{exc}"
    finally:
        result["finished_ns"] = time.time_ns()
        (output / "public-qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = qualify(args.root, args.output)
    print(json.dumps({key: result[key] for key in ("status", "public_provider", "real_execution")}))
    if result["status"] == "FAIL":
        raise SystemExit(result.get("failure", "PUBLIC_QUALIFICATION_FAILED"))


if __name__ == "__main__":
    main()
