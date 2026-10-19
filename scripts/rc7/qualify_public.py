"""Bounded isolated public/Sandbox proof; never usable as an execution launcher."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from trader_assist_v0.nautilus_e4.native_catalog import replay_catalog_quotes


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
        proofs = []
        for phase, universe, duration in (
            ("initial", ["--provider-coins", "ETH", "xyz:SKHX"], 420),
            ("restart", ["--snapshot", str(root / "resolved-pit-universe.json")], 60),
        ):
            command = [
                sys.executable,
                "-m",
                "scripts.rc7.run_public",
                "--root",
                str(root),
                "--duration-seconds",
                str(duration),
                "--sandbox",
                "--sandbox-probe",
                "--maker-rate",
                "0.00015",
                "--taker-rate",
                "0.00045",
                *universe,
            ]
            with (output / f"{phase}.log").open("w") as log:
                completed = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=duration + 150,
                )
            if completed.returncode:
                raise RuntimeError(f"{phase}:NATIVE_PUBLIC_RUNTIME_EXIT:{completed.returncode}")
            proof = json.loads((root / "close-proof.json").read_text())
            (output / f"{phase}-close-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
            proofs.append(proof)
        if proofs[0]["public_coverage"] != "PASS":
            raise RuntimeError("PUBLIC_STREAM_COVERAGE_INCOMPLETE")
        result["public_provider"] = "PASS_ETH_AND_XYZ_SKHX_ALL_FIVE_STREAMS"
        result["restart"] = json.loads((root / "recovery-proof.json").read_text())
        result["replay"] = replay_catalog_quotes(root, proofs[0]["instance_id"])
        result["sandbox"] = proofs[0]["sandbox"]
        if result["sandbox"].get("status") != "OBSERVED":
            raise RuntimeError("SANDBOX_NO_NATIVE_FILL_OBSERVED")
        result["status"] = "PASS_BOUNDED_CAPTURE_RECOVERY_REPLAY_SANDBOX_OBSERVED"
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
